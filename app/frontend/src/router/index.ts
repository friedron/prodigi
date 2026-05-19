import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import HomeView from '../views/HomeView.vue';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'home',
    component: HomeView,
  },
  {
    path: '/subtracting',
    name: 'subtracting',
    component: () => import('../views/SubtractingView.vue'),
    children: [
      { path: 'upload', component: () => import('../components/UploadPage.vue') },
      { path: 'params', component: () => import('../components/subtracting/ParamPageDD.vue') },
      { path: 'exploratory', component: () => import('../components/subtracting/Exploratory.vue') },
      { path: 'surrogate', component: () => import('../components/surrogate/SurrogatePage.vue') },
      { path: 'uq', component: () => import('../components/UqPage.vue') },
      { path: 'subtract', component: () => import('../components/subtracting/SubtractEffects.vue') },
      { path: 'thresholdExceedance', component: () => import('../components/subtracting/ThresholdExceedance.vue') },
    ]
  },
  {
    path: '/surrogate',
    name: 'surrogate',
    component: () => import('../views/SurrogateView.vue'),
    children: [
      { path: 'upload', component: () => import('../components/UploadPage.vue') },
      { path: 'params', component: () => import('../components/surrogate/ParamPage.vue') },
      { path: 'sample', component: () => import('../components/surrogate/SampleQoIPage.vue') },
      { path: 'exploratory', component: () => import('../components/subtracting/Exploratory.vue') },
      { path: 'surrogate', component: () => import('../components/surrogate/SurrogatePage.vue') },
      { path: 'uq', component: () => import('../components/UqPage.vue') },
      { path: 'measurements', component: () => import('../components/surrogate/MeasurementsPage.vue') },
      { path: 'compare', component: () => import('../components/CompareMeasurement.vue') },
      { path: 'update', component: () => import('../components/UpdatePage.vue') },
    ]
  },
  {
    path: '/inverse',
    name: 'inverse',
    component: () => import('../views/InverseView.vue'),
    children: [
      { path: 'upload', component: () => import('../components/UploadPage.vue') },
      { path: 'params', component: () => import('../components/surrogate/ParamPage.vue') },
      { path: 'sample', component: () => import('../components/surrogate/SampleQoIPage.vue') },
      { path: 'exploratory', component: () => import('../components/subtracting/Exploratory.vue') },
      { path: 'inverse', component: () => import('../components/surrogate/SurrogatePage.vue') }, // Placeholder
      { path: 'measurements', component: () => import('../components/surrogate/MeasurementsPage.vue') },
      { path: 'compare', component: () => import('../components/CompareMeasurement.vue') },
      { path: 'compute', component: () => import('../components/UpdatePage.vue') }, // Placeholder
    ]
  },
  {
    path: '/multi-model',
    name: 'multiModel',
    component: () => import('../views/MultiModelView.vue'),
    children: [
      { path: 'upload', component: () => import('../components/UploadPage.vue') },
      { path: 'measurements', component: () => import('../components/multiModel/MeasurementsPageMulti.vue') },
      { path: 'update', component: () => import('../components/UpdatePage.vue') },
    ]
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

export default router;
