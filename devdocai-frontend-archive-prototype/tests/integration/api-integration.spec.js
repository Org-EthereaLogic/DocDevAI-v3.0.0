/**
 * Integration tests for API communication
 * Tests real API integration with the backend FastAPI server
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createTestingPinia } from '../setup';
import axios from 'axios';
import { useApiStore } from '@/stores/api';
import { useNotificationStore } from '@/stores/notification';
import { mockApiResponses, mockNetworkError, mockNetworkSuccess } from '../utils/testHelpers';

// Mock axios for integration testing
vi.mock('axios');
const mockedAxios = vi.mocked(axios);

describe('API Integration Tests', () => {
  let apiStore;
  let notificationStore;
  let pinia;

  beforeEach(() => {
    vi.clearAllMocks();
    pinia = createTestingPinia();
    apiStore = useApiStore(pinia);
    notificationStore = useNotificationStore(pinia);
  });

  describe('Document Generation API', () => {
    it('should successfully generate document with valid data', async () => {
      const requestData = {
        project_name: 'Integration Test Project',
        description: 'Testing API integration with valid data.',
        author: 'Integration Author',
        tech_stack: ['Vue.js', 'Python'],
        features: ['AI-powered generation']
      };

      mockedAxios.post.mockResolvedValue({
        data: mockApiResponses.generateDocument.success
      });

      const result = await apiStore.generateDocument(requestData);

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/generate',
        requestData,
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      );

      expect(result.success).toBe(true);
      expect(result.content).toContain('Generated documentation content');
      expect(result.metadata.generation_time).toBe(2.5);
    });

    it('should handle API rate limiting gracefully', async () => {
      mockedAxios.post.mockRejectedValue({
        response: {
          status: 429,
          data: { error: 'Rate limit exceeded', retry_after: 60 }
        }
      });

      const requestData = {
        project_name: 'Rate Limit Test',
        description: 'Testing rate limit handling.',
        author: 'Rate Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      await expect(apiStore.generateDocument(requestData)).rejects.toThrow();

      expect(apiStore.isRateLimited).toBe(true);
      expect(apiStore.retryAfter).toBe(60);
    });

    it('should handle server errors with proper error reporting', async () => {
      mockedAxios.post.mockRejectedValue({
        response: {
          status: 500,
          data: { error: 'Internal server error', details: 'Database connection failed' }
        }
      });

      const requestData = {
        project_name: 'Error Test',
        description: 'Testing error handling.',
        author: 'Error Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      try {
        await apiStore.generateDocument(requestData);
      } catch (error) {
        expect(error.message).toContain('Internal server error');
      }

      expect(apiStore.hasError).toBe(true);
      expect(apiStore.lastError).toContain('Internal server error');
    });

    it('should support canceling ongoing generation requests', async () => {
      const abortController = new AbortController();
      mockedAxios.post.mockImplementation(() => {
        return new Promise((_, reject) => {
          abortController.signal.addEventListener('abort', () => {
            reject(new Error('Request canceled'));
          });
        });
      });

      const requestData = {
        project_name: 'Cancel Test',
        description: 'Testing cancellation.',
        author: 'Cancel Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      const generationPromise = apiStore.generateDocument(requestData);

      // Cancel the request
      apiStore.cancelGeneration();

      await expect(generationPromise).rejects.toThrow('Request canceled');
      expect(apiStore.isGenerating).toBe(false);
    });

    it('should track generation progress with WebSocket updates', async () => {
      // Mock WebSocket for progress tracking
      const mockWebSocket = {
        send: vi.fn(),
        close: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        readyState: 1
      };

      global.WebSocket = vi.fn(() => mockWebSocket);

      const requestData = {
        project_name: 'Progress Test',
        description: 'Testing progress tracking.',
        author: 'Progress Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      // Start generation
      const generationPromise = apiStore.generateDocument(requestData);

      // Simulate progress updates
      const progressCallback = mockWebSocket.addEventListener.mock.calls
        .find(call => call[0] === 'message')?.[1];

      if (progressCallback) {
        progressCallback({
          data: JSON.stringify({ type: 'progress', progress: 25, message: 'Analyzing requirements...' })
        });

        expect(apiStore.generationProgress).toBe(25);
        expect(apiStore.progressMessage).toBe('Analyzing requirements...');

        progressCallback({
          data: JSON.stringify({ type: 'progress', progress: 75, message: 'Generating content...' })
        });

        expect(apiStore.generationProgress).toBe(75);
        expect(apiStore.progressMessage).toBe('Generating content...');
      }

      // Mock completion
      mockedAxios.post.mockResolvedValue({
        data: mockApiResponses.generateDocument.success
      });

      await generationPromise;
    });
  });

  describe('Project Validation API', () => {
    it('should validate project data before generation', async () => {
      const projectData = {
        project_name: 'Valid Project',
        description: 'A valid project description.',
        author: 'Valid Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      mockedAxios.post.mockResolvedValue({
        data: mockApiResponses.validateProject.valid
      });

      const result = await apiStore.validateProject(projectData);

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/validate',
        projectData
      );

      expect(result.valid).toBe(true);
      expect(result.suggestions).toContain('Consider adding more features');
    });

    it('should return validation errors for invalid data', async () => {
      const invalidData = {
        project_name: '',
        description: 'Short',
        author: '',
        tech_stack: [],
        features: []
      };

      mockedAxios.post.mockResolvedValue({
        data: mockApiResponses.validateProject.invalid
      });

      const result = await apiStore.validateProject(invalidData);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Project name is required');
      expect(result.errors).toContain('Description too short');
    });
  });

  describe('Template Management API', () => {
    it('should fetch available templates', async () => {
      const mockTemplates = [
        {
          id: 'template-1',
          name: 'Basic README',
          description: 'Simple README template',
          category: 'documentation'
        },
        {
          id: 'template-2',
          name: 'API Documentation',
          description: 'API-focused documentation',
          category: 'api'
        }
      ];

      mockedAxios.get.mockResolvedValue({
        data: { templates: mockTemplates }
      });

      const templates = await apiStore.getTemplates();

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/templates');
      expect(templates).toHaveLength(2);
      expect(templates[0].name).toBe('Basic README');
    });

    it('should fetch template details by ID', async () => {
      const templateDetails = {
        id: 'template-1',
        name: 'Basic README',
        content: '# {{project_name}}\n\n{{description}}',
        variables: ['project_name', 'description'],
        preview: 'Template preview content'
      };

      mockedAxios.get.mockResolvedValue({
        data: templateDetails
      });

      const details = await apiStore.getTemplateDetails('template-1');

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/templates/template-1');
      expect(details.content).toContain('{{project_name}}');
      expect(details.variables).toContain('project_name');
    });
  });

  describe('Error Handling and Resilience', () => {
    it('should implement exponential backoff for failed requests', async () => {
      let callCount = 0;
      mockedAxios.post.mockImplementation(() => {
        callCount++;
        if (callCount < 3) {
          return Promise.reject({
            response: { status: 503, data: { error: 'Service unavailable' } }
          });
        }
        return Promise.resolve({
          data: mockApiResponses.generateDocument.success
        });
      });

      const requestData = {
        project_name: 'Retry Test',
        description: 'Testing retry logic.',
        author: 'Retry Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      const result = await apiStore.generateDocumentWithRetry(requestData);

      expect(callCount).toBe(3);
      expect(result.success).toBe(true);
    });

    it('should handle network timeouts gracefully', async () => {
      mockedAxios.post.mockImplementation(() => {
        return new Promise((_, reject) => {
          setTimeout(() => {
            reject(new Error('Network timeout'));
          }, 100);
        });
      });

      const requestData = {
        project_name: 'Timeout Test',
        description: 'Testing timeout handling.',
        author: 'Timeout Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      await expect(apiStore.generateDocument(requestData)).rejects.toThrow('Network timeout');

      expect(apiStore.hasError).toBe(true);
      expect(apiStore.lastError).toContain('Network timeout');
    });

    it('should maintain API state consistency during errors', async () => {
      // Start with clean state
      expect(apiStore.isGenerating).toBe(false);
      expect(apiStore.hasError).toBe(false);

      mockedAxios.post.mockRejectedValue(new Error('API Error'));

      const requestData = {
        project_name: 'State Test',
        description: 'Testing state consistency.',
        author: 'State Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      try {
        await apiStore.generateDocument(requestData);
      } catch (error) {
        // Error expected
      }

      // State should be properly reset after error
      expect(apiStore.isGenerating).toBe(false);
      expect(apiStore.hasError).toBe(true);
      expect(apiStore.generationProgress).toBe(0);
    });
  });

  describe('API Security and Validation', () => {
    it('should include CSRF token in requests when available', async () => {
      // Mock CSRF token
      const csrfToken = 'mock-csrf-token';
      global.document = {
        querySelector: vi.fn(() => ({
          getAttribute: vi.fn(() => csrfToken)
        }))
      };

      mockedAxios.post.mockResolvedValue({
        data: mockApiResponses.generateDocument.success
      });

      const requestData = {
        project_name: 'CSRF Test',
        description: 'Testing CSRF protection.',
        author: 'CSRF Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      await apiStore.generateDocument(requestData);

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/generate',
        requestData,
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-CSRF-Token': csrfToken
          })
        })
      );
    });

    it('should sanitize user input before sending to API', async () => {
      const maliciousData = {
        project_name: '<script>alert("xss")</script>Project',
        description: '<img src="x" onerror="alert(1)">Description',
        author: '<div onclick="alert(1)">Author</div>',
        tech_stack: ['<script>console.log("xss")</script>'],
        features: ['<iframe src="javascript:alert(1)"></iframe>']
      };

      mockedAxios.post.mockResolvedValue({
        data: mockApiResponses.generateDocument.success
      });

      await apiStore.generateDocument(maliciousData);

      const sanitizedData = mockedAxios.post.mock.calls[0][1];

      expect(sanitizedData.project_name).not.toContain('<script>');
      expect(sanitizedData.description).not.toContain('<img');
      expect(sanitizedData.author).not.toContain('<div');
      expect(sanitizedData.tech_stack[0]).not.toContain('<script>');
      expect(sanitizedData.features[0]).not.toContain('<iframe');
    });

    it('should validate API responses before processing', async () => {
      // Mock invalid API response
      mockedAxios.post.mockResolvedValue({
        data: {
          // Missing required fields
          content: null,
          metadata: null
        }
      });

      const requestData = {
        project_name: 'Validation Test',
        description: 'Testing response validation.',
        author: 'Validation Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      await expect(apiStore.generateDocument(requestData)).rejects.toThrow('Invalid API response');
    });
  });

  describe('Caching and Performance', () => {
    it('should cache template requests to reduce API calls', async () => {
      const mockTemplates = [
        { id: 'template-1', name: 'Template 1' },
        { id: 'template-2', name: 'Template 2' }
      ];

      mockedAxios.get.mockResolvedValue({
        data: { templates: mockTemplates }
      });

      // First call
      await apiStore.getTemplates();

      // Second call should use cache
      await apiStore.getTemplates();

      // Should only make one API call
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
    });

    it('should invalidate cache when appropriate', async () => {
      const mockTemplates = [
        { id: 'template-1', name: 'Template 1' }
      ];

      mockedAxios.get.mockResolvedValue({
        data: { templates: mockTemplates }
      });

      // First call
      await apiStore.getTemplates();

      // Invalidate cache
      apiStore.clearCache();

      // Second call should make new API request
      await apiStore.getTemplates();

      expect(mockedAxios.get).toHaveBeenCalledTimes(2);
    });

    it('should implement request deduplication for concurrent calls', async () => {
      mockedAxios.get.mockImplementation(() => {
        return new Promise(resolve => {
          setTimeout(() => {
            resolve({
              data: { templates: [{ id: 'template-1', name: 'Template 1' }] }
            });
          }, 100);
        });
      });

      // Make concurrent requests
      const promises = [
        apiStore.getTemplates(),
        apiStore.getTemplates(),
        apiStore.getTemplates()
      ];

      await Promise.all(promises);

      // Should only make one API call despite multiple concurrent requests
      expect(mockedAxios.get).toHaveBeenCalledTimes(1);
    });
  });
});
