/**
 * M011 API Security Layer - CSRF protection, request validation, and rate limiting
 * 
 * Provides comprehensive API security including CSRF tokens, request validation,
 * rate limiting, and secure communication with backend services. Integrates with
 * auth-manager for token management.
 */

import { authManager } from './auth-manager';
import { securityUtils, SecurityEventType } from './security-utils';

/**
 * Request method types
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD' | 'OPTIONS';

/**
 * API security configuration
 */
export interface APISecurityConfig {
  baseURL: string;
  timeout: number;
  enableCSRF: boolean;
  enableRateLimiting: boolean;
  enableRequestValidation: boolean;
  enableResponseValidation: boolean;
  maxRetries: number;
  retryDelay: number;
  rateLimitWindow: number; // milliseconds
  rateLimitMaxRequests: number;
  allowedOrigins: string[];
  allowedMethods: HttpMethod[];
  securityHeaders: Record<string, string>;
}

/**
 * Default API security configuration
 */
const DEFAULT_API_CONFIG: APISecurityConfig = {
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  timeout: 30000,
  enableCSRF: true,
  enableRateLimiting: true,
  enableRequestValidation: true,
  enableResponseValidation: true,
  maxRetries: 3,
  retryDelay: 1000,
  rateLimitWindow: 60000, // 1 minute
  rateLimitMaxRequests: 100,
  allowedOrigins: ['http://localhost:3000', 'http://localhost:8000'],
  allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
  securityHeaders: {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
  }
};

/**
 * Request interceptor interface
 */
export interface RequestInterceptor {
  onRequest?: (config: RequestConfig) => Promise<RequestConfig>;
  onRequestError?: (error: any) => Promise<any>;
}

/**
 * Response interceptor interface
 */
export interface ResponseInterceptor {
  onResponse?: (response: any) => Promise<any>;
  onResponseError?: (error: any) => Promise<any>;
}

/**
 * Request configuration
 */
export interface RequestConfig {
  url: string;
  method: HttpMethod;
  headers?: Record<string, string>;
  params?: Record<string, any>;
  data?: any;
  timeout?: number;
  withCredentials?: boolean;
  validateStatus?: (status: number) => boolean;
  signal?: AbortSignal;
}

/**
 * Rate limiter implementation
 */
class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private config: APISecurityConfig;

  constructor(config: APISecurityConfig) {
    this.config = config;
    this.startCleanupTimer();
  }

  /**
   * Check if request is allowed
   */
  public isAllowed(endpoint: string, userId?: string): boolean {
    if (!this.config.enableRateLimiting) {
      return true;
    }

    const key = userId ? `${userId}:${endpoint}` : endpoint;
    const now = Date.now();
    const requests = this.requests.get(key) || [];
    
    // Remove old requests outside the window
    const validRequests = requests.filter(
      timestamp => now - timestamp < this.config.rateLimitWindow
    );
    
    if (validRequests.length >= this.config.rateLimitMaxRequests) {
      securityUtils['logSecurityEvent']({
        type: SecurityEventType.RATE_LIMIT_EXCEEDED,
        message: 'Rate limit exceeded',
        details: { endpoint, userId, requests: validRequests.length },
        severity: 'medium'
      });
      return false;
    }
    
    validRequests.push(now);
    this.requests.set(key, validRequests);
    return true;
  }

  /**
   * Get remaining requests
   */
  public getRemainingRequests(endpoint: string, userId?: string): number {
    const key = userId ? `${userId}:${endpoint}` : endpoint;
    const requests = this.requests.get(key) || [];
    const now = Date.now();
    
    const validRequests = requests.filter(
      timestamp => now - timestamp < this.config.rateLimitWindow
    );
    
    return Math.max(0, this.config.rateLimitMaxRequests - validRequests.length);
  }

  /**
   * Reset rate limit for endpoint
   */
  public reset(endpoint: string, userId?: string): void {
    const key = userId ? `${userId}:${endpoint}` : endpoint;
    this.requests.delete(key);
  }

  /**
   * Start cleanup timer
   */
  private startCleanupTimer(): void {
    setInterval(() => {
      const now = Date.now();
      
      this.requests.forEach((timestamps, key) => {
        const validRequests = timestamps.filter(
          timestamp => now - timestamp < this.config.rateLimitWindow
        );
        
        if (validRequests.length === 0) {
          this.requests.delete(key);
        } else {
          this.requests.set(key, validRequests);
        }
      });
    }, this.config.rateLimitWindow);
  }
}

/**
 * CSRF token manager
 */
class CSRFTokenManager {
  private token: string | null = null;
  private tokenExpiry: number = 0;
  private readonly TOKEN_LIFETIME = 3600000; // 1 hour

  /**
   * Get CSRF token
   */
  public async getToken(): Promise<string> {
    if (!this.token || Date.now() >= this.tokenExpiry) {
      await this.refreshToken();
    }
    return this.token!;
  }

  /**
   * Refresh CSRF token
   */
  private async refreshToken(): Promise<void> {
    // In production, fetch from backend
    // For now, generate locally
    this.token = securityUtils.generateToken(32);
    this.tokenExpiry = Date.now() + this.TOKEN_LIFETIME;
    
    // Store in cookie for double-submit pattern
    document.cookie = `csrf_token=${this.token}; SameSite=Strict; Secure`;
  }

  /**
   * Validate CSRF token
   */
  public validateToken(token: string): boolean {
    return this.token === token && Date.now() < this.tokenExpiry;
  }

  /**
   * Clear token
   */
  public clearToken(): void {
    this.token = null;
    this.tokenExpiry = 0;
    document.cookie = 'csrf_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; SameSite=Strict; Secure';
  }
}

/**
 * API Security class
 */
export class APISecurity {
  private static instance: APISecurity;
  private config: APISecurityConfig;
  private rateLimiter: RateLimiter;
  private csrfManager: CSRFTokenManager;
  private requestInterceptors: RequestInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor[] = [];
  private pendingRequests: Map<string, AbortController> = new Map();

  private constructor(config?: Partial<APISecurityConfig>) {
    this.config = { ...DEFAULT_API_CONFIG, ...config };
    this.rateLimiter = new RateLimiter(this.config);
    this.csrfManager = new CSRFTokenManager();
    this.setupDefaultInterceptors();
  }

  /**
   * Get singleton instance
   */
  public static getInstance(config?: Partial<APISecurityConfig>): APISecurity {
    if (!APISecurity.instance) {
      APISecurity.instance = new APISecurity(config);
    }
    return APISecurity.instance;
  }

  /**
   * Setup default interceptors
   */
  private setupDefaultInterceptors(): void {
    // Request interceptor for auth and CSRF
    this.addRequestInterceptor({
      onRequest: async (config) => {
        // Add auth header
        const authHeader = authManager.getAuthHeader();
        config.headers = { ...config.headers, ...authHeader };
        
        // Add CSRF token for state-changing methods
        if (this.config.enableCSRF && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(config.method)) {
          const csrfToken = await this.csrfManager.getToken();
          config.headers = {
            ...config.headers,
            'X-CSRF-Token': csrfToken
          };
        }
        
        // Add security headers
        config.headers = {
          ...config.headers,
          ...this.config.securityHeaders
        };
        
        return config;
      }
    });

    // Response interceptor for error handling
    this.addResponseInterceptor({
      onResponseError: async (error) => {
        if (error.response?.status === 401) {
          // Try to refresh token
          const refreshed = await authManager.refreshAccessToken();
          if (refreshed) {
            // Retry original request
            return this.request(error.config);
          }
          // Redirect to login
          authManager.logout();
        }
        
        if (error.response?.status === 403) {
          securityUtils['logSecurityEvent']({
            type: SecurityEventType.VALIDATION_FAILED,
            message: 'Forbidden access attempt',
            details: { url: error.config?.url },
            severity: 'high'
          });
        }
        
        throw error;
      }
    });
  }

  /**
   * Make secure API request
   */
  public async request<T = any>(config: RequestConfig): Promise<T> {
    // Validate request
    if (this.config.enableRequestValidation && !this.validateRequest(config)) {
      throw new Error('Invalid request configuration');
    }

    // Check rate limiting
    const endpoint = new URL(config.url, this.config.baseURL).pathname;
    const userId = authManager.getCurrentUser()?.id;
    
    if (!this.rateLimiter.isAllowed(endpoint, userId)) {
      throw new Error('Rate limit exceeded');
    }

    // Create abort controller
    const abortController = new AbortController();
    const requestId = `${config.method}:${config.url}:${Date.now()}`;
    this.pendingRequests.set(requestId, abortController);

    try {
      // Apply request interceptors
      let processedConfig = config;
      for (const interceptor of this.requestInterceptors) {
        if (interceptor.onRequest) {
          processedConfig = await interceptor.onRequest(processedConfig);
        }
      }

      // Set timeout
      const timeoutId = setTimeout(() => {
        abortController.abort();
      }, processedConfig.timeout || this.config.timeout);

      // Make request
      const response = await fetch(new URL(processedConfig.url, this.config.baseURL).toString(), {
        method: processedConfig.method,
        headers: {
          'Content-Type': 'application/json',
          ...processedConfig.headers
        },
        body: processedConfig.data ? JSON.stringify(processedConfig.data) : undefined,
        credentials: processedConfig.withCredentials ? 'include' : 'same-origin',
        signal: processedConfig.signal || abortController.signal
      });

      clearTimeout(timeoutId);

      // Validate response
      if (this.config.enableResponseValidation && !this.validateResponse(response)) {
        throw new Error('Invalid response');
      }

      // Parse response
      let data: any;
      const contentType = response.headers.get('content-type');
      
      if (contentType?.includes('application/json')) {
        const text = await response.text();
        
        // Validate JSON for security issues
        if (securityUtils.validateJSON(text)) {
          data = JSON.parse(text);
        } else {
          throw new Error('Potentially malicious JSON response');
        }
      } else {
        data = await response.text();
      }

      // Check status
      if (!response.ok) {
        const error: any = new Error(`Request failed with status ${response.status}`);
        error.response = { status: response.status, data, headers: response.headers };
        error.config = config;
        
        // Apply response error interceptors
        for (const interceptor of this.responseInterceptors) {
          if (interceptor.onResponseError) {
            await interceptor.onResponseError(error);
          }
        }
        
        throw error;
      }

      // Apply response interceptors
      let processedData = data;
      for (const interceptor of this.responseInterceptors) {
        if (interceptor.onResponse) {
          processedData = await interceptor.onResponse({ data: processedData, response });
        }
      }

      return processedData;
    } catch (error: any) {
      // Apply request error interceptors
      for (const interceptor of this.requestInterceptors) {
        if (interceptor.onRequestError) {
          await interceptor.onRequestError(error);
        }
      }
      
      // Handle timeout
      if (error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      
      throw error;
    } finally {
      this.pendingRequests.delete(requestId);
    }
  }

  /**
   * GET request
   */
  public async get<T = any>(url: string, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ ...config, url, method: 'GET' });
  }

  /**
   * POST request
   */
  public async post<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ ...config, url, method: 'POST', data });
  }

  /**
   * PUT request
   */
  public async put<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ ...config, url, method: 'PUT', data });
  }

  /**
   * DELETE request
   */
  public async delete<T = any>(url: string, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ ...config, url, method: 'DELETE' });
  }

  /**
   * PATCH request
   */
  public async patch<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<T> {
    return this.request<T>({ ...config, url, method: 'PATCH', data });
  }

  /**
   * Validate request configuration
   */
  private validateRequest(config: RequestConfig): boolean {
    // Validate URL
    try {
      const url = new URL(config.url, this.config.baseURL);
      
      // Check allowed origins
      if (!this.config.allowedOrigins.includes(url.origin) && 
          !url.origin.startsWith(this.config.baseURL)) {
        securityUtils['logSecurityEvent']({
          type: SecurityEventType.VALIDATION_FAILED,
          message: 'Invalid request origin',
          details: { origin: url.origin },
          severity: 'high'
        });
        return false;
      }
    } catch {
      return false;
    }

    // Validate method
    if (!this.config.allowedMethods.includes(config.method)) {
      securityUtils['logSecurityEvent']({
        type: SecurityEventType.VALIDATION_FAILED,
        message: 'Invalid HTTP method',
        details: { method: config.method },
        severity: 'medium'
      });
      return false;
    }

    // Validate data if present
    if (config.data) {
      const dataStr = JSON.stringify(config.data);
      
      // Check for potential injection
      if (securityUtils.detectSQLInjection(dataStr) || 
          securityUtils.detectXSS(dataStr)) {
        securityUtils['logSecurityEvent']({
          type: SecurityEventType.SQL_INJECTION_ATTEMPT,
          message: 'Potential injection in request data',
          details: { url: config.url },
          severity: 'critical'
        });
        return false;
      }
    }

    return true;
  }

  /**
   * Validate response
   */
  private validateResponse(response: Response): boolean {
    // Check for suspicious headers
    const contentType = response.headers.get('content-type');
    
    if (contentType && !contentType.includes('application/json') && 
        !contentType.includes('text/') && !contentType.includes('image/')) {
      securityUtils['logSecurityEvent']({
        type: SecurityEventType.VALIDATION_FAILED,
        message: 'Suspicious content type in response',
        details: { contentType },
        severity: 'medium'
      });
      return false;
    }

    // Check for security headers
    const xssProtection = response.headers.get('x-xss-protection');
    const contentTypeOptions = response.headers.get('x-content-type-options');
    
    if (!xssProtection || !contentTypeOptions) {
      console.warn('Missing security headers in response');
    }

    return true;
  }

  /**
   * Add request interceptor
   */
  public addRequestInterceptor(interceptor: RequestInterceptor): void {
    this.requestInterceptors.push(interceptor);
  }

  /**
   * Add response interceptor
   */
  public addResponseInterceptor(interceptor: ResponseInterceptor): void {
    this.responseInterceptors.push(interceptor);
  }

  /**
   * Cancel all pending requests
   */
  public cancelAllRequests(): void {
    this.pendingRequests.forEach(controller => {
      controller.abort();
    });
    this.pendingRequests.clear();
  }

  /**
   * Get rate limit status
   */
  public getRateLimitStatus(endpoint: string): {
    remaining: number;
    limit: number;
    window: number;
  } {
    const userId = authManager.getCurrentUser()?.id;
    return {
      remaining: this.rateLimiter.getRemainingRequests(endpoint, userId),
      limit: this.config.rateLimitMaxRequests,
      window: this.config.rateLimitWindow
    };
  }

  /**
   * Update configuration
   */
  public updateConfig(config: Partial<APISecurityConfig>): void {
    this.config = { ...this.config, ...config };
  }
}

/**
 * Default export
 */
export const apiSecurity = APISecurity.getInstance();

/**
 * React hook for API security
 */
export function useAPISecurity() {
  return APISecurity.getInstance();
}

/**
 * Export types
 */
export type { RequestConfig, RequestInterceptor, ResponseInterceptor, APISecurityConfig };