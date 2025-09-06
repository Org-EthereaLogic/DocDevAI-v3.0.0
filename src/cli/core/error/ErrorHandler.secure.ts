/**
 * @fileoverview Secure error handler with sanitization and rate limiting
 * @module @cli/core/error/ErrorHandler.secure
 * @version 3.0.0
 * @performance <5ms handling time with security layers
 * @security Stack trace sanitization, PII detection, rate limiting
 */

import { ErrorHandlerOptimized } from './ErrorHandler.optimized';
import { 
  inputValidator, 
  auditLogger, 
  rateLimiter,
  encryptionService 
} from '../security';
import * as crypto from 'crypto';

/**
 * Sensitive information patterns to detect and remove
 */
const SENSITIVE_PATTERNS = [
  // API Keys and Tokens
  /\b[A-Za-z0-9]{32,}\b/g,                          // Generic long tokens
  /sk-[A-Za-z0-9]{48}/g,                            // OpenAI style keys
  /Bearer\s+[A-Za-z0-9\-._~+/]+=*/g,                // Bearer tokens
  /api[_-]?key["\s]*[:=]["\s]*["']?[^"',\s]+/gi,   // API key patterns
  
  // Passwords and Secrets
  /password["\s]*[:=]["\s]*["']?[^"',\s]+/gi,      // Password patterns
  /secret["\s]*[:=]["\s]*["']?[^"',\s]+/gi,        // Secret patterns
  /token["\s]*[:=]["\s]*["']?[^"',\s]+/gi,         // Token patterns
  
  // Personal Information
  /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,  // Email addresses
  /\b\d{3}-\d{2}-\d{4}\b/g,                         // SSN
  /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g,   // Credit card numbers
  /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g,                // Phone numbers
  
  // File Paths with User Info
  /\/home\/[^/\s]+/g,                               // Unix home paths
  /\/Users\/[^/\s]+/g,                              // macOS home paths
  /C:\\Users\\[^\\s]+/g,                            // Windows home paths
  
  // IP Addresses
  /\b(?:\d{1,3}\.){3}\d{1,3}\b/g,                  // IPv4
  /\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b/g, // IPv6
];

/**
 * Error context with security metadata
 */
export interface SecureErrorContext {
  correlationId: string;
  timestamp: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  sanitized: boolean;
  rateLimited: boolean;
  userFacing: boolean;
}

/**
 * Secure error class with sanitized information
 */
export class SecureError extends Error {
  public readonly code: string;
  public readonly context: SecureErrorContext;
  public readonly originalStack?: string;
  public readonly sanitizedStack?: string;

  constructor(
    message: string,
    code: string,
    context?: Partial<SecureErrorContext>
  ) {
    super(message);
    this.name = 'SecureError';
    this.code = code;
    this.context = {
      correlationId: crypto.randomBytes(16).toString('hex'),
      timestamp: Date.now(),
      severity: context?.severity || 'medium',
      sanitized: true,
      rateLimited: false,
      userFacing: context?.userFacing ?? true,
      ...context
    };
  }
}

/**
 * Secure error handler with comprehensive security features
 * Extends optimized handler to maintain performance while adding security
 */
export class SecureErrorHandler extends ErrorHandlerOptimized {
  private readonly errorCounts = new Map<string, number>();
  private readonly correlationMap = new Map<string, SecureError>();
  private readonly maxStackFrames = 10;
  private readonly maxMessageLength = 500;
  private readonly enableSecurityFeatures: boolean;

  constructor(enableSecurity: boolean = true) {
    super();
    this.enableSecurityFeatures = enableSecurity;
    
    // Set up rate limiter handlers
    if (this.enableSecurityFeatures) {
      rateLimiter.on('rate_limit_exceeded', (event) => {
        if (event.operation === 'error_generation') {
          this.handleRateLimitExceeded(event);
        }
      });
    }
  }

  /**
   * Handles an error with security sanitization
   */
  public handleError(error: Error | unknown, context?: Record<string, any>): SecureError {
    const startTime = Date.now();

    try {
      // Check rate limit
      if (this.enableSecurityFeatures) {
        const errorType = error instanceof Error ? error.constructor.name : 'UnknownError';
        if (!rateLimiter.checkErrorGenerationLimit(errorType)) {
          // Create rate limit error
          const rateLimitError = new SecureError(
            'Error generation rate limit exceeded. Please try again later.',
            'RATE_LIMIT_EXCEEDED',
            { severity: 'high', rateLimited: true }
          );

          // Audit the rate limit
          auditLogger.logSuspiciousActivity(
            'Excessive error generation detected',
            'high',
            { errorType, count: this.errorCounts.get(errorType) || 0 }
          );

          return rateLimitError;
        }
      }

      // Convert to Error if needed
      const actualError = this.normalizeError(error);
      
      // Create secure error
      const secureError = this.createSecureError(actualError, context);
      
      // Track error count
      this.trackErrorCount(secureError.code);
      
      // Store for correlation
      this.correlationMap.set(secureError.context.correlationId, secureError);
      
      // Audit the error
      if (this.enableSecurityFeatures) {
        auditLogger.logErrorGeneration({
          code: secureError.code,
          message: this.sanitizeForAudit(secureError.message),
          context: secureError.context
        });
      }

      // Performance check
      const processingTime = Date.now() - startTime;
      if (processingTime > 5) {
        console.warn(`Secure error handling exceeded target: ${processingTime}ms`);
      }

      return secureError;
    } catch (handlingError) {
      // Fallback error if handling fails
      return new SecureError(
        'An error occurred while processing the error',
        'ERROR_HANDLING_FAILED',
        { severity: 'critical' }
      );
    }
  }

  /**
   * Normalizes unknown error types to Error
   */
  private normalizeError(error: unknown): Error {
    if (error instanceof Error) {
      return error;
    }
    
    if (typeof error === 'string') {
      return new Error(error);
    }
    
    if (error && typeof error === 'object' && 'message' in error) {
      return new Error(String(error.message));
    }
    
    return new Error('An unknown error occurred');
  }

  /**
   * Creates a secure error with sanitized information
   */
  private createSecureError(error: Error, context?: Record<string, any>): SecureError {
    // Sanitize message
    const sanitizedMessage = this.sanitizeMessage(error.message);
    
    // Determine error code
    const errorCode = this.generateErrorCode(error);
    
    // Determine severity
    const severity = this.determineSeverity(error);
    
    // Create secure error
    const secureError = new SecureError(
      sanitizedMessage,
      errorCode,
      {
        severity,
        userFacing: this.isUserFacing(error),
        ...context
      }
    );

    // Sanitize stack trace
    if (error.stack && this.enableSecurityFeatures) {
      secureError.originalStack = error.stack;
      secureError.sanitizedStack = this.sanitizeStackTrace(error.stack);
      secureError.stack = secureError.sanitizedStack;
    }

    return secureError;
  }

  /**
   * Sanitizes error message to remove sensitive information
   */
  private sanitizeMessage(message: string): string {
    if (!this.enableSecurityFeatures) {
      return message;
    }

    let sanitized = message;

    // Truncate if too long
    if (sanitized.length > this.maxMessageLength) {
      sanitized = sanitized.substring(0, this.maxMessageLength) + '...';
    }

    // Remove sensitive patterns
    for (const pattern of SENSITIVE_PATTERNS) {
      sanitized = sanitized.replace(pattern, '[REDACTED]');
    }

    // Sanitize user input
    sanitized = inputValidator.sanitizeUserInput(sanitized) as string;

    return sanitized;
  }

  /**
   * Sanitizes stack trace to remove sensitive information
   */
  private sanitizeStackTrace(stack: string): string {
    if (!this.enableSecurityFeatures) {
      return stack;
    }

    const lines = stack.split('\n');
    const sanitizedLines: string[] = [];
    
    // Keep error message and limited stack frames
    for (let i = 0; i < Math.min(lines.length, this.maxStackFrames + 1); i++) {
      let line = lines[i];
      
      // Remove sensitive patterns
      for (const pattern of SENSITIVE_PATTERNS) {
        line = line.replace(pattern, '[REDACTED]');
      }
      
      // Remove absolute paths, keep relative
      line = line.replace(/\/(Users|home|var|opt|tmp)\/[^/\s:]+/g, '/[REDACTED]');
      line = line.replace(/C:\\Users\\[^\\s:]+/g, 'C:\\[REDACTED]');
      
      // Remove specific file paths but keep file names
      line = line.replace(/\(([^)]*\/)?([^/)]+)\)/g, '($2)');
      
      sanitizedLines.push(line);
    }
    
    if (lines.length > this.maxStackFrames + 1) {
      sanitizedLines.push(`    ... ${lines.length - this.maxStackFrames - 1} more frames`);
    }
    
    return sanitizedLines.join('\n');
  }

  /**
   * Generates error code from error type
   */
  private generateErrorCode(error: Error): string {
    // Check for existing code
    if ('code' in error && typeof error.code === 'string') {
      return error.code;
    }
    
    // Generate based on error type
    const errorType = error.constructor.name;
    const hash = crypto.createHash('md5')
      .update(errorType + error.message)
      .digest('hex')
      .substring(0, 8)
      .toUpperCase();
    
    return `${errorType.toUpperCase()}_${hash}`;
  }

  /**
   * Determines error severity
   */
  private determineSeverity(error: Error): 'low' | 'medium' | 'high' | 'critical' {
    // Check for specific error types
    if (error.name === 'SecurityError' || error.message.includes('security')) {
      return 'critical';
    }
    
    if (error.name === 'ValidationError' || error.message.includes('validation')) {
      return 'medium';
    }
    
    if (error.name === 'RateLimitError' || error.message.includes('rate limit')) {
      return 'high';
    }
    
    // Check error count frequency
    const errorCode = this.generateErrorCode(error);
    const count = this.errorCounts.get(errorCode) || 0;
    
    if (count > 100) return 'critical';
    if (count > 50) return 'high';
    if (count > 10) return 'medium';
    
    return 'low';
  }

  /**
   * Determines if error should be shown to user
   */
  private isUserFacing(error: Error): boolean {
    // Internal errors should not be shown to users
    const internalErrors = [
      'AssertionError',
      'ReferenceError',
      'SyntaxError',
      'SystemError'
    ];
    
    return !internalErrors.includes(error.name);
  }

  /**
   * Tracks error count for rate limiting
   */
  private trackErrorCount(errorCode: string): void {
    const count = this.errorCounts.get(errorCode) || 0;
    this.errorCounts.set(errorCode, count + 1);
    
    // Clean up old entries periodically
    if (this.errorCounts.size > 1000) {
      const entries = Array.from(this.errorCounts.entries());
      entries.sort((a, b) => a[1] - b[1]);
      
      // Remove least frequent errors
      for (let i = 0; i < 500; i++) {
        this.errorCounts.delete(entries[i][0]);
      }
    }
  }

  /**
   * Sanitizes value for audit logging
   */
  private sanitizeForAudit(value: string): string {
    // Remove PII but keep enough for debugging
    let sanitized = value;
    
    // Replace emails with domain only
    sanitized = sanitized.replace(
      /([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})/g,
      '[email]@$2'
    );
    
    // Replace IPs with partial
    sanitized = sanitized.replace(
      /\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b/g,
      '$1.$2.xxx.xxx'
    );
    
    return sanitized;
  }

  /**
   * Handles rate limit exceeded events
   */
  private handleRateLimitExceeded(event: any): void {
    // Log suspicious activity
    auditLogger.logSuspiciousActivity(
      'Error generation rate limit exceeded',
      'high',
      event
    );
    
    // Clear error counts for the source
    if (event.source) {
      this.errorCounts.delete(event.source);
    }
  }

  /**
   * Gets error by correlation ID
   */
  public getErrorByCorrelationId(correlationId: string): SecureError | undefined {
    return this.correlationMap.get(correlationId);
  }

  /**
   * Formats error for user display
   */
  public formatForUser(error: SecureError): string {
    if (!error.context.userFacing) {
      return 'An internal error occurred. Please contact support with correlation ID: ' + 
             error.context.correlationId;
    }
    
    return `Error: ${error.message} (Code: ${error.code})`;
  }

  /**
   * Formats error for logging
   */
  public formatForLogging(error: SecureError): string {
    return JSON.stringify({
      correlationId: error.context.correlationId,
      code: error.code,
      message: error.message,
      severity: error.context.severity,
      timestamp: error.context.timestamp,
      stack: error.sanitizedStack
    }, null, 2);
  }

  /**
   * Gets error statistics
   */
  public getStatistics(): {
    totalErrors: number;
    uniqueErrors: number;
    topErrors: Array<{ code: string; count: number }>;
    severityDistribution: Record<string, number>;
  } {
    const topErrors = Array.from(this.errorCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([code, count]) => ({ code, count }));
    
    const severityDistribution: Record<string, number> = {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0
    };
    
    for (const error of this.correlationMap.values()) {
      severityDistribution[error.context.severity]++;
    }
    
    const totalErrors = Array.from(this.errorCounts.values())
      .reduce((sum, count) => sum + count, 0);
    
    return {
      totalErrors,
      uniqueErrors: this.errorCounts.size,
      topErrors,
      severityDistribution
    };
  }

  /**
   * Clears error history
   */
  public clearHistory(): void {
    this.errorCounts.clear();
    this.correlationMap.clear();
    
    if (this.enableSecurityFeatures) {
      auditLogger.logSecurityEvent({
        type: 'configuration_change',
        severity: 'info',
        source: 'error_handler',
        action: 'clear_history',
        result: 'success'
      });
    }
  }
}

// Export singleton instance
export const secureErrorHandler = new SecureErrorHandler();