"""MDN and CRPS surrogate models, built on torchnaut.

`digital_twinning.PredictiveModel` only dispatches on method in
{"DNN", "gPCE", "GBT", "LinReg"} - it has no notion of MDN/CRPS. These classes subclass
`PredictiveModel` and override just the method-dispatch points (`get_model`,
`train_and_validate`, `predict`, the scaler defaults, `get_mean_and_var`) so
`train_test_split`, `evaluate_model`, `save_model`, and pickling are reused
unmodified from the base class.

Training loop (AdamW + LR warmup + early stopping + grad clipping) and the MDN
log-likelihood clamp follow the reference torchnaut notebook this was built
from. `predict` stays mean-only (what `evaluate_model`/SHAP/Sobol expect);
`predict_samples` additionally returns draws from the predictive distribution,
used by `plot_predicted_vs_feature` for confidence-band plots.
"""

from copy import deepcopy

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap
from SALib.analyze import sobol

from digital_twinning import PredictiveModel
from torchnaut.mdn import MDNMV
from torchnaut.crps import EpsilonSampler, crps_loss_mv

# Noise dimensions fed into the CRPS backbone via EpsilonSampler. Not exposed
# in the UI (only the number of samples drawn per prediction, numSamplers, is).
CRPS_NOISE_DIM = 8

# Floor on mixture log-probabilities during MDN training, to keep NLL finite
# for near-zero-density samples early in training.
MDN_MIN_LOG_PROBA = -20

# Training-loop hyperparameters that aren't exposed in the UI (only
# optimizer/epochs/batch_size are); values follow the reference notebook.
TRAIN_LR = 1e-3
TRAIN_L2REG = 1e-6
TRAIN_WARMUP_EPOCHS = 10
TRAIN_MAX_PATIENCE = 50
TRAIN_GRAD_CLIP_NORM = 10

_ACTIVATIONS = {
    'gelu': nn.GELU,
    'relu': nn.ReLU,
    'sigmoid': nn.Sigmoid,
    'tanh': nn.Tanh,
    'leakyrelu': nn.LeakyReLU,
    'softmax': lambda: nn.Softmax(dim=-1),
    'none': nn.Identity,
}


def _build_hidden_layers(input_size, layers):
    modules = []
    prev_size = input_size
    for layer in layers:
        neurons = int(layer.get('neurons') or 32)
        activation = (layer.get('activation') or 'relu').lower()
        dropout = float(layer.get('dropout') or 0.0)
        modules.append(nn.Linear(prev_size, neurons))
        modules.append(_ACTIVATIONS.get(activation, nn.ReLU)())
        modules.append(nn.Dropout(dropout))
        prev_size = neurons
    return nn.Sequential(*modules), prev_size


def _coerce_train_config(optimizer, epochs, batch_size):
    optimizer = (optimizer or 'adam').lower()
    epochs = int(epochs) if epochs not in (None, '') else 5
    batch_size = int(batch_size) if batch_size not in (None, '') else 64
    return optimizer, epochs, batch_size


def _make_optimizer(name, params, lr=TRAIN_LR, weight_decay=TRAIN_L2REG):
    if name == 'rmsprop':
        return optim.RMSprop(params, lr=lr, weight_decay=weight_decay)
    return optim.AdamW(params, lr=lr, weight_decay=weight_decay)


def _train_with_early_stopping(model, loss_fn, train_loader, val_loader, tag,
                                optimizer='adam', max_epoch=5, max_patience=TRAIN_MAX_PATIENCE):
    """Shared MDN/CRPS training loop: AdamW/RMSprop + LR warmup + grad clipping +
    early stopping on validation loss, restoring the best-seen weights at the end.
    `loss_fn(model, xb, yb) -> scalar loss tensor` carries all model-specific behavior.
    """
    opt = _make_optimizer(optimizer, model.parameters())
    scheduler = optim.lr_scheduler.LinearLR(opt, start_factor=0.1, total_iters=TRAIN_WARMUP_EPOCHS)

    best_val, best_state, bad_epochs = float("inf"), deepcopy(model.state_dict()), 0
    avg_train_loss, avg_val_loss = 0.0, 0.0

    for epoch in range(max_epoch + 1):
        model.train()
        running = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(model.device), yb.to(model.device)
            opt.zero_grad()
            loss = loss_fn(model, xb, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=TRAIN_GRAD_CLIP_NORM)
            opt.step()
            running += loss.item()
        scheduler.step()
        avg_train_loss = running / max(len(train_loader), 1)

        model.eval()
        val_running = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(model.device), yb.to(model.device)
                val_running += loss_fn(model, xb, yb).item()
        avg_val_loss = val_running / max(len(val_loader), 1)

        if epoch % 50 == 0:
            print(f"[{tag}] Epoch [{epoch}/{max_epoch}], train: {avg_train_loss:.4f}, val: {avg_val_loss:.4f}")

        if avg_val_loss < best_val - 1e-6:
            best_val, best_state, bad_epochs = avg_val_loss, deepcopy(model.state_dict()), 0
        else:
            bad_epochs += 1
        if bad_epochs > max_patience:
            print(f"[{tag}] Early stopping at epoch {epoch} (best val loss {best_val:.4f})")
            break

    model.load_state_dict(best_state)
    model.eval()
    return avg_train_loss, avg_val_loss


class _SensitivityMixin:
    """Sobol + SHAP support for the torchnaut models, computed on the predictive
    *mean* (`PredictiveModel.predict`).

    `PredictiveModel.get_sobol_sensitivity` / `get_shap_values` dispatch to
    `self.model.compute_partial_vars` / `self.model.get_shap_values`, which the
    four built-in methods define but MDN/CRPS otherwise don't. These mirror the
    `digital_twinning` DNN implementations (SALib Saltelli for Sobol, a SHAP
    `KernelExplainer` over `predict`), so everything downstream - the plots,
    `subtract_effects` - works unchanged. Only the mean response is decomposed;
    the learned aleatoric spread is not.
    """

    def compute_partial_vars(self, model_obj, max_index):
        variableset = model_obj.Q
        QoI_names = model_obj.QoI_names

        problem = {
            'num_vars': variableset.num_variables(),
            'names': variableset.variable_names(),
            'dists': variableset.get_dist_types(),
            'bounds': variableset.get_dist_params(),
        }

        q = variableset.sample(method='Sobol_saltelli', n=8192)  # N * (2D + 2); Saltelli needs uniform inputs
        y = np.asarray(model_obj.predict(q))

        S1, S2 = [], []
        cols_S1, cols_S2 = [], []
        for i in range(y.shape[1]):
            Si_i = sobol.analyze(problem, y[:, i])
            _, first_Si, (_, second_Si) = sobol.Si_to_pandas_dict(Si_i)
            df = Si_i.to_df()
            cols_S1 = list(df[1].index)
            cols_S2 = list(df[2].index)
            S1.append(first_Si['S1'])
            S2.append(second_Si['S2'])

        S1, S2 = np.array(S1), np.array(S2)

        col_names, sobol_index = cols_S1, S1
        if max_index == 2:
            sobol_index = np.concatenate([S1, S2], axis=1)
            col_names = list(cols_S1) + list(cols_S2)

        def _label(x):
            if isinstance(x, (tuple, list, np.ndarray)):
                return ' '.join(map(str, x))
            return str(x)

        col_names = [_label(x) for x in col_names]

        y_var = y.var(axis=0).reshape(-1, 1)
        partial_variance = sobol_index * y_var

        partial_var_df = pd.DataFrame(partial_variance, columns=col_names, index=QoI_names)
        sobol_index_df = pd.DataFrame(sobol_index, columns=col_names, index=QoI_names)
        return partial_var_df, sobol_index_df, y_var

    def get_shap_values(self, predict_fn, q, forced=False, explainer_type="kernelexplainer", silent=False):
        if not hasattr(self, 'explainer') or forced:
            self.explainer = shap.KernelExplainer(predict_fn, q)
        return self.explainer(q, silent=silent)

    def __getstate__(self):
        # the SHAP explainer holds a reference to the bound predict method (and
        # isn't reliably picklable); drop it, like the digital_twinning models do.
        state = self.__dict__.copy()
        state.pop('explainer', None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)


class MDNModel(_SensitivityMixin, nn.Module):
    """Backbone network + torchnaut MDNMV mixture head."""

    def __init__(self, input_size, output_size, layers, num_components):
        super().__init__()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.head = MDNMV(n_components=num_components, target_dim=output_size)
        self.backbone, prev_size = _build_hidden_layers(input_size, layers)
        self.output_layer = nn.Linear(prev_size, self.head.network_output_dim)
        self.to(self.device)

    def forward(self, x):
        return self.output_layer(self.backbone(x))

    def train_and_validate(self, q_train, y_train, q_val, y_val, optimizer='adam', epochs=5, batch_size=64, **_ignored):
        optimizer, epochs, batch_size = _coerce_train_config(optimizer, epochs, batch_size)
        train_loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(q_train, y_train), batch_size=batch_size, shuffle=True
        )
        val_loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(q_val, y_val), batch_size=batch_size, shuffle=False
        )

        def loss_fn(model, xb, yb):
            return -model.head.log_likelihood(model(xb), yb, min_log_proba=MDN_MIN_LOG_PROBA).mean()

        return _train_with_early_stopping(
            self, loss_fn, train_loader, val_loader, tag="MDN", optimizer=optimizer, max_epoch=epochs
        )

    def predict(self, q):
        self.eval()
        preds = []
        with torch.no_grad():
            for start in range(0, q.shape[0], 512):
                chunk = q[start:start + 512].to(self.device)
                preds.append(self.head.expected_value(self(chunk)).cpu().numpy())
        return np.concatenate(preds, axis=0)

    def predict_samples(self, q, n_samples=2000):
        """Returns `(mean, draws)`: the mixture's expected value per row, and
        `n_samples` draws per row from the predictive mixture distribution -
        both still in scaled/network units (chunked over `q` to bound memory)."""
        self.eval()
        means, draws = [], []
        with torch.no_grad():
            for start in range(0, q.shape[0], 512):
                chunk = q[start:start + 512].to(self.device)
                out = self(chunk)
                means.append(self.head.expected_value(out).cpu().numpy())
                draws.append(self.head.sample(out, n=n_samples).cpu().numpy())
        return np.concatenate(means, axis=0), np.concatenate(draws, axis=0)


class CRPSModel(_SensitivityMixin, nn.Module):
    """Backbone network trained against the (multivariate) CRPS / energy score."""

    def __init__(self, input_size, output_size, layers, num_samplers):
        super().__init__()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.num_samplers = int(num_samplers) if num_samplers else 100
        self.sampler = EpsilonSampler(CRPS_NOISE_DIM)
        self.backbone, prev_size = _build_hidden_layers(input_size + CRPS_NOISE_DIM, layers)
        self.output_layer = nn.Linear(prev_size, output_size)
        self.to(self.device)

    def forward(self, x, n_samples=None):
        xs = self.sampler(x, n_samples=n_samples or self.num_samplers)
        return self.output_layer(self.backbone(xs))

    def train_and_validate(self, q_train, y_train, q_val, y_val, optimizer='adam', epochs=5, batch_size=64, **_ignored):
        optimizer, epochs, batch_size = _coerce_train_config(optimizer, epochs, batch_size)
        train_loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(q_train, y_train), batch_size=batch_size, shuffle=True
        )
        val_loader = torch.utils.data.DataLoader(
            torch.utils.data.TensorDataset(q_val, y_val), batch_size=batch_size, shuffle=False
        )

        def loss_fn(model, xb, yb):
            return crps_loss_mv(model(xb), yb).mean()

        return _train_with_early_stopping(
            self, loss_fn, train_loader, val_loader, tag="CRPS", optimizer=optimizer, max_epoch=epochs
        )

    def predict(self, q):
        self.eval()
        preds = []
        with torch.no_grad():
            for start in range(0, q.shape[0], 512):
                chunk = q[start:start + 512].to(self.device)
                yps = self(chunk, n_samples=self.num_samplers)
                preds.append(yps.mean(dim=-2).cpu().numpy())
        return np.concatenate(preds, axis=0)

    def predict_samples(self, q, n_samples=2000):
        """Returns `(mean, draws)`: the sample-mean prediction per row, and the
        `n_samples` raw draws per row the mean was computed from - both still
        in scaled/network units (chunked over `q` to bound memory)."""
        self.eval()
        means, draws = [], []
        with torch.no_grad():
            for start in range(0, q.shape[0], 512):
                chunk = q[start:start + 512].to(self.device)
                yps = self(chunk, n_samples=n_samples)
                means.append(yps.mean(dim=-2).cpu().numpy())
                draws.append(yps.cpu().numpy())
        return np.concatenate(means, axis=0), np.concatenate(draws, axis=0)


class _TorchnautPredictiveModel(PredictiveModel):
    """Shared plumbing for the MDN/CRPS PredictiveModel subclasses.

    Only overrides the points where the base class hard-codes a
    `match self.method` over the four built-in methods; `train`,
    `train_test_split`, `evaluate_model`, `save_model` and pickling are
    inherited unchanged.
    """

    def get_q_scaler(self, q, q_scaler, scale_method='default'):
        if scale_method == 'default':
            scale_method = 'minmax'
        return super().get_q_scaler(q, q_scaler, scale_method)

    def get_y_scaler(self, y, y_scaler, scale_method='default'):
        if scale_method == 'default':
            scale_method = 'minmax'
        return super().get_y_scaler(y, y_scaler, scale_method)

    def train(self, q_train, y_train, train_config=None, q_scaler=None, y_scaler=None, k_fold=None, **params):
        # `on_train` calls `model.train(x, y, t_cfg)` positionally; the base
        # class's 3rd positional parameter is `q_scaler` (unused by minmax
        # scaling), so the config would otherwise never reach **params.
        if train_config:
            params = {**train_config, **params}
        return super().train(q_train, y_train, q_scaler=q_scaler, y_scaler=y_scaler, k_fold=k_fold, **params)

    def train_and_validate(self, xi_train, yt_train, xi_val, yt_val, **params):
        xi_tr = torch.tensor(xi_train, dtype=torch.float64)
        xi_vl = torch.tensor(xi_val, dtype=torch.float64)
        yt_tr = torch.tensor(yt_train, dtype=torch.float64)
        yt_vl = torch.tensor(yt_val, dtype=torch.float64)
        return self.model.train_and_validate(xi_tr, yt_tr, xi_vl, yt_vl, **params)

    def predict(self, q, **params):
        if not isinstance(q, pd.DataFrame):
            q = pd.DataFrame(q, columns=self.Q.variable_names())
        xi = self.get_scaled_q(q)
        xi = torch.tensor(xi, dtype=torch.float64)
        y_t = self.model.predict(xi, **params)
        return self.get_orig_y(y_t)

    def predict_samples(self, q, n_samples=2000):
        """Like `predict`, but also returns `n_samples` draws per row from the
        predictive distribution, both descaled to original y-units. Kept separate
        from `predict` since `evaluate_model`/SHAP/Sobol expect a mean-only result;
        used for confidence-band plotting (`plot_predicted_vs_feature`) instead."""
        if not isinstance(q, pd.DataFrame):
            q = pd.DataFrame(q, columns=self.Q.variable_names())
        xi = self.get_scaled_q(q)
        xi = torch.tensor(xi, dtype=torch.float64)
        mean_t, draws_t = self.model.predict_samples(xi, n_samples=n_samples)
        mean = self.get_orig_y(mean_t)
        n, k, d = draws_t.shape
        draws = self.get_orig_y(draws_t.reshape(-1, d)).reshape(n, k, d)
        return mean, draws

    def get_mean_and_var(self, n_sample=1000):
        q = self.Q.sample(n_sample)
        q_df = pd.DataFrame(q, columns=self.Q.variable_names())
        y_predict = self.predict(q_df)
        return y_predict.mean(axis=0), y_predict.var(axis=0)


class MDNPredictiveModel(_TorchnautPredictiveModel):
    def get_model(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        layers = self.init_config.get("layers", [])
        num_components = int(self.init_config.get("numComponents") or 5)
        model = MDNModel(self.Q.num_variables(), len(self.QoI_names), layers, num_components)
        return model.double()


class CRPSPredictiveModel(_TorchnautPredictiveModel):
    def get_model(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        layers = self.init_config.get("layers", [])
        num_samplers = int(self.init_config.get("numSamplers") or 100)
        model = CRPSModel(self.Q.num_variables(), len(self.QoI_names), layers, num_samplers)
        return model.double()


def plot_predicted_vs_feature(model, X_train, X_val, y_train, y_val, feature,
                               X_test=None, y_test=None, qoi=None,
                               ci_level=0.95, n_samples=2000, ylabel=None, xlabel=None):
    """Scatter observations against `feature` (a column of X), overlaid with the
    model's predicted mean and a `ci_level` confidence band built from samples
    drawn via `model.predict_samples`. `model` is a trained `MDNPredictiveModel`
    or `CRPSPredictiveModel`.

    Follows the Granada workflow: train/val come from the reference-period split,
    and `X_test`/`y_test` (optional) is a separately supplied held-out evaluation
    set (e.g. a later period). When given, its observations are drawn in a
    distinct colour. `qoi` picks which output column to plot (defaults to the
    single QoI when the model has only one).

    Returns the `Figure` (caller ships it out, e.g. via `fig_to_binary`) rather
    than calling `plt.show()`.
    """
    if feature not in X_train.columns:
        raise ValueError(f"feature must be one of {list(X_train.columns)}, got {feature!r}")

    qoi_names = list(y_train.columns)
    if qoi is None:
        if len(qoi_names) != 1:
            raise ValueError(f"qoi must be one of {qoi_names} when the model has multiple outputs")
        qoi = qoi_names[0]
    if qoi not in qoi_names:
        raise ValueError(f"qoi must be one of {qoi_names}, got {qoi!r}")
    q_idx = qoi_names.index(qoi)

    has_test = X_test is not None and y_test is not None
    X_ref = pd.concat([X_train, X_val], axis=0)
    y_ref = pd.concat([y_train, y_val], axis=0)
    X_all = pd.concat([X_ref, X_test], axis=0) if has_test else X_ref
    y_all = pd.concat([y_ref, y_test], axis=0) if has_test else y_ref

    pred_mean, draws = model.predict_samples(X_all, n_samples=n_samples)
    pred_mean = np.asarray(pred_mean)[:, q_idx]
    draws = np.asarray(draws)[:, :, q_idx]
    lower = np.quantile(draws, (1 - ci_level) / 2, axis=1)
    upper = np.quantile(draws, 1 - (1 - ci_level) / 2, axis=1)

    x_vals = X_all[feature].values
    y_np = y_all[qoi].values
    order = np.argsort(x_vals)
    n_ref = len(X_ref)

    fig, ax = plt.subplots(figsize=(10, 6))
    fontsize = 14

    ax.fill_between(
        x_vals[order], lower[order], upper[order],
        color='tab:blue', alpha=0.25, zorder=1, label=f'{int(ci_level * 100)}% CI',
    )
    ref_mask = order < n_ref
    ax.scatter(x_vals[order][ref_mask], y_np[order][ref_mask], s=8, color='gray',
               alpha=0.5, zorder=2, label='observed (reference)')
    if has_test:
        ax.scatter(x_vals[order][~ref_mask], y_np[order][~ref_mask], s=8, color='tab:orange',
                   alpha=0.6, zorder=2, label='observed (held-out)')
    ax.plot(x_vals[order], pred_mean[order], color='tab:blue', linewidth=2, zorder=3, label='predicted mean')

    ax.set_xlabel(xlabel or feature, fontsize=fontsize)
    ax.set_ylabel(ylabel or f'Predicted {qoi}', fontsize=fontsize)
    ax.set_title(f'Predicted mean vs. {feature}, {int(ci_level * 100)}% CI', fontsize=fontsize + 2)
    ax.legend(fontsize=fontsize - 2)
    ax.tick_params(axis='both', labelsize=fontsize - 2)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    return fig
