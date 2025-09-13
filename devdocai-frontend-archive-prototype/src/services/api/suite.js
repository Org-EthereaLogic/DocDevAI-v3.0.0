import apiClient, { buildQueryString } from './index';

export const suiteAPI = {
  // Get all suites (real backend endpoint)
  getSuites: async (params = {}) => {
    try {
      const queryString = buildQueryString({
        status: params.status,
        project_id: params.project_id,
        limit: params.limit || 50,
        offset: params.offset || 0
      });

      const response = await apiClient.get(`/v1/suites${queryString}`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error('Error fetching suites:', error);
      throw error;
    }
  },

  // Get suite by ID (real backend endpoint)
  getSuite: async (suiteId) => {
    try {
      const response = await apiClient.get(`/v1/suites/${suiteId}`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error fetching suite ${suiteId}:`, error);
      throw error;
    }
  },

  // Create new suite (real backend endpoint)
  createSuite: async (suiteData) => {
    try {
      const response = await apiClient.post('/v1/suites', {
        name: suiteData.name,
        description: suiteData.description,
        project_id: suiteData.project_id || suiteData.projectId,
        document_types: suiteData.document_types || suiteData.documentTypes || [],
        metadata: suiteData.metadata || {}
      });
      return {
        data: response.data
      };
    } catch (error) {
      console.error('Error creating suite:', error);
      throw error;
    }
  },

  // Update suite (real backend endpoint)
  updateSuite: async (suiteId, suiteData) => {
    try {
      const response = await apiClient.put(`/v1/suites/${suiteId}`, {
        name: suiteData.name,
        description: suiteData.description,
        status: suiteData.status,
        document_types: suiteData.document_types || suiteData.documentTypes,
        metadata: suiteData.metadata || {}
      });
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error updating suite ${suiteId}:`, error);
      throw error;
    }
  },

  // Delete suite (real backend endpoint)
  deleteSuite: async (suiteId) => {
    try {
      const response = await apiClient.delete(`/v1/suites/${suiteId}`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error deleting suite ${suiteId}:`, error);
      throw error;
    }
  },

  // Get suite tracking (real backend endpoint)
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
  }
};
