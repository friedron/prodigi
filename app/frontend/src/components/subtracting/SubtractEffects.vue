<template>
    <div class="subtract-effects-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/static/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/static/logos/UGR_logo.PNG', alt: 'Sztaki Logo' },
                    { src: '/static/logos/UL_logo.png', alt: 'Uni Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'uq'" :changePage="changePage" />

        <!-- Feature Selection Card -->
        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-scissors fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Feature Effect Subtraction</h2>
            </div>
            
            <p class="text-muted mb-4">Select the input features whose influence you wish to remove from the Quantities of Interest (QoI).</p>

            <div class="row g-4">
                <div class="col-md-6">
                    <div class="selection-box border rounded p-3 bg-light">
                        <label class="form-label fw-bold d-block mb-3">Available Features</label>
                        <div class="scroll-area bg-white border rounded p-2">
                            <div v-for="feat in surrogatePage.selectedFeats" :key="feat" class="custom-check">
                                <input class="form-check-input" type="checkbox" :id="'f-' + feat" :value="feat" v-model="subtractPage.selectedFeatures" />
                                <label class="form-check-label" :for="'f-' + feat">{{ feat }}</label>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6 d-flex flex-column justify-content-center align-items-center border-start">
                    <div v-if="subtracted_df === null" class="text-center w-100">
                        <button class="btn-pro px-4 py-3" :disabled="subtractPage.selectedFeatures.length === 0" @click="subtract">
                            <i class="bi bi-calculator-history"></i> Subtract Selected Features Effect from QoI
                        </button>
                        <p class="small text-muted mt-3" v-if="subtractPage.selectedFeatures.length === 0">Select at least one feature to continue.</p>
                    </div>
                    <div v-else class="text-center">
                        <div class="alert alert-success d-flex align-items-center mb-0">
                            <i class="bi bi-check-circle-fill me-2"></i>
                            Subtraction Complete
                        </div>
                        <button class="btn-pro btn-outline-pro mt-3" @click="subtracted_df = null">
                            <i class="bi bi-arrow-repeat"></i> Reset Analysis
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Statistics Card -->
        <div class="card-pro content-card mb-4" v-if="describe_df">
            <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom">
                <div class="d-flex align-items-center">
                    <i class="bi bi-table fs-4 me-2 text-primary"></i>
                    <h2 class="h4 mb-0">Subtracted Data Statistics</h2>
                </div>
                <div class="d-flex gap-2">
                    <OutputLoader
                        :title="'Export Data'"
                        :dkgApiStatus="dkgApiStatus"
                        :socket="socket"
                        @save-file="download"
                        :mode="'subtracted_data'"
                        :dkgToken="dkgToken"
                    />
                    <button class="btn-pro btn-outline-pro btn-sm" @click="download_describe">
                        <i class="bi bi-download"></i> Export Stats
                    </button>
                </div>
            </div>

            <div class="table-responsive">
                <table class="table table-hover align-middle custom-table border">
                    <thead>
                        <tr>
                            <th>QoI</th>
                            <th class="text-end">Mean</th>
                            <th class="text-end">Std</th>
                            <th class="text-end">Min</th>
                            <th class="text-end">25%</th>
                            <th class="text-end">50%</th>
                            <th class="text-end">75%</th>
                            <th class="text-end">Max</th>
                            <th class="text-end">Count</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, key) in describe_df" :key="key">
                            <td class="fw-bold text-primary">{{ key }}</td>
                            <td class="text-end font-monospace">{{ row.mean.toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row.std === null ? "-" : row.std.toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row.min.toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row["25%"].toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row["50%"].toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row["75%"].toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row.max.toFixed(4) }}</td>
                            <td class="text-end font-monospace text-muted small">{{ row.count }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Paired Scatter Analysis Card -->
        <div class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-dot-circle fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Paired Scatter Analysis</h2>
            </div>

            <div class="row g-3 mb-4">
                <div class="col-md-4">
                    <label class="form-label fw-bold small text-uppercase text-muted">X-Axis</label>
                    <select v-model="param1" class="form-select">
                        <optgroup label="Parameters">
                            <option v-for="param in paramPage.data.params" :key="'p1-'+param.name" :value="param.name">{{ param.name }}</option>
                        </optgroup>
                        <optgroup label="QoI">
                            <option v-for="param in surrogatePage.outputQoI" :key="'q1-'+param" :value="param">{{ param }}</option>
                        </optgroup>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold small text-uppercase text-muted">Y-Axis</label>
                    <select v-model="param2" class="form-select">
                        <optgroup label="Parameters">
                            <option v-for="param in paramPage.data.params" :key="'p2-'+param.name" :value="param.name">{{ param.name }}</option>
                        </optgroup>
                        <optgroup label="QoI">
                            <option v-for="param in surrogatePage.outputQoI" :key="'q2-'+param" :value="param">{{ param }}</option>
                        </optgroup>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold small text-uppercase text-muted">Color by</label>
                    <select v-model="colorBy" class="form-select">
                        <option value="">None</option>
                        <optgroup label="Parameters">
                            <option v-for="param in paramPage.data.params" :key="'pc-'+param.name" :value="param.name">{{ param.name }}</option>
                        </optgroup>
                        <optgroup label="QoI">
                            <option v-for="param in surrogatePage.outputQoI" :key="'qc-'+param" :value="param">{{ param }}</option>
                        </optgroup>
                    </select>
                </div>
            </div>

            <div class="d-flex justify-content-center mb-4">
                <button
                    class="btn-pro px-5"
                    :disabled="!param1 || !param2"
                    @click="
                        socket.emit('subtracted_plot_scatter', {
                            param1: this.param1,
                            param2: this.param2,
                            hue: this.colorBy,
                        })
                    "
                >
                    <i class="bi bi-play-fill"></i> Show Plot
                </button>
            </div>

            <div v-if="plot_scatter" class="plot-container">
                <img class="img-fluid plot-img" :src="plot_scatter" alt="Subtracted Plot" />
            </div>
            <div v-else-if="param1 && param2" class="plot-placeholder bg-light">
                <p class="text-muted mb-0">Select axes and click "Show Plot" to visualize relationships after effect subtraction.</p>
            </div>
        </div>

        <NextButton :nextPage="'thresholdExceedance'" :available="true" :changePage="changePage" />
    </div>
</template>

<script>
import NextButton from "../NextButton.vue";
import BackButton from "../BackButton.vue";
import LogoLine from "../LogoLine.vue";
import InputLoader from "../InputLoader.vue";
import OutputLoader from "../OutputLoader.vue";

export default {
    components: {
        NextButton,
        BackButton,
        LogoLine,
        InputLoader,
        OutputLoader,
    },
    props: {
        paramPage: {
            type: Object,
            required: true,
        },
        surrogatePage: {
            type: Object,
            required: true,
        },
        subtractPage: {
            type: Object,
            required: true,
        },
        socket: {
            type: Object,
            required: true,
        },
        changePage: {
            type: Function,
            required: true,
        },
        dkgApiStatus: {
            type: String,
            required: true,
        },
        convertToBase64: {
            type: Function,
            required: true,
        },
        dkgToken: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            param1: null,
            param2: null,
            colorBy: "",
            plot_scatter: null,
            subtracted_df: null,
            describe_df: null,
        };
    },

    methods: {
        loadInput(event) {
            const file = event;
            if (!file) {
                return;
            }
            const reader = new FileReader();
            reader.onload = (event) => {
                const csvContent = event.target.result;
                this.socket.emit("load_subtract_input", { name: file.name, type: file.type, data: csvContent });
            };
            reader.readAsText(file);
        },
        loadOutput(event) {
            const file = event;
            if (!file) {
                return;
            }
            const reader = new FileReader();
            reader.onload = (event) => {
                const csvContent = event.target.result;
                this.socket.emit("load_subtract_output", { name: file.name, type: file.type, data: csvContent });
            };
            reader.readAsText(file);
        },
        subtract() {
            this.$emit("set-loading", true);
            this.socket.emit("subtract", {
                selected_features: this.subtractPage.selectedFeatures,
            });
        },
        download() {
            this.socket.emit("download_subtracted");
        },
        download_describe() {
            this.socket.emit("download_subtracted_describe");
        },
        saveSubtracted() {
            this.socket.emit("save_subtracted_data");
        },
        saveReferenceStats() {
            this.socket.emit("save_reference_stats");
        },
        saveMonitoringStats() {
            this.socket.emit("save_monitoring_stats");
        },
    },
    mounted() {
        this.socket.on("download_subtracted_data", (csvData) => {
            const blob = new Blob([csvData], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "subtracted_data.csv";
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 0);
        });
        this.socket.on("download_subtracted_describe", (csvData) => {
            const blob = new Blob([csvData], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "subtracted_stats.csv";
            document.body.appendChild(a);
            a.click();
            setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }, 0);
        });
        this.socket.on("subtracted_data", (data) => {
            const subtracted = JSON.parse(data["subtracted_df"]);
            const describe = JSON.parse(data["describe_df"]);
            this.subtracted_df = subtracted;
            this.describe_df = describe;
            this.$emit("set-loading", false);
        });
        this.socket.on("subtracted_plot_scatter", (data) => {
            this.convertToBase64(data)
                .then((base64Image) => {
                    this.plot_scatter = base64Image;
                })
                .catch((err) => {
                    console.error(err);
                });
        });
    },

    beforeUnmount() {
        this.socket.off("subtracted_data");
        this.socket.off("subtracted_plot_scatter");
        this.socket.off("download_subtracted_data");
        this.socket.off("download_subtracted_describe");
    },
};
</script>

<style scoped>
.subtract-effects-page {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
}

.scroll-area {
    max-height: 200px;
    overflow-y: auto;
}

.custom-check {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0.4rem 0.75rem;
    border-radius: 6px;
    transition: background 0.2s ease;
    cursor: pointer;
}

.custom-check:hover {
    background-color: var(--secondary);
}

.custom-check input {
    margin: 0;
    cursor: pointer;
    width: 1.1rem;
    height: 1.1rem;
    accent-color: var(--primary);
}

.custom-check label {
    margin: 0;
    cursor: pointer;
    font-size: 0.9rem;
    color: var(--text-main);
    flex-grow: 1;
}

.custom-table thead th {
    background-color: var(--secondary);
    font-size: 0.75rem;
    text-transform: uppercase;
    color: var(--text-muted);
}

.plot-container {
    background: white;
    padding: var(--spacing-md);
    border-radius: var(--radius);
    border: 1px solid var(--border-color);
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    display: flex;
    justify-content: center;
    overflow: hidden;
}

.plot-img {
    max-height: 500px;
    object-fit: contain;
}

.plot-placeholder {
    height: 300px;
    border: 2px dashed var(--border-color);
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.font-monospace {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.9em;
}

.form-select:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(163, 0, 54, 0.1);
}

optgroup {
    font-weight: 700;
    color: var(--primary);
}
</style>