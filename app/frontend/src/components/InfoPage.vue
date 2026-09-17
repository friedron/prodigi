<template>
    <div class="info-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <div class="card-pro content-card">
            
            <div class="description-text mb-5" v-html="descriptions[mode]"></div>

            <div class="action-footer d-flex flex-wrap gap-3 pt-4 border-top">
                <template v-if="mode === 'surrogate' || mode === 'subtracting' || mode === 'mosaic' || mode === 'inverse'">
                    <button class="btn-pro btn-outline-pro" @click="changePage('variables')">
                        <i class="bi bi-plus-circle"></i> Create New Model
                    </button>
                    <button class="btn-pro" @click="changePage('upload')">
                        <i class="bi bi-upload"></i> Upload Existing Model
                    </button>
                </template>

                <template v-if="mode === 'multiModel'">
                    <button class="btn-pro" @click="changePage('upload')">
                        Get Started <i class="bi bi-arrow-right"></i>
                    </button>
                </template>

                <template v-if="mode === 'climateResilience' || mode === 'earthquakeResilience'">
                    <button class="btn-pro btn-outline-pro" @click="openManual">
                        <i class="bi bi-file-earmark-pdf"></i> View Documentation
                    </button>
                    <button class="btn-pro" @click="changePage('input')">
                        Initialize Project <i class="bi bi-arrow-right"></i>
                    </button>
                </template>

                <div class="ms-auto d-flex gap-2">
                    <button v-if="mode === 'subtracting'" class="btn-pro btn-secondary" @click="subtractingDemo" :disabled="demoLoading">
                        <span v-if="demoLoading" class="btn-spinner"></span>
                        <i v-else class="bi bi-play-circle"></i>
                        {{ demoLoading ? "Loading…" : "Run Demo" }}
                    </button>
                    <button v-if="mode === 'surrogate'" class="btn-pro btn-secondary" @click="hybridDemo" :disabled="demoLoading">
                        <span v-if="demoLoading" class="btn-spinner"></span>
                        <i v-else class="bi bi-play-circle"></i>
                        {{ demoLoading ? "Loading…" : "Run Demo" }}
                    </button>
                    <button v-if="mode === 'multiModel'" class="btn-pro btn-secondary" @click="multiModelDemo" :disabled="demoLoading">
                        <span v-if="demoLoading" class="btn-spinner"></span>
                        <i v-else class="bi bi-play-circle"></i>
                        {{ demoLoading ? "Loading…" : "Run Demo" }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import LogoLine from "./LogoLine.vue";

// How long to keep the demo button's own spinner up after the last
// demo-related socket event, independent of the app-wide activity indicator.
const DEMO_DEBOUNCE_MS = 1500;

export default {
    components: { LogoLine },
    props: {
        mode: { type: String, required: true },
        activePage: { type: String, required: true },
        socket: { type: Object, required: true },
        changePage: { type: Function, required: true },
    },
    data() {
        return {
            demoLoading: false,
            titles: {
                subtracting: "Weather Effect Modeling",
                surrogate: "Model Calibration — MCMC (Surrogate-Based)",
                multiModel: "Multi-Building Design Updating",
                mosaic: "MOSAIC Surrogate Modeling",
                earthquakeResilience: "Assessment of Earthquake Resilience",
                climateResilience: "Analyzing Climate Resilience",
            },
            descriptions: {
                surrogate: `
                    <h3>Model Calibration — MCMC (Surrogate-Based)</h3>
                    <p>Create accurate digital twins by combining physics-based models with data-driven surrogate models. This hybrid approach balances computational efficiency with physical accuracy.</p>
                    <ul>
                        <li>Train surrogate models from simulation or real-world data</li>
                        <li>Integrate with existing physics-based models</li>
                        <li>Optimize performance and accuracy trade-offs</li>
                    </ul>
                `,
                subtracting: `
                    <h3>Weather Effect Modeling</h3>
                    <p>Isolate the effects of structural changes by removing weather-related impacts from sensor measurements. This data-driven approach helps identify true structural behavior.</p>
                    <ul>
                        <li>Remove environmental noise from measurements</li>
                        <li>Identify structural anomalies and damage</li>
                        <li>Improve monitoring accuracy</li>
                    </ul>
                `,
                inverse: `
                    <h3>Model Calibration — Direct Inversion (Regression-Based)</h3>
                    <p>Calibrate a model by learning the inverse map directly: a regression from
                    <b>measured responses → parameters</b>, trained on simulated pairs. The model input
                    is what a forward model produces as output, and the model output is its input —
                    so at inference a single forward pass turns a measurement into a parameter estimate,
                    with no per-measurement MCMC.</p>
                    <ul>
                        <li>Upload measured responses as the model input and parameters as the model output</li>
                        <li>Train a probabilistic regressor (MDN or CRPS) for calibrated uncertainty</li>
                        <li>Inspect predicted parameter vs. response with confidence bands</li>
                    </ul>
                `,
                multiModel: `
                    <h3>Multi-Building Design Updating</h3>
                    <p>Update and calibrate models for multiple buildings simultaneously using a unified framework. Share knowledge across similar structures for improved predictions.</p>
                    <ul>
                        <li>Calibrate models across building portfolios</li>
                        <li>Transfer learning between similar structures</li>
                        <li>Reduce computational requirements</li>
                    </ul>
                `,
                mosaic: `
                    <h3>MOSAIC Surrogate Modeling</h3>
                    <p>Train a classification-based data-driven surrogate over frequency and eigenvector degrees-of-approximation, then calibrate it against measurements.</p>
                    <ul>
                        <li>Define variables and sample or upload QoI data</li>
                        <li>Train a MOSAIC model with a configurable resolution and classification method</li>
                        <li>Link measurements and update the digital twin</li>
                    </ul>
                `
            }
        };
    },
    methods: {
        openManual() {
            const file = this.mode === "earthquakeResilience" ? "./EPUSH_paper.pdf" : "./climate_paper.pdf";
            window.open(file, "_blank");
        },
        startDemoLoading() {
            this.demoLoading = true;
            clearTimeout(this._demoHideTimer);
            this._demoHideTimer = setTimeout(() => {
                this.demoLoading = false;
            }, DEMO_DEBOUNCE_MS);
        },
        onDemoSocketActivity() {
            if (!this.demoLoading) return;
            clearTimeout(this._demoHideTimer);
            this._demoHideTimer = setTimeout(() => {
                this.demoLoading = false;
            }, DEMO_DEBOUNCE_MS);
        },
        async subtractingDemo() {
            this.startDemoLoading();
            await this.socket.emit("data_driven_demo");
        },
        async hybridDemo() {
            this.startDemoLoading();
            await this.socket.emit("hybrid_demo");
        },
        async multiModelDemo() {
            this.startDemoLoading();
            await this.socket.emit("multi_model_demo");
        },
    },
    mounted() {
        this.stopDemoLoadingOnError = () => { this.demoLoading = false; };
        this.socket.onAny(this.onDemoSocketActivity);
        this.socket.on("error", this.stopDemoLoadingOnError);
    },
    beforeUnmount() {
        clearTimeout(this._demoHideTimer);
        this.socket.offAny(this.onDemoSocketActivity);
        this.socket.off("error", this.stopDemoLoadingOnError);
    }
};
</script>

<style scoped>
.info-page {
    max-width: 900px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-xl);
}

.description-text {
    color: var(--text-main);
    line-height: 1.8;
}

:deep(h3) {
    font-size: 1.25rem;
    margin-top: 2rem;
    margin-bottom: 1rem;
    color: var(--primary);
    border-left: 4px solid var(--primary);
    padding-left: 1rem;
}

:deep(ol), :deep(ul) {
    margin-bottom: 2rem;
    padding-left: 1.5rem;
}

:deep(li) {
    margin-bottom: 0.75rem;
    position: relative;
}

.btn-secondary {
    background-color: var(--secondary);
    color: var(--text-main);
    border-color: var(--border-color);
}

.btn-secondary:hover {
    background-color: #e2e6ea;
    border-color: #dae0e5;
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
