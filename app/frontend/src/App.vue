<script setup>
import LogoBar from "./components/LogoBar.vue";
import MeasurementsPage from "./components/surrogate/MeasurementsPage.vue";
import SubtractEffects from "./components/subtracting/SubtractEffects.vue";
import ParamPage from "./components/surrogate/ParamPage.vue";
import ParamPageDD from "./components/subtracting/ParamPageDD.vue";
import Sidebar from "./components/Sidebar.vue";
import SurrogatePage from "./components/surrogate/SurrogatePage.vue";
import UpdatePage from "./components/UpdatePage.vue";
import UqPage from "./components/UqPage.vue";
import MeasurementsPageMulti from "./components/multiModel/MeasurementsPageMulti.vue";
import UploadPage from "./components/UploadPage.vue";
import HomePage from "./components/HomePage.vue";
import InfoPage from "./components/InfoPage.vue";
import ConfirmDialog from "./components/ConfirmDialog.vue";
import SampleQoIPage from "./components/surrogate/SampleQoIPage.vue";
import CompareMeasurement from "./components/CompareMeasurement.vue";
import Exploratory from "./components/subtracting/Exploratory.vue";
import ThresholdExceedance from "./components/subtracting/ThresholdExceedance.vue";
import LoadingIndicator from "./components/LoadingIndicator.vue";
</script>
<template>
    <div class="app-container" :class="{ loading: isLoading }">
        <div class="app-background"></div>
        <LoadingIndicator />
        <LogoBar></LogoBar>
        <Sidebar
            :mode="mode"
            :activePage="activePage"
            :completedPages="completedPages"
            @change-page="changePage"
            @change-mode="changeMode"
        />
        <div class="main-content">
            <HomePage
                v-if="mode === 'home'"
                v-model:mode="mode"
                v-model:activePage="activePage"
                :socket="socket"
                @update-mode="changeMode"
            />
            <InfoPage
                v-if="activePage === 'info'"
                v-model:mode="mode"
                v-model:activePage="activePage"
                :socket="socket"
                :changePage="changePage"
                @set-loading="setLoading"
            />
            <UploadPage
                v-if="activePage === 'upload'"
                v-model:uploadPage="uploadPage"
                v-model:mode="mode"
                :socket="socket"
                :addPageDone="addPageDone"
                :changePage="changePage"
                :sendInChunks="sendInChunks"
            />
            <ParamPage
                v-if="activePage === 'params' && mode === 'surrogate'"
                v-model:paramPage="paramPage"
                :socket="socket"
                :changePage="changePage"
                :addPageDone="addPageDone"
                :sendInChunks="sendInChunks"
            />
            <SampleQoIPage
                v-if="activePage === 'sample' && mode === 'surrogate'"
                v-model:paramPage="paramPage"
                :socket="socket"
                :changePage="changePage"
                :addPageDone="addPageDone"
                :sendInChunks="sendInChunks"
            />
            <ParamPageDD
                v-if="activePage === 'params' && mode === 'subtracting'"
                v-model:paramPage="paramPage"
                :socket="socket"
                :changePage="changePage"
                :addPageDone="addPageDone"
                :sendInChunks="sendInChunks"
            />
            <Exploratory
                v-if="activePage === 'exploratory'"
                :paramPage="paramPage"
                :socket="socket"
                :convertToBase64="convertToBase64"
                :changePage="changePage"
            />
            <SurrogatePage
                v-if="activePage === 'surrogate'"
                v-model:surrogatePage="surrogatePage"
                :mode="mode"
                :paramPage="paramPage"
                :socket="socket"
                :changePage="changePage"
                :addPageDone="addPageDone"
            />
            <UqPage
                v-if="activePage === 'uq'"
                v-model:uqPage="uqPage"
                :paramPage="paramPage"
                :surrogatePage="surrogatePage"
                :mode="mode"
                :socket="socket"
                :changePage="changePage"
                :isLoading="isLoading"
                @set-loading="setLoading"
            />
            <SubtractEffects
                v-if="activePage === 'subtract'"
                v-model:subtractPage="subtractPage"
                :paramPage="paramPage"
                :surrogatePage="surrogatePage"
                :socket="socket"
                :changePage="changePage"
                @set-loading="setLoading"
                :convertToBase64="convertToBase64"
            />
            <ThresholdExceedance
                v-if="activePage === 'thresholdExceedance'"
                v-model:subtractPage="subtractPage"
                :paramPage="paramPage"
                :socket="socket"
                :changePage="changePage"
                :sendInChunks="sendInChunks"
                @set-loading="setLoading"
            />
            <MeasurementsPage
                v-if="activePage === 'measurements' && mode !== 'multiModel'"
                v-model:measurementsPage="measurementsPage"
                :mode="mode"
                :socket="socket"
                :changePage="changePage"
                :addPageDone="addPageDone"
                :sendInChunks="sendInChunks"
            />
            <MeasurementsPageMulti
                v-if="activePage === 'measurements' && mode === 'multiModel'"
                v-model:measurementsPage="measurementsPage"
                :uploadPage="uploadPage"
                :mode="mode"
                :socket="socket"
                :changePage="changePage"
                :addPageDone="addPageDone"
            />
            <CompareMeasurement
                v-if="activePage === 'compare'"
                v-model:measurementsPage="measurementsPage"
                :qoi="Object.keys(paramPage.qoiTable)"
                :measured="Object.keys(measurementsPage.zmean)"
                :mode="mode"
                :socket="socket"
                :changePage="changePage"
                :addPageDone="addPageDone"
            />
            <UpdatePage
                v-if="activePage === 'update'"
                v-model:updatePage="updatePage"
                :uploadPage="uploadPage"
                :mode="mode"
                :socket="socket"
                :changePage="changePage"
                :isLoading="isLoading"
                @set-loading="setLoading"
            />
        </div>
        <div class="footer">
            <img
                alt="Logo"
                class="img-fluid"
                style="max-height: 5vh; margin: 0.5rem"
            />
            <p>
                © 2025 Main developer: SZTAKI
            </p>
            <p>Version: Beta 1.4</p>
            <p>Last Updated: 2026-02-20</p>
        </div>
        <Teleport to="body">
            <ConfirmDialog
                v-if="showConfirm"
                :visible="true"
                message="Are you sure you want to change mode? ALL progress will be lost."
                @confirm="confirmChangeMode"
                @cancel="cancelChangeMode"
            ></ConfirmDialog>
        </Teleport>
    </div>
</template>

<script>
import socket from "./socket";

export default {
    data() {
        return {
            uploadInProgress: false,
            ...this.getDefaultData(),
        };
    },
    components: {
        UploadPage,
        Sidebar,
        ParamPage,
        ParamPageDD,
        SurrogatePage,
        UqPage,
        MeasurementsPage,
        MeasurementsPageMulti,
        SubtractEffects,
        UpdatePage,
        HomePage,
        InfoPage,
        ConfirmDialog,
        ThresholdExceedance,
        CompareMeasurement,
        Exploratory,
    },
    methods: {
        getDefaultData() {
            return {
                mode: "home",
                activePage: "info",
                isLoading: false,
                completedPages: [],
                pendingMode: null,
                showConfirm: false,
                uploadPage: {
                    models: [],
                    jointCreated: false,
                },
                paramPage: {
                    data: {
                        params: [],
                        sampleMethod: null,
                        numSamples: null,
                        randomSeed: null,
                    },
                    inputStats: {},
                    qoiTable: {},
                    samples: [],
                },
                surrogatePage: {
                    selectedLayer: null,
                    showModal: false,
                    selectedFeats: [],
                    selectedLabels: [],
                    modesList: [],
                    effectsList: [],
                    outputQoI: [],
                    splitConfig: {
                        trainTestRatio: 0.8,
                        trainTestSplit: "shuffle",
                        seed: null,
                    },
                    modelConfig: {
                        modelType: "",
                        gpcConfig: {
                            initConfig: {
                                p: 3,
                            },
                            trainConfig: {},
                        },
                        gbtConfig: {
                            initConfig: {
                                gbt_method: "xgboost",
                            },
                            trainConfig: {
                                maxDepth: null,
                                numOfIter: null,
                            },
                        },
                        nnConfig: {
                            initConfig: {
                                layers: [],
                                outputAF: "",
                            },
                            trainConfig: {
                                optimizer: "",
                                loss: "",
                                epochs: null,
                                batch_size: null,
                            },
                        },
                    },
                    tooltips: {
                        split: false,
                        modelType: false,
                        gpc: {
                            degOfPoly: false,
                        },
                        gbt: {
                            method: false,
                            maxDepth: false,
                            numOfIter: false,
                        },
                        nn: {
                            outputAF: false,
                            loss: false,
                            optimizer: false,
                            epochs: false,
                            batchSize: false,
                        },
                    },
                    trainResult: "",
                    overallTrainMetrics: {},
                    individualTrainMetrics: {},
                    selectedQoIForMetric: null,
                },
                uqPage: {
                    mode: "global",
                    maxOrder: 1,
                    mean: [],
                    variance: [],
                    sensitivities: {
                        partialVariance: {},
                        sobolIndex: {},
                    },
                    shap: {},
                    prediction: [],
                    paramValues: [],
                    selectedQoI: null,
                },
                subtractPage: {
                    input: {},
                    output: {},
                    threshold: 0.1,
                    selectedFeatures: [],
                    problematicRows: null,
                    errorRatio: null,
                    referenceStats: null,
                    monitoringStats: null,
                },
                measurementsPage: {
                    zmean: null,
                    sigma: null,
                    multiModel: {},
                    done: false,
                },
                updatePage: {
                    data: {
                        nwalkers: 32,
                        nburn: 50,
                        niter: 150,
                    },
                    mcmcPlot: null,
                    multiPlots: [],
                    mean: null,
                    variance: null,
                },
            };
        },
        changeMode(mode) {
            this.pendingMode = mode;
            if (this.mode === "home") {
                this.mode = mode;
                socket.emit("mode", mode);
                this.changePage("info");
            } else if (this.mode === mode) {
                this.changePage("info");
            } else {
                this.showConfirm = true;
            }
        },
        confirmChangeMode() {
            const pendingMode = this.pendingMode;
            this.showConfirm = false;
            socket.emit("clear_session");
            Object.assign(this.$data, this.getDefaultData());
            this.mode = pendingMode;
            socket.emit("mode", this.mode);
            this.changePage("info");
        },
        cancelChangeMode() {
            this.showConfirm = false;
        },
        addPageDone(page) {
            if (this.completedPages.includes(page)) return;
            this.completedPages.push(page);
        },
        changePage(page) {
            this.activePage = page;
            new Promise(resolve => setTimeout(resolve, 100)).then(() => {
                window.scrollTo(0, 0);
            });
        },
        setLoading(value) {
            this.isLoading = value;
        },
        generateId() {
            return "_" + Math.random().toString(36).slice(2, 9);
        },
        convertToBase64(data) {
            return new Promise((resolve, reject) => {
                if (data instanceof Blob || data instanceof ArrayBuffer) {
                    const reader = new FileReader();
                    reader.onload = () => {
                        const base64Image = `data:image/png;base64,${reader.result.split(",")[1]}`;
                        resolve(base64Image);
                    };
                    reader.onerror = () => {
                        reject("Error reading data");
                    };
                    reader.readAsDataURL(new Blob([data]));
                } else {
                    reject("Unexpected data format received");
                }
            });
        },
        sendInChunks(file, eventName, socket, args = {}) {
            if (this.uploadInProgress) return;
            this.uploadInProgress = true;
            try {
                if (!file) return;
                if (file.size > 10 * 1024 * 1024) {
                    console.log("File size exceeds 10 MB.");
                }

                const chunkSize = 640 * 1024; // 640 KB
                let offset = 0;
                const fileName = file.name;
                const fileType = file.type;
                const self = this;

                function readChunk() {
                    const slice = file.slice(offset, offset + chunkSize);
                    const reader = new FileReader();

                    reader.onload = (e) => {
                        const chunk = e.target.result;
                        const isLast = offset + chunk.byteLength >= file.size;
                        socket.emit(eventName, {
                            name: fileName,
                            type: fileType,
                            data: chunk,
                            offset: offset,
                            total: file.size,
                            isLast: isLast,
                            ...args,
                        });

                        offset += chunk.byteLength;

                        if (!isLast) {
                            readChunk();
                        } else {
                            self.uploadInProgress = false;
                        }
                    };
                    reader.onerror = (err) => {
                        console.error("File read error:", err);
                    };
                    reader.readAsArrayBuffer(slice);
                }
                readChunk();
            } catch (error) {
                console.error(error);
                self.uploadInProgress = false;
            }
        },
    },
    mounted() {
        socket.on("connect_error", (err) => {
            console.error("Connection error:", err.message);
        });
        socket.on("connect", () => {
            console.log("Connected to server");
        });
        socket.on("error", (data) => {
            console.log("error: ", data);
            alert("Server error: " + data);
            this.setLoading(false);
        });
        socket.on("mode", (data) => {
            this.mode = data;
        });
        function deepMerge(target, source) {
            for (const key in source) {
                if (source[key] && typeof source[key] === "object" && !Array.isArray(source[key])) {
                    if (!target[key]) target[key] = {};
                    deepMerge(target[key], source[key]);
                } else {
                    target[key] = source[key];
                }
            }
            return target;
        }
        socket.on("load_model", (data) => {
            const { params, modelConfig } = data;
            this.paramPage.data.params = Array.isArray(params) ? params : [];
            for (let param of this.paramPage.data.params) {
                param["id"] = this.generateId();
            }
            this.surrogatePage.modelConfig = deepMerge(this.surrogatePage.modelConfig, modelConfig);
            this.addPageDone("params");
            this.addPageDone("sample");
            this.addPageDone("surrogate");
            this.addPageDone("upload");
        });
        socket.on("modes_list", (data) => {
            this.surrogatePage.modesList = data;
        });
        socket.on("effects", (data) => {
            this.surrogatePage.effectsList = data;
        });
        socket.on("params", (data) => {
            this.paramPage.data.params = data;
        });
        socket.on("sample", (data) => {
            this.paramPage.samples = data;
        });
        socket.on("shift_scale", (data) => {
            this.paramPage.data.params = data;
        });
        socket.on("qoi", (data) => {
            const parsed = JSON.parse(data);
            this.paramPage.qoiTable = parsed;
        });
        socket.on("features_stats", (data) => {
            const parsed = JSON.parse(data);
            this.paramPage.inputStats = parsed;
        });
        socket.on("train_result", (data) => {
            this.surrogatePage.trainResult = data;
        });
        socket.on("train_metrics", (data) => {
            this.surrogatePage.overallTrainMetrics = data["overall"];
            this.surrogatePage.individualTrainMetrics = data["individual"];
        });
        socket.on("outputQoi", (data) => {
            this.surrogatePage.outputQoI = data;
        });
        socket.on("mean_var", (data) => {
            const { mean, variance } = data;
            this.uqPage.mean = mean;
            this.uqPage.variance = variance;
            this.setLoading(false);
        });
        socket.on("sobol", (data) => {
            const { partialVariance, sobolIndex } = data;
            this.uqPage.sensitivities.partialVariance = partialVariance;
            this.uqPage.sensitivities.sobolIndex = sobolIndex;
            this.setLoading(false);
        });
        socket.on("sobol_plot", (data) => {
            this.convertToBase64(data)
                .then((base64Image) => {
                    this.uqPage.sobolPlot = base64Image;
                    this.setLoading(false);
                })
                .catch((err) => {
                    console.error(err);
                });
        });
        socket.on("sobol_plot_single", (data) => {
            this.convertToBase64(data)
                .then((base64Image) => {
                    this.uqPage.sobolPlotSingle = base64Image;
                    this.setLoading(false);
                })
                .catch((err) => {
                    console.error(err);
                });
        });
        socket.on("shap", (data) => {
            this.uqPage.shap = data;
            this.setLoading(false);
        });
        socket.on("beeswarm_plot", (data) => {
            this.convertToBase64(data)
                .then((base64Image) => {
                    this.uqPage.beeswarmPlot = base64Image;
                    this.setLoading(false);
                })
                .catch((err) => {
                    console.error(err);
                });
        });
        socket.on("shap_plot", (data) => {
            this.convertToBase64(data)
                .then((base64Image) => {
                    this.uqPage.shapPlot = base64Image;
                    this.setLoading(false);
                })
                .catch((err) => {
                    console.error(err);
                });
        });
        socket.on("shap_plot_single", (data) => {
            this.convertToBase64(data)
                .then((base64Image) => {
                    this.uqPage.shapPlotSingle = base64Image;
                    this.setLoading(false);
                })
                .catch((err) => {
                    console.error(err);
                });
        });
        socket.on("shap_plot_multi", (data) => {
            this.convertToBase64(data)
                .then((base64Image) => {
                    this.uqPage.shapPlotMulti = base64Image;
                    this.setLoading(false);
                })
                .catch((err) => {
                    console.error(err);
                });
        });
        socket.on("predict", (data) => {
            this.uqPage.prediction = data[0];
            this.setLoading(false);
        });
        socket.on("save_model", (data) => {
            const blob = new Blob([data], { type: "application/octet-stream" });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            if (this.mode === "subtracting") {
                link.download = "model.ddpm";
            }
            if (this.mode === "surrogate") {
                link.download = "model.sm";
            }
            link.click();
            URL.revokeObjectURL(url);
        });
        socket.on("zmean", (data) => {
            this.measurementsPage.zmean = data;
            if (this.measurementsPage.sigma) {
                this.addPageDone("measurements");
            }
        });
        socket.on("multi_measurements", (data) => {
            this.measurementsPage.multiModel = data;
            const models = Object.keys(this.uploadPage.models);
            let done = false;
            for (const model of models) {
                if (
                    this.measurementsPage.multiModel[model] &&
                    Object.keys(this.measurementsPage.multiModel[model].zmean).length > 0 &&
                    Object.keys(this.measurementsPage.multiModel[model].sigma).length > 0
                ) {
                    done = true;
                } else {
                    done = false;
                }
            }
            if (done) {
                this.addPageDone("measurements");
                this.measurementsPage.done = true;
            }
        });
        socket.on("sigma", (data) => {
            this.measurementsPage.sigma = data;
            if (this.measurementsPage.zmean) {
                this.addPageDone("measurements");
            }
        });
        socket.on("update", (data) => {
            this.convertToBase64(data["mcmc"])
                .then((base64Image) => {
                    this.updatePage.mcmcPlot = base64Image;
                })
                .catch((err) => {
                    console.error(err);
                });
            this.updatePage.mean = data["mean"];
            this.updatePage.variance = data["variance"];
            this.updatePage.map = data["map"];
            this.setLoading(false);
        });
        socket.on("update_multi", (data) => {
            const promises = data.map((plot) => this.convertToBase64(plot));
            Promise.all(promises)
                .then((base64Images) => {
                    this.updatePage.multiPlots = base64Images;
                })
                .catch((err) => {
                    console.error(err);
                });
            this.setLoading(false);
        });
        socket.on("subtract_input", (data) => {
            this.subtractPage.input = data;
        });
        socket.on("subtract_output", (data) => {
            this.subtractPage.output = data;
        });
        socket.on("subtract_data", (data) => {
            this.setLoading(false);
            this.convertToBase64(data["fig"])
                .then((base64Image) => {
                    this.subtractPage.plot = base64Image;
                })
                .catch((err) => {
                    s;
                    console.error(err);
                });
            this.subtractPage.errorRatio = data["error_ratio"];
            this.subtractPage.problematicRows = data["problematic_rows"];
            this.subtractPage.referenceStats = data["reference_statistics"];
            this.subtractPage.monitoringStats = data["monitoring_statistics"];
        });
        socket.on("models", (data) => {
            this.uploadPage.models = data;
        });
        socket.on("joint_created", () => {
            this.addPageDone("upload");
            this.uploadPage.jointCreated = true;
        });
    }
};
</script>

<style scoped>
.app-container {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.main-content {
    margin-left: var(--sidebar-width);
    margin-top: var(--header-height);
    padding: var(--spacing-lg);
    flex-grow: 1;
    background-color: var(--bg-main);
    min-height: calc(100vh - var(--header-height) - 150px); /* Adjust for footer */
}

.loading {
    cursor: wait;
    opacity: 0.7;
}

.footer {
    margin-left: var(--sidebar-width);
    padding: var(--spacing-lg);
    background: var(--bg-sidebar);
    border-top: 1px solid var(--border-color);
    font-size: 0.85rem;
    color: var(--text-muted);
    text-align: center;
}

.footer p {
    margin-bottom: 0.25rem;
}

.app-background {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    z-index: -1;
    opacity: 0.3;
}
</style>
