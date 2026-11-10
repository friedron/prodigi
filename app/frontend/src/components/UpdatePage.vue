<template>
    <div class="update-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
            :logos="[
                { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                { src: '/logos/hs_logo.png', alt: 'HS Logo' },
            ]"
        />
        </div>

        <BackButton :prevPage="'measurements'" :changePage="changePage" />

        <!-- MCMC Configuration Card -->
        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-gear-wide-connected fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">MCMC Configuration</h2>
            </div>
            
            <p class="text-muted mb-4">Set the parameters for the Markov Chain Monte Carlo (MCMC) Bayesian update process.</p>

            <div class="row g-4 align-items-end">
                <div class="col-md-3">
                    <label for="nwalkers" class="form-label fw-bold small text-uppercase text-muted">Number of Walkers</label>
                    <input id="nwalkers" type="number" class="form-control" v-model="updatePage.data.nwalkers" />
                </div>
                <div class="col-md-3">
                    <label for="nburn" class="form-label fw-bold small text-uppercase text-muted">Number of Burn</label>
                    <input id="nburn" type="number" class="form-control" v-model="updatePage.data.nburn" />
                </div>
                <div class="col-md-3">
                    <label for="niter" class="form-label fw-bold small text-uppercase text-muted">Number of Iterations</label>
                    <input id="niter" type="number" class="form-control" v-model="updatePage.data.niter" />
                </div>
                <div class="col-md-3">
                    <button class="btn-pro w-100 py-2" @click="update" :disabled="isLoading">
                        <span v-if="isLoading" class="btn-spinner me-2"></span>
                        <i v-else class="bi bi-play-circle-fill me-2"></i>
                        {{ isLoading ? "Running…" : "Run Bayesian Update" }}
                    </button>
                </div>
            </div>

            <div v-if="updatePage.mcmcProgress" class="mt-4">
                <div class="d-flex justify-content-between small text-muted mb-1">
                    <span v-if="updatePage.mcmcProgress.phase === 'starting'">Starting MCMC…</span>
                    <span v-else>
                        {{ updatePage.mcmcProgress.phase === 'burn-in' ? 'Burn-in' : 'Sampling' }}:
                        step {{ updatePage.mcmcProgress.step }} / {{ updatePage.mcmcProgress.total }}
                    </span>
                    <span v-if="updatePage.mcmcProgress.fraction >= 1">Computing posterior statistics…</span>
                    <span v-else>{{ Math.round(updatePage.mcmcProgress.fraction * 100) }}%</span>
                </div>
                <div
                    class="progress"
                    role="progressbar"
                    aria-label="MCMC progress"
                    :aria-valuenow="Math.round(updatePage.mcmcProgress.fraction * 100)"
                    aria-valuemin="0"
                    aria-valuemax="100"
                >
                    <div
                        class="progress-bar mcmc-progress-bar"
                        :class="{ 'progress-bar-striped progress-bar-animated': updatePage.mcmcProgress.fraction >= 1 }"
                        :style="{ width: (updatePage.mcmcProgress.fraction * 100) + '%' }"
                    ></div>
                </div>
            </div>
        </div>

        <!-- Multi-Model Selection Card -->
        <div v-if="mode === 'multiModel'" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-layers-half fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Model Selection</h2>
            </div>
            
            <div v-if="updateDone" class="row align-items-end">
                <div class="col-md-8">
                    <label class="form-label fw-bold small text-uppercase text-muted">Select Model to Analyze</label>
                    <select v-model="selectedModel" class="form-select">
                        <option v-for="(model, index) in Object.keys(uploadPage.models)" :key="index" :value="index">
                            {{ model }}
                        </option>
                    </select>
                </div>
                <div class="col-md-4">
                    <button class="btn-pro btn-outline-pro w-100 py-2" @click="getDataForModel" :disabled="selectedModel === null || isLoading">
                        <span v-if="isLoading" class="btn-spinner me-2"></span>
                        <i v-else class="bi bi-search me-2"></i>
                        {{ isLoading ? "Loading…" : "Get Model Data" }}
                    </button>
                </div>
            </div>
            <div v-else class="text-center py-4">
                <p class="text-muted mb-0 italic">Run the update process above to enable model selection.</p>
            </div>
        </div>

        <!-- Results Analysis Card -->
        <div v-if="updatePage.map || updatePage.mcmcPlot" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-bar-chart-line fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Posterior Analysis</h2>
            </div>

            <div v-if="updatePage.mcmcPlot" class="plot-container mb-5">
                <img :src="updatePage.mcmcPlot" class="img-fluid plot-img" alt="MCMC Plot" />
            </div>

            <div v-if="updatePage.mcmcAnimation || updatePage.mcmcAnimationPending || updatePage.mcmcAnimationError" class="mb-5">
                <h5 class="small text-uppercase fw-bold text-muted mb-3">MCMC Random Walk</h5>
                <div v-if="updatePage.mcmcAnimation" class="plot-container">
                    <video
                        :src="updatePage.mcmcAnimation"
                        class="plot-img mcmc-video"
                        controls autoplay loop muted playsinline
                    ></video>
                </div>
                <div v-else-if="updatePage.mcmcAnimationPending" class="d-flex align-items-center gap-2 text-muted">
                    <span class="btn-spinner"></span> Rendering animation…
                </div>
                <div v-else class="alert alert-warning mb-0">
                    The animation could not be rendered: {{ updatePage.mcmcAnimationError }}
                </div>
                <div v-if="updatePage.mcmcAnimation" class="mt-2 text-end">
                    <a :href="updatePage.mcmcAnimation" download="mcmc_walk.mp4" class="btn btn-sm btn-outline-secondary">
                        <i class="bi bi-download me-1"></i> Download MP4
                    </a>
                </div>
            </div>

            <div v-if="updatePage.map" class="row g-4">
                <!-- Mean Table -->
                <div v-if="updatePage.mean" class="col-lg-4">
                    <h5 class="small text-uppercase fw-bold text-muted mb-3">Mean Distribution</h5>
                    <div class="table-responsive">
                        <table class="table table-hover border custom-table">
                            <thead>
                                <tr>
                                    <th>Param</th>
                                    <th class="text-end">Mean</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(row, index) in updatePage.mean" :key="'mean-'+index">
                                    <td class="fw-bold">{{ index }}</td>
                                    <td class="text-end font-monospace text-primary">{{ row[0].toFixed(4) }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- MAP Table -->
                <div v-if="updatePage.map" class="col-lg-4">
                    <h5 class="small text-uppercase fw-bold text-muted mb-3">Estimated MAP</h5>
                    <div class="table-responsive">
                        <table class="table table-hover border custom-table">
                            <thead>
                                <tr>
                                    <th>Param</th>
                                    <th class="text-end">MAP</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(row, index) in updatePage.map" :key="'map-'+index">
                                    <td class="fw-bold">{{ index }}</td>
                                    <td class="text-end font-monospace text-primary">{{ row[0].toFixed(4) }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Variance Table -->
                <div v-if="updatePage.variance" class="col-lg-4">
                    <h5 class="small text-uppercase fw-bold text-muted mb-3">Variance Distribution</h5>
                    <div class="table-responsive">
                        <table class="table table-hover border custom-table">
                            <thead>
                                <tr>
                                    <th>Param</th>
                                    <th class="text-end">Variance</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="(row, index) in updatePage.variance" :key="'var-'+index">
                                    <td class="fw-bold">{{ index }}</td>
                                    <td class="text-end font-monospace text-primary">{{ row[0].toFixed(4) }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Export Card -->
        <div v-if="updatePage.map" class="card-pro content-card mb-5">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-cloud-download fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Export Results</h2>
            </div>
            
            <div class="d-flex flex-wrap gap-3">
                <OutputLoader
                    :title="'Export Posterior Statistics'"
                    :loading="savingStatistics"
                    @save-file="saveStatistics"
                />
                <OutputLoader
                    :title="'Export Posterior Samples'"
                    :loading="savingSamples"
                    @save-file="savePostSamples"
                />
            </div>
        </div>
    </div>
</template>

<script>
import BackButton from "./BackButton.vue";
import LogoLine from "./LogoLine.vue";
import OutputLoader from "./OutputLoader.vue";

export default {
    components: {
        BackButton,
        LogoLine,
        OutputLoader,
    },
    props: {
        uploadPage: { type: Object, required: true },
        updatePage: { type: Object, required: true },
        mode: { type: String, required: true },
        socket: { type: Object, required: true },
        changePage: { type: Function, required: true },
        // Mirrors App.vue's own isLoading, which the "update"/"update_multi"
        // socket handlers clear at the precise moment each response lands -
        // reusing it here (rather than the generic activity-based indicator)
        // keeps this button accurate for a slow MCMC run with no in-between
        // socket chatter.
        isLoading: { type: Boolean, default: false },
    },
    data() {
        return {
            updateDone: false,
            selectedModel: null,
            stats: {
                MAP: {},
                mean: {},
                variance: {},
            },
            savingStatistics: false,
            savingSamples: false,
        };
    },
    methods: {
        update() {
            this.$emit("set-loading", true);
            this.updatePage.mcmcProgress = { phase: "starting", fraction: 0 };
            if (this.mode === "multiModel") {
                this.socket.emit("update_multi", this.updatePage.data);
            } else {
                this.socket.emit("update", this.updatePage.data);
            }
        },
        savePostSamples() {
            this.savingSamples = true;
            this.socket.emit("get_posterior_samples");
        },
        saveStatistics() {
            this.savingStatistics = true;
            this.socket.emit("get_posterior_statistics");
        },
        getDataForModel() {
            this.$emit("set-loading", true);
            this.socket.emit("get_multi_data", { index: this.selectedModel });
        },
    },
    mounted() {
        this.socket.on("posterior_samples", (data) => {
            this.savingSamples = false;
            const blob = new Blob([data], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "posterior_samples.csv";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        });
        this.socket.on("update_done", () => {
            this.updatePage.mcmcProgress = null;
            this.$emit("set-loading", false);
            this.updateDone = true;
        });
        this.socket.on("posterior_statistics", (data) => {
            this.savingStatistics = false;
            const blob = new Blob([data], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "posterior_statistics.csv";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        });
        this._errorHandler = () => {
            this.updatePage.mcmcProgress = null;
            this.savingSamples = false;
            this.savingStatistics = false;
        };
        this.socket.on("error", this._errorHandler);
    },
    beforeUnmount() {
        this.socket.off("posterior_samples");
        this.socket.off("update_done");
        this.socket.off("posterior_statistics");
        this.socket.off("error", this._errorHandler);
    }
};
</script>

<style scoped>
.update-page {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
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
    max-height: 600px;
    object-fit: contain;
}

.mcmc-video {
    max-width: 100%;
}

.mcmc-progress-bar {
    background-color: var(--primary);
    transition: width 0.2s ease;
}

.custom-table thead th {
    background-color: var(--secondary);
    font-size: 0.75rem;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 0.75rem;
}

.custom-table tbody td {
    padding: 0.75rem;
}

.font-monospace {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.9em;
}

.form-control:focus, .form-select:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(163, 0, 54, 0.1);
}

.italic {
    font-style: italic;
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