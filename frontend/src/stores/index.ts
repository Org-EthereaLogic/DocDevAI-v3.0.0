// Pinia Stores - Central Configuration and Export

import { createPinia } from 'pinia';
import type { App } from 'vue';

// Create Pinia instance
export const pinia = createPinia();

// Store persistence plugin (for localStorage)
const persistencePlugin = ({ store }: { store: any }) => {
  const storageKey = `devdocai-${store.$id}`;

  // Restore state from localStorage on store creation
  const savedState = localStorage.getItem(storageKey);
  if (savedState) {
    try {
      const parsedState = JSON.parse(savedState);

      // Restore only specific fields that should be persisted
      if (store.$id === 'config' && parsedState.settings) {
        store.settings = parsedState.settings;
        if (parsedState.lastFetchTime) {
          store.lastFetchTime = new Date(parsedState.lastFetchTime);
        }
      }

      if (store.$id === 'app' && parsedState.theme) {
        store.theme = parsedState.theme;
        store.sidebarCollapsed = parsedState.sidebarCollapsed;
        store.language = parsedState.language;
      }

      if (store.$id === 'documents') {
        // Only persist filters, not actual data
        if (parsedState.templatesFilter) {
          store.templatesFilter = parsedState.templatesFilter;
        }
        if (parsedState.documentsFilter) {
          store.documentsFilter = parsedState.documentsFilter;
        }
      }
    } catch (error) {
      console.warn(`Failed to restore state for store ${store.$id}:`, error);
    }
  }

  // Save state to localStorage on any mutation
  store.$subscribe((mutation: any, state: any) => {
    // Only persist specific stores and fields
    const persistentStores = ['config', 'app', 'documents'];

    if (!persistentStores.includes(store.$id)) {
      return;
    }

    let dataToSave: any = {};

    if (store.$id === 'config') {
      dataToSave = {
        settings: state.settings,
        lastFetchTime: state.lastFetchTime,
      };
    }

    if (store.$id === 'app') {
      dataToSave = {
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        language: state.language,
      };
    }

    if (store.$id === 'documents') {
      dataToSave = {
        templatesFilter: state.templatesFilter,
        documentsFilter: state.documentsFilter,
      };
    }

    try {
      localStorage.setItem(storageKey, JSON.stringify(dataToSave));
    } catch (error) {
      console.warn(`Failed to save state for store ${store.$id}:`, error);
    }
  });
};

// Add persistence plugin
pinia.use(persistencePlugin);

// Export stores
export { useConfigStore } from './config';
export { useDocumentsStore } from './documents';
export { useAppStore } from './app';
export { useNotificationsStore } from './notifications';

// Store installation function
export const installStores = (app: App) => {
  app.use(pinia);
  return pinia;
};

// Store initialization function
export const initializeStores = async () => {
  // Import stores to ensure they're available
  const { useConfigStore } = await import('./config');
  const { useAppStore } = await import('./app');
  const { useDocumentsStore } = await import('./documents');

  // Initialize stores that need setup
  const configStore = useConfigStore();
  const appStore = useAppStore();
  const documentsStore = useDocumentsStore();

  try {
    // Initialize configuration first
    await configStore.initialize();

    // Initialize app theme and settings
    await appStore.initialize();

    // Initialize documents if config is ready
    if (configStore.isConfigured) {
      await documentsStore.initialize();
    }
  } catch (error) {
    console.error('Store initialization failed:', error);
    // Don't throw here - let the app continue with default state
  }
};

// Cleanup function for testing or app teardown
export const resetStores = () => {
  // Clear localStorage for all stores
  const stores = ['config', 'app', 'documents', 'notifications'];
  stores.forEach(storeId => {
    localStorage.removeItem(`devdocai-${storeId}`);
  });

  // Reset Pinia state
  pinia.state.value = {};
};

// Development helpers
if (import.meta.env.DEV) {
  // Make stores available globally for debugging
  (window as any).__PINIA__ = pinia;

  // Store performance monitoring
  const storePerformance: Record<string, { calls: number; totalTime: number }> = {};

  pinia.use(({ store }) => {
    const storeId = store.$id;
    storePerformance[storeId] = { calls: 0, totalTime: 0 };

    store.$onAction(({ name, after, onError }) => {
      const start = Date.now();

      after(() => {
        const duration = Date.now() - start;
        storePerformance[storeId].calls++;
        storePerformance[storeId].totalTime += duration;

        if (duration > 100) {
          console.warn(`Slow store action: ${storeId}.${name} took ${duration}ms`);
        }
      });

      onError((error) => {
        console.error(`Store action error: ${storeId}.${name}`, error);
      });
    });
  });

  // Expose performance data
  (window as any).__STORE_PERFORMANCE__ = storePerformance;
}

export default pinia;