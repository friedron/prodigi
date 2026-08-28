<template>
    <button class="btn-pro" @click="showInputLoader = true">
        <i class="bi bi-upload"></i> Data Loader
    </button>

    <Teleport to="body">
        <div
            v-if="showInputLoader"
            class="pro-modal-backdrop"
            @click.self="closeModal"
        >
            <div class="pro-modal-dialog card-pro" @click.stop>
                <div class="modal-header mb-4">
                    <h2 class="modal-title">Load Data</h2>
                    <button type="button" class="btn-close-custom" @click="closeModal">&times;</button>
                </div>
                
                <div class="modal-body">
                    <div class="form-group mb-4">
                        <label class="d-block mb-2 fw-bold">Load File from Your Computer</label>
                        <div class="file-upload-wrapper">
                            <input
                                type="file"
                                id="fileInput"
                                class="file-input-hidden"
                                @change="handleFileUpload"
                                :accept="fileType"
                                :disabled="isLoading"
                            />
                            <label for="fileInput" class="file-upload-label">
                                <span v-if="!fileInput">Choose a file or drag it here</span>
                                <span v-else class="text-primary fw-bold">{{ fileInput.name }}</span>
                            </label>
                        </div>
                        <div v-if="isLoading" class="loading-row mt-3">
                            <span class="btn-spinner"></span> Loading data&hellip;
                        </div>
                    </div>
                </div>

                <div class="modal-footer d-flex justify-content-end gap-2 pt-3 border-top">
                    <button type="button" class="btn-pro btn-outline-pro" @click="closeModal">Cancel</button>
                    <button type="button" class="btn-pro" @click="load_file" :disabled="!fileInput || isLoading">
                        <span v-if="isLoading" class="btn-spinner"></span>
                        {{ isLoading ? "Loading…" : "Load Data" }}
                    </button>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script>
export default {
    props: {
        socket: { type: Object, required: true },
        fileType: { type: String, default: ".csv" },
        loadType: { type: String, required: true },
    },
    emits: ["load-file", "close"],
    data() {
        return {
            showInputLoader: false,
            fileInput: null,
            isLoading: false,
        };
    },
    methods: {
        handleFileUpload(event) {
            this.fileInput = event.target.files[0];
        },
        closeModal() {
            this.showInputLoader = false;
            this.isLoading = false;
            this.$emit("close");
        },
        load_file() {
            if (this.fileInput) {
                this.isLoading = true;
                this.$emit("load-file", this.fileInput);
            } else {
                alert("Please select a file.");
            }
        },
    },
    mounted() {
        // These are the exact events the backend fires once a load actually
        // finishes - tying the spinner to them (rather than a generic "any
        // socket activity" timer) means it stays up for the full duration of
        // slow parses/unpickles instead of fading out mid-request.
        this._loadCompleteHandler = () => this.closeModal();
        this._loadEvents = ["labels_loaded", "features_loaded", "load_model", "zmean_loaded", "sigma_loaded", "building_loaded"];
        this._loadEvents.forEach(event => {
            this.socket.on(event, this._loadCompleteHandler);
        });
        this._errorHandler = () => {
            this.isLoading = false;
        };
        this.socket.on("error", this._errorHandler);
    },
    beforeUnmount() {
        this._loadEvents.forEach(event => this.socket.off(event, this._loadCompleteHandler));
        this.socket.off("error", this._errorHandler);
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
    margin: 0 var(--spacing-md);
    background: white;
    position: relative;
    z-index: var(--z-modal-dialog);
    pointer-events: auto;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-title {
    font-size: 1.5rem;
    margin: 0;
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

.file-upload-wrapper {
    position: relative;
    width: 100%;
}

.file-input-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
}

.file-upload-label {
    display: block;
    padding: var(--spacing-xl) var(--spacing-md);
    border: 2px dashed var(--border-color);
    border-radius: var(--radius);
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    background: var(--secondary);
}

.file-upload-label:hover {
    border-color: var(--primary);
    background: rgba(163, 0, 54, 0.02);
}

.loading-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--text-muted);
    font-size: 0.9rem;
}

.btn-spinner {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid rgba(127, 127, 127, 0.35);
    border-top-color: currentColor;
    animation: btn-spin 0.7s linear infinite;
    display: inline-block;
    flex-shrink: 0;
}

@keyframes btn-spin {
    to { transform: rotate(360deg); }
}
</style>
