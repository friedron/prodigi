<template>
    <div class="param-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'info'" :changePage="changePage" />

        <div class="card-pro content-card mt-4">
            <div class="d-flex align-items-center justify-content-between mb-4 pb-3 border-bottom">
                <h1 class="h3 mb-0">Definition of A-priori Uncertain Parameters</h1>
                <div class="d-flex gap-2 align-items-center">
                    <label for="paramInput" class="btn-pro btn-outline-pro mb-0">
                        <i class="bi bi-upload"></i> Load from JSON
                        <input type="file" id="paramInput" @change="loadParams" accept=".json" class="d-none" />
                    </label>
                    <button class="btn-pro" @click="addParam">
                        <i class="bi bi-plus-circle"></i> Add Parameter
                    </button>
                </div>
            </div>

            <div class="table-custom-responsive">
                <table class="table-custom table-hover align-middle custom-table">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Distribution</th>
                            <th>Param 1</th>
                            <th>Param 2</th>
                            <th>Scale</th>
                            <th>Shift</th>
                            <th class="text-end">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="param in paramPage.data.params" :key="param.id" @click="openEditModal(param)" class="cursor-pointer">
                            <td class="fw-bold text-primary">{{ param.name || 'Unnamed' }}</td>
                            <td><span class="badge rounded-pill bg-light text-dark border">{{ param.distribution || 'None' }}</span></td>
                            <td><code>{{ param.distParam1 ?? '-' }}</code></td>
                            <td><code>{{ param.distParam2 ?? '-' }}</code></td>
                            <td><code>{{ param.scale ?? '1.0' }}</code></td>
                            <td><code>{{ param.shift ?? '0.0' }}</code></td>
                            <td class="text-end">
                                <div class="d-flex justify-content-end gap-1">
                                    <button class="btn-action edit" @click.stop="openEditModal(param)" title="Edit">
                                        <i class="bi bi-pencil-square"></i>
                                    </button>
                                    <button class="btn-action remove" @click.stop="removeParam(param.id)" title="Remove">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                        <tr v-if="paramPage.data.params.length === 0">
                            <td colspan="7" class="text-center py-5 text-muted">
                                <i class="bi bi-info-circle fs-2 d-block mb-2"></i>
                                No parameters defined. Click "Add Parameter" to start.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="mt-4 d-flex justify-content-between align-items-center">
                <button 
                    v-if="paramPage.data.params.length > 0" 
                    class="btn-pro btn-outline-pro" 
                    @click="saveParams"
                >
                    <i class="bi bi-download"></i> Export to File
                </button>
                <div class="ms-auto">
                    <NextButton :nextPage="'sample'" :available="isPageDone()" :changePage="changePage" />
                </div>
            </div>
        </div>

        <!-- Edit Parameter Modal -->
        <EditParamModal
            v-if="showModal"
            :visible="showModal"
            :param="selectedParam"
            @close-modal="closeEditModal"
            @save-changes="updateParam"
        />
    </div>
</template>

<script>
import EditParamModal from "../EditParamModal.vue";
import NextButton from "../NextButton.vue";
import BackButton from "../BackButton.vue";
import LogoLine from "../LogoLine.vue";

export default {
    components: {
        EditParamModal,
        NextButton,
        BackButton,
        LogoLine,
    },
    props: {
        socket: { type: Object, required: true },
        paramPage: { type: Object, required: true },
        changePage: { type: Function, required: true },
        addPageDone: { type: Function, required: true },
        sendInChunks: { type: Function, required: true },
    },
    data() {
        return {
            showModal: false,
            selectedParam: null,
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
    methods: {
        generateId() {
            return "_" + Math.random().toString(36).slice(2, 9);
        },
        addParam() {
            const newParam = {
                id: this.generateId(),
                name: "param_" + (this.paramPage.data.params.length + 1),
                distribution: "",
                distParam1: null,
                distParam2: null,
                scale: 1.0,
                shift: 0.0,
            };
            this.paramPage.data.params.push(newParam);
            this.openEditModal(newParam);
        },
        removeParam(id) {
            this.paramPage.data.params = this.paramPage.data.params.filter((param) => param.id !== id);
            this.refreshParams();
        },
        openEditModal(param) {
            this.selectedParam = { ...param };
            this.showModal = true;
        },
        closeEditModal() {
            this.showModal = false;
            this.selectedParam = null;
        },
        updateParam(updatedParam) {
            const index = this.paramPage.data.params.findIndex((param) => param.id === updatedParam.id);
            if (index !== -1) {
                this.paramPage.data.params.splice(index, 1, updatedParam);
            }
            this.closeEditModal();
            this.refreshParams();
        },
        refreshParams() {
            this.socket.emit("refresh_variables", this.paramPage.data.params);
        },
        loadParams(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            let updated = false;
            reader.onload = async (loadEvent) => {
                try {
                    const data = JSON.parse(loadEvent.target.result);
                    if (!("params" in data)) {
                        throw new Error("Invalid file format.");
                    }
                    this.paramPage.data.params = data["params"];
                    for (let param of this.paramPage.data.params) {
                        if (!param.id) param["id"] = this.generateId();
                    }
                    updated = true;
                } catch (error) {
                    console.log("Error: ", error.message);
                    alert("Failed to load parameters: " + error.message);
                }
            };
            reader.readAsText(file);
            reader.onloadend = () => {
                if (updated) {
                    this.refreshParams();
                }
                event.target.value = ''; // Reset input
            };
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
        isPageDone() {
            const isDone =
                this.paramPage.data.params.length > 0 &&
                this.paramPage.data.params.every(
                    (param) =>
                        param.name && param.distribution && param.distParam1 !== null && param.distParam2 !== null
                );
            if (isDone) {
                this.addPageDone("params");
            }
            return isDone;
        },
    },
};
</script>

<style scoped>
.param-page {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-xl);
}

.custom-table {
    border-collapse: separate;
    border-spacing: 0;
    margin-bottom: 0;
}

.custom-table thead th {
    background-color: var(--secondary);
    border-bottom: 2px solid var(--border-color);
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    padding: var(--spacing-md);
}

.custom-table tbody td {
    padding: var(--spacing-md);
    border-bottom: 1px solid var(--border-color);
}

.cursor-pointer {
    cursor: pointer;
}

.custom-table tbody tr:last-child td {
    border-bottom: none;
}

.btn-action {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    border: 1px solid var(--border-color);
    background: white;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    cursor: pointer;
    color: var(--text-muted);
}

.btn-action.edit:hover {
    color: var(--primary);
    border-color: var(--primary);
    background: rgba(163, 0, 54, 0.05);
}

.btn-action.remove:hover {
    color: var(--danger);
    border-color: var(--danger);
    background: rgba(220, 53, 69, 0.05);
}

code {
    background: var(--secondary);
    padding: 2px 4px;
    border-radius: 4px;
    font-size: 0.85rem;
    color: var(--text-main);
}

.badge {
    font-weight: 500;
}

.text-primary {
    color: var(--primary) !important;
}
</style>
