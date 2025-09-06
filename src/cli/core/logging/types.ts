/**
 * Logger specific types
 * Module 1: Core Infrastructure - Logging System
 */

import { LogLevel, LogContext, LogEntry } from '../../types/core';

// Re-export types from core
export { LogLevel, LogContext, LogEntry } from '../../types/core';

export interface ILogger {
  /**
   * Log debug message
   * @param message - The message to log
   * @param context - Optional context information
   */
  debug(message: string, context?: Partial<LogContext>): void;

  /**
   * Log info message
   * @param message - The message to log
   * @param context - Optional context information
   */
  info(message: string, context?: Partial<LogContext>): void;

  /**
   * Log warning message
   * @param message - The message to log
   * @param context - Optional context information
   */
  warn(message: string, context?: Partial<LogContext>): void;

  /**
   * Log error message
   * @param message - The message to log
   * @param error - Optional error object
   * @param context - Optional context information
   */
  error(message: string, error?: Error, context?: Partial<LogContext>): void;

  /**
   * Set the logging level
   * @param level - The log level to set
   */
  setLevel(level: LogLevel): void;

  /**
   * Get the current logging level
   * @returns Current log level
   */
  getLevel(): LogLevel;

  /**
   * Add a log transport
   * @param transport - The transport to add
   */
  addTransport(transport: LogTransportFunction): void;

  /**
   * Remove a log transport
   * @param name - The name of the transport to remove
   */
  removeTransport(name: string): void;

  /**
   * Create a child logger with additional context
   * @param context - Additional context for the child logger
   * @returns Child logger instance
   */
  child(context: Partial<LogContext>): ILogger;

  /**
   * Flush all pending log entries
   */
  flush(): Promise<void>;

  /**
   * Set correlation ID for request tracking
   * @param correlationId - The correlation ID
   */
  setCorrelationId(correlationId: string): void;
}

export type LogFilter = (entry: LogEntry) => boolean;
export type LogFormatterFunction = (entry: LogEntry) => string;
export type LogTransportFunction = (formatted: string, entry: LogEntry) => void;

export interface LoggerOptions {
  level?: LogLevel;
  format?: 'json' | 'pretty';
  timestamp?: boolean;
  colorize?: boolean;
  transports?: ('console' | 'file')[];
  filters?: LogFilter[];
  maxFileSize?: number;
  maxFiles?: number;
  filePath?: string;
}

export interface ConsoleTransport {
  name: 'console';
  enableColors: boolean;
  format: 'json' | 'text';
  write: LogTransportFunction;
}

export interface FileTransport {
  name: 'file';
  filepath: string;
  maxSize?: number;
  maxFiles?: number;
  compress?: boolean;
  write: LogTransportFunction;
}

export interface LogFormatter {
  format(entry: LogEntry): string;
}

export interface LogBuffer {
  entries: LogEntry[];
  maxSize: number;
  add(entry: LogEntry): void;
  flush(): LogEntry[];
  clear(): void;
}