<template>
  <div class="landing-page d-flex flex-column justify-content-center align-items-center">
    <img src="/logos/trace_logo2.png" alt="Trace Structures Logo" class="main-logo" style="max-width: 10vw" />
            <h1 class="logo-title">
                <span class="orange">TRACE Structures</span><span class="blue"> – API for </span>
                <span class="orange">T</span><span class="blue">winning, </span> <span class="orange">R</span
                ><span class="blue">esilience, and </span> <span class="orange">A</span
                ><span class="blue">I-driven </span> <span class="orange">C</span
                ><span class="blue">omputational </span> <span class="orange">E</span
                ><span class="blue">ngineering for Building </span>
                <span class="orange">Structures</span>
            </h1>
    <button class="btn btn-lg btn-primary mb-4" @click="goToApp">🚀 Start App</button>
    <div class="d-flex flex-wrap justify-content-center gap-3 mb-4">
      <a href="https://buildchain-project.eu/" class="btn btn-outline-secondary" target="_blank">🌍 Buildchain Website</a>
      <a href="/notebooks" class="btn btn-outline-secondary" target="_blank">📓 Notebooks</a>
      <a href="/templates" class="btn btn-outline-secondary" target="_blank">📝 Templates</a>
      <a href="./trace_deliverable.pdf" class="btn btn-outline-secondary" target="_blank">📑 Documentation</a>
    </div>
  </div>
</template>

<style scoped>
.landing-page {
  margin-left: -20vw;
  height: 100vh;
  width: 100vw;
  padding: 2rem;
  box-sizing: border-box;
  background: #f8f9fa;
  align-self: flex-start
  /* flex centering is inherited from classes */
}

.main-logo {
  max-width: 300px;
  margin-bottom: 1.5rem;
}

.logo-title {
  font-size: 2.5rem;
  margin-bottom: 2.5rem;
  color: #00649e; /* match your blue */
}

a.btn-outline-secondary {
  min-width: 160px;
}
</style>

<script>
export default {
  methods: {
    goToApp() {
        this.$router.push("/app");
    },
  },
};
</script>
