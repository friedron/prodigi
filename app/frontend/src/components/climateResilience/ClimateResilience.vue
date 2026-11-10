<template>
    <div class="climate-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'info'" :changePage="changePage" />

        <div class="card-pro content-card mt-4 mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-geo-alt fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Location</h2>
                <Tooltip
                    class="ms-2"
                    content="Indicates the geographical coordinates of the city in latitude and longitude expressed
                            in decimal degree"
                />
            </div>

            <div class="row g-3 align-items-end">
                <div class="col-md-4">
                    <label class="form-label small fw-bold text-uppercase text-muted">Latitude</label>
                    <input type="number" class="form-control" v-model="climateResiliencePage.latitude" />
                </div>
                <div class="col-md-4">
                    <label class="form-label small fw-bold text-uppercase text-muted">Longitude</label>
                    <input type="number" class="form-control" v-model="climateResiliencePage.longitude" />
                </div>
                <div class="col-md-4">
                    <button class="btn-pro w-100" @click="validate">
                        <i class="bi bi-check2-circle"></i> Validate Location
                    </button>
                </div>
            </div>

            <div v-if="climateResiliencePage.city && climateResiliencePage.country" class="mt-3">
                <span class="badge rounded-pill bg-light text-dark border px-3 py-2">
                    <i class="bi bi-pin-map-fill text-primary me-1"></i>
                    {{ climateResiliencePage.city }}, {{ climateResiliencePage.country }}
                </span>
            </div>

            <div class="map-wrapper mt-3" v-if="plotly_map">
                <iframe :srcdoc="plotly_map" class="map-frame" scrolling="no"></iframe>
            </div>
        </div>

        <div v-if="climateResiliencePage.city && climateResiliencePage.country" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-sliders fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Climate Data Parameters</h2>
            </div>

            <div class="row g-4">
                <div class="col-md-6">
                    <label class="form-label small fw-bold text-uppercase text-muted">
                        Experiment
                        <Tooltip
                            content="For CORDEX projections, the available experiments should be Historical
                                and Scenarios (RCP 4.5 and RCP 8.5).<br />
                                <b>Historical</b>: covers past period in which in situ observations already exist.
                                This experiment shows how the RCMs perform for the past climate when forced by GCMs
                                and can be used as a reference period for comparison with scenario runs for the future.
                                The period covered is typically 1950-2005.<br />
                                <b>Scenarios</b>: Representative Concentration Pathways (RCPs) are a set of scenarios under
                                which future projections are run, encompassing trajectories of emissions, concentrations,
                                and land use changes. These scenarios are the RCP4.5 (midrange mitigation emission scenario)
                                and RCP8.5 (highest mitigation emission scenario) providing different pathways of the future
                                climate forcing. The period covered is typically 2006-2100."
                        />
                    </label>
                    <select v-model="climateResiliencePage.experiment" class="form-select">
                        <option value="null" disabled selected hidden>Select experiment</option>
                        <option value="4.5">Historical + RCP 4.5</option>
                        <option value="8.5">Historical + RCP 8.5</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label small fw-bold text-uppercase text-muted">
                        Climate Variable
                        <Tooltip
                            content="The variables are provided with daily temporal resolution<br />
                                <b>Maximum Temperature [C]</b> is the daily maximum air temperature near the surface,
                                usually at 2m above the surface<br />
                                <b>Minimum Temperature [C]</b> is the daily minimum air temperature near the surface,
                                usually at 2m above the surface<br />
                                <b>Precipitation [mm]</b> is total daily amount of rain, snow and hail measured as the
                                height of the equivalent liquid water in a square metre<br />
                                <b>Wind Speed [ms-1]</b> is the magnitude of the two-dimensional horizontal air velocity, it is
                                the mean over the aggregation period (day) at 10m above the surface"
                        />
                    </label>
                    <select v-model="climateResiliencePage.variable" class="form-select">
                        <option value="null" disabled selected hidden>Select a variable</option>
                        <option value="tasmax">Maximum Temperature [°C]</option>
                        <option value="tasmin">Minimum Temperature [°C]</option>
                        <option value="pr">Precipitation [mm]</option>
                        <option value="sfcWind">Wind Speed [ms⁻¹]</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="form-label small fw-bold text-uppercase text-muted">
                        Climate Indicator
                        <Tooltip content="The indicators are provided with daily temporal resolution" />
                    </label>
                    <select v-model="climateResiliencePage.output" class="form-select">
                        <option value="null" disabled selected hidden>Select an indicator</option>
                        <option value="FC">Factor of Change of Characteristic value</option>
                        <option value="Charact">Characteristic Value</option>
                        <option value="Mean">Mean Value</option>
                        <option value="Cov">Coefficient of Variation</option>
                    </select>
                </div>
            </div>

            <div class="mt-4">
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <label class="form-label small fw-bold text-uppercase text-muted mb-0">
                        Models
                        <Tooltip content="The models are provided with daily temporal resolution" />
                    </label>
                    <div class="btn-group btn-group-sm">
                        <button type="button" class="btn btn-outline-secondary py-0 px-2" @click="setAllModels(true)">All</button>
                        <button type="button" class="btn btn-outline-secondary py-0 px-2" @click="setAllModels(false)">None</button>
                    </div>
                </div>
                <div class="row g-2 p-3 bg-light rounded border">
                    <div v-for="(model, index) in models" :key="`model-${index}`" class="col-6 col-sm-4 col-lg-3">
                        <div class="form-check">
                            <input
                                class="form-check-input"
                                type="checkbox"
                                :id="`model-${model}`"
                                v-model="climateResiliencePage.models"
                                :value="model"
                            />
                            <label class="form-check-label" :for="`model-${model}`">{{ model }}</label>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div v-if="isPageDone()" class="card-pro content-card mb-4">
            <div class="d-flex align-items-center justify-content-between mb-4 pb-2 border-bottom flex-wrap gap-2">
                <div class="d-flex align-items-center">
                    <i class="bi bi-cloud-download fs-4 me-2 text-primary"></i>
                    <h2 class="h4 mb-0">Climate Data</h2>
                </div>
                <div class="d-flex gap-2">
                    <button class="btn-pro" @click="download">
                        <i class="bi bi-play-fill"></i> Show
                    </button>
                    <button class="btn-pro btn-outline-pro" @click="openPdfInfo">
                        <i class="bi bi-file-earmark-pdf"></i> Save Report
                    </button>
                </div>
            </div>

            <img v-if="img" :src="img" alt="Climate Data Visualization" class="img-fluid rounded border mb-3 zoomable" />

            <div class="plot-container mb-3" v-if="plotly_data">
                <div id="climate-chart"></div>
            </div>

            <div class="d-flex justify-content-end mb-2" v-if="tableData">
                <button class="btn-pro btn-outline-pro" @click="downloadTableCsv">
                    <i class="bi bi-filetype-csv"></i> Download CSV
                </button>
            </div>
            <div class="table-responsive mb-3" v-if="tableData">
                <table class="table table-sm table-hover align-middle custom-table border">
                    <thead>
                        <tr>
                            <th v-for="col in tableData.columns" :key="col">{{ col }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="(row, i) in tableData.rows" :key="i">
                            <td v-for="(cell, j) in row" :key="j">{{ cell }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <ReportInfo
            v-if="showReportInfo"
            :socket="socket"
            @close="showReportInfo = false"
            @save="pdfReport"
        />
    </div>
</template>
<script>
import Tooltip from "../Tooltip.vue";
import LogoLine from "../LogoLine.vue";
import BackButton from "../BackButton.vue";
import ReportInfo from "./ReportInfo.vue";
import { ref } from "vue";

export default {
    components: {
        Tooltip,
        BackButton,
        LogoLine,
        ReportInfo,
    },
    props: {
        climateResiliencePage: {
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
        socket: {
            type: Object,
            required: true,
        },
    },
    data() {
        let pageDone = ref(false);
        return {
            noCID: false,
            pageDone,
            plotly_map: null,
            plotly_data: null,
            models: ['frnet', 'gereu', 'irden', 'ireu', 'irnet', 'norden', 'norge', 'ukden', 'ukeu', 'uknet'],
            img : null,
            tableData: null,
            showReportInfo: false,
        };
    },
    methods: {
        setAllModels(selected) {
            this.climateResiliencePage.models = selected ? [...this.models] : [];
        },
        setLoading(value) {
            this.$emit("set-loading", value);
        },
        loadFile(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.socket.emit("climate_file", e.target.result);
                };
                reader.readAsArrayBuffer(file);
            }
        },
        isPageDone() {
            const isPageDone =
                this.climateResiliencePage?.longitude !== null &&
                this.climateResiliencePage?.latitude !== null &&
                this.climateResiliencePage?.variable !== null &&
                this.climateResiliencePage?.experiment !== null &&
                this.climateResiliencePage?.city !== null &&
                this.climateResiliencePage?.models?.length > 0 &&
                this.climateResiliencePage?.output !== null;

            return isPageDone;
        },
        validate() {
            this.setLoading(true);
            this.socket.emit("validate_location_climate", {
                longitude: this.climateResiliencePage.longitude,
                latitude: this.climateResiliencePage.latitude,
            });
        },
        download() {
            this.tableData = null;
            this.socket.emit("select_climate_data", {
                longitude: this.climateResiliencePage.longitude,
                latitude: this.climateResiliencePage.latitude,
                variable: this.climateResiliencePage.variable,
                experiment: this.climateResiliencePage.experiment,
                value: this.climateResiliencePage.output,
                models: this.climateResiliencePage.models,
            });
        },
        downloadTableCsv() {
            if (!this.tableData) return;
            const escape = (value) => {
                const s = value === null || value === undefined ? "" : String(value);
                return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
            };
            const lines = [
                this.tableData.columns.map(escape).join(","),
                ...this.tableData.rows.map((row) => row.map(escape).join(",")),
            ];
            // BOM so Excel reads UTF-8 (e.g. unit symbols) correctly
            const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
            const { variable, experiment, city } = this.climateResiliencePage;
            const name = ["climate", city, variable, experiment]
                .filter(Boolean)
                .join("_")
                .replace(/[^\w.-]+/g, "_");
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = `${name}.csv`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        },
        openPdfInfo() {
            this.showReportInfo = true;
        },
        pdfReport(formData) {
            try {
                this.$emit("set-loading", true);
                this.socket.emit("process_climate_data", {
                    lat: this.climateResiliencePage.latitude,
                    lon: this.climateResiliencePage.longitude,
                    experiment: this.climateResiliencePage.experiment,
                    variable: this.climateResiliencePage.variable,
                    value: this.climateResiliencePage.output,
                    models: this.climateResiliencePage.models,
                });
                // We will wait for process_climate_data to finish in mounted and emit get_climate_report_pdf there
                this._pendingPdfReport = formData;
            } catch (error) {
                console.error("Error requesting PDF report:", error);
            }
        },
    },
    mounted() {
        this.socket.on("downloaded_climate_data", () => {
            this.pageDone = true;
        });
        this.socket.on("plotly_map", (plotly) => {
            this.plotly_map = plotly;
            this.$emit("set-loading", false);
        });
        this.socket.on("location_data", (data) => {
            if (data.module !== "climate") return;
            this.climateResiliencePage.city = data.city;
            this.climateResiliencePage.country = data.country;
        });
        this.socket.on("climate_selection_result", (data) => {
            this.plotly_data = true;
            this.$nextTick(async () => {
                const gd = document.getElementById("climate-chart");
                if (!gd) return;
                const figure = JSON.parse(data);
                const Plotly = (await import("plotly.js-dist-min")).default;
                Plotly.react(gd, figure.data, figure.layout, { responsive: true, displaylogo: false });
            });
        });
        this.socket.on("climate_table_result", (data) => {
            this.tableData = data;
        });
        this.socket.on("climate_report_pdf", (data) => {
            this.$emit("set-loading", false);
            const bytes = Uint8Array.from(atob(data.file), c => c.charCodeAt(0));
            const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
            const link = document.createElement("a");
            link.href = url;
            link.download = data.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        });
        this.socket.on("processed_climate_data", () => {
            if (this._pendingPdfReport) {
                const formData = this._pendingPdfReport;
                this._pendingPdfReport = null;
                this.socket.emit("get_climate_report_pdf", {
                    building_name: formData.building_name,
                    address: formData.address,
                    author: formData.author,
                    owner: formData.owner,
                    location: formData.location,
                });
            } else {
                this.$emit("set-loading", false);
            }
        });
    },
    beforeUnmount() {
        this.socket.off("downloaded_climate_data");
        this.socket.off("plotly_map");
        this.socket.off("location_data");
        this.socket.off("climate_selection_result");
        this.socket.off("climate_table_result");
        this.socket.off("climate_report_pdf");
        this.socket.off("processed_climate_data");
    },
};
</script>
<style scoped>
.climate-page {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
}

.map-wrapper {
    display: flex;
    justify-content: center;
}

.map-frame {
    /* Matches the folium.Figure(width=500, height=500) rendered server-side -
       stretching the iframe wider than that leaves blank space inside the border. */
    width: 500px;
    height: 500px;
    max-width: 100%;
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    overflow: hidden;
}

.plot-container {
    background: white;
    padding: var(--spacing-md);
    border-radius: var(--radius);
    border: 1px solid var(--border-color);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    overflow: hidden;
}

#climate-chart {
    width: 100% !important;
    min-height: 500px;
    height: auto;
}

.custom-table thead th {
    background-color: var(--secondary);
    font-size: 0.75rem;
    text-transform: uppercase;
    color: var(--text-muted);
}
</style>
