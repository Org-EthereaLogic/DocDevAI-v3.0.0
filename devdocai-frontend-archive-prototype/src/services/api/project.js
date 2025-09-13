import apiClient, { buildQueryString } from './index';

export const projectAPI = {
  // Get all projects (real backend endpoint)
  getProjects: async (params = {}) => {
    try {
      const queryString = buildQueryString({
        limit: params.limit || 100,
        offset: params.offset || 0
      });

      const response = await apiClient.get(`/v1/projects${queryString}`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error('Error fetching projects:', error);
      throw error;
    }
  },

  // Get project health (real backend endpoint)
  getProjectHealth: async (projectId) => {
    try {
      const response = await apiClient.get(`/v1/projects/${projectId}/health`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error fetching project health for ${projectId}:`, error);
      throw error;
    }
  },

  // Get dashboard statistics (real backend endpoint)
  getDashboardStats: async (days = 30) => {
    try {
      const response = await apiClient.get(`/v1/dashboard/stats`, {
        params: { days }
      });
      return {
        data: response.data
      };
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      throw error;
    }
  },

  // Legacy method for backward compatibility
  getProject: async (id) => {
    console.warn('projectAPI.getProject() is deprecated - use getProjectHealth() instead');
    try {
      return await projectAPI.getProjectHealth(id);
    } catch (error) {
      return {
        data: {
          project_id: id,
          name: id.replace('_', ' ').replace('-', ' '),
          health_score: 0,
          status: 'unknown',
          document_count: 0
        }
      };
    }
  }
};
