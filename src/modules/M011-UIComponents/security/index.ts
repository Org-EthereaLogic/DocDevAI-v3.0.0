/**
 * M011 Security Module - Centralized export for all security components
 * 
 * Provides comprehensive security features for the React UI including:
 * - XSS prevention and input sanitization
 * - Encrypted state management
 * - JWT authentication and RBAC
 * - CSRF protection and API security
 * - Security monitoring and anomaly detection
 */

// Security utilities and XSS prevention
export {
  SecurityUtils,
  securityUtils,
  useSecurityUtils,
  CSPBuilder,
  SecurityConfig,
  SecurityEvent,
  SecurityEventType,
  DEFAULT_SECURITY_CONFIG
} from './security-utils';

// Secure state management
export {
  SecureStateManager,
  GlobalSecureStateManager,
  useSecureGlobalState,
  MemorySanitizer,
  EncryptionConfig,
  SessionConfig
} from './state-management-secure';

// Authentication and authorization
export {
  AuthManager,
  authManager,
  useAuth,
  withAuth,
  UserRole,
  Permission,
  User,
  AuthToken,
  LoginCredentials,
  MFAChallenge,
  AuthConfig
} from './auth-manager';

// API security
export {
  APISecurity,
  apiSecurity,
  useAPISecurity,
  HttpMethod,
  APISecurityConfig,
  RequestConfig,
  RequestInterceptor,
  ResponseInterceptor
} from './api-security';

// Security monitoring
export {
  SecurityMonitor,
  securityMonitor,
  useSecurityMonitor,
  SecurityMetricType,
  AttackPattern,
  SecurityMetric,
  AnomalyResult,
  AttackSurfaceItem,
  MonitorConfig
} from './security-monitor';

/**
 * Initialize all security features
 */
export function initializeSecurity(config?: {
  security?: Partial<import('./security-utils').SecurityConfig>;
  auth?: Partial<import('./auth-manager').AuthConfig>;
  api?: Partial<import('./api-security').APISecurityConfig>;
  monitor?: Partial<import('./security-monitor').MonitorConfig>;
}): void {
  // Initialize security utilities
  if (config?.security) {
    securityUtils.updateConfig(config.security);
  }

  // Initialize authentication
  if (config?.auth) {
    AuthManager.getInstance(config.auth);
  }

  // Initialize API security
  if (config?.api) {
    APISecurity.getInstance(config.api);
  }

  // Initialize security monitor
  if (config?.monitor) {
    SecurityMonitor.getInstance(config.monitor);
  }

  // Setup Content Security Policy
  setupCSP();

  // Initialize secure state management
  GlobalSecureStateManager.getSecureInstance().initialize();

  // Log initialization
  console.info('[Security] All security features initialized');
}

/**
 * Setup Content Security Policy
 */
export function setupCSP(): void {
  const cspBuilder = new CSPBuilder();
  
  // Generate nonce for inline scripts
  const scriptNonce = securityUtils.generateCSPNonce();
  const styleNonce = securityUtils.generateCSPNonce();
  
  // Add nonces to CSP
  cspBuilder
    .addScriptNonce(scriptNonce)
    .addStyleNonce(styleNonce);
  
  // Create meta tag for CSP
  const metaCSP = document.createElement('meta');
  metaCSP.httpEquiv = 'Content-Security-Policy';
  metaCSP.content = cspBuilder.buildMetaContent();
  document.head.appendChild(metaCSP);
  
  // Add nonces to existing inline scripts and styles
  document.querySelectorAll('script:not([src])').forEach(script => {
    script.setAttribute('nonce', scriptNonce);
  });
  
  document.querySelectorAll('style').forEach(style => {
    style.setAttribute('nonce', styleNonce);
  });
  
  // Store nonces for dynamic content
  (window as any).__CSP_NONCE__ = {
    script: scriptNonce,
    style: styleNonce
  };
}

/**
 * Security health check
 */
export function performSecurityHealthCheck(): {
  status: 'healthy' | 'degraded' | 'critical';
  score: number;
  issues: string[];
} {
  const issues: string[] = [];
  let score = 100;

  // Check authentication
  if (!authManager.isAuthenticated()) {
    issues.push('User not authenticated');
    score -= 10;
  }

  // Check HTTPS
  if (window.location.protocol !== 'https:' && process.env.NODE_ENV === 'production') {
    issues.push('Not using HTTPS in production');
    score -= 30;
  }

  // Check CSP
  const hasCSP = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
  if (!hasCSP) {
    issues.push('Content Security Policy not configured');
    score -= 20;
  }

  // Check for sensitive data in storage
  ['localStorage', 'sessionStorage'].forEach(storage => {
    const storageObj = storage === 'localStorage' ? localStorage : sessionStorage;
    Object.keys(storageObj).forEach(key => {
      if (!key.startsWith('secure_') && 
          (key.includes('token') || key.includes('password') || key.includes('key'))) {
        issues.push(`Potentially unencrypted sensitive data in ${storage}: ${key}`);
        score -= 15;
      }
    });
  });

  // Check security headers
  const securityScore = securityMonitor.getSecurityScore();
  if (securityScore.score < 70) {
    issues.push(`Low security score: ${securityScore.score}/100`);
    score -= 20;
  }

  // Determine status
  let status: 'healthy' | 'degraded' | 'critical';
  if (score >= 80) {
    status = 'healthy';
  } else if (score >= 50) {
    status = 'degraded';
  } else {
    status = 'critical';
  }

  return { status, score: Math.max(0, score), issues };
}

/**
 * React hook for security health
 */
export function useSecurityHealth() {
  const [health, setHealth] = React.useState(performSecurityHealthCheck());

  React.useEffect(() => {
    const interval = setInterval(() => {
      setHealth(performSecurityHealthCheck());
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, []);

  return health;
}

/**
 * Security context provider
 */
export const SecurityContext = React.createContext<{
  auth: AuthManager;
  api: APISecurity;
  monitor: SecurityMonitor;
  utils: SecurityUtils;
  health: ReturnType<typeof performSecurityHealthCheck>;
} | null>(null);

/**
 * Security provider component
 */
export function SecurityProvider({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  const api = useAPISecurity();
  const monitor = useSecurityMonitor();
  const utils = useSecurityUtils();
  const health = useSecurityHealth();

  React.useEffect(() => {
    // Initialize security on mount
    initializeSecurity();

    // Cleanup on unmount
    return () => {
      monitor.destroy();
    };
  }, []);

  return (
    <SecurityContext.Provider value={{ auth, api, monitor, utils, health }}>
      {children}
    </SecurityContext.Provider>
  );
}

/**
 * Hook to use security context
 */
export function useSecurity() {
  const context = React.useContext(SecurityContext);
  if (!context) {
    throw new Error('useSecurity must be used within SecurityProvider');
  }
  return context;
}

// Import React for JSX support
import * as React from 'react';