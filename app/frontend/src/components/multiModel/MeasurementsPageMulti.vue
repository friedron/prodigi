<template>
    <div>
        <LogoLine
            :logos="[
                { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                { src: '/logos/hs_logo.png', alt: 'HS Logo' },
            ]"
        />
        <BackButton :prevPage="'upload'" :changePage="changePage" />
        <h1>Definition of Measurement</h1>
        <label>Import mean measured value for model:</label>
        <div v-for="model in Object.keys(uploadPage.models || {})" :key="model" class="">
            <label class="me-auto">{{ model }}:</label>
            <InputLoader
                :dkgApiStatus="dkgApiStatus"
                :socket="socket"
                @load-file="loadMean($event, model)"
                :fileType="'.csv'"
                :loadType="'zmean'"
                :dkgToken="dkgToken"
            />
            <div
                v-if="
                    measurementsPage.multiModel &&
                    measurementsPage.multiModel[model] &&
                    measurementsPage.multiModel[model].zmean &&
                    Object.keys(measurementsPage.multiModel[model].zmean).length > 0
                "
                class="center"
            >
                <table class="table-custom table-bordered table-striped table-hover text-center custom-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th>Measured Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(value, key) in measurementsPage.multiModel[model].zmean" :key="key">
                            <td>{{ key }}</td>
                            <td>{{ value[0].toFixed(4) }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <h1>Standard Deviation of Measurement Error</h1>
        <label>Import standard deviation of measurement error for model:</label>
        <div v-for="model in Object.keys(uploadPage.models || {})" :key="model" class="">
            <label class="me-auto">{{ model }}:</label>
            <InputLoader
                :dkgApiStatus="dkgApiStatus"
                :socket="socket"
                @load-file="loadSigma($event, model)"
                :fileType="'.csv'"
                :loadType="'sigma'"
                :dkgToken="dkgToken"
            />
            <div
                v-if="
                    measurementsPage.multiModel &&
                    measurementsPage.multiModel[model] &&
                    measurementsPage.multiModel[model].sigma &&
                    Object.keys(measurementsPage.multiModel[model].sigma).length > 0
                "
                class="center"
            >
                <table class="table-custom table-bordered table-striped table-hover text-center custom-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th>STD of Measured Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(value, key) in measurementsPage.multiModel[model].sigma" :key="key">
                            <td>{{ key }}</td>
                            <td>{{ value[0].toFixed(4) }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        <div class="mb-3">
            <NextButton :nextPage="'update'" :available="measurementsPage.done" :changePage="changePage" />
        </div>
    </div>
</template>
<script>
import NextButton from "../NextButton.vue";
import LogoLine from "../LogoLine.vue";
import BackButton from "../BackButton.vue";
import InputLoader from "../InputLoader.vue";

export default {
    components: {
        NextButton,
        LogoLine,
        BackButton,
        InputLoader,
    },
    props: {
        measurementsPage: {
            type: Object,
            required: true,
        },
        uploadPage: {
            type: Object,
            required: true,
        },
        mode: {
            type: String,
            required: true,
        },
        socket: {
            type: Object,
            required: true,
        },
        changePage: {
            type: Function,
            required: true,
        },
        addPageDone: {
            type: Function,
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
    },
    data() {
        return {
            measurement_done: false,
        };
    },
    watch: {},
    methods: {
        loadMean(event, model) {
            const file = event;
            if (!file) {
                return;
            }
            const reader = new FileReader();
            reader.onload = (event) => {
                const csvContent = event.target.result;
                this.socket.emit("load_zmean_multi", {
                    name: file.name,
                    type: file.type,
                    model_name: model,
                    data: csvContent,
                });
            };
            reader.readAsText(file);
        },
        loadSigma(event, model) {
            const file = event;
            if (!file) {
                return;
            }
            const reader = new FileReader();
            reader.onload = (event) => {
                const csvContent = event.target.result;
                this.socket.emit("load_sigma_multi", {
                    name: file.name,
                    type: file.type,
                    model_name: model,
                    data: csvContent,
                });
            };
            reader.readAsText(file);
        },
        isPageDone(page) {
            return this.measurementsPage.done;
        },
    },
    mounted() {
        this.socket.on("measurement_done", () => {
            this.measurement_done = true;
        });
    },
};
</script>
<style scoped></style>
