<template>
    <button class="btn-pro m-3" @click="showInputLoader = true">Fetch Weather Data</button>
    <Teleport to="body">
        <div
            v-if="showInputLoader"
            class="modal-backdrop"
            @click.self="closeModal"
        >
            <div
                class="modal-dialog card-pro"
                role="dialog"
                aria-modal="true"
                aria-labelledby="weather-modal-title"
                tabindex="-1"
                ref="dialog"
                @click.stop
                @keydown.esc="closeModal"
            >
                <div class="modal-header mb-4">
                    <h2 id="weather-modal-title" class="modal-title">Load Weather Data</h2>
                    <button type="button" class="btn-close-custom" aria-label="Close" @click="closeModal">&times;</button>
                </div>
                <div class="modal-body">
                    <!-- Weather Variables -->
                    <div class="mb-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h3 class="h6 text-muted text-uppercase fw-bold mb-0">Hourly Weather Variables</h3>
                            <div class="d-flex align-items-center gap-3">
                                <span class="selected-count">{{ selectedVariables.length }} selected</span>
                                <button type="button" class="btn-link-pro" @click="selectAllVariables">Select all</button>
                                <button type="button" class="btn-link-pro" @click="clearAllVariables">Clear</button>
                            </div>
                        </div>
                        <p v-if="errors.variables" class="field-error">{{ errors.variables }}</p>
                        <div class="row g-3">
                            <div class="col-12 col-sm-6 col-lg-3 variable-col" v-for="(group, gIdx) in variableGroups" :key="gIdx">
                                <fieldset class="variable-group">
                                    <legend class="variable-group-title">{{ group.title }}</legend>
                                    <div v-for="(variable, idx) in group.variables" :key="idx" class="form-check mb-1">
                                        <input class="form-check-input" type="checkbox" v-model="selectedVariables" :value="variable.value" :id="'var-' + gIdx + '-' + idx" />
                                        <label class="form-check-label small" :for="'var-' + gIdx + '-' + idx">
                                            {{ variable.label }}
                                        </label>
                                    </div>
                                </fieldset>
                            </div>
                        </div>
                    </div>
                    <!-- Location and Date -->
                    <div class="border-top pt-4">
                        <h3 class="h6 text-muted text-uppercase fw-bold mb-3">Location & Timeframe</h3>
                        <p v-if="errors.location" class="field-error">{{ errors.location }}</p>
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label class="form-label small fw-bold">Latitude</label>
                                <input type="number" v-model.number="latitude" step="0.01" min="-90" max="90" />
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold">Longitude</label>
                                <input type="number" v-model.number="longitude" step="0.01" min="-180" max="180" />
                            </div>
                        </div>
                        <p v-if="errors.dates" class="field-error mt-3">{{ errors.dates }}</p>
                        <div class="row g-3" :class="{ 'mt-0': !errors.dates }">
                            <div class="col-md-6">
                                <label class="form-label small fw-bold">Start Date</label>
                                <input type="date" v-model="startDate" :max="maxDate" />
                            </div>
                            <div class="col-md-6">
                                <label class="form-label small fw-bold">End Date</label>
                                <input type="date" v-model="endDate" :max="maxDate" />
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer d-flex justify-content-end gap-2 pt-3 mt-4 border-top">
                    <button type="button" class="btn-pro btn-outline-pro" @click="closeModal">Cancel</button>
                    <button type="button" class="btn-pro" @click="load" :disabled="loadingState.active">
                        <span v-if="loadingState.active" class="btn-spinner"></span>
                        {{ loadingState.active ? "Fetching…" : "Fetch Data" }}
                    </button>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script>
import { loadingState } from "../loadingState";

function formatDate(date) {
    return date.toISOString().slice(0, 10);
}

// Open-Meteo's archive typically lags a day behind, so default to the most
// recent complete day rather than "today".
const maxDate = new Date();

export default {
    setup() {
        return { loadingState };
    },
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
            startDate: "2025-02-04",
            endDate: "2026-02-04",
            maxDate: formatDate(maxDate),
            errors: {
                variables: "",
                location: "",
                dates: "",
            },
            // Grouped variables for easier rendering
            variableGroups: [
                {
                    title: "Temperature & Precipitation",
                    variables: [
                        { label: "Temperature (2 m)", value: "temperature_2m" },
                        { label: "Relative Humidity (2 m)", value: "relative_humidity_2m" },
                        { label: "Dewpoint (2 m)", value: "dewpoint_2m" },
                        { label: "Apparent Temperature", value: "apparent_temperature" },
                        { label: "Precipitation (rain + snow)", value: "precipitation" },
                        { label: "Rain", value: "rain" },
                        { label: "Snowfall", value: "snowfall" },
                        { label: "Snow depth", value: "snow_depth" },
                    ],
                },
                {
                    title: "Atmosphere",
                    variables: [
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
                },
                {
                    title: "Wind",
                    variables: [
                        { label: "Wind Speed (10 m)", value: "wind_speed_10m" },
                        { label: "Wind Speed (100 m)", value: "wind_speed_100m" },
                        { label: "Wind Direction (10 m)", value: "wind_direction_10m" },
                        { label: "Wind Direction (100 m)", value: "wind_direction_100m" },
                        { label: "Wind Gusts (10 m)", value: "wind_gusts_10m" },
                    ],
                },
                {
                    title: "Soil",
                    variables: [
                        { label: "Soil Temperature (0-7 cm)", value: "soil_temperature_0_to_7cm" },
                        { label: "Soil Temperature (7-28 cm)", value: "soil_temperature_7_to_28cm" },
                        { label: "Soil Temperature (28-100 cm)", value: "soil_temperature_28_to_100cm" },
                        { label: "Soil Temperature (100-255 cm)", value: "soil_temperature_100_to_255cm" },
                        { label: "Soil Moisture (0-7 cm)", value: "soil_moisture_0_to_7cm" },
                        { label: "Soil Moisture (7-28 cm)", value: "soil_moisture_7_to_28cm" },
                        { label: "Soil Moisture (28-100 cm)", value: "soil_moisture_28_to_100cm" },
                        { label: "Soil Moisture (100-255 cm)", value: "soil_moisture_100_to_255cm" },
                    ],
                },
            ],
        };
    },
    watch: {
        showInputLoader(isOpen) {
            if (isOpen) {
                this.$nextTick(() => this.$refs.dialog?.focus());
            }
        },
    },
    methods: {
        closeModal() {
            this.showInputLoader = false;
        },
        selectAllVariables() {
            this.selectedVariables = this.variableGroups.flatMap((group) => group.variables.map((variable) => variable.value));
        },
        clearAllVariables() {
            this.selectedVariables = [];
        },
        load() {
            this.errors = { variables: "", location: "", dates: "" };

            if (this.selectedVariables.length === 0) {
                this.errors.variables = "Select at least one weather variable.";
            }

            if (!Number.isFinite(this.latitude) || this.latitude < -90 || this.latitude > 90) {
                this.errors.location = "Latitude must be a number between -90 and 90.";
            } else if (!Number.isFinite(this.longitude) || this.longitude < -180 || this.longitude > 180) {
                this.errors.location = "Longitude must be a number between -180 and 180.";
            }

            if (!this.startDate || !this.endDate) {
                this.errors.dates = "Enter both a start and end date.";
            } else if (this.startDate > this.endDate) {
                this.errors.dates = "Start date must be before end date.";
            }

            if (this.errors.variables || this.errors.location || this.errors.dates) {
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
    max-height: 90vh;
    overflow-y: auto;
    overflow-x: hidden;
    margin: 0 var(--spacing-md);
    background: white;
    position: relative;
    z-index: var(--z-modal-dialog);
    pointer-events: auto;
}

.modal-dialog:focus {
    outline: none;
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

.field-error {
    color: var(--danger);
    font-size: 0.85rem;
    margin: 0.25rem 0 0;
}

.btn-link-pro {
    background: none;
    border: none;
    padding: 0;
    color: var(--primary);
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: underline;
}

.btn-link-pro:hover {
    color: var(--primary-hover);
}

.variable-col {
    min-width: 0;
}

.variable-group {
    border: 0;
    padding: 0;
    margin: 0;
    min-width: 0;
}

.variable-group-title {
    display: block;
    width: 100%;
    padding: 0;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
}

.selected-count {
    font-size: 0.8rem;
    color: var(--text-muted);
    white-space: nowrap;
}

.variable-group .form-check {
    display: flex;
    align-items: flex-start;
    gap: 0.4rem;
    padding-left: 0;
}

.variable-group .form-check-input {
    float: none;
    flex-shrink: 0;
    margin: 0.2em 0 0;
}

.form-check-label {
    overflow-wrap: anywhere;
    word-break: break-word;
}

.btn-spinner {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid rgba(127, 127, 127, 0.35);
    border-top-color: currentColor;
    animation: btn-spin 0.7s linear infinite;
    display: inline-block;
}

@keyframes btn-spin {
    to { transform: rotate(360deg); }
}
</style>
