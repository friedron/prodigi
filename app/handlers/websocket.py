import asyncio
import base64
import io
import json
import logging
import os
import pickle
import struct
import sys
import tempfile
import time
import uuid
import contextlib
import functools
from types import SimpleNamespace
import bimquake
import pandas as pd
import numpy as np
import socketio
import tornado
from tornado.ioloop import PeriodicCallback

# Science & Engineering imports
import plotly.io as pio
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table as RLTable, TableStyle

# Installed packages
from digital_twinning import (
    DigitalTwin, JointManager, utils,
    gPCE, GBT, DNN, LinReg, MOSAIC, MDN, CRPS,
    get_modes_and_nodes, plot_modal_validation_errors,
)
from digital_twinning.model_updating.mcmc_animation import animate_MCMC_walk
from digital_twinning.utils import preprocess_modeshape_data as ppm
from uncertain_variables import generate_stndrn_variable_set
from uncertain_variables.variable_set import VariableSet
from uncertain_variables.variable import Variable
from uncertain_variables.distributions import NormalDistribution, UniformDistribution, LogNormalDistribution, BetaDistribution, ExponentialDistribution, TranslatedDistribution
import utils.climate_resilience as cr
import utils.climate_plotting as cp



# Local library imports
from utils.preprocess_modeshape_data import (
    plot_correlation,
    scatter_plot,
)
import utils.get_openmeteo_data as openmeteo
from handlers.rate_limiter import RateLimiter
from handlers.safe_unpickle import restricted_loads

# Configuration
os.environ["SCIPY_ARRAY_API"] = "1"
# base_dir points to the 'app' directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class AppHandler(socketio.AsyncNamespace):
    def __init__(self, application, args):
        super().__init__("/")
        self.application = application
        self.args = args
        self.data = {}  # Keyed by socket ID
        self.socket_to_session = {} # Keyed by session ID
        self.last_activity = {}
        self.cleanup_callback = None
        self.rate_limiter = RateLimiter(max_requests=200, window_seconds=60)
        self.setup_cleanup_task()

    # --- Session & Lifecycle ---
    def setup_cleanup_task(self):
        if self.cleanup_callback is None:
            # 1 hour check interval (3600 * 1000 ms)
            self.cleanup_callback = PeriodicCallback(
                self.cleanup_expired_sessions, 3600 * 1000
            )
            self.cleanup_callback.start()

    async def cleanup_expired_sessions(self):
        try:
            now = time.time()
            expired_sids = [
                sid for sid, last_active in self.last_activity.items()
                if now - last_active > 172800  # 2 days
            ]

            for sid in expired_sids:
                self.data.pop(sid, None)
                self.last_activity.pop(sid, None)
                # Reverse lookup for session cleanup if needed
                session_id = next((k for k, v in self.socket_to_session.items() if v == sid), None)
                if session_id:
                    self.socket_to_session.pop(session_id)
                logging.info(f"Cleaned up expired session: {sid}")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")

    def decode_session_token(self, token):
        if token:
            try:
                decoded = tornado.web.decode_signed_value(
                    secret=self.application.settings["cookie_secret"],
                    name="session_id",
                    value=token,
                    max_age_days=3,
                )
                if decoded:
                    return decoded.decode()
            except Exception as e:
                logging.error(f"Session decoding error: {e}")
        return None

    def get_or_create_session_id(self, auth):
        auth = auth or {}
        session_id = self.decode_session_token(auth.get("session"))
        if session_id:
            return session_id
        # A new tab or browser start resumes the last session left, unless it's still open in another tab.
        last_id = self.decode_session_token(auth.get("last"))
        if last_id:
            current_sid = self.socket_to_session.get(last_id)
            if not (current_sid and self.server.manager.is_connected(current_sid, self.namespace)):
                return last_id
        return str(uuid.uuid4())

    async def on_connect(self, sid, environ, auth=None):
        logging.info(f"Client connected: {sid}")
        self.data[sid] = {}
        self.last_activity[sid] = time.time()
        session_id = self.get_or_create_session_id(auth)
        # The tab keeps this token and sends it back on reconnect; a cookie can't do this
        # because the socket's origin isn't necessarily the one serving the page.
        token = tornado.web.create_signed_value(
            self.application.settings["cookie_secret"], "session_id", session_id
        ).decode()
        restored = bool(self.data.get(self.socket_to_session.get(session_id)))
        await self.emit("session", {"id": session_id, "token": token, "restored": restored}, to=sid)
        try:
            await self.restore_client_data(sid, session_id)
        except Exception as e:
            # An exception here would make Socket.IO reject the connection, leaving the page with no socket.
            logging.error(f"Restore session error: {e}")
        self.socket_to_session[session_id] = sid

    async def on_disconnect(self, sid):
        logging.info(f"Client disconnected: {sid}")

    async def on_clear_session(self, sid):
        self.data[sid] = {}

    async def restore_client_data(self, sid, session_id):
        old_sid = self.socket_to_session.get(session_id)
        if old_sid and old_sid in self.data:
            self.data[sid] = self.data.pop(old_sid)
        else:
            self.data[sid] = {}
        
        d = self.data[sid]
        if not d: return

        # Restore stateful components
        if d.get("mode"): await self.emit("mode", d["mode"], to=sid)
        if d.get("model"): await self.send_model(sid)
        if d.get("variableset"): await self.send_variableset(sid)
        if d.get("zmean") is not None: await self.emit("zmean", d["zmean"].to_dict(), to=sid)
        if d.get("sigma") is not None: await self.emit("sigma", d["sigma"].to_dict(), to=sid)
        if d.get("subtract_input") is not None: await self.emit("subtract_input", d["subtract_input"].to_dict(), to=sid)
        if d.get("subtract_output") is not None: await self.emit("subtract_output", d["subtract_output"].to_dict(), to=sid)
        
        if d.get("models"):
            await self.emit("models", self.format_models(d["models"]), to=sid)
            await self.send_multi_measurements(sid)
            if d.get("joint_manager"): await self.emit("joint_created", to=sid)
        
        if d.get("building_data"): await self.emit("building_data", json.dumps(d["building_data"]), to=sid)
        if d.get("climate_fig"): await self.emit("climate_fig", d["climate_fig"], to=sid)
        if d.get("mcmc_animation"): await self.emit("mcmc_animation", d["mcmc_animation"], to=sid)
        if d.get("sample") is not None: await self.emit("sample", d["sample"].to_numpy().tolist(), to=sid)
        if d.get("qoi") is not None:
            await self.emit("qoi", d["qoi"].describe().to_json(), to=sid)
            await self.send_modes_and_nodes(sid, d["qoi"])

        if d.get("location_data"):
            module = "earthquake" if "ParaTR" in d["location_data"] else "climate"
            await self.emit("location_data", {
                "module": module,
                "city": d["location_data"]["city"],
                "country": d["location_data"]["country"]
            }, to=sid)

    # --- Utilities ---
    async def _check_rate_limit(self, sid):
        if not self.rate_limiter.is_allowed(sid):
            await self.emit("error", "Rate limit exceeded.", to=sid)
            return False
        return True

    def _render_png(self, fig):
        buf = io.BytesIO()
        if hasattr(fig, 'savefig'):
            fig.savefig(buf, format="png")
        else: # Handle plotly or other types if needed
            pio.write_image(fig, buf, format="png")
        buf.seek(0)
        return buf.read()

    async def fig_to_binary(self, fig):
        # Rendering is slow and CPU-bound; keep it off the event loop.
        return await asyncio.to_thread(self._render_png, fig)

    async def recieve_chunks(self, sid, data):
        name = data["name"]
        if "chunks" not in self.data[sid]: self.data[sid]["chunks"] = {}
        chunks = self.data[sid]["chunks"].setdefault(name, [])
        chunks.append(data["data"])

        if data.get("isLast"):
            complete = b"".join(chunks)
            del self.data[sid]["chunks"][name]
            return complete, name
        return None, None

    # --- Formatting ---
    def format_variables(self, variables):
        mapping = {
            "NormalDistribution": "normal",
            "UniformDistribution": "uniform",
            "LogNormalDistribution": "logNormal",
            "BetaDistribution": "beta",
            "ExponentialDistribution": "exponential",
        }
        res = []
        for name, dist in variables.items():
            cls = dist.__class__.__name__
            p = {"name": name, "distribution": mapping.get(cls, "unknown")}
            if cls in ["NormalDistribution", "LogNormalDistribution"]:
                p.update({"distParam1": dist.mu, "distParam2": dist.sigma})
            elif cls in ["UniformDistribution", "BetaDistribution"]:
                p.update({"distParam1": dist.a, "distParam2": dist.b})
            elif cls == "ExponentialDistribution":
                p.update({"distParam1": dist.lambda_})
            res.append(p)
        return res

    def format_model_config(self, model):
        # The model class names match the UI's modelType values.
        m_type = type(model).__name__
        cfg = {"modelType": m_type}
        if m_type == "MOSAIC":
            kwargs = model.class_kwargs or {}
            cfg["mosaicConfig"] = {
                "resolution": model.resolution,
                "maxDoaFrequencies": model.max_freq_degree,
                "maxDoaEigenvectors": model.max_vect_degree,
                "svcConfig": {
                    "C": kwargs.get("C", 1.0),
                    "kernel": kwargs.get("kernel", "rbf"),
                    "degree": kwargs.get("degree", 3),
                    "gamma": kwargs.get("gamma", "scale"),
                },
            }
        elif m_type == "gPCE":
            cfg["gpcConfig"] = {"trainConfig": {}, "initConfig": {"p": model.p}}
        elif m_type == "GBT":
            params = model.model.get_params()
            cfg["gbtConfig"] = {
                "trainConfig": {"maxDepth": params.get("max_depth"), "numOfIter": params.get("n_estimators")},
            }
        elif m_type == "DNN":
            cfg["nnConfig"] = {
                "trainConfig": getattr(model, "train_config", {}),
                "initConfig": {"layers": model.layers, "outputAF": model.outputAF},
            }
        return cfg

    def format_models(self, models):
        return {name: obj["model"].Q.variable_names() for name, obj in models.items()}

    # --- Data Emitters ---
    async def send_model(self, sid):
        m = self.data[sid]["model"]
        if isinstance(m, MOSAIC):
            await self.emit("train_result", "Done", to=sid)
            await self.emit("load_model", {
                "variables": self.format_variables(m.Q.variables),
                "modelConfig": self.format_model_config(m)
            }, to=sid)
            subdomains = await asyncio.to_thread(m.get_number_of_subdomains)
            await self.emit("mosaic_subdomains", np.asarray(subdomains).astype(int).tolist(), to=sid)
            return
        await self.emit("sample", m.samples.to_numpy().tolist(), to=sid)
        await self.emit("train_result", "Done", to=sid)
        await self.emit("load_model", {
            "variables": self.format_variables(m.Q.variables),
            "modelConfig": self.format_model_config(m)
        }, to=sid)
        await self.emit("qoi", m.QoI.describe().to_json(), to=sid)
        await self.emit("outputQoi", list(m.QoI_names), to=sid)
        await self.emit("features_stats", m.samples.describe().to_json(), to=sid)

    async def send_modes_and_nodes(self, sid, qoi_df):
        # MOSAIC QoI columns are "f.<mode>" and "S.<mode>.<node>.<dir>"; for any
        # other naming this yields (0, 0), so it's safe to send for every QoI load.
        try:
            n_modes, n_nodes = get_modes_and_nodes(qoi_df)
        except Exception as e:
            logging.warning(f"Could not infer modes/nodes from QoI columns: {e}")
            n_modes, n_nodes = 0, 0
        await self.emit("modes_and_nodes", {"nModes": int(n_modes), "nNodes": int(n_nodes)}, to=sid)

    async def send_modal_validation(self, sid, model, x_val, y_val):
        # Boxplots of the per-mode relative frequency and MAC errors on the validation split.
        try:
            def _plot():
                freq_errors, mac_errors = model.modal_validation(x_val, y_val)
                return plot_modal_validation_errors(freq_errors, mac_errors)
            fig = await asyncio.to_thread(_plot)
            await self.emit("mosaic_modal_validation_plot", await self.fig_to_binary(fig), to=sid)
        except Exception as e:
            logging.error(f"Modal validation error: {e}")
            await self.emit("error", f"Modal validation error: {e}", to=sid)

    async def send_mcmc_animation(self, sid, render):
        # `render(path)` writes the MCMC random-walk MP4 to `path` (needs ffmpeg). It runs
        # after the "update" event, so a failure here only loses the video, not the results.
        self.data[sid].pop("mcmc_animation", None)

        def _render():
            fd, path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)
            try:
                render(path)
                with open(path, "rb") as f:
                    return f.read()
            finally:
                if os.path.exists(path):
                    os.remove(path)

        try:
            video = await asyncio.to_thread(_render)
        except Exception as e:
            logging.error(f"MCMC animation error: {e}")
            await self.emit("mcmc_animation_error", str(e), to=sid)
            return
        self.data[sid]["mcmc_animation"] = video
        await self.emit("mcmc_animation", video, to=sid)

    def _track_mcmc_progress(self, sid, target, nwalkers, nburn, niter):
        # Emits "mcmc_progress" while `target` (DigitalTwin or JointManager) runs emcee, which
        # calls get_logprob once per walker per step plus once per walker for the start, so
        # calls // nwalkers is the step. Returns a function that removes the hook.
        loop = asyncio.get_running_loop()
        original = target.get_logprob
        nwalkers, nburn, niter = max(int(nwalkers), 1), int(nburn), int(niter)
        total = nburn + niter
        state = {"calls": 0, "last_step": -1, "last_emit": 0.0}

        def counted(*args, **kwargs):
            state["calls"] += 1
            step = min(max(state["calls"] - nwalkers, 0) // nwalkers, total)
            now = time.monotonic()
            if step != state["last_step"] and (now - state["last_emit"] >= 0.2 or step == total):
                state["last_step"], state["last_emit"] = step, now
                burning = step < nburn
                payload = {
                    "phase": "burn-in" if burning else "sampling",
                    "step": step if burning else step - nburn,
                    "total": nburn if burning else niter,
                    "fraction": step / total if total else 1.0,
                }
                asyncio.run_coroutine_threadsafe(self.emit("mcmc_progress", payload, to=sid), loop)
            return original(*args, **kwargs)

        target.get_logprob = counted
        return lambda: target.__dict__.pop("get_logprob", None)

    @staticmethod
    def _render_joint_animation(joint_manager, index, path):
        # JointManager has no animate method, so present model `index`'s slice of the
        # joint chain with the DigitalTwin attributes animate_MCMC_walk reads. The
        # joint sampler doesn't keep its burn-in, so only the sampling steps are shown.
        Q = joint_manager.models[index].Q
        chain = np.asarray(joint_manager.sampler.get_chain())[:, :, joint_manager.indices[index]]
        map_df = joint_manager.get_MAP_by_model(scaled=True)[index]
        walk = SimpleNamespace(
            model=SimpleNamespace(Q=Q),
            sampler=SimpleNamespace(get_chain=lambda: chain),
            burn_chain=None,
            get_MAP=lambda: map_df,
        )
        animate_MCMC_walk(walk, Q.sample(1000), filename=path, include_burn=False, map=True)

    async def send_variableset(self, sid):
        await self.emit("variables", self.format_variables(self.data[sid]["variableset"].variables), to=sid)

    async def send_multi_measurements(self, sid):
        res = {
            k: {
                "zmean": v["zmean"].to_dict() if "zmean" in v else {},
                "sigma": v["sigma"].to_dict() if "sigma" in v else {},
            } for k, v in self.data[sid]["models"].items()
        }
        await self.emit("multi_measurements", res, to=sid)

    # --- Data Loading Handlers ---
    async def on_load_features(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            
            df = await asyncio.to_thread(pd.read_csv, io.BytesIO(complete))
            self.data[sid]["sample"] = df
            self.data[sid]["variableset"] = utils.get_variableset_from_data(df)
            
            await self.emit("features_loaded", {"filename": name}, to=sid)
            await self.emit("sample", df.to_numpy().tolist(), to=sid)
            await self.emit("features_stats", df.describe().to_json(), to=sid)
            await self.send_variableset(sid)
        except Exception as e:
            logging.error(f"Load features error: {e}")
            await self.emit("error", f"Load features error: {e}", to=sid)

    async def on_load_sample(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return

            df = await asyncio.to_thread(pd.read_csv, io.BytesIO(complete))
            self.data[sid]["sample"] = df
            if self.data[sid].get("variableset") is None:
                self.data[sid]["variableset"] = utils.get_variableset_from_data(df)

            await self.emit("features_loaded", {"filename": name}, to=sid)
            await self.emit("sample", df.to_numpy().tolist(), to=sid)
            await self.emit("features_stats", df.describe().to_json(), to=sid)
        except Exception as e:
            logging.error(f"Load sample error: {e}")
            await self.emit("error", f"Load sample error: {e}", to=sid)

    async def on_sample(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            variableset = self.data[sid].get("variableset")
            if variableset is None:
                await self.emit("error", "Please define variables before sampling.", to=sid)
                return

            n = int(data["numSamples"])
            method = data.get("sampleMethod") or "MC"
            seed = data.get("randomSeed")
            seed = int(seed) if seed is not None and seed != "" else None

            arr = await asyncio.to_thread(
                variableset.sample, n, method=method, random_seed=seed
            )
            df = pd.DataFrame(np.asarray(arr), columns=variableset.variable_names())
            self.data[sid]["sample"] = df

            await self.emit("sample", df.to_numpy().tolist(), to=sid)
            await self.emit("features_stats", df.describe().to_json(), to=sid)
        except Exception as e:
            logging.error(f"Sampling error: {e}")
            await self.emit("error", f"Sampling error: {e}", to=sid)

    @staticmethod
    def ensure_dataframes(model):
        """The app works on DataFrames; a model trained from plain arrays stores arrays."""
        if not isinstance(model.samples, pd.DataFrame):
            model.samples = pd.DataFrame(model.samples, columns=model.Q.variable_names())
        if not isinstance(model.QoI, pd.DataFrame):
            model.QoI = pd.DataFrame(model.QoI, columns=model.QoI_names)

    async def on_load_model(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return

            model = await asyncio.to_thread(restricted_loads, complete)
            self.ensure_dataframes(model)
            # A loaded model has no split from this session; drop any left over from earlier training.
            self.data[sid].pop("train_val_split", None)
            # samples/QoI hold the features/labels selected when the model was trained.
            self.data[sid].update({
                "model": model, "variableset": model.Q,
                "sample": model.samples, "qoi": model.QoI,
                "selected_sample": model.samples, "selected_qoi": model.QoI,
            })
            await self.send_model(sid)
        except Exception as e:
            logging.error(f"Load model error: {e}")
            await self.emit("error", f"Load model error: {e}", to=sid)

    async def _load_csv_chunk(self, sid, data, *, store_key, loaded_event, data_event, formatter, error_label):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            df = await asyncio.to_thread(pd.read_csv, io.BytesIO(complete))
            self.data[sid][store_key] = df
            await self.emit(loaded_event, {"filename": name}, to=sid)
            await self.emit(data_event, formatter(df), to=sid)
        except Exception as e:
            await self.emit("error", f"{error_label}: {e}", to=sid)

    async def on_qoi_csv(self, sid, data):
        await self._load_csv_chunk(sid, data, store_key="qoi", loaded_event="labels_loaded",
                                    data_event="qoi", formatter=lambda df: df.describe().to_json(),
                                    error_label="Load QoI error")
        if self.data[sid].get("qoi") is not None:
            await self.send_modes_and_nodes(sid, self.data[sid]["qoi"])

    async def on_qoi_unv(self, sid, data):
        # Consume the upload first so the buffered chunks are always drained and
        # any validation error is emitted once (on the final chunk) rather than
        # once per chunk.
        retrieved_file, filename = await self.recieve_chunks(sid, data)
        if retrieved_file is None:
            return
        if "weather_full" not in self.data[sid]:
            await self.emit(
                "error",
                "A .unv QoI file needs weather data first: use the Input Features "
                "loader to fetch weather from the API (or upload a plain .csv QoI "
                "file instead).",
                to=sid,
            )
            return
        if self.data[sid].get("sample") is None:
            await self.emit("error", "Please load the input features before the QoI file.", to=sid)
            return
        temp_path = None
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".unv")
            with os.fdopen(fd, 'wb') as tmp:
                tmp.write(retrieved_file)

            def _process_unv(path, weather_full, x_cols):
                df = ppm.df_from_unv(path)
                modeshapes_df = ppm.merge_dataframes(df, weather_full)
                modes = sorted(df['mode_id'].unique().tolist())
                modeshapes_dict = ppm.separate__and_flip_modes(modeshapes_df)
                modeshapes_df = ppm.merge_modes(modeshapes_dict)

                # Only prune constant *target* columns (frequency/modeshapes) -
                # weather predictor columns must survive even if constant over this window.
                protected_cols = [c for c in modeshapes_df.columns if c in x_cols or c in ('Datetime', 'mode_id')]
                reduced = ppm.remove_constant_columns(modeshapes_df.drop(columns=protected_cols))
                modeshapes_df = pd.concat([modeshapes_df[protected_cols], reduced], axis=1)

                # select_cols builds a UniformDistribution(min, max) per x_col, which
                # requires min != max - drop weather columns that are constant over
                # this UNV's time window since they carry no information anyway.
                x_cols = [c for c in x_cols if modeshapes_df[c].min() != modeshapes_df[c].max()]

                y_cols = 'frequency+modeshapes'
                X, y, _, _ = ppm.select_cols(modeshapes_df, modes, x_cols, y_cols)
                mask = y.notna().all(axis=1)
                y = y[mask]
                X = X.loc[mask]
                return X, y

            X, y = await asyncio.to_thread(
                _process_unv,
                temp_path,
                self.data[sid]["weather_full"],
                self.data[sid]["sample"].columns.tolist(),
            )
            if X.shape[1] == 0:
                await self.emit(
                    "error",
                    "All weather predictors were constant over this UNV file's "
                    "time window (recording session shorter than the weather "
                    "data's resolution) and were dropped - no usable features "
                    "remain. Fetch weather data at a finer resolution or use a "
                    "longer UNV recording.",
                    to=sid,
                )
                return

            self.data[sid]["sample"] = X
            self.data[sid]["qoi"] = y
            await self.emit(
                "qoi", self.data[sid]["qoi"].describe().to_json(), to=sid
            )
            await self.send_modes_and_nodes(sid, self.data[sid]["qoi"])
            await self.emit("labels_loaded", {"filename": filename}, to=sid)
        except Exception as e:
            await self.emit("error", f"Error handling event load_unv: {str(e)}", to=sid)
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    async def on_load_zmean(self, sid, data):
        await self._load_csv_chunk(sid, data, store_key="zmean", loaded_event="zmean_loaded",
                                    data_event="zmean", formatter=lambda df: df.to_dict(),
                                    error_label="Load Z-mean error")

    async def on_load_sigma(self, sid, data):
        await self._load_csv_chunk(sid, data, store_key="sigma", loaded_event="sigma_loaded",
                                    data_event="sigma", formatter=lambda df: df.to_dict(),
                                    error_label="Load Sigma error")

    async def on_load_subtract_input(self, sid, data):
        await self._load_csv_chunk(sid, data, store_key="subtract_input", loaded_event="features_loaded",
                                    data_event="subtract_input", formatter=lambda df: df.to_dict(),
                                    error_label="Load Subtract Input error")

    async def on_load_subtract_output(self, sid, data):
        await self._load_csv_chunk(sid, data, store_key="subtract_output", loaded_event="labels_loaded",
                                    data_event="subtract_output", formatter=lambda df: df.to_dict(),
                                    error_label="Load Subtract Output error")

    async def on_subtract(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            selected_features = data["selected_features"]
            model = self.data[sid]["model"]
            x_train = self.data[sid]["selected_sample"]
            y_train = self.data[sid]["selected_qoi"]
            subtracted = await model.subtract_effects(
                x_train, y_train, selected_features
            )
            self.data[sid]["subtracted"] = subtracted
            await self.emit(
                "subtracted_data",
                {
                    "subtracted_df": subtracted.to_json(orient="records"),
                    "describe_df": subtracted.describe().to_json(),
                },
                to=sid,
            )
        except Exception as e:
            await self.emit("error", str(e), to=sid)
    
    async def on_download_subtracted(self, sid):
        try:
            subtracted = self.data[sid]["subtracted"]
            await self.emit(
                "download_subtracted_data",
                subtracted.to_csv(index=False),
                to=sid,
            )
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    async def on_download_subtracted_describe(self, sid):
        try:
            subtracted = self.data[sid]["subtracted"]
            await self.emit(
                "download_subtracted_describe",
                subtracted.describe().reset_index().to_csv(index=False),
                to=sid,
            )
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    async def on_subtracted_plot_scatter(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            subtracted = self.data[sid]["subtracted"]
            param1 = data["param1"]
            param2 = data["param2"]
            fig = scatter_plot(
                pd.DataFrame(
                    self.data[sid]["selected_sample"],
                    columns=self.data[sid]["model"].Q.variable_names(),
                ),
                self.data[sid]["subtracted"],
                param1,
                param2,
                hue_col=data["hue"] if "hue" in data and data["hue"] != "" else None,
            )
            binary_fig = await self.fig_to_binary(fig)
            await self.emit("subtracted_plot_scatter", binary_fig, to=sid)
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    async def on_threshold_exceed(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            selected_features = data["selected_features"]
            threshold = data.get("threshold", None)
            model = self.data[sid]["model"]
            q = self.data[sid]["sample"]
            QoI = self.data[sid]["selected_qoi"]
            (
                fig,
                alert,
                remained_effects_df,
                error_ratio,
                problematic_rows,
                reference_statistics,
                monitoring_statistics,
            ) = await model.plot_subtract_effects_and_alert(
                q,
                QoI,
                self.data[sid]["subtract_input"],
                self.data[sid]["subtract_output"],
                selected_features,
                threshold_ratio=threshold,
            )
            self.data[sid]["remained_effects"] = remained_effects_df
            self.data[sid]["reference_statistics"] = reference_statistics
            self.data[sid]["monitoring_statistics"] = monitoring_statistics
            binary_data = await self.fig_to_binary(fig)
            await self.emit(
                "subtract_data",
                {
                    "fig": binary_data,
                    "error_ratio": error_ratio,
                    "problematic_rows": problematic_rows.to_dict(orient="records"),
                    "reference_statistics": reference_statistics.reset_index().to_dict(
                        orient="records"
                    ),
                    "monitoring_statistics": monitoring_statistics.reset_index().to_dict(
                        orient="records"
                    ),
                },
                to=sid,
            )
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    async def on_save_subtracted_data(self, sid):
        await self.emit(
            "subtracted_data",
            self.data[sid]["remained_effects"].to_csv(index=False),
            to=sid,
        )

    async def on_save_reference_stats(self, sid):
        await self.emit(
            "reference_stats",
            self.data[sid]["reference_statistics"].to_csv(index=False),
            to=sid
        )

    async def on_save_monitoring_stats(self, sid):
        await self.emit(
            "monitoring_stats",
            self.data[sid]["monitoring_statistics"].to_csv(index=False),
            to=sid
        )

    # --- Core Handlers ---
    async def on_mode(self, sid, mode):
        self.data[sid]["mode"] = mode

    @staticmethod
    @contextlib.contextmanager
    def detached_shap_state(model):
        """SHAP state on the model (and, for DNN, the inner network) isn't picklable
        (KernelExplainer) or loadable under restricted_loads (shap.Explanation), and
        PredictiveModel.__getstate__ only drops the outer `explainer`. Detach `explainer`
        and `shap_values` for the dump and put them back for later SHAP plots."""
        holders = [h for h in (model, getattr(model, "model", None)) if hasattr(h, "__dict__")]
        saved = [(h, {k: h.__dict__.pop(k) for k in ("explainer", "shap_values") if k in h.__dict__})
                 for h in holders]
        try:
            yield
        finally:
            for h, state in saved:
                h.__dict__.update(state)

    async def on_save_model(self, sid):
        try:
            model = self.data[sid]["model"]
            with self.detached_shap_state(model):
                serialized = model.save_model()
            await self.emit("save_model", serialized, to=sid)
        except Exception as e:
            await self.emit("error", f"Error saving model: {str(e)}", to=sid)

    async def on_refresh_variables(self, sid, data):
        try:
            variableset = VariableSet()
            for param in data:
                name = param["name"]
                dist_param1 = float(param["distParam1"])
                dist_param2 = float(param["distParam2"])
                match param["distribution"]:
                    case "normal":
                        dist = NormalDistribution(dist_param1, dist_param2)
                    case "uniform":
                        dist = UniformDistribution(dist_param1, dist_param2)
                    case "logNormal":
                        dist = LogNormalDistribution(dist_param1, dist_param2)
                    case "beta":
                        dist = BetaDistribution(dist_param1, dist_param2)
                    case "exponential":
                        dist = ExponentialDistribution(dist_param1)
                    case _:
                        raise ValueError(f"Unknown distribution type: {param['distribution']}")

                isTranslated = False
                if "optional" in param and param["optional"] is not None:
                    match param["optional"]:
                        case "bounds":
                            if (
                                "minBound" in param
                                and "maxBound" in param
                                and param["minBound"] is not None
                                and param["maxBound"] is not None
                            ):
                                minBound = float(param["minBound"])
                                maxBound = float(param["maxBound"])
                                dist = dist.fix_bounds(minBound, maxBound)
                                isTranslated = type(dist) is TranslatedDistribution
                        case "moments":
                            if (
                                "mean" in param
                                and "var" in param
                                and param["mean"] is not None
                                and param["var"] is not None
                            ):
                                mean = float(param["mean"])
                                var = float(param["var"])
                                dist = dist.fix_moments(mean, var)
                                isTranslated = type(dist) is TranslatedDistribution
                if isTranslated:
                    param["shift"] = dist.get_shift()
                    param["scale"] = dist.get_scale()
                else:
                    param["shift"] = 0
                    param["scale"] = 1
                P = Variable(name, dist)
                variableset.add(P)
            self.data[sid]["variableset"] = variableset
            await self.emit("shift_scale", data, to=sid)
        except Exception as e:
            await self.emit("error", f"Error refreshing variables: {e}", to=sid)

    async def on_fetch_weather_data(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            latitude = data["latitude"]
            longitude = data["longitude"]
            start_date = data["start_date"]
            end_date = data["end_date"]
            features = data["features"]
            data = await asyncio.to_thread(
                openmeteo.get_openmeteo_data,
                latitude, longitude, start_date, end_date, features
            )
            processed = ppm.preprocess_weather_df(data)
            self.data[sid]["weather_full"] = processed
            export_df = processed.copy()
            if "Datetime" in export_df.columns:
                export_df["Datetime"] = export_df["Datetime"].dt.strftime('%Y-%m-%d %H:%M:%S')
            numeric_only = processed.drop(columns=["Datetime"]).astype(float)
            self.data[sid]["sample"] = numeric_only
            self.data[sid]["variableset"] = utils.get_variableset_from_data(numeric_only)
            await self.emit("sample", export_df.values.tolist(), to=sid)
            await self.emit("features_stats", numeric_only.describe().to_json(), to=sid)
            await self.emit("features_loaded", {"filename": "Weather Data"}, to=sid)
            await self.send_variableset(sid)
            await self.emit("weather_done", to=sid)
        except Exception as e:
            await self.emit("error", f"Error fetching weather data: {str(e)}", to=sid)

    async def on_download_weather_csv(self, sid, data=None):
        try:
            if not await self._check_rate_limit(sid): return
            df = self.data.get(sid, {}).get("weather_full")
            if df is None:
                await self.emit("error", "No weather data has been fetched in this session.", to=sid)
                return
            df = df.copy()
            filename = "weather_data.csv"
            if "Datetime" in df.columns:
                start = df["Datetime"].min().strftime('%Y-%m-%d')
                end = df["Datetime"].max().strftime('%Y-%m-%d')
                filename = f"weather_data_{start}_{end}.csv"
                df["Datetime"] = df["Datetime"].dt.strftime('%Y-%m-%d %H:%M:%S')
                df = df[["Datetime"] + [c for c in df.columns if c != "Datetime"]]
            csv_text = await asyncio.to_thread(df.to_csv, index=False)
            await self.emit("weather_csv", {"filename": filename, "csv": csv_text}, to=sid)
        except Exception as e:
            await self.emit("error", f"Error exporting weather data: {str(e)}", to=sid)

    async def on_exploratory_plot(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            df = pd.DataFrame(self.data[sid]["sample"], columns=self.data[sid]["variableset"].variable_names())
            fig = plot_correlation(df, self.data[sid]["qoi"], mode=data.get("mode", "input-output"))
            binary_data = await self.fig_to_binary(fig)
            await self.emit("exploratory_plot", binary_data, to=sid)
        except Exception as e:
            await self.emit("error", f"Error generating correlation plot: {str(e)}", to=sid)

    async def on_exploratory_plot_scatter(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            df = pd.DataFrame(self.data[sid]["sample"], columns=self.data[sid]["variableset"].variable_names())
            fig = scatter_plot(df, self.data[sid]["qoi"], data["param1"], data["param2"],
                              hue_col=data.get("hue") if data.get("hue") else None)
            binary_data = await self.fig_to_binary(fig)
            await self.emit("exploratory_plot_scatter", binary_data, to=sid)
        except Exception as e:
            await self.emit("error", f"Error generating scatter plot: {str(e)}", to=sid)

    # --- Training & Analysis Handlers ---
    async def on_train(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            m_cfg = data["modelConfig"]
            m_type = m_cfg["modelType"]
            if not m_type: return

            if m_type == "MOSAIC":
                s_feats = self.data[sid]["sample"].columns.tolist()
                s_labels = self.data[sid]["qoi"].columns.tolist()
                variableset = self.data[sid]["variableset"]
            else:
                s_feats = data["selectedFeats"]
                s_labels = data["selectedLabels"]
                variableset = utils.get_variableset_from_data(self.data[sid]["sample"][s_feats])

            x_data = self.data[sid]["sample"][s_feats]
            y_data = self.data[sid]["qoi"][s_labels]

            self.data[sid].update({"selected_sample": x_data, "selected_qoi": y_data, "filtered_variableset": variableset})

            model = None
            if m_type == "gPCE":
                p = int(m_cfg["gpcConfig"]["initConfig"]["p"])
                model = gPCE(variableset, s_labels, p=p)
                t_cfg = {}
            elif m_type == "GBT":
                # Unset fields keep the model defaults.
                gbt_train = m_cfg["gbtConfig"]["trainConfig"]
                gbt_args = {}
                if gbt_train.get("maxDepth"):
                    gbt_args["max_depth"] = int(gbt_train["maxDepth"])
                if gbt_train.get("numOfIter"):
                    gbt_args["num_of_iter"] = int(gbt_train["numOfIter"])
                model = GBT(variableset, s_labels, **gbt_args)
                t_cfg = {}
            elif m_type == "DNN":
                init = {
                    "layers": [{
                        "neurons": int(l["numOfNeurons"]), "activation": l["activationFunction"], "dropout": float(l["dropout"])
                    } for l in m_cfg["nnConfig"]["initConfig"]["layers"]],
                    "outputAF": m_cfg["nnConfig"]["initConfig"]["outputAF"]
                }
                model = DNN(variableset, s_labels, **init)
                # Blank UI fields mean "use the model default".
                t_cfg = {k: v for k, v in m_cfg["nnConfig"]["trainConfig"].items() if v not in (None, "")}
                for k in ("epochs", "batch_size"):
                    if k in t_cfg:
                        t_cfg[k] = int(t_cfg[k])
            elif m_type == "LinReg":
                model = LinReg(variableset, s_labels)
                t_cfg = {}
            elif m_type in ("MDN", "CRPS"):
                init = {
                    "layers": [{
                        "neurons": int(l["numOfNeurons"]), "activation": l["activationFunction"], "dropout": float(l["dropout"])
                    } for l in m_cfg["nnConfig"]["initConfig"]["layers"]],
                }
                # digital_twinning's MDN/CRPS size the network as
                # input=len(QoI_names), output=Q.num_variables(), so for a
                # features -> labels model the feature names go in QoI_names and
                # Q describes the labels.
                label_set = utils.get_variableset_from_data(y_data)
                if m_type == "MDN":
                    init["n_components"] = int(m_cfg["mdnConfig"]["initConfig"]["numComponents"])
                    model = MDN(label_set, s_feats, **init)
                else:
                    init["n_epsilon"] = int(m_cfg["crpsConfig"]["trainConfig"]["numSamplers"])
                    model = CRPS(label_set, s_feats, **init)
                nn_train = m_cfg["nnConfig"]["trainConfig"]
                t_cfg = {}
                if nn_train.get("epochs") not in (None, ""):
                    t_cfg["max_epoch"] = int(nn_train["epochs"])
                if nn_train.get("batch_size") not in (None, ""):
                    t_cfg["batch_size"] = int(nn_train["batch_size"])
                if nn_train.get("optimizer"):
                    t_cfg["optimizer"] = nn_train["optimizer"]
            elif m_type == "MOSAIC":
                svc_cfg = m_cfg["mosaicConfig"]["svcConfig"]
                model = MOSAIC(
                    variableset, s_labels,
                    resolution=float(m_cfg["mosaicConfig"]["resolution"]),
                    max_freq_degree=int(m_cfg["mosaicConfig"]["maxDoaFrequencies"]),
                    max_vect_degree=int(m_cfg["mosaicConfig"]["maxDoaEigenvectors"]),
                    C=float(svc_cfg["C"]), kernel=svc_cfg["kernel"],
                    degree=int(svc_cfg["degree"]), gamma=svc_cfg["gamma"],
                )
                t_cfg = {}

            if model:
                x_t, x_v, y_t, y_v = model.train_test_split(
                    x_data, y_data,
                    train_test_ratio=data["splitConfig"]["trainTestRatio"],
                    random_seed=data["splitConfig"]["seed"],
                    split_type=data["splitConfig"]["trainTestSplit"]
                )
                await asyncio.to_thread(functools.partial(model.train, x_t, y_t, **t_cfg))
                # digital_twinning's MDN/CRPS don't implement evaluate_model yet.
                if hasattr(model, "evaluate_model"):
                    ind_m, over_m = await asyncio.to_thread(model.evaluate_model, y_t, x_v, y_v)
                    ind_m = ind_m.to_dict()
                else:
                    ind_m, over_m = {}, {}
                self.data[sid]["model"] = model
                self.data[sid]["train_val_split"] = {
                    "x_train": x_t, "x_val": x_v, "y_train": y_t, "y_val": y_v,
                }
                await self.emit("outputQoi", y_t.columns.tolist(), to=sid)
                await self.emit("train_result", "Done", to=sid)
                await self.emit("train_metrics", {"individual": ind_m, "overall": over_m}, to=sid)
                if m_type == "MOSAIC":
                    subdomains = await asyncio.to_thread(model.get_number_of_subdomains)
                    await self.emit("mosaic_subdomains", np.asarray(subdomains).astype(int).tolist(), to=sid)
                    await self.send_modal_validation(sid, model, x_v, y_v)
        except Exception as e:
            logging.error(f"Training error: {e}")
            await self.emit("train_result", f"Error: {e}", to=sid)

    async def on_mosaic_variable_space_exploration(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            model = self.data[sid]["model"]
            mode = int(data["mode"])
            # Order is (eigenvectors, space division, correlation); the last two are
            # None when the mode has a single subdomain.
            fig_eigvecs, fig_space, fig_corr = await asyncio.to_thread(
                model.plot_variable_space_exploration, mode
            )
            for event, fig in (
                ("mosaic_space_division_plot", fig_space),
                ("mosaic_reference_eigenvectors_plot", fig_eigvecs),
                ("mosaic_reference_correlation_plot", fig_corr),
            ):
                if fig is not None:
                    await self.emit(event, await self.fig_to_binary(fig), to=sid)
        except Exception as e:
            await self.emit("error", f"Error generating variable space exploration plots: {e}", to=sid)

    async def on_predict(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            m = self.data[sid]["model"]
            pdf = pd.DataFrame(np.array(data, ndmin=2), columns=m.Q.variable_names())
            await self.emit("predict", m.predict(pdf).tolist(), to=sid)
        except Exception as e:
            await self.emit("error", f"Prediction error: {e}", to=sid)

    async def on_load_eval_set(self, sid, data):
        """Optional held-out evaluation set for the Predicted-vs-Feature plot: a
        single CSV holding both feature and QoI columns (the Granada workflow's
        'future period' set). Split into features/labels at plot time against the
        trained model's known column names."""
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            df = await asyncio.to_thread(pd.read_csv, io.BytesIO(complete))
            self.data[sid]["eval_set"] = df
            await self.emit("eval_set_loaded", {"filename": name, "rows": len(df)}, to=sid)
        except Exception as e:
            await self.emit("error", f"Load evaluation set error: {e}", to=sid)

    async def on_predicted_vs_feature(self, sid, data):
        # The plot needs predictive draws per input row; MDN/CRPS.inference only returns
        # draws for the first row.
        await self.emit(
            "error",
            "The Predicted vs. Feature plot isn't available yet: digital_twinning's MDN/CRPS "
            "models can't draw predictive samples for each input row.",
            to=sid,
        )

    async def on_mean_var(self, sid):
        try:
            if not await self._check_rate_limit(sid): return
            model = self.data[sid]["model"]
            mean, variance = await asyncio.to_thread(model.get_mean_and_var)
            logging.debug(f"mean={mean}, variance={variance}")
            await self.emit(
                "mean_var", {"mean": mean.tolist(), "variance": variance.tolist()}, to=sid
            )
        except Exception as e:
            logging.error(f"Error computing mean and variance: {str(e)}")
            await self.emit(
                "error", f"Error computing mean and variance: {str(e)}", to=sid
            )
    
    def _shap_data(self, sid):
        """Held-out features for SHAP, so explanations aren't computed on training
        data. Models loaded from file have no stored split and use all samples."""
        split = self.data[sid].get("train_val_split")
        return pd.DataFrame(split["x_val"] if split else self.data[sid]["selected_sample"])

    async def on_shap_beeswarm(self, sid, param_name):
        try:
            if not await self._check_rate_limit(sid): return
            model = self.data[sid]["model"]
            X_test = self._shap_data(sid)
            fig = await model.plot_shap_beeswarm(X_test=X_test, param_name=param_name, silent=True)
            binary_data = await self.fig_to_binary(fig)
            await self.emit("beeswarm_plot", binary_data, to=sid)
        except Exception as e:
            await self.emit(
                "error", f"Error generating beeswarm plot: {str(e)}", to=sid
            )

    async def on_waterfall_multi(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            model = self.data[sid]["model"]
            values = data
            fig = await model.plot_shap_multiple_waterfalls(X_test=self._shap_data(sid), q=values, silent=True)
            binary_data = await self.fig_to_binary(fig)
            await self.emit("shap_plot_multi", binary_data, to=sid)
        except Exception as e:
            logging.error(f"Error generating multiple waterfall plot: {e}")
            await self.emit(
                "error", f"Error generating multiple waterfall plot: {str(e)}", to=sid
            )

    async def on_waterfall_single(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            model = self.data[sid]["model"]
            qoi = data["qoi"]
            values = data["values"]
            fig = await model.plot_shap_single_waterfall(
                X_test=self._shap_data(sid), q=values, param_name=qoi, silent=True
            )
            binary_data = await self.fig_to_binary(fig)
            await self.emit("shap_plot_single", binary_data, to=sid)
        except Exception as e:
            logging.error(f"Error generating single waterfall plot: {e}")
            await self.emit(
                "error", f"Error generating single waterfall plot: {str(e)}", to=sid
            )

    async def on_sobol(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            m = self.data[sid]["model"]
            p_var, s_idx = await asyncio.to_thread(m.get_sobol_sensitivity, data)
            print(f"Partial Variance:\n{p_var}\nSobol Index:\n{s_idx}")
            self.data[sid].update({"partial_var_df": p_var, "sobol_index_df": s_idx})
            fig = await asyncio.to_thread(m.plot_sobol_sensitivity, self.data[sid]["selected_qoi"], max_index=data)
            await self.emit("sobol", {"partialVariance": p_var.to_dict(), "sobolIndex": s_idx.to_dict()}, to=sid)
            binary_data = await self.fig_to_binary(fig)
            await self.emit("sobol_plot", binary_data, to=sid)
        except Exception as e:
            await self.emit("error", f"Sobol error: {e}", to=sid)

    async def on_sobol_single(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            model = self.data[sid]["model"]
            qoi = data
            if "partial_var_df" not in self.data[sid]:
                p_var, s_idx = await asyncio.to_thread(model.get_sobol_sensitivity)
                self.data[sid].update({"partial_var_df": p_var, "sobol_index_df": s_idx})
            partial_var_df = self.data[sid]["partial_var_df"]
            sobol_index_df = self.data[sid]["sobol_index_df"]
            fig = await asyncio.to_thread(model.plot_sobol_sensitivity, self.data[sid]["selected_qoi"], param_name=qoi)
            binary_data = await self.fig_to_binary(fig)
            await self.emit(
                "sobol",
                {
                    "partialVariance": partial_var_df.to_dict(),
                    "sobolIndex": sobol_index_df.to_dict(),
                },
                to=sid,
            )
            await self.emit("sobol_plot_single", binary_data, to=sid)
        except Exception as e:
            logging.error(f"Error computing single Sobol index: {e}")
            await self.emit(
                "error", f"Error computing single Sobol index: {str(e)}", to=sid
            )

    async def on_shap(self, sid):
        try:
            if not await self._check_rate_limit(sid): return
            m = self.data[sid]["model"]
            df = self._shap_data(sid)
            vals = await m.get_shap_values(df, mean=True)
            await self.emit("shap", vals.values.T.tolist(), to=sid)
        except Exception as e:
            await self.emit("error", f"SHAP error: {e}", to=sid)

    async def on_name_pairs(self, sid, data):
        tuple_list = [tuple(item) for item in data]
        self.data[sid]["name_pairs"] = tuple_list

    async def on_update(self, sid, data):
        if not await self._check_rate_limit(sid): return
        nwalkers = data["nwalkers"]
        nburn = data["nburn"]
        niter = data["niter"]
        try:
            sigma_flat = self.data[sid]["sigma"].values.flatten()
            E = generate_stndrn_variable_set(sigma_flat)
            dt = DigitalTwin(self.data[sid]["model"], E)
            untrack = self._track_mcmc_progress(sid, dt, nwalkers, nburn, niter)
            try:
                await asyncio.to_thread(
                    functools.partial(dt.update, self.data[sid]["zmean"], nwalkers, nburn, niter)
                )
            finally:
                untrack()
            # get_MAP/plot_MCMC evaluate the model many times, so keep them off the event loop.
            map = await asyncio.to_thread(dt.get_MAP)
            fig_mcmc = await asyncio.to_thread(dt.plot_MCMC, self.data[sid]["sample"], map=True)
            means_df, variances_df = await asyncio.to_thread(dt.get_mean_and_var_of_posterior)
            self.data[sid]["dt"] = dt
            await self.emit(
                "update",
                {
                    "mcmc": await self.fig_to_binary(fig_mcmc),
                    "mean": means_df.to_dict(),
                    "variance": variances_df.to_dict(),
                    "map": map.to_dict(),
                },
                to=sid,
            )
            # The animation reads the prior by column position.
            sample = self.data[sid]["sample"]
            names = dt.model.Q.variable_names()
            prior = sample[names] if set(names).issubset(sample.columns) else sample
            await self.send_mcmc_animation(
                sid, lambda path: dt.animate_MCMC(prior, filename=path, map=True)
            )
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    async def on_get_posterior_samples(self, sid):
        try:
            dt = self.data[sid]["dt"]
            post_samples_df = await asyncio.to_thread(dt.get_posterior_samples)
            await self.emit("posterior_samples", post_samples_df.to_csv(index=False), to=sid)
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    async def on_get_posterior_statistics(self, sid):
        try:
            dt = self.data[sid]["dt"]
            means_df, variances_df = await asyncio.to_thread(dt.get_mean_and_var_of_posterior)
            map_df = await asyncio.to_thread(dt.get_MAP)
            stats_df = pd.concat([means_df, variances_df, map_df], ignore_index=True)
            stats_df.insert(0, "statistic", ["mean", "variance", "map"])
            await self.emit("posterior_statistics", stats_df.to_csv(index=False), to=sid)
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    # --- Multi-Model Handlers ---
    async def on_add_model(self, sid, data):
        try:
            retrieved_file, name = await self.recieve_chunks(sid, data)
            if retrieved_file is not None:
                model = await asyncio.to_thread(restricted_loads, retrieved_file)
                if "models" not in self.data[sid]:
                    self.data[sid]["models"] = {}
                self.data[sid]["models"][name] = {"model": model}
                await self.emit("models", self.format_models(self.data[sid]["models"]), to=sid)
        except Exception as e:
            logging.error(f"Error adding model: {e}")
            await self.emit("error", f"Error adding model: {str(e)}", to=sid)

    async def on_load_zmean_multi(self, sid, data):
        try:
            name = data["name"]
            model_name = data["model_name"]
            csv_text = data["data"]
            self.data[sid]["models"][model_name]["zmean"] = pd.read_csv(io.StringIO(csv_text))
            await self.send_multi_measurements(sid)
            await self.emit("zmean_loaded", {"filename": name}, to=sid)
        except Exception as e:
            await self.emit(
                "error", f"Error handling event load_zmean_multi: {str(e)}", to=sid
            )

    async def on_load_sigma_multi(self, sid, data):
        try:
            name = data["name"]
            model_name = data["model_name"]
            csv_text = data["data"]
            self.data[sid]["models"][model_name]["sigma"] = pd.read_csv(io.StringIO(csv_text))
            await self.send_multi_measurements(sid)
            await self.emit("sigma_loaded", {"filename": name}, to=sid)
        except Exception as e:
            await self.emit(
                "error", f"Error handling event load_sigma_multi: {str(e)}", to=sid
            )

    async def on_create_joint(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            models = [obj["model"] for obj in self.data[sid]["models"].values()]
            self.data[sid]["joint_manager"] = JointManager(models, data)
            await self.emit("joint_created", to=sid)
        except Exception as e:
            logging.error(f"Error creating joint manager: {e}")
            await self.emit("error", f"Error creating joint manager: {e}", to=sid)

    async def on_get_multi_data(self, sid, data):
        if not await self._check_rate_limit(sid): return
        index = data["index"]
        try:
            joint_manager = self.data[sid]["joint_manager"]
            if joint_manager is not None:
                # MAP computation evaluates the models many times; keep it off the event loop.
                map, means_df, variances_df, posterior_samples = await asyncio.to_thread(
                    joint_manager.get_data_of_model, index
                )
                self.data[sid]["posterior_samples"] = posterior_samples
                model_names = list(self.data[sid]["models"].keys())
                figs = await asyncio.to_thread(
                    functools.partial(joint_manager.plot_multimodel_MCMC, model_names=model_names)
                )
                binary_figs = [await self.fig_to_binary(fig) for fig in figs]
                await self.emit(
                    "update",
                    {
                        "mcmc": binary_figs[index],
                        "mean": means_df.to_dict(),
                        "variance": variances_df.to_dict(),
                        "map": map.to_dict(),
                    },
                    to=sid,
                )
                await self.emit("update_multi", binary_figs, to=sid)
                await self.send_mcmc_animation(
                    sid, functools.partial(self._render_joint_animation, joint_manager, index)
                )
            else:
                await self.emit("error", "Joint manager not found", to=sid)
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    async def on_update_multi(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            means = [obj["zmean"] for obj in self.data[sid]["models"].values()]
            sigmas = [obj["sigma"] for obj in self.data[sid]["models"].values()]
            joint_manager = self.data[sid]["joint_manager"]
            untrack = self._track_mcmc_progress(
                sid, joint_manager, data["nwalkers"], data["nburn"], data["niter"]
            )
            try:
                await asyncio.to_thread(
                    functools.partial(joint_manager.update, means, sigmas, **data)
                )
            finally:
                untrack()
            await self.emit("update_done", to=sid)
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    # --- Climate Resilience Handlers ---
    _CLIMATE_VARIABLE_LABELS = {
        "tasmax": "Maximum Temperature [°C]",
        "tasmin": "Minimum Temperature [°C]",
        "pr": "Precipitation [mm]",
        "sfcWind": "Wind Speed [ms⁻¹]",
    }
    _CLIMATE_OUTPUT_LABELS = {
        "FC": "Factor of Change of Characteristic value",
        "Charact": "Characteristic Value",
        "Mean": "Mean Value",
        "Cov": "Coefficient of Variation",
    }

    async def _generate_climate_report_bytes(self, sid, data):
        report = self.data[sid].get("climate_report")
        if not report:
            raise ValueError("Run the climate analysis before saving a report.")

        location = self.data[sid].get("location_data", {})

        styles = getSampleStyleSheet()
        elements = [
            Paragraph("Climate Exposure Report", styles["Title"]),
            Spacer(1, 12),
            Paragraph(f"Building: {data.get('building_name', '')}", styles["Normal"]),
            Paragraph(f"Address: {data.get('address', '')}", styles["Normal"]),
            Paragraph(f"Author: {data.get('author', '')}", styles["Normal"]),
            Paragraph(f"Owner: {data.get('owner', '')}", styles["Normal"]),
            Paragraph(f"Location: {location.get('city', '')}, {location.get('country', '')}", styles["Normal"]),
            Paragraph(
                "Indicator: {} — {}".format(
                    self._CLIMATE_OUTPUT_LABELS.get(report["output"], report["output"]),
                    self._CLIMATE_VARIABLE_LABELS.get(report["variable"], report["variable"]),
                ),
                styles["Normal"],
            ),
            Spacer(1, 16),
        ]

        chart_png = await self.fig_to_binary(report["figure"])
        elements.append(RLImage(io.BytesIO(chart_png), width=460, height=290))
        elements.append(Spacer(1, 16))

        table_df = report["table"]
        table_rows = [["Model"] + table_df.columns.tolist()]
        table_rows += [[str(idx)] + [f"{val:.3f}" for val in row.values] for idx, row in table_df.iterrows()]
        pdf_table = RLTable(table_rows, hAlign="LEFT")
        pdf_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONTSIZE", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(pdf_table)

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        doc.build(elements)
        buf.seek(0)
        return buf.read()

    async def on_get_climate_report_pdf(self, sid, data):
        try:
            pdf_bytes = await self._generate_climate_report_bytes(sid, data)
            pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
            await self.emit("climate_report_pdf", {"filename": "Climate_Exposure_Report.pdf", "file": pdf_base64}, to=sid)
        except Exception as e:
            error_line = f"{e.__class__.__name__} on line {sys.exc_info()[-1].tb_lineno}: {e}"
            print(error_line)
            await self.emit("error", error_line, to=sid)

    async def on_validate_location_climate(self, sid, data):
        longitude = data.get("longitude")
        latitude = data.get("latitude")
        try:
            city, country = cr.coordinate_check(latitude, longitude)
            self.data[sid]["location_data"] = {
                "city": city,
                "country": country,
            }
            plotly = bimquake.get_map(latitude, longitude, city, country)
            await self.emit("plotly_map", plotly._repr_html_(), to=sid)
            await self.emit(
                "location_data",
                {
                    "module": "climate",
                    "city": self.data[sid]["location_data"]["city"],
                    "country": self.data[sid]["location_data"]["country"],
                },
                to=sid,
            )
        except Exception as e:
            print(f"An error occurred: {e}")
            await self.emit("error", str(e), to=sid)

    async def on_select_climate_data(self, sid, data):
        _BDATA_STRUCT = {'f8': ('d', 8), 'f4': ('f', 4), 'i4': ('i', 4), 'u4': ('I', 4), 'i2': ('h', 2), 'u2': ('H', 2)}

        def _decode_bdata(obj):
            """Recursively decode plotly 6.x binary-encoded arrays to plain Python lists.
            Plotly 6.x stores numpy arrays as {'dtype': 'f8', 'bdata': '<base64>'};
            Plotly.js 2.x cannot parse this format so we decode to plain lists."""
            if isinstance(obj, dict):
                if 'bdata' in obj and 'dtype' in obj and obj['dtype'] in _BDATA_STRUCT:
                    fmt, size = _BDATA_STRUCT[obj['dtype']]
                    raw = base64.b64decode(obj['bdata'])
                    return list(struct.unpack(f'{len(raw)//size}{fmt}', raw))
                return {k: _decode_bdata(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_decode_bdata(x) for x in obj]
            return obj
        def _fig_to_json(fig):
            """Serialize a Plotly figure to JSON with plain numeric arrays (Plotly.js 2.x/3.x compatible)."""
            return json.dumps(_decode_bdata(fig.to_dict()))
        try:
            lat = data.get("latitude", 43.7696)
            lon = data.get("longitude", 11.2558)
            scenario = data.get("experiment", "historical")
            variable = data.get("variable", "tasmin")
            value = data.get("value", "Mean")
            models = data.get("models", [])
            figure, table = cp.get_figure_and_table(lat, lon, scenario, variable, value, models)
            figure_json = _fig_to_json(figure)
            await self.emit("climate_selection_result", figure_json, to=sid)
            if table is not None:
                table_data = {
                    "columns": ["Model"] + table.columns.tolist(),
                    "rows": [[str(idx)] + [round(float(val), 3) for val in row.values] for idx, row in table.iterrows()]
                }
                await self.emit("climate_table_result", table_data, to=sid)
        except KeyError as e:
            print(f"KeyError: {e}")
            await self.emit("error", "No climate data available", to=sid)

    async def on_process_climate_data(self, sid, data):
        try:
            lat = data.get("lat")
            lon = data.get("lon")
            experiment = data.get("experiment")
            variable = data.get("variable")
            output = data.get("value", "Mean")
            models = data.get("models", [])

            figure, table = cp.get_figure_and_table(lat, lon, experiment, variable, output, models)
            if figure is None or table is None:
                await self.emit("error", "No climate data available for the selected parameters.", to=sid)
                return

            self.data[sid]["climate_report"] = {
                "figure": figure,
                "table": table,
                "experiment": experiment,
                "variable": variable,
                "output": output,
            }
            await self.emit("processed_climate_data", to=sid)
        except Exception as e:
            error_line = f"{e.__class__.__name__} on line {sys.exc_info()[-1].tb_lineno}: {e}"
            print(error_line)
            await self.emit("error", error_line, to=sid)

    # --- Demo Handlers ---
    async def on_data_driven_demo(self, sid):
        try:
            d_path = os.path.join(BASE_DIR, "demo/data/sine_data")
            with open(os.path.join(d_path, "model.ddpm"), "rb") as f:
                m = pickle.load(f)
            self.ensure_dataframes(m)
            self.data[sid].update({
                "model": m, "variableset": m.Q, "qoi": m.QoI, "selected_qoi": m.QoI,
                "sample": m.samples, "selected_sample": m.samples,
                "zmean": pd.read_csv(os.path.join(d_path, "example_z_m_df.csv")),
                "sigma": pd.read_csv(os.path.join(d_path, "example_sigma_df.csv")),
                "subtract_input": pd.read_csv(os.path.join(d_path, "example_x_df.csv")),
                "subtract_output": pd.read_csv(os.path.join(d_path, "example_y_df.csv"))
            })
            await self.send_model(sid)
            await self.emit("outputQoi", m.QoI.columns.tolist(), to=sid)
            await self.emit("zmean", self.data[sid]["zmean"].to_dict(), to=sid)
            await self.emit("sigma", self.data[sid]["sigma"].to_dict(), to=sid)
            await self.emit("subtract_input", self.data[sid]["subtract_input"].to_dict(), to=sid)
            await self.emit("subtract_output", self.data[sid]["subtract_output"].to_dict(), to=sid)
            await self.emit("demo_done", to=sid)
        except Exception as e:
            await self.emit("error", f"Demo error: {e}", to=sid)

    async def on_hybrid_demo(self, sid):
        try:
            d_path = os.path.join(BASE_DIR, "demo/data/spring_data")
            with open(os.path.join(d_path, "spring1.ddpm"), "rb") as f:
                m = pickle.load(f)
            self.data[sid].update({
                "model": m, "variableset": m.Q, "qoi": m.QoI, "selected_qoi": m.QoI,
                "sample": m.samples, "selected_sample": m.samples,
                "zmean": pd.read_csv(os.path.join(d_path, "z_spring1_df.csv")),
                "sigma": pd.read_csv(os.path.join(d_path, "sigma_spring1.csv"))
            })
            await self.send_model(sid)
            await self.emit("zmean", self.data[sid]["zmean"].to_dict(), to=sid)
            await self.emit("sigma", self.data[sid]["sigma"].to_dict(), to=sid)
            await self.emit("demo_done", to=sid)
        except Exception as e:
            await self.emit("error", f"Hybrid Demo error: {e}", to=sid)

    async def on_multi_model_demo(self, sid):
        try:
            model1_path = os.path.abspath(
                os.path.join(BASE_DIR, "demo/data/spring_data/Spring1_model.sm")
            )
            model2_path = os.path.abspath(
                os.path.join(BASE_DIR, "demo/data/spring_data/Spring2_model.sm")
            )

            zm1_path = os.path.abspath(
                os.path.join(BASE_DIR, "demo/data/spring_data/z_spring1_df.csv")
            )
            zm2_path = os.path.abspath(
                os.path.join(BASE_DIR, "demo/data/spring_data/z_spring2_df.csv")
            )
            sigma1_path = os.path.abspath(
                os.path.join(BASE_DIR, "demo/data/spring_data/sigma_spring1.csv")
            )
            sigma2_path = os.path.abspath(
                os.path.join(BASE_DIR, "demo/data/spring_data/sigma_spring2.csv")
            )

            join = {"joint_m1_m2": ["m1", "m2"], "joint_k1_k2": ["k1", "k2"]}

            with open(model1_path, "rb") as f:
                model1 = pickle.load(f)
            with open(model2_path, "rb") as f:
                model2 = pickle.load(f)
            self.data[sid]["models"] = {
                "model1": {"model": model1},
                "model2": {"model": model2},
            }
            await self.emit(
                "models", self.format_models(self.data[sid]["models"]), to=sid
            )

            self.data[sid]["joint_manager"] = JointManager([model1, model2], join)
            await self.emit("joint_created", {"connections": join}, to=sid)
            zm1_df = pd.read_csv(zm1_path)
            zm2_df = pd.read_csv(zm2_path)
            self.data[sid]["models"]["model1"]["zmean"] = zm1_df
            self.data[sid]["models"]["model2"]["zmean"] = zm2_df
            sigma1_df = pd.read_csv(sigma1_path)
            sigma2_df = pd.read_csv(sigma2_path)
            self.data[sid]["models"]["model1"]["sigma"] = sigma1_df
            self.data[sid]["models"]["model2"]["sigma"] = sigma2_df
            await self.send_multi_measurements(sid)
            await self.emit("demo_done", to=sid)
        except Exception as e:
            logging.error(f"Error running multi-model demo: {e}")
            await self.emit("error", str(e), to=sid)

    async def on_mosaic_demo(self, sid):
        try:
            # Toy model from demo/data/mosaic/MOSAIC_toy_model_2_variables.ipynb.
            d_path = os.path.join(BASE_DIR, "demo/data/mosaic")
            x_df = pd.read_csv(os.path.join(d_path, "mosaic_toy_2_x_df.csv"))
            y_df = pd.read_csv(os.path.join(d_path, "mosaic_toy_2_y_df.csv"))

            # Use the pre-trained model instead of running the training loop.
            with open(os.path.join(d_path, "model.msic"), "rb") as f:
                model = await asyncio.to_thread(restricted_loads, f.read())
            variableset = model.Q
            x_t, x_v, y_t, y_v = model.train_test_split(
                x_df, y_df, train_test_ratio=0.8, random_seed=1997, split_type="shuffle"
            )
            ind_m, over_m = await asyncio.to_thread(model.evaluate_model, y_t, x_v, y_v)

            self.data[sid].update({
                "model": model, "variableset": variableset,
                "sample": x_df, "qoi": y_df,
                "selected_sample": x_t, "selected_qoi": y_t,
                "train_val_split": {"x_train": x_t, "x_val": x_v, "y_train": y_t, "y_val": y_v},
                "zmean": pd.read_csv(os.path.join(d_path, "mosaic_toy_2_z_m_df.csv")),
                "sigma": pd.read_csv(os.path.join(d_path, "mosaic_toy_2_sigma.csv")),
            })

            await self.send_model(sid)
            await self.emit("sample", x_df.to_numpy().tolist(), to=sid)
            await self.emit("qoi", y_df.describe().to_json(), to=sid)
            await self.send_modes_and_nodes(sid, y_df)
            await self.emit("features_stats", x_df.describe().to_json(), to=sid)
            await self.emit("outputQoi", y_t.columns.tolist(), to=sid)
            await self.emit("train_metrics", {"individual": ind_m.to_dict(), "overall": over_m}, to=sid)
            await self.send_modal_validation(sid, model, x_v, y_v)
            await self.emit("zmean", self.data[sid]["zmean"].to_dict(), to=sid)
            await self.emit("sigma", self.data[sid]["sigma"].to_dict(), to=sid)
            await self.emit("demo_done", to=sid)
        except Exception as e:
            logging.error(f"MOSAIC Demo error: {e}")
            await self.emit("error", f"MOSAIC Demo error: {e}", to=sid)

