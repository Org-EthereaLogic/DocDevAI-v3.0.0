/**
 * ErrorHandler specific types
 * Module 1: Core Infrastructure - Error Management
 */

import { FormattedError, ErrorCategory } from '../../types/core';

// Re-export types that ErrorHandler needs
export { ErrorCategory } from '../../types/core';

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical'
}

export interface StructuredError extends Error {
  code: string;
  category: ErrorCategory;
  severity: ErrorSeverity;
  recoverable: boolean;
  context?: ErrorContext;
  timestamp?: Date;
  suggestions?: string[];
}

export interface ErrorHandlerOptions {
  logErrors?: boolean;
  throwOnUnrecoverable?: boolean;
  maxRetries?: number;
  maxHistorySize?: number;
  enableStackTrace?: boolean;
  enableSuggestions?: boolean;
  logToFile?: boolean;
  logFilePath?: string;
}

export interface IErrorHandler {
  /**
   * Handle an error and return formatted error information
   * @param error - The error to handle
   * @returns Formatted error with code, message, and suggestion
   */
  handle(error: Error): FormattedError;

  /**
   * Throw an error with a specific error code
   * @param code - Error code (1000-5999)
   * @param message - Error message
   * @throws Error with code and message
   */
  throwWithCode(code: string, message: string): never;

  /**
   * Check if an error is recoverable
   * @param error - The error to check
   * @returns True if error is recoverable
   */
  isRecoverable(error: Error): boolean;

  /**
   * Get suggestion for handling an error
   * @param code - Error code
   * @returns Suggestion text for handling the error
   */
  getSuggestion(code: string): string;

  /**
   * Register custom error handler for specific error codes
   * @param code - Error code or pattern
   * @param handler - Custom handler function
   */
  registerHandler(code: string | RegExp, handler: ErrorHandlerFunction): void;

  /**
   * Format error for logging
   * @param error - The error to format
   * @returns Formatted error string
   */
  formatForLogging(error: Error): string;
}

export type ErrorHandlerFunction = (error: Error) => FormattedError;

export interface ErrorCodeRange {
  category: ErrorCategory;
  start: number;
  end: number;
  description: string;
}

export interface ErrorContext {
  operation?: string;
  module?: string;
  input?: unknown;
  metadata?: Record<string, unknown>;
}

export interface DevDocAIError extends Error {
  code: string;
  category: ErrorCategory;
  recoverable: boolean;
  context?: ErrorContext;
  cause?: Error;
}