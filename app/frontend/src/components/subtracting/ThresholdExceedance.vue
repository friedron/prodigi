<template>
    <div class="threshold-exceedance-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="skipUq ? 'surrogate' : 'uq'" :changePage="changePage" />

        <!-- Monitoring Data Setup -->
        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-broadcast-pin fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Monitoring Period Setup</h2>
            </div>
            
            <p class="text-muted mb-4">Upload new input and output data to detect deviations from the reference model after effect subtraction.</p>

            <div class="row g-4">
                <div class="col-md-6">
                    <div class="upload-zone p-3 border rounded bg-light">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="fw-bold">Input Data (.csv)</span>
                            <InputLoader :socket="socket" @load-file="loadInput" :fileType="'.csv'" :loadType="'subtract_input'" />
                        </div>
                        <div v-if="features_file" class="small text-success d-flex align-items-center">
                            <i class="bi bi-check-circle-fill me-1"></i> Loaded: {{ features_file }}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="upload-zone p-3 border rounded bg-light">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="fw-bold">Output Data (.csv, .unv)</span>
                            <InputLoader :socket="socket" @load-file="loadOutput" :fileType="'.csv, .unv'" :loadType="'subtract_output'" />
                        </div>
                        <div v-if="labels_file" class="small text-success d-flex align-items-center">
                            <i class="bi bi-check-circle-fill me-1"></i> Loaded: {{ labels_file }}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Configuration Card -->
        <div class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-sliders fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Analysis Configuration</h2>
            </div>

            <div class="row g-4">
                <div class="col-md-6">
                    <label class="form-label fw-bold">Target Features for Subtraction</label>
                    <div class="scroll-area border rounded p-2 bg-white" v-if="Object.keys(subtractPage.input).length > 0">
                        <div v-for="(value, key) in subtractPage.input" :key="key" class="custom-check">
                            <input type="checkbox" :id="key" :value="key" v-model="subtractPage.selectedFeatures" />
                            <label :for="key">{{ key }}</label>
                        </div>
                    </div>
                    <div v-else class="text-center py-4 text-muted border rounded bg-light border-dashed">
                        Upload input data to select features.
                    </div>
                </div>
                <div class="col-md-6">
                    <label class="form-label fw-bold d-flex align-items-center gap-1">
                        Outlier Detection Threshold
                        <Tooltip content="<h3>Threshold Explanation</h3><p>Non-negative number setting the bounds of the acceptable region. If 0, bounds are min-max of reference. If >0, more exceedance is allowed relative to spread.</p>" />
                    </label>
                    <div class="input-group">
                        <span class="input-group-text bg-light"><i class="bi bi-exclamation-triangle"></i></span>
                        <input type="number" class="form-control" v-model.number="subtractPage.threshold" step="0.01" min="0" placeholder="e.g., 0.05" />
                    </div>
                    <p class="small text-muted mt-2">Determines the sensitivity of the anomaly detection algorithm.</p>
                </div>
            </div>

            <div class="mt-4 pt-3 border-top d-flex justify-content-center">
                <button class="btn-pro px-5" @click="subtract" :disabled="isAnalyzing">
                    <span v-if="isAnalyzing" class="btn-spinner"></span>
                    <i v-else class="bi bi-shield-check"></i>
                    {{ isAnalyzing ? "Analyzing…" : "Analyze Threshold Exceedance" }}
                </button>
            </div>
        </div>

        <!-- Analysis Results -->
        <div v-if="subtractPage.plot || subtractPage.errorRatio !== null" class="card-pro content-card mb-4 border-primary shadow-sm">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-activity fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Detection Results</h2>
            </div>

            <div class="row g-4 align-items-center mb-4">
                <div class="col-md-6">
                    <div class="p-4 rounded border text-center" :class="subtractPage.errorRatio > 0 ? 'bg-light-danger border-danger' : 'bg-light-success border-success'">
                        <label class="text-muted small text-uppercase fw-bold d-block mb-1">Error Ratio</label>
                        <span class="h2 mb-0 fw-bold" :class="subtractPage.errorRatio > 0 ? 'text-danger' : 'text-success'">
                            {{ (subtractPage.errorRatio * 100).toFixed(2) }}%
                        </span>
                    </div>
                </div>
                <div class="col-md-6 d-flex justify-content-center">
                    <OutputLoader
                        v-if="subtractPage.errorRatio !== null"
                        :title="'Export Analyzed Data'"
                        :loading="isSavingSubtracted"
                        @save-file="saveSubtracted"
                    />
                </div>
            </div>

            <div v-if="subtractPage.plot" class="plot-container">
                <img :src="subtractPage.plot" class="img-fluid plot-img" />
            </div>
        </div>

        <!-- Outliers Table -->
        <div v-if="subtractPage.problematicRows" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-exclamation-octagon fs-4 me-2" :class="subtractPage.problematicRows.length > 0 ? 'text-danger' : 'text-success'"></i>
                <h2 class="h4 mb-0">Detected Outliers</h2>
                <Tooltip class="ms-2" content="<p>Rows with at least one QoI value outside acceptance region. Values represent exceedance relative to reference spread.</p>" />
            </div>

            <div v-if="subtractPage.problematicRows.length > 0" class="table-responsive">
                <table class="table table-sm table-hover align-middle custom-table border">
                    <thead>
                        <tr>
                            <th>Row Index</th>
                            <th v-for="(param, index) in subtractPage.problematicRows[0]" :key="index" class="text-end">{{ index }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, index) in subtractPage.problematicRows" :key="index">
                            <td class="fw-bold">{{ index }}</td>
                            <td v-for="(param, pIdx) in row" :key="pIdx" class="text-end font-monospace text-danger">
                                {{ param.toFixed(2) }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div v-else class="alert alert-success d-flex align-items-center py-4">
                <i class="bi bi-check-circle-fill fs-4 me-3"></i>
                <div>
                    <h5 class="alert-heading mb-1">No outliers detected</h5>
                    <p class="mb-0">All monitoring data points fall within the acceptable reference region.</p>
                </div>
            </div>
        </div>

        <!-- Detailed Statistics -->
        <div v-if="subtractPage.referenceStats || subtractPage.monitoringStats" class="row g-4 mb-4">
            <div class="col-lg-6" v-if="subtractPage.referenceStats">
                <div class="card-pro content-card h-100">
                    <div class="d-flex align-items-center justify-content-between mb-3 border-bottom pb-2">
                        <h3 class="h5 mb-0">Reference Statistics</h3>
                        <button class="btn btn-sm btn-outline-pro" @click="saveReferenceStats"><i class="bi bi-download"></i></button>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover align-middle custom-table small border">
                            <thead>
                                <tr>
                                    <th v-for="key in Object.keys(subtractPage.referenceStats[0])" :key="key">
                                        <span v-if="key !== 'index'">{{ key }}</span>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(row, rowIdx) in subtractPage.referenceStats" :key="rowIdx">
                                    <td v-for="(val, key) in row" :key="key" :class="{'text-end font-monospace': key !== 'index'}">
                                        {{ typeof val === 'number' ? val.toFixed(4) : val }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-lg-6" v-if="subtractPage.monitoringStats">
                <div class="card-pro content-card h-100">
                    <div class="d-flex align-items-center justify-content-between mb-3 border-bottom pb-2">
                        <h3 class="h5 mb-0">Monitoring Statistics</h3>
                        <button class="btn btn-sm btn-outline-pro" @click="saveMonitoringStats"><i class="bi bi-download"></i></button>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover align-middle custom-table small border">
                            <thead>
                                <tr>
                                    <th v-for="key in Object.keys(subtractPage.monitoringStats[0])" :key="key">
                                        <span v-if="key !== 'index'">{{ key }}</span>
                                    </th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(row, rowIdx) in subtractPage.monitoringStats" :key="rowIdx">
                                    <td v-for="(val, key) in row" :key="key" :class="{'text-end font-monospace': key !== 'index'}">
                                        {{ typeof val === 'number' ? val.toFixed(4) : val }}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import NextButton from "../NextButton.vue";
import BackButton from "../BackButton.vue";
import LogoLine from "../LogoLine.vue";
import InputLoader from "../InputLoader.vue";
import Tooltip from "../Tooltip.vue";
import OutputLoader from "../OutputLoader.vue";

export default {
    components: {
        NextButton,
        BackButton,
        LogoLine,
        InputLoader,
        Tooltip,
        OutputLoader,
    },
    props: {
        skipUq: { type: Boolean, default: false },
        variablePage: { type: Object, required: true },
        subtractPage: { type: Object, required: true },
        socket: { type: Object, required: true },
        changePage: { type: Function, required: true },
        sendInChunks: { type: Function, required: true },
    },
    data() {
        return {
            features_file: null,
            labels_file: null,
            isAnalyzing: false,
            isSavingSubtracted: false,
        };
    },
    methods: {
        loadInput(event) {
            this.sendInChunks(event, "load_subtract_input", this.socket);
        },
        loadOutput(event) {
            this.sendInChunks(event, "load_subtract_output", this.socket);
        },
        subtract() {
            this.isAnalyzing = true;
            this.$emit("set-loading", true);
            this.socket.emit("threshold_exceed", {
                selected_features: this.subtractPage.selectedFeatures,
                threshold: this.subtractPage.threshold,
            });
        },
        saveSubtracted() {
            this.isSavingSubtracted = true;
            this.socket.emit("save_subtracted_data");
        },
        saveReferenceStats() { this.socket.emit("save_reference_stats"); },
        saveMonitoringStats() { this.socket.emit("save_monitoring_stats"); },
    },
    mounted() {
        this.socket.on("subtracted_data", (csvData) => {
            this.isSavingSubtracted = false;
            const blob = new Blob([csvData], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "subtracted_data.csv";
            a.click();
            URL.revokeObjectURL(url);
        });
        this.socket.on("reference_stats", (csvData) => {
            const blob = new Blob([csvData], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "reference_statistics.csv";
            a.click();
            URL.revokeObjectURL(url);
        });
        this.socket.on("monitoring_stats", (csvData) => {
            const blob = new Blob([csvData], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "monitoring_statistics.csv";
            a.click();
            URL.revokeObjectURL(url);
        });
        this.socket.on("features_loaded", (data) => { this.features_file = data.filename; });
        this.socket.on("labels_loaded", (data) => { this.labels_file = data.filename; });
        this.socket.on("subtract_data", () => { this.isAnalyzing = false; });
        this.socket.on("error", () => {
            this.isAnalyzing = false;
            this.isSavingSubtracted = false;
        });
    },
    beforeUnmount() {
        this.socket.off("subtracted_data");
        this.socket.off("reference_stats");
        this.socket.off("monitoring_stats");
        this.socket.off("features_loaded");
        this.socket.off("labels_loaded");
    },
};
</script>

<style scoped>
.threshold-exceedance-page {
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

.bg-light-danger {
    background-color: rgba(220, 53, 69, 0.05);
}

.bg-light-success {
    background-color: rgba(25, 135, 84, 0.05);
}

.font-monospace {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.9em;
}

.custom-table thead th {
    background-color: var(--secondary);
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--text-muted);
}

.btn-spinner {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid rgba(127, 127, 127, 0.35);
    border-top-color: currentColor;
    animation: btn-spin 0.7s linear infinite;
    display: inline-block;
}

@keyframes btn-spin {
    to { transform: rotate(360deg); }
}
</style>
