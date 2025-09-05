/**
 * DevDocAI v3.0.0 - Security Configuration
 * 
 * Centralized security settings and utilities for the application
 */

export interface SecurityConfig {
  storage: StorageConfig;
  api: APIConfig;
  content: ContentConfig;
  privacy: PrivacyConfig;
  validation: ValidationConfig;
}

export interface StorageConfig {
  // Maximum size for localStorage data
  maxStorageSize: number;
  // Maximum number of items to store
  maxItems: number;
  // Data expiry in days
  expiryDays: number;
  // Storage key prefix
  keyPrefix: string;
  // Encrypt sensitive data
  encryption: {
    enabled: boolean;
    algorithm: string;
  };
}

export interface APIConfig {
  // API endpoints
  baseUrl: string;
  // Request timeout in ms
  timeout: number;
  // Retry configuration
  retry: {
    maxAttempts: number;
    backoffMs: number;
  };
  // Rate limiting
  rateLimit: {
    requestsPerMinute: number;
    burstSize: number;
  };
  // Authentication
  auth: {
    enabled: boolean;
    tokenKey: string;
    refreshInterval: number;
  };
}

export interface ContentConfig {
  // Maximum content size in bytes
  maxContentSize: number;
  // Allowed file extensions
  allowedExtensions: string[];
  // Sanitization rules
  sanitization: {
    removeScripts: boolean;
    removeStyles: boolean;
    removeComments: boolean;
    allowedTags: string[];
    allowedAttributes: string[];
  };
}

export interface PrivacyConfig {
  // PII detection
  piiDetection: {
    enabled: boolean;
    patterns: Record<string, RegExp>;
    blockStorage: boolean;
    warnUser: boolean;
  };
  // Data retention
  retention: {
    defaultDays: number;
    maxDays: number;
    autoDelete: boolean;
  };
  // Compliance
  compliance: {
    gdpr: boolean;
    ccpa: boolean;
    requireConsent: boolean;
  };
}

export interface ValidationConfig {
  // Input validation rules
  fileName: {
    maxLength: number;
    pattern: RegExp;
    blacklist: string[];
  };
  content: {
    maxLength: number;
    minLength: number;
    requireNonEmpty: boolean;
  };
  // Security headers
  headers: {
    csp: string;
    hsts: boolean;
    frameOptions: string;
    contentTypeOptions: string;
  };
}

// Default security configuration
export const defaultSecurityConfig: SecurityConfig = {
  storage: {
    maxStorageSize: 1024 * 1024, // 1MB
    maxItems: 10,
    expiryDays: 30,
    keyPrefix: 'devdocai_',
    encryption: {
      enabled: true,
      algorithm: 'AES-256',
    },
  },
  api: {
    baseUrl: process.env.REACT_APP_API_URL || '/api',
    timeout: 30000, // 30 seconds
    retry: {
      maxAttempts: 3,
      backoffMs: 1000,
    },
    rateLimit: {
      requestsPerMinute: 10, // Conservative for AI operations
      burstSize: 3,
    },
    auth: {
      enabled: false, // Enable in production
      tokenKey: 'devdocai_auth_token',
      refreshInterval: 3600000, // 1 hour
    },
  },
  content: {
    maxContentSize: 50000, // 50KB
    allowedExtensions: ['.md', '.txt', '.rst', '.adoc'],
    sanitization: {
      removeScripts: true,
      removeStyles: true,
      removeComments: true,
      allowedTags: [
        'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'code', 'pre', 'ul', 'ol', 'li', 'a', 'img'
      ],
      allowedAttributes: ['href', 'src', 'alt', 'title', 'class'],
    },
  },
  privacy: {
    piiDetection: {
      enabled: true,
      patterns: {
        ssn: /\b\d{3}-\d{2}-\d{4}\b/,
        creditCard: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/,
        email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/,
        phone: /\b(\+?1?\d{10,14}|\(\d{3}\)\s?\d{3}-\d{4})\b/,
        ipAddress: /\b(?:\d{1,3}\.){3}\d{1,3}\b/,
        apiKey: /\b[A-Za-z0-9]{32,}\b/,
        jwt: /^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/,
      },
      blockStorage: true,
      warnUser: true,
    },
    retention: {
      defaultDays: 30,
      maxDays: 90,
      autoDelete: true,
    },
    compliance: {
      gdpr: true,
      ccpa: true,
      requireConsent: true,
    },
  },
  validation: {
    fileName: {
      maxLength: 100,
      pattern: /^[a-zA-Z0-9._-]+$/,
      blacklist: ['..', '/', '\\', '~', '${', '%'],
    },
    content: {
      maxLength: 50000,
      minLength: 1,
      requireNonEmpty: true,
    },
    headers: {
      csp: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' http://localhost:*",
      hsts: true,
      frameOptions: 'DENY',
      contentTypeOptions: 'nosniff',
    },
  },
};

// Security utilities
export class SecurityUtils {
  private static config: SecurityConfig = defaultSecurityConfig;

  /**
   * Set custom security configuration
   */
  static setConfig(config: Partial<SecurityConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get current security configuration
   */
  static getConfig(): SecurityConfig {
    return this.config;
  }

  /**
   * Validate file name against security rules
   */
  static validateFileName(fileName: string): { valid: boolean; sanitized: string } {
    const { maxLength, pattern, blacklist } = this.config.validation.fileName;
    
    // Check for blacklisted patterns
    for (const black of blacklist) {
      if (fileName.includes(black)) {
        return { valid: false, sanitized: 'document.md' };
      }
    }

    // Sanitize
    let sanitized = fileName.substring(0, maxLength);
    sanitized = sanitized.replace(/[^a-zA-Z0-9._-]/g, '');
    
    // Validate against pattern
    const valid = pattern.test(sanitized) && sanitized.length > 0;
    
    return {
      valid,
      sanitized: valid ? sanitized : 'document.md',
    };
  }

  /**
   * Check content for PII
   */
  static checkForPII(content: string): { hasPII: boolean; types: string[]; matches: number } {
    if (!this.config.privacy.piiDetection.enabled) {
      return { hasPII: false, types: [], matches: 0 };
    }

    const detectedTypes: string[] = [];
    let totalMatches = 0;

    for (const [type, pattern] of Object.entries(this.config.privacy.piiDetection.patterns)) {
      const matches = (content.match(pattern) || []).length;
      if (matches > 0) {
        detectedTypes.push(type);
        totalMatches += matches;
      }
    }

    return {
      hasPII: detectedTypes.length > 0,
      types: detectedTypes,
      matches: totalMatches,
    };
  }

  /**
   * Generate secure random ID
   */
  static generateSecureId(): string {
    const timestamp = Date.now().toString(36);
    const randomStr = Math.random().toString(36).substring(2, 15);
    const browserRandom = window.crypto.getRandomValues(new Uint32Array(1))[0].toString(36);
    return `${timestamp}_${randomStr}_${browserRandom}`;
  }

  /**
   * Calculate content hash
   */
  static async hashContent(content: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex;
  }

  /**
   * Sanitize HTML content
   */
  static sanitizeHTML(html: string): string {
    const { allowedTags, allowedAttributes } = this.config.content.sanitization;
    
    // Create temporary element
    const temp = document.createElement('div');
    temp.innerHTML = html;
    
    // Remove script tags
    const scripts = temp.getElementsByTagName('script');
    for (let i = scripts.length - 1; i >= 0; i--) {
      scripts[i].parentNode?.removeChild(scripts[i]);
    }
    
    // Remove style tags if configured
    if (this.config.content.sanitization.removeStyles) {
      const styles = temp.getElementsByTagName('style');
      for (let i = styles.length - 1; i >= 0; i--) {
        styles[i].parentNode?.removeChild(styles[i]);
      }
    }
    
    // Remove event handlers
    const allElements = temp.getElementsByTagName('*');
    for (let i = 0; i < allElements.length; i++) {
      const elem = allElements[i] as HTMLElement;
      // Remove event handlers
      for (const attr of Array.from(elem.attributes)) {
        if (attr.name.startsWith('on')) {
          elem.removeAttribute(attr.name);
        }
      }
    }
    
    return temp.innerHTML;
  }

  /**
   * Check if storage quota is available
   */
  static async checkStorageQuota(): Promise<{ usage: number; quota: number; percentUsed: number }> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      const usage = estimate.usage || 0;
      const quota = estimate.quota || 0;
      const percentUsed = quota > 0 ? (usage / quota) * 100 : 0;
      
      return { usage, quota, percentUsed };
    }
    
    // Fallback for older browsers
    const usage = new Blob(Object.values(localStorage)).size;
    const quota = 5 * 1024 * 1024; // 5MB default
    const percentUsed = (usage / quota) * 100;
    
    return { usage, quota, percentUsed };
  }

  /**
   * Add security headers to fetch requests
   */
  static addSecurityHeaders(headers: HeadersInit = {}): HeadersInit {
    return {
      ...headers,
      'X-Requested-With': 'XMLHttpRequest',
      'X-Request-ID': this.generateSecureId(),
      'Cache-Control': 'no-cache, no-store, must-revalidate',
    };
  }

  /**
   * Create CSP meta tag
   */
  static createCSPMetaTag(): HTMLMetaElement {
    const meta = document.createElement('meta');
    meta.httpEquiv = 'Content-Security-Policy';
    meta.content = this.config.validation.headers.csp;
    return meta;
  }

  /**
   * Apply security headers to document
   */
  static applySecurityHeaders(): void {
    // Add CSP if not present
    if (!document.querySelector('meta[http-equiv="Content-Security-Policy"]')) {
      document.head.appendChild(this.createCSPMetaTag());
    }

    // Add other security meta tags
    const securityMeta = [
      { httpEquiv: 'X-Content-Type-Options', content: this.config.validation.headers.contentTypeOptions },
      { httpEquiv: 'X-Frame-Options', content: this.config.validation.headers.frameOptions },
      { httpEquiv: 'X-XSS-Protection', content: '1; mode=block' },
      { name: 'referrer', content: 'strict-origin-when-cross-origin' },
    ];

    securityMeta.forEach(({ httpEquiv, name, content }) => {
      if (!document.querySelector(`meta[${httpEquiv ? 'http-equiv' : 'name'}="${httpEquiv || name}"]`)) {
        const meta = document.createElement('meta');
        if (httpEquiv) meta.httpEquiv = httpEquiv;
        if (name) meta.name = name;
        meta.content = content;
        document.head.appendChild(meta);
      }
    });
  }
}

// Auto-apply security headers on load
if (typeof window !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    SecurityUtils.applySecurityHeaders();
  });
}

export default SecurityUtils;