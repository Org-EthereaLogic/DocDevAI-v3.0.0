/**
 * @fileoverview Secure memory mode detector with access controls
 * @module @cli/core/memory/MemoryModeDetector.secure
 * @version 3.0.0
 * @performance <1ms detection time with security checks
 * @security Access controls, resource validation, privilege checking
 */

import * as os from 'os';
import { MemoryModeDetectorOptimized, MemoryMode } from './MemoryModeDetector.optimized';
import { 
  auditLogger,
  rateLimiter
} from '../security';
import * as crypto from 'crypto';

/**
 * Security context for memory detection
 */
export interface MemoryDetectionContext {
  requestId: string;
  timestamp: number;
  source: string;
  privileged: boolean;
  validated: boolean;
}

/**
 * Memory access policy
 */
export interface MemoryAccessPolicy {
  allowSystemInfo: boolean;
  allowResourceProbing: boolean;
  maxDetectionFrequency: number;  // Detections per second
  requirePrivilege: boolean;
  resourceLimits: {
    maxMemoryCheck: number;      // Max memory to report in GB
    maxCpuCheck: number;         // Max CPUs to report
  };
}

/**
 * Secure memory information with sanitized data
 */
export interface SecureMemoryInfo {
  mode: MemoryMode;
  totalMemory: number;
  availableMemory: number;
  cpuCount: number;
  sanitized: boolean;
  detectionTime: number;
  context: MemoryDetectionContext;
}

/**
 * Secure memory mode detector with access controls
 * Extends optimized detector to maintain performance while adding security
 */
export class SecureMemoryModeDetector extends MemoryModeDetectorOptimized {
  private readonly policy: MemoryAccessPolicy;
  private readonly detectionHistory: Map<string, number[]> = new Map();
  private readonly privilegedSources = new Set<string>([
    'system',
    'admin',
    'config_loader',
    'performance_monitor'
  ]);
  private lastDetectionTime = 0;
  private detectionCount = 0;

  constructor(policy?: Partial<MemoryAccessPolicy>) {
    super();
    
    this.policy = {
      allowSystemInfo: policy?.allowSystemInfo ?? true,
      allowResourceProbing: policy?.allowResourceProbing ?? true,
      maxDetectionFrequency: policy?.maxDetectionFrequency ?? 10,
      requirePrivilege: policy?.requirePrivilege ?? false,
      resourceLimits: {
        maxMemoryCheck: policy?.resourceLimits?.maxMemoryCheck ?? 1024,  // 1TB max
        maxCpuCheck: policy?.resourceLimits?.maxCpuCheck ?? 256
      }
    };
  }

  /**
   * Detects memory mode with security checks
   */
  public detect(source: string = 'unknown'): MemoryMode {
    const startTime = Date.now();
    const context = this.createContext(source);

    try {
      // Check rate limit
      if (!this.checkRateLimit(context)) {
        this.handleRateLimitExceeded(context);
        return this.getCachedMode() || 'standard';
      }

      // Check access permissions
      if (!this.checkAccess(context)) {
        this.handleAccessDenied(context);
        return 'baseline';  // Return most restrictive mode
      }

      // Validate system access
      if (!this.validateSystemAccess()) {
        return 'baseline';
      }

      // Perform detection with parent method
      const mode = super.detect();

      // Validate detected mode
      const validatedMode = this.validateMode(mode, context);

      // Audit successful detection
      this.auditDetection(validatedMode, context, Date.now() - startTime);

      // Update history
      this.updateHistory(context);

      // Performance check
      const detectionTime = Date.now() - startTime;
      if (detectionTime > 1) {
        console.warn(`Secure memory detection exceeded target: ${detectionTime}ms`);
      }

      return validatedMode;
    } catch (error) {
      this.handleDetectionError(error, context);
      return 'baseline';
    }
  }

  /**
   * Gets secure memory information
   */
  public getSecureMemoryInfo(source: string = 'unknown'): SecureMemoryInfo | null {
    const context = this.createContext(source);

    // Check permissions
    if (!this.checkAccess(context)) {
      this.handleAccessDenied(context);
      return null;
    }

    // Check if system info is allowed
    if (!this.policy.allowSystemInfo) {
      auditLogger.logAccessAttempt('system_info', 'denied', {
        source,
        reason: 'System info access disabled by policy'
      });
      return null;
    }

    const startTime = Date.now();

    try {
      // Get system information
      const totalMemory = os.totalmem();
      const freeMemory = os.freemem();
      const cpus = os.cpus();

      // Sanitize values based on policy
      const sanitizedInfo: SecureMemoryInfo = {
        mode: this.detect(source),
        totalMemory: this.sanitizeMemoryValue(totalMemory),
        availableMemory: this.sanitizeMemoryValue(freeMemory),
        cpuCount: Math.min(cpus.length, this.policy.resourceLimits.maxCpuCheck),
        sanitized: true,
        detectionTime: Date.now() - startTime,
        context
      };

      // Audit information access
      auditLogger.logAccessAttempt('system_info', 'allowed', {
        source,
        infoRequested: ['memory', 'cpu'],
        sanitized: true
      });

      return sanitizedInfo;
    } catch (error) {
      this.handleDetectionError(error, context);
      return null;
    }
  }

  /**
   * Creates security context for detection
   */
  private createContext(source: string): MemoryDetectionContext {
    return {
      requestId: crypto.randomBytes(8).toString('hex'),
      timestamp: Date.now(),
      source,
      privileged: this.privilegedSources.has(source),
      validated: false
    };
  }

  /**
   * Checks rate limit for detection
   */
  private checkRateLimit(context: MemoryDetectionContext): boolean {
    // Always allow privileged sources
    if (context.privileged) {
      return true;
    }

    // Check global rate limit
    if (!rateLimiter.checkMemoryDetectionLimit()) {
      return false;
    }

    // Check per-source rate limit
    const now = Date.now();
    const history = this.detectionHistory.get(context.source) || [];
    
    // Remove old entries (older than 1 second)
    const recentHistory = history.filter(time => now - time < 1000);
    
    if (recentHistory.length >= this.policy.maxDetectionFrequency) {
      return false;
    }

    return true;
  }

  /**
   * Checks access permissions
   */
  private checkAccess(context: MemoryDetectionContext): boolean {
    // Check if privilege is required
    if (this.policy.requirePrivilege && !context.privileged) {
      return false;
    }

    // Check if resource probing is allowed
    if (!this.policy.allowResourceProbing && !context.privileged) {
      return false;
    }

    context.validated = true;
    return true;
  }

  /**
   * Validates system access
   */
  private validateSystemAccess(): boolean {
    try {
      // Try to access system information
      const mem = os.totalmem();
      const cpus = os.cpus();
      
      // Validate reasonable values
      if (mem <= 0 || mem > 1024 * 1024 * 1024 * 1024 * 1024) { // > 1PB is unrealistic
        auditLogger.logSuspiciousActivity(
          'Unrealistic memory value detected',
          'high',
          { value: mem }
        );
        return false;
      }

      if (cpus.length <= 0 || cpus.length > this.policy.resourceLimits.maxCpuCheck) {
        auditLogger.logSuspiciousActivity(
          'Unrealistic CPU count detected',
          'medium',
          { count: cpus.length }
        );
        return false;
      }

      return true;
    } catch (error) {
      // System access failed
      auditLogger.logSecurityEvent({
        type: 'access_denied',
        severity: 'medium',
        source: 'memory_detector',
        action: 'system_access',
        result: 'failure',
        details: { error: error instanceof Error ? error.message : 'Unknown error' }
      });
      return false;
    }
  }

  /**
   * Validates detected memory mode
   */
  private validateMode(mode: MemoryMode, context: MemoryDetectionContext): MemoryMode {
    // Non-privileged sources can't get performance mode
    if (!context.privileged && mode === 'performance') {
      auditLogger.logSuspiciousActivity(
        'Non-privileged source attempted performance mode',
        'medium',
        { source: context.source, attemptedMode: mode }
      );
      return 'enhanced';
    }

    // Validate mode is within allowed set
    const validModes: MemoryMode[] = ['baseline', 'standard', 'enhanced', 'performance'];
    if (!validModes.includes(mode)) {
      auditLogger.logSuspiciousActivity(
        'Invalid memory mode detected',
        'high',
        { detectedMode: mode }
      );
      return 'standard';
    }

    return mode;
  }

  /**
   * Sanitizes memory value based on policy
   */
  private sanitizeMemoryValue(bytes: number): number {
    const maxBytes = this.policy.resourceLimits.maxMemoryCheck * 1024 * 1024 * 1024;
    
    if (bytes > maxBytes) {
      // Cap at maximum allowed value
      return maxBytes;
    }

    // Round to nearest MB to avoid leaking exact values
    return Math.round(bytes / (1024 * 1024)) * 1024 * 1024;
  }

  /**
   * Handles rate limit exceeded
   */
  private handleRateLimitExceeded(context: MemoryDetectionContext): void {
    auditLogger.logSecurityEvent({
      type: 'rate_limit_exceeded',
      severity: 'medium',
      source: 'memory_detector',
      userId: context.source,
      result: 'blocked',
      details: {
        requestId: context.requestId,
        frequency: this.detectionHistory.get(context.source)?.length || 0
      }
    });
  }

  /**
   * Handles access denied
   */
  private handleAccessDenied(context: MemoryDetectionContext): void {
    auditLogger.logAccessAttempt('memory_detection', 'denied', {
      source: context.source,
      requestId: context.requestId,
      privileged: context.privileged,
      reason: 'Insufficient privileges'
    });
  }

  /**
   * Handles detection error
   */
  private handleDetectionError(error: unknown, context: MemoryDetectionContext): void {
    auditLogger.logSecurityEvent({
      type: 'error_generated',
      severity: 'low',
      source: 'memory_detector',
      result: 'failure',
      details: {
        requestId: context.requestId,
        source: context.source,
        error: error instanceof Error ? error.message : 'Unknown error'
      }
    });
  }

  /**
   * Audits successful detection
   */
  private auditDetection(
    mode: MemoryMode,
    context: MemoryDetectionContext,
    duration: number
  ): void {
    // Only audit non-cached detections
    if (duration > 0.1) {  // If it took more than 0.1ms, it wasn't cached
      auditLogger.logAccessAttempt('memory_detection', 'allowed', {
        source: context.source,
        requestId: context.requestId,
        mode,
        duration,
        privileged: context.privileged
      });
    }

    // Track detection count
    this.detectionCount++;
    
    // Log milestone detections
    if (this.detectionCount % 1000 === 0) {
      auditLogger.logSecurityEvent({
        type: 'access_granted',
        severity: 'info',
        source: 'memory_detector',
        result: 'success',
        details: {
          milestone: this.detectionCount,
          averageMode: this.getAverageMode()
        }
      });
    }
  }

  /**
   * Updates detection history
   */
  private updateHistory(context: MemoryDetectionContext): void {
    const history = this.detectionHistory.get(context.source) || [];
    history.push(context.timestamp);
    
    // Keep only last 100 entries per source
    if (history.length > 100) {
      history.shift();
    }
    
    this.detectionHistory.set(context.source, history);
    
    // Clean up old sources
    if (this.detectionHistory.size > 100) {
      const oldestEntries = Array.from(this.detectionHistory.entries())
        .sort((a, b) => Math.max(...a[1]) - Math.max(...b[1]))
        .slice(0, 50);
      
      for (const [source] of oldestEntries) {
        this.detectionHistory.delete(source);
      }
    }
  }

  /**
   * Gets average detected mode
   */
  private getAverageMode(): string {
    // This is a simplified implementation
    // In production, you'd track mode distribution
    return 'standard';
  }

  /**
   * Gets cached mode if available
   */
  private getCachedMode(): MemoryMode | null {
    // Check if we have a recent detection
    if (Date.now() - this.lastDetectionTime < 1000) {
      return this.cachedMode;
    }
    return null;
  }

  /**
   * Updates access policy
   */
  public updatePolicy(updates: Partial<MemoryAccessPolicy>): void {
    // Audit policy change
    auditLogger.logConfigurationChange({
      path: 'memory_detector_policy',
      oldValue: { ...this.policy },
      newValue: { ...this.policy, ...updates },
      reason: 'Policy update'
    });

    // Apply updates
    Object.assign(this.policy, updates);
  }

  /**
   * Adds privileged source
   */
  public addPrivilegedSource(source: string): void {
    if (!this.privilegedSources.has(source)) {
      this.privilegedSources.add(source);
      
      auditLogger.logConfigurationChange({
        path: 'privileged_sources',
        newValue: { added: source },
        reason: 'Privilege granted'
      });
    }
  }

  /**
   * Removes privileged source
   */
  public removePrivilegedSource(source: string): void {
    if (this.privilegedSources.has(source)) {
      this.privilegedSources.delete(source);
      
      auditLogger.logConfigurationChange({
        path: 'privileged_sources',
        oldValue: { removed: source },
        reason: 'Privilege revoked'
      });
    }
  }

  /**
   * Gets detection statistics
   */
  public getStatistics(): {
    totalDetections: number;
    uniqueSources: number;
    privilegedDetections: number;
    deniedAttempts: number;
    rateLimitHits: number;
  } {
    const events = auditLogger.getSecurityEvents();
    
    const deniedAttempts = events.filter(e => 
      e.source === 'memory_detector' && e.result === 'blocked'
    ).length;
    
    const rateLimitHits = events.filter(e =>
      e.source === 'memory_detector' && e.type === 'rate_limit_exceeded'
    ).length;
    
    const privilegedDetections = events.filter(e =>
      e.source === 'memory_detector' && 
      e.details?.privileged === true
    ).length;

    return {
      totalDetections: this.detectionCount,
      uniqueSources: this.detectionHistory.size,
      privilegedDetections,
      deniedAttempts,
      rateLimitHits
    };
  }

  /**
   * Clears detection history
   */
  public clearHistory(): void {
    this.detectionHistory.clear();
    this.detectionCount = 0;
    
    auditLogger.logSecurityEvent({
      type: 'configuration_change',
      severity: 'info',
      source: 'memory_detector',
      action: 'clear_history',
      result: 'success'
    });
  }
}

// Export singleton instance
export const secureMemoryModeDetector = new SecureMemoryModeDetector();