// DevDocAI API Service Layer - FastAPI Backend Integration

import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import type {
  ApiResponse,
  ApiError,
  PaginationParams,
  PaginatedResponse
} from '@/types/api';

// API Configuration
const API_CONFIG = {
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
};

// Axios Instance
class ApiClient {
  private client: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.client = axios.create(API_CONFIG);
    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request Interceptor
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }

        // Add request metadata
        config.headers['X-Request-ID'] = this.generateRequestId();
        config.headers['X-Client-Version'] = '3.6.0';
        config.headers['X-Timestamp'] = new Date().toISOString();

        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response Interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => {
        // Handle successful responses
        if (response.data && !response.data.success) {
          throw new ApiClientError(
            response.data.error?.message || 'API request failed',
            response.data.error?.code || 'UNKNOWN_ERROR',
            response.status,
            response.data.error?.details
          );
        }
        return response;
      },
      (error) => {
        // Handle errors
        if (error.response) {
          const apiError = error.response.data?.error;
          throw new ApiClientError(
            apiError?.message || 'Request failed',
            apiError?.code || 'HTTP_ERROR',
            error.response.status,
            apiError?.details
          );
        }

        if (error.request) {
          throw new ApiClientError(
            'Network error - Unable to reach server',
            'NETWORK_ERROR',
            0
          );
        }

        throw new ApiClientError(
          error.message || 'Unknown error occurred',
          'UNKNOWN_ERROR',
          0
        );
      }
    );
  }

  private generateRequestId(): string {
    return Math.random().toString(36).substring(2) + Date.now().toString(36);
  }

  public setAuthToken(token: string): void {
    this.token = token;
  }

  public clearAuthToken(): void {
    this.token = null;
  }

  // HTTP Methods
  public async get<T = any>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.client.get<ApiResponse<T>>(url, config);
    return response.data;
  }

  public async post<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.client.post<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  public async put<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.client.put<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  public async patch<T = any>(
    url: string,
    data?: any,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.client.patch<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  public async delete<T = any>(
    url: string,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const response = await this.client.delete<ApiResponse<T>>(url, config);
    return response.data;
  }

  // Utility Methods
  public buildPaginationParams(params: PaginationParams): string {
    const searchParams = new URLSearchParams();

    searchParams.append('page', params.page.toString());
    searchParams.append('limit', params.limit.toString());

    if (params.sort_by) {
      searchParams.append('sort_by', params.sort_by);
    }

    if (params.sort_order) {
      searchParams.append('sort_order', params.sort_order);
    }

    return searchParams.toString();
  }

  public async downloadFile(url: string, filename?: string): Promise<void> {
    const response = await this.client.get(url, {
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');

    link.href = downloadUrl;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.URL.revokeObjectURL(downloadUrl);
  }

  public async uploadFile(
    url: string,
    file: File,
    onProgress?: (progressEvent: ProgressEvent) => void
  ): Promise<ApiResponse> {
    const formData = new FormData();
    formData.append('file', file);

    return this.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress,
    });
  }
}

// Custom Error Class
export class ApiClientError extends Error {
  public readonly code: string;
  public readonly status: number;
  public readonly details?: Record<string, any>;

  constructor(
    message: string,
    code: string,
    status: number,
    details?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApiClientError';
    this.code = code;
    this.status = status;
    this.details = details;
  }

  public isNetworkError(): boolean {
    return this.code === 'NETWORK_ERROR';
  }

  public isValidationError(): boolean {
    return this.status === 422 || this.code === 'VALIDATION_ERROR';
  }

  public isAuthError(): boolean {
    return this.status === 401 || this.status === 403;
  }

  public isServerError(): boolean {
    return this.status >= 500;
  }

  public isRetryable(): boolean {
    return this.isNetworkError() || this.isServerError();
  }
}

// Request/Response Logging (Development)
export const enableApiLogging = (enable: boolean = true): void => {
  if (enable && import.meta.env.DEV) {
    apiClient.client.interceptors.request.use((config) => {
      console.group(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`);
      console.log('Config:', config);
      console.groupEnd();
      return config;
    });

    apiClient.client.interceptors.response.use(
      (response) => {
        console.group(`✅ API Response: ${response.status} ${response.config.url}`);
        console.log('Data:', response.data);
        console.log('Headers:', response.headers);
        console.groupEnd();
        return response;
      },
      (error) => {
        console.group(`❌ API Error: ${error.config?.url}`);
        console.error('Error:', error);
        console.groupEnd();
        return Promise.reject(error);
      }
    );
  }
};

// Create and export singleton instance
export const apiClient = new ApiClient();

// Enable logging in development
if (import.meta.env.DEV) {
  enableApiLogging(true);
}

export default apiClient;