import chalk from 'chalk';
import { 
  ErrorCategory,
  ErrorSeverity,
  StructuredError,
  ErrorContext,
  ErrorHandlerOptions
} from './types';
import { ERROR_CODES } from './codes';

export class ErrorHandler {
  private errorHistory: StructuredError[] = [];
  private options: ErrorHandlerOptions;

  constructor(options?: ErrorHandlerOptions) {
    this.options = {
      maxHistorySize: options?.maxHistorySize || 100,
      enableStackTrace: options?.enableStackTrace ?? true,
      enableSuggestions: options?.enableSuggestions ?? true,
      logToFile: options?.logToFile ?? false,
      logFilePath: options?.logFilePath || './error.log'
    };
  }

  handle(error: Error | StructuredError, context?: ErrorContext): StructuredError {
    const structuredError = this.createStructuredError(error, context);
    this.addToHistory(structuredError);
    
    if (this.options.logToFile) {
      this.logToFile(structuredError);
    }
    
    return structuredError;
  }

  format(error: StructuredError): string {
    const parts: string[] = [];
    
    // Header with severity
    const severityColor = this.getSeverityColor(error.severity);
    parts.push(severityColor(`[${error.severity.toUpperCase()}] ${error.message}`));
    
    // Error code
    parts.push(chalk.gray(`Error Code: ${error.code}`));
    
    // Timestamp
    parts.push(chalk.gray(`Time: ${error.timestamp ? error.timestamp.toISOString() : new Date().toISOString()}`));
    
    // Context if available
    if (error.context) {
      parts.push(chalk.cyan('Context:'));
      for (const [key, value] of Object.entries(error.context)) {
        parts.push(chalk.gray(`  ${key}: ${JSON.stringify(value)}`));
      }
    }
    
    // Suggestions if available and enabled
    if (this.options.enableSuggestions && error.suggestions && error.suggestions.length > 0) {
      parts.push(chalk.yellow('Suggestions:'));
      error.suggestions.forEach((suggestion: any, index: number) => {
        parts.push(chalk.yellow(`  ${index + 1}. ${suggestion}`));
      });
    }
    
    // Stack trace if enabled
    if (this.options.enableStackTrace && error.stack) {
      parts.push(chalk.gray('\nStack Trace:'));
      parts.push(chalk.gray(error.stack));
    }
    
    return parts.join('\n');
  }

  getHistory(): StructuredError[] {
    return [...this.errorHistory];
  }

  clearHistory(): void {
    this.errorHistory = [];
  }

  getSuggestions(errorCode: string): string[] {
    const errorDef = this.findErrorDefinition(errorCode);
    return errorDef?.suggestions || [];
  }

  categorize(error: Error | StructuredError): ErrorCategory {
    if ('category' in error && error.category) {
      return error.category;
    }
    
    const code = 'code' in error ? error.code : this.inferErrorCode(error);
    const numCode = parseInt(code);
    
    if (numCode >= 1000 && numCode < 2000) return ErrorCategory.CONFIGURATION;
    if (numCode >= 2000 && numCode < 3000) return ErrorCategory.PROCESSING;
    if (numCode >= 3000 && numCode < 4000) return ErrorCategory.API;
    if (numCode >= 4000 && numCode < 5000) return ErrorCategory.SECURITY;
    if (numCode >= 5000 && numCode < 6000) return ErrorCategory.SYSTEM;
    
    return ErrorCategory.SYSTEM;
  }

  private createStructuredError(error: Error | StructuredError, context?: ErrorContext): StructuredError {
    if (this.isStructuredError(error)) {
      return {
        ...error,
        context: context || error.context,
        timestamp: error.timestamp || new Date()
      };
    }
    
    const code = this.inferErrorCode(error);
    const errorDef = this.findErrorDefinition(code);
    
    const structuredError: StructuredError = Object.assign(new Error(error.message || errorDef?.message || 'Unknown error'), {
      name: 'StructuredError',
      code,
      severity: errorDef?.severity || ErrorSeverity.MEDIUM,
      category: this.categorize(error),
      timestamp: new Date(),
      stack: error.stack,
      context,
      suggestions: errorDef?.suggestions,
      recoverable: errorDef?.recoverable || false
    });
    return structuredError;
  }

  private isStructuredError(error: any): error is StructuredError {
    return error && 
           typeof error === 'object' && 
           'code' in error && 
           'severity' in error && 
           'category' in error;
  }

  private inferErrorCode(error: Error): string {
    // Check if error has a code property
    if ('code' in error && typeof (error as any).code === 'string') {
      return (error as any).code;
    }
    
    // Try to infer from message
    const message = error.message.toLowerCase();
    
    if (message.includes('config')) return '1000';
    if (message.includes('file') || message.includes('enoent')) return '2001';
    if (message.includes('network') || message.includes('fetch')) return '3000';
    if (message.includes('validation') || message.includes('invalid')) return '4000';
    
    return '5000'; // Default to runtime error
  }

  private findErrorDefinition(code: string): any {
    for (const category of Object.values(ERROR_CODES)) {
      for (const [errorCode, errorDef] of Object.entries(category)) {
        if (errorCode === code) {
          return errorDef;
        }
      }
    }
    return null;
  }

  private addToHistory(error: StructuredError): void {
    this.errorHistory.push(error);
    
    // Trim history if it exceeds max size
    if (this.errorHistory.length > this.options.maxHistorySize!) {
      this.errorHistory = this.errorHistory.slice(-this.options.maxHistorySize!);
    }
  }

  private logToFile(error: StructuredError): void {
    // Simple implementation for GREEN phase - just console.log for now
    // In production, would write to actual file
    if (this.options.logToFile) {
      const logEntry = {
        timestamp: error.timestamp ? error.timestamp.toISOString() : new Date().toISOString(),
        code: error.code,
        message: error.message,
        severity: error.severity,
        category: error.category,
        context: error.context
      };
      // In GREEN phase, just simulate file logging
      console.error('[File Log]', JSON.stringify(logEntry));
    }
  }

  private getSeverityColor(severity: ErrorSeverity): typeof chalk {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
        return chalk.red.bold;
      case ErrorSeverity.HIGH:
        return chalk.red;
      case ErrorSeverity.MEDIUM:
        return chalk.yellow;
      case ErrorSeverity.LOW:
        return chalk.blue;
      default:
        return chalk.white;
    }
  }
}