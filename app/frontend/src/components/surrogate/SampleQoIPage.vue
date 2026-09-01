<template>
    <div class="sample-qoi-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'variables'" :changePage="changePage" />

        <!-- MOSAIC Training Data Card -->
        <div v-if="mode === 'mosaic'" class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-file-earmark-binary fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">MOSAIC Training Data</h2>
            </div>
            <p class="text-muted small">
                Upload the pre-computed FE analysis results as <code>.npy</code> files, matching the reference notebook workflow.
                Define variables (previous page) in the same column order as <code>parameters.npy</code>.
            </p>

            <div class="row g-3">
                <div class="col-md-4">
                    <label class="form-label fw-bold d-block">Parameters</label>
                    <label for="mosaicParams" class="btn-pro btn-sm btn-outline-pro mb-2">
                        <i class="bi bi-upload"></i> Load parameters.npy
                        <input type="file" id="mosaicParams" @change="loadMosaicParameters" accept=".npy" class="d-none" />
                    </label>
                    <div class="small text-muted">
                        {{ variablePage.mosaic.parametersShape ? `Shape: (${variablePage.mosaic.parametersShape.join(", ")})` : "Not loaded" }}
                    </div>
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold d-block">Frequencies</label>
                    <label for="mosaicFreqs" class="btn-pro btn-sm btn-outline-pro mb-2">
                        <i class="bi bi-upload"></i> Load frequencies.npy
                        <input type="file" id="mosaicFreqs" @change="loadMosaicFrequencies" accept=".npy" class="d-none" />
                    </label>
                    <div class="small text-muted">
                        {{ variablePage.mosaic.frequenciesShape ? `Shape: (${variablePage.mosaic.frequenciesShape.join(", ")})` : "Not loaded" }}
                    </div>
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold d-block">Eigenvectors</label>
                    <label for="mosaicEigvecs" class="btn-pro btn-sm btn-outline-pro mb-2">
                        <i class="bi bi-upload"></i> Load eigenvectors.npy
                        <input type="file" id="mosaicEigvecs" @change="loadMosaicEigenvectors" accept=".npy" class="d-none" />
                    </label>
                    <div class="small text-muted">
                        {{ variablePage.mosaic.eigenvectorsShape ? `Shape: (${variablePage.mosaic.eigenvectorsShape.join(", ")})` : "Not loaded" }}
                    </div>
                </div>
            </div>
        </div>

        <!-- Sampling Configuration Card -->
        <div v-else class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom">
                <div class="d-flex align-items-center">
                    <i class="bi bi-dice-5 fs-4 me-2 text-primary"></i>
                    <h2 class="h4 mb-0">Sampling Configuration</h2>
                </div>
                <div class="d-flex gap-2">
                    <label for="sampleSettings" class="btn-pro btn-sm btn-outline-pro mb-0">
                        <i class="bi bi-upload"></i> Settings
                        <input type="file" id="sampleSettings" @change="loadSampleSettings" accept=".json" class="d-none" />
                    </label>
                    <label for="sampleInput" class="btn-pro btn-sm btn-outline-pro mb-0">
                        <i class="bi bi-file-earmark-spreadsheet"></i> Samples
                        <input type="file" id="sampleInput" @change="loadSample" accept=".csv" class="d-none" />
                    </label>
                </div>
            </div>

            <div class="row g-3">
                <div class="col-md-4">
                    <label class="form-label fw-bold">Sampling Method</label>
                    <select id="sampleMethod" class="form-select" v-model="variablePage.data.sampleMethod">
                        <option :value="null" selected disabled hidden>Choose Method</option>
                        <option value="MC">Monte Carlo</option>
                        <option value="QMC_Halton">QMC Halton</option>
                        <option value="QMC_LHS">QMC LHS</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold">Number of Samples</label>
                    <input id="numSamples" type="number" class="form-control" v-model.number="variablePage.data.numSamples" placeholder="Enter count" />
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold">Random Seed (Optional)</label>
                    <input id="randomSeed" type="number" class="form-control" placeholder="Random" v-model.number="variablePage.data.randomSeed" />
                </div>
            </div>

            <div class="mt-4 pt-3 border-top d-flex justify-content-center gap-3">
                <button class="btn-pro px-5" @click="sample" :disabled="loadingState.active">
                    <span v-if="loadingState.active" class="btn-spinner"></span>
                    <i v-else class="bi bi-play-fill"></i>
                    {{ loadingState.active ? "Sampling…" : "Run Sampling" }}
                </button>
                <button v-if="variablePage.samples.length > 0" class="btn-pro btn-outline-pro" @click="saveSample">
                    <i class="bi bi-download"></i> Save Results
                </button>
            </div>
        </div>

        <!-- QoI Card -->
        <div v-if="mode !== 'mosaic'" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom">
                <div class="d-flex align-items-center">
                    <i class="bi bi-bar-chart-steps fs-4 me-2 text-primary"></i>
                    <h2 class="h4 mb-0">Quantity of Interest (QoI)</h2>
                </div>
                <label for="qoiInput" class="btn-pro btn-sm mb-0">
                    <i class="bi bi-upload"></i> Load QoI CSV
                    <input type="file" id="qoiInput" @change="loadQoi" accept=".csv" class="d-none" />
                </label>
            </div>

            <div v-if="Object.keys(variablePage.qoiTable).length > 0" class="table-responsive">
                <table class="table-custom table-hover align-middle custom-table border">
                    <thead>
                        <tr>
                            <th>Metric</th>
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
                        <tr v-for="(row, key) in variablePage.qoiTable" :key="key">
                            <td class="fw-bold text-primary">{{ key }}</td>
                            <td class="text-end font-monospace">{{ row.mean.toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row.std ? row.std.toFixed(4) : '-' }}</td>
                            <td class="text-end font-monospace">{{ row.min.toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row["25%"].toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row["50%"].toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row["75%"].toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row.max.toFixed(4) }}</td>
                            <td class="text-end font-monospace text-muted small">{{ row.count }}</td>
                        </tr>
                    </tbody>
                </table>
                <p class="text-muted small mt-3">Summary statistics of samples of QoI.</p>
            </div>
            <div v-else class="text-center py-5 text-muted bg-light rounded border border-dashed">
                <i class="bi bi-table fs-1 d-block mb-3"></i>
                No QoI data loaded. Please upload a CSV file to view statistics.
            </div>
        </div>

        <NextButton
            :nextPage="'exploratory'"
            :available="mode === 'mosaic' ? mosaicDataReady : (variablePage.samples.length > 0 && Object.keys(variablePage.qoiTable).length > 0)"
            :changePage="changePage"
        />
    </div>
</template>

<script>
import NextButton from "../NextButton.vue";
import BackButton from "../BackButton.vue";
import LogoLine from "../LogoLine.vue";
import { loadingState } from "../../loadingState";

export default {
    components: {
        NextButton,
        BackButton,
        LogoLine,
    },
    setup() {
        return { loadingState };
    },
    props: {
        socket: { type: Object, required: true },
        variablePage: { type: Object, required: true },
        mode: { type: String, default: "" },
        changePage: { type: Function, required: true },
        addPageDone: { type: Function, required: true },
        sendInChunks: { type: Function, required: true },
    },
    computed: {
        mosaicDataReady() {
            const m = this.variablePage.mosaic;
            return !!(m && m.parametersShape && m.frequenciesShape && m.eigenvectorsShape);
        },
    },
    watch: {
        variablePage: {
            handler(newVal) {
                if (this.mode === "mosaic") {
                    if (this.mosaicDataReady && newVal.data.variables.length > 0) {
                        this.addPageDone("sample");
                    }
                    return;
                }
                if (
                    newVal.samples.length > 0 &&
                    Object.keys(newVal.qoiTable).length > 0 &&
                    newVal.data.variables.length > 0
                ) {
                    this.addPageDone("sample");
                }
            },
            deep: true,
            immediate: true,
        },
    },
    methods: {
        loadMosaicParameters(event) {
            this.sendInChunks(event.target.files[0], "load_mosaic_parameters", this.socket);
        },
        loadMosaicFrequencies(event) {
            this.sendInChunks(event.target.files[0], "load_mosaic_frequencies", this.socket);
        },
        loadMosaicEigenvectors(event) {
            this.sendInChunks(event.target.files[0], "load_mosaic_eigenvectors", this.socket);
        },
        loadSampleSettings(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = async (loadEvent) => {
                try {
                    const data = JSON.parse(loadEvent.target.result);
                    if (!("sampleMethod" in data)) {
                        console.log("Invalid file format.");
                        return;
                    }
                    this.variablePage.data["sampleMethod"] = data["sampleMethod"];
                    this.variablePage.data["numSamples"] = data["numSamples"];
                    this.variablePage.data["randomSeed"] = data["randomSeed"];
                } catch (error) {
                    console.log("Error: ", error.message);
                }
            };
            reader.readAsText(file);
        },
        loadSample(event) {
            this.sendInChunks(event.target.files[0], "load_sample", this.socket);
        },
        sample() {
            if (this.variablePage.data.sampleMethod !== null && this.variablePage.data.numSamples !== null) {
                this.socket.emit("sample", this.variablePage.data);
            } else {
                alert("Please select a sampling method and enter the number of samples.");
            }
        },
        saveSample() {
            const download = (content, fileName, mimeType) => {
                const blob = new Blob([content], { type: mimeType });
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = fileName;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            };

            try {
                const variableNames = this.variablePage.data.variables.map(v => v.name);
                let csv = variableNames.join(",") + "\n" +
                        this.variablePage.samples.map(row => row.join(",")).join("\n");

                download(csv, "sample.csv", "text/csv");

                setTimeout(() => {
                    const { variables, ...sampleSettings } = this.variablePage.data;
                    download(JSON.stringify(sampleSettings), "sampleSettings.json", "application/json");
                }, 500);

            } catch (error) {
                console.error("Export failed:", error);
            }
        },
        loadQoi(event) {
            this.sendInChunks(event.target.files[0], "qoi_csv", this.socket);
        },
    },
};
</script>

<style scoped>
.sample-qoi-page {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
}

.font-monospace {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.9em;
}

.custom-table thead th {
    background-color: var(--secondary);
    font-size: 0.75rem;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: var(--spacing-md);
    white-space: nowrap;
}

.custom-table tbody td {
    padding: var(--spacing-md);
}

.border-dashed {
    border-style: dashed !important;
}

.text-primary {
    color: var(--primary) !important;
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
