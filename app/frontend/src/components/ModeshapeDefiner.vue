<template>
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
                    <h5 class="modal-title">Modeshape Definer</h5>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label for="fileInput"><b>Fill Modeshape Columns</b></label>
                        <div>
                            <div class="form-inline">
                                <label>Names:</label>
                                <input v-model="modeshape_cols" type="text" class="form-control" placeholder="a,b,c" />
                            </div>
                        </div>
                    </div>
                    <button class="btn-pro" @click="finalize">OK</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        
    },
    emits: ["finalize"],
    methods: {
        finalize() {
            this.$emit("finalize", this.modeshape_cols);
        },
    },
    data() {
        return {
            showInputLoader: true,
            modeshape_cols: ['phi_sensor_1_real', 'phi_sensor_1_imag', 'phi_sensor_2_real',
       'phi_sensor_2_imag', 'phi_sensor_3_real', 'phi_sensor_3_imag',
       'phi_sensor_4_real', 'phi_sensor_4_imag', 'phi_sensor_5_real',
       'phi_sensor_5_imag', 'phi_sensor_6_real', 'phi_sensor_6_imag'],
        };
    },
    mounted() {
        
    },
    beforeUnmount() {
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
