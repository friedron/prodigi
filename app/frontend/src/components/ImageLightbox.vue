<template>
    <Teleport to="body">
        <div v-if="src" class="image-lightbox" @click="src = null">
            <img :src="src" alt="Enlarged plot" />
        </div>
    </Teleport>
</template>

<script>
// Any <img class="plot-img"> (or class="zoomable") opens here on click, so
// pages don't need their own click handlers.
const ZOOMABLE = "img.plot-img, img.zoomable";

export default {
    data() {
        return { src: null };
    },
    mounted() {
        this._onClick = (e) => {
            const img = e.target instanceof Element ? e.target.closest(ZOOMABLE) : null;
            if (img && img.src) this.src = img.src;
        };
        this._onKey = (e) => {
            if (e.key === "Escape") this.src = null;
        };
        document.addEventListener("click", this._onClick);
        document.addEventListener("keydown", this._onKey);
    },
    beforeUnmount() {
        document.removeEventListener("click", this._onClick);
        document.removeEventListener("keydown", this._onKey);
    },
};
</script>

<style scoped>
.image-lightbox {
    position: fixed;
    inset: 0;
    z-index: 2000;
    background: rgba(0, 0, 0, 0.85);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    cursor: zoom-out;
}

.image-lightbox img {
    max-width: 100%;
    max-height: 100%;
    background: white;
    border-radius: var(--radius);
}
</style>
