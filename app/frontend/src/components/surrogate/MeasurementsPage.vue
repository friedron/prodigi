<template>
    <div class="measurements-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
            :logos="[
                { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                { src: '/logos/hs_logo.png', alt: 'HS Logo' },
            ]"
        />
        </div>

        <BackButton :prevPage="mode === 'surrogate' ? 'uq' : 'subtract'" :changePage="changePage" />

        <!-- Measurement/Targeted Labels Card -->
        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-rulers fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0" v-if="mode === 'surrogate'">Definition of Measurement</h2>
                <h2 class="h4 mb-0" v-else>Definition of Targeted Label(s)</h2>
            </div>

            <div class="row align-items-center mb-4">
                <div class="col-md-8">
                    <p class="text-muted mb-0" v-if="mode === 'surrogate'">
                        Import the mean measured values for your Quantities of Interest.
                    </p>
                    <p class="text-muted mb-0" v-else>
                        Import the targeted labels for your data-driven analysis.
                    </p>
                </div>
                <div class="col-md-4 text-end">
                    <InputLoader 
                        :socket="socket" 
                        @load-file="loadMean" 
                        :fileType="'.csv'" 
                        :loadType="'zmean'" 
                    />
                </div>
            </div>

            <div v-if="zmean_file" class="mb-3">
                <span class="badge bg-light text-dark border">
                    <i class="bi bi-file-earmark-check me-1 text-success"></i>
                    Loaded: {{ zmean_file }}
                </span>
            </div>

            <div v-if="measurementsPage.zmean" class="table-responsive">
                <table class="table table-hover align-middle custom-table border">
                    <thead>
                        <tr>
                            <th>Parameter/QoI</th>
                            <th class="text-end">Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(value, key) in measurementsPage.zmean" :key="key">
                            <td class="fw-bold text-primary">{{ key }}</td>
                            <td class="text-end font-monospace">{{ (+Object.values(value)[0]).toFixed(4) }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Standard Deviation/Tolerance Card -->
        <div class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-plus-slash-minus fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0" v-if="mode === 'surrogate'">Standard Deviation of Measurement Error</h2>
                <h2 class="h4 mb-0" v-else>Tolerated Deviation from Targeted Label(s)</h2>
            </div>

            <div class="row align-items-center mb-4">
                <div class="col-md-8">
                    <p class="text-muted mb-0" v-if="mode === 'surrogate'">
                        Import the standard deviation representing the uncertainty in your measurements.
                    </p>
                    <p class="text-muted mb-0" v-else>
                        Import the tolerated deviation ranges for each targeted label.
                    </p>
                </div>
                <div class="col-md-4 text-end">
                    <InputLoader 
                        :socket="socket" 
                        @load-file="loadSigma" 
                        :fileType="'.csv'" 
                        :loadType="'sigma'" 
                    />
                </div>
            </div>

            <div v-if="sigma_file" class="mb-3">
                <span class="badge bg-light text-dark border">
                    <i class="bi bi-file-earmark-check me-1 text-success"></i>
                    Loaded: {{ sigma_file }}
                </span>
            </div>

            <div v-if="measurementsPage.sigma" class="table-responsive">
                <table class="table table-hover align-middle custom-table border">
                    <thead>
                        <tr>
                            <th>Parameter/QoI</th>
                            <th class="text-end">STD / Deviation</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(value, key) in measurementsPage.sigma" :key="key">
                            <td class="fw-bold text-primary">{{ key }}</td>
                            <td class="text-end font-monospace">{{ (+Object.values(value)[0]).toFixed(4) }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <NextButton
            :nextPage="'compare'"
            :available="measurementsPage.zmean !== null && measurementsPage.sigma !== null"
            :changePage="changePage"
        />
    </div>
</template>

<script>
import NextButton from "../NextButton.vue";
import BackButton from "../BackButton.vue";
import LogoLine from "../LogoLine.vue";
import InputLoader from "../InputLoader.vue";

export default {
    components: {
        NextButton,
        BackButton,
        LogoLine,
        InputLoader,
    },
    props: {
        measurementsPage: { type: Object, required: true },
        mode: { type: String, required: true },
        socket: { type: Object, required: true },
        changePage: { type: Function, required: true },
        addPageDone: { type: Function, required: true },
        sendInChunks: { type: Function, required: true },
    },
    data() {
        return {
            zmean_file: null,
            sigma_file: null,
        };
    },
    watch: {
        measurementsPage: {
            handler() {
                if (this.measurementsPage.zmean !== null && this.measurementsPage.sigma !== null) {
                    this.addPageDone("measurements");
                }
            },
            deep: true,
        },
    },
    methods: {
        loadMean(event) {
            this.sendInChunks(event, "load_zmean", this.socket);
        },
        loadSigma(event) {
            this.sendInChunks(event, "load_sigma", this.socket);
        },
    },
    mounted() {
        this.socket.on("zmean_loaded", (data) => {
            this.zmean_file = data.filename;
        });
        this.socket.on("sigma_loaded", (data) => {
            this.sigma_file = data.filename;
        });
    },
    beforeUnmount() {
        this.socket.off("zmean_loaded");
        this.socket.off("sigma_loaded");
    }
};
</script>

<style scoped>
.measurements-page {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
}

.custom-table thead th {
    background-color: var(--secondary);
    font-size: 0.75rem;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 1rem;
}

.custom-table tbody td {
    padding: 0.75rem 1rem;
}

.font-monospace {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.95em;
    color: var(--text-main);
}

.badge {
    font-weight: 500;
    padding: 0.5em 0.8em;
}

.bi-file-earmark-check {
    font-size: 1.1em;
}
</style>