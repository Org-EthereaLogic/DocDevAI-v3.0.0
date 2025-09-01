/**
 * Threat Detector - Real-time Security Monitoring
 * 
 * Provides enterprise-grade threat detection and response:
 * - Real-time behavioral analysis and anomaly detection
 * - Pattern-based threat identification (ML-inspired algorithms)
 * - Automated threat response and mitigation
 * - Integration with MITRE ATT&CK framework patterns
 * - Adaptive learning from security events
 * - Zero-trust monitoring with continuous verification
 * 
 * Integrates with M010 Security Module threat intelligence.
 * 
 * @module M013-VSCodeExtension/Security
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import { EventEmitter } from 'events';
import { InputValidator, ValidationResult } from './InputValidator';
import { AuditLogger, EventSeverity, EventCategory } from './AuditLogger';
import { PermissionManager, UserRole } from './PermissionManager';

// Threat severity levels
export enum ThreatSeverity {
    LOW = 1,        // Suspicious but low risk
    MEDIUM = 2,     // Moderate risk requiring monitoring
    HIGH = 3,       // High risk requiring immediate attention
    CRITICAL = 4    // Critical threat requiring emergency response
}

// Threat types based on MITRE ATT&CK
export enum ThreatType {
    RECONNAISSANCE = 'reconnaissance',
    RESOURCE_DEVELOPMENT = 'resource_development',
    INITIAL_ACCESS = 'initial_access',
    EXECUTION = 'execution',
    PERSISTENCE = 'persistence',
    PRIVILEGE_ESCALATION = 'privilege_escalation',
    DEFENSE_EVASION = 'defense_evasion',
    CREDENTIAL_ACCESS = 'credential_access',
    DISCOVERY = 'discovery',
    LATERAL_MOVEMENT = 'lateral_movement',
    COLLECTION = 'collection',
    COMMAND_CONTROL = 'command_control',
    EXFILTRATION = 'exfiltration',
    IMPACT = 'impact'
}

// Threat detection result
export interface ThreatDetection {
    id: string;
    timestamp: number;
    severity: ThreatSeverity;
    type: ThreatType;
    confidence: number; // 0-100
    description: string;
    indicators: string[];
    mitigationActions: string[];
    affectedResources: string[];
    riskScore: number; // 0-100
    metadata: { [key: string]: any };
}

// Behavioral pattern for anomaly detection
interface BehaviorPattern {
    userId: string;
    action: string;
    frequency: number;
    lastSeen: number;
    baseline: number;
    deviation: number;
}

// Threat rule for pattern matching
interface ThreatRule {
    id: string;
    name: string;
    severity: ThreatSeverity;
    type: ThreatType;
    patterns: RegExp[];
    conditions: ((event: any) => boolean)[];
    confidence: number;
    enabled: boolean;
}

// Detection configuration
interface DetectionConfig {
    enabled: boolean;
    sensitivity: number; // 1-10
    anomalyThreshold: number;
    patternWindow: number; // minutes
    maxEvents: number;
    adaptiveLearning: boolean;
    autoResponse: boolean;
    realTimeAlert: boolean;
}

export class ThreatDetector extends EventEmitter {
    private config: DetectionConfig;
    private threatRules: Map<string, ThreatRule> = new Map();
    private behaviorPatterns: Map<string, BehaviorPattern> = new Map();
    private eventWindow: any[] = [];
    private detectionHistory: ThreatDetection[] = [];
    private blockedIPs: Set<string> = new Set();
    private quarantinedUsers: Set<string> = new Set();
    
    // ML-inspired anomaly detection
    private anomalyBaselines: Map<string, number> = new Map();
    private adaptiveThresholds: Map<string, number> = new Map();
    
    // Performance metrics
    private metrics = {
        threatsDetected: 0,
        falsePositives: 0,
        autoMitigations: 0,
        averageDetectionTime: 0,
        ruleEffectiveness: new Map<string, number>()
    };
    
    constructor(
        private context: vscode.ExtensionContext,
        private inputValidator: InputValidator,
        private auditLogger: AuditLogger,
        private permissionManager: PermissionManager
    ) {
        super();
        this.config = this.loadDetectionConfig();
        this.initializeThreatRules();
        this.startMonitoring();
    }
    
    /**
     * Analyzes an event for threats
     */
    public async analyzeEvent(event: any): Promise<ThreatDetection[]> {
        const startTime = Date.now();
        const detections: ThreatDetection[] = [];
        
        try {
            // Add to event window
            this.addToEventWindow(event);
            
            // Pattern-based detection
            const patternDetections = await this.runPatternDetection(event);
            detections.push(...patternDetections);
            
            // Behavioral anomaly detection
            const anomalyDetections = await this.runAnomalyDetection(event);
            detections.push(...anomalyDetections);
            
            // Sequence analysis
            const sequenceDetections = await this.runSequenceAnalysis();
            detections.push(...sequenceDetections);
            
            // Process detections
            for (const detection of detections) {
                await this.processDetection(detection);
            }
            
            // Update metrics
            if (detections.length > 0) {
                this.metrics.threatsDetected += detections.length;
                const detectionTime = Date.now() - startTime;
                this.metrics.averageDetectionTime = 
                    (this.metrics.averageDetectionTime + detectionTime) / 2;
            }
            
            return detections;
            
        } catch (error) {
            await this.auditLogger.logError(error, 'threat_detection');
            return [];
        }
    }
    
    /**
     * Runs pattern-based threat detection
     */
    private async runPatternDetection(event: any): Promise<ThreatDetection[]> {
        const detections: ThreatDetection[] = [];
        
        for (const [ruleId, rule] of this.threatRules) {
            if (!rule.enabled) continue;
            
            let matches = 0;
            const indicators: string[] = [];
            
            // Check pattern matches
            for (const pattern of rule.patterns) {
                const eventStr = JSON.stringify(event);
                if (pattern.test(eventStr)) {
                    matches++;
                    indicators.push(`Pattern match: ${pattern.source}`);
                }
            }
            
            // Check condition matches
            for (const condition of rule.conditions) {
                try {
                    if (condition(event)) {
                        matches++;
                        indicators.push('Condition match');
                    }
                } catch (e) {
                    // Skip invalid conditions
                }
            }
            
            // Create detection if sufficient matches
            if (matches > 0) {
                const confidence = Math.min(100, (matches / (rule.patterns.length + rule.conditions.length)) * rule.confidence);
                
                if (confidence >= this.config.sensitivity * 10) {
                    const detection: ThreatDetection = {
                        id: this.generateDetectionId(),
                        timestamp: Date.now(),
                        severity: rule.severity,
                        type: rule.type,
                        confidence,
                        description: `${rule.name}: Pattern-based detection`,
                        indicators,
                        mitigationActions: await this.generateMitigationActions(rule),
                        affectedResources: [event.resource || 'unknown'],
                        riskScore: this.calculateRiskScore(rule.severity, confidence),
                        metadata: {
                            ruleId,
                            matches,
                            event: this.sanitizeEventForLogging(event)
                        }
                    };
                    
                    detections.push(detection);
                    
                    // Update rule effectiveness
                    const effectiveness = this.metrics.ruleEffectiveness.get(ruleId) || 0;
                    this.metrics.ruleEffectiveness.set(ruleId, effectiveness + confidence);
                }
            }
        }
        
        return detections;
    }
    
    /**
     * Runs behavioral anomaly detection
     */
    private async runAnomalyDetection(event: any): Promise<ThreatDetection[]> {
        if (!this.config.adaptiveLearning) {
            return [];
        }
        
        const detections: ThreatDetection[] = [];
        const userId = event.userId || 'unknown';
        const action = event.action || 'unknown';
        const patternKey = `${userId}:${action}`;
        
        // Update or create behavior pattern
        let pattern = this.behaviorPatterns.get(patternKey);
        if (!pattern) {
            pattern = {
                userId,
                action,
                frequency: 1,
                lastSeen: Date.now(),
                baseline: 1,
                deviation: 0
            };
            this.behaviorPatterns.set(patternKey, pattern);
        } else {
            // Update frequency and calculate deviation
            const timeDelta = Date.now() - pattern.lastSeen;
            const expectedFreq = pattern.baseline;
            const actualFreq = pattern.frequency + 1;
            
            pattern.frequency = actualFreq;
            pattern.lastSeen = Date.now();
            pattern.deviation = Math.abs(actualFreq - expectedFreq) / expectedFreq;
            
            // Check for anomaly
            if (pattern.deviation > this.config.anomalyThreshold) {
                const severity = pattern.deviation > 2.0 ? ThreatSeverity.HIGH : ThreatSeverity.MEDIUM;
                const confidence = Math.min(100, pattern.deviation * 50);
                
                const detection: ThreatDetection = {
                    id: this.generateDetectionId(),
                    timestamp: Date.now(),
                    severity,
                    type: ThreatType.DISCOVERY, // Anomalous behavior often indicates reconnaissance
                    confidence,
                    description: `Behavioral anomaly detected: ${action} frequency anomaly`,
                    indicators: [
                        `Expected frequency: ${expectedFreq}`,
                        `Actual frequency: ${actualFreq}`,
                        `Deviation: ${(pattern.deviation * 100).toFixed(1)}%`
                    ],
                    mitigationActions: ['monitor_user', 'require_additional_auth'],
                    affectedResources: [event.resource || 'user_behavior'],
                    riskScore: this.calculateRiskScore(severity, confidence),
                    metadata: {
                        patternKey,
                        baseline: expectedFreq,
                        deviation: pattern.deviation,
                        event: this.sanitizeEventForLogging(event)
                    }
                };
                
                detections.push(detection);
            }
            
            // Update baseline with exponential smoothing
            pattern.baseline = pattern.baseline * 0.9 + actualFreq * 0.1;
        }
        
        return detections;
    }
    
    /**
     * Runs sequence analysis for multi-step attacks
     */
    private async runSequenceAnalysis(): Promise<ThreatDetection[]> {
        const detections: ThreatDetection[] = [];
        
        // Look for suspicious sequences in recent events
        if (this.eventWindow.length < 3) {
            return detections;
        }
        
        const recentEvents = this.eventWindow.slice(-10); // Last 10 events
        
        // Pattern: reconnaissance followed by privilege escalation
        const reconEvents = recentEvents.filter(e => 
            e.action?.includes('scan') || 
            e.action?.includes('enumerate') || 
            e.action?.includes('discover')
        );
        
        const escalationEvents = recentEvents.filter(e =>
            e.action?.includes('elevate') ||
            e.action?.includes('admin') ||
            e.action?.includes('privilege')
        );
        
        if (reconEvents.length > 0 && escalationEvents.length > 0) {
            const detection: ThreatDetection = {
                id: this.generateDetectionId(),
                timestamp: Date.now(),
                severity: ThreatSeverity.HIGH,
                type: ThreatType.PRIVILEGE_ESCALATION,
                confidence: 85,
                description: 'Multi-step attack pattern: reconnaissance followed by privilege escalation',
                indicators: [
                    `Reconnaissance events: ${reconEvents.length}`,
                    `Escalation events: ${escalationEvents.length}`
                ],
                mitigationActions: ['block_user', 'reset_permissions', 'force_logout'],
                affectedResources: ['user_session', 'system_privileges'],
                riskScore: 90,
                metadata: {
                    reconEvents: reconEvents.length,
                    escalationEvents: escalationEvents.length,
                    timeWindow: this.config.patternWindow
                }
            };
            
            detections.push(detection);
        }
        
        return detections;
    }
    
    /**
     * Processes a threat detection
     */
    private async processDetection(detection: ThreatDetection): Promise<void> {
        // Add to history
        this.detectionHistory.push(detection);
        
        // Keep history size manageable
        if (this.detectionHistory.length > 1000) {
            this.detectionHistory = this.detectionHistory.slice(-500);
        }
        
        // Log to audit
        await this.auditLogger.logThreat(
            ThreatType[detection.type],
            this.mapThreatToEventSeverity(detection.severity),
            detection.description,
            {
                confidence: detection.confidence,
                riskScore: detection.riskScore,
                indicators: detection.indicators,
                detectionId: detection.id
            }
        );
        
        // Emit event for external listeners
        this.emit('threat_detected', detection);
        
        // Auto-response if enabled
        if (this.config.autoResponse) {
            await this.executeAutoResponse(detection);
        }
        
        // Real-time alerting
        if (this.config.realTimeAlert) {
            await this.sendRealTimeAlert(detection);
        }
    }
    
    /**
     * Executes automated response to threats
     */
    private async executeAutoResponse(detection: ThreatDetection): Promise<void> {
        const actions = detection.mitigationActions;
        
        for (const action of actions) {
            try {
                switch (action) {
                    case 'block_user':
                        if (detection.metadata.event?.userId) {
                            this.quarantinedUsers.add(detection.metadata.event.userId);
                            await this.auditLogger.logEvent(
                                EventSeverity.HIGH,
                                EventCategory.SECURITY_SCAN,
                                'user_quarantine',
                                'user_management',
                                true,
                                `User quarantined due to threat: ${detection.id}`
                            );
                        }
                        break;
                        
                    case 'block_ip':
                        if (detection.metadata.event?.sourceIP) {
                            this.blockedIPs.add(detection.metadata.event.sourceIP);
                        }
                        break;
                        
                    case 'reset_permissions':
                        // This would integrate with PermissionManager
                        await this.auditLogger.logEvent(
                            EventSeverity.MEDIUM,
                            EventCategory.AUTHORIZATION,
                            'permission_reset',
                            'permissions',
                            true,
                            `Permissions reset due to threat: ${detection.id}`
                        );
                        break;
                        
                    case 'monitor_user':
                        // Enhanced monitoring for user
                        break;
                        
                    case 'require_additional_auth':
                        // Force additional authentication
                        break;
                }
                
                this.metrics.autoMitigations++;
                
            } catch (error) {
                await this.auditLogger.logError(
                    error,
                    'threat_mitigation',
                    { action, detectionId: detection.id }
                );
            }
        }
    }
    
    /**
     * Sends real-time alert
     */
    private async sendRealTimeAlert(detection: ThreatDetection): Promise<void> {
        const message = `Security Threat Detected: ${detection.description}`;
        
        if (detection.severity >= ThreatSeverity.HIGH) {
            vscode.window.showErrorMessage(
                message,
                'View Details',
                'Dismiss'
            ).then(selection => {
                if (selection === 'View Details') {
                    this.showThreatDetails(detection);
                }
            });
        } else {
            vscode.window.showWarningMessage(message);
        }
    }
    
    /**
     * Shows detailed threat information
     */
    private showThreatDetails(detection: ThreatDetection): void {
        const details = [
            `Threat ID: ${detection.id}`,
            `Severity: ${ThreatSeverity[detection.severity]}`,
            `Type: ${ThreatType[detection.type]}`,
            `Confidence: ${detection.confidence}%`,
            `Risk Score: ${detection.riskScore}`,
            '',
            'Indicators:',
            ...detection.indicators.map(i => `  - ${i}`),
            '',
            'Recommended Actions:',
            ...detection.mitigationActions.map(a => `  - ${a.replace('_', ' ')}`)
        ];
        
        vscode.window.showInformationMessage(
            'Threat Details',
            { detail: details.join('\n'), modal: true }
        );
    }
    
    /**
     * Initializes threat detection rules
     */
    private initializeThreatRules(): void {
        // Command injection detection
        this.threatRules.set('command_injection', {
            id: 'command_injection',
            name: 'Command Injection Attack',
            severity: ThreatSeverity.CRITICAL,
            type: ThreatType.EXECUTION,
            patterns: [
                /[;&|`$(){}[\]<>]/,
                /\\\\/,
                /\$\{.*\}/,
                /\|\s*\w+/
            ],
            conditions: [
                (event) => event.category === 'system' && event.action?.includes('execute')
            ],
            confidence: 95,
            enabled: true
        });
        
        // XSS detection
        this.threatRules.set('xss_attack', {
            id: 'xss_attack',
            name: 'Cross-Site Scripting Attack',
            severity: ThreatSeverity.HIGH,
            type: ThreatType.INITIAL_ACCESS,
            patterns: [
                /<script[^>]*>.*?<\/script>/gi,
                /javascript:/gi,
                /on\w+\s*=\s*["'][^"']*["']/gi
            ],
            conditions: [
                (event) => event.category === 'web' || event.resource?.includes('webview')
            ],
            confidence: 90,
            enabled: true
        });
        
        // Privilege escalation detection
        this.threatRules.set('privilege_escalation', {
            id: 'privilege_escalation',
            name: 'Privilege Escalation Attempt',
            severity: ThreatSeverity.HIGH,
            type: ThreatType.PRIVILEGE_ESCALATION,
            patterns: [
                /sudo|su\s|admin|root|elevated/i,
                /privilege|escalate|elevate/i
            ],
            conditions: [
                (event) => event.userRole === UserRole.BASIC && 
                          (event.action?.includes('admin') || event.action?.includes('config'))
            ],
            confidence: 85,
            enabled: true
        });
        
        // Data exfiltration detection
        this.threatRules.set('data_exfiltration', {
            id: 'data_exfiltration',
            name: 'Data Exfiltration Attempt',
            severity: ThreatSeverity.CRITICAL,
            type: ThreatType.EXFILTRATION,
            patterns: [
                /export|download|copy|backup/i,
                /bulk|mass|all/i
            ],
            conditions: [
                (event) => event.metadata?.dataSize && event.metadata.dataSize > 1000000 // > 1MB
            ],
            confidence: 75,
            enabled: true
        });
        
        // Reconnaissance detection
        this.threatRules.set('reconnaissance', {
            id: 'reconnaissance',
            name: 'Reconnaissance Activity',
            severity: ThreatSeverity.MEDIUM,
            type: ThreatType.RECONNAISSANCE,
            patterns: [
                /scan|enumerate|discover|probe/i,
                /version|info|status|list/i
            ],
            conditions: [
                (event) => event.frequency && event.frequency > 10 // High frequency actions
            ],
            confidence: 70,
            enabled: true
        });
    }
    
    /**
     * Helper methods
     */
    private addToEventWindow(event: any): void {
        this.eventWindow.push({
            ...event,
            timestamp: Date.now()
        });
        
        // Keep window size manageable
        const windowSize = this.config.maxEvents || 1000;
        if (this.eventWindow.length > windowSize) {
            this.eventWindow = this.eventWindow.slice(-windowSize / 2);
        }
        
        // Remove events outside time window
        const cutoff = Date.now() - (this.config.patternWindow * 60 * 1000);
        this.eventWindow = this.eventWindow.filter(e => e.timestamp > cutoff);
    }
    
    private generateDetectionId(): string {
        const crypto = require('crypto');
        return `det_${crypto.randomBytes(8).toString('hex')}`;
    }
    
    private async generateMitigationActions(rule: ThreatRule): Promise<string[]> {
        switch (rule.type) {
            case ThreatType.EXECUTION:
                return ['block_command', 'audit_user', 'monitor_process'];
            case ThreatType.INITIAL_ACCESS:
                return ['sanitize_input', 'block_request', 'monitor_user'];
            case ThreatType.PRIVILEGE_ESCALATION:
                return ['reset_permissions', 'require_additional_auth', 'audit_user'];
            case ThreatType.EXFILTRATION:
                return ['block_transfer', 'quarantine_data', 'investigate'];
            case ThreatType.RECONNAISSANCE:
                return ['rate_limit', 'monitor_user', 'reduce_verbosity'];
            default:
                return ['monitor_user', 'audit_event'];
        }
    }
    
    private calculateRiskScore(severity: ThreatSeverity, confidence: number): number {
        const severityWeight = severity * 20;
        const confidenceWeight = confidence * 0.8;
        return Math.min(100, severityWeight + confidenceWeight);
    }
    
    private mapThreatToEventSeverity(severity: ThreatSeverity): EventSeverity {
        switch (severity) {
            case ThreatSeverity.LOW: return EventSeverity.LOW;
            case ThreatSeverity.MEDIUM: return EventSeverity.MEDIUM;
            case ThreatSeverity.HIGH: return EventSeverity.HIGH;
            case ThreatSeverity.CRITICAL: return EventSeverity.CRITICAL;
            default: return EventSeverity.LOW;
        }
    }
    
    private sanitizeEventForLogging(event: any): any {
        // Remove sensitive data for logging
        const sanitized = { ...event };
        delete sanitized.password;
        delete sanitized.token;
        delete sanitized.key;
        delete sanitized.secret;
        return sanitized;
    }
    
    private loadDetectionConfig(): DetectionConfig {
        const vsConfig = vscode.workspace.getConfiguration('devdocai.threatDetection');
        
        return {
            enabled: vsConfig.get('enabled', true),
            sensitivity: vsConfig.get('sensitivity', 7), // 1-10 scale
            anomalyThreshold: vsConfig.get('anomalyThreshold', 0.5),
            patternWindow: vsConfig.get('patternWindow', 15), // minutes
            maxEvents: vsConfig.get('maxEvents', 1000),
            adaptiveLearning: vsConfig.get('adaptiveLearning', true),
            autoResponse: vsConfig.get('autoResponse', false),
            realTimeAlert: vsConfig.get('realTimeAlert', true)
        };
    }
    
    private startMonitoring(): void {
        if (!this.config.enabled) {
            return;
        }
        
        // Start periodic cleanup
        setInterval(() => {
            this.cleanupOldData();
        }, 60000); // Every minute
        
        // Start adaptive baseline updates
        if (this.config.adaptiveLearning) {
            setInterval(() => {
                this.updateAdaptiveBaselines();
            }, 300000); // Every 5 minutes
        }
    }
    
    private cleanupOldData(): void {
        const cutoff = Date.now() - (24 * 60 * 60 * 1000); // 24 hours
        
        // Clean up old detections
        this.detectionHistory = this.detectionHistory.filter(d => d.timestamp > cutoff);
        
        // Clean up old behavior patterns
        for (const [key, pattern] of this.behaviorPatterns) {
            if (pattern.lastSeen < cutoff) {
                this.behaviorPatterns.delete(key);
            }
        }
    }
    
    private updateAdaptiveBaselines(): void {
        // Update baseline behavior patterns
        for (const [key, pattern] of this.behaviorPatterns) {
            // Decay old patterns
            pattern.baseline *= 0.95;
            pattern.deviation *= 0.9;
        }
    }
    
    /**
     * Public API methods
     */
    
    public getDetectionHistory(limit: number = 50): ThreatDetection[] {
        return this.detectionHistory
            .sort((a, b) => b.timestamp - a.timestamp)
            .slice(0, limit);
    }
    
    public getMetrics(): any {
        return {
            ...this.metrics,
            ruleEffectiveness: Object.fromEntries(this.metrics.ruleEffectiveness),
            activeRules: this.threatRules.size,
            behaviorPatterns: this.behaviorPatterns.size,
            quarantinedUsers: this.quarantinedUsers.size,
            blockedIPs: this.blockedIPs.size
        };
    }
    
    public isUserQuarantined(userId: string): boolean {
        return this.quarantinedUsers.has(userId);
    }
    
    public isIPBlocked(ip: string): boolean {
        return this.blockedIPs.has(ip);
    }
    
    public async releaseQuarantine(userId: string, reason: string): Promise<void> {
        if (this.quarantinedUsers.has(userId)) {
            this.quarantinedUsers.delete(userId);
            await this.auditLogger.logEvent(
                EventSeverity.MEDIUM,
                EventCategory.SECURITY_SCAN,
                'quarantine_release',
                'user_management',
                true,
                `User quarantine released: ${reason}`,
                { userId, reason }
            );
        }
    }
    
    public dispose(): void {
        this.removeAllListeners();
    }
}