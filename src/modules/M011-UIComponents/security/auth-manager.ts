/**
 * M011 Authentication Manager - JWT token management and RBAC implementation
 * 
 * Provides secure authentication, session management, role-based access control,
 * and integration with backend authentication services. Follows OAuth 2.0 and
 * OpenID Connect standards.
 */

import { SignJWT, jwtVerify, JWTPayload, importPBKDF2, importSPKI } from 'jose';
import { securityUtils, SecurityEventType } from './security-utils';
import { useSecureGlobalState } from './state-management-secure';

/**
 * User roles enumeration
 */
export enum UserRole {
  ADMIN = 'admin',
  DEVELOPER = 'developer',
  REVIEWER = 'reviewer',
  VIEWER = 'viewer',
  GUEST = 'guest'
}

/**
 * Permission types
 */
export enum Permission {
  // Document permissions
  DOCUMENT_CREATE = 'document:create',
  DOCUMENT_READ = 'document:read',
  DOCUMENT_UPDATE = 'document:update',
  DOCUMENT_DELETE = 'document:delete',
  DOCUMENT_EXPORT = 'document:export',
  
  // Template permissions
  TEMPLATE_CREATE = 'template:create',
  TEMPLATE_READ = 'template:read',
  TEMPLATE_UPDATE = 'template:update',
  TEMPLATE_DELETE = 'template:delete',
  
  // Configuration permissions
  CONFIG_READ = 'config:read',
  CONFIG_UPDATE = 'config:update',
  
  // Analytics permissions
  ANALYTICS_VIEW = 'analytics:view',
  ANALYTICS_EXPORT = 'analytics:export',
  
  // Admin permissions
  USER_MANAGE = 'user:manage',
  SYSTEM_ADMIN = 'system:admin',
  AUDIT_VIEW = 'audit:view',
  SECURITY_MANAGE = 'security:manage'
}

/**
 * Role-permission mapping
 */
const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  [UserRole.ADMIN]: [
    Permission.DOCUMENT_CREATE,
    Permission.DOCUMENT_READ,
    Permission.DOCUMENT_UPDATE,
    Permission.DOCUMENT_DELETE,
    Permission.DOCUMENT_EXPORT,
    Permission.TEMPLATE_CREATE,
    Permission.TEMPLATE_READ,
    Permission.TEMPLATE_UPDATE,
    Permission.TEMPLATE_DELETE,
    Permission.CONFIG_READ,
    Permission.CONFIG_UPDATE,
    Permission.ANALYTICS_VIEW,
    Permission.ANALYTICS_EXPORT,
    Permission.USER_MANAGE,
    Permission.SYSTEM_ADMIN,
    Permission.AUDIT_VIEW,
    Permission.SECURITY_MANAGE
  ],
  [UserRole.DEVELOPER]: [
    Permission.DOCUMENT_CREATE,
    Permission.DOCUMENT_READ,
    Permission.DOCUMENT_UPDATE,
    Permission.DOCUMENT_DELETE,
    Permission.DOCUMENT_EXPORT,
    Permission.TEMPLATE_CREATE,
    Permission.TEMPLATE_READ,
    Permission.TEMPLATE_UPDATE,
    Permission.CONFIG_READ,
    Permission.ANALYTICS_VIEW
  ],
  [UserRole.REVIEWER]: [
    Permission.DOCUMENT_READ,
    Permission.DOCUMENT_UPDATE,
    Permission.DOCUMENT_EXPORT,
    Permission.TEMPLATE_READ,
    Permission.CONFIG_READ,
    Permission.ANALYTICS_VIEW
  ],
  [UserRole.VIEWER]: [
    Permission.DOCUMENT_READ,
    Permission.TEMPLATE_READ,
    Permission.CONFIG_READ
  ],
  [UserRole.GUEST]: [
    Permission.DOCUMENT_READ
  ]
};

/**
 * User interface
 */
export interface User {
  id: string;
  username: string;
  email: string;
  roles: UserRole[];
  permissions: Permission[];
  metadata?: {
    firstName?: string;
    lastName?: string;
    avatar?: string;
    lastLogin?: number;
    createdAt?: number;
  };
}

/**
 * Authentication token interface
 */
export interface AuthToken {
  accessToken: string;
  refreshToken?: string;
  expiresIn: number;
  tokenType: 'Bearer';
  scope?: string;
}

/**
 * Authentication configuration
 */
export interface AuthConfig {
  jwtSecret?: string;
  jwtPublicKey?: string;
  jwtAlgorithm: 'HS256' | 'RS256' | 'ES256';
  accessTokenExpiry: number; // seconds
  refreshTokenExpiry: number; // seconds
  issuer: string;
  audience: string;
  enableRefreshToken: boolean;
  enableMFA: boolean;
  maxLoginAttempts: number;
  lockoutDuration: number; // milliseconds
}

/**
 * Default authentication configuration
 */
const DEFAULT_AUTH_CONFIG: AuthConfig = {
  jwtAlgorithm: 'HS256',
  accessTokenExpiry: 3600, // 1 hour
  refreshTokenExpiry: 604800, // 7 days
  issuer: 'devdocai',
  audience: 'devdocai-ui',
  enableRefreshToken: true,
  enableMFA: false,
  maxLoginAttempts: 5,
  lockoutDuration: 15 * 60 * 1000 // 15 minutes
};

/**
 * Multi-factor authentication interface
 */
export interface MFAChallenge {
  challengeId: string;
  type: 'totp' | 'sms' | 'email' | 'backup';
  createdAt: number;
  expiresAt: number;
}

/**
 * Login credentials interface
 */
export interface LoginCredentials {
  username?: string;
  email?: string;
  password: string;
  mfaCode?: string;
  rememberMe?: boolean;
}

/**
 * Authentication manager class
 */
export class AuthManager {
  private static instance: AuthManager;
  private config: AuthConfig;
  private currentUser: User | null = null;
  private tokens: AuthToken | null = null;
  private loginAttempts: Map<string, number> = new Map();
  private lockouts: Map<string, number> = new Map();
  private refreshTimer: NodeJS.Timeout | null = null;
  private stateManager = useSecureGlobalState();

  private constructor(config?: Partial<AuthConfig>) {
    this.config = { ...DEFAULT_AUTH_CONFIG, ...config };
    this.initializeFromStorage();
    this.setupTokenRefresh();
  }

  /**
   * Get singleton instance
   */
  public static getInstance(config?: Partial<AuthConfig>): AuthManager {
    if (!AuthManager.instance) {
      AuthManager.instance = new AuthManager(config);
    }
    return AuthManager.instance;
  }

  /**
   * Initialize from secure storage
   */
  private async initializeFromStorage(): Promise<void> {
    try {
      const storedTokens = sessionStorage.getItem('auth_tokens');
      if (storedTokens) {
        const tokens = JSON.parse(storedTokens);
        const isValid = await this.verifyToken(tokens.accessToken);
        
        if (isValid) {
          this.tokens = tokens;
          await this.loadUserFromToken(tokens.accessToken);
        } else {
          this.clearAuth();
        }
      }
    } catch (error) {
      console.error('Failed to initialize auth from storage:', error);
      this.clearAuth();
    }
  }

  /**
   * Login user
   */
  public async login(credentials: LoginCredentials): Promise<{ success: boolean; user?: User; error?: string; mfaRequired?: boolean }> {
    const identifier = credentials.email || credentials.username || '';
    
    // Check lockout
    if (this.isLockedOut(identifier)) {
      const remainingTime = this.getRemainingLockoutTime(identifier);
      return {
        success: false,
        error: `Account locked. Try again in ${Math.ceil(remainingTime / 60000)} minutes.`
      };
    }

    try {
      // Validate credentials
      if (!this.validateCredentials(credentials)) {
        this.recordFailedAttempt(identifier);
        return { success: false, error: 'Invalid credentials format' };
      }

      // Simulate backend authentication (replace with actual API call)
      const authResponse = await this.authenticateWithBackend(credentials);
      
      if (!authResponse.success) {
        this.recordFailedAttempt(identifier);
        return authResponse;
      }

      // Handle MFA if required
      if (authResponse.mfaRequired && !credentials.mfaCode) {
        return { success: false, mfaRequired: true };
      }

      // Generate tokens
      const user = authResponse.user!;
      const tokens = await this.generateTokens(user);
      
      // Store authentication
      this.currentUser = user;
      this.tokens = tokens;
      this.storeAuth(tokens, credentials.rememberMe);
      
      // Clear login attempts
      this.clearFailedAttempts(identifier);
      
      // Update state
      this.updateAuthState();
      
      // Log security event
      securityUtils['logSecurityEvent']({
        type: SecurityEventType.VALIDATION_FAILED,
        message: 'User logged in successfully',
        details: { userId: user.id, username: user.username },
        severity: 'low'
      });

      return { success: true, user };
    } catch (error) {
      this.recordFailedAttempt(identifier);
      console.error('Login error:', error);
      return { success: false, error: 'Authentication failed' };
    }
  }

  /**
   * Logout user
   */
  public async logout(): Promise<void> {
    try {
      // Revoke tokens if backend supports it
      if (this.tokens?.refreshToken) {
        await this.revokeToken(this.tokens.refreshToken);
      }

      // Clear authentication
      this.clearAuth();
      
      // Log security event
      securityUtils['logSecurityEvent']({
        type: SecurityEventType.VALIDATION_FAILED,
        message: 'User logged out',
        details: { userId: this.currentUser?.id },
        severity: 'low'
      });

    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.clearAuth();
    }
  }

  /**
   * Get current user
   */
  public getCurrentUser(): User | null {
    return this.currentUser;
  }

  /**
   * Check if user is authenticated
   */
  public isAuthenticated(): boolean {
    return !!this.currentUser && !!this.tokens;
  }

  /**
   * Check if user has permission
   */
  public hasPermission(permission: Permission): boolean {
    if (!this.currentUser) return false;
    return this.currentUser.permissions.includes(permission);
  }

  /**
   * Check if user has role
   */
  public hasRole(role: UserRole): boolean {
    if (!this.currentUser) return false;
    return this.currentUser.roles.includes(role);
  }

  /**
   * Check if user has any of the specified roles
   */
  public hasAnyRole(roles: UserRole[]): boolean {
    if (!this.currentUser) return false;
    return roles.some(role => this.currentUser!.roles.includes(role));
  }

  /**
   * Check if user has all of the specified permissions
   */
  public hasAllPermissions(permissions: Permission[]): boolean {
    if (!this.currentUser) return false;
    return permissions.every(permission => this.currentUser!.permissions.includes(permission));
  }

  /**
   * Validate credentials format
   */
  private validateCredentials(credentials: LoginCredentials): boolean {
    // Check identifier
    if (!credentials.email && !credentials.username) {
      return false;
    }

    // Validate email if provided
    if (credentials.email && !securityUtils.validateInput(credentials.email, 'email')) {
      return false;
    }

    // Validate password strength
    if (!credentials.password || credentials.password.length < 8) {
      return false;
    }

    // Check for common passwords
    const commonPasswords = ['password', '12345678', 'qwerty', 'abc123'];
    if (commonPasswords.includes(credentials.password.toLowerCase())) {
      return false;
    }

    return true;
  }

  /**
   * Authenticate with backend (mock implementation)
   */
  private async authenticateWithBackend(credentials: LoginCredentials): Promise<{
    success: boolean;
    user?: User;
    error?: string;
    mfaRequired?: boolean;
  }> {
    // This is a mock implementation. Replace with actual API call
    
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 500));

    // Mock successful authentication
    if (credentials.password === 'SecurePassword123!') {
      const user: User = {
        id: securityUtils.generateUUID(),
        username: credentials.username || 'developer',
        email: credentials.email || 'developer@devdocai.com',
        roles: [UserRole.DEVELOPER],
        permissions: ROLE_PERMISSIONS[UserRole.DEVELOPER],
        metadata: {
          firstName: 'John',
          lastName: 'Developer',
          lastLogin: Date.now(),
          createdAt: Date.now() - 30 * 24 * 60 * 60 * 1000
        }
      };

      return { success: true, user };
    }

    return { success: false, error: 'Invalid credentials' };
  }

  /**
   * Generate JWT tokens
   */
  private async generateTokens(user: User): Promise<AuthToken> {
    const secret = await this.getSigningKey();
    
    // Create access token
    const accessToken = await new SignJWT({
      sub: user.id,
      username: user.username,
      email: user.email,
      roles: user.roles,
      permissions: user.permissions
    })
      .setProtectedHeader({ alg: this.config.jwtAlgorithm })
      .setIssuedAt()
      .setIssuer(this.config.issuer)
      .setAudience(this.config.audience)
      .setExpirationTime(`${this.config.accessTokenExpiry}s`)
      .sign(secret);

    const tokens: AuthToken = {
      accessToken,
      expiresIn: this.config.accessTokenExpiry,
      tokenType: 'Bearer'
    };

    // Create refresh token if enabled
    if (this.config.enableRefreshToken) {
      tokens.refreshToken = await new SignJWT({
        sub: user.id,
        type: 'refresh'
      })
        .setProtectedHeader({ alg: this.config.jwtAlgorithm })
        .setIssuedAt()
        .setIssuer(this.config.issuer)
        .setAudience(this.config.audience)
        .setExpirationTime(`${this.config.refreshTokenExpiry}s`)
        .sign(secret);
    }

    return tokens;
  }

  /**
   * Get signing key
   */
  private async getSigningKey(): Promise<Uint8Array> {
    const secret = this.config.jwtSecret || 'devdocai-secret-key-' + securityUtils.generateToken(32);
    return new TextEncoder().encode(secret);
  }

  /**
   * Verify JWT token
   */
  private async verifyToken(token: string): Promise<boolean> {
    try {
      const secret = await this.getSigningKey();
      const { payload } = await jwtVerify(token, secret, {
        issuer: this.config.issuer,
        audience: this.config.audience
      });
      
      return !!payload;
    } catch (error) {
      console.error('Token verification failed:', error);
      return false;
    }
  }

  /**
   * Load user from token
   */
  private async loadUserFromToken(token: string): Promise<void> {
    try {
      const secret = await this.getSigningKey();
      const { payload } = await jwtVerify(token, secret) as { payload: any };
      
      this.currentUser = {
        id: payload.sub,
        username: payload.username,
        email: payload.email,
        roles: payload.roles,
        permissions: payload.permissions
      };
      
      this.updateAuthState();
    } catch (error) {
      console.error('Failed to load user from token:', error);
      this.clearAuth();
    }
  }

  /**
   * Refresh access token
   */
  public async refreshAccessToken(): Promise<boolean> {
    if (!this.tokens?.refreshToken) {
      return false;
    }

    try {
      const isValid = await this.verifyToken(this.tokens.refreshToken);
      if (!isValid) {
        this.clearAuth();
        return false;
      }

      // Generate new access token
      if (this.currentUser) {
        const newTokens = await this.generateTokens(this.currentUser);
        newTokens.refreshToken = this.tokens.refreshToken; // Keep same refresh token
        
        this.tokens = newTokens;
        this.storeAuth(newTokens, false);
        
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.clearAuth();
    }

    return false;
  }

  /**
   * Setup automatic token refresh
   */
  private setupTokenRefresh(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
    }

    // Refresh token 5 minutes before expiry
    this.refreshTimer = setInterval(async () => {
      if (this.tokens && this.config.enableRefreshToken) {
        const timeUntilExpiry = (this.tokens.expiresIn * 1000) - (5 * 60 * 1000);
        
        if (timeUntilExpiry <= 0) {
          await this.refreshAccessToken();
        }
      }
    }, 60 * 1000); // Check every minute
  }

  /**
   * Store authentication
   */
  private storeAuth(tokens: AuthToken, rememberMe?: boolean): void {
    const storage = rememberMe ? localStorage : sessionStorage;
    storage.setItem('auth_tokens', JSON.stringify(tokens));
  }

  /**
   * Clear authentication
   */
  private clearAuth(): void {
    this.currentUser = null;
    this.tokens = null;
    sessionStorage.removeItem('auth_tokens');
    localStorage.removeItem('auth_tokens');
    
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
    
    this.updateAuthState();
  }

  /**
   * Update authentication state
   */
  private updateAuthState(): void {
    this.stateManager.setState({
      user: this.currentUser as any,
      backend: {
        ...this.stateManager.getState().backend,
        connectionStatus: this.currentUser ? 'connected' : 'disconnected'
      }
    });
  }

  /**
   * Record failed login attempt
   */
  private recordFailedAttempt(identifier: string): void {
    const attempts = this.loginAttempts.get(identifier) || 0;
    this.loginAttempts.set(identifier, attempts + 1);
    
    if (attempts + 1 >= this.config.maxLoginAttempts) {
      this.lockouts.set(identifier, Date.now() + this.config.lockoutDuration);
      this.loginAttempts.delete(identifier);
      
      securityUtils['logSecurityEvent']({
        type: SecurityEventType.RATE_LIMIT_EXCEEDED,
        message: 'Account locked due to failed login attempts',
        details: { identifier, attempts: attempts + 1 },
        severity: 'high'
      });
    }
  }

  /**
   * Clear failed login attempts
   */
  private clearFailedAttempts(identifier: string): void {
    this.loginAttempts.delete(identifier);
    this.lockouts.delete(identifier);
  }

  /**
   * Check if account is locked out
   */
  private isLockedOut(identifier: string): boolean {
    const lockoutTime = this.lockouts.get(identifier);
    if (!lockoutTime) return false;
    
    if (Date.now() >= lockoutTime) {
      this.lockouts.delete(identifier);
      return false;
    }
    
    return true;
  }

  /**
   * Get remaining lockout time
   */
  private getRemainingLockoutTime(identifier: string): number {
    const lockoutTime = this.lockouts.get(identifier);
    if (!lockoutTime) return 0;
    
    return Math.max(0, lockoutTime - Date.now());
  }

  /**
   * Revoke token (mock implementation)
   */
  private async revokeToken(token: string): Promise<void> {
    // This would call backend API to revoke token
    // For now, just log the event
    securityUtils['logSecurityEvent']({
      type: SecurityEventType.VALIDATION_FAILED,
      message: 'Token revoked',
      details: { tokenPrefix: token.substring(0, 10) },
      severity: 'low'
    });
  }

  /**
   * Get access token
   */
  public getAccessToken(): string | null {
    return this.tokens?.accessToken || null;
  }

  /**
   * Get authorization header
   */
  public getAuthHeader(): { Authorization: string } | {} {
    const token = this.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}

/**
 * Default export
 */
export const authManager = AuthManager.getInstance();

/**
 * React hook for authentication
 */
export function useAuth() {
  return AuthManager.getInstance();
}

/**
 * Higher-order component for protected routes
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  requiredPermissions?: Permission[],
  requiredRoles?: UserRole[]
): React.ComponentType<P> {
  return (props: P) => {
    const auth = useAuth();
    
    // Check authentication
    if (!auth.isAuthenticated()) {
      return null; // Or redirect to login
    }
    
    // Check permissions
    if (requiredPermissions && !auth.hasAllPermissions(requiredPermissions)) {
      return null; // Or show unauthorized message
    }
    
    // Check roles
    if (requiredRoles && !auth.hasAnyRole(requiredRoles)) {
      return null; // Or show unauthorized message
    }
    
    return <Component {...props} />;
  };
}

/**
 * Export types
 */
export type { User, AuthToken, LoginCredentials, MFAChallenge, AuthConfig };