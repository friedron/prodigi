<template>
    <div class="uq-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'surrogate'" :changePage="changePage" />

        <!-- Mode Switcher -->
        <div class="mode-switcher d-flex justify-content-center mb-4 mt-4">
            <div class="btn-group p-1 bg-light rounded-pill border shadow-sm">
                <button 
                    class="btn rounded-pill px-4" 
                    :class="uqPage.mode === 'global' ? 'btn-primary' : 'btn-light'"
                    @click="uqPage.mode = 'global'; uqPage.selectedQoI = null;"
                >
                    <i class="bi bi-globe2 me-2"></i>Global Sensitivities
                </button>
                <button 
                    class="btn rounded-pill px-4" 
                    :class="uqPage.mode === 'local' ? 'btn-primary' : 'btn-light'"
                    @click="uqPage.mode = 'local'; uqPage.selectedQoI = null;"
                >
                    <i class="bi bi-geo-alt me-2"></i>Local Sensitivities
                </button>
            </div>
        </div>

        <!-- GLOBAL SENSITIVITIES MODE -->
        <div v-if="uqPage.mode === 'global'" class="mode-container">
            <!-- Moments Section -->
            <div class="card-pro content-card mb-4">
                <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-calculator fs-4 me-2 text-primary"></i>
                        <h2 class="h4 mb-0">Computation of Moments and Sensitivities</h2>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn-pro" @click="computeMeanVar" :disabled="isLoading">
                            <span v-if="isLoading" class="btn-spinner"></span>
                            <i v-else class="bi bi-play-fill"></i>
                            {{ isLoading ? "Computing…" : "Compute" }}
                        </button>
                        <button v-if="uqPage.mean.length > 0" class="btn-pro btn-outline-pro" @click="saveMeanVar">
                            <i class="bi bi-download"></i> Export
                        </button>
                    </div>
                </div>

                <div v-if="uqPage.mean.length > 0" class="table-responsive">
                    <table class="table table-hover align-middle custom-table bg-white border">
                        <thead>
                            <tr>
                                <th>Quantity of Interest</th>
                                <th class="text-end">Mean Value</th>
                                <th class="text-end">Variance</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(row, index) in surrogatePage.outputQoI" :key="index">
                                <td class="fw-bold">{{ row }}</td>
                                <td class="text-end font-monospace">{{ uqPage.mean[index]?.toFixed(4) }}</td>
                                <td class="text-end font-monospace">{{ uqPage.variance[index]?.toFixed(4) }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-else class="text-center py-4 text-muted bg-light rounded border border-dashed">
                    Click "Compute" to analyze mean and variance values.
                </div>
            </div>

            <!-- Sobol Sensitivities Section -->
            <div class="card-pro content-card mb-4">
                <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-bar-chart-steps fs-4 me-2 text-primary"></i>
                        <h2 class="h4 mb-0">Sobol Sensitivities</h2>
                    </div>
                    <div class="d-flex gap-3 align-items-center">
                        <div class="d-flex align-items-center gap-2">
                            <label class="small fw-bold text-muted text-uppercase mb-0">Max Order</label>
                            <input type="number" class="form-control form-control-sm" style="width: 70px" v-model="uqPage.maxOrder" />
                        </div>
                        <button class="btn-pro" @click="computeSobol" :disabled="isLoading">
                            <span v-if="isLoading" class="btn-spinner"></span>
                            <i v-else class="bi bi-lightning-fill"></i>
                            {{ isLoading ? "Running…" : "Run Analysis" }}
                        </button>
                        <button v-if="hasSobolData" class="btn-pro btn-outline-pro" @click="saveSobol">
                            <i class="bi bi-download"></i> Export
                        </button>
                    </div>
                </div>

                <div v-if="hasSobolData" class="row g-4">
                    <div class="col-12">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover align-middle custom-table border">
                                <caption class="caption-top fw-bold text-primary px-2">Partial Variance</caption>
                                <thead>
                                    <tr>
                                        <th>QoI</th>
                                        <th v-for="(param, key) in uqPage.sensitivities.partialVariance" :key="key" class="text-end">{{ key }}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="(row, index) in surrogatePage.outputQoI" :key="'pv-' + index">
                                        <td class="fw-bold">{{ row }}</td>
                                        <td v-for="(column, key) in uqPage.sensitivities.partialVariance" :key="key" class="text-end font-monospace">
                                            {{ column[row].toFixed(4) }}
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="col-12">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover align-middle custom-table border">
                                <caption class="caption-top fw-bold text-primary px-2">Sobol Indices (Main Effects)</caption>
                                <thead>
                                    <tr>
                                        <th>QoI</th>
                                        <th v-for="(param, key) in uqPage.sensitivities.sobolIndex" :key="key" class="text-end">{{ key }}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="(row, index) in surrogatePage.outputQoI" :key="'si-' + index">
                                        <td class="fw-bold">{{ row }}</td>
                                        <td v-for="(column, key) in uqPage.sensitivities.sobolIndex" :key="key" class="text-end font-monospace">
                                            {{ column[row].toFixed(4) }}
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <div v-if="uqPage.sobolPlot" class="plot-container mt-4">
                    <img class="img-fluid plot-img" :src="uqPage.sobolPlot" />
                </div>
                <div v-else-if="!hasSobolData" class="text-center py-4 text-muted bg-light rounded border border-dashed">
                    Configure Max Order and run Sobol sensitivity analysis.
                </div>
            </div>

            <!-- SHAP Values Section -->
            <div class="card-pro content-card mb-4">
                <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-pie-chart fs-4 me-2 text-primary"></i>
                        <h2 class="h4 mb-0">SHAP Explanations</h2>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn-pro" @click="computeAvgShap" :disabled="isLoading">
                            <span v-if="isLoading" class="btn-spinner"></span>
                            <i v-else class="bi bi-cpu"></i>
                            {{ isLoading ? "Computing…" : "Compute SHAP" }}
                        </button>
                        <button v-if="hasShapData" class="btn-pro btn-outline-pro" @click="saveShap">
                            <i class="bi bi-download"></i> Export
                        </button>
                    </div>
                </div>

                <div v-if="hasShapData" class="table-responsive">
                    <table class="table table-sm table-hover align-middle custom-table border">
                        <caption class="caption-top fw-bold text-primary px-2">Average SHAP Values (Global Importance)</caption>
                        <thead>
                            <tr>
                                <th>QoI</th>
                                <th v-for="param in surrogatePage.selectedFeats" :key="param" class="text-end">{{ param }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(row, index) in surrogatePage.outputQoI" :key="'shap-' + index">
                                <td class="fw-bold">{{ row }}</td>
                                <td v-for="(value, sIdx) in uqPage.shap[index]" :key="sIdx" class="text-end font-monospace">
                                    {{ Number(value).toPrecision(4) }}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div v-if="uqPage.shapPlot" class="plot-container mt-4">
                    <img class="img-fluid plot-img" :src="uqPage.shapPlot" />
                </div>
                <div v-else-if="!hasShapData" class="text-center py-4 text-muted bg-light rounded border border-dashed">
                    Run SHAP analysis to determine individual parameter contributions.
                </div>
            </div>

            <!-- Single QoI Deep Dive -->
            <div class="card-pro content-card mb-4 border-primary shadow-sm">
                <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                    <i class="bi bi-zoom-in fs-4 me-2 text-primary"></i>
                    <h2 class="h4 mb-0">Detailed QoI Analysis</h2>
                </div>

                <div class="row g-3 align-items-end mb-4">
                    <div class="col-md-6">
                        <label class="form-label fw-bold">Select target for deep analysis</label>
                        <select v-model="uqPage.selectedQoI" class="form-select">
                            <option v-for="(name, index) in surrogatePage.outputQoI" :key="index" :value="{ name, index }">
                                {{ name }}
                            </option>
                        </select>
                    </div>
                    <div class="col-md-6 d-flex gap-2">
                        <button class="btn-pro flex-grow-1" :disabled="!uqPage.selectedQoI || isLoading" @click="computeShapBeeswarm">
                            <span v-if="isLoading" class="btn-spinner"></span>
                            <i v-else class="bi bi-grid-3x3"></i>
                            SHAP Beeswarm
                        </button>
                        <button class="btn-pro flex-grow-1" :disabled="!uqPage.selectedQoI || isLoading" @click="computeSobolSingle">
                            <span v-if="isLoading" class="btn-spinner"></span>
                            <i v-else class="bi bi-circle-square"></i>
                            Sobol Single
                        </button>
                    </div>
                </div>

                <div class="row g-3">
                    <div v-if="uqPage.beeswarmPlot" class="col-md-6">
                        <div class="plot-container p-2 border">
                            <img class="img-fluid plot-img" :src="uqPage.beeswarmPlot" />
                        </div>
                    </div>
                    <div v-if="uqPage.sobolPlotSingle" class="col-md-6">
                        <div class="plot-container p-2 border">
                            <img :src="uqPage.sobolPlotSingle" class="img-fluid plot-img" />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- LOCAL SENSITIVITIES MODE -->
        <div v-if="uqPage.mode === 'local'" class="mode-container">
            <div class="card-pro content-card mb-4">
                <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom">
                    <div class="d-flex align-items-center">
                        <i class="bi bi-pin-map fs-4 me-2 text-primary"></i>
                        <h2 class="h4 mb-0">Point Prediction & Attribution</h2>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn-pro" @click="computeSingle" :disabled="isLoading">
                            <span v-if="isLoading" class="btn-spinner"></span>
                            <i v-else class="bi bi-play-circle"></i>
                            {{ isLoading ? "Predicting…" : "Run Prediction" }}
                        </button>
                        <button v-if="uqPage.prediction.length > 0" class="btn-pro btn-outline-pro" @click="savePred">
                            <i class="bi bi-download"></i> Save Results
                        </button>
                    </div>
                </div>

                <p class="text-muted">Enter specific parameter values to predict system response and analyze local feature contributions.</p>
                
                <div class="row g-3 mb-4 p-3 bg-light rounded border">
                    <div v-for="(param, index) in surrogatePage.selectedFeats" :key="param" class="col-md-4 col-lg-3">
                        <label class="form-label small fw-bold text-muted mb-1">{{ param }}</label>
                        <input type="number" class="form-control" v-model="uqPage.paramValues[index]" />
                    </div>
                </div>

                <div v-if="uqPage.shapPlotMulti" class="plot-container mb-4">
                    <img :src="uqPage.shapPlotMulti" class="img-fluid plot-img" />
                </div>

                <div v-if="uqPage.prediction.length > 0" class="border-top pt-4">
                    <div class="d-flex align-items-center justify-content-between mb-3">
                        <h3 class="h5 mb-0">Results for Single QoI</h3>
                        <div class="d-flex align-items-center gap-2" style="width: 300px">
                            <label class="small fw-bold text-muted mb-0">Analysis Target</label>
                            <select v-model="uqPage.selectedQoI" class="form-select form-select-sm" @change="selectQoI">
                                <option v-for="(name, index) in surrogatePage.outputQoI" :key="index" :value="{ name, index }">
                                    {{ name }}
                                </option>
                            </select>
                        </div>
                    </div>

                    <div v-if="uqPage.selectedQoI" class="row g-4">
                        <div class="col-md-6">
                            <div class="table-responsive border rounded bg-white p-3 shadow-sm">
                                <table class="table table-sm mb-0">
                                    <thead>
                                        <tr>
                                            <th>Metric</th>
                                            <th class="text-end">Predicted Value</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td class="fw-bold">Mean Response</td>
                                            <td class="text-end font-monospace text-primary fw-bold" v-if="uqPage.mean[uqPage.selectedQoI.index]">
                                                {{ uqPage.mean[uqPage.selectedQoI.index].toFixed(4) }}
                                            </td>
                                        </tr>
                                        <tr>
                                            <td class="fw-bold">Variance</td>
                                            <td class="text-end font-monospace" v-if="uqPage.variance[uqPage.selectedQoI.index]">
                                                {{ uqPage.variance[uqPage.selectedQoI.index].toFixed(4) }}
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="col-12" v-if="uqPage.shapPlotSingle">
                            <div class="plot-container">
                                <img :src="uqPage.shapPlotSingle" class="img-fluid plot-img" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <NextButton
            :nextPage="mode === 'surrogate' ? 'measurements' : 'subtract'"
            :available="true"
            :changePage="changePage"
        />
    </div>
</template>

<script>
import NextButton from "./NextButton.vue";
import BackButton from "./BackButton.vue";
import LogoLine from "./LogoLine.vue";

export default {
    components: {
        NextButton,
        BackButton,
        LogoLine,
    },
    props: {
        paramPage: { type: Object, required: true },
        surrogatePage: { type: Object, required: true },
        uqPage: { type: Object, required: true },
        mode: { type: String, required: true },
        socket: { type: Object, required: true },
        changePage: { type: Function, required: true },
        // Mirrors App.vue's own isLoading, which its socket handlers for
        // mean_var/sobol/shap/predict/etc already clear at the precise
        // moment each response lands - reusing it here (rather than the
        // generic activity-based indicator) keeps these buttons accurate
        // for slow compute with no in-between socket chatter.
        isLoading: { type: Boolean, default: false },
    },
    computed: {
        hasSobolData() {
            return this.uqPage.sensitivities.partialVariance && 
                   Object.keys(this.uqPage.sensitivities.partialVariance).length > 0;
        },
        hasShapData() {
            return this.uqPage.shap && Object.keys(this.uqPage.shap).length > 0;
        }
    },
    methods: {
        computeMeanVar() {
            this.socket.emit("mean_var");
        },
        saveMeanVar() {
            try {
                const paramNames = Object.keys(this.paramPage.qoiTable);
                const meanVarData = paramNames.map((name, index) => ({
                    parameter: name,
                    mean: this.uqPage.mean[index] || null,
                    variance: this.uqPage.variance[index] || null,
                }));
                const data = JSON.stringify(meanVarData, null, 2);
                const blob = new Blob([data], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = "mean_variance.json";
                link.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                console.log("Error saving mean/variance file: ", error);
            }
        },
        computeSobol() {
            this.setLoading(true);
            this.socket.emit("sobol", this.uqPage.maxOrder);
        },
        computeSobolSingle() {
            if (!this.uqPage.selectedQoI) {
                alert("Please select QoI first");
                return;
            }
            this.setLoading(true);
            this.socket.emit("sobol_single", this.uqPage.selectedQoI.name);
        },
        saveSobol() {
            try {
                const data = JSON.stringify({
                    partialVariance: this.uqPage.sensitivities.partialVariance,
                    sobolIndex: this.uqPage.sensitivities.sobolIndex
                }, null, 2);
                const blob = new Blob([data], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = "sensitivities.json";
                link.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                console.log("Error saving sensitivities: ", error);
            }
        },
        computeAvgShap() {
            this.setLoading(true);
            this.socket.emit("shap");
        },
        saveShap() {
            try {
                const data = JSON.stringify(this.uqPage.shap, null, 2);
                const blob = new Blob([data], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = "shap.json";
                link.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                console.log("Error saving shap file: ", error);
            }
        },
        computeShapBeeswarm() {
            if (!this.uqPage.selectedQoI) {
                alert("Please select QoI first");
                return;
            }
            this.setLoading(true);
            this.socket.emit("shap_beeswarm", this.uqPage.selectedQoI.name);
        },
        computeWaterFallMulti() {
            this.setLoading(true);
            this.socket.emit("waterfall_multi", this.uqPage.paramValues);
        },
        computeWaterfallSingle() {
            this.setLoading(true);
            this.socket.emit("waterfall_single", {
                "qoi": this.uqPage.selectedQoI.name,
                "values": this.uqPage.paramValues,
            });
        },
        computePred() {
            this.setLoading(true);
            this.socket.emit("predict", this.uqPage.paramValues);
        },
        savePred() {
            try {
                const data = JSON.stringify(this.uqPage.prediction, null, 2);
                const blob = new Blob([data], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = "prediction.json";
                link.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                console.log("Error saving prediction file: ", error);
            }
        },
        selectQoI() {
            if (this.validateParmValues()) {
                this.computePredSingle();
                this.computeWaterfallSingle();
            } else {
                this.uqPage.selectedQoI = null;
            }
        },
        computePredSingle() {
            this.setLoading(true);
            this.socket.emit("predict_single", this.uqPage.selectedQoI.name, this.uqPage.paramValues);
        },
        computeSingle() {
            if (this.validateParmValues()) {
                this.computePred();
                this.computeWaterFallMulti();
            }
        },
        validateParmValues() {
            if (
                this.uqPage.paramValues.length !== this.surrogatePage.selectedFeats.length ||
                this.uqPage.paramValues.includes(undefined) ||
                this.uqPage.paramValues.includes("")
            ) {
                alert("Please fill all the values");
                return false;
            }
            return true;
        },
        setLoading(value) {
            this.$emit("set-loading", value);
        },
    }
};
</script>

<style scoped>
.uq-page {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
}

.btn-primary {
    background-color: var(--primary);
    border-color: var(--primary);
    color: white;
}

.btn-primary:hover {
    background-color: var(--primary-hover);
    border-color: var(--primary-hover);
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

.border-dashed {
    border-style: dashed !important;
    border-width: 2px !important;
}

.font-monospace {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.9em;
}

.caption-top {
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
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
