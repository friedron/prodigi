<template>
    <div class="tooltip-container">
        <button 
            class="tooltip-btn" 
            @mouseenter="onMouseOver" 
            @mousemove="onMouseMove" 
            @mouseleave="showTooltip = false"
            type="button"
        >
            <img src="/info.png" alt="info" class="info-icon" />
        </button>
        
        <Teleport to="body">
            <Transition name="fade">
                <div
                    v-if="showTooltip"
                    class="custom-tooltip"
                    :style="{ top: tooltipPosition.top + 'px', left: tooltipPosition.left + 'px' }"
                    ref="tooltip"
                >
                    <div class="tooltip-content" v-html="content"></div>
                </div>
            </Transition>
        </Teleport>
    </div>
</template>

<script>
export default {
    props: {
        content: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            showTooltip: false,
            tooltipPosition: { top: 0, left: 0 },
        };
    },
    methods: {
        onMouseOver(event) {
            this.showTooltip = true;
            this.$nextTick(() => {
                this.updateTooltipPosition(event);
            });
        },
        onMouseMove(event) {
            if (this.showTooltip) {
                this.updateTooltipPosition(event);
            }
        },
        updateTooltipPosition(event) {
            const padding = 15;
            const tooltip = this.$refs.tooltip;
            if (!tooltip) return;

            const tooltipWidth = tooltip.offsetWidth;
            const tooltipHeight = tooltip.offsetHeight;
            
            let left = event.clientX + 15;
            let top = event.clientY + 15;

            // Horizontal boundary check
            if (left + tooltipWidth > window.innerWidth - padding) {
                left = window.innerWidth - tooltipWidth - padding;
            }
            if (left < padding) {
                left = padding;
            }

            // Vertical boundary check
            if (top + tooltipHeight > window.innerHeight - padding) {
                top = event.clientY - tooltipHeight - 15;
            }
            if (top < padding) {
                top = padding;
            }

            this.tooltipPosition = { top, left };
        },
    },
};
</script>

<style scoped>
.tooltip-container {
    display: inline-block;
    vertical-align: middle;
    line-height: 1;
}

.tooltip-btn {
    background: none;
    border: none;
    padding: 0;
    margin-left: 8px;
    cursor: help;
    display: flex;
    align-items: center;
    transition: transform 0.2s ease;
}

.tooltip-btn:hover {
    transform: scale(1.1);
}

.info-icon {
    width: 20px;
    height: 20px;
    object-fit: contain;
}

.custom-tooltip {
    position: fixed;
    background-color: #2c3e50;
    color: #ffffff;
    padding: var(--spacing-md);
    border-radius: var(--radius);
    font-size: 0.9rem;
    max-width: 400px;
    z-index: var(--z-tooltip);
    pointer-events: none;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.1);
    line-height: 1.5;
}

.tooltip-content :deep(h3) {
    color: #ffffff;
    font-size: 1rem;
    margin-bottom: 0.5rem;
    margin-top: 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    padding-bottom: 0.25rem;
}

.tooltip-content :deep(p) {
    margin-bottom: 0.5rem;
}

.tooltip-content :deep(p:last-child) {
    margin-bottom: 0;
}

.tooltip-content :deep(code) {
    background: rgba(0, 0, 0, 0.3);
    padding: 2px 4px;
    border-radius: 3px;
    font-family: monospace;
}

/* Animation */
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
