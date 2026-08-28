<template>
    <nav id="sidebar" class="col-md-3 col-lg-2 d-md-block sidebar">
        <div class="position-sticky">
            <ul class="nav flex-column">
                <li class="nav-item" v-for="(modeObj, modeKey) in menuStructure" :key="modeKey">
                    <button
                        class="nav-link main-item"
                        :class="{ active: mode === modeKey }"
                        @click.prevent="$emit('change-mode', modeKey)"
                    >
                        {{ modeObj.name }}
                    </button>
                    <ul v-if="mode === modeKey" class="nav flex-column sub-menu">
                        <li v-for="item in modeObj.items" :key="item.page">
                            <button
                                class="nav-link sub-item"
                                :class="{ done: isPageDone(item.page), active: activePage === item.page }"
                                :disabled="!isPageAvailable(item.page)"
                                @click.prevent="$emit('change-page', item.page)"
                            >
                                {{ item.label }}
                            </button>
                        </li>
                    </ul>
                </li>
            </ul>
        </div>
    </nav>
</template>

<script>
const MENU_STRUCTURE = {
    home: {
        items: [],
        name: "Home",
    },
    subtracting: {
        items: [
            { page: "upload", label: "Upload Already Trained Data-Driven Predictive Model", requires: [] },
            { page: "variables", label: "Upload Features And Labels", requires: [] },
            { page: "exploratory", label: "Exploratory Data Analysis", requires: ["variables"] },
            { page: "surrogate", label: "Data-Driven Modeling", requires: ["variables"] },
            { page: "uq", label: "UQ and Sensitivities", requires: ["surrogate"] },
            { page: "subtract", label: "Remove External Effects", requires: ["surrogate"] },
            { page: "thresholdExceedance", label: "Detect Threshold Exceedance", requires: ["surrogate"] },
        ],
        name: "Weather Effect Modeling",
    },
    surrogate: {
        items: [
            { page: "upload", label: "Upload Already Trained Surrogate Predictive Model", requires: [] },
            { page: "variables", label: "Variable Definition", requires: [] },
            { page: "sample", label: "Sample And Upload QoI", requires: ["variables"] },
            { page: "exploratory", label: "Exploratory Data Analysis", requires: ["variables"] },
            { page: "surrogate", label: "Surrogate Modeling", requires: ["sample"] },
            { page: "uq", label: "UQ And Sensitivities", requires: ["surrogate"] },
            { page: "measurements", label: "Definition Of Measurements", requires: ["surrogate"] },
            { page: "compare", label: "Link QoI And Measurement", requires: ["measurements"] },
            { page: "update", label: "Update / Digital Twining", requires: ["compare"] },
        ],
        name: "Model Calibration — MCMC (Surrogate-Based)",
    },
    inverse: {
        items: [
            { page: "upload", label: "Upload Already Trained Data-Driven Predictive Model", requires: [] },
            { page: "variables", label: "Upload Features And Labels", requires: [] },
            { page: "exploratory", label: "Exploratory Data Analysis", requires: ["variables"] },
            { page: "surrogate", label: "Data-Driven Modeling", requires: ["variables"] },
            { page: "uq", label: "UQ and Sensitivities", requires: ["surrogate"] },
            { page: "subtract", label: "Remove External Effects", requires: ["surrogate"] },
            { page: "thresholdExceedance", label: "Detect Threshold Exceedance", requires: ["surrogate"] },
        ],
        name: "Model Calibration — Direct Inversion (Regression-Based)",
    },
    multiModel: {
        items: [
            { page: "upload", label: "Upload Predictive Models and Link Parameters", requires: [] },
            { page: "measurements", label: "Definition Of Measurements", requires: ["upload"] },
            { page: "update", label: "Joint Update", requires: ["measurements"] },
        ],
        name: "Multi-infrastructure Updating",
    },
    mosaic: {
        items: [
            { page: "upload", label: "Upload Already Trained MOSAIC Model", requires: [] },
            { page: "variables", label: "Variable Definition", requires: [] },
            { page: "sample", label: "Sample And Upload QoI", requires: ["variables"] },
            { page: "exploratory", label: "Exploratory Data Analysis", requires: ["variables"] },
            { page: "surrogate", label: "Data-Driven Modeling", requires: ["variables"] },
            { page: "measurements", label: "Definition Of Measurements", requires: ["surrogate"] },
            { page: "compare", label: "Link QoI And Measurement", requires: ["measurements"] },
            { page: "update", label: "Update / Digital Twining", requires: ["compare"] },
        ],
        name: "MOSAIC Modeling",
    },
};

export default {
    props: {
        mode: {
            type: String,
            required: true,
        },
        activePage: {
            type: String,
            required: true,
        },
        completedPages: {
            type: Array,
            required: true,
        },
    },
    computed: {
        menuStructure() {
            return MENU_STRUCTURE;
        },
    },
    methods: {
        isPageDone(page) {
            return this.completedPages.includes(page);
        },
        isPageAvailable(page) {
            if (this.isPageDone(page)) return true;
            const item = (MENU_STRUCTURE[this.mode]?.items ?? []).find((i) => i.page === page);
            if (!item) return false;
            return item.requires.every((requiredPage) => this.completedPages.includes(requiredPage));
        },
    },
};
</script>

<style scoped>
.sidebar {
  background: var(--bg-sidebar);
  position: fixed;
  top: var(--header-height);
  left: 0;
  width: var(--sidebar-width);
  height: calc(100vh - var(--header-height));
  border-right: 1px solid var(--border-color);
  padding: var(--spacing-md) 0;
  overflow-y: auto;
  z-index: 100;
  box-shadow: 4px 0 10px rgba(0, 0, 0, 0.03);
}

.nav-item {
  margin-bottom: 2px;
  padding: 0 var(--spacing-sm);
}

.nav-link {
  display: flex;
  align-items: center;
  text-align: left;
  padding: 0.5rem var(--spacing-md);
  color: var(--text-main);
  border: none;
  background: transparent;
  width: 100%;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 0.95rem;
  border-radius: var(--radius);
  line-height: 1.3;
}

.nav-link:hover:not(:disabled) {
  background-color: var(--secondary);
  color: var(--primary);
}

.nav-link.active {
  background-color: var(--primary);
  color: #ffffff !important;
  font-weight: 600;
}

.nav-link.active:hover {
  background-color: var(--primary-hover);
  color: #ffffff !important;
}

.main-item {
  color: var(--primary);
  font-weight: 700;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  margin-top: var(--spacing-sm);
  margin-bottom: 2px;
  opacity: 0.8;
}

.main-item.active {
  opacity: 1;
}

.sub-menu {
  margin-left: var(--spacing-sm);
  margin-top: 2px;
  margin-bottom: var(--spacing-sm);
  padding-left: 0;
  list-style: none;
  border-left: 1px solid var(--border-color);
}

.sub-item {
  padding-left: var(--spacing-md);
  font-size: 0.875rem;
  color: var(--text-muted);
  min-height: 2.2rem;
}

.sub-item.active {
  color: #ffffff;
}

.nav-link.done::after {
  content: " \2714";
  font-size: 0.8rem;
  color: var(--success);
  margin-left: auto;
}

.nav-link.active.done::after {
  color: #ffffff;
}

.nav-link:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
