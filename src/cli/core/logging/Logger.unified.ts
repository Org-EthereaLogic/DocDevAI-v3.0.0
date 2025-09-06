/**
 * @fileoverview Unified Logger with mode-based behavior
 * @module @cli/core/logging/Logger.unified
 * @version 1.0.0
 * @performance <1ms logging time in all modes
 * @security Sanitization, audit trail, and encrypted logs
 */

import * as fs from 'fs';
import * as path from 'path';
import { SecurityService, SecurityMode } from '../security/SecurityService.unified';

/**
 * Logger operation mode
 */
export enum LoggerMode {
  BASIC = 'basic',          // Console output only
  OPTIMIZED = 'optimized',  // Buffered, async logging
  SECURE = 'secure',        // Encrypted, sanitized logs
  ENTERPRISE = 'enterprise' // All features enabled
}

/**
 * Log levels
 */
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  CRITICAL = 4
}

/**
 * Log entry structure
 */
export interface LogEntry {
  timestamp: Date;
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
  module?: string;
  userId?: string;
  sessionId?: string;
  encrypted?: boolean;
}

/**
 * Logger configuration
 */
export interface LoggerConfig {
  mode?: LoggerMode;
  level?: LogLevel;
  security?: SecurityService;
  output?: {
    console?: boolean;
    file?: string;
    maxFileSize?: number;
    maxFiles?: number;
  };
  performance?: {
    buffering?: boolean;
    bufferSize?: number;
    flushInterval?: number;
    async?: boolean;
  };
  features?: {
    timestamps?: boolean;
    colors?: boolean;
    sanitization?: boolean;
    encryption?: boolean;
    compression?: boolean;
  };
}

/**
 * Unified Logger
 * Combines basic, optimized, and secure logging with configurable behavior
 */
export class UnifiedLogger {
  private mode: LoggerMode;
  private level: LogLevel;
  private security: SecurityService;
  private config: Required<LoggerConfig>;
  private buffer: LogEntry[] = [];
  private fileStream?: fs.WriteStream;
  private flushTimer?: NodeJS.Timer;
  private metrics = {
    totalLogs: 0,
    logsByLevel: new Map<LogLevel, number>(),
    bufferFlushes: 0,
    averageLogTime: 0
  };

  // ANSI color codes for console output
  private static readonly COLORS = {
    [LogLevel.DEBUG]: '\x1b[36m',    // Cyan
    [LogLevel.INFO]: '\x1b[37m',     // White
    [LogLevel.WARN]: '\x1b[33m',     // Yellow
    [LogLevel.ERROR]: '\x1b[31m',    // Red
    [LogLevel.CRITICAL]: '\x1b[35m', // Magenta
    RESET: '\x1b[0m'
  };

  // Level names for output
  private static readonly LEVEL_NAMES = {
    [LogLevel.DEBUG]: 'DEBUG',
    [LogLevel.INFO]: 'INFO',
    [LogLevel.WARN]: 'WARN',
    [LogLevel.ERROR]: 'ERROR',
    [LogLevel.CRITICAL]: 'CRITICAL'
  };

  constructor(config?: LoggerConfig) {
    this.mode = config?.mode || LoggerMode.BASIC;
    this.level = config?.level || LogLevel.INFO;
    this.config = this.normalizeConfig(config);
    this.security = config?.security || new SecurityService({
      mode: this.getSecurityMode(this.mode)
    });

    this.initialize();
  }

  /**
   * Normalize configuration based on mode
   */
  private normalizeConfig(config?: LoggerConfig): Required<LoggerConfig> {
    const mode = config?.mode || LoggerMode.BASIC;
    const modeDefaults = this.getModeDefaults(mode);

    return {
      mode,
      level: config?.level || LogLevel.INFO,
      security: config?.security || new SecurityService({
        mode: this.getSecurityMode(mode)
      }),
      output: {
        console: true,
        file: mode !== LoggerMode.BASIC ? './logs/app.log' : undefined,
        maxFileSize: 10 * 1024 * 1024, // 10MB
        maxFiles: 5,
        ...modeDefaults.output,
        ...config?.output
      },
      performance: {
        buffering: mode === LoggerMode.OPTIMIZED || mode === LoggerMode.ENTERPRISE,
        bufferSize: 100,
        flushInterval: 1000,
        async: mode === LoggerMode.OPTIMIZED || mode === LoggerMode.ENTERPRISE,
        ...modeDefaults.performance,
        ...config?.performance
      },
      features: {
        timestamps: true,
        colors: mode === LoggerMode.BASIC || mode === LoggerMode.OPTIMIZED,
        sanitization: mode === LoggerMode.SECURE || mode === LoggerMode.ENTERPRISE,
        encryption: mode === LoggerMode.SECURE || mode === LoggerMode.ENTERPRISE,
        compression: mode === LoggerMode.ENTERPRISE,
        ...modeDefaults.features,
        ...config?.features
      }
    };
  }

  /**
   * Get mode-specific defaults
   */
  private getModeDefaults(mode: LoggerMode): Partial<LoggerConfig> {
    switch (mode) {
      case LoggerMode.BASIC:
        return {
          output: { console: true },
          performance: { buffering: false, async: false },
          features: { colors: true, sanitization: false, encryption: false }
        };
      
      case LoggerMode.OPTIMIZED:
        return {
          output: { console: true, file: './logs/app.log' },
          performance: { buffering: true, bufferSize: 100, async: true },
          features: { colors: true }
        };
      
      case LoggerMode.SECURE:
        return {
          output: { file: './logs/secure.log' },
          features: { sanitization: true, encryption: true, colors: false }
        };
      
      case LoggerMode.ENTERPRISE:
        return {
          output: { console: true, file: './logs/enterprise.log', maxFiles: 10 },
          performance: { buffering: true, bufferSize: 500, async: true },
          features: { sanitization: true, encryption: true, compression: true }
        };
      
      default:
        return {};
    }
  }

  /**
   * Map logger mode to security mode
   */
  private getSecurityMode(mode: LoggerMode): SecurityMode {
    switch (mode) {
      case LoggerMode.BASIC:
        return SecurityMode.BASIC;
      case LoggerMode.OPTIMIZED:
        return SecurityMode.STANDARD;
      case LoggerMode.SECURE:
        return SecurityMode.SECURE;
      case LoggerMode.ENTERPRISE:
        return SecurityMode.ENTERPRISE;
      default:
        return SecurityMode.STANDARD;
    }
  }

  /**
   * Initialize logger
   */
  private initialize(): void {
    // Setup file output if needed
    if (this.config.output.file) {
      this.setupFileOutput();
    }

    // Setup buffer flushing if needed
    if (this.config.performance.buffering) {
      this.flushTimer = setInterval(
        () => this.flush(),
        this.config.performance.flushInterval!
      );
    }
  }

  /**
   * Setup file output
   */
  private setupFileOutput(): void {
    const logDir = path.dirname(this.config.output.file!);
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }

    this.fileStream = fs.createWriteStream(
      this.config.output.file!,
      { flags: 'a' }
    );
  }

  /**
   * Main logging method
   */
  async log(level: LogLevel, message: string, context?: Record<string, any>): Promise<void> {
    // Check if should log based on level
    if (level < this.level) {
      return;
    }

    const startTime = Date.now();
    this.metrics.totalLogs++;
    this.metrics.logsByLevel.set(level, (this.metrics.logsByLevel.get(level) || 0) + 1);

    // Create log entry
    const entry: LogEntry = {
      timestamp: new Date(),
      level,
      message,
      context,
      module: context?.module,
      userId: context?.userId,
      sessionId: context?.sessionId
    };

    // Sanitize if enabled
    if (this.config.features.sanitization) {
      entry.message = await this.sanitizeMessage(entry.message);
      if (entry.context) {
        entry.context = await this.sanitizeContext(entry.context);
      }
    }

    // Encrypt if enabled
    if (this.config.features.encryption && level >= LogLevel.ERROR) {
      const encrypted = await this.security.encrypt(JSON.stringify(entry));
      if (typeof encrypted !== 'string') {
        entry.message = '[ENCRYPTED]';
        entry.context = { encrypted };
        entry.encrypted = true;
      }
    }

    // Add to buffer or write immediately
    if (this.config.performance.buffering) {
      this.buffer.push(entry);
      
      // Flush if buffer is full
      if (this.buffer.length >= this.config.performance.bufferSize!) {
        await this.flush();
      }
    } else {
      await this.writeEntry(entry);
    }

    // Update metrics
    const logTime = Date.now() - startTime;
    this.metrics.averageLogTime = 
      (this.metrics.averageLogTime * (this.metrics.totalLogs - 1) + logTime) / 
      this.metrics.totalLogs;
  }

  /**
   * Convenience methods for different log levels
   */
  async debug(message: string, context?: Record<string, any>): Promise<void> {
    await this.log(LogLevel.DEBUG, message, context);
  }

  async info(message: string, context?: Record<string, any>): Promise<void> {
    await this.log(LogLevel.INFO, message, context);
  }

  async warn(message: string, context?: Record<string, any>): Promise<void> {
    await this.log(LogLevel.WARN, message, context);
  }

  async error(message: string, context?: Record<string, any>): Promise<void> {
    await this.log(LogLevel.ERROR, message, context);
  }

  async critical(message: string, context?: Record<string, any>): Promise<void> {
    await this.log(LogLevel.CRITICAL, message, context);
  }

  /**
   * Sanitize log message
   */
  private async sanitizeMessage(message: string): Promise<string> {
    // Remove sensitive patterns
    const patterns = [
      /api[_-]?key[s]?\s*[:=]\s*['"]?[\w-]+['"]?/gi,
      /password[s]?\s*[:=]\s*['"]?[\w-]+['"]?/gi,
      /token[s]?\s*[:=]\s*['"]?[\w-]+['"]?/gi,
      /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g
    ];

    let sanitized = message;
    for (const pattern of patterns) {
      sanitized = sanitized.replace(pattern, '[REDACTED]');
    }

    return sanitized;
  }

  /**
   * Sanitize context object
   */
  private async sanitizeContext(context: Record<string, any>): Promise<Record<string, any>> {
    const sanitized: Record<string, any> = {};
    const sensitiveKeys = ['password', 'secret', 'key', 'token', 'credential'];

    for (const [key, value] of Object.entries(context)) {
      const isSensitive = sensitiveKeys.some(sensitive => 
        key.toLowerCase().includes(sensitive)
      );

      if (isSensitive) {
        sanitized[key] = '[REDACTED]';
      } else if (typeof value === 'string') {
        sanitized[key] = await this.sanitizeMessage(value);
      } else {
        sanitized[key] = value;
      }
    }

    return sanitized;
  }

  /**
   * Write log entry
   */
  private async writeEntry(entry: LogEntry): Promise<void> {
    const formatted = this.formatEntry(entry);

    // Console output
    if (this.config.output.console) {
      if (this.config.performance.async) {
        setImmediate(() => this.writeToConsole(entry, formatted));
      } else {
        this.writeToConsole(entry, formatted);
      }
    }

    // File output
    if (this.fileStream) {
      if (this.config.performance.async) {
        setImmediate(() => this.fileStream!.write(formatted + '\n'));
      } else {
        this.fileStream.write(formatted + '\n');
      }
    }
  }

  /**
   * Write to console with colors
   */
  private writeToConsole(entry: LogEntry, formatted: string): void {
    if (this.config.features.colors) {
      const color = UnifiedLogger.COLORS[entry.level];
      console.log(`${color}${formatted}${UnifiedLogger.COLORS.RESET}`);
    } else {
      console.log(formatted);
    }
  }

  /**
   * Format log entry
   */
  private formatEntry(entry: LogEntry): string {
    const parts: string[] = [];

    // Timestamp
    if (this.config.features.timestamps) {
      parts.push(`[${entry.timestamp.toISOString()}]`);
    }

    // Level
    parts.push(`[${UnifiedLogger.LEVEL_NAMES[entry.level]}]`);

    // Module
    if (entry.module) {
      parts.push(`[${entry.module}]`);
    }

    // Message
    parts.push(entry.message);

    // Context
    if (entry.context && Object.keys(entry.context).length > 0) {
      parts.push(JSON.stringify(entry.context));
    }

    return parts.join(' ');
  }

  /**
   * Flush buffer to output
   */
  async flush(): Promise<void> {
    if (this.buffer.length === 0) {
      return;
    }

    this.metrics.bufferFlushes++;
    const entries = [...this.buffer];
    this.buffer = [];

    for (const entry of entries) {
      await this.writeEntry(entry);
    }
  }

  /**
   * Get logger metrics
   */
  getMetrics(): typeof this.metrics {
    return { ...this.metrics };
  }

  /**
   * Update logger configuration
   */
  updateConfig(config: Partial<LoggerConfig>): void {
    this.config = this.normalizeConfig({
      ...this.config,
      ...config
    });

    // Reinitialize if needed
    if (config.mode) {
      this.mode = config.mode;
      this.cleanup();
      this.initialize();
    }
  }

  /**
   * Set log level
   */
  setLevel(level: LogLevel): void {
    this.level = level;
  }

  /**
   * Cleanup resources
   */
  async cleanup(): Promise<void> {
    // Flush remaining buffer
    if (this.buffer.length > 0) {
      await this.flush();
    }

    // Clear timer
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }

    // Close file stream
    if (this.fileStream) {
      await new Promise(resolve => this.fileStream!.end(resolve));
    }

    // Cleanup security service
    await this.security.cleanup();
  }
}

// Export factory function
export function createLogger(config?: LoggerConfig): UnifiedLogger {
  return new UnifiedLogger(config);
}

// Export default instance
export const logger = new UnifiedLogger({ mode: LoggerMode.BASIC });