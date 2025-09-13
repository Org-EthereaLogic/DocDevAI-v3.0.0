import apiClient from './index';

export const reviewAPI = {
  // Get document quality review (real backend endpoint)
  getDocumentQuality: async (documentId) => {
    try {
      const response = await apiClient.get(`/v1/review/${documentId}/quality`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error fetching document quality for ${documentId}:`, error);
      throw error;
    }
  },

  // Get document review (real backend endpoint)
  getDocumentReview: async (documentId) => {
    try {
      const response = await apiClient.get(`/v1/review/${documentId}/review`);
      return {
        data: response.data
      };
    } catch (error) {
      console.error(`Error fetching document review for ${documentId}:`, error);
      throw error;
    }
  },

  // Legacy methods for backward compatibility
  getReviews: async () => {
    console.warn('reviewAPI.getReviews() is deprecated - use specific document review methods');
    return {
      data: {
        data: []
      }
    };
  },

  getReview: async (id) => {
    console.warn('reviewAPI.getReview() is deprecated - use getDocumentReview() instead');
    try {
      return await reviewAPI.getDocumentReview(id);
    } catch (error) {
      return {
        data: {
          id,
          document_id: id,
          score: 0,
          issues: [],
          created_at: new Date().toISOString()
        }
      };
    }
  }
};
