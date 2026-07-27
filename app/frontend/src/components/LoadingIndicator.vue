<template>
    <Teleport to="body">
        <div class="loading-pill" :class="{ 'is-active': loadingState.active }" aria-hidden="true">
            <span class="loading-spinner"></span>
            <span class="loading-label">Working&hellip;</span>
        </div>
        <span class="visually-hidden" role="status" aria-live="polite">
            {{ loadingState.active ? "Working" : "" }}
        </span>
    </Teleport>
</template>

<script setup>
import { loadingState } from "../loadingState";
</script>

<style scoped>
.loading-pill {
    position: fixed;
    right: var(--spacing-lg);
    bottom: var(--spacing-lg);
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.55rem 1rem;
    background: #1f2733;
    color: #fff;
    border-radius: 999px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
    z-index: var(--z-loading-bar);
    pointer-events: none;
    opacity: 0;
    transform: translateY(8px);
    transition: opacity 0.2s ease, transform 0.2s ease;
}

.loading-pill.is-active {
    opacity: 1;
    transform: translateY(0);
}

.loading-label {
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.01em;
}

.loading-spinner {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.35);
    border-top-color: var(--primary);
    animation: loading-spin 0.7s linear infinite;
    flex-shrink: 0;
}

@media (prefers-reduced-motion: reduce) {
    .loading-spinner {
        animation: loading-pulse 1.2s ease-in-out infinite;
        border-top-color: rgba(255, 255, 255, 0.35);
        background: var(--primary);
    }
}

@keyframes loading-spin {
    to {
        transform: rotate(360deg);
    }
}

@keyframes loading-pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 1; }
}

.visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    border: 0;
}
</style>
