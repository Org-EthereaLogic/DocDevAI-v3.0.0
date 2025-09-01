/**
 * M011 Security Tests - Comprehensive security test suite
 * 
 * Tests all security features including XSS prevention, encryption,
 * authentication, API security, and monitoring.
 */

import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import {
  securityUtils,
  SecurityEventType,
  CSPBuilder
} from '../../../src/modules/M011-UIComponents/security/security-utils';
import {
  SecureStateManager,
  GlobalSecureStateManager,
  MemorySanitizer
} from '../../../src/modules/M011-UIComponents/security/state-management-secure';
import {
  authManager,
  UserRole,
  Permission
} from '../../../src/modules/M011-UIComponents/security/auth-manager';
import {
  apiSecurity,
  HttpMethod
} from '../../../src/modules/M011-UIComponents/security/api-security';
import {
  securityMonitor,
  SecurityMetricType,
  AttackPattern
} from '../../../src/modules/M011-UIComponents/security/security-monitor';

// Mock fetch for API tests
global.fetch = jest.fn();

describe('Security Utilities', () => {
  describe('XSS Prevention', () => {
    it('should detect XSS patterns', () => {
      const xssInputs = [
        '<script>alert("XSS")</script>',
        'javascript:alert("XSS")',
        '<img src=x onerror=alert("XSS")>',
        '<iframe src="javascript:alert(\'XSS\')"></iframe>',
        'onclick=alert("XSS")',
        '<svg onload=alert("XSS")>',
        'data:text/html,<script>alert("XSS")</script>'
      ];

      xssInputs.forEach(input => {
        expect(securityUtils.detectXSS(input)).toBe(true);
      });
    });

    it('should sanitize HTML content', () => {
      const maliciousHTML = '<p>Hello</p><script>alert("XSS")</script><b>World</b>';
      const sanitized = securityUtils.sanitizeHTML(maliciousHTML);
      
      expect(sanitized).toContain('<p>Hello</p>');
      expect(sanitized).toContain('<b>World</b>');
      expect(sanitized).not.toContain('<script>');
      expect(sanitized).not.toContain('alert');
    });

    it('should escape HTML entities', () => {
      const input = '<script>alert("XSS")</script>';
      const escaped = securityUtils.escapeHTML(input);
      
      expect(escaped).toBe('&lt;script&gt;alert(&quot;XSS&quot;)&lt;&#x2F;script&gt;');
    });

    it('should sanitize various input types', () => {
      expect(securityUtils.sanitizeInput('test@example.com', 'email'))
        .toBe('test@example.com');
      
      expect(securityUtils.sanitizeInput('https://example.com', 'url'))
        .toBe('https://example.com');
      
      expect(securityUtils.sanitizeInput('123.45', 'number'))
        .toBe('123.45');
      
      expect(securityUtils.sanitizeInput('abc123', 'alphanumeric'))
        .toBe('abc123');
    });
  });

  describe('SQL Injection Prevention', () => {
    it('should detect SQL injection patterns', () => {
      const sqlInputs = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "admin' --",
        "1 UNION SELECT * FROM users",
        "'; EXEC xp_cmdshell('dir'); --",
        "waitfor delay '00:00:10'--"
      ];

      sqlInputs.forEach(input => {
        expect(securityUtils.detectSQLInjection(input)).toBe(true);
      });
    });

    it('should escape SQL special characters', () => {
      const input = "'; DROP TABLE users; --";
      const escaped = securityUtils.escapeSQL(input);
      
      expect(escaped).not.toContain("'");
      expect(escaped).toContain("''");
    });
  });

  describe('Path Traversal Prevention', () => {
    it('should detect path traversal patterns', () => {
      const pathInputs = [
        '../../../etc/passwd',
        '..\\..\\..\\windows\\system32',
        '%2e%2e%2f',
        '..;/',
        '..%252f',
        '..%c0%af'
      ];

      pathInputs.forEach(input => {
        expect(securityUtils.detectPathTraversal(input)).toBe(true);
      });
    });
  });

  describe('Input Validation', () => {
    it('should validate email addresses', () => {
      expect(securityUtils.validateInput('test@example.com', 'email')).toBe(true);
      expect(securityUtils.validateInput('invalid-email', 'email')).toBe(false);
    });

    it('should validate URLs', () => {
      expect(securityUtils.validateInput('https://example.com', 'url')).toBe(true);
      expect(securityUtils.validateInput('javascript:alert(1)', 'url')).toBe(false);
    });

    it('should validate JSON', () => {
      expect(securityUtils.validateInput('{"key": "value"}', 'json')).toBe(true);
      expect(securityUtils.validateInput('invalid json', 'json')).toBe(false);
    });

    it('should detect prototype pollution in JSON', () => {
      const maliciousJSON = '{"__proto__": {"isAdmin": true}}';
      expect(securityUtils.validateJSON(maliciousJSON)).toBe(false);
    });
  });

  describe('CSP Builder', () => {
    it('should build valid CSP string', () => {
      const csp = new CSPBuilder();
      const policy = csp.build();
      
      expect(policy).toContain("default-src 'self'");
      expect(policy).toContain("script-src");
      expect(policy).toContain("style-src");
    });

    it('should add nonces correctly', () => {
      const csp = new CSPBuilder();
      const nonce = 'test-nonce';
      
      csp.addScriptNonce(nonce);
      csp.addStyleNonce(nonce);
      
      const policy = csp.build();
      expect(policy).toContain(`'${nonce}'`);
    });
  });
});

describe('Secure State Management', () => {
  let secureState: SecureStateManager<any>;

  beforeEach(() => {
    secureState = new SecureStateManager(
      { sensitive: 'secret', normal: 'public' },
      'test-state'
    );
  });

  it('should encrypt sensitive fields', async () => {
    // Mock encryption key initialization
    await secureState['initializeEncryptionKey']();
    
    secureState.setState({ sensitive: 'new-secret' });
    const rawState = secureState['state'];
    
    // Check if sensitive field is encrypted
    expect(typeof rawState.sensitive).toBe('string');
    expect(rawState.sensitive).toMatch(/^ENC:/);
  });

  it('should decrypt sensitive fields on retrieval', async () => {
    await secureState['initializeEncryptionKey']();
    
    secureState.setState({ sensitive: 'secret-value' });
    const decrypted = secureState.getState();
    
    expect(decrypted.sensitive).toBe('secret-value');
  });

  it('should handle session timeout', (done) => {
    const config = {
      timeout: 100, // 100ms for testing
      clearOnTimeout: true
    };
    
    const testState = new SecureStateManager(
      { data: 'test' },
      'timeout-test',
      undefined,
      config
    );
    
    // Listen for timeout event
    window.addEventListener('sessionTimeout', () => {
      expect(testState.getState().data).toBeNull();
      done();
    });
  });

  it('should sanitize memory', () => {
    const sensitiveObj = {
      password: 'secret123',
      apiKey: 'key-123',
      normalData: 'public'
    };
    
    MemorySanitizer.sanitize(sensitiveObj);
    
    expect(sensitiveObj.password).toBeUndefined();
    expect(sensitiveObj.apiKey).toBeUndefined();
    expect(sensitiveObj.normalData).toBe('public');
  });
});

describe('Authentication Manager', () => {
  beforeEach(() => {
    // Clear any existing auth
    authManager['clearAuth']();
  });

  it('should validate login credentials', async () => {
    const result = await authManager.login({
      email: 'invalid-email',
      password: 'short'
    });
    
    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });

  it('should handle successful login', async () => {
    const result = await authManager.login({
      email: 'test@example.com',
      password: 'SecurePassword123!'
    });
    
    expect(result.success).toBe(true);
    expect(result.user).toBeDefined();
    expect(authManager.isAuthenticated()).toBe(true);
  });

  it('should check permissions correctly', async () => {
    await authManager.login({
      email: 'developer@example.com',
      password: 'SecurePassword123!'
    });
    
    expect(authManager.hasPermission(Permission.DOCUMENT_CREATE)).toBe(true);
    expect(authManager.hasPermission(Permission.SYSTEM_ADMIN)).toBe(false);
  });

  it('should handle role checks', async () => {
    await authManager.login({
      email: 'developer@example.com',
      password: 'SecurePassword123!'
    });
    
    expect(authManager.hasRole(UserRole.DEVELOPER)).toBe(true);
    expect(authManager.hasRole(UserRole.ADMIN)).toBe(false);
  });

  it('should implement account lockout', async () => {
    const email = 'test@example.com';
    
    // Simulate multiple failed attempts
    for (let i = 0; i < 5; i++) {
      await authManager.login({
        email,
        password: 'wrong-password'
      });
    }
    
    // Next attempt should be locked out
    const result = await authManager.login({
      email,
      password: 'SecurePassword123!'
    });
    
    expect(result.success).toBe(false);
    expect(result.error).toContain('locked');
  });

  it('should generate valid JWT tokens', async () => {
    await authManager.login({
      email: 'test@example.com',
      password: 'SecurePassword123!'
    });
    
    const token = authManager.getAccessToken();
    expect(token).toBeDefined();
    expect(token).toMatch(/^[\w-]+\.[\w-]+\.[\w-]+$/); // JWT format
  });
});

describe('API Security', () => {
  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
  });

  it('should add security headers to requests', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      text: async () => '{"success": true}'
    });
    
    await apiSecurity.get('/api/test');
    
    const call = (global.fetch as jest.Mock).mock.calls[0];
    const options = call[1];
    
    expect(options.headers['X-Content-Type-Options']).toBe('nosniff');
    expect(options.headers['X-Frame-Options']).toBe('DENY');
  });

  it('should add CSRF token for state-changing methods', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      text: async () => '{"success": true}'
    });
    
    await apiSecurity.post('/api/test', { data: 'test' });
    
    const call = (global.fetch as jest.Mock).mock.calls[0];
    const options = call[1];
    
    expect(options.headers['X-CSRF-Token']).toBeDefined();
  });

  it('should implement rate limiting', async () => {
    const endpoint = '/api/test';
    
    // Check initial rate limit
    const status = apiSecurity.getRateLimitStatus(endpoint);
    expect(status.remaining).toBe(status.limit);
    
    // Make requests
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      text: async () => '{"success": true}'
    });
    
    await apiSecurity.get(endpoint);
    
    // Check updated rate limit
    const newStatus = apiSecurity.getRateLimitStatus(endpoint);
    expect(newStatus.remaining).toBe(status.limit - 1);
  });

  it('should validate request configuration', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: new Headers(),
      text: async () => 'response'
    });
    
    // Invalid method should throw
    await expect(apiSecurity.request({
      url: '/api/test',
      method: 'INVALID' as HttpMethod
    })).rejects.toThrow('Invalid request configuration');
  });

  it('should detect injection in request data', async () => {
    const maliciousData = {
      query: "'; DROP TABLE users; --"
    };
    
    await expect(apiSecurity.post('/api/test', maliciousData))
      .rejects.toThrow('Invalid request configuration');
  });
});

describe('Security Monitor', () => {
  beforeEach(() => {
    securityMonitor['events'] = [];
    securityMonitor['anomalies'] = [];
  });

  it('should log security events', () => {
    securityMonitor.logEvent({
      type: SecurityEventType.XSS_ATTEMPT,
      message: 'XSS attempt detected',
      severity: 'high',
      details: { input: '<script>' }
    });
    
    const events = securityMonitor.getEvents();
    expect(events.length).toBeGreaterThan(0);
    expect(events[0].type).toBe(SecurityEventType.XSS_ATTEMPT);
  });

  it('should detect brute force attacks', () => {
    // Simulate multiple failed login events
    for (let i = 0; i < 15; i++) {
      securityMonitor.logEvent({
        type: SecurityEventType.VALIDATION_FAILED,
        message: 'Failed login attempt',
        severity: 'medium',
        details: { username: 'admin' }
      });
    }
    
    // Trigger anomaly detection
    securityMonitor['detectAnomalies']();
    
    const anomalies = securityMonitor.getAnomalies();
    const bruteForce = anomalies.find(a => a.pattern === AttackPattern.BRUTE_FORCE);
    
    expect(bruteForce).toBeDefined();
    expect(bruteForce?.severity).toBe('high');
  });

  it('should detect XSS campaigns', () => {
    // Simulate multiple XSS attempts
    for (let i = 0; i < 10; i++) {
      securityMonitor.logEvent({
        type: SecurityEventType.XSS_ATTEMPT,
        message: 'XSS pattern detected',
        severity: 'high',
        details: { payload: `<script>alert(${i})</script>` }
      });
    }
    
    securityMonitor['detectAnomalies']();
    
    const anomalies = securityMonitor.getAnomalies();
    const xssCampaign = anomalies.find(a => a.pattern === AttackPattern.XSS_CAMPAIGN);
    
    expect(xssCampaign).toBeDefined();
    expect(xssCampaign?.severity).toBe('critical');
  });

  it('should calculate security score', () => {
    const score = securityMonitor.getSecurityScore();
    
    expect(score.score).toBeGreaterThanOrEqual(0);
    expect(score.score).toBeLessThanOrEqual(100);
    expect(score.breakdown).toHaveProperty('authentication');
    expect(score.breakdown).toHaveProperty('encryption');
    expect(score.recommendations).toBeInstanceOf(Array);
  });

  it('should track metrics', () => {
    securityMonitor.logEvent({
      type: SecurityEventType.XSS_ATTEMPT,
      message: 'XSS detected',
      severity: 'high',
      details: {}
    });
    
    securityMonitor['collectMetrics']();
    
    const metrics = securityMonitor.getMetrics(SecurityMetricType.XSS_ATTEMPTS);
    expect(metrics.length).toBeGreaterThan(0);
  });

  it('should identify attack surface', () => {
    // Create test form element
    const form = document.createElement('form');
    form.method = 'POST';
    form.id = 'test-form';
    document.body.appendChild(form);
    
    securityMonitor['initializeAttackSurface']();
    
    const attackSurface = securityMonitor.getAttackSurface();
    const formItem = attackSurface.find(item => item.type === 'form');
    
    expect(formItem).toBeDefined();
    expect(formItem?.risk).toBe('high'); // POST form without CSRF
    
    // Cleanup
    document.body.removeChild(form);
  });

  it('should generate security report', () => {
    // Add some test data
    securityMonitor.logEvent({
      type: SecurityEventType.XSS_ATTEMPT,
      message: 'Test XSS',
      severity: 'high',
      details: {}
    });
    
    const report = securityMonitor.generateReport();
    
    expect(report).toContain('Security Report');
    expect(report).toContain('Security Score');
    expect(report).toContain('Recent Security Events');
    expect(report).toContain('Recommendations');
  });
});

describe('Integration Tests', () => {
  it('should integrate auth with API security', async () => {
    // Login to get token
    await authManager.login({
      email: 'test@example.com',
      password: 'SecurePassword123!'
    });
    
    // Mock fetch
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      headers: new Headers({ 'content-type': 'application/json' }),
      text: async () => '{"data": "secure"}'
    });
    
    // Make API request
    await apiSecurity.get('/api/secure');
    
    // Check that auth header was added
    const call = (global.fetch as jest.Mock).mock.calls[0];
    const options = call[1];
    
    expect(options.headers['Authorization']).toMatch(/^Bearer /);
  });

  it('should log API security events to monitor', () => {
    const initialEventCount = securityMonitor.getEvents().length;
    
    // Trigger rate limit
    for (let i = 0; i < 101; i++) {
      try {
        apiSecurity['rateLimiter'].isAllowed('/api/test', 'user1');
      } catch {}
    }
    
    const events = securityMonitor.getEvents();
    expect(events.length).toBeGreaterThan(initialEventCount);
  });

  it('should handle secure state with monitoring', async () => {
    const secureState = GlobalSecureStateManager.getSecureInstance();
    
    secureState.setState({
      backend: {
        apiKeys: 'secret-key',
        connectionStatus: 'connected'
      }
    } as any);
    
    // Check encryption happened
    const rawState = secureState['secureStateManager']['state'];
    expect(rawState.backend.apiKeys).toMatch(/^ENC:/);
    
    // Check decryption works
    const decrypted = secureState.getState();
    expect(decrypted.backend.apiKeys).toBe('secret-key');
  });
});

describe('Attack Simulation Tests', () => {
  it('should prevent stored XSS', () => {
    const userInput = '<img src=x onerror="alert(document.cookie)">';
    const sanitized = securityUtils.sanitizeHTML(userInput);
    
    // Create element with sanitized content
    const div = document.createElement('div');
    div.innerHTML = sanitized;
    document.body.appendChild(div);
    
    // Check that no script executed (no alert)
    expect(div.innerHTML).not.toContain('onerror');
    expect(div.innerHTML).not.toContain('alert');
    
    // Cleanup
    document.body.removeChild(div);
  });

  it('should prevent DOM-based XSS', () => {
    const maliciousURL = 'https://example.com#<script>alert(1)</script>';
    const sanitized = securityUtils.sanitizeInput(maliciousURL, 'url');
    
    expect(sanitized).not.toContain('<script>');
    expect(sanitized).not.toContain('alert');
  });

  it('should prevent CSRF attacks', async () => {
    // Attempt request without CSRF token
    const request = {
      url: '/api/delete',
      method: 'DELETE' as HttpMethod,
      headers: {}
    };
    
    // API security should add CSRF token automatically
    const processed = await apiSecurity['requestInterceptors'][0].onRequest!(request);
    expect(processed.headers?.['X-CSRF-Token']).toBeDefined();
  });

  it('should prevent session hijacking', () => {
    // Simulate session theft attempt
    const stolenToken = 'stolen-jwt-token';
    
    // Try to use stolen token
    authManager['tokens'] = { 
      accessToken: stolenToken,
      expiresIn: 3600,
      tokenType: 'Bearer'
    };
    
    // Verification should fail for invalid token
    authManager['verifyToken'](stolenToken).then(isValid => {
      expect(isValid).toBe(false);
    });
  });

  it('should prevent privilege escalation', async () => {
    // Login as regular user
    await authManager.login({
      email: 'user@example.com',
      password: 'SecurePassword123!'
    });
    
    // Try to access admin functionality
    const hasAdminAccess = authManager.hasPermission(Permission.SYSTEM_ADMIN);
    expect(hasAdminAccess).toBe(false);
    
    // Try to modify roles directly (should not work)
    const user = authManager.getCurrentUser();
    if (user) {
      user.roles.push(UserRole.ADMIN);
      
      // Check permission again - should still be false
      expect(authManager.hasPermission(Permission.SYSTEM_ADMIN)).toBe(false);
    }
  });
});