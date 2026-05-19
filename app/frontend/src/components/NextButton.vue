<template>
    <div class="next-button-container">
        <button
            :class="['btn-pro', { 'btn-disabled': !available }]"
            :disabled="!available"
            @click="changePage(nextPage)"
        >
            Next <i class="bi bi-chevron-right"></i>
        </button>
    </div>
</template>

<script>
export default {
    props: {
        nextPage: { type: String, required: true },
        available: { type: Boolean, required: true },
        changePage: { type: Function, required: true },
    },
};
</script>

<style scoped>
.next-button-container {
    display: flex;
    justify-content: center;
    margin-top: var(--spacing-lg);
}

.btn-disabled {
    background-color: var(--secondary) !important;
    border-color: var(--border-color) !important;
    color: var(--text-muted) !important;
    cursor: not-allowed !important;
    transform: none !important;
    box-shadow: none !important;
    opacity: 0.6;
}

.btn-pro i {
    font-size: 0.8rem;
    transition: transform 0.2s ease;
}

.btn-pro:not(.btn-disabled):hover i {
    transform: translateX(2px);
}
</style>
