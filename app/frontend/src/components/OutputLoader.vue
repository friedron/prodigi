<template>
    <button class="btn-pro" @click="$emit('save-file')" :disabled="loading">
        <span v-if="loading" class="btn-spinner"></span>
        {{ loading ? "Saving\u2026" : title }}
    </button>
</template>

<script>
export default {
    props: {
        title: { type: String, required: true },
        // Owned by the parent, which knows when THIS button's specific
        // request/response round-trip completes - keeps buttons independent
        // instead of all reacting to any socket activity in the app.
        loading: { type: Boolean, default: false },
    },
    emits: ["save-file"],
};
</script>

<style scoped>
.btn-spinner {
    width: 14px;
    height: 14px;
    border-radius: 50%;
    border: 2px solid rgba(127, 127, 127, 0.35);
    border-top-color: currentColor;
    animation: btn-spin 0.7s linear infinite;
    display: inline-block;
    flex-shrink: 0;
}

@keyframes btn-spin {
    to { transform: rotate(360deg); }
}
</style>
