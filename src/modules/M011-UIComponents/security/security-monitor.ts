/**
 * M011 Security Monitor - Security event logging, anomaly detection, and metrics
 * 
 * Provides comprehensive security monitoring including event aggregation, pattern
 * detection, attack surface monitoring, and security metrics collection. Integrates
 * with all security modules to provide centralized monitoring.
 */

import { securityUtils, SecurityEvent, SecurityEventType } from './security-utils';
import { authManager } from './auth-manager';
import { apiSecurity } from './api-security';

/**
 * Security metric types
 */
export enum SecurityMetricType {
  FAILED_LOGINS = 'failed_logins',
  SUCCESSFUL_LOGINS = 'successful_logins',
  XSS_ATTEMPTS = 'xss_attempts',
  SQL_INJECTION_ATTEMPTS = 'sql_injection_attempts',
  CSRF_VIOLATIONS = 'csrf_violations',
  RATE_LIMIT_VIOLATIONS = 'rate_limit_violations',
  UNAUTHORIZED_ACCESS = 'unauthorized_access',
  SUSPICIOUS_ACTIVITY = 'suspicious_activity',
  API_ERRORS = 'api_errors',
  SESSION_TIMEOUTS = 'session_timeouts'
}

/**
 * Attack pattern types
 */
export enum AttackPattern {
  BRUTE_FORCE = 'brute_force',
  CREDENTIAL_STUFFING = 'credential_stuffing',
  SESSION_HIJACKING = 'session_hijacking',
  XSS_CAMPAIGN = 'xss_campaign',
  SQL_INJECTION_SCAN = 'sql_injection_scan',
  DDOS_ATTEMPT = 'ddos_attempt',
  RECONNAISSANCE = 'reconnaissance',
  PRIVILEGE_ESCALATION = 'privilege_escalation'
}

/**
 * Security metric interface
 */
export interface SecurityMetric {
  type: SecurityMetricType;
  count: number;
  timestamp: number;
  window: number; // Time window in milliseconds
  metadata?: any;
}

/**
 * Anomaly detection result
 */
export interface AnomalyResult {
  id: string;
  pattern: AttackPattern;
  confidence: number; // 0-1
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  events: SecurityEvent[];
  timestamp: number;
  recommendations: string[];
}

/**
 * Attack surface item
 */
export interface AttackSurfaceItem {
  id: string;
  type: 'endpoint' | 'form' | 'input' | 'storage' | 'cookie' | 'header';
  name: string;
  risk: 'low' | 'medium' | 'high';
  vulnerabilities: string[];
  mitigations: string[];
  lastChecked: number;
}

/**
 * Security monitor configuration
 */
export interface MonitorConfig {
  enableAnomalyDetection: boolean;
  enableMetricsCollection: boolean;
  enableAttackSurfaceMonitoring: boolean;
  enableRealTimeAlerts: boolean;
  anomalyThreshold: number; // Events per minute to trigger anomaly
  metricsRetentionDays: number;
  alertWebhook?: string;
  logToConsole: boolean;
  logToServer: boolean;
}

/**
 * Default monitor configuration
 */
const DEFAULT_MONITOR_CONFIG: MonitorConfig = {
  enableAnomalyDetection: true,
  enableMetricsCollection: true,
  enableAttackSurfaceMonitoring: true,
  enableRealTimeAlerts: true,
  anomalyThreshold: 10,
  metricsRetentionDays: 30,
  logToConsole: process.env.NODE_ENV === 'development',
  logToServer: process.env.NODE_ENV === 'production'
};

/**
 * Security monitor class
 */
export class SecurityMonitor {
  private static instance: SecurityMonitor;
  private config: MonitorConfig;
  private events: SecurityEvent[] = [];
  private metrics: Map<SecurityMetricType, SecurityMetric[]> = new Map();
  private anomalies: AnomalyResult[] = [];
  private attackSurface: Map<string, AttackSurfaceItem> = new Map();
  private eventListeners: Map<string, Set<(event: SecurityEvent) => void>> = new Map();
  private monitoringInterval: NodeJS.Timeout | null = null;
  private readonly MAX_EVENTS = 10000;
  private readonly MAX_ANOMALIES = 100;

  private constructor(config?: Partial<MonitorConfig>) {
    this.config = { ...DEFAULT_MONITOR_CONFIG, ...config };
    this.initialize();
  }

  /**
   * Get singleton instance
   */
  public static getInstance(config?: Partial<MonitorConfig>): SecurityMonitor {
    if (!SecurityMonitor.instance) {
      SecurityMonitor.instance = new SecurityMonitor(config);
    }
    return SecurityMonitor.instance;
  }

  /**
   * Initialize monitor
   */
  private initialize(): void {
    // Start monitoring interval
    this.startMonitoring();
    
    // Initialize attack surface
    this.initializeAttackSurface();
    
    // Setup event listeners
    this.setupEventListeners();
    
    // Load historical data if available
    this.loadHistoricalData();
  }

  /**
   * Start monitoring
   */
  private startMonitoring(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }

    // Run every minute
    this.monitoringInterval = setInterval(() => {
      this.collectMetrics();
      
      if (this.config.enableAnomalyDetection) {
        this.detectAnomalies();
      }
      
      if (this.config.enableAttackSurfaceMonitoring) {
        this.updateAttackSurface();
      }
      
      this.cleanupOldData();
    }, 60000);
  }

  /**
   * Log security event
   */
  public logEvent(event: Omit<SecurityEvent, 'id' | 'timestamp'>): void {
    const fullEvent: SecurityEvent = {
      ...event,
      id: securityUtils.generateUUID(),
      timestamp: Date.now()
    };

    // Add to events array
    this.events.push(fullEvent);
    
    // Limit events array size
    if (this.events.length > this.MAX_EVENTS) {
      this.events = this.events.slice(-this.MAX_EVENTS);
    }

    // Update metrics
    this.updateMetrics(fullEvent);
    
    // Check for immediate threats
    this.checkImmediateThreats(fullEvent);
    
    // Notify listeners
    this.notifyListeners(fullEvent);
    
    // Log to console if enabled
    if (this.config.logToConsole) {
      console.warn('[Security Monitor]', fullEvent);
    }
    
    // Send to server if enabled
    if (this.config.logToServer) {
      this.sendToServer(fullEvent);
    }
  }

  /**
   * Collect metrics
   */
  private collectMetrics(): void {
    if (!this.config.enableMetricsCollection) {
      return;
    }

    const now = Date.now();
    const window = 60000; // 1 minute window

    // Count events by type in the last minute
    const recentEvents = this.events.filter(e => now - e.timestamp < window);
    
    const metrics: Partial<Record<SecurityMetricType, number>> = {
      [SecurityMetricType.XSS_ATTEMPTS]: recentEvents.filter(
        e => e.type === SecurityEventType.XSS_ATTEMPT
      ).length,
      [SecurityMetricType.SQL_INJECTION_ATTEMPTS]: recentEvents.filter(
        e => e.type === SecurityEventType.SQL_INJECTION_ATTEMPT
      ).length,
      [SecurityMetricType.CSRF_VIOLATIONS]: recentEvents.filter(
        e => e.type === SecurityEventType.CSRF_TOKEN_MISMATCH
      ).length,
      [SecurityMetricType.RATE_LIMIT_VIOLATIONS]: recentEvents.filter(
        e => e.type === SecurityEventType.RATE_LIMIT_EXCEEDED
      ).length
    };

    // Store metrics
    Object.entries(metrics).forEach(([type, count]) => {
      if (count > 0) {
        const metricType = type as SecurityMetricType;
        const metric: SecurityMetric = {
          type: metricType,
          count,
          timestamp: now,
          window
        };
        
        const existing = this.metrics.get(metricType) || [];
        existing.push(metric);
        this.metrics.set(metricType, existing);
      }
    });
  }

  /**
   * Update metrics from event
   */
  private updateMetrics(event: SecurityEvent): void {
    let metricType: SecurityMetricType | null = null;

    switch (event.type) {
      case SecurityEventType.XSS_ATTEMPT:
        metricType = SecurityMetricType.XSS_ATTEMPTS;
        break;
      case SecurityEventType.SQL_INJECTION_ATTEMPT:
        metricType = SecurityMetricType.SQL_INJECTION_ATTEMPTS;
        break;
      case SecurityEventType.CSRF_TOKEN_MISMATCH:
        metricType = SecurityMetricType.CSRF_VIOLATIONS;
        break;
      case SecurityEventType.RATE_LIMIT_EXCEEDED:
        metricType = SecurityMetricType.RATE_LIMIT_VIOLATIONS;
        break;
    }

    if (metricType) {
      const existing = this.metrics.get(metricType) || [];
      const lastMetric = existing[existing.length - 1];
      
      if (lastMetric && Date.now() - lastMetric.timestamp < lastMetric.window) {
        lastMetric.count++;
      } else {
        existing.push({
          type: metricType,
          count: 1,
          timestamp: Date.now(),
          window: 60000
        });
        this.metrics.set(metricType, existing);
      }
    }
  }

  /**
   * Detect anomalies
   */
  private detectAnomalies(): void {
    const now = Date.now();
    const window = 300000; // 5 minute window
    const recentEvents = this.events.filter(e => now - e.timestamp < window);

    // Detect brute force attacks
    const failedLogins = recentEvents.filter(
      e => e.type === SecurityEventType.VALIDATION_FAILED && 
          e.message.includes('login')
    );
    
    if (failedLogins.length > this.config.anomalyThreshold) {
      this.createAnomaly(
        AttackPattern.BRUTE_FORCE,
        failedLogins,
        0.8,
        'high',
        'Multiple failed login attempts detected'
      );
    }

    // Detect XSS campaigns
    const xssAttempts = recentEvents.filter(
      e => e.type === SecurityEventType.XSS_ATTEMPT
    );
    
    if (xssAttempts.length > this.config.anomalyThreshold / 2) {
      this.createAnomaly(
        AttackPattern.XSS_CAMPAIGN,
        xssAttempts,
        0.9,
        'critical',
        'Coordinated XSS attack detected'
      );
    }

    // Detect SQL injection scans
    const sqlAttempts = recentEvents.filter(
      e => e.type === SecurityEventType.SQL_INJECTION_ATTEMPT
    );
    
    if (sqlAttempts.length > this.config.anomalyThreshold / 2) {
      this.createAnomaly(
        AttackPattern.SQL_INJECTION_SCAN,
        sqlAttempts,
        0.9,
        'critical',
        'SQL injection vulnerability scan detected'
      );
    }

    // Detect DDoS attempts
    const rateLimitViolations = recentEvents.filter(
      e => e.type === SecurityEventType.RATE_LIMIT_EXCEEDED
    );
    
    if (rateLimitViolations.length > this.config.anomalyThreshold * 2) {
      this.createAnomaly(
        AttackPattern.DDOS_ATTEMPT,
        rateLimitViolations,
        0.7,
        'high',
        'Potential DDoS attack detected'
      );
    }

    // Detect reconnaissance
    const uniqueEndpoints = new Set(
      recentEvents
        .filter(e => e.details?.url)
        .map(e => e.details.url)
    );
    
    if (uniqueEndpoints.size > 50) {
      this.createAnomaly(
        AttackPattern.RECONNAISSANCE,
        recentEvents.slice(0, 10),
        0.6,
        'medium',
        'Potential reconnaissance activity detected'
      );
    }
  }

  /**
   * Create anomaly result
   */
  private createAnomaly(
    pattern: AttackPattern,
    events: SecurityEvent[],
    confidence: number,
    severity: 'low' | 'medium' | 'high' | 'critical',
    description: string
  ): void {
    const anomaly: AnomalyResult = {
      id: securityUtils.generateUUID(),
      pattern,
      confidence,
      severity,
      description,
      events,
      timestamp: Date.now(),
      recommendations: this.getRecommendations(pattern)
    };

    this.anomalies.push(anomaly);
    
    // Limit anomalies array size
    if (this.anomalies.length > this.MAX_ANOMALIES) {
      this.anomalies = this.anomalies.slice(-this.MAX_ANOMALIES);
    }

    // Send real-time alert if enabled
    if (this.config.enableRealTimeAlerts && severity !== 'low') {
      this.sendAlert(anomaly);
    }
  }

  /**
   * Get recommendations for attack pattern
   */
  private getRecommendations(pattern: AttackPattern): string[] {
    const recommendations: Record<AttackPattern, string[]> = {
      [AttackPattern.BRUTE_FORCE]: [
        'Enable account lockout after failed attempts',
        'Implement CAPTCHA for login forms',
        'Use multi-factor authentication',
        'Monitor for credential stuffing lists'
      ],
      [AttackPattern.CREDENTIAL_STUFFING]: [
        'Force password reset for affected accounts',
        'Implement device fingerprinting',
        'Check passwords against breach databases',
        'Enable anomaly detection for login patterns'
      ],
      [AttackPattern.SESSION_HIJACKING]: [
        'Rotate session tokens regularly',
        'Implement session binding to IP/User-Agent',
        'Use secure, httpOnly, sameSite cookies',
        'Enable session timeout'
      ],
      [AttackPattern.XSS_CAMPAIGN]: [
        'Review and update Content Security Policy',
        'Audit all user input handling',
        'Enable XSS protection headers',
        'Implement input validation whitelist'
      ],
      [AttackPattern.SQL_INJECTION_SCAN]: [
        'Use parameterized queries exclusively',
        'Implement stored procedures',
        'Enable SQL query logging',
        'Regular security audits of database access'
      ],
      [AttackPattern.DDOS_ATTEMPT]: [
        'Enable rate limiting',
        'Implement CAPTCHA challenges',
        'Use CDN with DDoS protection',
        'Configure auto-scaling'
      ],
      [AttackPattern.RECONNAISSANCE]: [
        'Limit information disclosure',
        'Implement honeypots',
        'Monitor for automated scanning',
        'Review exposed endpoints'
      ],
      [AttackPattern.PRIVILEGE_ESCALATION]: [
        'Review role-based access controls',
        'Implement principle of least privilege',
        'Audit permission changes',
        'Enable multi-factor for admin actions'
      ]
    };

    return recommendations[pattern] || ['Review security configuration'];
  }

  /**
   * Initialize attack surface
   */
  private initializeAttackSurface(): void {
    // Identify forms
    document.querySelectorAll('form').forEach((form, index) => {
      const item: AttackSurfaceItem = {
        id: `form-${index}`,
        type: 'form',
        name: form.id || form.name || `Form ${index}`,
        risk: form.method?.toUpperCase() === 'POST' ? 'medium' : 'low',
        vulnerabilities: [],
        mitigations: [],
        lastChecked: Date.now()
      };

      // Check for CSRF protection
      const csrfInput = form.querySelector('input[name*="csrf"]');
      if (!csrfInput) {
        item.vulnerabilities.push('Missing CSRF token');
        item.risk = 'high';
      }

      this.attackSurface.set(item.id, item);
    });

    // Identify inputs
    document.querySelectorAll('input, textarea').forEach((input, index) => {
      const element = input as HTMLInputElement;
      const item: AttackSurfaceItem = {
        id: `input-${index}`,
        type: 'input',
        name: element.id || element.name || `Input ${index}`,
        risk: 'low',
        vulnerabilities: [],
        mitigations: [],
        lastChecked: Date.now()
      };

      // Check for validation
      if (!element.pattern && !element.required && element.type === 'text') {
        item.vulnerabilities.push('No input validation');
        item.risk = 'medium';
      }

      // Check for sensitive data
      if (element.type === 'password' && !element.autocomplete) {
        item.vulnerabilities.push('Password field without autocomplete="off"');
      }

      this.attackSurface.set(item.id, item);
    });

    // Check localStorage/sessionStorage
    ['localStorage', 'sessionStorage'].forEach(storage => {
      const item: AttackSurfaceItem = {
        id: storage,
        type: 'storage',
        name: storage,
        risk: 'medium',
        vulnerabilities: [],
        mitigations: [],
        lastChecked: Date.now()
      };

      // Check for sensitive data
      const storageObj = storage === 'localStorage' ? localStorage : sessionStorage;
      Object.keys(storageObj).forEach(key => {
        if (key.includes('token') || key.includes('password') || key.includes('key')) {
          item.vulnerabilities.push(`Potentially sensitive data in ${storage}: ${key}`);
          item.risk = 'high';
        }
      });

      this.attackSurface.set(item.id, item);
    });
  }

  /**
   * Update attack surface
   */
  private updateAttackSurface(): void {
    // Re-scan for new elements
    this.initializeAttackSurface();
    
    // Check for new vulnerabilities
    this.attackSurface.forEach(item => {
      item.lastChecked = Date.now();
      
      // Update risk based on recent events
      const relatedEvents = this.events.filter(
        e => e.details?.source === item.name || 
             e.details?.target === item.name
      );
      
      if (relatedEvents.length > 0) {
        item.risk = 'high';
      }
    });
  }

  /**
   * Check for immediate threats
   */
  private checkImmediateThreats(event: SecurityEvent): void {
    // Critical events require immediate action
    if (event.severity === 'critical') {
      this.sendAlert({
        id: securityUtils.generateUUID(),
        pattern: AttackPattern.PRIVILEGE_ESCALATION,
        confidence: 1,
        severity: 'critical',
        description: `Critical security event: ${event.message}`,
        events: [event],
        timestamp: Date.now(),
        recommendations: ['Immediate investigation required']
      });
    }

    // Multiple high severity events in short time
    const recentHighSeverity = this.events.filter(
      e => e.severity === 'high' && 
           Date.now() - e.timestamp < 60000
    );
    
    if (recentHighSeverity.length > 5) {
      this.sendAlert({
        id: securityUtils.generateUUID(),
        pattern: AttackPattern.RECONNAISSANCE,
        confidence: 0.8,
        severity: 'high',
        description: 'Multiple high severity events detected',
        events: recentHighSeverity,
        timestamp: Date.now(),
        recommendations: ['Review security logs', 'Check for coordinated attack']
      });
    }
  }

  /**
   * Send alert
   */
  private sendAlert(anomaly: AnomalyResult): void {
    // Emit browser event
    const event = new CustomEvent('securityAlert', { detail: anomaly });
    window.dispatchEvent(event);
    
    // Send to webhook if configured
    if (this.config.alertWebhook) {
      fetch(this.config.alertWebhook, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(anomaly)
      }).catch(error => {
        console.error('Failed to send security alert:', error);
      });
    }
    
    // Log to console
    if (this.config.logToConsole) {
      console.error('[SECURITY ALERT]', anomaly);
    }
  }

  /**
   * Send event to server
   */
  private sendToServer(event: SecurityEvent): void {
    // This would send to your logging backend
    // For now, just store in a batch for later sending
    const batch = JSON.parse(sessionStorage.getItem('security_event_batch') || '[]');
    batch.push(event);
    
    if (batch.length >= 10) {
      // Send batch to server
      // apiSecurity.post('/api/security/events', batch);
      sessionStorage.removeItem('security_event_batch');
    } else {
      sessionStorage.setItem('security_event_batch', JSON.stringify(batch));
    }
  }

  /**
   * Setup event listeners
   */
  private setupEventListeners(): void {
    // Listen for security events from other modules
    window.addEventListener('securityEvent', (e: any) => {
      this.logEvent(e.detail);
    });

    // Listen for unhandled errors
    window.addEventListener('error', (e) => {
      this.logEvent({
        type: SecurityEventType.INVALID_INPUT,
        message: `Unhandled error: ${e.message}`,
        details: { 
          filename: e.filename,
          lineno: e.lineno,
          colno: e.colno
        },
        severity: 'medium'
      });
    });

    // Listen for unhandled promise rejections
    window.addEventListener('unhandledrejection', (e) => {
      this.logEvent({
        type: SecurityEventType.INVALID_INPUT,
        message: `Unhandled promise rejection: ${e.reason}`,
        details: { reason: e.reason },
        severity: 'medium'
      });
    });
  }

  /**
   * Add event listener
   */
  public addEventListener(eventType: string, callback: (event: SecurityEvent) => void): void {
    const listeners = this.eventListeners.get(eventType) || new Set();
    listeners.add(callback);
    this.eventListeners.set(eventType, listeners);
  }

  /**
   * Remove event listener
   */
  public removeEventListener(eventType: string, callback: (event: SecurityEvent) => void): void {
    const listeners = this.eventListeners.get(eventType);
    if (listeners) {
      listeners.delete(callback);
    }
  }

  /**
   * Notify listeners
   */
  private notifyListeners(event: SecurityEvent): void {
    const listeners = this.eventListeners.get(event.type) || new Set();
    listeners.forEach(callback => {
      try {
        callback(event);
      } catch (error) {
        console.error('Error in security event listener:', error);
      }
    });
  }

  /**
   * Load historical data
   */
  private loadHistoricalData(): void {
    try {
      const stored = localStorage.getItem('security_monitor_data');
      if (stored) {
        const data = JSON.parse(stored);
        this.events = data.events || [];
        this.anomalies = data.anomalies || [];
      }
    } catch (error) {
      console.error('Failed to load historical security data:', error);
    }
  }

  /**
   * Save data
   */
  private saveData(): void {
    try {
      const data = {
        events: this.events.slice(-1000), // Keep last 1000 events
        anomalies: this.anomalies.slice(-50) // Keep last 50 anomalies
      };
      localStorage.setItem('security_monitor_data', JSON.stringify(data));
    } catch (error) {
      console.error('Failed to save security data:', error);
    }
  }

  /**
   * Clean up old data
   */
  private cleanupOldData(): void {
    const now = Date.now();
    const retentionPeriod = this.config.metricsRetentionDays * 24 * 60 * 60 * 1000;
    
    // Clean events
    this.events = this.events.filter(e => now - e.timestamp < retentionPeriod);
    
    // Clean metrics
    this.metrics.forEach((metricList, type) => {
      const filtered = metricList.filter(m => now - m.timestamp < retentionPeriod);
      this.metrics.set(type, filtered);
    });
    
    // Clean anomalies
    this.anomalies = this.anomalies.filter(a => now - a.timestamp < retentionPeriod);
    
    // Save cleaned data
    this.saveData();
  }

  /**
   * Get security events
   */
  public getEvents(filters?: {
    type?: SecurityEventType;
    severity?: 'low' | 'medium' | 'high' | 'critical';
    since?: number;
    limit?: number;
  }): SecurityEvent[] {
    let events = [...this.events];

    if (filters) {
      if (filters.type) {
        events = events.filter(e => e.type === filters.type);
      }
      if (filters.severity) {
        events = events.filter(e => e.severity === filters.severity);
      }
      if (filters.since) {
        events = events.filter(e => e.timestamp >= filters.since);
      }
      if (filters.limit) {
        events = events.slice(-filters.limit);
      }
    }

    return events;
  }

  /**
   * Get metrics
   */
  public getMetrics(type?: SecurityMetricType): SecurityMetric[] {
    if (type) {
      return this.metrics.get(type) || [];
    }
    
    const allMetrics: SecurityMetric[] = [];
    this.metrics.forEach(metricList => {
      allMetrics.push(...metricList);
    });
    
    return allMetrics;
  }

  /**
   * Get anomalies
   */
  public getAnomalies(filters?: {
    pattern?: AttackPattern;
    severity?: 'low' | 'medium' | 'high' | 'critical';
    since?: number;
  }): AnomalyResult[] {
    let anomalies = [...this.anomalies];

    if (filters) {
      if (filters.pattern) {
        anomalies = anomalies.filter(a => a.pattern === filters.pattern);
      }
      if (filters.severity) {
        anomalies = anomalies.filter(a => a.severity === filters.severity);
      }
      if (filters.since) {
        anomalies = anomalies.filter(a => a.timestamp >= filters.since);
      }
    }

    return anomalies;
  }

  /**
   * Get attack surface
   */
  public getAttackSurface(): AttackSurfaceItem[] {
    return Array.from(this.attackSurface.values());
  }

  /**
   * Get security score
   */
  public getSecurityScore(): {
    score: number;
    breakdown: Record<string, number>;
    recommendations: string[];
  } {
    const breakdown: Record<string, number> = {
      authentication: 0,
      authorization: 0,
      inputValidation: 0,
      outputEncoding: 0,
      encryption: 0,
      monitoring: 0
    };

    // Calculate authentication score
    const hasAuth = authManager.isAuthenticated();
    const hasMFA = false; // Check MFA configuration
    breakdown.authentication = hasAuth ? (hasMFA ? 100 : 70) : 0;

    // Calculate authorization score
    const hasRBAC = authManager.getCurrentUser()?.roles.length > 0;
    breakdown.authorization = hasRBAC ? 80 : 40;

    // Calculate input validation score
    const xssAttempts = this.getMetrics(SecurityMetricType.XSS_ATTEMPTS);
    const sqlAttempts = this.getMetrics(SecurityMetricType.SQL_INJECTION_ATTEMPTS);
    const totalAttempts = xssAttempts.length + sqlAttempts.length;
    breakdown.inputValidation = totalAttempts === 0 ? 100 : Math.max(0, 100 - totalAttempts * 10);

    // Calculate output encoding score
    const hasCSP = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
    breakdown.outputEncoding = hasCSP ? 90 : 50;

    // Calculate encryption score
    const hasHTTPS = window.location.protocol === 'https:';
    const hasSecureStorage = sessionStorage.getItem('secure_') !== null;
    breakdown.encryption = hasHTTPS ? (hasSecureStorage ? 100 : 80) : 40;

    // Calculate monitoring score
    const hasMonitoring = this.config.enableAnomalyDetection && this.config.enableMetricsCollection;
    breakdown.monitoring = hasMonitoring ? 90 : 30;

    // Calculate overall score
    const scores = Object.values(breakdown);
    const score = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);

    // Generate recommendations
    const recommendations: string[] = [];
    
    if (breakdown.authentication < 70) {
      recommendations.push('Enable multi-factor authentication');
    }
    if (breakdown.authorization < 70) {
      recommendations.push('Implement role-based access control');
    }
    if (breakdown.inputValidation < 80) {
      recommendations.push('Strengthen input validation');
    }
    if (breakdown.outputEncoding < 80) {
      recommendations.push('Implement Content Security Policy');
    }
    if (breakdown.encryption < 80) {
      recommendations.push('Enable HTTPS and secure storage');
    }
    if (breakdown.monitoring < 80) {
      recommendations.push('Enable comprehensive security monitoring');
    }

    return { score, breakdown, recommendations };
  }

  /**
   * Generate security report
   */
  public generateReport(): string {
    const score = this.getSecurityScore();
    const events = this.getEvents({ limit: 100 });
    const anomalies = this.getAnomalies();
    const attackSurface = this.getAttackSurface();

    const report = `
# Security Report
Generated: ${new Date().toISOString()}

## Security Score: ${score.score}/100

### Score Breakdown
${Object.entries(score.breakdown)
  .map(([category, value]) => `- ${category}: ${value}/100`)
  .join('\n')}

## Recent Security Events (${events.length})
${events.slice(0, 10)
  .map(e => `- [${e.severity}] ${e.type}: ${e.message}`)
  .join('\n')}

## Detected Anomalies (${anomalies.length})
${anomalies
  .map(a => `- [${a.severity}] ${a.pattern}: ${a.description} (confidence: ${a.confidence})`)
  .join('\n')}

## Attack Surface (${attackSurface.length} items)
${attackSurface
  .filter(i => i.risk === 'high')
  .map(i => `- [${i.risk}] ${i.type}: ${i.name}`)
  .join('\n')}

## Recommendations
${score.recommendations.map(r => `- ${r}`).join('\n')}
    `;

    return report;
  }

  /**
   * Destroy monitor
   */
  public destroy(): void {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }
    
    this.saveData();
    this.eventListeners.clear();
  }
}

/**
 * Default export
 */
export const securityMonitor = SecurityMonitor.getInstance();

/**
 * React hook for security monitoring
 */
export function useSecurityMonitor() {
  return SecurityMonitor.getInstance();
}

/**
 * Export types
 */
export type { SecurityMetric, AnomalyResult, AttackSurfaceItem, MonitorConfig };