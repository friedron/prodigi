<template>
    <div class="exploratory-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="mode === 'mosaic' ? 'sample' : 'variables'" :changePage="changePage" />

        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-graph-up-arrow fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Correlation Analysis</h2>
            </div>
            
            <div class="row align-items-center mb-4">
                <div class="col-md-6">
                    <label class="form-label fw-bold">Analysis Mode</label>
                    <div class="d-flex gap-2">
                        <select v-model="plot_mode" class="form-select" @change="socket.emit('exploratory_plot', { mode: plot_mode })">
                            <option value="input-output">Features vs QoI</option>
                            <option value="input-input">Features vs Features</option>
                            <option value="output-output">QoI vs QoI</option>
                        </select>
                    </div>
                    <p class="text-muted small mt-2">
                        Visualize linear correlations between different sets of parameters and outputs.
                    </p>
                </div>
            </div>

            <div v-if="plot" class="plot-container">
                <img class="img-fluid plot-img" :src="plot" alt="Exploratory Plot" />
            </div>
            <div v-else class="plot-placeholder">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="mt-2 text-muted">Generating correlation plot...</p>
            </div>
        </div>

        <div class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-dot-circle fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Paired Scatter Analysis</h2>
            </div>

            <div class="row g-3 mb-4">
                <div class="col-md-4">
                    <label class="form-label fw-bold">X-Axis (Parameter/QoI)</label>
                    <select v-model="param1" class="form-select">
                        <optgroup label="Variables">
                            <option v-for="variable in variablePage.data.variables" :key="'p1-'+variable.name" :value="variable.name">
                                {{ variable.name }}
                            </option>
                        </optgroup>
                        <optgroup label="QoI" v-if="variablePage.qoiTable">
                            <option v-for="param in Object.keys(variablePage.qoiTable)" :key="'q1-'+param" :value="param">
                                {{ param }}
                            </option>
                        </optgroup>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold">Y-Axis (Parameter/QoI)</label>
                    <select v-model="param2" class="form-select">
                        <optgroup label="Variables">
                            <option v-for="variable in variablePage.data.variables" :key="'p2-'+variable.name" :value="variable.name">
                                {{ variable.name }}
                            </option>
                        </optgroup>
                        <optgroup label="QoI" v-if="variablePage.qoiTable">
                            <option v-for="param in Object.keys(variablePage.qoiTable)" :key="'q2-'+param" :value="param">
                                {{ param }}
                            </option>
                        </optgroup>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold">Color by (Optional)</label>
                    <select v-model="colorBy" class="form-select">
                        <option value="">None</option>
                        <optgroup label="Variables">
                            <option v-for="variable in variablePage.data.variables" :key="'pc-'+variable.name" :value="variable.name">
                                {{ variable.name }}
                            </option>
                        </optgroup>
                        <optgroup label="QoI" v-if="variablePage.qoiTable">
                            <option v-for="param in Object.keys(variablePage.qoiTable)" :key="'qc-'+param" :value="param">
                                {{ param }}
                            </option>
                        </optgroup>
                    </select>
                </div>
            </div>

            <div class="d-flex justify-content-center mb-4">
                <button
                    class="btn-pro px-5"
                    :disabled="!param1 || !param2"
                    @click="socket.emit('exploratory_plot_scatter', { param1, param2, hue: colorBy })"
                >
                    <i class="bi bi-play-fill"></i> Generate Scatter Plot
                </button>
            </div>

            <div v-if="plot_scatter" class="plot-container">
                <img class="img-fluid plot-img" :src="plot_scatter" alt="Scatter Plot" />
            </div>
            <div v-else-if="param1 && param2" class="plot-placeholder bg-light">
                <p class="text-muted mb-0">Select parameters and click "Generate" to visualize relationships.</p>
            </div>
        </div>

        <NextButton :nextPage="'surrogate'" :available="true" :changePage="changePage" />
    </div>
</template>

<script>
import NextButton from "../NextButton.vue";
import BackButton from "../BackButton.vue";
import LogoLine from "../LogoLine.vue";

export default {
    components: {
        NextButton,
        BackButton,
        LogoLine,
    },
    props: {
        mode: { type: String, default: "" },
        variablePage: { type: Object, required: true },
        socket: { type: Object, required: true },
        convertToBase64: { type: Function, required: true },
        changePage: { type: Function, required: true },
    },
    data() {
        return {
            plot_mode: "input-output",
            param1: null,
            param2: null,
            colorBy: "",
            plot: null,
            plot_scatter: null,
        };
    },
    mounted() {
        this.socket.on("exploratory_plot", (data) => {
            this.convertToBase64(data)
                .then((base64Image) => { this.plot = base64Image; })
                .catch((err) => console.error(err));
        });
        this.socket.on("exploratory_plot_scatter", (data) => {
            this.convertToBase64(data)
                .then((base64Image) => { this.plot_scatter = base64Image; })
                .catch((err) => console.error(err));
        });

        // Initial plot (socket.io buffers emits until connected, so no need to check connected state)
        this.socket.emit("exploratory_plot", { mode: this.plot_mode });
    },
    beforeUnmount() {
        this.socket.off("exploratory_plot");
        this.socket.off("exploratory_plot_scatter");
    }
};
</script>

<style scoped>
.exploratory-page {
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

.plot-placeholder {
    height: 300px;
    border: 2px dashed var(--border-color);
    border-radius: var(--radius);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
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
