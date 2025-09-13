import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { documentAPI } from '@/services/api/document';
import { useNotificationStore } from './notification';

export const useDocumentStore = defineStore('document', () => {
  // State
  const documents = ref([]);
  const currentDocument = ref(null);
  const isLoading = ref(false);
  const error = ref(null);
  const generationProgress = ref(0);
  const generationStatus = ref(null);
  const recentDocuments = ref([]);
  const documentStats = ref({
    total: 0,
    byType: {},
    avgHealthScore: 0,
    lastGenerated: null
  });

  // Generation options
  const generationOptions = ref({
    useAI: true,
    aiProvider: 'openai',
    enhancementLevel: 'standard',
    includeExamples: true,
    targetAudience: 'developers',
    language: 'en'
  });

  // Computed
  const documentsByType = computed(() => {
    const grouped = {};
    documents.value.forEach(doc => {
      if (!grouped[doc.type]) {
        grouped[doc.type] = [];
      }
      grouped[doc.type].push(doc);
    });
    return grouped;
  });

  const healthyDocuments = computed(() =>
    documents.value.filter(doc => doc.healthScore >= 85)
  );

  const needsReviewDocuments = computed(() =>
    documents.value.filter(doc => doc.healthScore < 70)
  );

  const averageHealthScore = computed(() => {
    if (documents.value.length === 0) return 0;
    const sum = documents.value.reduce((acc, doc) => acc + (doc.healthScore || 0), 0);
    return Math.round(sum / documents.value.length);
  });

  // Actions
  const fetchDocuments = async (projectId = null) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await documentAPI.list({ projectId });
      documents.value = response.documents || [];
      documentStats.value = response.stats || {
        total: 0,
        byType: {},
        avgHealthScore: 0,
        lastGenerated: null
      };
      return response;
    } catch (err) {
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch documents';
      error.value = errorMessage;

      const notificationStore = useNotificationStore();

      // Handle specific error scenarios
      if (err.code === 'ECONNABORTED') {
        notificationStore.addError('Request Timeout', 'The request took too long. Please try again.');
      } else if (!err.response) {
        notificationStore.addError('Network Error', 'Unable to connect to the server. Please check your connection.');
      } else {
        notificationStore.addError('Failed to fetch documents', errorMessage);
      }

      // Return empty data structure to prevent UI errors
      return {
        documents: [],
        stats: {
          total: 0,
          byType: {},
          avgHealthScore: 0,
          lastGenerated: null
        }
      };
    } finally {
      isLoading.value = false;
    }
  };

  const generateDocument = async (type, formData) => {
    isLoading.value = true;
    error.value = null;
    generationProgress.value = 0;
    generationStatus.value = 'initializing';

    const notificationStore = useNotificationStore();

    // Validate required fields
    const validationError = validateDocumentData(type, formData);
    if (validationError) {
      error.value = validationError;
      notificationStore.addError('Validation Error', validationError);
      isLoading.value = false;
      generationStatus.value = 'error';
      return Promise.reject(new Error(validationError));
    }

    let retryCount = 0;
    const maxRetries = 2;

    const attemptGeneration = async () => {
      try {
        // Combine form data with generation options
        const payload = {
          ...formData,
          document_type: type,  // Changed from 'type' to 'document_type' to match API
          options: generationOptions.value
        };

        // Start generation with progress tracking
        const response = await documentAPI.generate(payload, {
          onProgress: (progress) => {
            generationProgress.value = progress.percentage;
            generationStatus.value = progress.status;
          }
        });

        // Validate response structure
        if (!response || !response.document) {
          throw new Error('Invalid response from server: Missing document data');
        }

        currentDocument.value = response.document;

        // Add to documents list
        documents.value.unshift(response.document);

        // Update recent documents
        recentDocuments.value.unshift(response.document);
        if (recentDocuments.value.length > 5) {
          recentDocuments.value = recentDocuments.value.slice(0, 5);
        }

        // Update stats
        documentStats.value.total++;
        documentStats.value.lastGenerated = new Date().toISOString();

        notificationStore.addSuccess(
          'Document Generated',
          `Your ${type} document has been generated successfully!`
        );

        return response;
      } catch (err) {
        const errorMessage = err.response?.data?.message || err.message || 'Generation failed';

        // Handle timeout specifically (generation takes 47+ seconds)
        if (err.code === 'ECONNABORTED' || err.message.includes('timeout')) {
          if (retryCount < maxRetries) {
            retryCount++;
            notificationStore.addWarning(
              'Generation Taking Longer',
              `The AI is still working on your document. Attempt ${retryCount + 1}/${maxRetries + 1}...`
            );
            generationStatus.value = 'retrying';
            return attemptGeneration();
          } else {
            error.value = 'Document generation is taking longer than expected. The AI might be processing a complex request.';
            generationStatus.value = 'timeout';
            notificationStore.addError(
              'Generation Timeout',
              'The document generation is taking too long. Please try simplifying your request or try again later.'
            );
          }
        }
        // Handle API key issues
        else if (err.response?.status === 401 || errorMessage.includes('API key')) {
          error.value = 'API key issue detected. Please check your configuration.';
          generationStatus.value = 'auth_error';
          notificationStore.addError(
            'Authentication Error',
            'There was an issue with the API key. Please verify your configuration in settings.'
          );
        }
        // Handle rate limiting
        else if (err.response?.status === 429) {
          error.value = 'Rate limit exceeded. Please wait before generating more documents.';
          generationStatus.value = 'rate_limited';
          const retryAfter = err.response?.headers?.['retry-after'] || '60';
          notificationStore.addError(
            'Rate Limited',
            `Too many requests. Please wait ${retryAfter} seconds before trying again.`
          );
        }
        // Handle network errors
        else if (!err.response) {
          error.value = 'Network error. Please check your connection.';
          generationStatus.value = 'network_error';
          notificationStore.addError(
            'Network Error',
            'Unable to connect to the server. Please check your internet connection.'
          );
        }
        // Generic error
        else {
          error.value = errorMessage;
          generationStatus.value = 'error';
          notificationStore.addError('Generation Failed', errorMessage);
        }

        throw err;
      }
    };

    try {
      return await attemptGeneration();
    } finally {
      isLoading.value = false;
      generationProgress.value = 0;
      // Keep error status if there was an error
      if (generationStatus.value !== 'error' &&
          generationStatus.value !== 'timeout' &&
          generationStatus.value !== 'auth_error' &&
          generationStatus.value !== 'rate_limited' &&
          generationStatus.value !== 'network_error') {
        generationStatus.value = null;
      }
    }
  };

  const updateDocument = async (documentId, updates) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await documentAPI.update(documentId, updates);

      // Update in documents list
      const index = documents.value.findIndex(d => d.id === documentId);
      if (index !== -1) {
        documents.value[index] = response.document;
      }

      // Update current if it's the same document
      if (currentDocument.value?.id === documentId) {
        currentDocument.value = response.document;
      }

      const notificationStore = useNotificationStore();
      notificationStore.addSuccess('Document Updated', 'Changes saved successfully');

      return response;
    } catch (err) {
      error.value = err.message;
      const notificationStore = useNotificationStore();
      notificationStore.addError('Update Failed', err.message);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const deleteDocument = async (documentId) => {
    try {
      await documentAPI.delete(documentId);

      // Remove from documents list
      documents.value = documents.value.filter(d => d.id !== documentId);

      // Clear current if it's the deleted document
      if (currentDocument.value?.id === documentId) {
        currentDocument.value = null;
      }

      const notificationStore = useNotificationStore();
      notificationStore.addSuccess('Document Deleted', 'Document removed successfully');

      return true;
    } catch (err) {
      error.value = err.message;
      const notificationStore = useNotificationStore();
      notificationStore.addError('Delete Failed', err.message);
      throw err;
    }
  };

  const reviewDocument = async (documentId) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await documentAPI.review(documentId);

      // Update document with review results
      const index = documents.value.findIndex(d => d.id === documentId);
      if (index !== -1) {
        documents.value[index] = {
          ...documents.value[index],
          ...response.document,
          lastReviewed: new Date().toISOString()
        };
      }

      return response;
    } catch (err) {
      error.value = err.message;
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const enhanceDocument = async (documentId, enhancementOptions = {}) => {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await documentAPI.enhance(documentId, enhancementOptions);

      // Update document with enhanced content
      const index = documents.value.findIndex(d => d.id === documentId);
      if (index !== -1) {
        documents.value[index] = response.document;
      }

      if (currentDocument.value?.id === documentId) {
        currentDocument.value = response.document;
      }

      const notificationStore = useNotificationStore();
      notificationStore.addSuccess('Document Enhanced', 'AI enhancement completed successfully');

      return response;
    } catch (err) {
      error.value = err.message;
      const notificationStore = useNotificationStore();
      notificationStore.addError('Enhancement Failed', err.message);
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const exportDocument = async (documentId, format = 'markdown') => {
    try {
      const response = await documentAPI.export(documentId, format);
      return response;
    } catch (err) {
      error.value = err.message;
      const notificationStore = useNotificationStore();
      notificationStore.addError('Export Failed', err.message);
      throw err;
    }
  };

  const setCurrentDocument = (document) => {
    currentDocument.value = document;
  };

  const clearError = () => {
    error.value = null;
  };

  const updateGenerationOptions = (options) => {
    generationOptions.value = {
      ...generationOptions.value,
      ...options
    };
  };

  // Validation helper function
  const validateDocumentData = (type, formData) => {
    // Common required fields
    if (!formData.projectName && !formData.project_name) {
      return 'Project name is required';
    }

    // Type-specific validation
    switch (type) {
      case 'readme':
        if (!formData.description) {
          return 'Project description is required for README generation';
        }
        break;
      case 'api-doc':
      case 'api_doc':
        if (!formData.apiBaseUrl && !formData.api_base_url) {
          return 'API base URL is required for API documentation';
        }
        if ((!formData.endpoints || formData.endpoints.length === 0)) {
          return 'At least one endpoint is required for API documentation';
        }
        break;
      case 'changelog':
        if (!formData.version) {
          return 'Version number is required for changelog generation';
        }
        if ((!formData.changes || formData.changes.length === 0)) {
          return 'At least one change entry is required for changelog generation';
        }
        break;
    }

    return null; // No validation errors
  };

  // Retry helper for failed operations
  const retryOperation = async (operation, operationName, maxRetries = 2) => {
    let lastError;
    const notificationStore = useNotificationStore();

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (err) {
        lastError = err;

        if (attempt < maxRetries) {
          notificationStore.addInfo(
            'Retrying Operation',
            `Retrying ${operationName}... (Attempt ${attempt + 2}/${maxRetries + 1})`
          );
          // Wait before retrying (exponential backoff)
          await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
        }
      }
    }

    throw lastError;
  };

  // Check if the store has any errors
  const hasError = computed(() => !!error.value);

  // Get human-readable error message
  const errorMessage = computed(() => {
    if (!error.value) return null;

    // Format error message for display
    if (typeof error.value === 'string') {
      return error.value;
    }

    return error.value.message || 'An unexpected error occurred';
  });

  // Reset store
  const $reset = () => {
    documents.value = [];
    currentDocument.value = null;
    isLoading.value = false;
    error.value = null;
    generationProgress.value = 0;
    generationStatus.value = null;
    recentDocuments.value = [];
    documentStats.value = {
      total: 0,
      byType: {},
      avgHealthScore: 0,
      lastGenerated: null
    };
  };

  return {
    // State
    documents,
    currentDocument,
    isLoading,
    error,
    generationProgress,
    generationStatus,
    recentDocuments,
    documentStats,
    generationOptions,

    // Computed
    documentsByType,
    healthyDocuments,
    needsReviewDocuments,
    averageHealthScore,

    // Actions
    fetchDocuments,
    generateDocument,
    updateDocument,
    deleteDocument,
    reviewDocument,
    enhanceDocument,
    exportDocument,
    setCurrentDocument,
    clearError,
    updateGenerationOptions,
    validateDocumentData,
    retryOperation,
    $reset,

    // Additional computed
    hasError,
    errorMessage
  };
});
