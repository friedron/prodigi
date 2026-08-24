<template>
    <h1 class="text-center mb-4">Select features and effects</h1>
    <!-- Button to open modal -->
    <button class="btn-pro mb-3" @click="showModal = true">Select Features and Effects</button>

    <!-- Modal Popup -->
    <div v-if="showModal" class="modal-backdrop" @click.self="showModal = false">
        <div class="modal-dialog card-pro" @click.stop>
            <div class="modal-header mb-4">
                <h2 class="modal-title">Select Features and Effects</h2>
                <button type="button" class="btn-close-custom" @click="showModal = false">&times;</button>
            </div>
            <div class="modal-body">
                <h4 class="h6 text-muted text-uppercase fw-bold mb-3">Select Features</h4>
                <div class="mb-4">
                    <div v-for="(mode, index) in Object.keys(variablePage.inputStats)" :key="`mode-${index}`" class="form-check mb-2">
                        <input
                            class="form-check-input"
                            type="checkbox"
                            v-model="tempSelectedFeats"
                            :value="mode"
                            :id="`mode-${mode}`"
                        />
                        <label class="form-check-label ms-2" :for="`mode-${mode}`">{{ mode }}</label>
                    </div>
                </div>
                <h4 class="h6 text-muted text-uppercase fw-bold mb-3">Select Effects</h4>
                <div class="mb-4">
                    <div v-for="(effect, index) in Object.keys(variablePage.qoiTable)" :key="`effect-${index}`" class="form-check mb-2">
                        <input
                            class="form-check-input"
                            type="checkbox"
                            v-model="tempSelectedEffects"
                            :value="effect"
                            :id="`effect-${effect}`"
                        />
                        <label class="form-check-label ms-2" :for="`effect-${effect}`">{{ effect }}</label>
                    </div>
                </div>
            </div>
            <div class="modal-footer d-flex justify-content-end gap-2 pt-3 border-top">
                <button class="btn-pro btn-outline-pro" @click="showModal = false">Cancel</button>
                <button class="btn-pro" @click="applySelection">Apply Selection</button>
            </div>
        </div>
    </div>
</template>
<script>
export default {
    props: {
        surrogatePage: { type: Object, required: true },
        variablePage: { type: Object, required: true },
        socket: { type: Object, required: true },
    },
    data() {
        return {
            showModal: false,
            tempSelectedFeats: Object.keys(this.variablePage.inputStats),
            tempSelectedEffects: Object.keys(this.variablePage.qoiTable),
        };
    },
    methods: {
        applySelection() {
            if (this.tempSelectedFeats.length === 0 || this.tempSelectedEffects.length === 0) {
                alert("Please select at least one feature and one effect.");
                return;
            }
            // Get original order arrays
            const originalFeats = Object.keys(this.variablePage.inputStats);
            const originalEffects = Object.keys(this.variablePage.qoiTable);

            // Sort tempSelectedFeats according to original order
            const orderedFeats = originalFeats.filter((feat) => this.tempSelectedFeats.includes(feat));

            // Sort tempSelectedEffects according to original order
            const orderedEffects = originalEffects.filter((effect) => this.tempSelectedEffects.includes(effect));

            // Copy ordered selections to actual data
            this.surrogatePage.selectedFeats = orderedFeats;
            this.surrogatePage.selectedEffects = orderedEffects;

            this.showModal = false;
        },
    },
    watch: {
        showModal(val) {
            // When opening modal, sync temp selections with current selections
            if (val) {
                this.tempSelectedFeats = [...this.surrogatePage.selectedFeats];
                this.tempSelectedEffects = [...this.surrogatePage.selectedEffects];
            }
        },
    },
};
</script>
<style scoped>
.modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: var(--z-modal-backdrop);
}

.modal-dialog {
    width: 100%;
    max-width: 500px;
    margin: 0 var(--spacing-md);
    background: white;
    position: relative;
    z-index: var(--z-modal-dialog);
}

.btn-close-custom {
    background: none;
    border: none;
    font-size: 2rem;
    line-height: 1;
    cursor: pointer;
    color: var(--text-muted);
    transition: color 0.2s;
}

.btn-close-custom:hover {
    color: var(--danger);
}
</style>
