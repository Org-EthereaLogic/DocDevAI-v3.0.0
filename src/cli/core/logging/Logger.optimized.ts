import chalk from 'chalk';
import * as fs from 'fs';
import * as path from 'path';
import { LogLevel, LogEntry } from '../../types/core';
import { 
  LoggerOptions, 
  LogFormatter,
  LogTransportFunction,
  LogFilter
} from './types';

type LogContext = Record<string, any>;

/**
 * Optimized Logger for high-throughput logging (>10,000 logs/sec)
 * 
 * Performance optimizations:
 * 1. Async/buffered logging to prevent I/O blocking
 * 2. Object pooling for log entries
 * 3. Minimal string concatenation
 * 4. Batched file writes
 * 5. Optimized JSON serialization
 * 6. Level checking before processing
 */
export class LoggerOptimized {
  private options: LoggerOptions;
  private transports: LogTransportFunction[] = [];
  private filters: LogFilter[] = [];
  private formatter: LogFormatter;
  private correlationId?: string;
  private context: LogContext = {};
  
  // Performance optimizations
  private readonly levelValues: Map<LogLevel, number>;
  private currentLevelValue: number;
  
  // Buffer for batched file writes
  private fileBuffer: string[] = [];
  private fileBufferSize = 0;
  private readonly MAX_BUFFER_SIZE = 8192; // 8KB buffer
  private flushTimer?: NodeJS.Timeout;
  private fileStream?: fs.WriteStream;
  
  // Object pool for log entries
  private readonly entryPool: LogEntry[] = [];
  private readonly MAX_POOL_SIZE = 100;
  
  // Pre-allocated timestamp buffer
  private readonly timestampBuffer = new Date();
  
  // Cached chalk functions
  private static readonly colors = {
    debug: chalk.gray,
    info: chalk.blue,
    warn: chalk.yellow,
    error: chalk.red
  };

  constructor(options?: LoggerOptions) {
    this.options = {
      level: options?.level || LogLevel.INFO,
      format: options?.format || 'json',
      timestamp: options?.timestamp ?? true,
      colorize: options?.colorize ?? true,
      transports: options?.transports || ['console'],
      filters: options?.filters || [],
      maxFileSize: options?.maxFileSize || 10 * 1024 * 1024, // 10MB
      maxFiles: options?.maxFiles || 5,
      filePath: options?.filePath || './logs/app.log'
    };

    // Initialize level values for fast comparison
    this.levelValues = new Map([
      [LogLevel.DEBUG, 0],
      [LogLevel.INFO, 1],
      [LogLevel.WARN, 2],
      [LogLevel.ERROR, 3]
    ]);
    
    this.currentLevelValue = this.levelValues.get(this.options.level) || 1;
    
    this.formatter = this.createOptimizedFormatter();
    this.setupOptimizedTransports();
    this.filters = options?.filters || [];
    
    // Setup file stream if file transport is enabled
    if (this.options.transports?.includes('file')) {
      this.setupFileStream();
    }
  }

  private setupFileStream(): void {
    const logDir = path.dirname(this.options.filePath!);
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
    
    this.fileStream = fs.createWriteStream(this.options.filePath!, {
      flags: 'a',
      highWaterMark: 64 * 1024 // 64KB buffer
    });
  }

  debug(message: string, meta?: any): void {
    if (this.currentLevelValue > 0) return; // Fast level check
    this.logOptimized(LogLevel.DEBUG, message, meta);
  }

  info(message: string, meta?: any): void {
    if (this.currentLevelValue > 1) return; // Fast level check
    this.logOptimized(LogLevel.INFO, message, meta);
  }

  warn(message: string, meta?: any): void {
    if (this.currentLevelValue > 2) return; // Fast level check
    this.logOptimized(LogLevel.WARN, message, meta);
  }

  error(message: string, error?: Error | any, meta?: any): void {
    const errorMeta = this.createErrorMeta(error, meta);
    this.logOptimized(LogLevel.ERROR, message, errorMeta);
  }

  fatal(message: string, error?: Error | any, meta?: any): void {
    const errorMeta = this.createErrorMeta(error, meta);
    this.logOptimized(LogLevel.ERROR, message, errorMeta);
  }

  private createErrorMeta(error?: Error | any, meta?: any): any {
    if (error instanceof Error) {
      // Optimized error metadata creation
      return {
        error: {
          message: error.message,
          stack: error.stack,
          name: error.name
        },
        ...meta
      };
    }
    return { ...error, ...meta };
  }

  private logOptimized(level: LogLevel, message: string, meta?: any): void {
    // Apply filters efficiently
    for (let i = 0; i < this.filters.length; i++) {
      if (!this.filters[i]({ level, message, meta })) {
        return;
      }
    }
    
    // Get or create log entry from pool
    const entry = this.getPooledEntry();
    
    // Populate entry
    entry.level = level;
    entry.message = message;
    entry.timestamp = this.options.timestamp ? new Date() : undefined;
    entry.correlationId = this.correlationId;
    entry.context = this.context;
    entry.meta = meta;
    
    // Format and transport
    const formatted = this.formatter(entry);
    
    // Execute transports
    for (let i = 0; i < this.transports.length; i++) {
      this.transports[i](formatted, entry);
    }
    
    // Return entry to pool
    this.returnToPool(entry);
  }

  private getPooledEntry(): LogEntry {
    // Get entry from pool or create new one
    if (this.entryPool.length > 0) {
      return this.entryPool.pop()!;
    }
    
    return {
      level: LogLevel.INFO,
      message: '',
      timestamp: undefined,
      correlationId: undefined,
      context: undefined,
      meta: undefined
    };
  }

  private returnToPool(entry: LogEntry): void {
    // Clear entry and return to pool
    if (this.entryPool.length < this.MAX_POOL_SIZE) {
      entry.message = '';
      entry.meta = undefined;
      entry.context = undefined;
      entry.correlationId = undefined;
      this.entryPool.push(entry);
    }
  }

  private createOptimizedFormatter(): LogFormatter {
    if (this.options.format === 'json') {
      return this.jsonFormatterOptimized.bind(this);
    }
    
    return this.textFormatterOptimized.bind(this);
  }

  private jsonFormatterOptimized(entry: LogEntry): string {
    // Fast JSON serialization with minimal allocations
    const obj: any = {
      level: entry.level,
      message: entry.message
    };
    
    if (entry.timestamp) {
      obj.timestamp = entry.timestamp.toISOString();
    }
    
    if (entry.correlationId) {
      obj.correlationId = entry.correlationId;
    }
    
    if (entry.context && Object.keys(entry.context).length > 0) {
      obj.context = entry.context;
    }
    
    if (entry.meta) {
      obj.meta = entry.meta;
    }
    
    return JSON.stringify(obj);
  }

  private textFormatterOptimized(entry: LogEntry): string {
    // Optimized text formatting with string builder
    const parts: string[] = [];
    
    if (entry.timestamp) {
      parts.push(`[${entry.timestamp.toISOString()}]`);
    }
    
    // Use cached colors
    const color = this.options.colorize 
      ? LoggerOptimized.colors[entry.level] || chalk.white
      : (x: string) => x;
    
    parts.push(color(`[${entry.level.toUpperCase()}]`));
    parts.push(entry.message);
    
    if (entry.correlationId) {
      parts.push(`[${entry.correlationId}]`);
    }
    
    if (entry.meta) {
      parts.push(JSON.stringify(entry.meta));
    }
    
    return parts.join(' ');
  }

  private setupOptimizedTransports(): void {
    this.transports = [];
    
    if (this.options.transports?.includes('console')) {
      this.transports.push(this.consoleTransportOptimized.bind(this));
    }
    
    if (this.options.transports?.includes('file')) {
      this.transports.push(this.fileTransportOptimized.bind(this));
    }
  }

  private consoleTransportOptimized(formatted: string, entry: LogEntry): void {
    // Direct console output for speed
    if (entry.level === LogLevel.ERROR) {
      console.error(formatted);
    } else {
      console.log(formatted);
    }
  }

  private fileTransportOptimized(formatted: string, entry: LogEntry): void {
    // Buffer writes for better I/O performance
    const line = formatted + '\n';
    this.fileBuffer.push(line);
    this.fileBufferSize += line.length;
    
    // Flush if buffer is full
    if (this.fileBufferSize >= this.MAX_BUFFER_SIZE) {
      this.flushFileBuffer();
    } else {
      // Schedule flush if not already scheduled
      if (!this.flushTimer) {
        this.flushTimer = setTimeout(() => this.flushFileBuffer(), 100);
      }
    }
  }

  private flushFileBuffer(): void {
    if (this.fileBuffer.length === 0) return;
    
    if (this.fileStream && !this.fileStream.destroyed) {
      const data = this.fileBuffer.join('');
      this.fileStream.write(data);
    }
    
    // Reset buffer
    this.fileBuffer = [];
    this.fileBufferSize = 0;
    
    // Clear timer
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = undefined;
    }
  }

  setLevel(level: LogLevel): void {
    this.options.level = level;
    this.currentLevelValue = this.levelValues.get(level) || 1;
  }

  setCorrelationId(id: string): void {
    this.correlationId = id;
  }

  setContext(context: LogContext): void {
    // Shallow merge for speed
    Object.assign(this.context, context);
  }

  clearContext(): void {
    // Clear context efficiently
    const keys = Object.keys(this.context);
    for (let i = 0; i < keys.length; i++) {
      delete this.context[keys[i]];
    }
    this.correlationId = undefined;
  }

  addFilter(filter: LogFilter): void {
    this.filters.push(filter);
  }

  addTransport(transport: LogTransportFunction): void {
    this.transports.push(transport);
  }

  removeTransport(transport: LogTransportFunction): void {
    const index = this.transports.indexOf(transport);
    if (index !== -1) {
      this.transports.splice(index, 1);
    }
  }

  flush(): Promise<void> {
    return new Promise((resolve) => {
      this.flushFileBuffer();
      if (this.fileStream) {
        this.fileStream.end(() => resolve());
      } else {
        resolve();
      }
    });
  }

  close(): void {
    // Flush and close file stream
    this.flushFileBuffer();
    if (this.fileStream) {
      this.fileStream.end();
      this.fileStream = undefined;
    }
    
    // Clear timers
    if (this.flushTimer) {
      clearTimeout(this.flushTimer);
      this.flushTimer = undefined;
    }
  }
}