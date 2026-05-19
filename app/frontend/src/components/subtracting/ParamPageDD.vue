<template>
    <div class="param-page-dd container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'upload'" :changePage="changePage" />

        <!-- Data Upload Section -->
        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-cloud-arrow-up fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Reference Data Setup</h2>
            </div>
            
            <p class="text-muted mb-4">Upload the reference period datasets (Input Features and Output QoI) to initialize the data-driven analysis.</p>

            <div class="row g-4">
                <div class="col-md-6">
                    <div class="upload-zone p-3 border rounded bg-light">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="fw-bold">Input Features (.csv)</span>
                            <InputLoaderExtended :dkgApiStatus="dkgApiStatus" :socket="socket" @load-file="loadInput" :dkgToken="dkgToken"/>
                        </div>
                        <div v-if="features_file" class="small text-success d-flex align-items-center">
                            <i class="bi bi-check-circle-fill me-1"></i> Loaded: {{ features_file }}
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="upload-zone p-3 border rounded bg-light">
                        <div class="d-flex align-items-center justify-content-between mb-2">
                            <span class="fw-bold">Output QoI (.csv, .unv)</span>
                            <InputLoader
                                :dkgApiStatus="dkgApiStatus"
                                :socket="socket"
                                @load-file="loadOutput"
                                :fileType="'.csv, .unv'"
                                :loadType="'labels'"
                                :dkgToken="dkgToken"
                            />
                        </div>
                        <div v-if="labels_file" class="small text-success d-flex align-items-center">
                            <i class="bi bi-check-circle-fill me-1"></i> Loaded: {{ labels_file }}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Approximated Distributions Card -->
        <div v-if="Object.keys(paramPage.data.params).length > 0" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom">
                <div class="d-flex align-items-center">
                    <i class="bi bi-calculator fs-4 me-2 text-primary"></i>
                    <h2 class="h4 mb-0">Approximated Distributions</h2>
                </div>
                <button class="btn-pro btn-outline-pro btn-sm" @click="saveParams">
                    <i class="bi bi-download"></i> Export Parameters
                </button>
            </div>

            <div class="table-responsive">
                <table class="table table-hover align-middle custom-table border">
                    <thead>
                        <tr>
                            <th>Parameter Name</th>
                            <th>Inferred Distribution</th>
                            <th class="text-end">Dist Param 1</th>
                            <th class="text-end">Dist Param 2</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="param in paramPage.data.params" :key="param.id">
                            <td class="fw-bold text-primary">{{ param.name }}</td>
                            <td><span class="badge rounded-pill bg-light text-dark border">{{ param.distribution }}</span></td>
                            <td class="text-end font-monospace">{{ param.distParam1.toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ param.distParam2.toFixed(4) }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Input Summary Statistics Card -->
        <div v-if="Object.keys(paramPage.inputStats).length > 0" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-table fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Input Summary Statistics</h2>
            </div>
            
            <div class="table-responsive">
                <table class="table table-sm table-hover align-middle custom-table border">
                    <thead>
                        <tr>
                            <th>Feature</th>
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
                        <tr v-for="(row, key) in paramPage.inputStats" :key="key">
                            <td class="fw-bold text-primary">{{ key }}</td>
                            <td class="text-end font-monospace">{{ row.mean.toFixed(4) }}</td>
                            <td class="text-end font-monospace">{{ row.std.toFixed(4) }}</td>
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

        <!-- Output Summary Statistics Card -->
        <div v-if="Object.keys(paramPage.qoiTable).length > 0" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-clipboard-data fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Output Summary Statistics</h2>
            </div>

            <div class="table-responsive">
                <table class="table table-sm table-hover align-middle custom-table border">
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
                        <tr v-for="([key, row], idx) in filteredQoi" :key="key">
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

        <NextButton
            :nextPage="'exploratory'"
            :available="Object.keys(paramPage.inputStats).length > 0 && Object.keys(paramPage.qoiTable).length > 0"
            :changePage="changePage"
        />

        <ModeshapeDefiner v-if="modeshape_definer" @finalize="onModeshapeFinalized" />
    </div>
</template>

<script>
import EditParamModal from "../EditParamModal.vue";
import NextButton from "../NextButton.vue";
import BackButton from "../BackButton.vue";
import LogoLine from "../LogoLine.vue";
import InputLoader from "../InputLoader.vue";
import InputLoaderExtended from "../InputLoaderExtended.vue";
import ModeshapeDefiner from "../ModeshapeDefiner.vue";

export default {
    components: {
        EditParamModal,
        NextButton,
        BackButton,
        LogoLine,
        InputLoader,
        InputLoaderExtended,
        ModeshapeDefiner,
    },
    props: {
        socket: { type: Object, required: true },
        paramPage: { type: Object, required: true },
        changePage: { type: Function, required: true },
        addPageDone: { type: Function, required: true },
        sendInChunks: { type: Function, required: true },
        dkgApiStatus: { type: String, required: true },
        dkgToken: { type: String, required: true },
    },
    data() {
        return {
            showModal: false,
            selectedParam: null,
            features_file: null,
            labels_file: null,
            modeshape_definer: false,
            file : null
        };
    },
    watch: {
        paramPage: {
            handler(newVal) {
                if (
                    newVal.samples.length > 0 &&
                    Object.keys(newVal.qoiTable).length > 0 &&
                    newVal.data.params.length > 0
                ) {
                    this.addPageDone("params");
                }
            },
            deep: true,
            immediate: true,
        },
    },
    computed: {
        filteredQoi() {
            return Object.entries(this.paramPage.qoiTable).filter(([key]) => key !== "Datetime" && key !== "mode id");
        },
    },
    methods: {
        loadInput(event) {
            this.sendInChunks(event, "load_features", this.socket);
        },
        loadOutput(event) {
            const file = event;
            this.file = file;
            const fileExtension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
            if (fileExtension === ".unv") {
                this.modeshape_definer = true;
                return;
            }
            if (fileExtension === ".csv") {
                this.sendInChunks(file, "qoi_csv", this.socket);
                return;
            }
        },
        onModeshapeFinalized(cols) {
            this.sendInChunks(this.file, "qoi_unv", this.socket, { modeshape_cols: cols });
            this.modeshape_definer = false;
        },
        saveParams() {
            try {
                let filtered = { params: this.paramPage.data.params.map(({ id, ...rest }) => rest) };
                const data = JSON.stringify(filtered, null, 2);
                const blob = new Blob([data], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = "paramset.json";
                link.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                console.log("Error saving file: ", error);
            }
        },
    },
    mounted() {
        this.socket.on("features_loaded", (data) => {
            this.features_file = data.filename;
        });
        this.socket.on("labels_loaded", (data) => {
            this.labels_file = data.filename;
        });
    },
};
</script>

<style scoped>
.param-page-dd {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
}

.custom-table thead th {
    background-color: var(--secondary);
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--text-muted);
}

.font-monospace {
    font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 0.9em;
}

.badge {
    font-weight: 500;
}

.upload-zone {
    transition: all 0.2s ease;
}

.upload-zone:hover {
    border-color: var(--primary);
    background-color: white;
}
</style>
