<template>
    <div class="home-page">
        <div class="header-section mb-5">
            <h1 class="display-5 fw-bold">Select Analysis Mode</h1>
            <p class="lead text-muted">Choose a specialized module to begin your digital twinning and resilience assessment.</p>
        </div>

        <div class="modes-grid">
            <div class="mode-card" @click="selectMode('subtracting')">
                <div class="card-content">
                    <h3>Subtracting weather effects</h3>
                    <p>Construct purely data-driven models directly from input-output measurements. Isolate effects like temperature variations and assess output sensitivities.</p>
                    <button class="btn-pro mt-auto">Start Module</button>
                </div>
            </div>

            <div class="mode-card" @click="selectMode('surrogate')">
                <div class="card-content">
                    <h3>Surrogate-based updating</h3>
                    <p>Create calibrated digital twins by replacing physics-based simulations with surrogate models. Perform UQ, sensitivity analysis, and Bayesian inference.</p>
                    <button class="btn-pro mt-auto">Start Module</button>
                </div>
            </div>

            <div class="mode-card" @click="selectMode('inverse')">
                <div class="card-content">
                    <h3>AI-based inverse modeling</h3>
                    <p>Analyze building resilience by evaluate both local and global vulnerabilities through linear and non linear static analyses using AI-based inverse modeling.</p>
                    <button class="btn-pro mt-auto">Start Module</button>
                </div>
            </div>

            <div class="mode-card" @click="selectMode('multiModel')">
                <div class="card-content">
                    <h3>Multi-infrastructure Updating</h3>
                    <p>Enable parameter identification across multiple models with shared input parameters. Perform joint Bayesian updates for improved consistency and reliability.</p>
                    <button class="btn-pro mt-auto">Start Module</button>
                </div>
            </div>
        </div>
    </div>
</template>

<script>
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
        socket: {
            type: Object,
            required: true,
        },
    },
    methods: {
        selectMode(mode) {
            this.$emit("update-mode", mode);
        },
    },
};
</script>

<style scoped>
.home-page {
    max-width: 1200px;
    margin: 0 auto;
}

.modes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: var(--spacing-lg);
}

.mode-card {
    background: white;
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    padding: var(--spacing-lg);
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
}

.mode-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 20px rgba(0, 0, 0, 0.08);
    border-color: var(--primary);
}

.mode-card h3 {
    font-size: 1.25rem;
    margin-bottom: var(--spacing-md);
    color: var(--primary);
}

.mode-card p {
    color: var(--text-muted);
    font-size: 0.95rem;
    line-height: 1.5;
    margin-bottom: var(--spacing-lg);
}

.card-content {
    display: flex;
    flex-direction: column;
    height: 100%;
}

.header-section {
    border-bottom: 2px solid var(--secondary);
    padding-bottom: var(--spacing-md);
}
</style>
