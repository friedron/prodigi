<template>
    <div class="predicted-vs-feature-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'surrogate'" :changePage="changePage" />

        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-graph-up fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Predicted Mean vs. Feature</h2>
            </div>

            <p class="text-muted mb-4">
                Scatter the observed {{ isInverse ? 'model output' : 'QoI' }} against a single
                {{ isInverse ? 'model input' : 'feature' }}, overlaid with the model's predicted mean
                and a confidence band sampled from the predictive distribution. Requires a probabilistic
                model (MDN or CRPS) trained on the Data-Driven Modeling step.
                <span v-if="isInverse">
                    In direct inversion the model input is a <b>measured response</b> and the model
                    output is a <b>parameter</b>.
                </span>
            </p>

            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label fw-bold">{{ isInverse ? 'Measured Response (x-axis)' : 'Feature (x-axis)' }}</label>
                    <select class="form-select" v-model="feature">
                        <option value="" disabled hidden>Select a {{ isInverse ? 'response' : 'feature' }}</option>
                        <option v-for="f in featureOptions" :key="f" :value="f">{{ f }}</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label fw-bold">{{ isInverse ? 'Parameter (model output)' : 'Quantity of Interest' }}</label>
                    <select class="form-select" v-model="qoi">
                        <option value="" disabled hidden>Select a {{ isInverse ? 'parameter' : 'QoI' }}</option>
                        <option v-for="q in qoiOptions" :key="q" :value="q">{{ q }}</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label fw-bold d-flex align-items-center gap-1">
                        Confidence Level
                        <Tooltip :content="'<p>Width of the shaded band, as a central probability mass of the predictive distribution (e.g. 0.95 = 95% CI).</p>'" />
                    </label>
                    <input type="number" class="form-control" v-model.number="ciLevel" step="0.01" min="0.5" max="0.99" />
                </div>
                <div class="col-md-6">
                    <label class="form-label fw-bold d-flex align-items-center gap-1">
                        Samples per Point
                        <Tooltip :content="'<p>Number of draws from the predictive distribution used to estimate the band at each input.</p>'" />
                    </label>
                    <input type="number" class="form-control" v-model.number="nSamples" step="500" min="200" />
                </div>
            </div>

            <div class="mt-4 pt-3 border-top">
                <label class="form-label fw-bold d-flex align-items-center gap-1">
                    Held-out Evaluation Set <span class="text-muted fw-normal">(optional)</span>
                    <Tooltip :content="'<p>A single CSV holding both the feature and QoI columns for a separate period (the Granada &quot;future period&quot; set). Its observations are drawn in a distinct colour.</p>'" />
                </label>
                <div class="d-flex align-items-center gap-3">
                    <div class="file-upload-wrapper">
                        <input
                            type="file"
                            id="evalSetInput"
                            class="file-input-hidden"
                            accept=".csv"
                            @change="handleEvalSet"
                        />
                        <label for="evalSetInput" class="btn-pro btn-outline-pro mb-0">
                            <i class="bi bi-upload"></i> Choose CSV
                        </label>
                    </div>
                    <span v-if="evalSetFile" class="small text-success d-flex align-items-center">
                        <i class="bi bi-check-circle-fill me-1"></i> {{ evalSetFile }}
                    </span>
                </div>
            </div>

            <div class="mt-4 pt-3 border-top d-flex justify-content-center">
                <button class="btn-pro px-5" @click="generate" :disabled="isGenerating || !feature || !qoi">
                    <span v-if="isGenerating" class="btn-spinner"></span>
                    <i v-else class="bi bi-bar-chart-line"></i>
                    {{ isGenerating ? "Generating…" : "Generate Plot" }}
                </button>
            </div>
        </div>

        <div v-if="plot" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-image fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Result</h2>
            </div>
            <img :src="plot" class="img-fluid plot-img" alt="Predicted mean vs. feature" />
        </div>
    </div>
</template>

<script>
import BackButton from "./BackButton.vue";
import Tooltip from "./Tooltip.vue";
import LogoLine from "./LogoLine.vue";

export default {
    components: { BackButton, Tooltip, LogoLine },
    props: {
        mode: { type: String, required: true },
        variablePage: { type: Object, required: true },
        surrogatePage: { type: Object, required: true },
        socket: { type: Object, required: true },
        changePage: { type: Function, required: true },
        addPageDone: { type: Function, required: true },
        sendInChunks: { type: Function, required: true },
        convertToBase64: { type: Function, required: true },
    },
    data() {
        return {
            feature: "",
            qoi: "",
            ciLevel: 0.95,
            nSamples: 2000,
            evalSetFile: null,
            plot: null,
            isGenerating: false,
        };
    },
    computed: {
        isInverse() {
            return this.mode === "inverse";
        },
        featureOptions() {
            const selected = this.surrogatePage.selectedFeats;
            if (selected && selected.length) return selected;
            return this.variablePage.data.variables.map((v) => v.name);
        },
        qoiOptions() {
            const trained = this.surrogatePage.outputQoI;
            if (trained && trained.length) return trained;
            return Object.keys(this.variablePage.qoiTable);
        },
    },
    watch: {
        featureOptions: {
            handler(opts) {
                if (!this.feature && opts.length) this.feature = opts[0];
            },
            immediate: true,
        },
        qoiOptions: {
            handler(opts) {
                if (!this.qoi && opts.length) this.qoi = opts[0];
            },
            immediate: true,
        },
    },
    methods: {
        handleEvalSet(event) {
            const file = event.target.files[0];
            if (!file) return;
            this.sendInChunks(file, "load_eval_set", this.socket);
        },
        generate() {
            if (!this.feature || !this.qoi) {
                alert("Please select a feature and a QoI.");
                return;
            }
            this.isGenerating = true;
            this.socket.emit("predicted_vs_feature", {
                feature: this.feature,
                qoi: this.qoi,
                ciLevel: this.ciLevel,
                nSamples: this.nSamples,
            });
        },
    },
    mounted() {
        this._plotHandler = (data) => {
            this.convertToBase64(data)
                .then((img) => {
                    this.plot = img;
                    this.addPageDone("plot");
                })
                .catch((err) => console.error(err))
                .finally(() => {
                    this.isGenerating = false;
                });
        };
        this.socket.on("predicted_vs_feature_plot", this._plotHandler);

        this._evalSetHandler = (data) => {
            this.evalSetFile = data.filename;
        };
        this.socket.on("eval_set_loaded", this._evalSetHandler);

        this._errorHandler = () => {
            this.isGenerating = false;
        };
        this.socket.on("error", this._errorHandler);
    },
    beforeUnmount() {
        this.socket.off("predicted_vs_feature_plot", this._plotHandler);
        this.socket.off("eval_set_loaded", this._evalSetHandler);
        this.socket.off("error", this._errorHandler);
    },
};
</script>

<style scoped>
.predicted-vs-feature-page {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
}

.plot-img {
    width: 100%;
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
}

.file-upload-wrapper {
    position: relative;
}

.file-input-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
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
