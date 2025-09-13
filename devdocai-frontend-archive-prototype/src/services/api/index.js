import axios from 'axios';
import { useAuthStore } from '@/stores/auth';
import { useNotificationStore } from '@/stores/notification';
import router from '@/router';

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  timeout: 60000, // 60 seconds for AI generation operations
  headers: {
    'Content-Type': 'application/json',
    'X-Client-Version': '3.6.0'
  }
});

// Request interceptor for authentication
apiClient.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore();

    // Add auth token if available
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`;
    }

    // Add request ID for tracking
    config.headers['X-Request-ID'] = generateRequestId();

    // Log request in development
    if (import.meta.env.DEV) {
      console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.data);
    }

    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    // Log response in development
    if (import.meta.env.DEV) {
      console.log(`[API] Response from ${response.config.url}:`, response.data);
    }

    return response;
  },
  async (error) => {
    const authStore = useAuthStore();
    const notificationStore = useNotificationStore();

    // Handle different error scenarios
    if (error.response) {
      const { status, data } = error.response;

      switch (status) {
        case 401:
          // Unauthorized - try to refresh token
          if (authStore.refreshToken && !error.config._retry) {
            error.config._retry = true;
            try {
              await authStore.refreshSession();
              // Retry original request with new token
              return apiClient(error.config);
            } catch (refreshError) {
              // Refresh failed, logout user
              await authStore.logout();
              router.push('/login');
              notificationStore.addError('Session Expired', 'Please login again');
            }
          } else {
            // No refresh token or refresh already failed
            await authStore.logout();
            router.push('/login');
          }
          break;

        case 403:
          // Forbidden
          notificationStore.addError('Access Denied', data.message || 'You do not have permission to perform this action');
          break;

        case 404:
          // Not found
          notificationStore.addError('Not Found', data.message || 'The requested resource was not found');
          break;

        case 422:
          // Validation error
          if (data.errors) {
            const errorMessages = Object.values(data.errors).flat().join(', ');
            notificationStore.addError('Validation Error', errorMessages);
          } else {
            notificationStore.addError('Validation Error', data.message || 'Please check your input');
          }
          break;

        case 429:
          // Rate limited
          notificationStore.addError('Rate Limited', 'Too many requests. Please wait a moment and try again');
          break;

        case 500:
        case 502:
        case 503:
          // Server error
          notificationStore.addError('Server Error', 'Something went wrong on our end. Please try again later');
          break;

        default:
          // Other errors
          notificationStore.addError('Error', data.message || `An error occurred (${status})`);
      }
    } else if (error.request) {
      // Request was made but no response received
      notificationStore.addError('Network Error', 'Unable to connect to the server. Please check your connection');
    } else {
      // Something else happened
      notificationStore.addError('Error', error.message || 'An unexpected error occurred');
    }

    // Log error in development
    if (import.meta.env.DEV) {
      console.error('[API] Error:', error);
    }

    return Promise.reject(error);
  }
);

// Helper function to generate request ID
function generateRequestId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// Helper for building query strings
export function buildQueryString(params) {
  const searchParams = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') {
      if (Array.isArray(value)) {
        value.forEach(v => searchParams.append(key, v));
      } else {
        searchParams.append(key, value);
      }
    }
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

// Helper for handling paginated responses
export function processPaginatedResponse(response) {
  return {
    data: response.data.data || response.data.items || response.data.results || [],
    pagination: {
      currentPage: response.data.current_page || response.data.page || 1,
      totalPages: response.data.total_pages || response.data.pages || 1,
      perPage: response.data.per_page || response.data.limit || 20,
      total: response.data.total || response.data.count || 0
    },
    meta: response.data.meta || {}
  };
}

// Helper for file uploads
export function createFormData(data) {
  const formData = new FormData();

  Object.entries(data).forEach(([key, value]) => {
    if (value instanceof File || value instanceof Blob) {
      formData.append(key, value);
    } else if (Array.isArray(value)) {
      value.forEach((item, index) => {
        if (item instanceof File || item instanceof Blob) {
          formData.append(`${key}[${index}]`, item);
        } else {
          formData.append(`${key}[${index}]`, JSON.stringify(item));
        }
      });
    } else if (value !== null && value !== undefined) {
      formData.append(key, typeof value === 'object' ? JSON.stringify(value) : value);
    }
  });

  return formData;
}

// Export configured axios instance
export default apiClient;

// Export specific API modules
export { documentAPI } from './document';
export { templateAPI } from './template';
export { projectAPI } from './project';
export { authAPI } from './auth';
export { settingsAPI } from './settings';
export { reviewAPI } from './review';
export { trackingAPI } from './tracking';
export { suiteAPI } from './suite';
