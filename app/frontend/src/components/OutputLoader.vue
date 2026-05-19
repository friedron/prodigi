<template>
    <button class="btn-pro mb-3" @click="showInputLoader = !showInputLoader">{{ title }}</button>
    <div
        v-if="showInputLoader"
        class="modal"
        tabindex="-1"
        role="dialog"
        style="display: block; background: rgba(0, 0, 0, 0.5)"
    >
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Save Data</h5>
                    <button type="button" @click="closeModal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label for="fileInput"><b>Save to Your Computer</b></label>
                        <div>
                            <button class="btn-pro" @click="save">Save</button>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>OR</label>
                    </div>
                    <div class="form-group">
                        <label><b>Save to DKG API</b></label>
                        <div v-if="dkgApiStatus !== 'success' || token == ''">
                            <div class="form-inline">
                                <label>Authentication Token</label>
                                <input v-model="this.dkgToken" type="text" class="form-control" placeholder="" />
                            </div>
                            <button class="btn-pro" @click="login">Login</button>
                        </div>
                    </div>
                    <div v-if="dkgApiStatus === 'success' && selection === null">
                        <div class="form-inline">
                            <label>name</label>
                            <input v-model="name" type="text" class="form-control" placeholder="" />
                        </div>
                        <div class="form-inline">
                            <label>code</label>
                            <input v-model="code" type="text" class="form-control" placeholder="" />
                        </div>
                        <div class="form-inline">
                            <label>type</label>
                            <input v-model="type" type="text" class="form-control" placeholder="" />
                        </div>
                        <div class="form-inline">
                            <label>existsMeasurementData</label>
                            <input v-model="existsMeasurementData" type="text" class="form-control" placeholder="" />
                        </div>
                        <div class="form-inline">
                            <label>city</label>
                            <input v-model="city" type="text" class="form-control" placeholder="" />
                        </div>
                        <div class="form-inline">
                            <label>assetManagerDID</label>
                            <input v-model="assetManagerDID" type="text" class="form-control" placeholder="" />
                        </div>
                        <div class="form-inline">
                            <label>zone</label>
                            <input v-model="zone" type="text" class="form-control" placeholder="" />
                        </div>
                        <button class="btn-pro" @click="getData">Find Bulding</button>
                    </div>
                    <div v-if="selection !== null">
                        <label>Select Building</label>
                        <select v-model="selected" class="form-control">
                            <option v-for="option in selection" :key="option" :value="option">
                                {{ option }}
                            </option>
                        </select>
                        <label class="mt-3">File Name</label>
                        <input type="text" v-model="fileName" class="form-control" />
                        <label class="mt-3">Document Type</label>
                        <input type="text" v-model="docType" class="form-control" />
                        <label class="mt-3">Title</label>
                        <input type="text" v-model="fileTitle" class="form-control" />
                        <label class="mt-3">Desciption</label>
                        <input type="text" v-model="fileDescription" class="form-control" />
                        <button class="btn-pro mt-3" @click="saveToDkg">
                            Upload to DKG
                        </button>
                        <div class="mt-3" v-if="api_status !== ''">
                            {{ api_status }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        socket: {
            type: Object,
            required: true,
        },
        dkgApiStatus: {
            type: String,
            required: true,
        },
        dkgToken: {
            type: String,
            required: true,
        },
        title: {
            type: String,
            required: true,
        },
        mode : {
            type: String,
            required: true,
        },
    },
    emits: ["save-file"],
    methods: {
        save() {
            this.$emit("save-file");
            this.closeModal();
        },
        closeModal() {
            this.showInputLoader = false;
        },
        login() {
            this.socket.emit("dkg_login", { token: this.dkgToken });
        },
        getData() {
            this.socket.emit("dkg_get_building", {
                name: this.name,
                code: this.code,
                type: this.type,
                existsMeasurementData: this.existsMeasurementData,
                city: this.city,
                assetManagerDID: this.assetManagerDID,
                zone: this.zone,
                token: this.dkgToken,
            });
        },
        saveToDkg() {
            this.socket.emit("dkg_save_file", {
                mode: this.mode,
                token: this.dkgToken,
                building: this.selected,
                fileName: this.fileName,
                type: this.fileType,
                title: this.fileTitle,
                description: this.fileDescription,
            })
        },
    },
    data() {
        return {
            showInputLoader: false,
            name: "",
            code: "",
            type: "",
            existsMeasurementData: "",
            city: "",
            assetManagerDID: "",
            zone: "",
            selection: null,
            selected: null,
            fileName: "",
            fileType: "",
            fileTitle: "",
            fileDescription: "",
            api_status: "",
        };
    },
    mounted() {
        this.socket.on("building_selection", (data) => {
            this.selection = data;
        });
        this.socket.on("dkg_save_file_status", (data) => {
            if (data === "success") {
                this.api_status = "File sent to DKG.";
            } else {
                this.api_status = "Error saving file, please try again.";
            }
        });
    },
    beforeUnmount() {
        this.socket.off("building_selection");
    },
};
</script>

<style scoped>
input,
select,
textarea {
    background-color: white !important;
    color: black !important;
}
.col-auto {
    margin: 5px;
}
label {
    text-align: center;
    margin: 5px;
}
.modal-dialog {
    margin-top: 150px;
}
</style>
