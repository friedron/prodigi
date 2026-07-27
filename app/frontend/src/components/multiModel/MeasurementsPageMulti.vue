<template>
    <div class="measurements-multi container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'upload'" :changePage="changePage" />

        <!-- Mean Measured Value Card -->
        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-3 pb-2 border-bottom">
                <i class="bi bi-graph-up fs-4 me-2 text-primary"></i>
                <div>
                    <h2 class="h4 mb-0">Mean Measured Value</h2>
                    <p class="text-muted small mb-0 mt-1">
                        Import the mean measured value CSV file for each model.
                    </p>
                </div>
            </div>

            <div class="model-sections">
                <div
                    v-for="model in Object.keys(uploadPage.models || {})"
                    :key="'zmean-' + model"
                    class="model-block mb-4"
                >
                    <div class="model-block-header mb-2">
                        <div class="d-flex align-items-center gap-2">
                            <i class="bi bi-building text-primary"></i>
                            <span class="fw-bold">{{ model }}</span>
                            <span
                                v-if="
                                    measurementsPage.multiModel &&
                                    measurementsPage.multiModel[model] &&
                                    measurementsPage.multiModel[model].zmean &&
                                    Object.keys(measurementsPage.multiModel[model].zmean).length > 0
                                "
                                class="status-chip status-chip--loaded"
                            >
                                <i class="bi bi-check-circle-fill"></i> Loaded
                            </span>
                            <span v-else class="status-chip status-chip--pending">
                                <i class="bi bi-clock"></i> Awaiting file
                            </span>
                        </div>
                        <InputLoader
                            :socket="socket"
                            @load-file="loadMean($event, model)"
                            :fileType="'.csv'"
                            :loadType="'zmean'"
                        />
                    </div>

                    <div
                        v-if="
                            measurementsPage.multiModel &&
                            measurementsPage.multiModel[model] &&
                            measurementsPage.multiModel[model].zmean &&
                            Object.keys(measurementsPage.multiModel[model].zmean).length > 0
                        "
                        class="table-responsive table-scroll"
                    >
                        <table class="table-pro">
                            <thead>
                                <tr>
                                    <th>Parameter</th>
                                    <th class="text-end">Measured Value</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="(value, key) in measurementsPage.multiModel[model].zmean"
                                    :key="key"
                                >
                                    <td class="font-monospace">{{ key }}</td>
                                    <td class="text-end font-monospace">{{ value[0].toFixed(4) }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div v-else class="empty-state">
                        <i class="bi bi-file-earmark-bar-graph"></i>
                        <p>No data loaded yet. Upload a CSV file above.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Standard Deviation Card -->
        <div class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-3 pb-2 border-bottom">
                <i class="bi bi-distribute-vertical fs-4 me-2 text-primary"></i>
                <div>
                    <h2 class="h4 mb-0">Standard Deviation of Measurement Error</h2>
                    <p class="text-muted small mb-0 mt-1">
                        Import the measurement error standard deviation CSV file for each model.
                    </p>
                </div>
            </div>

            <div class="model-sections">
                <div
                    v-for="model in Object.keys(uploadPage.models || {})"
                    :key="'sigma-' + model"
                    class="model-block mb-4"
                >
                    <div class="model-block-header mb-2">
                        <div class="d-flex align-items-center gap-2">
                            <i class="bi bi-building text-primary"></i>
                            <span class="fw-bold">{{ model }}</span>
                            <span
                                v-if="
                                    measurementsPage.multiModel &&
                                    measurementsPage.multiModel[model] &&
                                    measurementsPage.multiModel[model].sigma &&
                                    Object.keys(measurementsPage.multiModel[model].sigma).length > 0
                                "
                                class="status-chip status-chip--loaded"
                            >
                                <i class="bi bi-check-circle-fill"></i> Loaded
                            </span>
                            <span v-else class="status-chip status-chip--pending">
                                <i class="bi bi-clock"></i> Awaiting file
                            </span>
                        </div>
                        <InputLoader
                            :socket="socket"
                            @load-file="loadSigma($event, model)"
                            :fileType="'.csv'"
                            :loadType="'sigma'"
                        />
                    </div>

                    <div
                        v-if="
                            measurementsPage.multiModel &&
                            measurementsPage.multiModel[model] &&
                            measurementsPage.multiModel[model].sigma &&
                            Object.keys(measurementsPage.multiModel[model].sigma).length > 0
                        "
                        class="table-responsive table-scroll"
                    >
                        <table class="table-pro">
                            <thead>
                                <tr>
                                    <th>Parameter</th>
                                    <th class="text-end">Std of Measured Value</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr
                                    v-for="(value, key) in measurementsPage.multiModel[model].sigma"
                                    :key="key"
                                >
                                    <td class="font-monospace">{{ key }}</td>
                                    <td class="text-end font-monospace">{{ value[0].toFixed(4) }}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div v-else class="empty-state">
                        <i class="bi bi-file-earmark-bar-graph"></i>
                        <p>No data loaded yet. Upload a CSV file above.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Footer action -->
        <div class="mb-4">
            <NextButton :nextPage="'update'" :available="measurementsPage.done" :changePage="changePage" />
        </div>
    </div>
</template>

<script>
import NextButton from "../NextButton.vue";
import LogoLine from "../LogoLine.vue";
import BackButton from "../BackButton.vue";
import InputLoader from "../InputLoader.vue";

export default {
    components: {
        NextButton,
        LogoLine,
        BackButton,
        InputLoader,
    },
    props: {
        measurementsPage: {
            type: Object,
            required: true,
        },
        uploadPage: {
            type: Object,
            required: true,
        },
        mode: {
            type: String,
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
        addPageDone: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            measurement_done: false,
        };
    },
    watch: {},
    methods: {
        loadMean(event, model) {
            const file = event;
            if (!file) {
                return;
            }
            const reader = new FileReader();
            reader.onload = (event) => {
                const csvContent = event.target.result;
                this.socket.emit("load_zmean_multi", {
                    name: file.name,
                    type: file.type,
                    model_name: model,
                    data: csvContent,
                });
            };
            reader.readAsText(file);
        },
        loadSigma(event, model) {
            const file = event;
            if (!file) {
                return;
            }
            const reader = new FileReader();
            reader.onload = (event) => {
                const csvContent = event.target.result;
                this.socket.emit("load_sigma_multi", {
                    name: file.name,
                    type: file.type,
                    model_name: model,
                    data: csvContent,
                });
            };
            reader.readAsText(file);
        },
        isPageDone(page) {
            return this.measurementsPage.done;
        },
    },
    mounted() {
        this.socket.on("measurement_done", () => {
            this.measurement_done = true;
        });
    },
};
</script>

<style scoped>
.measurements-multi {
    max-width: 900px;
    margin: 0 auto;
}

.logo-section {
    margin-bottom: 1rem;
}

.content-card {
    padding: var(--spacing-lg);
}

/* Per-model block */
.model-block {
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: 1rem 1.25rem;
    background: var(--secondary);
    transition: border-color 0.2s ease;
}

.model-block:last-child {
    margin-bottom: 0 !important;
}

.model-block:hover {
    border-color: rgba(163, 0, 54, 0.25);
}

.model-block-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 0.75rem;
}

/* Status chips */
.status-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.25rem 0.65rem;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.status-chip--loaded {
    background: rgba(25, 135, 84, 0.1);
    color: #198754;
    border: 1px solid rgba(25, 135, 84, 0.25);
}

.status-chip--pending {
    background: var(--secondary);
    color: var(--text-muted);
    border: 1px solid var(--border-color);
}

/* Table */
.table-pro {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    overflow: hidden;
    background: #fff;
    margin-top: 0.75rem;
}

.table-pro th {
    background: var(--secondary);
    padding: 0.75rem 1rem;
    font-weight: 600;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
    text-align: left;
}

.table-pro td {
    padding: 0.7rem 1rem;
    border-top: 1px solid var(--border-color);
    font-size: 0.9rem;
    color: var(--text-main);
}

.table-pro tbody tr:hover {
    background: rgba(163, 0, 54, 0.02);
}

.text-end {
    text-align: right;
}

/* Empty state */
.empty-state {
    text-align: center;
    padding: 1.5rem 1rem;
    border: 1px dashed var(--border-color);
    border-radius: var(--radius);
    color: var(--text-muted);
    background: #fff;
    margin-top: 0.75rem;
}

.empty-state i {
    font-size: 1.4rem;
    display: block;
    margin-bottom: 0.4rem;
    opacity: 0.5;
}

.empty-state p {
    margin: 0;
    font-size: 0.875rem;
}

/* Scrollable table container */
.table-scroll {
    max-height: 260px;
    overflow-y: auto;
    border-radius: var(--radius);
}

/* Sticky header inside scroll */
.table-scroll .table-pro thead th {
    position: sticky;
    top: 0;
    z-index: 1;
    box-shadow: 0 1px 0 var(--border-color);
}

/* Monospace numbers */
.font-monospace {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.88em;
}
</style>
