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

        <div v-if="localMode === 'surrogate' || localMode === 'subtracting' || localMode === 'mosaic'" class="card-pro mb-4">
            <div class="d-flex align-items-center justify-content-between">
                <h2 class="m-0">Upload Trained Model</h2>
                <InputLoader
                    v-if="localMode === 'surrogate'"
                    :socket="socket"
                    @load-file="loadModel"
                    :fileType="'.sm'"
                    :loadType="'model'"
                />
                <InputLoader
                    v-if="localMode === 'subtracting'"
                    :socket="socket"
                    @load-file="loadModel"
                    :fileType="'.ddpm'"
                    :loadType="'model'"
                />
                <InputLoader
                    v-if="localMode === 'mosaic'"
                    :socket="socket"
                    @load-file="loadModel"
                    :fileType="'.msic'"
                    :loadType="'model'"
                />
            </div>
            <p class="text-muted mt-2">Upload your previously trained predictive model file to continue with analysis.</p>
        </div>

        <div v-if="localMode === 'multiModel'" class="multi-model-container">
            <!-- Wizard progress rail -->
            <div class="wizard-rail mb-4">
                <template v-for="(step, index) in steps" :key="index">
                    <div class="wizard-step" :class="stepStateClass(index)">
                        <div class="wizard-step-marker">
                            <i v-if="step.done" class="bi bi-check-lg"></i>
                            <span v-else>{{ index + 1 }}</span>
                        </div>
                        <span class="wizard-step-label">{{ step.label }}</span>
                    </div>
                    <div v-if="index < steps.length - 1" class="wizard-connector" :class="{ filled: step.done }"></div>
                </template>
            </div>

            <!-- Step 1: Upload Models -->
            <div class="card-pro mb-4 step-card">
                <div class="step-card-header">
                    <div class="step-badge-lg" :class="{ 'is-done': modelCount > 0 }">
                        <i v-if="modelCount > 0" class="bi bi-check-lg"></i>
                        <span v-else>1</span>
                    </div>
                    <div>
                        <h2 class="step-title">Upload Trained Models</h2>
                        <p class="step-subtitle">Add each building's predictive model file to build a shared model library.</p>
                    </div>
                    <span v-if="modelCount > 0" class="step-count-badge">{{ modelCount }} model{{ modelCount > 1 ? "s" : "" }}</span>
                </div>

                <div class="row g-3 align-items-end mb-4">
                    <div class="col-md-4">
                        <label class="form-label fw-bold d-block">Model Name</label>
                        <input type="text" v-model="modelName" placeholder="Enter model name..." />
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold d-block">Select File</label>
                        <InputLoader
                            ref="modelInputLoader"
                            :socket="socket"
                            @load-file="selectModel"
                            :fileType="'.sm'"
                            :loadType="'model'"
                        />
                    </div>
                    <div class="col-md-4">
                        <button class="btn-pro w-100" @click="addModel" :disabled="!modelName || !selectedModel">
                            <i class="bi bi-plus-lg"></i> Add to List
                        </button>
                    </div>
                </div>
                <div v-if="selectedFile" class="selected-file-chip mb-4">
                    <i class="bi bi-file-earmark-check"></i> Selected: <strong>{{ selectedFile }}</strong>
                </div>
                <div v-else class="text-muted small mb-4">
                    Select a model file above before adding it to the list.
                </div>

                <div v-if="modelCount > 0">
                    <table class="table-pro">
                        <thead>
                            <tr>
                                <th>Model Name</th>
                                <th>Parameters</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(params, key) in uploadPage.models" :key="key">
                                <td>
                                    <div class="model-name-cell"><i class="bi bi-building"></i><strong>{{ key }}</strong></div>
                                </td>
                                <td><div class="param-tags"><span v-for="p in params" :key="p" class="badge-custom">{{ p }}</span></div></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="empty-state mt-4" v-else>
                    <i class="bi bi-inbox"></i>
                    <p>No models uploaded yet. Name your model, select its file, then <strong>Add to List</strong>.</p>
                </div>
            </div>

            <!-- Step 2: Link Parameters -->
            <div class="card-pro mb-4 step-card" v-if="modelCount > 1">
                <div class="step-card-header">
                    <div class="step-badge-lg" :class="{ 'is-done': connectionCount > 0 }">
                        <i v-if="connectionCount > 0" class="bi bi-check-lg"></i>
                        <span v-else>2</span>
                    </div>
                    <div>
                        <h2 class="step-title">Link Shared Parameters</h2>
                        <p class="step-subtitle">Match parameters that represent the same physical quantity across models, so they can be calibrated together.</p>
                    </div>
                </div>

                <div class="connector-rows">
                    <div v-for="(obj, index) in connect" :key="index" class="connector-row">
                        <div class="connector-field">
                            <label class="form-label small text-muted">Model</label>
                            <select v-model="obj.model">
                                <option disabled value="">Choose model</option>
                                <option v-for="name in filteredModels(index)" :key="name" :value="name">{{ name }}</option>
                            </select>
                        </div>
                        <i class="bi bi-arrow-right connector-arrow"></i>
                        <div class="connector-field">
                            <label class="form-label small text-muted">Parameter</label>
                            <select v-model="obj.param">
                                <option disabled value="">Choose parameter</option>
                                <option v-for="param in getAvailableParams(obj.model)" :key="param" :value="param">{{ param }}</option>
                            </select>
                        </div>
                        <button class="icon-btn-danger" @click="removeConnectElement(index)" title="Remove row">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>

                <div class="d-flex gap-2 mt-3">
                    <button class="btn-pro btn-outline-pro" @click="addConnectElement">
                        <i class="bi bi-plus"></i> Add Parameter
                    </button>
                    <button
                        class="btn-pro"
                        @click="connectParams"
                        v-if="connect.length > 1"
                        :disabled="connect.some(o => !o.model || !o.param)"
                    >
                        <i class="bi bi-link-45deg"></i> Connect Selected
                    </button>
                </div>

                <div class="mt-4">
                    <h4 class="h6 text-muted text-uppercase mb-3">Established Connections</h4>
                    <div v-if="connections.length > 0" class="connections-list">
                        <div v-for="(connection, index) in connections" :key="index" class="connection-card">
                            <div class="connection-pills">
                                <template v-for="(obj, idx) in connection" :key="idx">
                                    <span class="connection-pill"><strong>{{ obj.model }}</strong>: {{ obj.param }}</span>
                                    <i v-if="idx < connection.length - 1" class="bi bi-link-45deg connection-link-icon"></i>
                                </template>
                            </div>
                            <button class="icon-btn-danger" @click="removeConnection(index)" title="Remove connection">
                                <i class="bi bi-x-lg"></i>
                            </button>
                        </div>
                    </div>
                    <div v-else class="empty-state-inline">
                        <i class="bi bi-diagram-3"></i> No parameters linked yet — connect matching parameters above.
                    </div>
                </div>
            </div>

            <!-- Step 3: Finalize -->
            <div class="card-pro step-card step-card-final text-center">
                <div class="step-badge-lg mx-auto" :class="{ 'is-done': uploadPage.jointCreated }">
                    <i v-if="uploadPage.jointCreated" class="bi bi-check-lg"></i>
                    <span v-else>3</span>
                </div>
                <h2 class="step-title mt-3">Create Joint Manager</h2>
                <p class="step-subtitle mx-auto step-subtitle-final">
                    Combine the uploaded models and their linked parameters into a single manager for joint calibration.
                </p>

                <div class="summary-chips" v-if="!uploadPage.jointCreated">
                    <span class="summary-chip"><i class="bi bi-building"></i> {{ modelCount }} model{{ modelCount !== 1 ? "s" : "" }}</span>
                    <span class="summary-chip"><i class="bi bi-link-45deg"></i> {{ connectionCount }} linked parameter{{ connectionCount !== 1 ? "s" : "" }}</span>
                </div>

                <button
                    v-if="!uploadPage.jointCreated"
                    class="btn-pro btn-lg px-5 mt-4"
                    @click="createJoint"
                    :disabled="modelCount < 2 || loadingState.active"
                >
                    <span v-if="loadingState.active" class="btn-spinner me-2"></span>
                    {{ loadingState.active ? "Creating…" : "Create Joint Manager" }}
                </button>

                <div v-if="uploadPage.jointCreated" class="joint-success mt-3">
                    <i class="bi bi-check-circle-fill"></i>
                    <div>
                        <strong>Joint Manager Created</strong>
                        <p class="text-muted m-0">Your models are linked and ready for measurement definition.</p>
                    </div>
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
import { loadingState } from "../loadingState";

export default {
    components: { NextButton, BackButton, LogoLine, InputLoader },
    setup() {
        return { loadingState };
    },
    props: {
        uploadPage: { type: Object, required: true },
        socket: { type: Object, required: true },
        mode: { type: String, required: true },
        addPageDone: { type: Function, required: true },
        changePage: { type: Function, required: true },
        sendInChunks: { type: Function, required: true },
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
    computed: {
        modelCount() {
            return Object.keys(this.uploadPage.models).length;
        },
        connectionCount() {
            return this.connections.length;
        },
        steps() {
            return [
                { label: "Upload Models", done: this.modelCount > 0 },
                { label: "Link Parameters", done: this.connectionCount > 0 },
                { label: "Create Joint Manager", done: this.uploadPage.jointCreated },
            ];
        },
        activeStepIndex() {
            if (this.uploadPage.jointCreated) return 2;
            if (this.modelCount < 2) return 0;
            if (this.connectionCount === 0) return 1;
            return 2;
        },
    },
    methods: {
        stepStateClass(index) {
            if (this.steps[index].done) return "is-done";
            if (index === this.activeStepIndex) return "is-active";
            return "";
        },
        loadModel(event) {
            this.sendInChunks(event, "load_model", this.socket);
        },
        selectModel(event) {
            const file = event;
            if (!file) return;
            this.selectedFile = file.name;
            this.selectedModel = file;
            this.$refs.modelInputLoader?.closeModal();

        },
        addModel() {
            if (!this.modelName) {
                alert("Please enter a model name.");
                return;
            }
            if (!this.selectedModel) {
                alert("Please select a model.");
                return;
            }
            this.sendInChunks(this.selectedModel, "add_model", this.socket, { name: this.modelName });
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

.step-card-header {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.step-badge-lg {
    width: 40px;
    height: 40px;
    min-width: 40px;
    border-radius: 50%;
    background: var(--secondary);
    border: 2px solid var(--border-color);
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1rem;
    transition: all 0.25s ease;
}

.step-badge-lg.is-done {
    background: var(--success);
    border-color: var(--success);
    color: #fff;
}

.step-title {
    font-size: 1.25rem;
    margin-bottom: 0.25rem;
}

.step-subtitle {
    color: var(--text-muted);
    margin: 0;
    font-size: 0.9rem;
}

.step-subtitle-final {
    max-width: 480px;
}

.step-count-badge {
    margin-left: auto;
    background: rgba(163, 0, 54, 0.08);
    color: var(--primary);
    padding: 0.3rem 0.75rem;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    white-space: nowrap;
    align-self: flex-start;
}

.step-card-final {
    padding: var(--spacing-xl) var(--spacing-lg);
}

/* Wizard progress rail */
.wizard-rail {
    display: flex;
    align-items: flex-start;
    padding: 0.5rem 1rem 0;
}

.wizard-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
}

.wizard-step-marker {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #fff;
    border: 2px solid var(--border-color);
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.85rem;
    transition: all 0.25s ease;
}

.wizard-step-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text-muted);
    text-align: center;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    white-space: nowrap;
}

.wizard-step.is-done .wizard-step-marker {
    background: var(--success);
    border-color: var(--success);
    color: #fff;
}

.wizard-step.is-active .wizard-step-marker {
    background: var(--primary);
    border-color: var(--primary);
    color: #fff;
    box-shadow: 0 0 0 4px rgba(163, 0, 54, 0.12);
}

.wizard-step.is-done .wizard-step-label,
.wizard-step.is-active .wizard-step-label {
    color: var(--text-main);
}

.wizard-connector {
    flex: 1;
    height: 2px;
    background: var(--border-color);
    margin-top: 15px;
    transition: background 0.3s ease;
}

.wizard-connector.filled {
    background: var(--success);
}

.table-pro {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    overflow: hidden;
}

.table-pro th {
    background: var(--secondary);
    padding: 0.85rem 1rem;
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-muted);
    text-align: left;
}

.table-pro td {
    padding: 0.85rem 1rem;
    border-top: 1px solid var(--border-color);
}

.table-pro tbody tr:hover {
    background: var(--secondary);
}

.model-name-cell {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.model-name-cell i {
    color: var(--primary);
}

.selected-file-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(163, 0, 54, 0.06);
    color: var(--text-main);
    border: 1px solid rgba(163, 0, 54, 0.15);
    padding: 0.5rem 0.9rem;
    border-radius: var(--radius);
    font-size: 0.85rem;
}

.selected-file-chip i {
    color: var(--primary);
}

.empty-state {
    text-align: center;
    padding: 2rem 1rem;
    border: 1px dashed var(--border-color);
    border-radius: var(--radius);
    color: var(--text-muted);
}

.empty-state i {
    font-size: 1.5rem;
    display: block;
    margin-bottom: 0.5rem;
    opacity: 0.6;
}

.empty-state p {
    margin: 0;
    font-size: 0.9rem;
}

.empty-state-inline {
    color: var(--text-muted);
    font-size: 0.9rem;
    padding: 0.75rem 1rem;
    background: var(--secondary);
    border-radius: var(--radius);
}

.connector-rows {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}

.connector-row {
    display: flex;
    align-items: flex-end;
    gap: 0.75rem;
    padding: 0.85rem;
    background: var(--secondary);
    border: 1px solid transparent;
    border-radius: var(--radius);
    transition: border-color 0.2s ease;
}

.connector-row:hover {
    border-color: var(--border-color);
}

.connector-field {
    flex: 1;
    min-width: 0;
}

.connector-arrow {
    color: var(--text-muted);
    margin-bottom: 0.7rem;
    font-size: 1.1rem;
}

.icon-btn-danger {
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--danger);
    width: 38px;
    height: 38px;
    border-radius: var(--radius);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s ease;
    flex-shrink: 0;
}

.icon-btn-danger:hover {
    background: rgba(220, 53, 69, 0.08);
    border-color: var(--danger);
}

.connections-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.connection-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0.6rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
}

.connection-pills {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
}

.connection-link-icon {
    color: var(--text-muted);
}

.summary-chips {
    display: flex;
    justify-content: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-top: 1.25rem;
}

.summary-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: var(--secondary);
    border: 1px solid var(--border-color);
    padding: 0.4rem 0.9rem;
    border-radius: 20px;
    font-size: 0.85rem;
    color: var(--text-main);
    font-weight: 500;
}

.summary-chip i {
    color: var(--primary);
}

.joint-success {
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    text-align: left;
    padding: 1rem 1.25rem;
    background: rgba(25, 135, 84, 0.06);
    border: 1px solid rgba(25, 135, 84, 0.25);
    border-radius: var(--radius);
}

.joint-success i {
    color: var(--success);
    font-size: 1.5rem;
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
