import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 120000, // 2 minutes timeout for AI generation
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // You can add auth tokens here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response) {
      // Server responded with error status
      const errorMessage = error.response.data?.error || error.response.data?.detail || 'Server error';
      console.error('API Error:', errorMessage);
      return Promise.reject(new Error(errorMessage));
    } else if (error.request) {
      // Request was made but no response
      console.error('Network Error:', error.message);
      return Promise.reject(new Error('Network error - please check your connection'));
    } else {
      // Something else happened
      console.error('Error:', error.message);
      return Promise.reject(error);
    }
  }
);

// API endpoints
export const documentAPI = {
  // Generate README document
  generateReadme: async (data) => {
    try {
      const response = await api.post('/api/v1/documents/readme', data);
      return response;
    } catch (error) {
      console.error('Generate README error:', error);
      throw error;
    }
  },

  // Get available templates
  getTemplates: async () => {
    try {
      const response = await api.get('/api/v1/documents/templates');
      return response;
    } catch (error) {
      console.error('Get templates error:', error);
      throw error;
    }
  },

  // Validate document
  validateDocument: async (content, documentType = 'readme') => {
    try {
      const response = await api.post('/api/v1/documents/validate', {
        content,
        document_type: documentType,
      });
      return response;
    } catch (error) {
      console.error('Validate document error:', error);
      throw error;
    }
  },

  // Health check
  healthCheck: async () => {
    try {
      const response = await api.get('/api/v1/health');
      return response;
    } catch (error) {
      console.error('Health check error:', error);
      throw error;
    }
  },

  // API info
  getApiInfo: async () => {
    try {
      const response = await api.get('/api/v1/info');
      return response;
    } catch (error) {
      console.error('Get API info error:', error);
      throw error;
    }
  },
};

export default api;
