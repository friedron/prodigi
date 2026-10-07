<template>
    <div class="variable-page container-fluid px-0">
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
                <h1 class="h3 mb-0">Definition of A-priori Uncertain Variables</h1>
                <div class="d-flex gap-2 align-items-center">
                    <label for="variableInput" class="btn-pro btn-outline-pro mb-0">
                        <i class="bi bi-upload"></i> Load from JSON
                        <input type="file" id="variableInput" @change="loadVariables" accept=".json" class="d-none" />
                    </label>
                    <button class="btn-pro" @click="addVariable">
                        <i class="bi bi-plus-circle"></i> Add Variable
                    </button>
                </div>
            </div>

            <div class="table-responsive">
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
                        <tr v-for="variable in variablePage.data.variables" :key="variable.id" @click="openEditModal(variable)" class="cursor-pointer">
                            <td class="fw-bold text-primary">{{ variable.name || 'Unnamed' }}</td>
                            <td><span class="badge rounded-pill bg-light text-dark border">{{ variable.distribution || 'None' }}</span></td>
                            <td><code>{{ variable.distParam1 ?? '-' }}</code></td>
                            <td><code>{{ variable.distParam2 ?? '-' }}</code></td>
                            <td><code>{{ variable.scale ?? '' }}</code></td>
                            <td><code>{{ variable.shift ?? '' }}</code></td>
                            <td class="text-end">
                                <div class="d-flex justify-content-end gap-1">
                                    <button class="btn-action edit" @click.stop="openEditModal(variable)" title="Edit">
                                        <i class="bi bi-pencil-square"></i>
                                    </button>
                                    <button class="btn-action remove" @click.stop="removeVariable(variable.id)" title="Remove">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                        <tr v-if="variablePage.data.variables.length === 0">
                            <td colspan="7" class="text-center py-5 text-muted">
                                <i class="bi bi-info-circle fs-2 d-block mb-2"></i>
                                No variables defined. Click "Add Variable" to start.
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="mt-4 d-flex justify-content-between align-items-center">
                <button
                    v-if="variablePage.data.variables.length > 0"
                    class="btn-pro btn-outline-pro"
                    @click="saveVariables"
                >
                    <i class="bi bi-download"></i> Export to File
                </button>
                <div class="ms-auto">
                    <NextButton :nextPage="'sample'" :available="isPageDone()" :changePage="changePage" />
                </div>
            </div>
        </div>

        <!-- Edit Variable Modal -->
        <EditParamModal
            v-if="showModal"
            :visible="showModal"
            :variable="selectedVariable"
            @close-modal="closeEditModal"
            @save-changes="updateVariable"
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
        variablePage: { type: Object, required: true },
        changePage: { type: Function, required: true },
        addPageDone: { type: Function, required: true },
        sendInChunks: { type: Function, required: true },
    },
    data() {
        return {
            showModal: false,
            selectedVariable: null,
        };
    },
    watch: {
        variablePage: {
            handler(newVal) {
                if (
                    newVal.samples.length > 0 &&
                    Object.keys(newVal.qoiTable).length > 0 &&
                    newVal.data.variables.length > 0
                ) {
                    this.addPageDone("variables");
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
        addVariable() {
            const newVariable = {
                id: this.generateId(),
                name: "variable_" + (this.variablePage.data.variables.length + 1),
                distribution: "",
                distParam1: null,
                distParam2: null,
                scale: null,
                shift: null,
            };
            this.variablePage.data.variables.push(newVariable);
            this.openEditModal(newVariable);
        },
        removeVariable(id) {
            this.variablePage.data.variables = this.variablePage.data.variables.filter((variable) => variable.id !== id);
            this.refreshVariables();
        },
        openEditModal(variable) {
            this.selectedVariable = { ...variable };
            this.showModal = true;
        },
        closeEditModal() {
            this.showModal = false;
            this.selectedVariable = null;
        },
        updateVariable(updatedVariable) {
            const index = this.variablePage.data.variables.findIndex((variable) => variable.id === updatedVariable.id);
            if (index !== -1) {
                this.variablePage.data.variables.splice(index, 1, updatedVariable);
            }
            this.closeEditModal();
            this.refreshVariables();
        },
        refreshVariables() {
            this.socket.emit("refresh_variables", this.variablePage.data.variables);
        },
        loadVariables(event) {
            const file = event.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            let updated = false;
            reader.onload = async (loadEvent) => {
                try {
                    const data = JSON.parse(loadEvent.target.result);
                    if (!("variables" in data)) {
                        throw new Error("Invalid file format.");
                    }
                    this.variablePage.data.variables = data["variables"];
                    for (let variable of this.variablePage.data.variables) {
                        if (!variable.id) variable["id"] = this.generateId();
                    }
                    updated = true;
                } catch (error) {
                    console.log("Error: ", error.message);
                    alert("Failed to load variables: " + error.message);
                }
            };
            reader.readAsText(file);
            reader.onloadend = () => {
                if (updated) {
                    this.refreshVariables();
                }
                event.target.value = ''; // Reset input
            };
        },
        saveVariables() {
            try {
                let filtered = { variables: this.variablePage.data.variables.map(({ id, ...rest }) => rest) };
                const data = JSON.stringify(filtered, null, 2);
                const blob = new Blob([data], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = url;
                link.download = "variableset.json";
                link.click();
                URL.revokeObjectURL(url);
            } catch (error) {
                console.log("Error saving file: ", error);
            }
        },
        isPageDone() {
            const isDone =
                this.variablePage.data.variables.length > 0 &&
                this.variablePage.data.variables.every(
                    (variable) =>
                        variable.name && variable.distribution && variable.distParam1 !== null && variable.distParam2 !== null
                );
            if (isDone) {
                this.addPageDone("variables");
            }
            return isDone;
        },
    },
};
</script>

<style scoped>
.variable-page {
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
