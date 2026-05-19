<template>
    <div class="logo-bar">
        <img id="trace-logo" src="/logos/trace_logo.png" alt="Logo" class="img-fluid left-logo" />
        <div class="logo-center">
            <img src="/logos/trace_logo2.png" alt="Trace Structures Logo" class="img-fluid logo" />
            <h1 class="logo-title">
                <span class="orange">TRACE Structures</span><span class="blue"> – API for </span>
                <span class="orange">T</span><span class="blue">winning, </span> <span class="orange">R</span
                ><span class="blue">esilience, and </span> <span class="orange">A</span
                ><span class="blue">I-driven </span> <span class="orange">C</span
                ><span class="blue">omputational </span> <span class="orange">E</span
                ><span class="blue">ngineering for Building </span>
                <span class="orange">Structures</span>
            </h1>
        </div>
    </div>
</template>

<style scoped>
.logo-bar {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: var(--header-height);
    background-color: var(--bg-main);
    border-bottom: 1px solid var(--border-color);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
    z-index: 1000;
    display: flex;
    align-items: center;
    padding: 0 var(--spacing-lg);
}

#trace-logo {
    cursor: pointer;
    max-height: 7vh;
    transition: transform 0.2s ease;
}

#trace-logo:hover {
    transform: scale(1.05);
}

.logo-center {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.logo {
    max-height: 6vh;
    margin-bottom: var(--spacing-xs);
}

.logo-title {
    font-size: 1rem;
    margin: 0;
    color: var(--text-main);
    font-weight: 500;
    letter-spacing: 0.02em;
    opacity: 0.9;
}

.orange {
    color: var(--primary);
    font-weight: 600;
}

.blue {
    color: var(--text-main);
    opacity: 0.8;
}

@media (max-width: 1200px) {
    .logo-title {
        display: none;
    }
}
</style>
