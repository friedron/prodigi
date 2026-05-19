<template>
    <div class="pro-modal-backdrop" @click.self="$emit('cancel')">
        <div class="pro-modal-dialog card-pro" @click.stop>
            <div class="modal-header mb-3">
                <h2 v-if="title" class="modal-title">{{ title }}</h2>
                <button type="button" class="btn-close-custom" @click="$emit('cancel')">&times;</button>
            </div>
            <div class="modal-body">
                <p class="modal-message">{{ message }}</p>
            </div>
            <div class="modal-footer d-flex justify-content-end gap-3 pt-3 border-top" style="position: relative; z-index: 2">
                <button @click="$emit('cancel')" class="btn-pro btn-outline-pro">Cancel</button>
                <button @click="$emit('confirm')" class="btn-pro">Confirm</button>
            </div>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        title: {
            type: String,
            required: false,
            default: "Confirm Action"
        },
        message: {
            type: String,
            required: true,
        },
    },
    emits: ["confirm", "cancel"],
};
</script>

<style scoped>
.pro-modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: var(--z-confirm-backdrop);
}

.pro-modal-dialog {
    width: 100%;
    max-width: 450px;
    margin: 0 var(--spacing-md);
    background: white;
    position: relative;
    z-index: var(--z-confirm-dialog);
    pointer-events: auto;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-title {
    font-size: 1.5rem;
    margin: 0;
    color: var(--text-main);
}

.btn-close-custom {
    background: none;
    border: none;
    font-size: 2rem;
    line-height: 1;
    cursor: pointer;
    color: var(--text-muted);
    transition: color 0.2s;
}

.btn-close-custom:hover {
    color: var(--danger);
}

.modal-message {
    font-size: 1.05rem;
    color: var(--text-main);
    margin: var(--spacing-md) 0;
}
</style>
