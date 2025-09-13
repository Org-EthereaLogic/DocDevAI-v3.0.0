// Configuration Store - M001 Integration

import { defineStore } from 'pinia';
import { ref, computed, readonly } from 'vue';
import type { Ref } from 'vue';
import { configurationService } from '@/services';
import type { ConfigurationSettings } from '@/types/api';

export const useConfigStore = defineStore('config', () => {
  // State
  const settings = ref<ConfigurationSettings | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  const lastFetchTime = ref<Date | null>(null);

  // Getters
  const isConfigured = computed(() => settings.value !== null);

  const privacyMode = computed(() => settings.value?.privacy_mode || 'local_only');

  const memoryMode = computed(() => settings.value?.memory_mode || 'medium');

  const aiProvidersConfig = computed(() => settings.value?.ai_providers || {
    primary: 'claude',
    fallback: ['openai', 'gemini'],
    budget_limit: 10
  });

  const isEncryptionEnabled = computed(() => settings.value?.encryption_enabled ?? true);

  const isTelemetryEnabled = computed(() => settings.value?.telemetry_enabled ?? false);

  // Actions
  const fetchConfiguration = async () => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await configurationService.getConfiguration();
      settings.value = response.data;
      lastFetchTime.value = new Date();
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to fetch configuration';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const updateConfiguration = async (updates: Partial<ConfigurationSettings>) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await configurationService.updateConfiguration(updates);
      settings.value = response.data;
      lastFetchTime.value = new Date();
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update configuration';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const resetToDefaults = async () => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await configurationService.resetToDefaults();
      settings.value = response.data;
      lastFetchTime.value = new Date();
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to reset configuration';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const setPrivacyMode = async (mode: ConfigurationSettings['privacy_mode']) => {
    if (!settings.value) return;

    await updateConfiguration({
      ...settings.value,
      privacy_mode: mode
    });
  };

  const setMemoryMode = async (mode: ConfigurationSettings['memory_mode']) => {
    if (!settings.value) return;

    await updateConfiguration({
      ...settings.value,
      memory_mode: mode
    });
  };

  const setPrimaryAIProvider = async (provider: string) => {
    if (!settings.value) return;

    await updateConfiguration({
      ...settings.value,
      ai_providers: {
        ...settings.value.ai_providers,
        primary: provider
      }
    });
  };

  const setBudgetLimit = async (limit: number) => {
    if (!settings.value) return;

    await updateConfiguration({
      ...settings.value,
      ai_providers: {
        ...settings.value.ai_providers,
        budget_limit: limit
      }
    });
  };

  const toggleEncryption = async () => {
    if (!settings.value) return;

    await updateConfiguration({
      ...settings.value,
      encryption_enabled: !settings.value.encryption_enabled
    });
  };

  const toggleTelemetry = async () => {
    if (!settings.value) return;

    await updateConfiguration({
      ...settings.value,
      telemetry_enabled: !settings.value.telemetry_enabled
    });
  };

  const clearError = () => {
    error.value = null;
  };

  const refreshIfStale = async (maxAgeMinutes = 5) => {
    if (!lastFetchTime.value || !settings.value) {
      await fetchConfiguration();
      return;
    }

    const ageMinutes = (Date.now() - lastFetchTime.value.getTime()) / (1000 * 60);
    if (ageMinutes > maxAgeMinutes) {
      await fetchConfiguration();
    }
  };

  // Initialize store
  const initialize = async () => {
    if (!settings.value) {
      await fetchConfiguration();
    }
  };

  return {
    // State
    settings: readonly(settings),
    isLoading: readonly(isLoading),
    error: readonly(error),
    lastFetchTime: readonly(lastFetchTime),

    // Getters
    isConfigured,
    privacyMode,
    memoryMode,
    aiProvidersConfig,
    isEncryptionEnabled,
    isTelemetryEnabled,

    // Actions
    fetchConfiguration,
    updateConfiguration,
    resetToDefaults,
    setPrivacyMode,
    setMemoryMode,
    setPrimaryAIProvider,
    setBudgetLimit,
    toggleEncryption,
    toggleTelemetry,
    clearError,
    refreshIfStale,
    initialize,
  };
});


// Types for store composables
export type ConfigStore = ReturnType<typeof useConfigStore>;

// Store persistence plugin
export const configPersistPlugin = {
  key: 'devdocai-config',
  storage: localStorage,
  paths: ['settings', 'lastFetchTime'],
  beforeRestore: (context: any) => {
    // Validate stored data before restoring
    if (context.store.lastFetchTime) {
      context.store.lastFetchTime = new Date(context.store.lastFetchTime);
    }
  },
};