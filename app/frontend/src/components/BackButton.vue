<template>
    <div class="back-button-container">
        <button class="btn-back" @click="changePage(prevPage)">
            <i class="bi bi-chevron-left"></i> Back
        </button>
    </div>
</template>

<script>
export default {
    props: {
        prevPage: {
            type: String,
            required: true,
        },
        changePage: {
            type: Function,
            required: true,
        },
    },
};
</script>

<style scoped>
.back-button-container {
    display: flex;
    justify-content: center;
    margin-bottom: var(--spacing-lg);
}

.btn-back {
    background-color: transparent;
    color: var(--text-muted);
    padding: 0.5rem 1.25rem;
    border-radius: var(--radius);
    border: 1px solid var(--border-color);
    font-weight: 500;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
}

.btn-back:hover {
    background-color: var(--secondary);
    color: var(--text-main);
    border-color: var(--text-muted);
    transform: translateX(-2px);
}

.btn-back i {
    font-size: 0.8rem;
}
</style>
