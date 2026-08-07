"""MDN and CRPS surrogate models, built on torchnaut.

`digital_twinning.PredictiveModel` only dispatches on method in
{"DNN", "gPCE", "GBT", "LinReg"} - it has no notion of MDN/CRPS. These classes subclass
`PredictiveModel` and override just the method-dispatch points (`get_model`,
`train_and_validate`, `predict`, the scaler defaults, `get_mean_and_var`) so
`train_test_split`, `evaluate_model`, `save_model`, and pickling are reused
unmodified from the base class.
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd

from digital_twinning import PredictiveModel
from torchnaut.mdn import MDNMV
from torchnaut.crps import EpsilonSampler, crps_loss_mv

# Noise dimensions fed into the CRPS backbone via EpsilonSampler. Not exposed
# in the UI (only the number of samples drawn per prediction, numSamplers, is).
CRPS_NOISE_DIM = 8

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


def _make_optimizer(name, params):
    if name == 'rmsprop':
        return optim.RMSprop(params)
    return optim.Adam(params)


class MDNModel(nn.Module):
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
        opt = _make_optimizer(optimizer, self.parameters())

        avg_train_loss, avg_val_loss = 0.0, 0.0
        for epoch in range(epochs + 1):
            self.train()
            running = 0.0
            for xb, yb in train_loader:
                xb, yb = xb.to(self.device), yb.to(self.device)
                opt.zero_grad()
                loss = -self.head.log_likelihood(self(xb), yb).mean()
                loss.backward()
                opt.step()
                running += loss.item()
            avg_train_loss = running / max(len(train_loader), 1)

            self.eval()
            val_running = 0.0
            with torch.no_grad():
                for xb, yb in val_loader:
                    xb, yb = xb.to(self.device), yb.to(self.device)
                    val_running += (-self.head.log_likelihood(self(xb), yb).mean()).item()
            avg_val_loss = val_running / max(len(val_loader), 1)

            if epoch % 50 == 0:
                print(f"[MDN] Epoch [{epoch}/{epochs}], train NLL: {avg_train_loss:.4f}, val NLL: {avg_val_loss:.4f}")

        return avg_train_loss, avg_val_loss

    def predict(self, q):
        self.eval()
        preds = []
        with torch.no_grad():
            for start in range(0, q.shape[0], 512):
                chunk = q[start:start + 512].to(self.device)
                preds.append(self.head.expected_value(self(chunk)).cpu().numpy())
        return np.concatenate(preds, axis=0)


class CRPSModel(nn.Module):
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
        opt = _make_optimizer(optimizer, self.parameters())

        avg_train_loss, avg_val_loss = 0.0, 0.0
        for epoch in range(epochs + 1):
            self.train()
            running = 0.0
            for xb, yb in train_loader:
                xb, yb = xb.to(self.device), yb.to(self.device)
                opt.zero_grad()
                yps = self(xb)
                loss = crps_loss_mv(yps, yb).mean()
                loss.backward()
                opt.step()
                running += loss.item()
            avg_train_loss = running / max(len(train_loader), 1)

            self.eval()
            val_running = 0.0
            with torch.no_grad():
                for xb, yb in val_loader:
                    xb, yb = xb.to(self.device), yb.to(self.device)
                    val_running += crps_loss_mv(self(xb), yb).mean().item()
            avg_val_loss = val_running / max(len(val_loader), 1)

            if epoch % 50 == 0:
                print(f"[CRPS] Epoch [{epoch}/{epochs}], train CRPS: {avg_train_loss:.4f}, val CRPS: {avg_val_loss:.4f}")

        return avg_train_loss, avg_val_loss

    def predict(self, q):
        self.eval()
        preds = []
        with torch.no_grad():
            for start in range(0, q.shape[0], 512):
                chunk = q[start:start + 512].to(self.device)
                yps = self(chunk, n_samples=self.num_samplers)
                preds.append(yps.mean(dim=-2).cpu().numpy())
        return np.concatenate(preds, axis=0)


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
