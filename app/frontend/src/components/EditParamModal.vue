<template>
    <Teleport to="body">
        <div
            class="pro-modal-backdrop"
            @click.self="closeModal"
            v-if="visible"
        >
            <div class="pro-modal-dialog card-pro">
                <div class="modal-header border-bottom mb-4 pb-2 d-flex justify-content-between align-items-center">
                    <h5 class="modal-title h4 mb-0">Edit Variable</h5>
                    <button type="button" class="btn-close-custom" @click="closeModal">
                        <i class="bi bi-x-lg"></i>
                    </button>
                </div>
                
                <div class="modal-body">
                    <div class="form-section mb-4">
                        <label for="variableName" class="form-label">Variable Name</label>
                        <input type="text" id="variableName" v-model="variable.name" placeholder="e.g., YoungsModulus" />
                    </div>

                    <div class="form-section mb-4">
                        <label for="distribution" class="form-label">Distribution</label>
                        <select id="distribution" v-model="variable.distribution">
                            <option value="" selected disabled hidden>Choose Distribution</option>
                            <option value="normal">Normal</option>
                            <option value="uniform">Uniform</option>
                            <option value="logNormal">LogNormal</option>
                            <option value="beta">Beta</option>
                            <option value="exponential">Exponential</option>
                        </select>
                    </div>

                    <div v-if="variable.distribution === 'normal' || variable.distribution === 'logNormal'" class="row g-3 mb-4">
                        <div class="col-6">
                            <label for="distParam1" class="form-label">Mu (Mean)</label>
                            <input type="number" id="distParam1" v-model.number="variable.distParam1" step="any" />
                        </div>
                        <div class="col-6">
                            <label for="distParam2" class="form-label">Sigma (Std Dev)</label>
                            <input type="number" id="distParam2" v-model.number="variable.distParam2" step="any" />
                        </div>
                    </div>

                    <div v-if="variable.distribution === 'uniform' || variable.distribution === 'beta'" class="row g-3 mb-4">
                        <div class="col-6">
                            <label for="distParam1" class="form-label">A (Min / Alpha)</label>
                            <input type="number" id="distParam1" v-model.number="variable.distParam1" step="any" />
                        </div>
                        <div class="col-6">
                            <label for="distParam2" class="form-label">B (Max / Beta)</label>
                            <input type="number" id="distParam2" v-model.number="variable.distParam2" step="any" />
                        </div>
                    </div>

                    <div v-if="variable.distribution === 'exponential'" class="form-section mb-4">
                        <label for="distParam1" class="form-label">Lambda (Rate)</label>
                        <input type="number" id="distParam1" v-model.number="variable.distParam1" step="any" />
                    </div>

                    <!-- Optional Bounds/Moments -->
                    <div class="optional-section border-top pt-4">
                        <label for="optional" class="form-label text-muted small text-uppercase fw-bold">Advanced Settings (Optional)</label>
                        <select id="optional" v-model="variable.optional" class="mb-3">
                            <option value="" selected>None</option>
                            <option value="bounds">Set Bounds</option>
                            <option value="moments">Set Moments</option>
                        </select>

                        <div v-if="variable.optional === 'bounds'" class="row g-3">
                            <div class="col-6">
                                <label for="minBound" class="form-label">Min Bound</label>
                                <input type="number" id="minBound" v-model.number="variable.minBound" step="any" />
                            </div>
                            <div class="col-6">
                                <label for="maxBound" class="form-label">Max Bound</label>
                                <input type="number" id="maxBound" v-model.number="variable.maxBound" step="any" />
                            </div>
                        </div>

                        <div v-if="variable.optional === 'moments'" class="row g-3">
                            <div class="col-6">
                                <label for="mean" class="form-label">Mean</label>
                                <input type="number" id="mean" v-model.number="variable.mean" step="any" />
                            </div>
                            <div class="col-6">
                                <label for="var" class="form-label">Variance</label>
                                <input type="number" id="var" v-model.number="variable.var" step="any" />
                            </div>
                        </div>
                    </div>
                </div>

                <div class="modal-footer d-flex gap-2 justify-content-end mt-4 pt-3 border-top">
                    <button type="button" class="btn-pro btn-outline-pro" @click="closeModal">Cancel</button>
                    <button type="button" class="btn-pro" @click="saveChanges">Save Changes</button>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script>
export default {
    props: {
        visible: { type: Boolean, required: true },
        variable: { type: Object, required: true },
    },
    methods: {
        closeModal() {
            this.$emit("close-modal");
        },
        saveChanges() {
            this.$emit("save-changes", this.variable);
        },
    },
};
</script>

<style scoped>
.pro-modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: var(--z-modal-backdrop);
}

.pro-modal-dialog {
    width: 100%;
    max-width: 500px;
    max-height: 90vh;
    overflow-y: auto;
    margin: 0;
    position: relative;
    z-index: var(--z-modal-dialog);
    animation: modal-enter 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    pointer-events: auto;
}

@keyframes modal-enter {
    from { transform: scale(0.9) translateY(20px); opacity: 0; }
    to { transform: scale(1) translateY(0); opacity: 1; }
}

.form-label {
    display: block;
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--text-muted);
    margin-bottom: 0.4rem;
}

.btn-close-custom {
    background: none;
    border: none;
    font-size: 1.25rem;
    color: var(--text-muted);
    cursor: pointer;
    transition: color 0.2s ease;
    padding: 0;
    line-height: 1;
}

.btn-close-custom:hover {
    color: var(--primary);
}

.optional-section {
    background-color: var(--secondary);
    margin: 0 -1.5rem;
    padding: 1rem 1.5rem;
}

/* Custom scrollbar for the modal dialog */
.pro-modal-dialog::-webkit-scrollbar {
    width: 6px;
}
.pro-modal-dialog::-webkit-scrollbar-track {
    background: transparent;
}
.pro-modal-dialog::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 10px;
}
</style>
