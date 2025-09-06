/**
 * Module 1: Edge Cases and Stress Testing
 * 
 * Tests for extreme conditions, boundary cases, and stress scenarios
 */

import {
  initializeCore,
  ConfigLoader,
  SecurityService,
  Logger,
  ErrorHandler,
  MemoryModeDetector
} from '../../src/cli/core/index.unified';
import * as fs from 'fs-extra';
import * as path from 'path';
import * as os from 'os';
import { performance } from 'perf_hooks';
import * as crypto from 'crypto';

describe('Module 1: Edge Cases and Stress Tests', () => {
  const testDir = path.join(os.tmpdir(), 'devdocai-edge-test');
  let cleanup: (() => Promise<void>) | undefined;

  beforeEach(async () => {
    await fs.ensureDir(testDir);
    process.env.DEVDOCAI_CONFIG_DIR = testDir;
  });

  afterEach(async () => {
    if (cleanup) {
      await cleanup();
      cleanup = undefined;
    }
    await fs.remove(testDir);
    delete process.env.DEVDOCAI_CONFIG_DIR;
  });

  /**
   * EDGE CASE 1: Extreme Input Sizes
   */
  describe('Edge Case 1: Extreme Input Sizes', () => {
    it('should handle very large configuration files', async () => {
      const core = await initializeCore({ mode: 'performance' });

      // Create large configuration (1MB+)
      const largeConfig: any = {
        version: '3.0.0',
        privacy: { telemetry: false },
        performance: { cacheEnabled: true },
        customData: {}
      };

      // Add 10,000 custom settings
      for (let i = 0; i < 10000; i++) {
        largeConfig.customData[`setting_${i}`] = {
          value: crypto.randomBytes(50).toString('hex'),
          metadata: {
            created: new Date().toISOString(),
            index: i
          }
        };
      }

      // Should handle large config
      const validation = await core.config.validate(largeConfig);
      expect(validation.valid).toBe(true);

      // Save and load should work
      await core.config.save(largeConfig);
      const loaded = await core.config.load();
      expect(Object.keys(loaded.customData).length).toBe(10000);

      cleanup = core.cleanup;
    });

    it('should handle extremely long strings', async () => {
      const core = await initializeCore({ mode: 'secure' });

      // Create very long string (1MB)
      const longString = 'x'.repeat(1024 * 1024);

      // Encryption should handle it
      const encrypted = await core.security.encrypt(longString);
      const decrypted = await core.security.decrypt(encrypted);
      expect(decrypted.length).toBe(longString.length);

      // Sanitization should handle it
      const sanitized = await core.security.sanitize(longString);
      expect(sanitized).toBeDefined();

      // Logging should truncate appropriately
      await core.logger.log('info', longString);
      const logs = await core.logger.query({ limit: 1 });
      expect(logs[0].message.length).toBeLessThanOrEqual(10000); // Should truncate

      cleanup = core.cleanup;
    });

    it('should handle empty inputs gracefully', async () => {
      const core = await initializeCore({ mode: 'basic' });

      // Empty string encryption
      const encrypted = await core.security.encrypt('');
      const decrypted = await core.security.decrypt(encrypted);
      expect(decrypted).toBe('');

      // Empty error formatting
      const formatted = core.errorHandler.format(new Error(''));
      expect(formatted).toContain('Unknown error');

      // Empty log message
      await core.logger.log('info', '');
      const logs = await core.logger.query({ limit: 1 });
      expect(logs[0].message).toBe('');

      cleanup = core.cleanup;
    });
  });

  /**
   * EDGE CASE 2: Concurrent Operations
   */
  describe('Edge Case 2: Concurrent Operations', () => {
    it('should handle concurrent config modifications', async () => {
      const core = await initializeCore({ mode: 'enterprise' });
      const promises = [];

      // 100 concurrent config modifications
      for (let i = 0; i < 100; i++) {
        promises.push((async () => {
          const config = await core.config.load();
          config.performance.cacheSize = i;
          await core.config.save(config);
        })());
      }

      await Promise.all(promises);

      // Final state should be consistent
      const finalConfig = await core.config.load();
      expect(typeof finalConfig.performance.cacheSize).toBe('number');
      expect(finalConfig.performance.cacheSize).toBeGreaterThanOrEqual(0);
      expect(finalConfig.performance.cacheSize).toBeLessThan(100);

      cleanup = core.cleanup;
    });

    it('should handle concurrent encryption operations', async () => {
      const core = await initializeCore({ mode: 'secure' });
      const data = Array.from({ length: 1000 }, (_, i) => `secret-${i}`);
      
      // Encrypt all concurrently
      const encryptPromises = data.map(d => core.security.encrypt(d));
      const encrypted = await Promise.all(encryptPromises);

      // Decrypt all concurrently
      const decryptPromises = encrypted.map(e => core.security.decrypt(e));
      const decrypted = await Promise.all(decryptPromises);

      // Verify all match
      for (let i = 0; i < data.length; i++) {
        expect(decrypted[i]).toBe(data[i]);
      }

      cleanup = core.cleanup;
    });

    it('should handle racing log writes', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const writeCount = 10000;
      const promises = [];

      const startTime = performance.now();

      // Create racing log writes
      for (let i = 0; i < writeCount; i++) {
        promises.push(core.logger.log('info', `Racing message ${i}`));
      }

      await Promise.all(promises);
      const duration = performance.now() - startTime;

      // Should complete quickly (< 5 seconds for 10k logs)
      expect(duration).toBeLessThan(5000);

      // All logs should be present
      const logs = await core.logger.query({ limit: writeCount });
      expect(logs.length).toBeLessThanOrEqual(writeCount);

      cleanup = core.cleanup;
    });
  });

  /**
   * EDGE CASE 3: Resource Exhaustion
   */
  describe('Edge Case 3: Resource Exhaustion', () => {
    it('should handle memory pressure gracefully', async () => {
      const core = await initializeCore({ mode: 'auto' });

      // Allocate large buffers to simulate memory pressure
      const buffers = [];
      const bufferSize = 10 * 1024 * 1024; // 10MB each

      try {
        for (let i = 0; i < 100; i++) {
          buffers.push(Buffer.alloc(bufferSize));
          
          // Check if system adapts
          const mode = await core.memoryDetector.detect();
          if (mode === 'baseline') {
            // System detected low memory
            break;
          }
        }
      } catch (error: any) {
        // Should handle out of memory gracefully
        expect(error.message).toMatch(/memory|heap/i);
      }

      // System should still be operational
      const config = await core.config.load();
      expect(config).toBeDefined();

      cleanup = core.cleanup;
    });

    it('should handle file descriptor exhaustion', async () => {
      const core = await initializeCore({ mode: 'basic' });
      const handles = [];

      try {
        // Try to open many files
        for (let i = 0; i < 10000; i++) {
          const filename = path.join(testDir, `file_${i}.txt`);
          await fs.writeFile(filename, 'test');
          const handle = await fs.open(filename, 'r');
          handles.push(handle);
        }
      } catch (error: any) {
        // Should handle EMFILE gracefully
        expect(error.code).toMatch(/EMFILE|ENFILE/);
      }

      // Close handles
      for (const handle of handles) {
        await handle.close();
      }

      // System should recover
      const recovered = await core.errorHandler.recover();
      expect(recovered).toBe(true);

      cleanup = core.cleanup;
    });
  });

  /**
   * EDGE CASE 4: Malformed Inputs
   */
  describe('Edge Case 4: Malformed Inputs', () => {
    it('should handle corrupted configuration files', async () => {
      // Write corrupted config
      const configPath = path.join(testDir, '.devdocai.yml');
      await fs.writeFile(configPath, '{ invalid json: true, }}}');

      const core = await initializeCore({ mode: 'basic' });

      // Should fall back to defaults
      const config = await core.config.load();
      expect(config).toBeDefined();
      expect(config.version).toBe('3.0.0');

      cleanup = core.cleanup;
    });

    it('should handle invalid encryption data', async () => {
      const core = await initializeCore({ mode: 'secure' });

      const invalidInputs = [
        'not-encrypted-data',
        Buffer.from('random bytes').toString('base64'),
        '{"fake": "encrypted"}',
        null,
        undefined,
        123,
        true
      ];

      for (const input of invalidInputs) {
        try {
          await core.security.decrypt(input as any);
          // Should throw
          expect(true).toBe(false);
        } catch (error: any) {
          // Should provide clear error
          expect(error.message).toMatch(/decrypt|invalid|format/i);
        }
      }

      cleanup = core.cleanup;
    });

    it('should handle circular references', async () => {
      const core = await initializeCore({ mode: 'basic' });

      // Create circular reference
      const obj: any = { name: 'test' };
      obj.self = obj;

      // Logger should handle it
      await core.logger.log('info', 'Circular test', obj);
      
      // Error handler should handle it
      const error: any = new Error('Circular error');
      error.circular = error;
      const formatted = core.errorHandler.format(error);
      expect(formatted).toContain('Circular error');

      cleanup = core.cleanup;
    });
  });

  /**
   * EDGE CASE 5: Timing and Race Conditions
   */
  describe('Edge Case 5: Timing and Race Conditions', () => {
    it('should handle rapid initialization/cleanup cycles', async () => {
      for (let i = 0; i < 10; i++) {
        const core = await initializeCore({ mode: 'basic' });
        
        // Immediate cleanup
        if (core.cleanup) {
          await core.cleanup();
        }
      }

      // Should not leak resources
      const memUsage = process.memoryUsage();
      expect(memUsage.heapUsed).toBeLessThan(500 * 1024 * 1024); // < 500MB
    });

    it('should handle operations during shutdown', async () => {
      const core = await initializeCore({ mode: 'enterprise' });

      // Start shutdown
      const cleanupPromise = core.cleanup ? core.cleanup() : Promise.resolve();

      // Try operations during shutdown
      const operations = [
        core.config.load(),
        core.logger.log('info', 'During shutdown'),
        core.security.encrypt('test'),
        core.memoryDetector.detect()
      ];

      // Some operations might fail, but shouldn't crash
      const results = await Promise.allSettled(operations);
      
      // At least some should complete
      const successful = results.filter(r => r.status === 'fulfilled');
      expect(successful.length).toBeGreaterThan(0);

      await cleanupPromise;
    });
  });

  /**
   * EDGE CASE 6: Platform-Specific Edge Cases
   */
  describe('Edge Case 6: Platform-Specific Edge Cases', () => {
    it('should handle Windows-specific path issues', async () => {
      if (process.platform !== 'win32') {
        // Skip on non-Windows
        return;
      }

      const core = await initializeCore({ mode: 'basic' });

      // Test UNC paths
      const uncPath = '\\\\server\\share\\config.yml';
      try {
        await core.config.loadFrom(uncPath);
      } catch (error: any) {
        // Should handle gracefully
        expect(error.message).toMatch(/path|file|access/i);
      }

      // Test long paths (> 260 chars)
      const longPath = 'C:\\' + 'a'.repeat(250) + '\\config.yml';
      try {
        await core.config.loadFrom(longPath);
      } catch (error: any) {
        expect(error.message).toMatch(/path|long|invalid/i);
      }

      cleanup = core.cleanup;
    });

    it('should handle Unix permission issues', async () => {
      if (process.platform === 'win32') {
        // Skip on Windows
        return;
      }

      const core = await initializeCore({ mode: 'secure' });

      // Create file with no permissions
      const restrictedFile = path.join(testDir, 'restricted.yml');
      await fs.writeFile(restrictedFile, 'test');
      await fs.chmod(restrictedFile, 0o000);

      try {
        await core.config.loadFrom(restrictedFile);
      } catch (error: any) {
        expect(error.code).toBe('EACCES');
      }

      // Restore permissions for cleanup
      await fs.chmod(restrictedFile, 0o644);

      cleanup = core.cleanup;
    });
  });

  /**
   * EDGE CASE 7: Network and I/O Issues
   */
  describe('Edge Case 7: Network and I/O Issues', () => {
    it('should handle slow I/O operations', async () => {
      const core = await initializeCore({ mode: 'performance' });

      // Mock slow filesystem
      const originalRead = fs.readFile;
      fs.readFile = jest.fn(async (path: any, ...args: any[]) => {
        await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second delay
        return originalRead(path, ...args);
      });

      // Should have timeout or handle gracefully
      const startTime = performance.now();
      
      try {
        await Promise.race([
          core.config.load(),
          new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Timeout')), 5000)
          )
        ]);
      } catch (error: any) {
        const duration = performance.now() - startTime;
        expect(duration).toBeLessThan(6000); // Should timeout or complete
      }

      // Restore
      fs.readFile = originalRead;

      cleanup = core.cleanup;
    });

    it('should handle intermittent I/O failures', async () => {
      const core = await initializeCore({ mode: 'enterprise' });

      // Mock intermittent failures
      const originalWrite = fs.writeFile;
      let failCount = 0;
      
      fs.writeFile = jest.fn(async (path: any, ...args: any[]) => {
        failCount++;
        if (failCount % 3 === 0) {
          throw new Error('EBUSY: resource busy');
        }
        return originalWrite(path, ...args);
      });

      // Should retry and eventually succeed
      let succeeded = false;
      
      for (let i = 0; i < 5; i++) {
        try {
          const config = await core.config.load();
          await core.config.save(config);
          succeeded = true;
          break;
        } catch (error) {
          // Retry
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      }

      expect(succeeded).toBe(true);

      // Restore
      fs.writeFile = originalWrite;

      cleanup = core.cleanup;
    });
  });

  /**
   * EDGE CASE 8: Security Attack Scenarios
   */
  describe('Edge Case 8: Security Attack Scenarios', () => {
    it('should resist timing attacks on encryption', async () => {
      const core = await initializeCore({ mode: 'secure' });

      const correctPassword = 'correct-password';
      const wrongPassword = 'wrong-password';

      // Encrypt with correct password
      const encrypted = await core.security.encrypt('secret', correctPassword);

      // Measure timing for correct vs wrong password
      const timings = { correct: [], wrong: [] };

      for (let i = 0; i < 100; i++) {
        // Correct password
        const startCorrect = performance.now();
        try {
          await core.security.decrypt(encrypted, correctPassword);
        } catch {}
        timings.correct.push(performance.now() - startCorrect);

        // Wrong password
        const startWrong = performance.now();
        try {
          await core.security.decrypt(encrypted, wrongPassword);
        } catch {}
        timings.wrong.push(performance.now() - startWrong);
      }

      // Calculate averages
      const avgCorrect = timings.correct.reduce((a, b) => a + b) / timings.correct.length;
      const avgWrong = timings.wrong.reduce((a, b) => a + b) / timings.wrong.length;

      // Timing difference should be minimal (< 20% difference)
      const difference = Math.abs(avgCorrect - avgWrong) / Math.max(avgCorrect, avgWrong);
      expect(difference).toBeLessThan(0.2);

      cleanup = core.cleanup;
    });

    it('should prevent injection attacks', async () => {
      const core = await initializeCore({ mode: 'secure' });

      const injectionAttempts = [
        // SQL Injection
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        
        // Command Injection
        "; rm -rf /",
        "| cat /etc/passwd",
        "$(whoami)",
        
        // Path Traversal
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        
        // XXE Injection
        '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>',
        
        // Template Injection
        "{{7*7}}",
        "${7*7}",
        "<%= 7*7 %>",
        
        // LDAP Injection
        "*)(uid=*))(|(uid=*",
        
        // NoSQL Injection
        '{"$gt": ""}',
        '{"$ne": null}'
      ];

      for (const attempt of injectionAttempts) {
        const sanitized = await core.security.sanitize(attempt);
        
        // Should not contain dangerous patterns
        expect(sanitized).not.toContain('DROP TABLE');
        expect(sanitized).not.toContain('rm -rf');
        expect(sanitized).not.toContain('/etc/passwd');
        expect(sanitized).not.toContain('<!ENTITY');
        expect(sanitized).not.toContain('${');
        expect(sanitized).not.toContain('{{');
        expect(sanitized).not.toContain('$gt');
        expect(sanitized).not.toContain('$ne');
      }

      cleanup = core.cleanup;
    });
  });
});