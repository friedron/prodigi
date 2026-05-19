<template>
    <div
        class="modal"
        tabindex="-1"
        role="dialog"
        style="display: block; background: rgba(0, 0, 0, 0.5)"
        v-if="visible"
    >
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Edit Layer</h5>
                    <button type="button" class="close" @click="closeModal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label for="numOfNeurons">Number of Neurons</label>
                        <input type="number" id="numOfNeurons" class="form-control" v-model="layer.numOfNeurons" />
                    </div>

                    <div class="form-group">
                        <label for="activationFunction">Activation Function</label>
                        <select id="activationFunction" class="form-control" v-model="layer.activationFunction">
                            <option value="" selected disabled hidden>Choose Activation Function</option>
                            <option value="relu">Relu</option>
                            <option value="sigmoid">Sigmoid</option>
                            <option value="tanh">Tanh</option>
                            <option value="leakyrelu">Leakyrelu</option>
                            <option value="softmax">Softmax</option>
                            <option value="none">None</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="dropout">Dropout</label>
                        <input type="number" id="dropout" class="form-control" v-model="layer.dropout" step="0.1" />
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn-pro btn-outline-pro" @click="closeModal">Close</button>
                        <button type="button" class="btn-pro" @click="saveChanges">Save Changes</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
<script>
export default {
    props: {
        visible: {
            type: Boolean,
            required: true,
        },
        layer: {
            type: Object,
            required: true,
        },
    },

    methods: {
        closeModal() {
            this.$emit("close-modal");
        },
        saveChanges() {
            this.$emit("save-changes", this.layer);
            this.closeModal();
        },
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
