import apiClient, { buildQueryString, processPaginatedResponse } from './index';

// Input validation helpers
const validateEndpoint = (endpoint) => {
  if (!endpoint || typeof endpoint !== 'object') {
    throw new Error('Invalid endpoint structure');
  }

  if (!endpoint.path || !endpoint.method) {
    throw new Error('Endpoint must have path and method');
  }

  // Validate HTTP method
  const validMethods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'];
  if (!validMethods.includes(endpoint.method.toUpperCase())) {
    throw new Error(`Invalid HTTP method: ${endpoint.method}`);
  }

  return true;
};

const sanitizeInput = (input) => {
  if (typeof input !== 'string') return input;

  // Remove potential XSS vectors
  return input
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
    .replace(/javascript:/gi, '')
    .replace(/on\w+\s*=/gi, '');
};

const validateProjectName = (name) => {
  if (!name || typeof name !== 'string') {
    throw new Error('Project name is required and must be a string');
  }

  if (name.length < 2 || name.length > 100) {
    throw new Error('Project name must be between 2 and 100 characters');
  }

  return true;
};

export const documentAPI = {
  // Generate README document (real backend endpoint)
  generateReadme(data, options = {}) {
    // Validate and sanitize input
    try {
      validateProjectName(data.projectName || data.project_name);
    } catch (error) {
      return Promise.reject(error);
    }

    const sanitizedData = {
      project_name: sanitizeInput(data.projectName || data.project_name),
      description: sanitizeInput(data.description || ''),
      tech_stack: (data.techStack || data.tech_stack || []).map(sanitizeInput),
      features: (data.features || []).map(sanitizeInput),
      author: sanitizeInput(data.author || ''),
      installation_steps: (data.installationSteps || data.installation_steps || []).map(sanitizeInput)
    };

    if (options.onProgress) {
      return this.generateWithProgress('/v1/documents/readme', sanitizedData, options.onProgress);
    }

    return apiClient.post('/v1/documents/readme', sanitizedData)
      .then(response => response.data)
      .catch(error => {
        // Add context to error
        error.context = 'README generation';
        throw error;
      });
  },

  // Generate API Documentation (real backend endpoint)
  generateApiDoc(data, options = {}) {
    // Validate and sanitize input
    try {
      validateProjectName(data.projectName || data.project_name);

      // Validate endpoints
      const endpoints = data.endpoints || [];
      if (endpoints.length === 0) {
        throw new Error('At least one endpoint is required for API documentation');
      }

      endpoints.forEach(validateEndpoint);
    } catch (error) {
      return Promise.reject(error);
    }

    const sanitizedData = {
      project_name: sanitizeInput(data.projectName || data.project_name),
      api_base_url: sanitizeInput(data.apiBaseUrl || data.api_base_url || ''),
      endpoints: (data.endpoints || []).map(endpoint => ({
        ...endpoint,
        path: sanitizeInput(endpoint.path),
        method: sanitizeInput(endpoint.method),
        description: sanitizeInput(endpoint.description || '')
      })),
      authentication: sanitizeInput(data.authentication || ''),
      examples: (data.examples || []).map(sanitizeInput)
    };

    if (options.onProgress) {
      return this.generateWithProgress('/v1/documents/api-doc', sanitizedData, options.onProgress);
    }

    return apiClient.post('/v1/documents/api-doc', sanitizedData)
      .then(response => response.data)
      .catch(error => {
        // Add context to error
        error.context = 'API documentation generation';
        throw error;
      });
  },

  // Generate Changelog (real backend endpoint)
  generateChangelog(data, options = {}) {
    if (options.onProgress) {
      return this.generateWithProgress('/v1/documents/changelog', data, options.onProgress);
    }

    return apiClient.post('/v1/documents/changelog', {
      project_name: data.projectName || data.project_name,
      version: data.version,
      changes: data.changes || [],
      breaking_changes: data.breakingChanges || data.breaking_changes || [],
      deprecated: data.deprecated || []
    }).then(response => response.data);
  },

  // Generic generate method for backward compatibility
  generate(data, options = {}) {
    const documentType = data.documentType || data.document_type || 'readme';

    switch (documentType) {
      case 'readme':
        return this.generateReadme(data, options);
      case 'api-doc':
      case 'api_doc':
        return this.generateApiDoc(data, options);
      case 'changelog':
        return this.generateChangelog(data, options);
      default:
        return this.generateReadme(data, options);
    }
  },

  // Generate document with progress updates
  async generateWithProgress(endpoint, data, onProgress) {
    let progressInterval;
    let progressPercentage = 0;
    let statusMessage = 'Initializing AI generation...';

    // Start progress updates
    progressInterval = setInterval(() => {
      if (progressPercentage < 30) {
        progressPercentage += 5;
        statusMessage = 'Validating input data...';
      } else if (progressPercentage < 60) {
        progressPercentage += 3;
        statusMessage = 'AI is analyzing your requirements...';
      } else if (progressPercentage < 90) {
        progressPercentage += 2;
        statusMessage = 'Generating document content...';
      } else {
        progressPercentage = Math.min(95, progressPercentage + 1);
        statusMessage = 'Finalizing document...';
      }

      onProgress({
        percentage: progressPercentage,
        status: 'processing',
        message: statusMessage
      });
    }, 2000);

    try {
      // Create a custom timeout promise for long-running generation
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error('Document generation is taking longer than expected. Please try again.'));
        }, 120000); // 2 minutes timeout
      });

      // Race between the actual request and timeout
      const response = await Promise.race([
        apiClient.post(endpoint, data),
        timeoutPromise
      ]);

      clearInterval(progressInterval);
      onProgress({
        percentage: 100,
        status: 'completed',
        message: 'Document generated successfully!'
      });

      // Validate response structure
      if (!response.data) {
        throw new Error('Invalid response from server');
      }

      // Add metadata if not present
      if (!response.data.document) {
        response.data = {
          document: response.data,
          metadata: {
            generatedAt: new Date().toISOString(),
            type: data.type || 'readme'
          }
        };
      }

      return response.data;
    } catch (error) {
      clearInterval(progressInterval);

      // Enhanced error information
      const errorInfo = {
        percentage: 0,
        status: 'error',
        message: 'Generation failed',
        details: {}
      };

      if (error.response) {
        // Server responded with error
        errorInfo.message = error.response.data?.error || error.response.data?.message || 'Server error occurred';
        errorInfo.details = {
          status: error.response.status,
          statusText: error.response.statusText,
          data: error.response.data
        };

        // Handle specific error codes
        if (error.response.status === 401) {
          errorInfo.message = 'Authentication failed. Please check your API key.';
        } else if (error.response.status === 429) {
          errorInfo.message = 'Rate limit exceeded. Please wait before trying again.';
        } else if (error.response.status === 500) {
          errorInfo.message = 'Server error. The AI service may be temporarily unavailable.';
        }
      } else if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        errorInfo.message = 'Request timeout. Generation is taking longer than expected.';
        errorInfo.details.timeout = true;
      } else if (!error.response) {
        errorInfo.message = 'Network error. Please check your internet connection.';
        errorInfo.details.network = true;
      } else {
        errorInfo.message = error.message || 'An unexpected error occurred';
      }

      onProgress(errorInfo);
      throw error;
    }
  },

  // Get available templates (real backend endpoint)
  getTemplates() {
    return apiClient.get('/v1/documents/templates')
      .then(response => response.data);
  },

  // Validate document content (real backend endpoint)
  validate(content, documentType = 'readme') {
    return apiClient.post('/v1/documents/validate', {
      content,
      document_type: documentType
    }).then(response => response.data);
  },

  // Review document quality (real backend endpoint)
  reviewQuality(documentId) {
    return apiClient.get(`/v1/review/${documentId}/quality`)
      .then(response => response.data);
  },

  // Get document review (real backend endpoint)
  getReview(documentId) {
    return apiClient.get(`/v1/review/${documentId}/review`)
      .then(response => response.data);
  },

  // Check API health (real backend endpoint)
  healthCheck() {
    return apiClient.get('/v1/health')
      .then(response => response.data)
      .catch(() => ({ status: 'error' }));
  },

  // Get API readiness (real backend endpoint)
  readyCheck() {
    return apiClient.get('/v1/ready')
      .then(response => response.data)
      .catch(() => ({ status: 'error' }));
  },

  // Legacy methods for backward compatibility
  update(documentId, data) {
    console.warn('documentAPI.update() is deprecated - no backend endpoint available');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  delete(documentId) {
    console.warn('documentAPI.delete() is deprecated - no backend endpoint available');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  enhance(documentId, options = {}) {
    console.warn('documentAPI.enhance() is deprecated - use enhancement pipeline instead');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  export(documentId, format = 'markdown') {
    console.warn('documentAPI.export() is deprecated - no backend endpoint available');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  getDependencies(documentId) {
    console.warn('documentAPI.getDependencies() is deprecated - use suite tracking instead');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  getHealth(documentId) {
    console.warn('documentAPI.getHealth() is deprecated - use project health instead');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  getHistory(documentId) {
    console.warn('documentAPI.getHistory() is deprecated - no backend endpoint available');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  revert(documentId, versionId) {
    console.warn('documentAPI.revert() is deprecated - no backend endpoint available');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  estimateCost(data) {
    console.warn('documentAPI.estimateCost() is deprecated - costs are shown during generation');
    return Promise.resolve({ cost: 0, currency: 'USD', estimated: true });
  },

  getStats(params = {}) {
    console.warn('documentAPI.getStats() is deprecated - use dashboard stats instead');
    return Promise.resolve({ documents: 0, generated_today: 0 });
  },

  search(query, params = {}) {
    console.warn('documentAPI.search() is deprecated - no backend endpoint available');
    return Promise.resolve({ data: [], pagination: { total: 0 } });
  },

  batchUpdate(documentIds, updates) {
    console.warn('documentAPI.batchUpdate() is deprecated - no backend endpoint available');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  batchDelete(documentIds) {
    console.warn('documentAPI.batchDelete() is deprecated - no backend endpoint available');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  },

  batchReview(documentIds) {
    console.warn('documentAPI.batchReview() is deprecated - no backend endpoint available');
    return Promise.resolve({ success: false, error: 'Method not implemented' });
  }
};
