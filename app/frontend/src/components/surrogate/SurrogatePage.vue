<template>
    <div class="surrogate-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/logos/hs_logo.png', alt: 'HS Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'variables'" :changePage="changePage" />

        <!-- Data Configuration Section -->
        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-gear-wide-connected fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Training & Testing Configuration</h2>
            </div>

            <div class="row g-4 mb-4">
                <div class="col-md-6">
                    <div class="stats-box d-flex gap-4">
                        <div class="stat-item">
                            <label class="text-muted small text-uppercase fw-bold d-block">Inputs (Features)</label>
                            <span class="h4 mb-0">{{ variablePage.data.variables.length }}</span>
                        </div>
                        <div class="stat-item border-start ps-4">
                            <label class="text-muted small text-uppercase fw-bold d-block">Outputs (QoI)</label>
                            <span class="h4 mb-0">{{ Object.keys(variablePage.qoiTable).length || 0 }}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row g-3">
                <div class="col-md-4">
                    <label class="form-label fw-bold d-flex align-items-center gap-1">
                        Train-Test Ratio
                        <Tooltip :content="'<p><b>Train-Test Ratio:</b> The proportion of the dataset used for training versus testing. 0.8 means 80% of the dataset is used for training and 20% for testing.</p>'" />
                    </label>
                    <input type="number" class="form-control" v-model="surrogatePage.splitConfig.trainTestRatio" step="0.1" min="0.1" max="0.9" />
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold d-flex align-items-center gap-1">
                        Split Method
                        <Tooltip :content="'<p><b>Shuffle:</b> Randomly shuffled before splitting.<br><b>Don\'t Shuffle:</b> Split in original order.<br><b>Reverse:</b> Split in reverse order.</p>'" />
                    </label>
                    <select class="form-select" v-model="surrogatePage.splitConfig.trainTestSplit">
                        <option value="shuffle">Shuffle</option>
                        <option value="noshuffle">Don't shuffle</option>
                        <option value="reverse">Reverse</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label fw-bold">Random Seed</label>
                    <input type="number" class="form-control" v-model="surrogatePage.splitConfig.seed" placeholder="None" />
                </div>
            </div>
        </div>

        <!-- Model Selection & Hyperparameters Section -->
        <div class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-cpu fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Model & Hyperparameters</h2>
            </div>

            <div class="row mb-4" v-if="mode === 'subtracting'">
                <div class="col-md-6">
                    <label class="form-label fw-bold d-flex align-items-center gap-1">
                        Model Type
                        <Tooltip :content="'<p><b>Deterministic:</b> Produces a single point prediction for each output.<br><b>Probabilistic:</b> Produces a predictive distribution to quantify uncertainty.</p>'" />
                    </label>
                    <select class="form-select" v-model="surrogatePage.modelConfig.predictionType">
                        <option value="deterministic">Deterministic</option>
                        <option value="probabilistic">Probabilistic</option>
                    </select>
                </div>
            </div>

            <div class="row mb-4">
                <div class="col-md-6" v-if="mode === 'subtracting' && surrogatePage.modelConfig.predictionType === 'probabilistic'">
                    <label class="form-label fw-bold d-flex align-items-center gap-1">
                        Surrogate Model Architecture
                        <Tooltip :content="'<p><b>MDN:</b> Mixture Density Network, predicts a full probability distribution as a mixture of Gaussians.<br><b>CRPS:</b> Trained directly against the Continuous Ranked Probability Score for probabilistic forecasts.</p>'" />
                    </label>
                    <select class="form-select" v-model="surrogatePage.modelConfig.modelType">
                        <option value="" selected disabled hidden>Select an architecture</option>
                        <option value="MDN">Mixture Density Network (MDN)</option>
                        <option value="CRPS">CRPS</option>
                    </select>
                </div>
                <div class="col-md-6" v-if="(mode === 'subtracting' && surrogatePage.modelConfig.predictionType === 'deterministic') || mode === 'surrogate'">
                    <label class="form-label fw-bold d-flex align-items-center gap-1">
                        Surrogate Model Architecture
                        <Tooltip :content="'<p><b>GPCE:</b> Polynomial expansions for uncertainty quantification.<br><b>GBT:</b> Advanced tree boosting.<br><b>DNN:</b> Deep Neural Networks for complex non-linear mappings.</p>'" />
                    </label>
                    <select class="form-select" v-model="surrogatePage.modelConfig.modelType">
                        <option value="" selected disabled hidden>Select an architecture</option>
                        <option value="gPCE">Generalized Polynomial Chaos Expansion (gPCE)</option>
                        <option value="GBT">Gradient Boosted Decision Tree (GBT)</option>
                        <option value="DNN">Deep Neural Network (DNN)</option>
                        <option value="LinReg">Linear Regression</option>
                    </select>
                </div>
            </div>

            <!-- Conditional Hyperparameters -->
            <div class="hyper-config p-3 rounded bg-light border text-muted" v-if="surrogatePage.modelConfig.modelType === 'LinReg'">
                Linear Regression has no hyperparameters to configure.
            </div>
            <div class="hyper-config p-3 rounded bg-light border" v-else-if="surrogatePage.modelConfig.modelType">
                <div v-if="surrogatePage.modelConfig.modelType === 'gPCE'" class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label fw-bold d-flex align-items-center gap-1">
                            Polynomial Degree
                            <Tooltip :content="'<p>Highest power of the polynomial expansion.</p>'" />
                        </label>
                        <input type="number" class="form-control" v-model="surrogatePage.modelConfig.gpcConfig.initConfig.p" />
                    </div>
                </div>

                <div v-if="surrogatePage.modelConfig.modelType === 'GBT'" class="row g-3 align-items-end">
                    <div class="col-md-4">
                        <label class="form-label fw-bold d-flex align-items-center gap-1">
                            Max Depth
                            <Tooltip :content="'<p>Max levels a tree can grow. Controls complexity.</p>'" />
                        </label>
                        <input type="number" class="form-control" v-model="surrogatePage.modelConfig.gbtConfig.trainConfig.maxDepth" />
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold d-flex align-items-center gap-1">
                            Iterations
                            <Tooltip :content="'<p>Number of boosting iterations.</p>'" />
                        </label>
                        <input type="number" class="form-control" v-model="surrogatePage.modelConfig.gbtConfig.trainConfig.numOfIter" />
                    </div>
                    <div class="col-md-4">
                        <div class="p-2 border rounded bg-white text-center">
                            <label class="text-muted small text-uppercase d-block fw-bold">Computed Leaves</label>
                            <span class="fw-bold">{{ computeNumOfLeaves }}</span>
                        </div>
                    </div>
                </div>
                <div v-if="surrogatePage.modelConfig.modelType === 'MOSAIC'" class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label fw-bold d-flex align-items-center gap-1">
                            Resolution
                            <Tooltip :content="'<p>Resolution used when discretizing the mode/frequency space for classification.</p>'" />
                        </label>
                        <input type="number" class="form-control" step="0.1" v-model="surrogatePage.modelConfig.mosaicConfig.resolution" />
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold d-flex align-items-center gap-1">
                            Max. DOA of Frequencies
                            <Tooltip :content="'<p>Maximum degree of approximation used for frequencies.</p>'" />
                        </label>
                        <input type="number" class="form-control" step="1" v-model="surrogatePage.modelConfig.mosaicConfig.maxDoaFrequencies" />
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-bold d-flex align-items-center gap-1">
                            Max. DOA of Eigenvectors
                            <Tooltip :content="'<p>Maximum degree of approximation used for eigenvectors.</p>'" />
                        </label>
                        <input type="number" class="form-control" step="1" v-model="surrogatePage.modelConfig.mosaicConfig.maxDoaEigenvectors" />
                    </div>

                    <div class="col-md-4">
                        <label class="form-label fw-bold d-flex align-items-center gap-1">
                            Classification Method
                            <Tooltip :content="'<p>Algorithm used to classify samples during MOSAIC training.</p>'" />
                        </label>
                        <select class="form-select" v-model="surrogatePage.modelConfig.mosaicConfig.classificationMethod">
                            <option value="SVC">SVC</option>
                        </select>
                    </div>

                    <div class="col-12" v-if="surrogatePage.modelConfig.mosaicConfig.classificationMethod === 'SVC'">
                        <div class="d-flex justify-content-between align-items-center mb-3 mt-2">
                            <h5 class="mb-0 fs-6 fw-bold">Classifier Settings</h5>
                            <div class="btn-group btn-group-sm">
                                <button
                                    type="button"
                                    class="btn"
                                    :class="svcTab === 'basic' ? 'btn-pro' : 'btn-outline-secondary'"
                                    @click="svcTab = 'basic'"
                                >Basic</button>
                                <button
                                    type="button"
                                    class="btn"
                                    :class="svcTab === 'advanced' ? 'btn-pro' : 'btn-outline-secondary'"
                                    @click="svcTab = 'advanced'"
                                >Advanced</button>
                            </div>
                        </div>

                        <div v-if="svcTab === 'basic'" class="row g-3">
                            <div class="col-md-3">
                                <label class="form-label fw-bold">C</label>
                                <input type="number" class="form-control" step="0.1" v-model="surrogatePage.modelConfig.mosaicConfig.svcConfig.C" />
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Kernel</label>
                                <select class="form-select" v-model="surrogatePage.modelConfig.mosaicConfig.svcConfig.kernel">
                                    <option value="rbf">rbf</option>
                                    <option value="linear">linear</option>
                                    <option value="poly">poly</option>
                                    <option value="sigmoid">sigmoid</option>
                                    <option value="precomputed">precomputed</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Degree</label>
                                <input type="number" class="form-control" step="1" v-model="surrogatePage.modelConfig.mosaicConfig.svcConfig.degree" />
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold">Gamma</label>
                                <input type="text" class="form-control" v-model="surrogatePage.modelConfig.mosaicConfig.svcConfig.gamma" />
                            </div>
                        </div>
                        <div v-else class="hyper-config p-3 rounded bg-light border text-muted">
                            More SVC parameters coming soon.
                        </div>
                    </div>
                </div>

                <div v-if="['DNN', 'MDN', 'CRPS'].includes(surrogatePage.modelConfig.modelType)">
                    <div v-if="surrogatePage.modelConfig.modelType === 'MDN'" class="row g-3 mb-4">
                        <div class="col-md-4">
                            <label class="form-label fw-bold d-flex align-items-center gap-1">
                                Number of Components
                                <Tooltip :content="'<p>Number of Gaussian components in the mixture used to represent the predictive distribution.</p>'" />
                            </label>
                            <input type="number" class="form-control" v-model="surrogatePage.modelConfig.mdnConfig.initConfig.numComponents" />
                        </div>
                    </div>

                    <div v-if="surrogatePage.modelConfig.modelType === 'CRPS'" class="row g-3 mb-4">
                        <div class="col-md-4">
                            <label class="form-label fw-bold d-flex align-items-center gap-1">
                                Number of Independent Random Samplers
                                <Tooltip :content="'<p>Number of independent noise samples drawn per input when training against the CRPS/energy score.</p>'" />
                            </label>
                            <input type="number" class="form-control" v-model="surrogatePage.modelConfig.crpsConfig.trainConfig.numSamplers" />
                        </div>
                    </div>

                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <h5 class="mb-0 fs-6 fw-bold">Network Architecture</h5>
                        <button class="btn-pro btn-sm" @click="addLayer"><i class="bi bi-plus"></i> Add Layer</button>
                    </div>
                    
                    <div class="table-responsive mb-4">
                        <table class="table table-hover align-middle custom-table bg-white">
                            <thead>
                                <tr>
                                    <th>Neurons</th>
                                    <th>Activation</th>
                                    <th>Dropout</th>
                                    <th class="text-end">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr v-for="layer in surrogatePage.modelConfig.nnConfig.initConfig.layers" :key="layer.id" @click="openModal(layer)" class="cursor-pointer">
                                    <td>{{ layer.numOfNeurons || '64' }}</td>
                                    <td><span class="badge bg-secondary">{{ layer.activationFunction || 'relu' }}</span></td>
                                    <td>{{ layer.dropout || '0.0' }}</td>
                                    <td class="text-end">
                                        <button class="btn btn-sm btn-outline-danger" @click.stop="removeLayer(layer.id)">
                                            <i class="bi bi-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                                <tr v-if="surrogatePage.modelConfig.nnConfig.initConfig.layers.length === 0">
                                    <td colspan="4" class="text-center text-muted py-3">No layers defined.</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Output Activation</label>
                            <select class="form-select" v-model="surrogatePage.modelConfig.nnConfig.initConfig.outputAF">
                                <option value="relu">ReLU</option>
                                <option value="sigmoid">Sigmoid</option>
                                <option value="tanh">Tanh</option>
                                <option value="softmax">Softmax</option>
                                <option value="none">None</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label fw-bold">Loss Function</label>
                            <select class="form-select" v-model="surrogatePage.modelConfig.nnConfig.trainConfig.loss">
                                <option value="mse">Mean Squared Error</option>
                                <option value="mae">Mean Absolute Error</option>
                                <option value="crossentropy">Cross Entropy</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Optimizer</label>
                            <select class="form-select" v-model="surrogatePage.modelConfig.nnConfig.trainConfig.optimizer">
                                <option value="adam">Adam</option>
                                <option value="RMSprop">RMSprop</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Epochs</label>
                            <input type="number" class="form-control" v-model="surrogatePage.modelConfig.nnConfig.trainConfig.epochs" />
                        </div>
                        <div class="col-md-4">
                            <label class="form-label fw-bold">Batch Size</label>
                            <input type="number" class="form-control" v-model="surrogatePage.modelConfig.nnConfig.trainConfig.batch_size" />
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Selection Section -->
        <div class="card-pro content-card mb-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-list-check fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Feature & Label Selection</h2>
            </div>

            <div class="row g-4">
                <div class="col-md-6">
                    <div class="selection-box border rounded p-3 bg-white">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="fw-bold">Features (Input)</span>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-secondary py-0 px-2" @click="toggleAll('variables', true)">All</button>
                                <button class="btn btn-outline-secondary py-0 px-2" @click="toggleAll('variables', false)">None</button>
                            </div>
                        </div>
                        <div class="scroll-area">
                            <div v-for="variable in variablePage.data.variables" :key="variable.name" class="custom-check">
                                <input type="checkbox" :id="'p-' + variable.name" :value="variable.name" v-model="selectedFeats">
                                <label :for="'p-' + variable.name">{{ variable.name }}</label>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="col-md-6">
                    <div class="selection-box border rounded p-3 bg-white">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="fw-bold">Labels (Output)</span>
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-outline-secondary py-0 px-2" @click="toggleAll('labels', true)">All</button>
                                <button class="btn btn-outline-secondary py-0 px-2" @click="toggleAll('labels', false)">None</button>
                            </div>
                        </div>
                        <div class="scroll-area">
                            <div v-for="label in Object.keys(variablePage.qoiTable)" :key="label" class="custom-check">
                                <input type="checkbox" :id="'l-' + label" :value="label" v-model="selectedLabels">
                                <label :for="'l-' + label">{{ label }}</label>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="mt-4 pt-3 border-top d-flex justify-content-center">
                <button class="btn-pro px-5" @click="train" :disabled="isTraining">
                    <span v-if="isTraining" class="btn-spinner"></span>
                    <i v-else class="bi bi-lightning-fill"></i>
                    {{ isTraining ? "Training…" : "Train Model" }}
                </button>
            </div>
        </div>

        <!-- Evaluation Results -->
        <div v-if="surrogatePage.trainResult !== ''" class="card-pro content-card mb-4 border-primary">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-bar-chart-line fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Model Evaluation</h2>
            </div>

            <div class="alert alert-success d-flex align-items-center" role="alert">
                <i class="bi bi-check-circle-fill me-2"></i>
                <div>{{ surrogatePage.trainResult }}</div>
            </div>

            <div class="row g-4 mt-2">
                <div class="col-md-12 d-flex justify-content-end mb-3">
                    <OutputLoader 
                        :title="'Save Model'" 
                        @save-file="saveModel" 
                    />
                </div>

                <div class="col-md-6" v-if="Object.keys(surrogatePage.overallTrainMetrics).length > 0">
                    <h5 class="fw-bold mb-3 small text-uppercase text-muted">Overall Metrics</h5>
                    <table class="table table-sm custom-table bg-white border shadow-sm">
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th class="text-end">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(value, metric) in surrogatePage.overallTrainMetrics" :key="metric">
                                <td class="fw-bold">{{ metric }}</td>
                                <td class="text-end font-monospace">{{ value.toFixed(4) }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div class="col-md-6">
                    <h5 class="fw-bold mb-3 small text-uppercase text-muted">QoI Performance</h5>
                    <div class="mb-3">
                        <select class="form-select form-select-sm" v-model="surrogatePage.selectedQoIForMetric">
                            <option value="" selected disabled>Select QoI for detailed evaluation</option>
                            <option v-for="effect in surrogatePage.outputQoI" :key="effect" :value="effect">
                                {{ effect }}
                            </option>
                        </select>
                    </div>
                    
                    <table v-if="surrogatePage.selectedQoIForMetric" class="table table-sm custom-table bg-white border shadow-sm">
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th class="text-end">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(value, metric) in surrogatePage.individualTrainMetrics" :key="metric">
                                <td class="fw-bold">{{ metric }}</td>
                                <td class="text-end font-monospace">{{ value[surrogatePage.selectedQoIForMetric].toFixed(4) }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <NextButton :nextPage="'uq'" :available="surrogatePage.trainResult === 'Done'" :changePage="changePage" />
        
        <EditLayerModal
            v-if="showModal"
            :visible="showModal"
            :layer="selectedLayer"
            @close-modal="closeModal"
            @save-changes="saveChanges"
        />
    </div>
</template>

<script>
import BackButton from "../BackButton.vue";
import Tooltip from "../Tooltip.vue";
import { computeNumOfLeaves } from "../../utils/computeNumOfLeaves";
import EditLayerModal from "./EditLayerModal.vue";
import NextButton from "../NextButton.vue";
import LogoLine from "../LogoLine.vue";
import OutputLoader from "../OutputLoader.vue";

export default {
    components: {
        Tooltip,
        EditLayerModal,
        NextButton,
        BackButton,
        LogoLine,
        OutputLoader,
    },
    props: {
        mode: { type: String, required: true },
        surrogatePage: { type: Object, required: true },
        variablePage: { type: Object, required: true },
        socket: { type: Object, required: true },
        changePage: { type: Function, required: true },
        addPageDone: { type: Function, required: true },
    },
    data() {
        return {
            showModal: false,
            selectedLayer: null,
            selectedFeats: this.variablePage.data.variables.map(v => v.name),
            selectedLabels: this.variablePage.qoiTable ? Object.keys(this.variablePage.qoiTable) : [],
            isTraining: false,
            svcTab: "basic",
        };
    },
    created() {
        if (this.mode === "mosaic") {
            this.surrogatePage.modelConfig.modelType = "MOSAIC";
        }
    },
    watch: {
        surrogatePage: {
            handler() {
                if (this.surrogatePage.trainResult === "Done") {
                    this.addPageDone("surrogate");
                }
            },
            deep: true,
            immediate: true,
        },
        selectedFeats: {
            handler(newVal) {
                this.surrogatePage.selectedFeats = newVal;
            },
            deep: true,
            immediate: true,
        },
        selectedLabels: {
            handler(newVal) {
                this.surrogatePage.selectedLabels = newVal;
            },
            deep: true,
            immediate: true,
        },
        "surrogatePage.modelConfig.predictionType"() {
            this.surrogatePage.modelConfig.modelType = "";
        },
    },
    methods: {
        toggleAll(type, isSelectAll) {
            if (type === 'variables') {
                this.selectedFeats = isSelectAll ? this.variablePage.data.variables.map(v => v.name) : [];
            } else if (type === 'labels') {
                this.selectedLabels = isSelectAll ? Object.keys(this.variablePage.qoiTable) : [];
            }
        },
        generateId() {
            return "_" + Math.random().toString(36).slice(2, 9);
        },
        addLayer() {
            this.surrogatePage.modelConfig.nnConfig.initConfig.layers.push({ 
                id: this.generateId(),
                numOfNeurons: 64,
                activationFunction: 'relu',
                dropout: 0.0
            });
        },
        removeLayer(id) {
            this.surrogatePage.modelConfig.nnConfig.initConfig.layers =
                this.surrogatePage.modelConfig.nnConfig.initConfig.layers.filter((layer) => layer.id !== id);
        },
        openModal(layer) {
            this.selectedLayer = { ...layer };
            this.showModal = true;
        },
        closeModal() {
            this.showModal = false;
            this.selectedLayer = null;
        },
        saveChanges(updatedLayer) {
            const index = this.surrogatePage.modelConfig.nnConfig.initConfig.layers.findIndex(
                (layer) => layer.id === updatedLayer.id
            );
            if (index !== -1) {
                this.surrogatePage.modelConfig.nnConfig.initConfig.layers.splice(index, 1, updatedLayer);
            }
            this.closeModal();
        },
        train() {
            if (this.selectedFeats.length === 0 || this.selectedLabels.length === 0) {
                alert("Please select at least one feature and one label to train the model.");
                return;
            }
            if (this.surrogatePage.modelConfig.modelType === "") {
                alert("Please select a model type to train.");
                return;
            }
            const { splitConfig, modelConfig } = this.surrogatePage;
            this.isTraining = true;
            console.log("Training with config:", { splitConfig, modelConfig, selectedFeats: this.selectedFeats, selectedLabels: this.selectedLabels });
            this.socket.emit("train", {
                splitConfig,
                modelConfig,
                selectedFeats: this.selectedFeats,
                selectedLabels: this.selectedLabels
            });
        },
        saveModel() {
            this.socket.emit("save_model");
        },
    },
    mounted() {
        // The backend always emits train_result (either "Done" or an
        // "Error: ..." message) as the last step of training, whether it
        // succeeds or fails, so it's a reliable point to clear the spinner.
        this._trainResultHandler = () => {
            this.isTraining = false;
        };
        this.socket.on("train_result", this._trainResultHandler);
    },
    beforeUnmount() {
        this.socket.off("train_result", this._trainResultHandler);
    },
    computed: {
        computeNumOfLeaves() {
            return computeNumOfLeaves(this.surrogatePage, this.variablePage);
        },
    },
};
</script>

<style scoped>
.surrogate-page {
    max-width: 1000px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
}

.stats-box {
    background-color: var(--secondary);
    padding: var(--spacing-md);
    border-radius: var(--radius);
    border: 1px solid var(--border-color);
}

.stat-item label {
    margin-bottom: 0.25rem;
}

.hyper-config {
    margin-top: var(--spacing-md);
}

.scroll-area {
    max-height: 250px;
    overflow-y: auto;
    padding-right: 5px;
}

.scroll-area::-webkit-scrollbar {
    width: 5px;
}
.scroll-area::-webkit-scrollbar-thumb {
    background: var(--border-color);
    border-radius: 10px;
}

.custom-check {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 0.4rem 0.75rem;
    border-radius: 6px;
    transition: background 0.2s ease;
    cursor: pointer;
}

.custom-check:hover {
    background-color: var(--secondary);
}

.custom-check input {
    margin: 0;
    cursor: pointer;
    width: 1.1rem;
    height: 1.1rem;
    accent-color: var(--primary);
}

.custom-check label {
    margin: 0;
    cursor: pointer;
    font-size: 0.9rem;
    color: var(--text-main);
    flex-grow: 1;
}

.custom-table thead th {
    background-color: var(--secondary);
    font-size: 0.75rem;
    text-transform: uppercase;
    color: var(--text-muted);
}

.cursor-pointer {
    cursor: pointer;
}

.border-primary {
    border-top: 4px solid var(--primary) !important;
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
