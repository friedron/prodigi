<template>
    <div class="logo-line-container">
        <div class="logo-line">
            <img v-for="(logo, index) in logos" :key="index" :src="logo.src" :alt="logo.alt" class="logo-image" />
        </div>
    </div>
</template>
<script>
export default {
    props: {
        logos: {
            type: Array,
            default: () => [],
        },
    },
};
</script>

<style scoped>
.logo-line-container {
    display: flex;
    justify-content: center;
    width: 100%;
    margin-bottom: var(--spacing-lg);
}

.logo-line {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 2.5rem;
    padding: var(--spacing-sm) var(--spacing-xl);
    background: white;
    border-radius: 50px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.03);
    border: 1px solid var(--border-color);
}

.logo-image {
    height: 3.5rem;
    width: auto;
    object-fit: contain;
    transition: transform 0.3s ease;
}

.logo-image:hover {
    transform: translateY(-2px);
}
</style>
