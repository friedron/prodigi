import base64
import io
import json
import logging
import os
import pickle
import tempfile
import time
import uuid
from io import BytesIO, StringIO

import httpx
import pandas as pd
import numpy as np
import socketio
import tornado
from tornado.ioloop import PeriodicCallback

# Science & Engineering imports
import ifcopenshell
import bimquake
import plotly.io as pio
import matplotlib.pyplot as plt

# Installed packages
from digital_twinning import PredictiveModel, DigitalTwin, JointManager, utils
from uncertain_variables.distributions import (
    NormalDistribution, UniformDistribution, LogNormalDistribution,
    BetaDistribution, ExponentialDistribution, TranslatedDistribution
)
from uncertain_variables.variable_set import VariableSet
from uncertain_variables.variable import Variable

# Local library imports
from utils.preprocess_modeshape_data import (
    plot_correlation, preprocess_weather_df,
    scatter_plot, 
)
import utils.get_openmeteo_data as openmeteo
from handlers.rate_limiter import RateLimiter

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
        if d.get("paramset"): await self.send_paramset(sid)
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

    def validate_data(self, sid, data, req_type, req_fields):
        if not isinstance(data, req_type):
            return False, "Invalid data format."
        for f in req_fields:
            if f not in data:
                return False, f"Missing field: {f}"
        return True, None

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
    def format_params(self, variables):
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
        return {name: obj["model"].Q.param_names() for name, obj in models.items()}

    # --- Data Emitters ---
    async def send_model(self, sid):
        m = self.data[sid]["model"]
        await self.emit("sample", m.samples.to_numpy().tolist(), to=sid)
        await self.emit("train_result", "Done", to=sid)
        await self.emit("load_model", {
            "params": self.format_params(m.Q.variables),
            "modelConfig": self.format_model_config(m)
        }, to=sid)
        await self.emit("qoi", m.QoI.describe().to_json(), to=sid)

    async def send_paramset(self, sid):
        await self.emit("params", self.format_params(self.data[sid]["paramset"].variables))

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
            
            df = pd.read_csv(io.BytesIO(complete))
            self.data[sid]["sample"] = df
            self.data[sid]["paramset"] = utils.get_simparamset_from_data(df)
            
            await self.emit("features_loaded", {"filename": name}, to=sid)
            await self.emit("sample", df.to_numpy().tolist(), to=sid)
            await self.emit("features_stats", df.describe().to_json(), to=sid)
            await self.send_paramset(sid)
        except Exception as e:
            logging.error(f"Load features error: {e}")
            await self.emit("error", f"Load features error: {e}", to=sid)

    async def on_load_model(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            
            model = pickle.loads(complete)
            self.data[sid].update({
                "model": model, "paramset": model.Q, 
                "qoi": model.QoI, "sample": model.samples
            })
            await self.send_model(sid)
        except Exception as e:
            logging.error(f"Load model error: {e}")
            await self.emit("error", f"Load model error: {e}", to=sid)

    async def on_qoi_csv(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            
            df = pd.read_csv(io.BytesIO(complete))
            self.data[sid]["qoi"] = df
            await self.emit("labels_loaded", {"filename": name}, to=sid)
            await self.emit("qoi", df.describe().to_json(), to=sid)
        except Exception as e:
            logging.error(f"Load QoI error: {e}")
            await self.emit("error", f"Load QoI error: {e}", to=sid)

    async def on_load_zmean(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            
            df = pd.read_csv(io.BytesIO(complete), index_index=0)
            self.data[sid]["zmean"] = df
            await self.emit("zmean_loaded", {"filename": name}, to=sid)
            await self.emit("zmean", df.to_dict(), to=sid)
        except Exception as e:
            await self.emit("error", f"Load Z-mean error: {e}", to=sid)

    async def on_load_sigma(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            
            df = pd.read_csv(io.BytesIO(complete), index_index=0)
            self.data[sid]["sigma"] = df
            await self.emit("sigma_loaded", {"filename": name}, to=sid)
            await self.emit("sigma", df.to_dict(), to=sid)
        except Exception as e:
            await self.emit("error", f"Load Sigma error: {e}", to=sid)

    async def on_load_subtract_input(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            
            df = pd.read_csv(io.BytesIO(complete))
            self.data[sid]["subtract_input"] = df
            await self.emit("features_loaded", {"filename": name}, to=sid)
            await self.emit("subtract_input", df.to_dict(), to=sid)
        except Exception as e:
            await self.emit("error", f"Load Subtract Input error: {e}", to=sid)

    async def on_load_subtract_output(self, sid, data):
        try:
            complete, name = await self.recieve_chunks(sid, data)
            if not complete: return
            
            df = pd.read_csv(io.BytesIO(complete))
            self.data[sid]["subtract_output"] = df
            await self.emit("labels_loaded", {"filename": name}, to=sid)
            await self.emit("subtract_output", df.to_dict(), to=sid)
        except Exception as e:
            await self.emit("error", f"Load Subtract Output error: {e}", to=sid)

    async def on_subtract(self, sid, data):
        try:
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
            subtracted = self.data[sid]["subtracted"]
            param1 = data["param1"]
            param2 = data["param2"]
            fig = scatter_plot(
                pd.DataFrame(
                    self.data[sid]["selected_sample"],
                    columns=self.data[sid]["model"].Q.param_names(),
                ),
                self.data[sid]["subtracted"],
                param1,
                param2,
                hue_col=data["hue"] if "hue" in data and data["hue"] != "" else None,
            )
            binary_fig = self.fig_to_binary(fig)
            await self.emit("subtracted_plot_scatter", binary_fig, to=sid)
        except Exception as e:
            await self.emit("error", str(e), to=sid)

    async def on_threshold_exceed(self, sid, data):
        try:
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
            binary_data = self.fig_to_binary(fig)
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
        )

    async def on_save_monitoring_stats(self, sid):
        await self.emit(
            "monitoring_stats",
            self.data[sid]["monitoring_statistics"].to_csv(index=False),
        )

    # --- Core Handlers ---
    async def on_mode(self, sid, mode):
        self.data[sid]["mode"] = mode

    async def on_fetch_weather_data(self, sid, data):
        try:
            raw = openmeteo.get_openmeteo_data(
                data["latitude"], data["longitude"], 
                data["start_date"], data["end_date"], data["features"]
            )
            processed = preprocess_weather_df(raw)
            self.data[sid]["weather_full"] = processed
            
            export_df = processed.copy()
            if "Datetime" in export_df.columns:
                export_df["Datetime"] = export_df["Datetime"].dt.strftime('%Y-%m-%d %H:%M:%S')
            
            num_only = processed.drop(columns=["Datetime"], errors="ignore").astype(float)
            self.data[sid]["sample"] = num_only
            self.data[sid]["paramset"] = utils.get_simparamset_from_data(num_only)
            
            await self.emit("sample", export_df.values.tolist(), to=sid)
            await self.emit("features_stats", num_only.describe().to_json(), to=sid)
            await self.emit("features_loaded", {"filename": "Weather Data"}, to=sid)
            await self.send_paramset(sid)
        except Exception as e:
            await self.emit("error", f"Weather data error: {e}", to=sid)

    async def on_exploratory_plot(self, sid, data):
        df = pd.DataFrame(self.data[sid]["sample"], columns=self.data[sid]["paramset"].param_names())
        fig = plot_correlation(df, self.data[sid]["qoi"], mode=data.get("mode", "input-output"))
        await self.emit("exploratory_plot", self.fig_to_binary(fig), to=sid)

    async def on_exploratory_plot_scatter(self, sid, data):
        df = pd.DataFrame(self.data[sid]["sample"], columns=self.data[sid]["paramset"].param_names())
        fig = scatter_plot(df, self.data[sid]["qoi"], data["param1"], data["param2"], 
                          hue_col=data.get("hue") if data.get("hue") else None)
        await self.emit("exploratory_plot_scatter", self.fig_to_binary(fig), to=sid)

    # --- Training & Analysis Handlers ---
    async def on_train(self, sid, data):
        try:
            m_cfg = data["modelConfig"]
            m_type = m_cfg["modelType"]
            if not m_type: return
            
            s_feats = data["selectedFeats"]
            s_labels = data["selectedLabels"]
            
            x_data = self.data[sid]["sample"][s_feats]
            y_data = self.data[sid]["qoi"][s_labels]
            
            paramset = utils.get_simparamset_from_data(x_data)
            self.data[sid].update({"selected_sample": x_data, "selected_qoi": y_data, "filtered_paramset": paramset})
            
            model = None
            if m_type == "gPCE":
                p = int(m_cfg["gpcConfig"]["initConfig"]["p"])
                model = PredictiveModel(paramset, s_labels, m_type, p=p)
                t_cfg = m_cfg["gpcConfig"]["trainConfig"]
            elif m_type == "GBT":
                model = PredictiveModel(paramset, s_labels, m_type, **m_cfg["gbtConfig"]["initConfig"])
                t_cfg = m_cfg["gbtConfig"]["trainConfig"]
            elif m_type == "DNN":
                init = {
                    "layers": [{
                        "neurons": int(l["numOfNeurons"]), "activation": l["activationFunction"], "dropout": float(l["dropout"])
                    } for l in m_cfg["nnConfig"]["initConfig"]["layers"]],
                    "outputAF": m_cfg["nnConfig"]["initConfig"]["outputAF"]
                }
                model = PredictiveModel(paramset, s_labels, m_type, **init)
                t_cfg = m_cfg["nnConfig"]["trainConfig"]
            elif m_type == "LinReg":
                model = PredictiveModel(paramset, s_labels, m_type)
                t_cfg = {}

            if model:
                x_t, x_v, y_t, y_v = model.train_test_split(
                    x_data, y_data, 
                    train_test_ratio=data["splitConfig"]["trainTestRatio"],
                    random_seed=data["splitConfig"]["seed"],
                    split_type=data["splitConfig"]["trainTestSplit"]
                )
                model.train(x_t, y_t, t_cfg)
                ind_m, over_m = model.evaluate_model(y_t, x_v, y_v)
                self.data[sid]["model"] = model
                await self.emit("outputQoi", y_t.columns.tolist(), to=sid)
                await self.emit("train_result", "Done", to=sid)
                await self.emit("train_metrics", {"individual": ind_m.to_dict(), "overall": over_m}, to=sid)
        except Exception as e:
            logging.error(f"Training error: {e}")
            await self.emit("train_result", f"Error: {e}", to=sid)

    async def on_predict(self, sid, data):
        try:
            m = self.data[sid]["model"]
            pdf = pd.DataFrame(np.array(data, ndmin=2), columns=m.Q.param_names())
            await self.emit("predict", m.predict(pdf).tolist(), to=sid)
        except Exception as e:
            await self.emit("error", f"Prediction error: {e}", to=sid)

    async def on_mean_var(self, sid):
        try:
            model = self.data[sid]["model"]
            mean, variance = model.get_mean_and_var()
            print(mean, variance)
            await self.emit(
                "mean_var", {"mean": mean.tolist(), "variance": variance.tolist()}, to=sid
            )
        except Exception as e:
            print(f"Error computing mean and variance: {str(e)}")
            await self.emit(
                "error", f"Error computing mean and variance: {str(e)}", to=sid
            )
    
    async def on_shap_beeswarm(self, sid, param_name):
        try:
            model = self.data[sid]["model"]
            X_test = pd.DataFrame(self.data[sid]["sample"])
            fig = await model.plot_shap_beeswarm(X_test=X_test, param_name=param_name)
            binary_data = self.fig_to_binary(fig)
            await self.emit("beeswarm_plot", binary_data, to=sid)
        except Exception as e:
            await self.emit(
                "error", f"Error generating beeswarm plot: {str(e)}", to=sid
            )

    async def on_waterfall_multi(self, sid, data):
        try:
            model = self.data[sid]["model"]
            values = data
            fig = await model.plot_shap_multiple_waterfalls(X_test=pd.DataFrame(self.data[sid]["selected_sample"]), q=values)
            binary_data = self.fig_to_binary(fig)
            print("Emitting shap_plot_multi")
            print(binary_data[:100])  # Print the first 100 bytes of the binary data for debugging
            await self.emit("shap_plot_multi", binary_data, to=sid)
        except Exception as e:
            print(e)
            await self.emit(
                "error", f"Error generating multiple waterfall plot: {str(e)}", to=sid
            )

    async def on_waterfall_single(self, sid, data):
        try:
            model = self.data[sid]["model"]
            qoi = data["qoi"]
            values = data["values"]
            fig = await model.plot_shap_single_waterfall(
                X_test=pd.DataFrame(self.data[sid]["selected_sample"]), q=values, param_name=qoi
            )
            binary_data = self.fig_to_binary(fig)
            await self.emit("shap_plot_single", binary_data, to=sid)
        except Exception as e:
            print(e)
            await self.emit(
                "error", f"Error generating single waterfall plot: {str(e)}", to=sid
            )

    async def on_sobol(self, sid, data):
        try:
            m = self.data[sid]["model"]
            p_var, s_idx = m.get_sobol_sensitivity(data)
            self.data[sid].update({"partial_var_df": p_var, "sobol_index_df": s_idx})
            fig = m.plot_sobol_sensitivity(self.data[sid]["selected_qoi"])
            await self.emit("sobol", {"partialVariance": p_var.to_dict(), "sobolIndex": s_idx.to_dict()}, to=sid)
            await self.emit("sobol_plot", self.fig_to_binary(fig), to=sid)
        except Exception as e:
            await self.emit("error", f"Sobol error: {e}", to=sid)

    async def on_sobol_single(self, sid, data):
        try:
            model = self.data[sid]["model"]
            qoi = data
            partial_var_df = self.data[sid]["partial_var_df"]
            sobol_index_df = self.data[sid]["sobol_index_df"]
            fig = model.plot_sobol_sensitivity(self.data[sid]["selected_qoi"], param_name=qoi)
            binary_data = self.fig_to_binary(fig)
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
            print(e)
            await self.emit(
                "error", f"Error computing single Sobol index: {str(e)}", to=sid
            )

    async def on_shap(self, sid):
        try:
            m = self.data[sid]["model"]
            df = pd.DataFrame(self.data[sid]["selected_sample"])
            vals = await m.get_shap_values(df, mean=True)
            await self.emit("shap", vals.values.T.tolist(), to=sid)
        except Exception as e:
            await self.emit("error", f"SHAP error: {e}", to=sid)

    # --- Demo Handlers ---
    async def on_data_driven_demo(self, sid):
        try:
            d_path = os.path.join(BASE_DIR, "demo/data/sine_data")
            with open(os.path.join(d_path, "model2.ddpm"), "rb") as f:
                m = pickle.load(f)
            self.data[sid].update({
                "model": m, "paramset": m.Q, "qoi": m.QoI, "selected_qoi": m.QoI,
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
                "model": m, "paramset": m.Q, "qoi": m.QoI, "selected_qoi": m.QoI,
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
            d_path = os.path.join(BASE_DIR, "demo/data/spring_data")
            with open(os.path.join(d_path, "Spring1_model.sm"), "rb") as f1, \
                 open(os.path.join(d_path, "Spring2_model.sm"), "rb") as f2:
                m1, m2 = pickle.load(f1), pickle.load(f2)
            
            join = {"joint_m1_m2": ["m1", "m2"], "joint_k1_k2": ["k1", "k2"]}
            self.data[sid]["models"] = {
                "model1": {"model": m1, "zmean": pd.read_csv(os.path.join(d_path, "z_spring1_df.csv")), 
                          "sigma": pd.read_csv(os.path.join(d_path, "sigma_spring1.csv"))},
                "model2": {"model": m2, "zmean": pd.read_csv(os.path.join(d_path, "z_spring2_df.csv")), 
                          "sigma": pd.read_csv(os.path.join(d_path, "sigma_spring2.csv"))}
            }
            self.data[sid]["joint_manager"] = JointManager([m1, m2], join)
            await self.emit("models", self.format_models(self.data[sid]["models"]), to=sid)
            await self.emit("joint_created", to=sid)
            await self.send_multi_measurements(sid)
        except Exception as e:
            await self.emit("error", f"Multi-Model Demo error: {e}", to=sid)

