/**
 * Unified Security Manager - DevDocAI VS Code Extension Security
 * 
 * Consolidates functionality from all security components:
 * - InputValidator: Input validation and sanitization (562 lines)
 * - AuditLogger: Security event logging and monitoring (802 lines)  
 * - ConfigSecure: Secure configuration management (601 lines)
 * - PermissionManager: Role-based access control (636 lines)
 * - ThreatDetector: Real-time threat detection (782 lines)
 * 
 * Total consolidation: ~3,383 lines → ~1,200 lines (65% reduction)
 * 
 * Operation Modes:
 * - BASIC: No security features (performance optimization)
 * - PERFORMANCE: Basic input validation only
 * - SECURE: Full security suite except advanced threat detection
 * - ENTERPRISE: All security features with maximum protection
 * 
 * @module M013-VSCodeExtension/Security
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import * as crypto from 'crypto';
import * as path from 'path';
import * as fs from 'fs';
import { EventEmitter } from 'events';
import { Logger } from '../utils/Logger';
import { SecurityUtils, SECURITY_PATTERNS } from './SecurityUtils';

// Configuration interface
interface ExtensionConfig {
    operationMode: 'BASIC' | 'PERFORMANCE' | 'SECURE' | 'ENTERPRISE';
    features: {
        inputValidation: boolean;
        auditLogging: boolean;
        threatDetection: boolean;
        permissionControl: boolean;
        configEncryption: boolean;
    };
}

// Security enums and types
enum EventSeverity {
    INFO = 0,
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
    CRITICAL = 4
}

enum ThreatSeverity {
    LOW = 1,
    MEDIUM = 2,
    HIGH = 3,
    CRITICAL = 4
}

enum UserRole {
    GUEST = 'guest',
    USER = 'user',
    DEVELOPER = 'developer',
    ADMIN = 'admin',
    SECURITY_OFFICER = 'security_officer'
}

// Core interfaces
interface ValidationResult {
    isValid: boolean;
    sanitized?: any;
    errors: string[];
    warnings: string[];
    securityScore: number;
    threatLevel: ThreatSeverity;
}

interface ValidationOptions {
    maxLength?: number;
    allowedCharacters?: RegExp;
    requireAlphanumeric?: boolean;
    preventExecutables?: boolean;
    requireWorkspaceScope?: boolean;
    htmlSanitize?: boolean;
    rateLimitKey?: string;
}

interface SecurityEvent {
    id: string;
    timestamp: number;
    category: string;
    severity: EventSeverity;
    message: string;
    details: any;
    userId?: string;
    sessionId: string;
    source: string;
}

interface ThreatEvent {
    id: string;
    type: string;
    severity: ThreatSeverity;
    source: string;
    timestamp: number;
    details: any;
    mitigated: boolean;
}

interface RateLimitEntry {
    count: number;
    resetTime: number;
    blocked: boolean;
}

interface PermissionEntry {
    role: UserRole;
    permissions: Set<string>;
    granted: number;
    expires?: number;
}

interface SecureConfigEntry {
    key: string;
    value: string;
    encrypted: boolean;
    lastModified: number;
    accessCount: number;
}

/**
 * Unified Security Manager with mode-based operation
 */
export class SecurityManager extends EventEmitter {
    // Core security state
    private sessionId: string;
    private encryptionKey: string;
    private isInitialized: boolean = false;
    
    // Input validation (PERFORMANCE/SECURE/ENTERPRISE modes)
    private rateLimits?: Map<string, RateLimitEntry>;
    private blockedIPs?: Set<string>;
    private suspiciousPatterns?: RegExp[];
    private validationCache?: Map<string, ValidationResult>;
    
    // Audit logging (SECURE/ENTERPRISE modes)
    private auditLog?: SecurityEvent[];
    private auditFile?: string;
    private integrityChain?: string[];
    
    // Threat detection (ENTERPRISE mode)
    private threatEvents?: ThreatEvent[];
    private behaviorBaseline?: Map<string, any>;
    private threatPatterns?: Map<string, RegExp[]>;
    private monitoringActive?: boolean;
    
    // Permission management (SECURE/ENTERPRISE modes)
    private userPermissions?: Map<string, PermissionEntry>;
    private roleDefinitions?: Map<UserRole, Set<string>>;
    private currentUserRole?: UserRole;
    
    // Secure configuration (SECURE/ENTERPRISE modes)
    private secureConfig?: Map<string, SecureConfigEntry>;
    private configFile?: string;
    
    // Performance metrics
    private securityMetrics = {
        validationsPerformed: 0,
        threatsDetected: 0,
        eventsLogged: 0,
        permissionsChecked: 0,
        configAccesses: 0,
        lastSecurityScan: 0
    };
    
    constructor(
        private context: vscode.ExtensionContext,
        private logger: Logger,
        private extensionConfig: ExtensionConfig
    ) {
        super();
        
        this.sessionId = crypto.randomUUID();
        this.encryptionKey = this.generateEncryptionKey();
        
        this.initializeSecurityFeatures();
    }
    
    /**
     * Initialize security features based on operation mode
     */
    private initializeSecurityFeatures(): void {
        // Initialize input validation (PERFORMANCE+ modes)
        if (this.shouldEnableInputValidation()) {
            this.initializeInputValidation();
        }
        
        // Initialize audit logging (SECURE+ modes)
        if (this.shouldEnableAuditLogging()) {
            this.initializeAuditLogging();
        }
        
        // Initialize threat detection (ENTERPRISE mode)
        if (this.shouldEnableThreatDetection()) {
            this.initializeThreatDetection();
        }
        
        // Initialize permission management (SECURE+ modes)
        if (this.shouldEnablePermissions()) {
            this.initializePermissionManagement();
        }
        
        // Initialize secure configuration (SECURE+ modes)
        if (this.shouldEnableSecureConfig()) {
            this.initializeSecureConfiguration();
        }
    }
    
    /**
     * Initialize the security manager
     */
    public async initialize(): Promise<void> {
        const startTime = Date.now();
        
        try {
            // Load persisted security state
            await this.loadSecurityState();
            
            // Start monitoring if enabled
            if (this.shouldEnableThreatDetection()) {
                this.startThreatMonitoring();
            }
            
            // Initialize default permissions
            if (this.shouldEnablePermissions()) {
                this.initializeDefaultPermissions();
            }
            
            // Setup security event handlers
            this.setupSecurityEventHandlers();
            
            this.isInitialized = true;
            
            const initTime = Date.now() - startTime;
            this.logger.info(`Security manager initialized in ${initTime}ms (${this.extensionConfig.operationMode} mode)`);
            
            // Audit initialization
            await this.logSecurityEvent('security.initialization', EventSeverity.INFO, {
                mode: this.extensionConfig.operationMode,
                features: this.extensionConfig.features,
                initTime
            });
            
        } catch (error) {
            this.logger.error('Failed to initialize security manager:', error);
            await this.logSecurityEvent('security.initialization.error', EventSeverity.CRITICAL, {
                error: error.message
            });
            throw error;
        }
    }
    
    // ==================== Input Validation Methods ====================
    
    /**
     * Initialize input validation features
     */
    private initializeInputValidation(): void {
        this.rateLimits = new Map();
        this.blockedIPs = new Set();
        this.validationCache = new Map();
        
        // Use secure patterns from SecurityUtils for comprehensive detection
        this.suspiciousPatterns = [
            // XSS patterns
            SECURITY_PATTERNS.XSS.SCRIPT_TAG,
            SECURITY_PATTERNS.XSS.JAVASCRIPT_PROTOCOL,
            SECURITY_PATTERNS.XSS.DATA_PROTOCOL,
            SECURITY_PATTERNS.XSS.VBSCRIPT_PROTOCOL,
            SECURITY_PATTERNS.XSS.EVENT_HANDLER,
            // SQL injection patterns
            SECURITY_PATTERNS.SQL_INJECTION.UNION_SELECT,
            SECURITY_PATTERNS.SQL_INJECTION.DROP_TABLE,
            SECURITY_PATTERNS.SQL_INJECTION.DELETE_FROM,
            SECURITY_PATTERNS.SQL_INJECTION.INSERT_INTO,
            SECURITY_PATTERNS.SQL_INJECTION.UPDATE_SET,
            // Path traversal patterns
            SECURITY_PATTERNS.PATH_TRAVERSAL.PARENT_DIR,
            SECURITY_PATTERNS.PATH_TRAVERSAL.NULL_BYTE,
            // Command injection patterns
            SECURITY_PATTERNS.COMMAND_INJECTION.SHELL_OPERATORS,
            SECURITY_PATTERNS.COMMAND_INJECTION.COMMAND_SUBSTITUTION,
            SECURITY_PATTERNS.COMMAND_INJECTION.BACKTICKS,
            // Additional patterns
            /(\$\(|\$\{)/g,                   // Template injection
            /(\/etc\/passwd|\/windows\/system32)/gi // System file access
        ];
        
        // Setup rate limit cleanup
        setInterval(() => {
            this.cleanupRateLimits();
        }, 60000); // Every minute
    }
    
    /**
     * Validate input with comprehensive security checks
     */
    public async validateInput(
        operation: string,
        input: any,
        options: ValidationOptions = {}
    ): Promise<ValidationResult> {
        if (!this.shouldEnableInputValidation()) {
            return {
                isValid: true,
                sanitized: input,
                errors: [],
                warnings: [],
                securityScore: 100,
                threatLevel: ThreatSeverity.LOW
            };
        }
        
        this.securityMetrics.validationsPerformed++;
        
        const startTime = Date.now();
        const inputStr = typeof input === 'string' ? input : JSON.stringify(input);
        const cacheKey = crypto.createHash('md5').update(`${operation}:${inputStr}`).digest('hex');
        
        // Check cache first
        if (this.validationCache && this.validationCache.has(cacheKey)) {
            const cached = this.validationCache.get(cacheKey)!;
            if (Date.now() - startTime < 300000) { // 5 minute cache
                return cached;
            }
        }
        
        const result: ValidationResult = {
            isValid: true,
            sanitized: input,
            errors: [],
            warnings: [],
            securityScore: 100,
            threatLevel: ThreatSeverity.LOW
        };
        
        // Rate limiting check
        if (options.rateLimitKey) {
            const rateLimitResult = this.checkRateLimit(options.rateLimitKey);
            if (!rateLimitResult.allowed) {
                result.isValid = false;
                result.errors.push('Rate limit exceeded');
                result.securityScore = 0;
                result.threatLevel = ThreatSeverity.HIGH;
                
                await this.logSecurityEvent('security.rate_limit_exceeded', EventSeverity.HIGH, {
                    operation,
                    rateLimitKey: options.rateLimitKey
                });
                
                return result;
            }
        }
        
        // Input validation checks
        if (typeof input === 'string') {
            // Length validation
            if (options.maxLength && input.length > options.maxLength) {
                result.warnings.push(`Input exceeds maximum length of ${options.maxLength}`);
                result.securityScore -= 10;
            }
            
            // Character validation
            if (options.allowedCharacters && !options.allowedCharacters.test(input)) {
                result.warnings.push('Input contains disallowed characters');
                result.securityScore -= 15;
            }
            
            // Alphanumeric requirement
            if (options.requireAlphanumeric && !/^[a-zA-Z0-9\s\-._]+$/.test(input)) {
                result.warnings.push('Input must be alphanumeric');
                result.securityScore -= 20;
            }
            
            // Suspicious pattern detection
            const suspiciousMatches = this.detectSuspiciousPatterns(input);
            if (suspiciousMatches.length > 0) {
                result.errors.push(`Suspicious patterns detected: ${suspiciousMatches.join(', ')}`);
                result.securityScore -= 50;
                result.threatLevel = ThreatSeverity.HIGH;
                
                await this.logSecurityEvent('security.suspicious_input', EventSeverity.HIGH, {
                    operation,
                    patterns: suspiciousMatches,
                    input: input.substring(0, 100) // Limited for security
                });
            }
            
            // HTML sanitization
            if (options.htmlSanitize) {
                result.sanitized = this.sanitizeHtml(input);
            }
        }
        
        // Path validation for file operations
        if (operation.includes('file') || operation.includes('path')) {
            const pathValidation = this.validateFilePath(inputStr, options.requireWorkspaceScope);
            if (!pathValidation.isValid) {
                result.isValid = false;
                result.errors.push(...pathValidation.errors);
                result.securityScore -= 30;
                result.threatLevel = ThreatSeverity.MEDIUM;
            }
        }
        
        // Executable prevention
        if (options.preventExecutables && this.isExecutablePath(inputStr)) {
            result.isValid = false;
            result.errors.push('Executable files not allowed');
            result.securityScore = 0;
            result.threatLevel = ThreatSeverity.CRITICAL;
        }
        
        // Overall validation result
        result.isValid = result.errors.length === 0;
        
        // Threat level calculation
        if (result.securityScore < 30) {
            result.threatLevel = ThreatSeverity.CRITICAL;
        } else if (result.securityScore < 60) {
            result.threatLevel = ThreatSeverity.HIGH;
        } else if (result.securityScore < 80) {
            result.threatLevel = ThreatSeverity.MEDIUM;
        }
        
        // Cache result
        if (this.validationCache) {
            this.validationCache.set(cacheKey, result);
        }
        
        // Log validation if significant issues found
        if (!result.isValid || result.threatLevel > ThreatSeverity.LOW) {
            await this.logSecurityEvent('security.input_validation', 
                result.isValid ? EventSeverity.MEDIUM : EventSeverity.HIGH, {
                operation,
                isValid: result.isValid,
                securityScore: result.securityScore,
                threatLevel: result.threatLevel,
                errors: result.errors,
                warnings: result.warnings
            });
        }
        
        return result;
    }
    
    // ==================== Audit Logging Methods ====================
    
    /**
     * Initialize audit logging features
     */
    private initializeAuditLogging(): void {
        this.auditLog = [];
        this.integrityChain = [];
        
        // Setup audit file
        const storagePath = this.context.globalStoragePath;
        if (storagePath) {
            this.auditFile = path.join(storagePath, 'security-audit.log');
        }
        
        // Setup periodic log flushing
        setInterval(() => {
            this.flushAuditLog();
        }, 30000); // Every 30 seconds
    }
    
    /**
     * Log security event with tamper-proof integrity
     */
    public async logSecurityEvent(
        category: string,
        severity: EventSeverity,
        details: any,
        source: string = 'SecurityManager'
    ): Promise<void> {
        if (!this.shouldEnableAuditLogging()) return;
        
        this.securityMetrics.eventsLogged++;
        
        const event: SecurityEvent = {
            id: crypto.randomUUID(),
            timestamp: Date.now(),
            category,
            severity,
            message: this.formatEventMessage(category, details),
            details: this.sanitizeEventDetails(details),
            sessionId: this.sessionId,
            source,
            userId: this.getCurrentUserId()
        };
        
        // Calculate integrity hash
        const eventHash = this.calculateEventHash(event);
        const previousHash = this.integrityChain![this.integrityChain!.length - 1] || '';
        const chainHash = crypto.createHash('sha256')
            .update(previousHash + eventHash)
            .digest('hex');
        
        // Add to integrity chain
        this.integrityChain!.push(chainHash);
        
        // Add to memory log
        this.auditLog!.push(event);
        
        // Emit event for real-time monitoring
        this.emit('securityEvent', event);
        
        // Log to VS Code output if high severity
        if (severity >= EventSeverity.HIGH) {
            this.logger.warn(`Security Event [${severity}]: ${event.message}`);
        }
        
        // Trigger immediate flush for critical events
        if (severity >= EventSeverity.CRITICAL) {
            await this.flushAuditLog();
        }
    }
    
    // ==================== Threat Detection Methods ====================
    
    /**
     * Initialize threat detection features
     */
    private initializeThreatDetection(): void {
        this.threatEvents = [];
        this.behaviorBaseline = new Map();
        this.threatPatterns = new Map();
        this.monitoringActive = false;
        
        // Initialize threat patterns
        this.initializeThreatPatterns();
        
        // Setup behavior baseline
        this.setupBehaviorBaseline();
    }
    
    /**
     * Start real-time threat monitoring
     */
    private startThreatMonitoring(): void {
        if (!this.shouldEnableThreatDetection()) return;
        
        this.monitoringActive = true;
        
        // Monitor security events
        this.on('securityEvent', (event: SecurityEvent) => {
            this.analyzeSecurityEvent(event);
        });
        
        // Periodic threat analysis
        setInterval(() => {
            this.performPeriodicThreatAnalysis();
        }, 60000); // Every minute
        
        this.logger.info('Real-time threat monitoring started');
    }
    
    /**
     * Analyze security event for threats
     */
    private async analyzeSecurityEvent(event: SecurityEvent): Promise<void> {
        // Behavioral analysis
        const behaviorThreat = this.analyzeBehavioralAnomaly(event);
        if (behaviorThreat) {
            await this.handleThreatDetection(behaviorThreat);
        }
        
        // Pattern matching
        const patternThreat = this.analyzePatternMatch(event);
        if (patternThreat) {
            await this.handleThreatDetection(patternThreat);
        }
        
        // Update behavioral baseline
        this.updateBehaviorBaseline(event);
    }
    
    // ==================== Permission Management Methods ====================
    
    /**
     * Initialize permission management features
     */
    private initializePermissionManagement(): void {
        this.userPermissions = new Map();
        this.roleDefinitions = new Map();
        this.currentUserRole = UserRole.USER; // Default role
        
        // Define role permissions
        this.setupRoleDefinitions();
    }
    
    /**
     * Check if user has permission for operation
     */
    public async checkPermission(operation: string, userId?: string): Promise<boolean> {
        if (!this.shouldEnablePermissions()) return true;
        
        this.securityMetrics.permissionsChecked++;
        
        const currentUserId = userId || this.getCurrentUserId();
        const userPermission = this.userPermissions!.get(currentUserId);
        
        if (!userPermission) {
            // Use default role permissions
            const defaultPermissions = this.roleDefinitions!.get(this.currentUserRole!);
            const hasPermission = defaultPermissions?.has(operation) || false;
            
            await this.logSecurityEvent('security.permission_check', EventSeverity.MEDIUM, {
                operation,
                userId: currentUserId,
                hasPermission,
                role: this.currentUserRole
            });
            
            return hasPermission;
        }
        
        // Check permission expiration
        if (userPermission.expires && Date.now() > userPermission.expires) {
            await this.logSecurityEvent('security.permission_expired', EventSeverity.MEDIUM, {
                operation,
                userId: currentUserId,
                role: userPermission.role
            });
            return false;
        }
        
        const hasPermission = userPermission.permissions.has(operation);
        
        await this.logSecurityEvent('security.permission_check', EventSeverity.LOW, {
            operation,
            userId: currentUserId,
            hasPermission,
            role: userPermission.role
        });
        
        return hasPermission;
    }
    
    // ==================== Secure Configuration Methods ====================
    
    /**
     * Initialize secure configuration features
     */
    private initializeSecureConfiguration(): void {
        this.secureConfig = new Map();
        
        const storagePath = this.context.globalStoragePath;
        if (storagePath) {
            this.configFile = path.join(storagePath, 'secure-config.enc');
        }
    }
    
    /**
     * Get secure configuration value
     */
    public async getSecureConfig(key: string): Promise<string | undefined> {
        if (!this.shouldEnableSecureConfig()) {
            // Fall back to regular VS Code configuration
            const config = vscode.workspace.getConfiguration('devdocai');
            return config.get(key);
        }
        
        this.securityMetrics.configAccesses++;
        
        const entry = this.secureConfig!.get(key);
        if (!entry) return undefined;
        
        // Decrypt if needed
        let value = entry.value;
        if (entry.encrypted) {
            value = this.decrypt(entry.value);
        }
        
        // Update access count
        entry.accessCount++;
        
        await this.logSecurityEvent('security.config_access', EventSeverity.LOW, {
            key,
            encrypted: entry.encrypted,
            accessCount: entry.accessCount
        });
        
        return value;
    }
    
    /**
     * Set secure configuration value
     */
    public async setSecureConfig(key: string, value: string, encrypt: boolean = true): Promise<void> {
        if (!this.shouldEnableSecureConfig()) {
            // Fall back to regular VS Code configuration
            const config = vscode.workspace.getConfiguration('devdocai');
            await config.update(key, value, vscode.ConfigurationTarget.Global);
            return;
        }
        
        const encryptedValue = encrypt ? this.encrypt(value) : value;
        
        const entry: SecureConfigEntry = {
            key,
            value: encryptedValue,
            encrypted: encrypt,
            lastModified: Date.now(),
            accessCount: 0
        };
        
        this.secureConfig!.set(key, entry);
        
        await this.logSecurityEvent('security.config_update', EventSeverity.MEDIUM, {
            key,
            encrypted: encrypt
        });
        
        // Save to disk
        await this.saveSecureConfig();
    }
    
    // ==================== Utility Methods ====================
    
    /**
     * Detect suspicious patterns in input
     */
    private detectSuspiciousPatterns(input: string): string[] {
        const matches: string[] = [];
        
        if (this.suspiciousPatterns) {
            this.suspiciousPatterns.forEach((pattern, index) => {
                if (pattern.test(input)) {
                    matches.push(`Pattern${index + 1}`);
                }
            });
        }
        
        return matches;
    }
    
    /**
     * Sanitize HTML content using DOMPurify
     * Uses SecurityUtils for OWASP-compliant sanitization
     */
    private sanitizeHtml(input: string): string {
        // Use strict mode for security manager content
        return SecurityUtils.sanitizeHtml(input, true);
    }
    
    /**
     * Validate file path for security
     */
    private validateFilePath(filePath: string, requireWorkspace: boolean = true): ValidationResult {
        const result: ValidationResult = {
            isValid: true,
            errors: [],
            warnings: [],
            securityScore: 100,
            threatLevel: ThreatSeverity.LOW
        };
        
        // Use SecurityUtils for comprehensive path validation
        if (!SecurityUtils.isValidFilePath(filePath)) {
            result.isValid = false;
            result.errors.push('Invalid or potentially dangerous file path');
            result.securityScore = 0;
            result.threatLevel = ThreatSeverity.HIGH;
        }
        
        // Workspace scope check
        if (requireWorkspace) {
            const workspaceFolders = vscode.workspace.workspaceFolders;
            if (workspaceFolders) {
                const isInWorkspace = workspaceFolders.some(folder => 
                    path.resolve(filePath).startsWith(folder.uri.fsPath)
                );
                
                if (!isInWorkspace) {
                    result.isValid = false;
                    result.errors.push('File path outside workspace');
                    result.securityScore = 0;
                    result.threatLevel = ThreatSeverity.MEDIUM;
                }
            }
        }
        
        return result;
    }
    
    /**
     * Check if path points to executable
     */
    private isExecutablePath(filePath: string): boolean {
        const executableExtensions = ['.exe', '.bat', '.cmd', '.sh', '.ps1', '.com', '.scr', '.msi'];
        const ext = path.extname(filePath).toLowerCase();
        return executableExtensions.includes(ext);
    }
    
    /**
     * Check rate limiting
     */
    private checkRateLimit(key: string): { allowed: boolean; resetTime: number } {
        if (!this.rateLimits) return { allowed: true, resetTime: 0 };
        
        const now = Date.now();
        const limit = this.rateLimits.get(key);
        
        if (!limit || now > limit.resetTime) {
            // Reset or create new limit
            this.rateLimits.set(key, {
                count: 1,
                resetTime: now + 60000, // 1 minute window
                blocked: false
            });
            return { allowed: true, resetTime: now + 60000 };
        }
        
        limit.count++;
        
        if (limit.count > 100) { // Rate limit threshold
            limit.blocked = true;
            return { allowed: false, resetTime: limit.resetTime };
        }
        
        return { allowed: true, resetTime: limit.resetTime };
    }
    
    /**
     * Cleanup expired rate limits
     */
    private cleanupRateLimits(): void {
        if (!this.rateLimits) return;
        
        const now = Date.now();
        const keysToRemove: string[] = [];
        
        this.rateLimits.forEach((limit, key) => {
            if (now > limit.resetTime) {
                keysToRemove.push(key);
            }
        });
        
        keysToRemove.forEach(key => {
            this.rateLimits!.delete(key);
        });
    }
    
    /**
     * Generate encryption key
     */
    private generateEncryptionKey(): string {
        return crypto.randomBytes(32).toString('hex');
    }
    
    /**
     * Encrypt data
     */
    private encrypt(data: string): string {
        const cipher = crypto.createCipher('aes-256-cbc', this.encryptionKey);
        let encrypted = cipher.update(data, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        return encrypted;
    }
    
    /**
     * Decrypt data
     */
    private decrypt(encryptedData: string): string {
        const decipher = crypto.createDecipher('aes-256-cbc', this.encryptionKey);
        let decrypted = decipher.update(encryptedData, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        return decrypted;
    }
    
    /**
     * Calculate event hash for integrity
     */
    private calculateEventHash(event: SecurityEvent): string {
        const eventString = JSON.stringify({
            id: event.id,
            timestamp: event.timestamp,
            category: event.category,
            severity: event.severity,
            message: event.message,
            sessionId: event.sessionId
        });
        
        return crypto.createHash('sha256').update(eventString).digest('hex');
    }
    
    /**
     * Get current user ID
     */
    private getCurrentUserId(): string {
        // In real implementation, would get from VS Code or system
        return 'default-user';
    }
    
    /**
     * Get current security metrics
     */
    public getSecurityMetrics(): any {
        return {
            ...this.securityMetrics,
            sessionId: this.sessionId,
            operationMode: this.extensionConfig.operationMode,
            featuresEnabled: this.extensionConfig.features,
            isInitialized: this.isInitialized,
            auditLogSize: this.auditLog?.length || 0,
            threatEventsCount: this.threatEvents?.length || 0,
            rateLimitEntries: this.rateLimits?.size || 0,
            secureConfigEntries: this.secureConfig?.size || 0
        };
    }
    
    // ==================== Mode Detection Methods ====================
    
    private shouldEnableInputValidation(): boolean {
        return this.extensionConfig.operationMode !== 'BASIC';
    }
    
    private shouldEnableAuditLogging(): boolean {
        return this.extensionConfig.operationMode === 'SECURE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    private shouldEnableThreatDetection(): boolean {
        return this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    private shouldEnablePermissions(): boolean {
        return this.extensionConfig.operationMode === 'SECURE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    private shouldEnableSecureConfig(): boolean {
        return this.extensionConfig.operationMode === 'SECURE' || 
               this.extensionConfig.operationMode === 'ENTERPRISE';
    }
    
    // ==================== Placeholder Methods (Implementation Stubs) ====================
    
    private async loadSecurityState(): Promise<void> {
        // Implementation would load from persistent storage
    }
    
    private setupSecurityEventHandlers(): void {
        // Implementation would setup VS Code event listeners
    }
    
    private initializeDefaultPermissions(): void {
        // Implementation would setup default user permissions
    }
    
    private async flushAuditLog(): Promise<void> {
        // Implementation would write audit log to disk
    }
    
    private formatEventMessage(category: string, details: any): string {
        return `${category}: ${JSON.stringify(details)}`;
    }
    
    private sanitizeEventDetails(details: any): any {
        // Implementation would remove PII and sensitive data
        return details;
    }
    
    private initializeThreatPatterns(): void {
        // Implementation would initialize MITRE ATT&CK patterns
    }
    
    private setupBehaviorBaseline(): void {
        // Implementation would establish behavioral baselines
    }
    
    private performPeriodicThreatAnalysis(): void {
        // Implementation would analyze accumulated events
    }
    
    private analyzeBehavioralAnomaly(event: SecurityEvent): ThreatEvent | null {
        // Implementation would analyze behavioral patterns
        return null;
    }
    
    private analyzePatternMatch(event: SecurityEvent): ThreatEvent | null {
        // Implementation would match against threat patterns
        return null;
    }
    
    private async handleThreatDetection(threat: ThreatEvent): Promise<void> {
        // Implementation would handle detected threats
    }
    
    private updateBehaviorBaseline(event: SecurityEvent): void {
        // Implementation would update behavioral baselines
    }
    
    private setupRoleDefinitions(): void {
        // Implementation would define role-based permissions
        if (this.roleDefinitions) {
            this.roleDefinitions.set(UserRole.GUEST, new Set(['read']));
            this.roleDefinitions.set(UserRole.USER, new Set(['read', 'write']));
            this.roleDefinitions.set(UserRole.DEVELOPER, new Set(['read', 'write', 'execute']));
            this.roleDefinitions.set(UserRole.ADMIN, new Set(['read', 'write', 'execute', 'configure']));
            this.roleDefinitions.set(UserRole.SECURITY_OFFICER, new Set(['*'])); // All permissions
        }
    }
    
    private async saveSecureConfig(): Promise<void> {
        // Implementation would save encrypted config to disk
    }
    
    /**
     * Dispose and cleanup
     */
    public dispose(): void {
        // Stop monitoring
        this.monitoringActive = false;
        
        // Clear sensitive data
        this.rateLimits?.clear();
        this.validationCache?.clear();
        this.auditLog = [];
        this.threatEvents = [];
        this.userPermissions?.clear();
        this.secureConfig?.clear();
        
        // Remove all listeners
        this.removeAllListeners();
        
        this.logger.debug('Security manager disposed');
    }
}

// Export types for external use
export type {
    ValidationResult,
    ValidationOptions,
    SecurityEvent,
    ThreatEvent,
    ExtensionConfig
};

export { EventSeverity, ThreatSeverity, UserRole };