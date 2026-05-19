<template>
    <button class="btn-pro m-3" @click="showInputLoader = true">Fetch Weather Data</button>
    <div
        v-if="showInputLoader"
        class="modal-backdrop"
        @click.self="closeModal"
    >
        <div class="modal-dialog card-pro" @click.stop>
            <div class="modal-header mb-4">
                <h2 class="modal-title">Load Weather Data</h2>
                <button type="button" class="btn-close-custom" @click="closeModal">&times;</button>
            </div>
            <div class="modal-body">
                <!-- Weather Variables -->
                <div class="mb-4">
                    <h4 class="h6 text-muted text-uppercase fw-bold mb-3">Hourly Weather Variables</h4>
                    <div class="row g-3">
                        <div class="col-6 col-md-3" v-for="(group, gIdx) in variableGroups" :key="gIdx">
                            <div v-for="(variable, idx) in group" :key="idx" class="form-check mb-1">
                                <input class="form-check-input" type="checkbox" v-model="selectedVariables" :value="variable.value" :id="'var-' + gIdx + '-' + idx" />
                                <label class="form-check-label small ms-1" :for="'var-' + gIdx + '-' + idx">
                                    {{ variable.label }}
                                </label>
                            </div>
                        </div>
                    </div>
                </div>
                <!-- Location and Date -->
                <div class="border-top pt-4">
                    <h4 class="h6 text-muted text-uppercase fw-bold mb-3">Location & Timeframe</h4>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label small fw-bold">Latitude</label>
                            <input type="number" v-model="latitude" step="0.01" />
                        </div>
                        <div class="col-md-6">
                            <label class="form-label small fw-bold">Longitude</label>
                            <input type="number" v-model="longitude" step="0.01" />
                        </div>
                        <div class="col-md-6">
                            <label class="form-label small fw-bold">Start Date</label>
                            <input type="date" v-model="startDate" />
                        </div>
                        <div class="col-md-6">
                            <label class="form-label small fw-bold">End Date</label>
                            <input type="date" v-model="endDate" />
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer d-flex justify-content-end gap-2 pt-3 mt-4 border-top">
                <button type="button" class="btn-pro btn-outline-pro" @click="closeModal">Cancel</button>
                <button type="button" class="btn-pro" @click="load">Fetch Data</button>
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
    },
    emits: ["load-file", "close"],
    data() {
        return {
            showInputLoader: false,
            selectedVariables: [],
            latitude: 52.52,
            longitude: 13.41,
            startDate: "2025-07-23",
            endDate: "2025-08-06",
            // Grouped variables for easier rendering
            variableGroups: [
                [
                    { label: "Temperature (2 m)", value: "temperature_2m" },
                    { label: "Relative Humidity (2 m)", value: "relative_humidity_2m" },
                    { label: "Dewpoint (2 m)", value: "dewpoint_2m" },
                    { label: "Apparent Temperature", value: "apparent_temperature" },
                    { label: "Precipitation (rain + snow)", value: "precipitation" },
                    { label: "Rain", value: "rain" },
                    { label: "Snowfall", value: "snowfall" },
                    { label: "Snow depth", value: "snow_depth" },
                ],
                [
                    { label: "Weather code", value: "weather_code" },
                    { label: "Sea-level Pressure", value: "pressure_msl" },
                    { label: "Surface Pressure", value: "surface_pressure" },
                    { label: "Cloud cover Total", value: "cloud_cover" },
                    { label: "Cloud cover Low", value: "cloud_cover_low" },
                    { label: "Cloud cover Mid", value: "cloud_cover_mid" },
                    { label: "Cloud cover High", value: "cloud_cover_high" },
                    { label: "Reference Evapotranspiration (ET₀)", value: "et0_fao_evapotranspiration" },
                    { label: "Vapour Pressure Deficit", value: "vapour_pressure_deficit" },
                ],
                [
                    { label: "Wind Speed (10 m)", value: "wind_speed_10m" },
                    { label: "Wind Speed (100 m)", value: "wind_speed_100m" },
                    { label: "Wind Direction (10 m)", value: "wind_direction_10m" },
                    { label: "Wind Direction (100 m)", value: "wind_direction_100m" },
                    { label: "Wind Gusts (10 m)", value: "wind_gusts_10m" },
                ],
                [
                    { label: "Soil Temperature (0-7 cm)", value: "soil_temperature_0_to_7cm" },
                    { label: "Soil Temperature (7-28 cm)", value: "soil_temperature_7_to_28cm" },
                    { label: "Soil Temperature (28-100 cm)", value: "soil_temperature_28_to_100cm" },
                    { label: "Soil Temperature (100-255 cm)", value: "soil_temperature_100_to_255cm" },
                    { label: "Soil Moisture (0-7 cm)", value: "soil_moisture_0_to_7cm" },
                    { label: "Soil Moisture (7-28 cm)", value: "soil_moisture_7_to_28cm" },
                    { label: "Soil Moisture (28-100 cm)", value: "soil_moisture_28_to_100cm" },
                    { label: "Soil Moisture (100-255 cm)", value: "soil_moisture_100_to_255cm" },
                ],
            ],
        };
    },
    methods: {
        closeModal() {
            this.showInputLoader = false;
        },
        load() {
            if (this.selectedVariables.length === 0) {
                alert("Please select at least one weather variable.");
                return;
            }
            if (!this.latitude || !this.longitude) {
                alert("Please enter valid latitude and longitude.");
                return;
            }
            if (!this.startDate || !this.endDate) {
                alert("Please enter valid start and end dates.");
                return;
            }
            if (this.startDate > this.endDate) {
                alert("Start date must be before end date.");
                return;
            }

            const params = {
                latitude: this.latitude,
                longitude: this.longitude,
                start_date: this.startDate,
                end_date: this.endDate,
                features: this.selectedVariables,
            };
            this.socket.emit("fetch_weather_data", params);
            this.$emit("close");
            this.closeModal();
        },
    },
};
</script>
<style scoped>
.modal-backdrop {
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

.modal-dialog {
    width: 100%;
    max-width: 900px;
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

.form-label {
    margin-bottom: 0.25rem;
}
</style>
