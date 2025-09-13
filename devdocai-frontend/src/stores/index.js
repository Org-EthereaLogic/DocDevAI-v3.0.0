import { createPinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';

const pinia = createPinia();

// Add persistence plugin for selected stores
pinia.use(piniaPluginPersistedstate);

export default pinia;

// Export all stores for easy importing
export { useAuthStore } from './auth';
export { useDocumentStore } from './document';
export { useTemplateStore } from './template';
export { useProjectStore } from './project';
export { useSettingsStore } from './settings';
export { useOnboardingStore } from './onboarding';
export { useNotificationStore } from './notification';
export { useReviewStore } from './review';
