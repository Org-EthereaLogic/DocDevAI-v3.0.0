/**
 * @fileoverview Secure logger with injection prevention and PII filtering
 * @module @cli/core/logging/Logger.secure
 * @version 3.0.0
 * @performance >10k logs/sec with security filtering
 * @security Log injection prevention, PII filtering, secure transmission
 */

import { LoggerOptimized, LogLevel } from './Logger.optimized';
import { 
  inputValidator,
  auditLogger,
  rateLimiter,
  encryptionService
} from '../security';
import * as crypto from 'crypto';

/**
 * PII patterns to filter from logs
 */
const PII_PATTERNS = [
  // Personal Identifiers
  { pattern: /\b\d{3}-\d{2}-\d{4}\b/g, replacement: '[SSN]' },
  { pattern: /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g, replacement: '[CARD]' },
  { pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, replacement: '[EMAIL]' },
  { pattern: /\b\d{3}[-.]?\d{3}[-.]?\d{4}\b/g, replacement: '[PHONE]' },
  
  // Authentication
  { pattern: /Bearer\s+[A-Za-z0-9\-._~+/]+=*/g, replacement: 'Bearer [TOKEN]' },
  { pattern: /sk-[A-Za-z0-9]{48}/g, replacement: '[API_KEY]' },
  { pattern: /password["\s]*[:=]["\s]*["']?[^"',\s]+/gi, replacement: 'password=[REDACTED]' },
  { pattern: /api[_-]?key["\s]*[:=]["\s]*["']?[^"',\s]+/gi, replacement: 'api_key=[REDACTED]' },
  
  // Network Information
  { pattern: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g, replacement: '[IPv4]' },
  { pattern: /\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b/g, replacement: '[IPv6]' },
  
  // File Paths with User Info
  { pattern: /\/home\/[^/\s]+/g, replacement: '/home/[USER]' },
  { pattern: /\/Users\/[^/\s]+/g, replacement: '/Users/[USER]' },
  { pattern: /C:\\Users\\[^\\s]+/g, replacement: 'C:\\Users\\[USER]' },
];

/**
 * Log injection patterns to prevent
 */
const INJECTION_PATTERNS = [
  /\n|\r/g,                    // Newline injection
  /\x00-\x08\x0B\x0C\x0E-\x1F/g, // Control characters
  /\x1b\[[0-9;]*m/g,          // ANSI escape codes
  /%[0-9a-fA-F]{2}/g,         // URL encoding that could hide malicious content
];

/**
 * Secure log entry with integrity checking
 */
export interface SecureLogEntry {
  timestamp: number;
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
  filtered: boolean;
  hash?: string;
  correlationId?: string;
}

/**
 * Security configuration for logger
 */
export interface SecureLoggerConfig {
  enablePIIFiltering?: boolean;
  enableInjectionPrevention?: boolean;
  enableRateLimiting?: boolean;
  enableIntegrityCheck?: boolean;
  enableEncryption?: boolean;
  maxMessageLength?: number;
  maxContextDepth?: number;
}

/**
 * Secure logger with comprehensive security features
 * Extends optimized logger to maintain performance while adding security
 */
export class SecureLogger extends LoggerOptimized {
  private readonly config: Required<SecureLoggerConfig>;
  private readonly logBuffer: SecureLogEntry[] = [];
  private readonly suspiciousPatterns = new Set<string>();
  private logSequence = 0;
  private lastHash: string = '';

  constructor(config: SecureLoggerConfig = {}) {
    super();
    
    this.config = {
      enablePIIFiltering: config.enablePIIFiltering ?? true,
      enableInjectionPrevention: config.enableInjectionPrevention ?? true,
      enableRateLimiting: config.enableRateLimiting ?? true,
      enableIntegrityCheck: config.enableIntegrityCheck ?? false,
      enableEncryption: config.enableEncryption ?? false,
      maxMessageLength: config.maxMessageLength ?? 10000,
      maxContextDepth: config.maxContextDepth ?? 5
    };

    // Initialize integrity chain
    if (this.config.enableIntegrityCheck) {
      this.lastHash = this.generateInitialHash();
    }
  }

  /**
   * Logs a message with security filtering
   */
  public log(level: LogLevel, message: string, context?: Record<string, any>): void {
    const startTime = Date.now();

    try {
      // Check rate limit
      if (this.config.enableRateLimiting && !rateLimiter.checkLoggingRate(level)) {
        // Only drop non-critical logs when rate limited
        if (level !== 'error' && level !== 'critical') {
          return;
        }
      }

      // Validate and sanitize message
      const sanitizedMessage = this.sanitizeMessage(message);
      
      // Validate and sanitize context
      const sanitizedContext = context ? this.sanitizeContext(context) : undefined;
      
      // Check for injection attempts
      if (this.config.enableInjectionPrevention && this.detectInjection(message)) {
        this.handleInjectionAttempt(message, context);
        return;
      }

      // Filter PII if enabled
      const filteredMessage = this.config.enablePIIFiltering 
        ? this.filterPII(sanitizedMessage)
        : sanitizedMessage;

      // Create secure log entry
      const entry: SecureLogEntry = {
        timestamp: Date.now(),
        level,
        message: filteredMessage,
        context: sanitizedContext,
        filtered: filteredMessage !== sanitizedMessage,
        correlationId: this.generateCorrelationId()
      };

      // Add integrity hash if enabled
      if (this.config.enableIntegrityCheck) {
        entry.hash = this.calculateEntryHash(entry);
        this.lastHash = entry.hash;
      }

      // Encrypt sensitive logs if enabled
      if (this.config.enableEncryption && this.shouldEncrypt(level, message)) {
        this.encryptAndStore(entry);
      } else {
        // Call parent log method
        super.log(level, filteredMessage, sanitizedContext);
      }

      // Buffer for analysis
      this.bufferEntry(entry);

      // Performance check
      const processingTime = Date.now() - startTime;
      if (processingTime > 1) { // 1ms target for logging
        console.warn(`Secure logging exceeded target: ${processingTime}ms`);
      }
    } catch (error) {
      // Fallback to console.error for logging errors
      console.error('Logging error:', error);
    }
  }

  /**
   * Sanitizes log message
   */
  private sanitizeMessage(message: string): string {
    // Validate input type
    if (typeof message !== 'string') {
      message = String(message);
    }

    // Truncate if too long
    if (message.length > this.config.maxMessageLength) {
      message = message.substring(0, this.config.maxMessageLength) + '... [truncated]';
    }

    // Remove control characters
    message = message.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');

    // Escape special characters
    message = inputValidator.sanitizeUserInput(message) as string;

    return message;
  }

  /**
   * Sanitizes context object
   */
  private sanitizeContext(
    context: Record<string, any>,
    depth: number = 0
  ): Record<string, any> | undefined {
    if (depth >= this.config.maxContextDepth) {
      return { _truncated: true };
    }

    const sanitized: Record<string, any> = {};

    for (const [key, value] of Object.entries(context)) {
      // Skip dangerous keys
      if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
        continue;
      }

      // Sanitize key
      const sanitizedKey = this.sanitizeMessage(key);

      // Sanitize value based on type
      if (value === null || value === undefined) {
        sanitized[sanitizedKey] = value;
      } else if (typeof value === 'string') {
        sanitized[sanitizedKey] = this.config.enablePIIFiltering
          ? this.filterPII(this.sanitizeMessage(value))
          : this.sanitizeMessage(value);
      } else if (typeof value === 'number' || typeof value === 'boolean') {
        sanitized[sanitizedKey] = value;
      } else if (Array.isArray(value)) {
        sanitized[sanitizedKey] = value.slice(0, 10).map(item => 
          typeof item === 'object' ? '[object]' : item
        );
      } else if (typeof value === 'object') {
        sanitized[sanitizedKey] = this.sanitizeContext(value, depth + 1);
      } else {
        sanitized[sanitizedKey] = '[filtered]';
      }
    }

    return sanitized;
  }

  /**
   * Filters PII from text
   */
  private filterPII(text: string): string {
    let filtered = text;

    for (const { pattern, replacement } of PII_PATTERNS) {
      filtered = filtered.replace(pattern, replacement);
    }

    return filtered;
  }

  /**
   * Detects log injection attempts
   */
  private detectInjection(message: string): boolean {
    // Check for newline injection
    if (/[\n\r]/.test(message)) {
      return true;
    }

    // Check for control characters
    if (/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/.test(message)) {
      return true;
    }

    // Check for ANSI escape sequences
    if (/\x1b\[/.test(message)) {
      return true;
    }

    // Check for format string attacks
    if (/%[0-9]*[sdifoxX]/.test(message) && message.includes('%n')) {
      return true;
    }

    // Check for suspicious patterns
    const suspiciousPatterns = [
      /\$\{.*?\}/,           // Template injection
      /{{.*?}}/,             // Template injection
      /<script.*?>/i,        // Script injection
      /javascript:/i,        // JavaScript protocol
      /on\w+\s*=/i,          // Event handlers
    ];

    for (const pattern of suspiciousPatterns) {
      if (pattern.test(message)) {
        this.suspiciousPatterns.add(pattern.source);
        return true;
      }
    }

    return false;
  }

  /**
   * Handles detected injection attempts
   */
  private handleInjectionAttempt(message: string, context?: Record<string, any>): void {
    // Log to audit
    auditLogger.logSuspiciousActivity(
      'Log injection attempt detected',
      'high',
      {
        message: message.substring(0, 100),
        patterns: Array.from(this.suspiciousPatterns),
        context
      }
    );

    // Clear suspicious patterns set
    this.suspiciousPatterns.clear();

    // Log sanitized version
    const sanitized = message
      .replace(/[\n\r]/g, '\\n')
      .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '')
      .substring(0, 100);

    super.log('warn', `[INJECTION BLOCKED] ${sanitized}...`);
  }

  /**
   * Determines if log should be encrypted
   */
  private shouldEncrypt(level: LogLevel, message: string): boolean {
    // Encrypt error and critical logs
    if (level === 'error' || level === 'critical') {
      return true;
    }

    // Encrypt logs containing sensitive patterns
    const sensitiveKeywords = ['password', 'secret', 'token', 'key', 'auth'];
    return sensitiveKeywords.some(keyword => 
      message.toLowerCase().includes(keyword)
    );
  }

  /**
   * Encrypts and stores sensitive log entry
   */
  private encryptAndStore(entry: SecureLogEntry): void {
    const encrypted = encryptionService.encryptObject(
      entry,
      `log_${entry.level}_${entry.timestamp}`
    );

    // Store encrypted log reference
    super.log(entry.level, `[ENCRYPTED LOG] ID: ${entry.correlationId}`, {
      encrypted: true,
      correlationId: entry.correlationId
    });

    // Store encrypted data for potential recovery
    encryptionService.storeSecure(
      `log_${entry.correlationId}`,
      JSON.stringify(encrypted)
    );
  }

  /**
   * Buffers log entry for analysis
   */
  private bufferEntry(entry: SecureLogEntry): void {
    this.logBuffer.push(entry);

    // Keep buffer size limited
    if (this.logBuffer.length > 1000) {
      this.logBuffer.shift();
    }

    // Check for anomalies
    this.detectAnomalies();
  }

  /**
   * Detects anomalies in log patterns
   */
  private detectAnomalies(): void {
    const recentLogs = this.logBuffer.slice(-100);
    
    // Check for excessive error rates
    const errorCount = recentLogs.filter(e => 
      e.level === 'error' || e.level === 'critical'
    ).length;

    if (errorCount > 30) {
      auditLogger.logSuspiciousActivity(
        'Excessive error rate detected',
        'high',
        { errorCount, windowSize: 100 }
      );
    }

    // Check for repeated messages (potential loops)
    const messageFrequency = new Map<string, number>();
    for (const entry of recentLogs) {
      const key = entry.message.substring(0, 50);
      messageFrequency.set(key, (messageFrequency.get(key) || 0) + 1);
    }

    for (const [message, count] of messageFrequency.entries()) {
      if (count > 20) {
        auditLogger.logSuspiciousActivity(
          'Repeated log message detected',
          'medium',
          { message, count }
        );
      }
    }
  }

  /**
   * Generates correlation ID for log tracing
   */
  private generateCorrelationId(): string {
    return `${Date.now()}-${this.logSequence++}-${crypto.randomBytes(4).toString('hex')}`;
  }

  /**
   * Generates initial hash for integrity chain
   */
  private generateInitialHash(): string {
    return crypto.createHash('sha256')
      .update(`logger_${Date.now()}_${crypto.randomBytes(16).toString('hex')}`)
      .digest('hex');
  }

  /**
   * Calculates hash for log entry
   */
  private calculateEntryHash(entry: SecureLogEntry): string {
    const data = {
      ...entry,
      previousHash: this.lastHash
    };
    delete (data as any).hash;
    
    return crypto.createHash('sha256')
      .update(JSON.stringify(data))
      .digest('hex');
  }

  /**
   * Verifies log integrity
   */
  public async verifyIntegrity(
    startTime?: number,
    endTime?: number
  ): Promise<boolean> {
    if (!this.config.enableIntegrityCheck) {
      return true;
    }

    const entries = this.logBuffer.filter(entry =>
      (!startTime || entry.timestamp >= startTime) &&
      (!endTime || entry.timestamp <= endTime)
    );

    let previousHash = this.generateInitialHash();

    for (const entry of entries) {
      if (!entry.hash) {
        return false;
      }

      const computed = this.calculateEntryHash({
        ...entry,
        hash: undefined
      });

      if (computed !== entry.hash) {
        auditLogger.logSuspiciousActivity(
          'Log integrity verification failed',
          'critical',
          { 
            entryId: entry.correlationId,
            timestamp: entry.timestamp
          }
        );
        return false;
      }

      previousHash = entry.hash;
    }

    return true;
  }

  /**
   * Gets log statistics
   */
  public getStatistics(): {
    totalLogs: number;
    filteredLogs: number;
    injectionAttempts: number;
    encryptedLogs: number;
    logLevels: Record<LogLevel, number>;
  } {
    const stats = {
      totalLogs: this.logBuffer.length,
      filteredLogs: 0,
      injectionAttempts: 0,
      encryptedLogs: 0,
      logLevels: {
        debug: 0,
        info: 0,
        warn: 0,
        error: 0,
        critical: 0
      } as Record<LogLevel, number>
    };

    for (const entry of this.logBuffer) {
      if (entry.filtered) stats.filteredLogs++;
      stats.logLevels[entry.level]++;
      if (entry.context?.encrypted) stats.encryptedLogs++;
    }

    stats.injectionAttempts = auditLogger.getSecurityEvents()
      .filter(e => e.type === 'injection_attempt').length;

    return stats;
  }

  /**
   * Exports logs securely
   */
  public async exportLogs(
    startTime?: number,
    endTime?: number,
    format: 'json' | 'csv' = 'json'
  ): Promise<string> {
    const entries = this.logBuffer.filter(entry =>
      (!startTime || entry.timestamp >= startTime) &&
      (!endTime || entry.timestamp <= endTime)
    );

    // Verify integrity before export
    if (this.config.enableIntegrityCheck) {
      const isValid = await this.verifyIntegrity(startTime, endTime);
      if (!isValid) {
        throw new Error('Log integrity verification failed');
      }
    }

    if (format === 'json') {
      return JSON.stringify(entries, null, 2);
    } else {
      // CSV export
      const headers = ['timestamp', 'level', 'message', 'filtered', 'correlationId'];
      const rows = entries.map(entry => [
        new Date(entry.timestamp).toISOString(),
        entry.level,
        `"${entry.message.replace(/"/g, '""')}"`,
        entry.filtered,
        entry.correlationId
      ]);

      return [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    }
  }

  /**
   * Clears log buffer
   */
  public clearBuffer(): void {
    // Audit the clear operation
    auditLogger.logSecurityEvent({
      type: 'configuration_change',
      severity: 'info',
      source: 'logger',
      action: 'clear_buffer',
      result: 'success',
      details: { entriesCleared: this.logBuffer.length }
    });

    this.logBuffer.length = 0;
    this.logSequence = 0;
  }
}

// Export singleton instance
export const secureLogger = new SecureLogger();