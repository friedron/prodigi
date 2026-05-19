<template>
    <div class="compare-measurement-page container-fluid px-0">
        <div class="logo-section mb-4">
            <LogoLine
                :logos="[
                    { src: '/static/logos/sztaki_logo.svg', alt: 'Sztaki Logo' },
                    { src: '/static/logos/UGR_logo.PNG', alt: 'Sztaki Logo' },
                    { src: '/static/logos/UL_logo.png', alt: 'Uni Logo' },
                ]"
            />
        </div>

        <BackButton :prevPage="'measurements'" :changePage="changePage" />

        <div class="card-pro content-card mb-4 mt-4">
            <div class="d-flex align-items-center mb-4 pb-2 border-bottom">
                <i class="bi bi-link-45deg fs-4 me-2 text-primary"></i>
                <h2 class="h4 mb-0">Link QoI and Measurement</h2>
                <div class="ms-auto">
                    <Tooltip
                        content="
                    <p>
                        Connect <strong>QoI parameters</strong> to their corresponding measurements by
                        selecting the dots in the left and right columns.
                    </p>
                    <ul>
                        <li>Click a dot in the left column to start a link.</li>
                        <li>Click the matching dot in the right column to complete the connection.</li>
                    </ul>
                    <p>Press <strong>Finalize</strong> when you have matched all parameters to their measurements.</p>
                    "
                    />
                </div>
            </div>

            <p class="text-muted mb-4">Establish relationships between your model's Quantities of Interest and the physical measurements.</p>

            <div class="connection-container border rounded bg-light">
                <!-- LEFT COLUMN -->
                <div class="column">
                    <div class="column-header text-muted small text-uppercase fw-bold mb-3 px-2">Model QoIs</div>
                    <div v-for="(item, index) in qoi" :key="'left-' + index" class="item">
                        <span class="item-text text-end pe-3">{{ item }}</span>
                        <div
                            class="dot"
                            @click="handleDotClick('left', index)"
                            :class="{
                                connected: isConnected('left', index),
                                selected: selectedDot && selectedDot.side === 'left' && selectedDot.index === index,
                            }"
                        ></div>
                    </div>
                </div>

                <!-- CONNECTION LINES SVG -->
                <svg class="connections-svg" ref="svg">
                    <line
                        v-for="(conn, i) in connections"
                        :key="'conn-' + i"
                        :x1="conn.x1"
                        :y1="conn.y1"
                        :x2="conn.x2"
                        :y2="conn.y2"
                        stroke="var(--primary)"
                        stroke-width="3"
                        stroke-linecap="round"
                        opacity="0.8"
                    />
                </svg>

                <!-- RIGHT COLUMN -->
                <div class="column">
                    <div class="column-header text-muted small text-uppercase fw-bold mb-3 px-2">Measurements</div>
                    <div v-for="(item, index) in measured" :key="'right-' + index" class="item">
                        <div
                            class="dot"
                            @click="handleDotClick('right', index)"
                            :class="{
                                connected: isConnected('right', index),
                                selected: selectedDot && selectedDot.side === 'right' && selectedDot.index === index,
                            }"
                        ></div>
                        <span class="item-text ps-3">{{ item }}</span>
                    </div>
                </div>
            </div>

            <div class="d-flex justify-content-center mt-4">
                <button 
                    class="btn-pro px-5 py-2" 
                    :class="{ 'btn-outline-pro': connections.length === 0 }"
                    :disabled="connections.length === 0"
                    @click="finalize"
                >
                    <i class="bi bi-check-all me-2"></i> Finalize Mapping
                </button>
            </div>
        </div>

        <NextButton :nextPage="'update'" :available="pageDone" :changePage="changePage" />
    </div>
</template>

<script>
import LogoLine from "./LogoLine.vue";
import BackButton from "./BackButton.vue";
import NextButton from "./NextButton.vue";
import Tooltip from "./Tooltip.vue";

export default {
    components: {
        BackButton,
        LogoLine,
        NextButton,
        Tooltip,
    },
    props: {
        qoi: { type: Array, required: true },
        measured: { type: Array, required: true },
        changePage: { type: Function, required: true },
        socket: { type: Object, required: true },
        addPageDone: { type: Function, required: true },
    },
    data() {
        return {
            selectedDot: null, // { side: 'left'|'right', index: number }
            connections: [], // { leftIndex, rightIndex, x1, y1, x2, y2 }
            pageDone: false,
        };
    },
    methods: {
        handleDotClick(side, index) {
            if (!this.selectedDot) {
                this.selectedDot = { side, index };
                return;
            }
            if (this.selectedDot.side === side) {
                this.selectedDot = { side, index };
                return;
            }
            const leftIndex = side === "left" ? index : this.selectedDot.index;
            const rightIndex = side === "right" ? index : this.selectedDot.index;

            // Remove existing connections from either side
            this.connections = this.connections.filter(
                (conn) => conn.leftIndex !== leftIndex && conn.rightIndex !== rightIndex
            );

            this.connections.push({ leftIndex, rightIndex, x1: 0, y1: 0, x2: 0, y2: 0 });

            this.selectedDot = null;
            this.$nextTick(this.updateConnectionPositions);
        },
        isConnected(side, index) {
            if (side === "left") {
                return this.connections.some((conn) => conn.leftIndex === index);
            } else {
                return this.connections.some((conn) => conn.rightIndex === index);
            }
        },
        updateConnectionPositions() {
            if (!this.$refs.svg) return;
            const svgRect = this.$refs.svg.getBoundingClientRect();
            this.connections.forEach((conn) => {
                const leftDot = this.$el.querySelector(
                    `.column:first-child .item:nth-child(${conn.leftIndex + 2}) .dot`
                );
                const rightDot = this.$el.querySelector(
                    `.column:last-child .item:nth-child(${conn.rightIndex + 2}) .dot`
                );
                if (leftDot && rightDot) {
                    const leftRect = leftDot.getBoundingClientRect();
                    const rightRect = rightDot.getBoundingClientRect();
                    conn.x1 = leftRect.left + leftRect.width / 2 - svgRect.left;
                    conn.y1 = leftRect.top + leftRect.height / 2 - svgRect.top;
                    conn.x2 = rightRect.left + rightRect.width / 2 - svgRect.left;
                    conn.y2 = rightRect.top + rightRect.height / 2 - svgRect.top;
                }
            });
        },
        finalize() {
            const cons = this.connections.map((conn) => [this.qoi[conn.leftIndex], this.measured[conn.rightIndex]]);
            if (cons.length > 0) {
                this.socket.emit("name_pairs", cons);
                this.pageDone = true;
                this.addPageDone("compare");
            }
        },
        autoConnectMatchingPairs() {
            this.qoi.forEach((leftItem, leftIndex) => {
                this.measured.forEach((rightItem, rightIndex) => {
                    if (leftItem === rightItem) {
                        const alreadyConnected = this.connections.some(
                            (c) => c.leftIndex === leftIndex || c.rightIndex === rightIndex
                        );
                        if (!alreadyConnected) {
                            this.connections.push({
                                leftIndex,
                                rightIndex,
                                x1: 0,
                                y1: 0,
                                x2: 0,
                                y2: 0,
                            });
                        }
                    }
                });
            });
            this.$nextTick(this.updateConnectionPositions);
        },
    },
    mounted() {
        window.addEventListener("resize", this.updateConnectionPositions);
        this.autoConnectMatchingPairs();
        this.$nextTick(this.updateConnectionPositions);
    },
    updated() {
        this.$nextTick(this.updateConnectionPositions);
    },
    beforeUnmount() {
        window.removeEventListener("resize", this.updateConnectionPositions);
    },
};
</script>

<style scoped>
.compare-measurement-page {
    max-width: 1100px;
    margin: 0 auto;
}

.content-card {
    padding: var(--spacing-lg);
}

.connection-container {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    position: relative;
    padding: var(--spacing-xl) var(--spacing-lg);
    min-height: 400px;
    user-select: none;
    gap: 100px;
}

.column {
    display: flex;
    flex-direction: column;
    flex: 1;
    z-index: 2;
}

.column-header {
    letter-spacing: 0.05em;
    border-bottom: 2px solid var(--secondary);
    padding-bottom: 0.5rem;
    margin-bottom: 2rem !important;
}

.item {
    display: flex;
    align-items: center;
    margin-bottom: 2.5rem;
    position: relative;
}

.item-text {
    flex: 1;
    font-size: 0.95rem;
    font-weight: 500;
    color: var(--text-main);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.dot {
    width: 20px;
    height: 20px;
    background-color: white;
    border: 3px solid var(--border-color);
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    z-index: 3;
}

.dot:hover {
    border-color: var(--primary);
    transform: scale(1.15);
}

.dot.connected {
    background-color: var(--primary);
    border-color: var(--primary);
}

.dot.selected {
    background-color: white;
    border-color: var(--accent);
    box-shadow: 0 0 0 4px rgba(255, 102, 0, 0.2);
    transform: scale(1.2);
}

.column:first-child .item {
    justify-content: flex-end;
}

.column:last-child .item {
    justify-content: flex-start;
}

.connections-svg {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1;
}
</style>