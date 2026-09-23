<template>
    <div
        v-if="showLoader"
        class="modal"
        tabindex="-1"
        role="dialog"
        style="display: block; background: rgba(0, 0, 0, 0.5)"
    >
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Building Report Information</h5>
                    <button type="button" class="btn-close" @click="closeModal"></button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <div class="form-inline">
                            <label>Building Name</label>
                            <input v-model="this.building_name" type="text" class="form-control" placeholder="" />
                        </div>
                        <div class="form-inline">
                            <label>Address</label>
                            <input v-model="this.address" type="text" class="form-control" placeholder="" />
                        </div>
                        <div class="form-inline">
                            <label>Author</label>
                            <input v-model="this.author" type="text" class="form-control" placeholder="" />
                        </div>
                        <div class="form-inline">
                            <label>Owner</label>
                            <input v-model="this.owner" type="text" class="form-control" placeholder="" />
                        </div>
                        <div v-if="!isFormValid" class="mt-3 text-danger text-center">
                            Please fill in all the information above to enable saving.
                        </div>

                        <template v-if="isFormValid">
                            <div class="mt-3">
                                <div class="text-center">
                                    <button class="btn btn-primary" @click="save">Download</button>
                                </div>
                            </div>
                        </template>
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
        prefillBuildingName: {
            type: String,
            default: "",
        },
        prefillAddress: {
            type: String,
            default: "",
        },
    },
    emits: ["close", "save"],
    computed: {
        isFormValid() {
            return (
                this.building_name.trim() !== "" &&
                this.address.trim() !== "" &&
                this.author.trim() !== "" &&
                this.owner.trim() !== ""
            );
        },
    },
    methods: {
        save() {
            this.$emit("save", {
                building_name: this.building_name,
                address: this.address,
                author: this.author,
                owner: this.owner,
            });
            this.closeModal();
        },
        closeModal() {
            this.$emit("close");
            this.showLoader = false;
        },
    },
    data() {
        return {
            showLoader: true,
            building_name: this.prefillBuildingName || "",
            address: this.prefillAddress || "",
            author: "",
            owner: "",
        };
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
    max-width: 600px;
    height: 70vh;
}
.modal-body {
    max-height: calc(100vh - 200px);
    overflow-y: auto;
}
</style>
