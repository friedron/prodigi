import asyncio
import io
import json
import logging
import os
import pickle
import tempfile
import time
import uuid
import functools
import pandas as pd
import numpy as np
import socketio
import tornado
from tornado.ioloop import PeriodicCallback

# Science & Engineering imports
import plotly.io as pio

# Installed packages
from digital_twinning import PredictiveModel, DigitalTwin, JointManager, utils
from digital_twinning.unv_example_functions import preprocess_modeshape_data as ppm
from digital_twinning.utils.object_utils import generate_stdrn_simparamset
from uncertain_variables.variable_set import VariableSet
from uncertain_variables.variable import Variable
from uncertain_variables.distributions import NormalDistribution, UniformDistribution, LogNormalDistribution, BetaDistribution, ExponentialDistribution, TranslatedDistribution


# Local library imports
from utils.preprocess_modeshape_data import (
    plot_correlation,
    scatter_plot,
)
import utils.get_openmeteo_data as openmeteo
from utils.probabilistic_models import MDNPredictiveModel, CRPSPredictiveModel
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

    def get_or_create_session_id(self, environ):
        cookies = environ.get("HTTP_COOKIE", "")
        if cookies:
            cookie_dict = dict(c.split("=", 1) for c in cookies.split("; ") if "=" in c)
            encrypted_id = cookie_dict.get("session_id")
            if encrypted_id:
                try:
                    decoded = tornado.web.decode_signed_value(
                        secret=self.application.settings["cookie_secret"],
                        name="session_id",
                        value=encrypted_id,
                        max_age_days=3,
                    )
                    if decoded:
                        return decoded.decode()
                except Exception as e:
                    logging.error(f"Session decoding error: {e}")
        return str(uuid.uuid4())

    async def on_connect(self, sid, environ, auth=None):
        logging.info(f"Client connected: {sid}")
        self.data[sid] = {}
        self.last_activity[sid] = time.time()
        session_id = self.get_or_create_session_id(environ)
        await self.restore_client_data(sid, session_id)
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
        if d.get("zmean"): await self.emit("zmean", d["zmean"].to_dict(), to=sid)
        if d.get("sigma"): await self.emit("sigma", d["sigma"].to_dict(), to=sid)
        if d.get("subtract_input"): await self.emit("subtract_input", d["subtract_input"].to_dict(), to=sid)
        if d.get("subtract_output"): await self.emit("subtract_output", d["subtract_output"].to_dict(), to=sid)
        
        if d.get("models"):
            await self.emit("models", self.format_models(d["models"]), to=sid)
            await self.send_multi_measurements(sid)
            if d.get("joint_manager"): await self.emit("joint_created", to=sid)
        
        if d.get("building_data"): await self.emit("building_data", json.dumps(d["building_data"]), to=sid)
        if d.get("climate_fig"): await self.emit("climate_fig", d["climate_fig"], to=sid)
        if d.get("sample") is not None: await self.emit("sample", d["sample"].tolist(), to=sid)
        if d.get("qoi") is not None: await self.emit("qoi", d["qoi"].describe().to_json(), to=sid)
        
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

    def fig_to_binary(self, fig):
        buf = io.BytesIO()
        if hasattr(fig, 'savefig'):
            fig.savefig(buf, format="png")
        else: # Handle plotly or other types if needed
            pio.write_image(fig, buf, format="png")
        buf.seek(0)
        return buf.read()

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
        cfg = {"modelType": model.method}
        key_map = {"gPCE": "gpcConfig", "GBT": "gbtConfig", "DNN": "nnConfig"}
        if model.method in key_map:
            cfg[key_map[model.method]] = {
                "trainConfig": model.train_config,
                "initConfig": model.init_config
            }
        return cfg

    def format_models(self, models):
        return {name: obj["model"].Q.variable_names() for name, obj in models.items()}

    # --- Data Emitters ---
    async def send_model(self, sid):
        m = self.data[sid]["model"]
        await self.emit("sample", m.samples.to_numpy().tolist(), to=sid)
        await self.emit("train_result", "Done", to=sid)
        await self.emit("load_model", {
            "variables": self.format_variables(m.Q.variables),
            "modelConfig": self.format_model_config(m)
        }, to=sid)
        await self.emit("qoi", m.QoI.describe().to_json(), to=sid)
        await self.emit("features_stats", m.samples.describe().to_json(), to=sid)

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

    async def on_load_model(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            
            model = await asyncio.to_thread(restricted_loads, complete)
            self.data[sid].update({
                "model": model, "variableset": model.Q,
                "qoi": model.QoI, "sample": model.samples
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

    async def on_qoi_unv(self, sid, data):
        if "weather_full" not in self.data[sid]:
            await self.emit("error", "Please load weather data first", to=sid)
            return
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".unv")
            retrieved_file, filename, = await self.recieve_chunks(sid, data)
            if retrieved_file is not None:
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
                await self.emit("labels_loaded", {"filename": filename}, to=sid)
        except Exception as e:
            await self.emit("error", f"Error handling event load_unv: {str(e)}", to=sid)
        finally:
            if os.path.exists(temp_path):
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
            binary_fig = await asyncio.to_thread(self.fig_to_binary, fig)
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
            binary_data = await asyncio.to_thread(self.fig_to_binary, fig)
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

    async def on_save_model(self, sid):
        try:
            model = self.data[sid]["model"]
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
            data = openmeteo.get_openmeteo_data(
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
        except Exception as e:
            await self.emit("error", f"Error fetching weather data: {str(e)}", to=sid)

    async def on_exploratory_plot(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            df = pd.DataFrame(self.data[sid]["sample"], columns=self.data[sid]["variableset"].variable_names())
            fig = plot_correlation(df, self.data[sid]["qoi"], mode=data.get("mode", "input-output"))
            binary_data = await asyncio.to_thread(self.fig_to_binary, fig)
            await self.emit("exploratory_plot", binary_data, to=sid)
        except Exception as e:
            await self.emit("error", f"Error generating correlation plot: {str(e)}", to=sid)

    async def on_exploratory_plot_scatter(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            df = pd.DataFrame(self.data[sid]["sample"], columns=self.data[sid]["variableset"].variable_names())
            fig = scatter_plot(df, self.data[sid]["qoi"], data["param1"], data["param2"],
                              hue_col=data.get("hue") if data.get("hue") else None)
            binary_data = await asyncio.to_thread(self.fig_to_binary, fig)
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
            
            s_feats = data["selectedFeats"]
            s_labels = data["selectedLabels"]
            
            x_data = self.data[sid]["sample"][s_feats]
            y_data = self.data[sid]["qoi"][s_labels]
            
            variableset = utils.get_variableset_from_data(x_data)
            self.data[sid].update({"selected_sample": x_data, "selected_qoi": y_data, "filtered_variableset": variableset})

            model = None
            if m_type == "gPCE":
                p = int(m_cfg["gpcConfig"]["initConfig"]["p"])
                model = PredictiveModel(variableset, s_labels, m_type, p=p)
                t_cfg = m_cfg["gpcConfig"]["trainConfig"]
            elif m_type == "GBT":
                model = PredictiveModel(variableset, s_labels, m_type, **m_cfg["gbtConfig"]["initConfig"])
                t_cfg = m_cfg["gbtConfig"]["trainConfig"]
            elif m_type == "DNN":
                init = {
                    "layers": [{
                        "neurons": int(l["numOfNeurons"]), "activation": l["activationFunction"], "dropout": float(l["dropout"])
                    } for l in m_cfg["nnConfig"]["initConfig"]["layers"]],
                    "outputAF": m_cfg["nnConfig"]["initConfig"]["outputAF"]
                }
                model = PredictiveModel(variableset, s_labels, m_type, **init)
                t_cfg = m_cfg["nnConfig"]["trainConfig"]
            elif m_type == "LinReg":
                model = PredictiveModel(variableset, s_labels, m_type)
                t_cfg = {}
            elif m_type in ("MDN", "CRPS"):
                init = {
                    "layers": [{
                        "neurons": int(l["numOfNeurons"]), "activation": l["activationFunction"], "dropout": float(l["dropout"])
                    } for l in m_cfg["nnConfig"]["initConfig"]["layers"]],
                }
                if m_type == "MDN":
                    init["numComponents"] = int(m_cfg["mdnConfig"]["initConfig"]["numComponents"])
                    model = MDNPredictiveModel(variableset, s_labels, m_type, **init)
                else:
                    init["numSamplers"] = int(m_cfg["crpsConfig"]["trainConfig"]["numSamplers"])
                    model = CRPSPredictiveModel(variableset, s_labels, m_type, **init)
                t_cfg = m_cfg["nnConfig"]["trainConfig"]

            if model:
                x_t, x_v, y_t, y_v = model.train_test_split(
                    x_data, y_data, 
                    train_test_ratio=data["splitConfig"]["trainTestRatio"],
                    random_seed=data["splitConfig"]["seed"],
                    split_type=data["splitConfig"]["trainTestSplit"]
                )
                await asyncio.to_thread(model.train, x_t, y_t, t_cfg)
                ind_m, over_m = await asyncio.to_thread(model.evaluate_model, y_t, x_v, y_v)
                self.data[sid]["model"] = model
                await self.emit("outputQoi", y_t.columns.tolist(), to=sid)
                await self.emit("train_result", "Done", to=sid)
                await self.emit("train_metrics", {"individual": ind_m.to_dict(), "overall": over_m}, to=sid)
        except Exception as e:
            logging.error(f"Training error: {e}")
            await self.emit("train_result", f"Error: {e}", to=sid)

    async def on_predict(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            m = self.data[sid]["model"]
            pdf = pd.DataFrame(np.array(data, ndmin=2), columns=m.Q.variable_names())
            await self.emit("predict", m.predict(pdf).tolist(), to=sid)
        except Exception as e:
            await self.emit("error", f"Prediction error: {e}", to=sid)

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
    
    async def on_shap_beeswarm(self, sid, param_name):
        try:
            if not await self._check_rate_limit(sid): return
            model = self.data[sid]["model"]
            X_test = pd.DataFrame(self.data[sid]["sample"])
            fig = await model.plot_shap_beeswarm(X_test=X_test, param_name=param_name, silent=True)
            binary_data = await asyncio.to_thread(self.fig_to_binary, fig)
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
            fig = await model.plot_shap_multiple_waterfalls(X_test=pd.DataFrame(self.data[sid]["selected_sample"]), q=values, silent=True)
            binary_data = await asyncio.to_thread(self.fig_to_binary, fig)
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
                X_test=pd.DataFrame(self.data[sid]["selected_sample"]), q=values, param_name=qoi, silent=True
            )
            binary_data = await asyncio.to_thread(self.fig_to_binary, fig)
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
            self.data[sid].update({"partial_var_df": p_var, "sobol_index_df": s_idx})
            fig = await asyncio.to_thread(m.plot_sobol_sensitivity, self.data[sid]["selected_qoi"])
            await self.emit("sobol", {"partialVariance": p_var.to_dict(), "sobolIndex": s_idx.to_dict()}, to=sid)
            binary_data = await asyncio.to_thread(self.fig_to_binary, fig)
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
            binary_data = await asyncio.to_thread(self.fig_to_binary, fig)
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
            df = pd.DataFrame(self.data[sid]["selected_sample"])
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
            E = generate_stdrn_simparamset(sigma_flat)
            dt = DigitalTwin(self.data[sid]["model"], E)
            name_pairs = self.data[sid].get("name_pairs", None)
            await asyncio.to_thread(
                functools.partial(dt.update, self.data[sid]["zmean"], nwalkers, nburn, niter, name_pairs=name_pairs)
            )
            map = dt.get_MAP()
            fig_mcmc = utils.plot_MCMC(
                self.data[sid]["model"],
                self.data[sid]["sample"],
                dt,
                nwalkers=data["nwalkers"],
                map_point=map,
            )
            means_df, variances_df = dt.get_mean_and_var_of_posterior()
            self.data[sid]["dt"] = dt
            await self.emit(
                "update",
                {
                    "mcmc": self.fig_to_binary(fig_mcmc),
                    "mean": means_df.to_dict(),
                    "variance": variances_df.to_dict(),
                    "map": map.to_dict(),
                },
                to=sid,
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

    async def on_get_multi_data(self, sid, data):
        if not await self._check_rate_limit(sid): return
        index = data["index"]
        try:
            joint_manager = self.data[sid]["joint_manager"]
            if joint_manager is not None:
                map, means_df, variances_df, posterior_samples = (
                    joint_manager.get_data_of_model(index)
                )
                self.data[sid]["posterior_samples"] = posterior_samples
                model_names = list(self.data[sid]["models"].keys())
                figs = utils.plot_multimodel_MCMC(
                    joint_manager, model_names=model_names
                )
                binary_figs = [self.fig_to_binary(fig) for fig in figs]
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
            else:
                await self.emit("error", "Joint manager not found", to=sid)
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    async def on_update_multi(self, sid, data):
        try:
            if not await self._check_rate_limit(sid): return
            means = [obj["zmean"] for obj in self.data[sid]["models"].values()]
            sigmas = [obj["sigma"] for obj in self.data[sid]["models"].values()]
            self.data[sid]["joint_manager"].update(means, sigmas, **data)
            await self.emit("update_done", to=sid)
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    # --- Demo Handlers ---
    async def on_data_driven_demo(self, sid):
        try:
            d_path = os.path.join(BASE_DIR, "demo/data/sine_data")
            with open(os.path.join(d_path, "model2.ddpm"), "rb") as f:
                m = pickle.load(f)
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
        except Exception as e:
            logging.error(f"Error running multi-model demo: {e}")
            await self.emit("error", str(e), to=sid)

