/**
 * @fileoverview Unified Error Handler with mode-based behavior
 * @module @cli/core/error/ErrorHandler.unified
 * @version 1.0.0
 * @performance <5ms processing time in all modes
 * @security Sanitization, logging, and audit trail
 */

import { ErrorCode } from './codes';
import { SecurityService, SecurityMode } from '../security/SecurityService.unified';

/**
 * Error handler operation mode
 */
export enum ErrorHandlerMode {
  BASIC = 'basic',          // Simple error handling
  OPTIMIZED = 'optimized',  // Performance optimizations
  SECURE = 'secure',        // Security features enabled
  ENTERPRISE = 'enterprise' // All features enabled
}

/**
 * Error severity levels
 */
export enum ErrorSeverity {
  DEBUG = 'debug',
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical'
}

/**
 * Error context information
 */
export interface ErrorContext {
  code?: ErrorCode;
  severity?: ErrorSeverity;
  module?: string;
  operation?: string;
  metadata?: Record<string, any>;
  timestamp?: Date;
  stack?: string;
  userId?: string;
  sessionId?: string;
}

/**
 * Processed error information
 */
export interface ProcessedError {
  message: string;
  code: ErrorCode;
  severity: ErrorSeverity;
  context: ErrorContext;
  sanitized: boolean;
  suggestions?: string[];
  userMessage?: string;
  developerMessage?: string;
}

/**
 * Error handler configuration
 */
export interface ErrorHandlerConfig {
  mode?: ErrorHandlerMode;
  security?: SecurityService;
  performance?: {
    caching?: boolean;
    batchProcessing?: boolean;
    asyncLogging?: boolean;
  };
  features?: {
    stackTrace?: boolean;
    suggestions?: boolean;
    sanitization?: boolean;
    audit?: boolean;
  };
  recovery?: {
    enabled?: boolean;
    strategies?: Map<ErrorCode, () => Promise<void>>;
    maxRetries?: number;
  };
}

/**
 * Unified Error Handler
 * Combines basic, optimized, and secure error handling with
 * configurable mode-based behavior
 */
export class UnifiedErrorHandler {
  private mode: ErrorHandlerMode;
  private security: SecurityService;
  private config: Required<ErrorHandlerConfig>;
  private errorCache = new Map<string, ProcessedError>();
  private errorQueue: ProcessedError[] = [];
  private batchTimer?: NodeJS.Timer;
  private metrics = {
    totalErrors: 0,
    errorsByCode: new Map<ErrorCode, number>(),
    errorsBySeverity: new Map<ErrorSeverity, number>(),
    processingTime: 0,
    cacheHits: 0,
    cacheMisses: 0
  };

  // Pre-compiled error messages for performance
  private static readonly ERROR_MESSAGES = new Map<ErrorCode, string>([
    [ErrorCode.CONFIG_NOT_FOUND, 'Configuration file not found'],
    [ErrorCode.CONFIG_INVALID, 'Invalid configuration format'],
    [ErrorCode.CONFIG_PARSE_ERROR, 'Failed to parse configuration'],
    [ErrorCode.PERMISSION_DENIED, 'Permission denied'],
    [ErrorCode.FILE_NOT_FOUND, 'File not found'],
    [ErrorCode.NETWORK_ERROR, 'Network error occurred'],
    [ErrorCode.VALIDATION_ERROR, 'Validation failed'],
    [ErrorCode.RATE_LIMIT_EXCEEDED, 'Rate limit exceeded'],
    [ErrorCode.INTERNAL_ERROR, 'Internal error occurred'],
    [ErrorCode.UNKNOWN_ERROR, 'An unknown error occurred']
  ]);

  // Error recovery suggestions
  private static readonly ERROR_SUGGESTIONS = new Map<ErrorCode, string[]>([
    [ErrorCode.CONFIG_NOT_FOUND, [
      'Create a .devdocai.yml file in your project root',
      'Specify config path with --config flag',
      'Run `devdocai init` to create default configuration'
    ]],
    [ErrorCode.CONFIG_INVALID, [
      'Check YAML syntax for errors',
      'Validate against configuration schema',
      'Use `devdocai validate` to check configuration'
    ]],
    [ErrorCode.PERMISSION_DENIED, [
      'Check file permissions',
      'Run with appropriate privileges',
      'Ensure write access to output directory'
    ]],
    [ErrorCode.RATE_LIMIT_EXCEEDED, [
      'Wait before retrying',
      'Reduce request frequency',
      'Contact support for limit increase'
    ]]
  ]);

  constructor(config?: ErrorHandlerConfig) {
    this.mode = config?.mode || ErrorHandlerMode.BASIC;
    this.config = this.normalizeConfig(config);
    this.security = config?.security || new SecurityService({
      mode: this.getSecurityMode(this.mode)
    });

    // Setup batch processing if enabled
    if (this.config.performance.batchProcessing) {
      this.setupBatchProcessing();
    }
  }

  /**
   * Normalize configuration based on mode
   */
  private normalizeConfig(config?: ErrorHandlerConfig): Required<ErrorHandlerConfig> {
    const mode = config?.mode || ErrorHandlerMode.BASIC;
    const modeDefaults = this.getModeDefaults(mode);

    return {
      mode,
      security: config?.security || new SecurityService({
        mode: this.getSecurityMode(mode)
      }),
      performance: {
        caching: mode === ErrorHandlerMode.OPTIMIZED || mode === ErrorHandlerMode.ENTERPRISE,
        batchProcessing: mode === ErrorHandlerMode.OPTIMIZED || mode === ErrorHandlerMode.ENTERPRISE,
        asyncLogging: mode === ErrorHandlerMode.OPTIMIZED || mode === ErrorHandlerMode.ENTERPRISE,
        ...config?.performance
      },
      features: {
        stackTrace: mode !== ErrorHandlerMode.BASIC,
        suggestions: true,
        sanitization: mode === ErrorHandlerMode.SECURE || mode === ErrorHandlerMode.ENTERPRISE,
        audit: mode === ErrorHandlerMode.SECURE || mode === ErrorHandlerMode.ENTERPRISE,
        ...config?.features
      },
      recovery: {
        enabled: mode === ErrorHandlerMode.ENTERPRISE,
        strategies: config?.recovery?.strategies || new Map(),
        maxRetries: 3,
        ...config?.recovery
      }
    };
  }

  /**
   * Get mode-specific defaults
   */
  private getModeDefaults(mode: ErrorHandlerMode): Partial<ErrorHandlerConfig> {
    switch (mode) {
      case ErrorHandlerMode.BASIC:
        return {
          performance: { caching: false, batchProcessing: false },
          features: { stackTrace: false, sanitization: false, audit: false }
        };
      
      case ErrorHandlerMode.OPTIMIZED:
        return {
          performance: { caching: true, batchProcessing: true, asyncLogging: true },
          features: { stackTrace: true, suggestions: true }
        };
      
      case ErrorHandlerMode.SECURE:
        return {
          features: { stackTrace: true, sanitization: true, audit: true }
        };
      
      case ErrorHandlerMode.ENTERPRISE:
        return {
          performance: { caching: true, batchProcessing: true, asyncLogging: true },
          features: { stackTrace: true, sanitization: true, audit: true, suggestions: true },
          recovery: { enabled: true, maxRetries: 5 }
        };
      
      default:
        return {};
    }
  }

  /**
   * Map error handler mode to security mode
   */
  private getSecurityMode(mode: ErrorHandlerMode): SecurityMode {
    switch (mode) {
      case ErrorHandlerMode.BASIC:
        return SecurityMode.BASIC;
      case ErrorHandlerMode.OPTIMIZED:
        return SecurityMode.STANDARD;
      case ErrorHandlerMode.SECURE:
        return SecurityMode.SECURE;
      case ErrorHandlerMode.ENTERPRISE:
        return SecurityMode.ENTERPRISE;
      default:
        return SecurityMode.STANDARD;
    }
  }

  /**
   * Setup batch processing for async logging
   */
  private setupBatchProcessing(): void {
    this.batchTimer = setInterval(() => {
      if (this.errorQueue.length > 0) {
        this.processBatch();
      }
    }, 1000); // Process batch every second
  }

  /**
   * Handle an error with mode-based processing
   */
  async handle(error: Error | string, context?: ErrorContext): Promise<ProcessedError> {
    const startTime = Date.now();
    this.metrics.totalErrors++;

    try {
      // Create error key for caching
      const errorKey = this.createErrorKey(error, context);

      // Check cache if enabled
      if (this.config.performance.caching && this.errorCache.has(errorKey)) {
        this.metrics.cacheHits++;
        this.metrics.processingTime = Date.now() - startTime;
        return this.errorCache.get(errorKey)!;
      }
      this.metrics.cacheMisses++;

      // Process the error
      const processed = await this.processError(error, context);

      // Cache if enabled
      if (this.config.performance.caching) {
        this.errorCache.set(errorKey, processed);
      }

      // Add to batch queue if batch processing enabled
      if (this.config.performance.batchProcessing) {
        this.errorQueue.push(processed);
      } else {
        // Log immediately if not batching
        await this.logError(processed);
      }

      // Attempt recovery if enabled
      if (this.config.recovery.enabled && processed.code) {
        await this.attemptRecovery(processed);
      }

      this.metrics.processingTime = Date.now() - startTime;
      return processed;

    } catch (handlingError) {
      // Fallback error handling
      this.metrics.processingTime = Date.now() - startTime;
      return this.createFallbackError(error, handlingError);
    }
  }

  /**
   * Process an error
   */
  private async processError(error: Error | string, context?: ErrorContext): Promise<ProcessedError> {
    const errorMessage = typeof error === 'string' ? error : error.message;
    const errorStack = typeof error === 'object' ? error.stack : undefined;

    // Determine error code and severity
    const code = context?.code || this.detectErrorCode(errorMessage);
    const severity = context?.severity || this.determineSeverity(code);

    // Update metrics
    this.metrics.errorsByCode.set(code, (this.metrics.errorsByCode.get(code) || 0) + 1);
    this.metrics.errorsBySeverity.set(severity, (this.metrics.errorsBySeverity.get(severity) || 0) + 1);

    // Create processed error
    const processed: ProcessedError = {
      message: errorMessage,
      code,
      severity,
      context: {
        ...context,
        timestamp: new Date(),
        stack: this.config.features.stackTrace ? errorStack : undefined
      },
      sanitized: false
    };

    // Sanitize if enabled
    if (this.config.features.sanitization) {
      processed.message = await this.sanitizeMessage(processed.message);
      processed.sanitized = true;
      
      // Validate sanitized message
      const validation = await this.security.validate(processed.message, {
        type: 'error_message',
        context: 'error_sanitization'
      });
      
      if (!validation.valid) {
        processed.message = 'Error message contained invalid content';
      }
    }

    // Add suggestions if enabled
    if (this.config.features.suggestions) {
      processed.suggestions = this.getSuggestions(code);
    }

    // Create user-friendly and developer messages
    processed.userMessage = this.createUserMessage(processed);
    processed.developerMessage = this.createDeveloperMessage(processed);

    // Audit if enabled
    if (this.config.features.audit) {
      await this.security.audit('error_handled', {
        code,
        severity,
        module: context?.module,
        operation: context?.operation
      });
    }

    return processed;
  }

  /**
   * Detect error code from message
   */
  private detectErrorCode(message: string): ErrorCode {
    const lowercaseMessage = message.toLowerCase();
    
    if (lowercaseMessage.includes('config') && lowercaseMessage.includes('not found')) {
      return ErrorCode.CONFIG_NOT_FOUND;
    }
    if (lowercaseMessage.includes('config') && lowercaseMessage.includes('invalid')) {
      return ErrorCode.CONFIG_INVALID;
    }
    if (lowercaseMessage.includes('permission')) {
      return ErrorCode.PERMISSION_DENIED;
    }
    if (lowercaseMessage.includes('file') && lowercaseMessage.includes('not found')) {
      return ErrorCode.FILE_NOT_FOUND;
    }
    if (lowercaseMessage.includes('network')) {
      return ErrorCode.NETWORK_ERROR;
    }
    if (lowercaseMessage.includes('validation')) {
      return ErrorCode.VALIDATION_ERROR;
    }
    if (lowercaseMessage.includes('rate limit')) {
      return ErrorCode.RATE_LIMIT_EXCEEDED;
    }
    
    return ErrorCode.UNKNOWN_ERROR;
  }

  /**
   * Determine error severity
   */
  private determineSeverity(code: ErrorCode): ErrorSeverity {
    switch (code) {
      case ErrorCode.CONFIG_NOT_FOUND:
      case ErrorCode.FILE_NOT_FOUND:
        return ErrorSeverity.WARNING;
      
      case ErrorCode.CONFIG_INVALID:
      case ErrorCode.CONFIG_PARSE_ERROR:
      case ErrorCode.VALIDATION_ERROR:
        return ErrorSeverity.ERROR;
      
      case ErrorCode.PERMISSION_DENIED:
      case ErrorCode.RATE_LIMIT_EXCEEDED:
        return ErrorSeverity.ERROR;
      
      case ErrorCode.INTERNAL_ERROR:
        return ErrorSeverity.CRITICAL;
      
      default:
        return ErrorSeverity.ERROR;
    }
  }

  /**
   * Sanitize error message
   */
  private async sanitizeMessage(message: string): Promise<string> {
    // Remove sensitive patterns
    const patterns = [
      /api[_-]?key[s]?\s*[:=]\s*['"]?[\w-]+['"]?/gi,
      /password[s]?\s*[:=]\s*['"]?[\w-]+['"]?/gi,
      /token[s]?\s*[:=]\s*['"]?[\w-]+['"]?/gi,
      /\/home\/[\w-]+/g,
      /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g
    ];

    let sanitized = message;
    for (const pattern of patterns) {
      sanitized = sanitized.replace(pattern, '[REDACTED]');
    }

    return sanitized;
  }

  /**
   * Get suggestions for error code
   */
  private getSuggestions(code: ErrorCode): string[] {
    return UnifiedErrorHandler.ERROR_SUGGESTIONS.get(code) || [];
  }

  /**
   * Create user-friendly message
   */
  private createUserMessage(error: ProcessedError): string {
    const baseMessage = UnifiedErrorHandler.ERROR_MESSAGES.get(error.code) || error.message;
    
    if (error.suggestions && error.suggestions.length > 0) {
      return `${baseMessage}. Try: ${error.suggestions[0]}`;
    }
    
    return baseMessage;
  }

  /**
   * Create developer message
   */
  private createDeveloperMessage(error: ProcessedError): string {
    const parts = [
      `[${error.severity.toUpperCase()}]`,
      `Code: ${error.code}`,
      `Message: ${error.message}`
    ];

    if (error.context.module) {
      parts.push(`Module: ${error.context.module}`);
    }

    if (error.context.operation) {
      parts.push(`Operation: ${error.context.operation}`);
    }

    return parts.join(' | ');
  }

  /**
   * Create error key for caching
   */
  private createErrorKey(error: Error | string, context?: ErrorContext): string {
    const message = typeof error === 'string' ? error : error.message;
    const code = context?.code || '';
    const module = context?.module || '';
    return `${code}:${module}:${message}`;
  }

  /**
   * Log error
   */
  private async logError(error: ProcessedError): Promise<void> {
    const logEntry = {
      timestamp: error.context.timestamp,
      severity: error.severity,
      code: error.code,
      message: error.developerMessage,
      context: error.context
    };

    if (this.config.performance.asyncLogging) {
      // Async logging
      setImmediate(() => {
        console.error(JSON.stringify(logEntry));
      });
    } else {
      // Sync logging
      console.error(JSON.stringify(logEntry));
    }
  }

  /**
   * Process batch of errors
   */
  private async processBatch(): Promise<void> {
    const batch = [...this.errorQueue];
    this.errorQueue = [];

    // Log all errors in batch
    for (const error of batch) {
      await this.logError(error);
    }
  }

  /**
   * Attempt error recovery
   */
  private async attemptRecovery(error: ProcessedError): Promise<void> {
    const strategy = this.config.recovery.strategies?.get(error.code);
    
    if (!strategy) {
      return;
    }

    let retries = 0;
    const maxRetries = this.config.recovery.maxRetries || 3;

    while (retries < maxRetries) {
      try {
        await strategy();
        
        // Audit successful recovery
        if (this.config.features.audit) {
          await this.security.audit('error_recovered', {
            code: error.code,
            retries
          });
        }
        
        break;
      } catch (recoveryError) {
        retries++;
        
        if (retries >= maxRetries) {
          // Audit failed recovery
          if (this.config.features.audit) {
            await this.security.audit('error_recovery_failed', {
              code: error.code,
              retries,
              error: recoveryError.message
            });
          }
        }
      }
    }
  }

  /**
   * Create fallback error when handler itself fails
   */
  private createFallbackError(originalError: Error | string, handlingError: any): ProcessedError {
    return {
      message: 'Error handler encountered an error',
      code: ErrorCode.INTERNAL_ERROR,
      severity: ErrorSeverity.CRITICAL,
      context: {
        timestamp: new Date(),
        metadata: {
          originalError: typeof originalError === 'string' ? originalError : originalError.message,
          handlingError: handlingError.message
        }
      },
      sanitized: false,
      userMessage: 'An unexpected error occurred. Please try again.',
      developerMessage: `Error handler failed: ${handlingError.message}`
    };
  }

  /**
   * Get error metrics
   */
  getMetrics(): typeof this.metrics {
    return { ...this.metrics };
  }

  /**
   * Clear error cache
   */
  clearCache(): void {
    this.errorCache.clear();
  }

  /**
   * Update handler mode
   */
  updateMode(mode: ErrorHandlerMode): void {
    this.mode = mode;
    this.config = this.normalizeConfig({ ...this.config, mode });
    this.security.updateConfig({
      mode: this.getSecurityMode(mode)
    });
  }

  /**
   * Register recovery strategy
   */
  registerRecoveryStrategy(code: ErrorCode, strategy: () => Promise<void>): void {
    this.config.recovery.strategies?.set(code, strategy);
  }

  /**
   * Cleanup resources
   */
  async cleanup(): Promise<void> {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
    }
    
    // Process remaining batch
    if (this.errorQueue.length > 0) {
      await this.processBatch();
    }
    
    this.errorCache.clear();
    await this.security.cleanup();
  }
}

// Export factory function
export function createErrorHandler(config?: ErrorHandlerConfig): UnifiedErrorHandler {
  return new UnifiedErrorHandler(config);
}

// Export default instance
export const errorHandler = new UnifiedErrorHandler({ mode: ErrorHandlerMode.BASIC });