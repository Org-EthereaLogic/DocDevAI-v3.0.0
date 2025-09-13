import apiClient from './index';

export const settingsAPI = {
  // Get settings
  getSettings: async () => {
    return {
      data: {
        privacy: { mode: 'local' },
        appearance: { theme: 'system' },
        ai: { defaultProvider: 'gpt-4' }
      }
    };
  },

  // Update settings
  updateSettings: async (settings) => {
    return {
      data: { ...settings, updated: true }
    };
  }
};
