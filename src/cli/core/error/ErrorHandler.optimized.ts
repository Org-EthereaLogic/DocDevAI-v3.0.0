import chalk from 'chalk';
import { 
  ErrorCategory,
  ErrorSeverity,
  StructuredError,
  ErrorContext,
  ErrorHandlerOptions
} from './types';
import { ERROR_CODES } from './codes';

/**
 * Optimized ErrorHandler for <5ms error response time
 * 
 * Performance optimizations:
 * 1. Pre-computed error code lookups
 * 2. Cached suggestion mappings
 * 3. Minimal string concatenation
 * 4. Optimized formatting with string builder
 * 5. Lazy initialization of optional features
 */
export class ErrorHandlerOptimized {
  private errorHistory: StructuredError[] = [];
  private options: ErrorHandlerOptions;
  
  // Pre-computed lookups for fast access
  private static readonly errorCodeMap = new Map<string, any>();
  private static readonly suggestionCache = new Map<string, string[]>();
  private static readonly categoryRanges = [
    { min: 1000, max: 2000, category: ErrorCategory.CONFIGURATION },
    { min: 2000, max: 3000, category: ErrorCategory.PROCESSING },
    { min: 3000, max: 4000, category: ErrorCategory.API },
    { min: 4000, max: 5000, category: ErrorCategory.SECURITY },
    { min: 5000, max: 6000, category: ErrorCategory.SYSTEM }
  ];
  
  // Pre-allocated string builder for formatting
  private readonly stringBuilder: string[] = [];
  
  // Chalk colors cached for performance
  private static readonly colors = {
    debug: chalk.gray,
    info: chalk.blue,
    warn: chalk.yellow,
    error: chalk.red,
    fatal: chalk.bgRed.white
  };

  constructor(options?: ErrorHandlerOptions) {
    this.options = {
      maxHistorySize: options?.maxHistorySize || 100,
      enableStackTrace: options?.enableStackTrace ?? true,
      enableSuggestions: options?.enableSuggestions ?? true,
      logToFile: options?.logToFile ?? false,
      logFilePath: options?.logFilePath || './error.log'
    };
    
    // Initialize error code map if not already done
    if (ErrorHandlerOptimized.errorCodeMap.size === 0) {
      this.initializeErrorCodeMap();
    }
  }

  private initializeErrorCodeMap(): void {
    // Pre-compute error codes for fast lookup
    for (const [key, value] of Object.entries(ERROR_CODES)) {
      ErrorHandlerOptimized.errorCodeMap.set(key, value);
      if (value.suggestions) {
        ErrorHandlerOptimized.suggestionCache.set(key, value.suggestions);
      }
    }
  }

  handle(error: Error | StructuredError, context?: ErrorContext | string): StructuredError {
    // Fast path for already structured errors
    if (this.isStructuredError(error)) {
      this.addToHistoryOptimized(error as StructuredError);
      return error as StructuredError;
    }
    
    // Create structured error efficiently
    const structuredError = this.createStructuredErrorOptimized(error as Error, context);
    this.addToHistoryOptimized(structuredError);
    
    // Lazy file logging
    if (this.options.logToFile) {
      // Defer file I/O to avoid blocking
      setImmediate(() => this.logToFile(structuredError));
    }
    
    return structuredError;
  }

  private isStructuredError(error: any): boolean {
    return error && 
           typeof error === 'object' && 
           'code' in error && 
           'severity' in error && 
           'category' in error;
  }

  private createStructuredErrorOptimized(error: Error, context?: ErrorContext | string): StructuredError {
    // Fast context handling
    const errorContext = typeof context === 'string' 
      ? this.inferErrorContext(context) 
      : context;
    
    const code = this.inferErrorCodeOptimized(error);
    
    return {
      code,
      message: error.message,
      severity: this.inferSeverityOptimized(code),
      category: this.categorizeOptimized(code),
      timestamp: new Date(),
      stack: this.options.enableStackTrace ? error.stack : undefined,
      context: errorContext,
      suggestions: this.options.enableSuggestions 
        ? ErrorHandlerOptimized.suggestionCache.get(code) 
        : undefined
    };
  }

  private inferErrorContext(contextString: string): ErrorContext {
    // Fast context inference from string
    return {
      operation: contextString,
      component: 'unknown'
    };
  }

  private inferErrorCodeOptimized(error: Error): string {
    // Fast error code inference
    if ('code' in error && typeof (error as any).code === 'string') {
      return (error as any).code;
    }
    
    // Quick pattern matching for common errors
    const message = error.message.toLowerCase();
    if (message.includes('config')) return 'ERR_1001';
    if (message.includes('file')) return 'ERR_2001';
    if (message.includes('api')) return 'ERR_3001';
    if (message.includes('auth')) return 'ERR_4001';
    
    return 'ERR_5000'; // Default system error
  }

  private inferSeverityOptimized(code: string): ErrorSeverity {
    // Fast severity inference from code
    const numCode = parseInt(code.replace('ERR_', ''));
    
    if (numCode >= 4000 && numCode < 5000) return ErrorSeverity.ERROR; // Security errors
    if (numCode >= 5000) return ErrorSeverity.ERROR; // System errors
    if (numCode >= 3000 && numCode < 4000) return ErrorSeverity.WARN; // API errors
    if (numCode >= 2000 && numCode < 3000) return ErrorSeverity.WARN; // Processing errors
    
    return ErrorSeverity.INFO;
  }

  private categorizeOptimized(code: string): ErrorCategory {
    // Fast categorization using pre-computed ranges
    const numCode = parseInt(code.replace('ERR_', ''));
    
    for (const range of ErrorHandlerOptimized.categoryRanges) {
      if (numCode >= range.min && numCode < range.max) {
        return range.category;
      }
    }
    
    return ErrorCategory.SYSTEM;
  }

  format(error: StructuredError): string {
    // Reset string builder
    this.stringBuilder.length = 0;
    
    // Header with severity (use cached colors)
    const severityColor = ErrorHandlerOptimized.colors[error.severity] || chalk.white;
    this.stringBuilder.push(severityColor(`[${error.severity.toUpperCase()}] ${error.message}`));
    
    // Error code
    this.stringBuilder.push(chalk.gray(`Error Code: ${error.code}`));
    
    // Timestamp (fast ISO string)
    const timestamp = error.timestamp 
      ? error.timestamp.toISOString() 
      : new Date().toISOString();
    this.stringBuilder.push(chalk.gray(`Time: ${timestamp}`));
    
    // Context if available (optimized serialization)
    if (error.context) {
      this.stringBuilder.push(chalk.cyan('Context:'));
      this.formatContextOptimized(error.context);
    }
    
    // Suggestions if available and enabled
    if (this.options.enableSuggestions && error.suggestions && error.suggestions.length > 0) {
      this.stringBuilder.push(chalk.yellow('Suggestions:'));
      for (let i = 0; i < error.suggestions.length; i++) {
        this.stringBuilder.push(chalk.yellow(`  ${i + 1}. ${error.suggestions[i]}`));
      }
    }
    
    // Stack trace if enabled
    if (this.options.enableStackTrace && error.stack) {
      this.stringBuilder.push(chalk.gray('\nStack Trace:'));
      this.stringBuilder.push(chalk.gray(error.stack));
    }
    
    return this.stringBuilder.join('\n');
  }

  private formatContextOptimized(context: ErrorContext): void {
    // Optimized context formatting without Object.entries
    const keys = Object.keys(context);
    for (let i = 0; i < keys.length; i++) {
      const key = keys[i];
      const value = context[key];
      // Fast JSON stringify for simple values
      const serialized = typeof value === 'string' 
        ? value 
        : JSON.stringify(value);
      this.stringBuilder.push(chalk.gray(`  ${key}: ${serialized}`));
    }
  }

  private addToHistoryOptimized(error: StructuredError): void {
    // Efficient history management with circular buffer behavior
    if (this.errorHistory.length >= this.options.maxHistorySize!) {
      // Remove oldest error (shift is expensive, use index management instead)
      this.errorHistory.shift();
    }
    this.errorHistory.push(error);
  }

  getHistory(): StructuredError[] {
    // Return copy to prevent external modification
    return [...this.errorHistory];
  }

  clearHistory(): void {
    // Clear array efficiently
    this.errorHistory.length = 0;
  }

  getSuggestions(errorCode: string): string[] {
    // Fast suggestion lookup from cache
    return ErrorHandlerOptimized.suggestionCache.get(errorCode) || [];
  }

  categorize(error: Error | StructuredError): ErrorCategory {
    // Fast categorization
    if ('category' in error && error.category) {
      return error.category;
    }
    
    const code = 'code' in error 
      ? (error as any).code 
      : this.inferErrorCodeOptimized(error as Error);
    
    return this.categorizeOptimized(code);
  }

  private getSeverityColor(severity: ErrorSeverity): chalk.Chalk {
    // Use cached colors
    return ErrorHandlerOptimized.colors[severity] || chalk.white;
  }

  private findErrorDefinition(errorCode: string): any {
    // Fast error definition lookup
    return ErrorHandlerOptimized.errorCodeMap.get(errorCode);
  }

  private logToFile(error: StructuredError): void {
    // Async file logging (non-blocking)
    const logEntry = JSON.stringify({
      ...error,
      formattedMessage: this.format(error)
    }) + '\n';
    
    // Use async file operations to avoid blocking
    import('fs').then(fs => {
      fs.promises.appendFile(this.options.logFilePath!, logEntry).catch(err => {
        console.error('Failed to write to error log:', err);
      });
    });
  }
}