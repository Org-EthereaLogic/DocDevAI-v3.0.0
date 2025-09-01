/**
 * M011 Security Utilities - Comprehensive security utilities for React UI
 * 
 * Provides XSS prevention, input sanitization, and validation functions
 * following OWASP Top 10 guidelines and integrating with M010 Security Module.
 */

import DOMPurify from 'dompurify';
import validator from 'validator';
import { v4 as uuidv4 } from 'uuid';

/**
 * Security configuration interface
 */
export interface SecurityConfig {
  maxInputLength: number;
  allowedTags: string[];
  allowedAttributes: string[];
  allowedSchemes: string[];
  enableCSP: boolean;
  enableSanitization: boolean;
  enableValidation: boolean;
  logSecurityEvents: boolean;
}

/**
 * Default security configuration
 */
export const DEFAULT_SECURITY_CONFIG: SecurityConfig = {
  maxInputLength: 10000,
  allowedTags: ['p', 'b', 'i', 'em', 'strong', 'a', 'ul', 'ol', 'li', 'blockquote', 'code', 'pre'],
  allowedAttributes: ['href', 'title', 'target'],
  allowedSchemes: ['http', 'https', 'mailto'],
  enableCSP: true,
  enableSanitization: true,
  enableValidation: true,
  logSecurityEvents: true
};

/**
 * XSS attack patterns for detection
 */
const XSS_PATTERNS = [
  /<script[^>]*>.*?<\/script>/gi,
  /javascript:/gi,
  /on\w+\s*=/gi,
  /<iframe[^>]*>/gi,
  /<object[^>]*>/gi,
  /<embed[^>]*>/gi,
  /<applet[^>]*>/gi,
  /data:text\/html/gi,
  /vbscript:/gi,
  /onclick|onerror|onload|onmouseover|onfocus|onblur/gi,
  /<img[^>]*src[^>]*>/gi,
  /eval\s*\(/gi,
  /expression\s*\(/gi,
  /prompt\s*\(/gi,
  /confirm\s*\(/gi,
  /alert\s*\(/gi
];

/**
 * SQL injection patterns for detection
 */
const SQL_INJECTION_PATTERNS = [
  /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|FROM|WHERE|ORDER BY|GROUP BY|HAVING)\b)/gi,
  /(--)|(\/\*[\s\S]*?\*\/)/g,
  /(\bOR\b|\bAND\b)\s*\d+\s*=\s*\d+/gi,
  /['";].*(\bOR\b|\bAND\b).*['";]/gi,
  /\b(1=1|2=2|'=')\b/gi,
  /\bwaitfor\s+delay\b/gi,
  /\bexec\s*\(/gi,
  /\bxp_cmdshell\b/gi
];

/**
 * Path traversal patterns for detection
 */
const PATH_TRAVERSAL_PATTERNS = [
  /\.\.\//g,
  /\.\.%2[fF]/g,
  /%2e%2e/gi,
  /\.\.;/g,
  /\.\.%5[cC]/g,
  /\.\.%252[fF]/gi,
  /\.\.0x2f/gi,
  /\.\.%c0%af/gi
];

/**
 * Security event types
 */
export enum SecurityEventType {
  XSS_ATTEMPT = 'XSS_ATTEMPT',
  SQL_INJECTION_ATTEMPT = 'SQL_INJECTION_ATTEMPT',
  PATH_TRAVERSAL_ATTEMPT = 'PATH_TRAVERSAL_ATTEMPT',
  INVALID_INPUT = 'INVALID_INPUT',
  SANITIZATION_APPLIED = 'SANITIZATION_APPLIED',
  VALIDATION_FAILED = 'VALIDATION_FAILED',
  CSRF_TOKEN_MISMATCH = 'CSRF_TOKEN_MISMATCH',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'
}

/**
 * Security event interface
 */
export interface SecurityEvent {
  id: string;
  type: SecurityEventType;
  message: string;
  details: any;
  timestamp: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  source?: string;
  userId?: string;
  ip?: string;
}

/**
 * Security utilities class
 */
export class SecurityUtils {
  private static instance: SecurityUtils;
  private config: SecurityConfig;
  private securityEvents: SecurityEvent[] = [];
  private readonly MAX_EVENTS = 1000;

  private constructor(config: SecurityConfig = DEFAULT_SECURITY_CONFIG) {
    this.config = config;
    this.initializeDOMPurify();
  }

  /**
   * Get singleton instance
   */
  public static getInstance(config?: SecurityConfig): SecurityUtils {
    if (!SecurityUtils.instance) {
      SecurityUtils.instance = new SecurityUtils(config);
    }
    return SecurityUtils.instance;
  }

  /**
   * Initialize DOMPurify with custom configuration
   */
  private initializeDOMPurify(): void {
    // Configure DOMPurify
    DOMPurify.addHook('afterSanitizeAttributes', (node) => {
      // Force target="_blank" for external links
      if (node.tagName === 'A' && node.hasAttribute('href')) {
        const href = node.getAttribute('href') || '';
        if (href.startsWith('http') && !href.includes(window.location.hostname)) {
          node.setAttribute('target', '_blank');
          node.setAttribute('rel', 'noopener noreferrer');
        }
      }
    });

    // Remove dangerous elements
    DOMPurify.addHook('uponSanitizeElement', (node, data) => {
      if (data.tagName === 'script' || 
          data.tagName === 'iframe' || 
          data.tagName === 'object' ||
          data.tagName === 'embed' ||
          data.tagName === 'applet') {
        this.logSecurityEvent({
          type: SecurityEventType.XSS_ATTEMPT,
          message: `Blocked dangerous element: ${data.tagName}`,
          details: { tagName: data.tagName },
          severity: 'high'
        });
      }
    });
  }

  /**
   * Sanitize HTML content
   */
  public sanitizeHTML(input: string, customConfig?: Partial<SecurityConfig>): string {
    if (!this.config.enableSanitization) {
      return input;
    }

    const config = { ...this.config, ...customConfig };
    
    // Check for XSS patterns
    if (this.detectXSS(input)) {
      this.logSecurityEvent({
        type: SecurityEventType.XSS_ATTEMPT,
        message: 'XSS pattern detected in HTML content',
        details: { input: input.substring(0, 100) },
        severity: 'high'
      });
    }

    // Sanitize with DOMPurify
    const clean = DOMPurify.sanitize(input, {
      ALLOWED_TAGS: config.allowedTags,
      ALLOWED_ATTR: config.allowedAttributes,
      ALLOWED_URI_REGEXP: new RegExp(`^(${config.allowedSchemes.join('|')}):`, 'i'),
      KEEP_CONTENT: true,
      RETURN_DOM: false,
      RETURN_DOM_FRAGMENT: false,
      RETURN_DOM_IMPORT: false,
      SAFE_FOR_TEMPLATES: true,
      SANITIZE_DOM: true,
      WHOLE_DOCUMENT: false,
      FORCE_BODY: false,
      IN_PLACE: false
    });

    if (clean !== input) {
      this.logSecurityEvent({
        type: SecurityEventType.SANITIZATION_APPLIED,
        message: 'HTML content was sanitized',
        details: { 
          originalLength: input.length,
          sanitizedLength: clean.length
        },
        severity: 'low'
      });
    }

    return clean;
  }

  /**
   * Sanitize user input
   */
  public sanitizeInput(input: string, type: 'text' | 'email' | 'url' | 'number' | 'alphanumeric' = 'text'): string {
    if (!this.config.enableSanitization) {
      return input;
    }

    // Trim and limit length
    let sanitized = input.trim().substring(0, this.config.maxInputLength);

    // Check for injection patterns
    if (this.detectSQLInjection(sanitized)) {
      this.logSecurityEvent({
        type: SecurityEventType.SQL_INJECTION_ATTEMPT,
        message: 'SQL injection pattern detected',
        details: { input: sanitized.substring(0, 100) },
        severity: 'critical'
      });
      sanitized = this.escapeSQL(sanitized);
    }

    // Type-specific sanitization
    switch (type) {
      case 'email':
        sanitized = validator.normalizeEmail(sanitized) || '';
        break;
      case 'url':
        sanitized = this.sanitizeURL(sanitized);
        break;
      case 'number':
        sanitized = sanitized.replace(/[^0-9.-]/g, '');
        break;
      case 'alphanumeric':
        sanitized = sanitized.replace(/[^a-zA-Z0-9\s]/g, '');
        break;
      default:
        // Remove control characters and null bytes
        sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
        break;
    }

    // Escape HTML entities
    sanitized = this.escapeHTML(sanitized);

    return sanitized;
  }

  /**
   * Validate user input
   */
  public validateInput(input: string, type: 'text' | 'email' | 'url' | 'number' | 'alphanumeric' | 'json'): boolean {
    if (!this.config.enableValidation) {
      return true;
    }

    try {
      switch (type) {
        case 'email':
          return validator.isEmail(input);
        case 'url':
          return validator.isURL(input, {
            protocols: ['http', 'https'],
            require_protocol: true
          });
        case 'number':
          return validator.isNumeric(input);
        case 'alphanumeric':
          return validator.isAlphanumeric(input, 'en-US', { ignore: ' ' });
        case 'json':
          JSON.parse(input);
          return true;
        default:
          // Check for dangerous patterns
          return !this.detectXSS(input) && 
                 !this.detectSQLInjection(input) && 
                 !this.detectPathTraversal(input);
      }
    } catch (error) {
      this.logSecurityEvent({
        type: SecurityEventType.VALIDATION_FAILED,
        message: `Input validation failed for type: ${type}`,
        details: { error: error instanceof Error ? error.message : 'Unknown error' },
        severity: 'medium'
      });
      return false;
    }
  }

  /**
   * Escape HTML entities
   */
  public escapeHTML(input: string): string {
    const map: { [key: string]: string } = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#x27;',
      '/': '&#x2F;'
    };
    return input.replace(/[&<>"'/]/g, (char) => map[char] || char);
  }

  /**
   * Unescape HTML entities
   */
  public unescapeHTML(input: string): string {
    const map: { [key: string]: string } = {
      '&amp;': '&',
      '&lt;': '<',
      '&gt;': '>',
      '&quot;': '"',
      '&#x27;': "'",
      '&#x2F;': '/'
    };
    return input.replace(/&amp;|&lt;|&gt;|&quot;|&#x27;|&#x2F;/g, (entity) => map[entity] || entity);
  }

  /**
   * Escape SQL special characters
   */
  public escapeSQL(input: string): string {
    return input
      .replace(/'/g, "''")
      .replace(/"/g, '""')
      .replace(/\\/g, '\\\\')
      .replace(/\0/g, '\\0')
      .replace(/\n/g, '\\n')
      .replace(/\r/g, '\\r')
      .replace(/\x1a/g, '\\Z');
  }

  /**
   * Sanitize URL
   */
  public sanitizeURL(url: string): string {
    try {
      const parsed = new URL(url);
      
      // Only allow http(s) and mailto
      if (!['http:', 'https:', 'mailto:'].includes(parsed.protocol)) {
        this.logSecurityEvent({
          type: SecurityEventType.INVALID_INPUT,
          message: `Invalid URL protocol: ${parsed.protocol}`,
          details: { url: url.substring(0, 100) },
          severity: 'medium'
        });
        return '';
      }

      // Check for javascript: protocol disguised as path
      if (parsed.pathname.toLowerCase().includes('javascript:')) {
        this.logSecurityEvent({
          type: SecurityEventType.XSS_ATTEMPT,
          message: 'JavaScript protocol detected in URL',
          details: { url: url.substring(0, 100) },
          severity: 'high'
        });
        return '';
      }

      return parsed.toString();
    } catch (error) {
      this.logSecurityEvent({
        type: SecurityEventType.INVALID_INPUT,
        message: 'Invalid URL format',
        details: { url: url.substring(0, 100) },
        severity: 'low'
      });
      return '';
    }
  }

  /**
   * Detect XSS patterns
   */
  public detectXSS(input: string): boolean {
    return XSS_PATTERNS.some(pattern => pattern.test(input));
  }

  /**
   * Detect SQL injection patterns
   */
  public detectSQLInjection(input: string): boolean {
    return SQL_INJECTION_PATTERNS.some(pattern => pattern.test(input));
  }

  /**
   * Detect path traversal patterns
   */
  public detectPathTraversal(input: string): boolean {
    return PATH_TRAVERSAL_PATTERNS.some(pattern => pattern.test(input));
  }

  /**
   * Generate secure random token
   */
  public generateToken(length: number = 32): string {
    const array = new Uint8Array(length);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Generate UUID
   */
  public generateUUID(): string {
    return uuidv4();
  }

  /**
   * Generate CSP nonce
   */
  public generateCSPNonce(): string {
    return `nonce-${this.generateToken(16)}`;
  }

  /**
   * Validate file type
   */
  public validateFileType(file: File, allowedTypes: string[]): boolean {
    const fileType = file.type.toLowerCase();
    const isValid = allowedTypes.some(type => {
      if (type.includes('*')) {
        const [category] = type.split('/');
        return fileType.startsWith(`${category}/`);
      }
      return fileType === type;
    });

    if (!isValid) {
      this.logSecurityEvent({
        type: SecurityEventType.INVALID_INPUT,
        message: `Invalid file type: ${file.type}`,
        details: { 
          fileName: file.name,
          fileType: file.type,
          allowedTypes
        },
        severity: 'medium'
      });
    }

    return isValid;
  }

  /**
   * Validate file size
   */
  public validateFileSize(file: File, maxSizeInBytes: number): boolean {
    const isValid = file.size <= maxSizeInBytes;

    if (!isValid) {
      this.logSecurityEvent({
        type: SecurityEventType.INVALID_INPUT,
        message: `File size exceeds limit: ${file.size} > ${maxSizeInBytes}`,
        details: { 
          fileName: file.name,
          fileSize: file.size,
          maxSize: maxSizeInBytes
        },
        severity: 'low'
      });
    }

    return isValid;
  }

  /**
   * Check for suspicious patterns in JSON
   */
  public validateJSON(jsonString: string): boolean {
    try {
      const parsed = JSON.parse(jsonString);
      
      // Check for prototype pollution
      if ('__proto__' in parsed || 'constructor' in parsed || 'prototype' in parsed) {
        this.logSecurityEvent({
          type: SecurityEventType.INVALID_INPUT,
          message: 'Potential prototype pollution detected',
          details: { keys: Object.keys(parsed) },
          severity: 'high'
        });
        return false;
      }

      // Recursively check nested objects
      const checkObject = (obj: any): boolean => {
        if (obj && typeof obj === 'object') {
          for (const key in obj) {
            if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
              return false;
            }
            if (!checkObject(obj[key])) {
              return false;
            }
          }
        }
        return true;
      };

      return checkObject(parsed);
    } catch (error) {
      this.logSecurityEvent({
        type: SecurityEventType.INVALID_INPUT,
        message: 'Invalid JSON format',
        details: { error: error instanceof Error ? error.message : 'Unknown error' },
        severity: 'medium'
      });
      return false;
    }
  }

  /**
   * Create safe React props
   */
  public createSafeProps(props: any): any {
    const safeProps = { ...props };

    // Remove dangerous props
    delete safeProps.dangerouslySetInnerHTML;
    delete safeProps.innerHTML;

    // Sanitize event handlers
    Object.keys(safeProps).forEach(key => {
      if (key.startsWith('on') && typeof safeProps[key] === 'string') {
        delete safeProps[key];
        this.logSecurityEvent({
          type: SecurityEventType.XSS_ATTEMPT,
          message: `Removed string event handler: ${key}`,
          details: { prop: key },
          severity: 'high'
        });
      }
    });

    return safeProps;
  }

  /**
   * Log security event
   */
  private logSecurityEvent(event: Omit<SecurityEvent, 'id' | 'timestamp'>): void {
    if (!this.config.logSecurityEvents) {
      return;
    }

    const securityEvent: SecurityEvent = {
      ...event,
      id: this.generateUUID(),
      timestamp: Date.now()
    };

    this.securityEvents.push(securityEvent);

    // Limit stored events
    if (this.securityEvents.length > this.MAX_EVENTS) {
      this.securityEvents = this.securityEvents.slice(-this.MAX_EVENTS);
    }

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.warn('[Security Event]', securityEvent);
    }
  }

  /**
   * Get security events
   */
  public getSecurityEvents(filters?: {
    type?: SecurityEventType;
    severity?: 'low' | 'medium' | 'high' | 'critical';
    since?: number;
  }): SecurityEvent[] {
    let events = [...this.securityEvents];

    if (filters) {
      if (filters.type) {
        events = events.filter(e => e.type === filters.type);
      }
      if (filters.severity) {
        events = events.filter(e => e.severity === filters.severity);
      }
      if (filters.since) {
        events = events.filter(e => e.timestamp >= filters.since);
      }
    }

    return events;
  }

  /**
   * Clear security events
   */
  public clearSecurityEvents(): void {
    this.securityEvents = [];
  }

  /**
   * Update configuration
   */
  public updateConfig(config: Partial<SecurityConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get current configuration
   */
  public getConfig(): SecurityConfig {
    return { ...this.config };
  }
}

/**
 * Default export for convenience
 */
export const securityUtils = SecurityUtils.getInstance();

/**
 * React hook for security utilities
 */
export function useSecurityUtils(): SecurityUtils {
  return SecurityUtils.getInstance();
}

/**
 * Content Security Policy builder
 */
export class CSPBuilder {
  private directives: Map<string, string[]> = new Map();

  constructor() {
    // Set default directives
    this.directive('default-src', ["'self'"]);
    this.directive('script-src', ["'self'", "'unsafe-inline'"]);
    this.directive('style-src', ["'self'", "'unsafe-inline'"]);
    this.directive('img-src', ["'self'", 'data:', 'https:']);
    this.directive('font-src', ["'self'", 'data:']);
    this.directive('connect-src', ["'self'"]);
    this.directive('frame-ancestors', ["'none'"]);
    this.directive('base-uri', ["'self'"]);
    this.directive('form-action', ["'self'"]);
  }

  /**
   * Add directive
   */
  public directive(name: string, values: string[]): CSPBuilder {
    this.directives.set(name, values);
    return this;
  }

  /**
   * Add nonce to script-src
   */
  public addScriptNonce(nonce: string): CSPBuilder {
    const scriptSrc = this.directives.get('script-src') || [];
    scriptSrc.push(`'${nonce}'`);
    this.directives.set('script-src', scriptSrc);
    return this;
  }

  /**
   * Add nonce to style-src
   */
  public addStyleNonce(nonce: string): CSPBuilder {
    const styleSrc = this.directives.get('style-src') || [];
    styleSrc.push(`'${nonce}'`);
    this.directives.set('style-src', styleSrc);
    return this;
  }

  /**
   * Build CSP string
   */
  public build(): string {
    const policies: string[] = [];
    
    this.directives.forEach((values, directive) => {
      policies.push(`${directive} ${values.join(' ')}`);
    });

    return policies.join('; ');
  }

  /**
   * Build as meta tag content
   */
  public buildMetaContent(): string {
    // Remove frame-ancestors for meta tag (not supported)
    const temp = this.directives.get('frame-ancestors');
    this.directives.delete('frame-ancestors');
    
    const content = this.build();
    
    // Restore frame-ancestors
    if (temp) {
      this.directives.set('frame-ancestors', temp);
    }
    
    return content;
  }
}

/**
 * Export security event types and interfaces for external use
 */
export type { SecurityEvent };