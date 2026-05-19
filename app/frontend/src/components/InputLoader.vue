<template>
    <button class="btn-pro" @click="showInputLoader = true">
        <i class="bi bi-upload"></i> Input Loader
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
                            />
                            <label for="fileInput" class="file-upload-label">
                                <span v-if="!fileInput">Choose a file or drag it here</span>
                                <span v-else class="text-primary fw-bold">{{ fileInput.name }}</span>
                            </label>
                        </div>
                    </div>
                </div>

                <div class="modal-footer d-flex justify-content-end gap-2 pt-3 border-top">
                    <button type="button" class="btn-pro btn-outline-pro" @click="closeModal">Cancel</button>
                    <button type="button" class="btn-pro" @click="load_file" :disabled="!fileInput && !selected_file">
                        Load Data
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
        dkgApiStatus: { type: String, required: true },
        dkgToken: { type: String, required: true },
        fileType: { type: String, default: ".csv" },
        loadType: { type: String, required: true },
    },
    emits: ["load-file", "close"],
    data() {
        return {
            showInputLoader: false,
            fileInput: null,
            selected_file: null,
        };
    },
    methods: {
        handleFileUpload(event) {
            this.fileInput = event.target.files[0];
        },
        closeModal() {
            this.showInputLoader = false;
            this.$emit("close");
        },
        load_file() {
            if (this.selected_file) {
                this.socket.emit("dkg_get_file_data", { file: this.selected_file, type: this.loadType });
            } else if (this.fileInput) {
                this.$emit("load-file", this.fileInput);
            } else {
                alert("Please select a file.");
            }
        },
    },
    mounted() {
        const events = ["dkg_file_data", "labels_loaded", "features_loaded", "load_model", "zmean_loaded", "sigma_loaded", "building_loaded"];
        events.forEach(event => {
            this.socket.on(event, () => this.closeModal());
        });
    }
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
</style>
