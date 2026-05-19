<template>
    <div class="upload-page">
        <LogoLine
            :logos="[
                { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                { src: '/logos/hs_logo.png', alt: 'HS Logo' },
            ]"
        />
        
        <div class="header-actions mb-4">
            <BackButton :prevPage="'info'" :changePage="changePage" />
        </div>

        <div v-if="localMode === 'surrogate' || localMode === 'subtracting'" class="card-pro mb-4">
            <div class="d-flex align-items-center justify-content-between">
                <h2 class="m-0">Upload Trained Model</h2>
                <InputLoader
                    v-if="localMode === 'surrogate'"
                    :dkgApiStatus="dkgApiStatus"
                    :socket="socket"
                    @load-file="loadModel"
                    :fileType="'.sm'"
                    :loadType="'model'"
                    :dkgToken="dkgToken"
                />
                <InputLoader
                    v-if="localMode === 'subtracting'"
                    :dkgApiStatus="dkgApiStatus"
                    :socket="socket"
                    @load-file="loadModel"
                    :fileType="'.ddpm'"
                    :loadType="'model'"
                    :dkgToken="dkgToken"
                />
            </div>
            <p class="text-muted mt-2">Upload your previously trained predictive model file to continue with analysis.</p>
        </div>

        <div v-if="localMode === 'multiModel'" class="multi-model-container">
            <!-- Step 1: Upload Models -->
            <div class="card-pro mb-4">
                <h2 class="mb-4">1. Upload Trained Models</h2>
                <div class="row g-3 align-items-end">
                    <div class="col-md-4">
                        <label class="form-label fw-bold">Model Name</label>
                        <input type="text" v-model="modelName" placeholder="Enter model name..." />
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold">Select File</label>
                        <InputLoader
                            :dkgApiStatus="dkgApiStatus"
                            :socket="socket"
                            @load-file="selectModel"
                            :fileType="'.sm'"
                            :loadType="'model'"
                            :dkgToken="dkgToken"
                        />
                    </div>
                    <div class="col-md-4">
                        <button class="btn-pro w-100" @click="addModel">
                            <i class="bi bi-plus-lg"></i> Add to List
                        </button>
                    </div>
                </div>
                <div v-if="selectedFile" class="mt-3 alert alert-info py-2">
                    <small>Selected: <strong>{{ selectedFile }}</strong></small>
                </div>

                <div class="mt-4" v-if="Object.keys(uploadPage.models).length > 0">
                    <table class="table-custom-custom">
                        <thead>
                            <tr>
                                <th>Model Name</th>
                                <th>Parameters</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(params, key) in uploadPage.models" :key="key">
                                <td class="fw-bold">{{ key }}</td>
                                <td><div class="param-tags"><span v-for="p in params" :key="p" class="badge-custom">{{ p }}</span></div></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Step 2: Link Parameters -->
            <div class="card-pro mb-4" v-if="Object.keys(uploadPage.models).length > 1">
                <h2 class="mb-4">2. Link Parameters</h2>
                <div v-for="(obj, index) in connect" :key="index" class="link-row mb-3 p-3 bg-light rounded">
                    <div class="row g-2 align-items-end">
                        <div class="col-md-5">
                            <label class="form-label small text-muted">Model</label>
                            <select v-model="obj.model">
                                <option disabled value="">Choose Model</option>
                                <option v-for="name in filteredModels(index)" :key="name" :value="name">{{ name }}</option>
                            </select>
                        </div>
                        <div class="col-md-5">
                            <label class="form-label small text-muted">Parameter</label>
                            <select v-model="obj.param">
                                <option disabled value="">Choose Parameter</option>
                                <option v-for="param in getAvailableParams(obj.model)" :key="param" :value="param">{{ param }}</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <button class="btn-pro btn-danger w-100" @click="removeConnectElement(index)">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="d-flex gap-2">
                    <button class="btn-pro btn-outline-pro" @click="addConnectElement">
                        <i class="bi bi-plus"></i> Add Link
                    </button>
                    <button class="btn-pro" @click="connectParams" v-if="connect.length > 1">
                        <i class="bi bi-link"></i> Connect Selected
                    </button>
                </div>

                <div class="mt-4" v-if="connections.length > 0">
                    <h4 class="h6 text-muted text-uppercase mb-3">Established Connections</h4>
                    <table class="table-custom-custom">
                        <tbody>
                            <tr v-for="(connection, index) in connections" :key="index">
                                <td>
                                    <div class="d-flex flex-wrap gap-2 align-items-center">
                                        <div v-for="(obj, idx) in connection" :key="idx" class="connection-pill">
                                            <strong>{{ obj.model }}</strong>: {{ obj.param }}
                                        </div>
                                    </div>
                                </td>
                                <td style="width: 50px">
                                    <button class="text-danger border-0 bg-transparent" @click="removeConnection(index)">&times;</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Step 3: Finalize -->
            <div class="card-pro text-center py-5">
                <button class="btn-pro btn-lg px-5" @click="createJoint" :disabled="Object.keys(uploadPage.models).length < 2">
                    Create Joint Manager
                </button>
                <div v-if="uploadPage.jointCreated" class="mt-3 text-success fw-bold">
                    <i class="bi bi-check-circle-fill"></i> Joint Manager Successfully Created
                </div>
                <div class="mt-4">
                    <NextButton :nextPage="'measurements'" :available="uploadPage.jointCreated" :changePage="changePage" />
                </div>
            </div>
        </div>
    </div>
</template>

<script>
import NextButton from "./NextButton.vue";
import BackButton from "./BackButton.vue";
import LogoLine from "./LogoLine.vue";
import InputLoader from "./InputLoader.vue";

export default {
    components: { NextButton, BackButton, LogoLine, InputLoader },
    props: {
        uploadPage: { type: Object, required: true },
        socket: { type: Object, required: true },
        mode: { type: String, required: true },
        addPageDone: { type: Function, required: true },
        changePage: { type: Function, required: true },
        dkgApiStatus: { type: String, required: true },
        sendInChunks: { type: Function, required: true },
        dkgToken: { type: String, required: true },
    },
    data() {
        return {
            selectedFile: null,
            localMode: this.mode,
            modelName: "",
            selectedModel: null,
            connect: [{ model: "", param: "" }],
            connections: [],
        };
    },
    methods: {
        loadModel(event) {
            this.sendInChunks(event, "load_model", this.socket);
        },
        selectModel(event) {
            const file = event;
            if (!file) return;
            this.selectedFile = file.name;
            const reader = new FileReader();
            reader.onload = (e) => {
                this.selectedModel = e.target.result;
            };
            reader.readAsArrayBuffer(file);
        },
        addModel() {
            if (!this.modelName || !this.selectedModel) {
                alert("Please provide both a name and a model file.");
                return;
            }
            this.socket.emit("add_model", { name: this.modelName, model: this.selectedModel });
            this.modelName = "";
            this.selectedFile = null;
            this.selectedModel = null;
        },
        filteredModels(index) {
            let models = Object.keys(this.uploadPage.models);
            return models.filter(m => !this.connect.some((obj, idx) => obj.model === m && idx !== index));
        },
        getAvailableParams(model) {
            if (!model || !this.uploadPage.models[model]) return [];
            let params = [...this.uploadPage.models[model]];
            this.connections.forEach(conn => {
                conn.forEach(obj => {
                    if (obj.model === model) params = params.filter(p => p !== obj.param);
                });
            });
            return params;
        },
        addConnectElement() { this.connect.push({ model: "", param: "" }); },
        removeConnectElement(index) { this.connect.splice(index, 1); },
        removeConnection(index) { this.connections.splice(index, 1); },
        connectParams() {
            if (this.connect.some(obj => !obj.model || !obj.param)) {
                alert("Please fill in all link fields.");
                return;
            }
            this.connections.push([...this.connect]);
            this.connect = [{ model: "", param: "" }];
        },
        createJoint() {
            const results = this.connections.reduce((acc, group) => {
                const paramDict = group.reduce((gAcc, conn) => ({ ...gAcc, [conn.model]: conn.param }), {});
                const modelNames = Object.keys(this.uploadPage.models);
                const params = modelNames.map(m => paramDict[m] || "-");
                const key = `joint_${params.filter(p => p !== "-").join("_")}`;
                acc[key] = params;
                return acc;
            }, {});
            this.socket.emit("create_joint", results);
        }
    },
    watch: {
        "uploadPage.jointCreated"(val) { if (val) this.addPageDone("upload"); },
        mode(val) { this.localMode = val; }
    }
};
</script>

<style scoped>
.upload-page {
    max-width: 1000px;
    margin: 0 auto;
}

.table-custom {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    overflow: hidden;
}

.table-custom th {
    background: var(--secondary);
    padding: 1rem;
    font-weight: 600;
    text-align: left;
}

.table-custom td {
    padding: 1rem;
    border-top: 1px solid var(--border-color);
}

.param-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.badge-custom {
    background: rgba(163, 0, 54, 0.08);
    color: var(--primary);
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
}

.connection-pill {
    background: var(--primary);
    color: white;
    padding: 0.4rem 1rem;
    border-radius: 6px;
    font-size: 0.85rem;
}

.link-row {
    border: 1px solid transparent;
    transition: border-color 0.2s;
}

.link-row:hover {
    border-color: var(--border-color);
}
</style>
