<template>
  <div>
    <button class="btn-pro" @click="showModal = true">
      <i class="bi bi-box-arrow-in-down"></i> Input Loader
    </button>

    <Teleport to="body">
      <div
        v-if="showModal"
        class="pro-modal-backdrop"
        @click.self="closeModal"
      >
        <div class="pro-modal-dialog card-pro" @click.stop>
          <div class="modal-header mb-4">
            <h2 class="modal-title">Select Loader Type</h2>
            <button type="button" class="btn-close-custom" @click="closeModal">&times;</button>
          </div>

          <div class="modal-body">
            <div class="loader-selector mb-4 p-3 bg-light rounded">
              <label class="d-block mb-3 fw-bold text-muted text-uppercase small">Source Option</label>
              <div class="d-flex gap-4">
                <div class="form-check-pro">
                  <input
                    type="radio"
                    id="option1"
                    value="weather"
                    v-model="selectedOption"
                    class="radio-custom"
                  />
                  <label for="option1">Weather Data Loader</label>
                </div>
                <div class="form-check-pro">
                  <input
                    type="radio"
                    id="option2"
                    value="fileApi"
                    v-model="selectedOption"
                    class="radio-custom"
                  />
                  <label for="option2">File/API Loader</label>
                </div>
              </div>
            </div>

            <div class="nested-loader-container mt-2">
              <div v-if="selectedOption === 'weather'">
                <WeatherApi :socket="socket" @load-file="$emit('load-file', $event)" @close="closeModal" />
              </div>

              <div v-if="selectedOption === 'fileApi'">
                <InputLoader
                  :socket="socket"
                  :dkgApiStatus="dkgApiStatus"
                  fileType=".csv"
                  loadType="features"
                  @load-file="$emit('load-file', $event)"
                  @close="closeModal"
                  :dkgToken="dkgToken"
                />
              </div>
            </div>
          </div>

          <div class="modal-footer d-flex justify-content-end pt-4 mt-3 border-top">
            <button type="button" class="btn-pro btn-outline-pro" @click="closeModal">Close</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script>
import WeatherApi from './WeatherApi.vue';
import InputLoader from './InputLoader.vue';

export default {
  name: 'InputLoaderExtended',
  components: { WeatherApi, InputLoader },
  props: {
    socket: { type: Object, required: true },
    dkgApiStatus: { type: String, required: true },
    dkgToken: { type: String, required: true },
  },
  emits: ['load-file'],
  data() {
    return {
      showModal: false,
      selectedOption: 'weather',
    };
  },
  methods: {
    closeModal() {
      this.showModal = false;
    },
  },
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
    z-index: var(--z-modal-backdrop);
}

.pro-modal-dialog {
    width: 100%;
    max-width: 600px;
    margin: 0 var(--spacing-md);
    background: white;
    max-height: 90vh;
    overflow-y: auto;
    position: relative;
    z-index: var(--z-modal-dialog);
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

.form-check-pro {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
}

.radio-custom {
    width: 18px;
    height: 18px;
    accent-color: var(--primary);
    cursor: pointer;
}

.form-check-pro label {
    cursor: pointer;
    font-weight: 500;
}

.nested-loader-container {
    min-height: 100px;
}

/* Override nested component spacing to fit modal better */
:deep(.btn-pro.m-3) {
    margin: 0 !important;
    width: 100%;
    margin-top: 1rem !important;
}
</style>
