/**
 * Permission Manager - Role-Based Access Control (RBAC)
 * 
 * Provides enterprise-grade authorization and access control:
 * - Role-based permissions (Basic, Power User, Admin, Enterprise)
 * - Command-level authorization
 * - Resource access control
 * - Permission inheritance and delegation
 * - Integration with audit logging
 * 
 * Follows principle of least privilege and zero-trust security model.
 * 
 * @module M013-VSCodeExtension/Security
 * @version 3.0.0
 */

import * as vscode from 'vscode';
import { InputValidator, ValidationResult } from './InputValidator';

// User roles in ascending privilege order
export enum UserRole {
    BASIC = 0,      // Basic documentation operations
    POWER = 1,      // Advanced features, templates, quality analysis
    ADMIN = 2,      // Security scans, configuration, user management
    ENTERPRISE = 3  // All features, system configuration, audit access
}

// Permission categories
export enum PermissionCategory {
    DOCUMENTATION = 'documentation',
    QUALITY = 'quality',
    SECURITY = 'security',
    CONFIGURATION = 'configuration',
    TEMPLATES = 'templates',
    EXPORT = 'export',
    SYSTEM = 'system',
    AUDIT = 'audit'
}

// Specific permissions
export enum Permission {
    // Documentation permissions
    GENERATE_DOC = 'generate_documentation',
    VIEW_DOC = 'view_documentation',
    DELETE_DOC = 'delete_documentation',
    BULK_GENERATE = 'bulk_generate',
    
    // Quality permissions
    ANALYZE_QUALITY = 'analyze_quality',
    VIEW_METRICS = 'view_metrics',
    QUALITY_REPORTS = 'quality_reports',
    
    // Security permissions
    RUN_SECURITY_SCAN = 'run_security_scan',
    VIEW_SECURITY_REPORTS = 'view_security_reports',
    CONFIGURE_SECURITY = 'configure_security',
    ACCESS_AUDIT_LOGS = 'access_audit_logs',
    
    // Configuration permissions
    MODIFY_SETTINGS = 'modify_settings',
    MANAGE_API_KEYS = 'manage_api_keys',
    CONFIGURE_PROVIDERS = 'configure_providers',
    SYSTEM_CONFIG = 'system_configuration',
    
    // Template permissions
    USE_TEMPLATES = 'use_templates',
    CREATE_TEMPLATES = 'create_templates',
    MANAGE_TEMPLATES = 'manage_templates',
    SHARE_TEMPLATES = 'share_templates',
    
    // Export permissions
    EXPORT_BASIC = 'export_basic',
    EXPORT_ADVANCED = 'export_advanced',
    BULK_EXPORT = 'bulk_export',
    
    // System permissions
    VIEW_SYSTEM_INFO = 'view_system_info',
    MANAGE_PROCESSES = 'manage_processes',
    ACCESS_LOGS = 'access_logs'
}

// Permission grant interface
interface PermissionGrant {
    permission: Permission;
    granted: boolean;
    reason?: string;
    expires?: number;
    conditions?: string[];
}

// User context for authorization
interface UserContext {
    role: UserRole;
    workspace?: string;
    sessionId: string;
    lastActivity: number;
    permissions: Set<Permission>;
    temporaryGrants: Map<Permission, number>; // permission -> expiry time
    restrictions: string[];
}

// Authorization result
export interface AuthorizationResult {
    granted: boolean;
    reason: string;
    requiredRole?: UserRole;
    missingPermissions?: Permission[];
    conditions?: string[];
    securityScore: number;
}

export class PermissionManager {
    private userContext: UserContext;
    private rolePermissions: Map<UserRole, Set<Permission>> = new Map();
    private commandPermissions: Map<string, Permission[]> = new Map();
    private resourceAccess: Map<string, Permission> = new Map();
    private sessionTimeout: number = 8 * 60 * 60 * 1000; // 8 hours
    
    constructor(
        private context: vscode.ExtensionContext,
        private inputValidator: InputValidator
    ) {
        this.initializeRolePermissions();
        this.initializeCommandPermissions();
        this.initializeResourceAccess();
        this.userContext = this.loadUserContext();
    }
    
    /**
     * Initializes role-based permission mappings
     */
    private initializeRolePermissions(): void {
        // BASIC role permissions
        this.rolePermissions.set(UserRole.BASIC, new Set([
            Permission.GENERATE_DOC,
            Permission.VIEW_DOC,
            Permission.USE_TEMPLATES,
            Permission.ANALYZE_QUALITY,
            Permission.VIEW_METRICS,
            Permission.EXPORT_BASIC
        ]));
        
        // POWER role permissions (inherits BASIC + additional)
        const powerPermissions = new Set(this.rolePermissions.get(UserRole.BASIC));
        powerPermissions.add(Permission.DELETE_DOC);
        powerPermissions.add(Permission.BULK_GENERATE);
        powerPermissions.add(Permission.CREATE_TEMPLATES);
        powerPermissions.add(Permission.QUALITY_REPORTS);
        powerPermissions.add(Permission.EXPORT_ADVANCED);
        powerPermissions.add(Permission.MODIFY_SETTINGS);
        this.rolePermissions.set(UserRole.POWER, powerPermissions);
        
        // ADMIN role permissions (inherits POWER + additional)
        const adminPermissions = new Set(this.rolePermissions.get(UserRole.POWER));
        adminPermissions.add(Permission.RUN_SECURITY_SCAN);
        adminPermissions.add(Permission.VIEW_SECURITY_REPORTS);
        adminPermissions.add(Permission.CONFIGURE_SECURITY);
        adminPermissions.add(Permission.MANAGE_API_KEYS);
        adminPermissions.add(Permission.MANAGE_TEMPLATES);
        adminPermissions.add(Permission.SHARE_TEMPLATES);
        adminPermissions.add(Permission.BULK_EXPORT);
        adminPermissions.add(Permission.VIEW_SYSTEM_INFO);
        this.rolePermissions.set(UserRole.ADMIN, adminPermissions);
        
        // ENTERPRISE role permissions (inherits ADMIN + additional)
        const enterprisePermissions = new Set(this.rolePermissions.get(UserRole.ADMIN));
        enterprisePermissions.add(Permission.ACCESS_AUDIT_LOGS);
        enterprisePermissions.add(Permission.CONFIGURE_PROVIDERS);
        enterprisePermissions.add(Permission.SYSTEM_CONFIG);
        enterprisePermissions.add(Permission.MANAGE_PROCESSES);
        enterprisePermissions.add(Permission.ACCESS_LOGS);
        this.rolePermissions.set(UserRole.ENTERPRISE, enterprisePermissions);
    }
    
    /**
     * Maps commands to required permissions
     */
    private initializeCommandPermissions(): void {
        this.commandPermissions.set('devdocai.generateDocumentation', [Permission.GENERATE_DOC]);
        this.commandPermissions.set('devdocai.analyzeQuality', [Permission.ANALYZE_QUALITY]);
        this.commandPermissions.set('devdocai.runSecurityScan', [Permission.RUN_SECURITY_SCAN]);
        this.commandPermissions.set('devdocai.configureSettings', [Permission.MODIFY_SETTINGS]);
        this.commandPermissions.set('devdocai.selectTemplate', [Permission.USE_TEMPLATES]);
        this.commandPermissions.set('devdocai.exportDocumentation', [Permission.EXPORT_BASIC]);
        this.commandPermissions.set('devdocai.refreshDocumentation', [Permission.GENERATE_DOC]);
        this.commandPermissions.set('devdocai.showMIAIRInsights', [Permission.VIEW_METRICS]);
        this.commandPermissions.set('devdocai.toggleAutoDoc', [Permission.MODIFY_SETTINGS]);
    }
    
    /**
     * Maps resources to required permissions
     */
    private initializeResourceAccess(): void {
        this.resourceAccess.set('/templates', Permission.USE_TEMPLATES);
        this.resourceAccess.set('/security', Permission.RUN_SECURITY_SCAN);
        this.resourceAccess.set('/config', Permission.MODIFY_SETTINGS);
        this.resourceAccess.set('/audit', Permission.ACCESS_AUDIT_LOGS);
        this.resourceAccess.set('/system', Permission.VIEW_SYSTEM_INFO);
    }
    
    /**
     * Checks if user is authorized for a specific command
     */
    public async authorizeCommand(commandId: string, context?: any): Promise<AuthorizationResult> {
        // Validate command ID
        const commandValidation = this.inputValidator.validateParameter(
            'commandId',
            commandId,
            { maxLength: 100, requireAlphanumeric: false }
        );
        
        if (!commandValidation.isValid) {
            return {
                granted: false,
                reason: 'Invalid command ID',
                securityScore: 0
            };
        }
        
        // Check session validity
        if (!this.isSessionValid()) {
            return {
                granted: false,
                reason: 'Session expired or invalid',
                securityScore: 0
            };
        }
        
        // Get required permissions for command
        const requiredPermissions = this.commandPermissions.get(commandId) || [];
        if (requiredPermissions.length === 0) {
            // Command not registered - deny by default (fail-secure)
            return {
                granted: false,
                reason: `Command ${commandId} not authorized`,
                securityScore: 20
            };
        }
        
        // Check each required permission
        const missingPermissions: Permission[] = [];
        for (const permission of requiredPermissions) {
            if (!this.hasPermission(permission)) {
                missingPermissions.push(permission);
            }
        }
        
        if (missingPermissions.length > 0) {
            const requiredRole = this.getMinimumRoleForPermissions(missingPermissions);
            return {
                granted: false,
                reason: `Insufficient permissions. Required: ${missingPermissions.join(', ')}`,
                requiredRole,
                missingPermissions,
                securityScore: 30
            };
        }
        
        // Additional context-based checks
        const contextCheck = await this.checkContextualRestrictions(commandId, context);
        if (!contextCheck.granted) {
            return contextCheck;
        }
        
        // Update activity timestamp
        this.userContext.lastActivity = Date.now();
        
        return {
            granted: true,
            reason: 'Authorized',
            securityScore: 100
        };
    }
    
    /**
     * Checks if user can access a specific resource
     */
    public async authorizeResource(resourcePath: string, operation: 'read' | 'write' | 'delete'): Promise<AuthorizationResult> {
        // Validate resource path
        const pathValidation = this.inputValidator.validateFilePath(resourcePath, {
            requireWorkspaceScope: true
        });
        
        if (!pathValidation.isValid) {
            return {
                granted: false,
                reason: 'Invalid resource path',
                securityScore: 0
            };
        }
        
        // Check session validity
        if (!this.isSessionValid()) {
            return {
                granted: false,
                reason: 'Session expired',
                securityScore: 0
            };
        }
        
        // Determine required permission based on resource and operation
        const basePermission = this.resourceAccess.get(resourcePath) || Permission.VIEW_DOC;
        const requiredPermission = this.getPermissionForOperation(basePermission, operation);
        
        if (!this.hasPermission(requiredPermission)) {
            return {
                granted: false,
                reason: `Insufficient permissions for ${operation} operation on ${resourcePath}`,
                missingPermissions: [requiredPermission],
                securityScore: 25
            };
        }
        
        return {
            granted: true,
            reason: 'Resource access authorized',
            securityScore: 100
        };
    }
    
    /**
     * Grants temporary permission for specific operations
     */
    public async grantTemporaryPermission(
        permission: Permission, 
        durationMs: number,
        reason: string
    ): Promise<ValidationResult> {
        // Validate inputs
        const reasonValidation = this.inputValidator.validateParameter(
            'reason',
            reason,
            { maxLength: 500 }
        );
        
        if (!reasonValidation.isValid) {
            return reasonValidation;
        }
        
        // Check if current role can grant this permission
        if (this.userContext.role < UserRole.ADMIN) {
            return {
                isValid: false,
                errors: ['Insufficient privileges to grant permissions'],
                warnings: [],
                securityScore: 0
            };
        }
        
        // Limit duration (max 24 hours)
        const maxDuration = 24 * 60 * 60 * 1000;
        const actualDuration = Math.min(durationMs, maxDuration);
        const expiryTime = Date.now() + actualDuration;
        
        this.userContext.temporaryGrants.set(permission, expiryTime);
        
        // Save to persistent storage
        await this.saveUserContext();
        
        return {
            isValid: true,
            errors: [],
            warnings: [],
            securityScore: 90
        };
    }
    
    /**
     * Elevates user role temporarily
     */
    public async elevateRole(
        targetRole: UserRole,
        durationMs: number,
        justification: string
    ): Promise<AuthorizationResult> {
        // Validate justification
        const justificationValidation = this.inputValidator.validateParameter(
            'justification',
            justification,
            { maxLength: 1000 }
        );
        
        if (!justificationValidation.isValid) {
            return {
                granted: false,
                reason: 'Invalid justification',
                securityScore: 0
            };
        }
        
        // Check if elevation is allowed
        if (targetRole <= this.userContext.role) {
            return {
                granted: false,
                reason: 'Cannot elevate to same or lower role',
                securityScore: 30
            };
        }
        
        if (this.userContext.role < UserRole.ADMIN) {
            return {
                granted: false,
                reason: 'Insufficient privileges for role elevation',
                securityScore: 20
            };
        }
        
        // Limit duration (max 1 hour for role elevation)
        const maxDuration = 60 * 60 * 1000;
        const actualDuration = Math.min(durationMs, maxDuration);
        
        // Temporarily elevate permissions
        const targetPermissions = this.rolePermissions.get(targetRole) || new Set();
        for (const permission of targetPermissions) {
            if (!this.userContext.permissions.has(permission)) {
                this.userContext.temporaryGrants.set(permission, Date.now() + actualDuration);
            }
        }
        
        await this.saveUserContext();
        
        return {
            granted: true,
            reason: `Role elevated to ${UserRole[targetRole]} for ${actualDuration / 1000} seconds`,
            securityScore: 85
        };
    }
    
    /**
     * Checks if user has specific permission
     */
    public hasPermission(permission: Permission): boolean {
        // Check permanent permissions
        if (this.userContext.permissions.has(permission)) {
            return true;
        }
        
        // Check temporary grants
        const tempGrantExpiry = this.userContext.temporaryGrants.get(permission);
        if (tempGrantExpiry && Date.now() < tempGrantExpiry) {
            return true;
        }
        
        // Clean up expired temporary grants
        if (tempGrantExpiry && Date.now() >= tempGrantExpiry) {
            this.userContext.temporaryGrants.delete(permission);
        }
        
        return false;
    }
    
    /**
     * Gets user's current role
     */
    public getUserRole(): UserRole {
        return this.userContext.role;
    }
    
    /**
     * Gets all user permissions (permanent + temporary)
     */
    public getUserPermissions(): Permission[] {
        const allPermissions = new Set(this.userContext.permissions);
        
        // Add non-expired temporary grants
        const now = Date.now();
        for (const [permission, expiry] of this.userContext.temporaryGrants) {
            if (now < expiry) {
                allPermissions.add(permission);
            }
        }
        
        return Array.from(allPermissions);
    }
    
    /**
     * Checks session validity
     */
    private isSessionValid(): boolean {
        const now = Date.now();
        const timeSinceActivity = now - this.userContext.lastActivity;
        
        if (timeSinceActivity > this.sessionTimeout) {
            return false;
        }
        
        return true;
    }
    
    /**
     * Checks contextual restrictions
     */
    private async checkContextualRestrictions(commandId: string, context?: any): Promise<AuthorizationResult> {
        // Time-based restrictions (e.g., no security scans during business hours)
        if (commandId === 'devdocai.runSecurityScan') {
            const hour = new Date().getHours();
            if (hour >= 9 && hour <= 17) { // Business hours
                return {
                    granted: false,
                    reason: 'Security scans not allowed during business hours',
                    securityScore: 40
                };
            }
        }
        
        // Rate limiting per user/command
        const rateLimitResult = this.inputValidator.validateRateLimit(
            `user-${this.userContext.sessionId}-${commandId}`,
            this.userContext.role === UserRole.ENTERPRISE ? 100 : 50
        );
        
        if (!rateLimitResult.isValid) {
            return {
                granted: false,
                reason: 'Rate limit exceeded for this command',
                securityScore: 10
            };
        }
        
        return {
            granted: true,
            reason: 'Context checks passed',
            securityScore: 100
        };
    }
    
    /**
     * Gets minimum role required for given permissions
     */
    private getMinimumRoleForPermissions(permissions: Permission[]): UserRole {
        let minRole = UserRole.BASIC;
        
        for (const [role, rolePermissions] of this.rolePermissions) {
            const hasAllPermissions = permissions.every(p => rolePermissions.has(p));
            if (hasAllPermissions) {
                return role;
            }
            if (permissions.some(p => rolePermissions.has(p))) {
                minRole = Math.max(minRole, role);
            }
        }
        
        return minRole;
    }
    
    /**
     * Gets permission required for specific operation
     */
    private getPermissionForOperation(basePermission: Permission, operation: string): Permission {
        switch (operation) {
            case 'write':
            case 'delete':
                // Map to higher privilege permissions
                if (basePermission === Permission.VIEW_DOC) return Permission.GENERATE_DOC;
                if (basePermission === Permission.USE_TEMPLATES) return Permission.CREATE_TEMPLATES;
                return basePermission;
            case 'read':
            default:
                return basePermission;
        }
    }
    
    /**
     * Loads user context from storage
     */
    private loadUserContext(): UserContext {
        const storedContext = this.context.globalState.get<any>('userContext');
        
        if (storedContext) {
            return {
                role: storedContext.role || UserRole.BASIC,
                workspace: storedContext.workspace,
                sessionId: storedContext.sessionId || this.generateSessionId(),
                lastActivity: storedContext.lastActivity || Date.now(),
                permissions: new Set(storedContext.permissions || this.rolePermissions.get(UserRole.BASIC)),
                temporaryGrants: new Map(storedContext.temporaryGrants || []),
                restrictions: storedContext.restrictions || []
            };
        }
        
        // Default context for new users
        return {
            role: UserRole.BASIC,
            sessionId: this.generateSessionId(),
            lastActivity: Date.now(),
            permissions: this.rolePermissions.get(UserRole.BASIC) || new Set(),
            temporaryGrants: new Map(),
            restrictions: []
        };
    }
    
    /**
     * Saves user context to storage
     */
    private async saveUserContext(): Promise<void> {
        const contextToSave = {
            role: this.userContext.role,
            workspace: this.userContext.workspace,
            sessionId: this.userContext.sessionId,
            lastActivity: this.userContext.lastActivity,
            permissions: Array.from(this.userContext.permissions),
            temporaryGrants: Array.from(this.userContext.temporaryGrants.entries()),
            restrictions: this.userContext.restrictions
        };
        
        await this.context.globalState.update('userContext', contextToSave);
    }
    
    /**
     * Generates secure session ID
     */
    private generateSessionId(): string {
        const crypto = require('crypto');
        return crypto.randomBytes(16).toString('hex');
    }
    
    /**
     * Gets security summary for audit purposes
     */
    public getSecuritySummary(): any {
        return {
            role: UserRole[this.userContext.role],
            permissionCount: this.userContext.permissions.size,
            temporaryGrantCount: this.userContext.temporaryGrants.size,
            sessionValid: this.isSessionValid(),
            lastActivity: new Date(this.userContext.lastActivity).toISOString(),
            restrictions: this.userContext.restrictions.length
        };
    }
    
    /**
     * Disposes permission manager
     */
    public async dispose(): Promise<void> {
        await this.saveUserContext();
    }
}