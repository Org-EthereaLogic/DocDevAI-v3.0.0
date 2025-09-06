/**
 * @fileoverview Audit logging service for security event tracking
 * @module @cli/core/security/AuditLogger
 * @version 1.0.0
 * @security Tamper-evident audit logging with integrity verification
 */

import * as fs from 'fs';
import * as path from 'path';
import { createHash, randomBytes } from 'crypto';
import { EventEmitter } from 'events';

/**
 * Security event types
 */
export type SecurityEventType = 
  | 'access_granted'
  | 'access_denied'
  | 'authentication_success'
  | 'authentication_failure'
  | 'configuration_change'
  | 'validation_failure'
  | 'injection_attempt'
  | 'rate_limit_exceeded'
  | 'encryption_operation'
  | 'decryption_operation'
  | 'error_generated'
  | 'suspicious_activity';

/**
 * Security event severity levels
 */
export type SecuritySeverity = 'info' | 'low' | 'medium' | 'high' | 'critical';

/**
 * Audit log entry interface
 */
export interface AuditLogEntry {
  id: string;
  timestamp: number;
  type: SecurityEventType;
  severity: SecuritySeverity;
  source: string;
  userId?: string;
  sessionId?: string;
  ipAddress?: string;
  resource?: string;
  action?: string;
  result: 'success' | 'failure' | 'blocked';
  details?: Record<string, unknown>;
  correlationId?: string;
  hash?: string;
  previousHash?: string;
}

/**
 * Configuration change event
 */
export interface ConfigChange {
  path: string;
  oldValue?: unknown;
  newValue?: unknown;
  changedBy?: string;
  reason?: string;
}

/**
 * Error event for audit
 */
export interface ErrorEvent {
  code: string;
  message: string;
  stack?: string;
  context?: Record<string, unknown>;
}

/**
 * Audit logger configuration
 */
export interface AuditLoggerConfig {
  logPath?: string;
  maxLogSize?: number;
  maxLogFiles?: number;
  enableConsole?: boolean;
  enableFile?: boolean;
  minSeverity?: SecuritySeverity;
  hashAlgorithm?: string;
  enableIntegrityCheck?: boolean;
}

/**
 * Tamper-evident audit logging service
 * Provides comprehensive security event tracking with integrity verification
 */
export class AuditLogger extends EventEmitter {
  private config: Required<AuditLoggerConfig>;
  private logBuffer: AuditLogEntry[] = [];
  private currentLogFile?: string;
  private lastHash: string = '';
  private sessionId: string;
  private logStream?: fs.WriteStream;
  private flushTimer?: NodeJS.Timeout;
  private readonly severityLevels: Record<SecuritySeverity, number> = {
    info: 0,
    low: 1,
    medium: 2,
    high: 3,
    critical: 4
  };

  constructor(config: AuditLoggerConfig = {}) {
    super();
    
    this.config = {
      logPath: config.logPath || path.join(process.cwd(), 'audit'),
      maxLogSize: config.maxLogSize || 10 * 1024 * 1024, // 10MB
      maxLogFiles: config.maxLogFiles || 10,
      enableConsole: config.enableConsole ?? false,
      enableFile: config.enableFile ?? true,
      minSeverity: config.minSeverity || 'info',
      hashAlgorithm: config.hashAlgorithm || 'sha256',
      enableIntegrityCheck: config.enableIntegrityCheck ?? true
    };

    this.sessionId = this.generateSessionId();
    this.initializeLogger();
  }

  /**
   * Initializes the audit logger
   */
  private initializeLogger(): void {
    if (this.config.enableFile) {
      // Create audit directory if it doesn't exist
      if (!fs.existsSync(this.config.logPath)) {
        fs.mkdirSync(this.config.logPath, { recursive: true, mode: 0o700 });
      }

      // Initialize log file
      this.rotateLogFile();
      
      // Set up periodic flush
      this.flushTimer = setInterval(() => this.flush(), 5000);
    }

    // Initialize hash chain
    this.lastHash = this.generateInitialHash();
  }

  /**
   * Logs a security event
   */
  public logSecurityEvent(event: Partial<AuditLogEntry> & { type: SecurityEventType }): void {
    const entry: AuditLogEntry = {
      id: this.generateEventId(),
      timestamp: Date.now(),
      severity: event.severity || 'info',
      source: event.source || 'unknown',
      sessionId: this.sessionId,
      result: event.result || 'success',
      ...event,
      previousHash: this.config.enableIntegrityCheck ? this.lastHash : undefined
    };

    // Add hash for tamper detection
    if (this.config.enableIntegrityCheck) {
      entry.hash = this.calculateHash(entry);
      this.lastHash = entry.hash;
    }

    // Check severity threshold
    if (this.severityLevels[entry.severity] < this.severityLevels[this.config.minSeverity]) {
      return;
    }

    // Add to buffer
    this.logBuffer.push(entry);

    // Log to console if enabled
    if (this.config.enableConsole) {
      this.logToConsole(entry);
    }

    // Emit event for real-time monitoring
    this.emit('audit', entry);

    // Flush if buffer is getting large or event is critical
    if (this.logBuffer.length > 100 || entry.severity === 'critical') {
      this.flush();
    }
  }

  /**
   * Logs an access attempt
   */
  public logAccessAttempt(
    resource: string, 
    result: 'allowed' | 'denied',
    details?: Record<string, unknown>
  ): void {
    this.logSecurityEvent({
      type: result === 'allowed' ? 'access_granted' : 'access_denied',
      severity: result === 'denied' ? 'medium' : 'info',
      resource,
      result: result === 'allowed' ? 'success' : 'blocked',
      details
    });
  }

  /**
   * Logs a configuration change
   */
  public logConfigurationChange(change: ConfigChange): void {
    this.logSecurityEvent({
      type: 'configuration_change',
      severity: 'medium',
      source: 'configuration',
      resource: change.path,
      details: {
        oldValue: this.sanitizeValue(change.oldValue),
        newValue: this.sanitizeValue(change.newValue),
        changedBy: change.changedBy,
        reason: change.reason
      },
      result: 'success'
    });
  }

  /**
   * Logs error generation
   */
  public logErrorGeneration(error: ErrorEvent): void {
    this.logSecurityEvent({
      type: 'error_generated',
      severity: 'low',
      source: 'error_handler',
      details: {
        code: error.code,
        message: this.sanitizeValue(error.message),
        context: error.context
      },
      result: 'failure'
    });
  }

  /**
   * Logs suspicious activity
   */
  public logSuspiciousActivity(
    activity: string,
    severity: SecuritySeverity = 'high',
    details?: Record<string, unknown>
  ): void {
    this.logSecurityEvent({
      type: 'suspicious_activity',
      severity,
      source: 'security_monitor',
      action: activity,
      details,
      result: 'blocked'
    });
  }

  /**
   * Verifies the integrity of the audit log
   */
  public async verifyIntegrity(startTime?: number, endTime?: number): Promise<boolean> {
    if (!this.config.enableIntegrityCheck) {
      return true;
    }

    try {
      const logs = await this.readLogs(startTime, endTime);
      let previousHash = this.generateInitialHash();

      for (const entry of logs) {
        if (!entry.hash || !entry.previousHash) {
          return false;
        }

        if (entry.previousHash !== previousHash) {
          return false;
        }

        const calculatedHash = this.calculateHash({ ...entry, hash: undefined });
        if (calculatedHash !== entry.hash) {
          return false;
        }

        previousHash = entry.hash;
      }

      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Reads audit logs within a time range
   */
  public async readLogs(startTime?: number, endTime?: number): Promise<AuditLogEntry[]> {
    const logs: AuditLogEntry[] = [];
    
    if (!this.config.enableFile) {
      return this.logBuffer.filter(entry => 
        (!startTime || entry.timestamp >= startTime) &&
        (!endTime || entry.timestamp <= endTime)
      );
    }

    const logFiles = fs.readdirSync(this.config.logPath)
      .filter(file => file.endsWith('.audit.log'))
      .sort();

    for (const file of logFiles) {
      const content = fs.readFileSync(path.join(this.config.logPath, file), 'utf-8');
      const lines = content.split('\n').filter(line => line.trim());
      
      for (const line of lines) {
        try {
          const entry = JSON.parse(line) as AuditLogEntry;
          if ((!startTime || entry.timestamp >= startTime) &&
              (!endTime || entry.timestamp <= endTime)) {
            logs.push(entry);
          }
        } catch {
          // Skip malformed entries
        }
      }
    }

    return logs;
  }

  /**
   * Generates a unique session ID
   */
  private generateSessionId(): string {
    return randomBytes(16).toString('hex');
  }

  /**
   * Generates a unique event ID
   */
  private generateEventId(): string {
    return `${Date.now()}-${randomBytes(8).toString('hex')}`;
  }

  /**
   * Generates initial hash for the hash chain
   */
  private generateInitialHash(): string {
    const data = {
      sessionId: this.sessionId,
      timestamp: Date.now(),
      random: randomBytes(32).toString('hex')
    };
    return createHash(this.config.hashAlgorithm)
      .update(JSON.stringify(data))
      .digest('hex');
  }

  /**
   * Calculates hash for an audit entry
   */
  private calculateHash(entry: Omit<AuditLogEntry, 'hash'>): string {
    const data = { ...entry };
    delete (data as any).hash;
    return createHash(this.config.hashAlgorithm)
      .update(JSON.stringify(data))
      .digest('hex');
  }

  /**
   * Sanitizes values to prevent information leakage
   */
  private sanitizeValue(value: unknown): unknown {
    if (typeof value === 'string') {
      // Remove potential secrets
      return value
        .replace(/password["\s]*[:=]["\s]*["']?[^"',\s]+/gi, 'password=***')
        .replace(/api[_-]?key["\s]*[:=]["\s]*["']?[^"',\s]+/gi, 'api_key=***')
        .replace(/token["\s]*[:=]["\s]*["']?[^"',\s]+/gi, 'token=***')
        .replace(/secret["\s]*[:=]["\s]*["']?[^"',\s]+/gi, 'secret=***')
        .replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '***@***.***')
        .replace(/\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/g, '****-****-****-****');
    }
    return value;
  }

  /**
   * Logs to console
   */
  private logToConsole(entry: AuditLogEntry): void {
    const severityColors: Record<SecuritySeverity, string> = {
      info: '\x1b[36m',    // Cyan
      low: '\x1b[32m',     // Green
      medium: '\x1b[33m',  // Yellow
      high: '\x1b[31m',    // Red
      critical: '\x1b[35m' // Magenta
    };

    const color = severityColors[entry.severity];
    const reset = '\x1b[0m';
    
    console.log(
      `${color}[AUDIT]${reset} ${new Date(entry.timestamp).toISOString()} ` +
      `[${entry.severity.toUpperCase()}] ${entry.type}: ${entry.result} ` +
      `(${entry.source}${entry.resource ? ` -> ${entry.resource}` : ''})`
    );
  }

  /**
   * Flushes log buffer to file
   */
  private flush(): void {
    if (!this.config.enableFile || this.logBuffer.length === 0) {
      return;
    }

    const entries = this.logBuffer.splice(0, this.logBuffer.length);
    
    for (const entry of entries) {
      if (this.logStream) {
        this.logStream.write(JSON.stringify(entry) + '\n');
      }
    }

    // Check if rotation is needed
    if (this.currentLogFile && fs.existsSync(this.currentLogFile)) {
      const stats = fs.statSync(this.currentLogFile);
      if (stats.size > this.config.maxLogSize) {
        this.rotateLogFile();
      }
    }
  }

  /**
   * Rotates log files
   */
  private rotateLogFile(): void {
    // Close existing stream
    if (this.logStream) {
      this.logStream.end();
    }

    // Generate new filename
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    this.currentLogFile = path.join(this.config.logPath, `audit-${timestamp}.audit.log`);
    
    // Create new stream
    this.logStream = fs.createWriteStream(this.currentLogFile, {
      flags: 'a',
      mode: 0o600
    });

    // Clean up old files
    this.cleanupOldLogs();
  }

  /**
   * Cleans up old log files
   */
  private cleanupOldLogs(): void {
    const files = fs.readdirSync(this.config.logPath)
      .filter(file => file.endsWith('.audit.log'))
      .map(file => ({
        name: file,
        path: path.join(this.config.logPath, file),
        time: fs.statSync(path.join(this.config.logPath, file)).mtime.getTime()
      }))
      .sort((a, b) => b.time - a.time);

    // Keep only the configured number of files
    if (files.length > this.config.maxLogFiles) {
      const toDelete = files.slice(this.config.maxLogFiles);
      for (const file of toDelete) {
        fs.unlinkSync(file.path);
      }
    }
  }

  /**
   * Generates audit report
   */
  public async generateReport(startTime: number, endTime: number): Promise<string> {
    const logs = await this.readLogs(startTime, endTime);
    
    const summary = {
      totalEvents: logs.length,
      bySeverity: {} as Record<SecuritySeverity, number>,
      byType: {} as Record<SecurityEventType, number>,
      byResult: {} as Record<string, number>,
      suspiciousActivities: 0,
      injectionAttempts: 0,
      accessDenied: 0
    };

    for (const entry of logs) {
      summary.bySeverity[entry.severity] = (summary.bySeverity[entry.severity] || 0) + 1;
      summary.byType[entry.type] = (summary.byType[entry.type] || 0) + 1;
      summary.byResult[entry.result] = (summary.byResult[entry.result] || 0) + 1;
      
      if (entry.type === 'suspicious_activity') summary.suspiciousActivities++;
      if (entry.type === 'injection_attempt') summary.injectionAttempts++;
      if (entry.type === 'access_denied') summary.accessDenied++;
    }

    return JSON.stringify(summary, null, 2);
  }

  /**
   * Closes the audit logger
   */
  public close(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }
    
    this.flush();
    
    if (this.logStream) {
      this.logStream.end();
    }
  }
}

// Export singleton instance
export const auditLogger = new AuditLogger();