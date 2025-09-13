import apiClient from './index';

export const trackingAPI = {
  // Get suite tracking information (real backend endpoint)
  getSuiteTracking: async (suiteId) => {
    try {
      const response = await apiClient.get(`/v1/suites/${suiteId}/tracking`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error fetching suite tracking for ${suiteId}:`, error);
      throw error;
    }
  },

  // Legacy methods for backward compatibility
  getTrackingMatrix: async () => {
    console.warn('trackingAPI.getTrackingMatrix() is deprecated - use getSuiteTracking() instead');
    return {
      data: {
        nodes: [],
        edges: [],
        dependencies: []
      }
    };
  },

  getDependencies: async (documentId) => {
    console.warn('trackingAPI.getDependencies() is deprecated - use getSuiteTracking() instead');
    return {
      data: {
        dependencies: [],
        dependents: []
      }
    };
  }
};
