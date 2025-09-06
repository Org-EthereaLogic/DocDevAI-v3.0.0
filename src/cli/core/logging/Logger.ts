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

export class Logger {
  private options: LoggerOptions;
  private transports: LogTransportFunction[] = [];
  private filters: LogFilter[] = [];
  private formatter: LogFormatter;
  private correlationId?: string;
  private context: LogContext = {};

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

    this.formatter = this.createFormatter();
    this.setupTransports();
    this.filters = options?.filters || [];
  }

  debug(message: string, meta?: any): void {
    this.log(LogLevel.DEBUG, message, meta);
  }

  info(message: string, meta?: any): void {
    this.log(LogLevel.INFO, message, meta);
  }

  warn(message: string, meta?: any): void {
    this.log(LogLevel.WARN, message, meta);
  }

  error(message: string, error?: Error | any, meta?: any): void {
    const errorMeta = error instanceof Error ? {
      error: {
        message: error.message,
        stack: error.stack,
        name: error.name
      },
      ...meta
    } : { ...error, ...meta };
    
    this.log(LogLevel.ERROR, message, errorMeta);
  }

  fatal(message: string, error?: Error | any, meta?: any): void {
    const errorMeta = error instanceof Error ? {
      error: {
        message: error.message,
        stack: error.stack,
        name: error.name
      },
      ...meta
    } : { ...error, ...meta };
    
    // Map 'fatal' to 'error' since LogLevel doesn't have 'fatal'
    this.log(LogLevel.ERROR, message, errorMeta);
  }

  setLevel(level: LogLevel): void {
    this.options.level = level;
  }

  setCorrelationId(id: string): void {
    this.correlationId = id;
  }

  setContext(context: LogContext): void {
    this.context = { ...this.context, ...context };
  }

  clearContext(): void {
    this.context = {};
    this.correlationId = undefined;
  }

  addFilter(filter: LogFilter): void {
    this.filters.push(filter);
  }

  addTransport(transport: LogTransportFunction): void {
    this.transports.push(transport);
  }

  child(context: LogContext): Logger {
    const childLogger = new Logger(this.options);
    childLogger.setContext({ ...this.context, ...context });
    if (this.correlationId) {
      childLogger.setCorrelationId(this.correlationId);
    }
    return childLogger;
  }

  private log(level: LogLevel, message: string, meta?: any): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const entry: LogEntry = {
      level,
      message,
      context: {
        timestamp: new Date().toISOString(),
        correlationId: this.correlationId || '',
        ...this.context,
        metadata: meta
      }
    };

    // Apply filters
    for (const filter of this.filters) {
      if (!filter(entry)) {
        return; // Skip this log entry
      }
    }

    // Format and send to transports
    const formatted = this.formatter.format(entry);
    for (const transport of this.transports) {
      transport(formatted, entry);
    }
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: LogLevel[] = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARN, LogLevel.ERROR];
    const currentLevelIndex = levels.indexOf(this.options.level || LogLevel.INFO);
    const messageLevelIndex = levels.indexOf(level);
    return messageLevelIndex >= currentLevelIndex;
  }

  private createFormatter(): LogFormatter {
    if (this.options.format === 'json') {
      return {
        format: (entry: LogEntry) => {
          const obj: any = {
            level: entry.level,
            message: entry.message,
            ...(this.options.timestamp && { timestamp: entry.context.timestamp }),
            ...(entry.context.correlationId && { correlationId: entry.context.correlationId }),
            ...(entry.context.metadata && { meta: entry.context.metadata })
          };
          return JSON.stringify(obj);
        }
      };
    } else {
      // Pretty format
      return {
        format: (entry: LogEntry) => {
        const parts: string[] = [];
        
        if (this.options.timestamp) {
          parts.push(chalk.gray(`[${entry.context.timestamp}]`));
        }
        
        const levelColor = this.getLevelColor(entry.level);
        parts.push(levelColor(`[${entry.level.toUpperCase()}]`));
        
        if (entry.context.correlationId) {
          parts.push(chalk.cyan(`[${entry.context.correlationId}]`));
        }
        
        parts.push(entry.message);
        
        if (entry.context.metadata) {
          parts.push(chalk.gray(JSON.stringify(entry.context.metadata, null, 2)));
        }
        
          return parts.join(' ');
        }
      };
    }
  }

  private setupTransports(): void {
    for (const transportType of this.options.transports!) {
      if (transportType === 'console') {
        this.transports.push(this.createConsoleTransport());
      } else if (transportType === 'file') {
        this.transports.push(this.createFileTransport());
      }
    }
  }

  private createConsoleTransport(): LogTransportFunction {
    return (formatted: string, entry: LogEntry) => {
      if (this.options.colorize && this.options.format === 'pretty') {
        console.log(formatted);
      } else if (entry.level === LogLevel.ERROR) {
        console.error(formatted);
      } else {
        console.log(formatted);
      }
    };
  }

  private createFileTransport(): LogTransportFunction {
    return (formatted: string, _entry: LogEntry) => {
      // Simple file logging for GREEN phase
      try {
        const logDir = path.dirname(this.options.filePath!);
        if (!fs.existsSync(logDir)) {
          fs.mkdirSync(logDir, { recursive: true });
        }
        
        fs.appendFileSync(this.options.filePath!, formatted + '\n');
        
        // Simple rotation check
        const stats = fs.statSync(this.options.filePath!);
        if (stats.size > this.options.maxFileSize!) {
          // Rotate file
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          const rotatedPath = this.options.filePath!.replace('.log', `-${timestamp}.log`);
          fs.renameSync(this.options.filePath!, rotatedPath);
        }
      } catch (error) {
        console.error('Failed to write to log file:', error);
      }
    };
  }

  private getLevelColor(level: LogLevel): typeof chalk {
    switch (level) {
      case LogLevel.DEBUG:
        return chalk.gray;
      case LogLevel.INFO:
        return chalk.blue;
      case LogLevel.WARN:
        return chalk.yellow;
      case LogLevel.ERROR:
        return chalk.red;
      default:
        return chalk.white;
    }
  }
}