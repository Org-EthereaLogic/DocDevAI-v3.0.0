import apiClient, { buildQueryString } from './index';

export const templateAPI = {
  // Get all templates with real backend call
  getTemplates: async (params = {}) => {
    try {
      const queryString = buildQueryString({
        category: params.category,
        language: params.language,
        search: params.search,
        sort_by: params.sort_by || 'downloads',
        limit: params.per_page || params.limit || 50,
        offset: ((params.page || 1) - 1) * (params.per_page || params.limit || 50)
      });

      const response = await apiClient.get(`/v1/templates${queryString}`);

      // Transform backend response to match frontend expectations
      return {
        data: {
          data: response.data.templates || [],
          pagination: {
            current_page: Math.floor((params.offset || 0) / (params.limit || 50)) + 1,
            total_pages: Math.ceil((response.data.total || 0) / (params.limit || 50)),
            per_page: params.limit || 50,
            total: response.data.total || 0
          },
          categories: response.data.categories || [],
          languages: response.data.languages || []
        }
      };
    } catch (error) {
      console.error('Error fetching templates:', error);
      throw error;
    }
  },

  // Get template by ID with real backend call
  getTemplate: async (id) => {
    try {
      const response = await apiClient.get(`/v1/templates/${id}`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error fetching template ${id}:`, error);
      throw error;
    }
  },

  // Download and install template
  downloadTemplate: async (templateId, install = true) => {
    try {
      const response = await apiClient.post(`/v1/templates/${templateId}/download`, null, {
        params: { install }
      });
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error downloading template ${templateId}:`, error);
      throw error;
    }
  },

  // Get template preview
  getTemplatePreview: async (templateId) => {
    try {
      const response = await apiClient.get(`/v1/templates/${templateId}/preview`, {
        responseType: 'text'
      });
      return response.data;
    } catch (error) {
      console.error(`Error getting template preview ${templateId}:`, error);
      throw error;
    }
  },

  // Uninstall template
  uninstallTemplate: async (templateId) => {
    try {
      const response = await apiClient.delete(`/v1/templates/${templateId}`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error uninstalling template ${templateId}:`, error);
      throw error;
    }
  },

  // Search templates (using getTemplates with search param)
  searchTemplates: async (query) => {
    return await templateAPI.getTemplates({ search: query });
  }
};
