/**
 * Module 1: Performance Benchmarking Suite
 * 
 * Comprehensive performance validation under various load conditions
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
import { performance, PerformanceObserver } from 'perf_hooks';
import * as cluster from 'cluster';
import * as crypto from 'crypto';

// Performance targets from requirements
const PERFORMANCE_TARGETS = {
  configLoad: 10,        // < 10ms
  errorHandling: 5,      // < 5ms
  memoryDetection: 1,    // < 1ms
  logsPerSecond: 10000,  // > 10k/sec
  startup: 100,          // < 100ms
  encryptDecrypt: 50,    // < 50ms for small data
  concurrentOps: 1000    // Handle 1000+ concurrent operations
};

describe('Module 1: Performance Benchmarking', () => {
  const testDir = path.join(os.tmpdir(), 'devdocai-perf-test');
  let cleanup: (() => Promise<void>) | undefined;

  // Performance tracking
  const metrics: any = {
    operations: {},
    memory: {},
    timing: {}
  };

  beforeAll(async () => {
    // Set up performance observer
    const obs = new PerformanceObserver((items) => {
      items.getEntries().forEach((entry) => {
        if (!metrics.timing[entry.name]) {
          metrics.timing[entry.name] = [];
        }
        metrics.timing[entry.name].push(entry.duration);
      });
    });
    obs.observe({ entryTypes: ['measure'] });
  });

  beforeEach(async () => {
    await fs.ensureDir(testDir);
    process.env.DEVDOCAI_CONFIG_DIR = testDir;

    // Record initial memory
    if (global.gc) global.gc();
    metrics.memory.initial = process.memoryUsage();
  });

  afterEach(async () => {
    // Record final memory
    if (global.gc) global.gc();
    metrics.memory.final = process.memoryUsage();

    if (cleanup) {
      await cleanup();
      cleanup = undefined;
    }
    await fs.remove(testDir);
    delete process.env.DEVDOCAI_CONFIG_DIR;
  });

  afterAll(() => {
    // Generate performance report
    console.log('\n=== PERFORMANCE REPORT ===\n');
    
    // Calculate averages
    for (const [operation, times] of Object.entries(metrics.timing)) {
      const avg = (times as number[]).reduce((a, b) => a + b, 0) / (times as number[]).length;
      const min = Math.min(...(times as number[]));
      const max = Math.max(...(times as number[]));
      
      console.log(`${operation}:`);
      console.log(`  Average: ${avg.toFixed(2)}ms`);
      console.log(`  Min: ${min.toFixed(2)}ms`);
      console.log(`  Max: ${max.toFixed(2)}ms`);
    }

    // Memory usage
    const heapGrowth = metrics.memory.final?.heapUsed - metrics.memory.initial?.heapUsed;
    console.log(`\nMemory Growth: ${(heapGrowth / 1024 / 1024).toFixed(2)}MB`);
  });

  /**
   * BENCHMARK 1: Startup Performance
   */
  describe('Benchmark 1: Startup Performance', () => {
    it('should initialize in < 100ms', async () => {
      const times: number[] = [];

      // Test multiple initializations
      for (let i = 0; i < 10; i++) {
        performance.mark('startup-start');
        const core = await initializeCore({ mode: 'basic' });
        performance.mark('startup-end');
        performance.measure('startup', 'startup-start', 'startup-end');

        const measure = performance.getEntriesByName('startup').pop() as any;
        times.push(measure.duration);

        if (core.cleanup) await core.cleanup();
        performance.clearMarks();
        performance.clearMeasures();
      }

      const avgStartup = times.reduce((a, b) => a + b) / times.length;
      
      console.log(`Startup Performance: ${avgStartup.toFixed(2)}ms average`);
      expect(avgStartup).toBeLessThan(PERFORMANCE_TARGETS.startup);
    });

    it('should handle different modes efficiently', async () => {
      const modes: CoreMode[] = ['basic', 'performance', 'secure', 'enterprise'];
      const modeTimes: Record<string, number> = {};

      for (const mode of modes) {
        const start = performance.now();
        const core = await initializeCore({ mode });
        const duration = performance.now() - start;
        
        modeTimes[mode] = duration;
        
        if (core.cleanup) await core.cleanup();
      }

      console.log('Mode Initialization Times:', modeTimes);
      
      // All modes should initialize in reasonable time
      for (const time of Object.values(modeTimes)) {
        expect(time).toBeLessThan(PERFORMANCE_TARGETS.startup * 2); // Allow 2x for complex modes
      }
    });
  });

  /**
   * BENCHMARK 2: Configuration Performance
   */
  describe('Benchmark 2: Configuration Performance', () => {
    it('should load configuration in < 10ms', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const times: number[] = [];

      // Warm up
      await core.config.load();

      // Benchmark
      for (let i = 0; i < 100; i++) {
        const start = performance.now();
        await core.config.load();
        times.push(performance.now() - start);
      }

      const avgLoad = times.reduce((a, b) => a + b) / times.length;
      
      console.log(`Config Load: ${avgLoad.toFixed(2)}ms average`);
      expect(avgLoad).toBeLessThan(PERFORMANCE_TARGETS.configLoad);

      cleanup = core.cleanup;
    });

    it('should handle concurrent config operations', async () => {
      const core = await initializeCore({ mode: 'performance' });
      
      const start = performance.now();
      const promises = [];

      // 1000 concurrent config loads
      for (let i = 0; i < 1000; i++) {
        promises.push(core.config.load());
      }

      await Promise.all(promises);
      const duration = performance.now() - start;
      const opsPerSecond = 1000 / (duration / 1000);

      console.log(`Concurrent Config Ops: ${opsPerSecond.toFixed(0)} ops/sec`);
      expect(opsPerSecond).toBeGreaterThan(100); // Should handle > 100 ops/sec

      cleanup = core.cleanup;
    });

    it('should efficiently validate large configurations', async () => {
      const core = await initializeCore({ mode: 'performance' });

      // Create large config
      const largeConfig: any = {
        version: '3.0.0',
        privacy: { telemetry: false },
        performance: { cacheEnabled: true },
        custom: {}
      };

      // Add many custom fields
      for (let i = 0; i < 1000; i++) {
        largeConfig.custom[`field_${i}`] = {
          value: `value_${i}`,
          enabled: i % 2 === 0,
          metadata: {
            created: Date.now(),
            index: i
          }
        };
      }

      const start = performance.now();
      const validation = await core.config.validate(largeConfig);
      const duration = performance.now() - start;

      console.log(`Large Config Validation: ${duration.toFixed(2)}ms`);
      expect(validation.valid).toBe(true);
      expect(duration).toBeLessThan(100); // Should validate in < 100ms

      cleanup = core.cleanup;
    });
  });

  /**
   * BENCHMARK 3: Logging Performance
   */
  describe('Benchmark 3: Logging Performance', () => {
    it('should handle > 10k logs/second', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const logCount = 10000;

      const start = performance.now();

      // Generate logs as fast as possible
      const promises = [];
      for (let i = 0; i < logCount; i++) {
        promises.push(core.logger.log('info', `Performance test log ${i}`));
      }

      await Promise.all(promises);
      const duration = performance.now() - start;
      const logsPerSecond = logCount / (duration / 1000);

      console.log(`Logging Performance: ${logsPerSecond.toFixed(0)} logs/sec`);
      expect(logsPerSecond).toBeGreaterThan(PERFORMANCE_TARGETS.logsPerSecond);

      cleanup = core.cleanup;
    });

    it('should handle mixed log levels efficiently', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const levels = ['debug', 'info', 'warn', 'error'] as const;
      const logsPerLevel = 2500;

      const start = performance.now();
      const promises = [];

      for (const level of levels) {
        for (let i = 0; i < logsPerLevel; i++) {
          promises.push(core.logger[level](`${level} message ${i}`));
        }
      }

      await Promise.all(promises);
      const duration = performance.now() - start;
      const totalLogs = levels.length * logsPerLevel;
      const logsPerSecond = totalLogs / (duration / 1000);

      console.log(`Mixed Level Logging: ${logsPerSecond.toFixed(0)} logs/sec`);
      expect(logsPerSecond).toBeGreaterThan(PERFORMANCE_TARGETS.logsPerSecond);

      cleanup = core.cleanup;
    });

    it('should efficiently query logs', async () => {
      const core = await initializeCore({ mode: 'performance' });

      // Generate test logs
      for (let i = 0; i < 10000; i++) {
        await core.logger.log('info', `Query test ${i}`);
      }

      // Benchmark queries
      const queryTimes: number[] = [];

      for (let i = 0; i < 10; i++) {
        const start = performance.now();
        const results = await core.logger.query({
          level: 'info',
          limit: 100,
          offset: i * 100
        });
        queryTimes.push(performance.now() - start);
        
        expect(results.length).toBeLessThanOrEqual(100);
      }

      const avgQuery = queryTimes.reduce((a, b) => a + b) / queryTimes.length;
      console.log(`Log Query Performance: ${avgQuery.toFixed(2)}ms average`);
      expect(avgQuery).toBeLessThan(50); // Queries should be < 50ms

      cleanup = core.cleanup;
    });
  });

  /**
   * BENCHMARK 4: Security Operations Performance
   */
  describe('Benchmark 4: Security Operations Performance', () => {
    it('should encrypt/decrypt efficiently', async () => {
      const core = await initializeCore({ mode: 'secure' });
      const testData = 'This is sensitive data that needs encryption';
      
      // Warm up
      const encrypted = await core.security.encrypt(testData);
      await core.security.decrypt(encrypted);

      // Benchmark encryption
      const encryptTimes: number[] = [];
      for (let i = 0; i < 100; i++) {
        const start = performance.now();
        await core.security.encrypt(testData);
        encryptTimes.push(performance.now() - start);
      }

      // Benchmark decryption
      const decryptTimes: number[] = [];
      for (let i = 0; i < 100; i++) {
        const start = performance.now();
        await core.security.decrypt(encrypted);
        decryptTimes.push(performance.now() - start);
      }

      const avgEncrypt = encryptTimes.reduce((a, b) => a + b) / encryptTimes.length;
      const avgDecrypt = decryptTimes.reduce((a, b) => a + b) / decryptTimes.length;

      console.log(`Encryption: ${avgEncrypt.toFixed(2)}ms average`);
      console.log(`Decryption: ${avgDecrypt.toFixed(2)}ms average`);

      expect(avgEncrypt).toBeLessThan(PERFORMANCE_TARGETS.encryptDecrypt);
      expect(avgDecrypt).toBeLessThan(PERFORMANCE_TARGETS.encryptDecrypt);

      cleanup = core.cleanup;
    });

    it('should handle large data encryption efficiently', async () => {
      const core = await initializeCore({ mode: 'secure' });
      
      // Test different data sizes
      const sizes = [
        { name: '1KB', data: crypto.randomBytes(1024).toString('hex') },
        { name: '10KB', data: crypto.randomBytes(10 * 1024).toString('hex') },
        { name: '100KB', data: crypto.randomBytes(100 * 1024).toString('hex') },
        { name: '1MB', data: crypto.randomBytes(1024 * 1024).toString('hex') }
      ];

      for (const { name, data } of sizes) {
        const encryptStart = performance.now();
        const encrypted = await core.security.encrypt(data);
        const encryptTime = performance.now() - encryptStart;

        const decryptStart = performance.now();
        const decrypted = await core.security.decrypt(encrypted);
        const decryptTime = performance.now() - decryptStart;

        console.log(`${name}: Encrypt ${encryptTime.toFixed(2)}ms, Decrypt ${decryptTime.toFixed(2)}ms`);
        
        // Verify correctness
        expect(decrypted).toBe(data);
        
        // Performance should scale reasonably
        expect(encryptTime).toBeLessThan(1000); // < 1 second even for 1MB
        expect(decryptTime).toBeLessThan(1000);
      }

      cleanup = core.cleanup;
    });

    it('should sanitize input efficiently', async () => {
      const core = await initializeCore({ mode: 'secure' });
      
      const maliciousInputs = [
        '<script>alert("xss")</script>',
        '../../etc/passwd',
        'SELECT * FROM users; DROP TABLE users;',
        '${7*7}',
        '{{template injection}}'
      ];

      const sanitizeTimes: number[] = [];

      for (let i = 0; i < 100; i++) {
        for (const input of maliciousInputs) {
          const start = performance.now();
          await core.security.sanitize(input);
          sanitizeTimes.push(performance.now() - start);
        }
      }

      const avgSanitize = sanitizeTimes.reduce((a, b) => a + b) / sanitizeTimes.length;
      console.log(`Input Sanitization: ${avgSanitize.toFixed(2)}ms average`);
      
      expect(avgSanitize).toBeLessThan(5); // Should be very fast < 5ms

      cleanup = core.cleanup;
    });
  });

  /**
   * BENCHMARK 5: Error Handling Performance
   */
  describe('Benchmark 5: Error Handling Performance', () => {
    it('should format errors in < 5ms', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const errors = [
        new Error('Simple error'),
        new TypeError('Type error'),
        new RangeError('Range error'),
        new SyntaxError('Syntax error')
      ];

      const times: number[] = [];

      for (let i = 0; i < 100; i++) {
        for (const error of errors) {
          const start = performance.now();
          core.errorHandler.format(error);
          times.push(performance.now() - start);
        }
      }

      const avgFormat = times.reduce((a, b) => a + b) / times.length;
      console.log(`Error Formatting: ${avgFormat.toFixed(2)}ms average`);
      
      expect(avgFormat).toBeLessThan(PERFORMANCE_TARGETS.errorHandling);

      cleanup = core.cleanup;
    });

    it('should handle error storms efficiently', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const errorCount = 10000;

      const start = performance.now();

      // Generate error storm
      for (let i = 0; i < errorCount; i++) {
        const error = new Error(`Storm error ${i}`);
        core.errorHandler.format(error);
      }

      const duration = performance.now() - start;
      const errorsPerSecond = errorCount / (duration / 1000);

      console.log(`Error Storm Handling: ${errorsPerSecond.toFixed(0)} errors/sec`);
      expect(errorsPerSecond).toBeGreaterThan(1000); // Should handle > 1000 errors/sec

      cleanup = core.cleanup;
    });
  });

  /**
   * BENCHMARK 6: Memory Detection Performance
   */
  describe('Benchmark 6: Memory Detection Performance', () => {
    it('should detect memory mode in < 1ms', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const times: number[] = [];

      // Warm up
      await core.memoryDetector.detect();

      for (let i = 0; i < 1000; i++) {
        const start = performance.now();
        await core.memoryDetector.detect();
        times.push(performance.now() - start);
      }

      const avgDetect = times.reduce((a, b) => a + b) / times.length;
      console.log(`Memory Detection: ${avgDetect.toFixed(3)}ms average`);
      
      expect(avgDetect).toBeLessThan(PERFORMANCE_TARGETS.memoryDetection);

      cleanup = core.cleanup;
    });

    it('should adapt to memory pressure efficiently', async () => {
      const core = await initializeCore({ mode: 'auto' });
      
      // Simulate memory pressure
      const buffers: Buffer[] = [];
      const detectionTimes: number[] = [];

      try {
        for (let i = 0; i < 50; i++) {
          // Allocate 10MB buffer
          buffers.push(Buffer.alloc(10 * 1024 * 1024));
          
          // Measure detection time
          const start = performance.now();
          const mode = await core.memoryDetector.detect();
          detectionTimes.push(performance.now() - start);
          
          console.log(`Iteration ${i}: Mode=${mode}, Time=${detectionTimes[i].toFixed(2)}ms`);
          
          // Detection should remain fast even under pressure
          expect(detectionTimes[i]).toBeLessThan(10);
        }
      } catch (error) {
        // Expected when memory is exhausted
        console.log('Memory exhausted at iteration', buffers.length);
      }

      const avgTime = detectionTimes.reduce((a, b) => a + b) / detectionTimes.length;
      console.log(`Average detection time under pressure: ${avgTime.toFixed(2)}ms`);
      
      expect(avgTime).toBeLessThan(5);

      cleanup = core.cleanup;
    });
  });

  /**
   * BENCHMARK 7: Concurrent Operations
   */
  describe('Benchmark 7: Concurrent Operations', () => {
    it('should handle 1000+ concurrent mixed operations', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const operations = [];

      const start = performance.now();

      // Mix of different operations
      for (let i = 0; i < 250; i++) {
        operations.push(core.config.load());
        operations.push(core.logger.log('info', `Concurrent ${i}`));
        operations.push(core.security.encrypt(`data-${i}`));
        operations.push(core.memoryDetector.detect());
      }

      await Promise.all(operations);
      const duration = performance.now() - start;
      const opsPerSecond = 1000 / (duration / 1000);

      console.log(`Mixed Concurrent Ops: ${opsPerSecond.toFixed(0)} ops/sec`);
      console.log(`Total time for 1000 ops: ${duration.toFixed(2)}ms`);
      
      expect(operations.length).toBe(PERFORMANCE_TARGETS.concurrentOps);
      expect(duration).toBeLessThan(10000); // Should complete in < 10 seconds

      cleanup = core.cleanup;
    });

    it('should maintain performance under sustained load', async () => {
      const core = await initializeCore({ mode: 'performance' });
      const testDuration = 5000; // 5 seconds
      const startTime = performance.now();
      let operationCount = 0;

      // Run operations for 5 seconds
      while (performance.now() - startTime < testDuration) {
        await Promise.all([
          core.config.load(),
          core.logger.log('info', `Sustained ${operationCount}`),
          core.security.sanitize(`input-${operationCount}`),
          core.memoryDetector.detect()
        ]);
        operationCount += 4;
      }

      const actualDuration = performance.now() - startTime;
      const opsPerSecond = operationCount / (actualDuration / 1000);

      console.log(`Sustained Load: ${opsPerSecond.toFixed(0)} ops/sec over ${(actualDuration/1000).toFixed(1)}s`);
      console.log(`Total operations: ${operationCount}`);
      
      expect(opsPerSecond).toBeGreaterThan(100); // Should maintain > 100 ops/sec

      cleanup = core.cleanup;
    });
  });

  /**
   * BENCHMARK 8: Memory Efficiency
   */
  describe('Benchmark 8: Memory Efficiency', () => {
    it('should not leak memory during operations', async () => {
      if (!global.gc) {
        console.log('Skipping memory leak test (run with --expose-gc)');
        return;
      }

      const core = await initializeCore({ mode: 'performance' });
      
      // Initial memory
      global.gc();
      const initialMemory = process.memoryUsage().heapUsed;

      // Perform many operations
      for (let cycle = 0; cycle < 10; cycle++) {
        const promises = [];
        
        for (let i = 0; i < 100; i++) {
          promises.push(core.config.load());
          promises.push(core.logger.log('info', `Memory test ${cycle}-${i}`));
          promises.push(core.security.encrypt(`data-${cycle}-${i}`));
        }
        
        await Promise.all(promises);
      }

      // Final memory after GC
      global.gc();
      const finalMemory = process.memoryUsage().heapUsed;
      const memoryGrowth = finalMemory - initialMemory;
      const growthMB = memoryGrowth / 1024 / 1024;

      console.log(`Memory growth: ${growthMB.toFixed(2)}MB`);
      
      // Should not grow more than 50MB for these operations
      expect(growthMB).toBeLessThan(50);

      cleanup = core.cleanup;
    });

    it('should efficiently handle large datasets', async () => {
      const core = await initializeCore({ mode: 'performance' });
      
      // Track memory for large operations
      const memorySnapshots: any[] = [];

      // Large config
      const largeConfig: any = { version: '3.0.0', data: {} };
      for (let i = 0; i < 10000; i++) {
        largeConfig.data[`key_${i}`] = `value_${i}`;
      }

      memorySnapshots.push({
        label: 'Before operations',
        memory: process.memoryUsage()
      });

      await core.config.save(largeConfig);
      
      memorySnapshots.push({
        label: 'After save',
        memory: process.memoryUsage()
      });

      await core.config.load();
      
      memorySnapshots.push({
        label: 'After load',
        memory: process.memoryUsage()
      });

      // Log large amount of data
      for (let i = 0; i < 1000; i++) {
        await core.logger.log('info', JSON.stringify(largeConfig));
      }

      memorySnapshots.push({
        label: 'After logging',
        memory: process.memoryUsage()
      });

      // Analyze memory usage
      for (let i = 1; i < memorySnapshots.length; i++) {
        const prev = memorySnapshots[i - 1];
        const curr = memorySnapshots[i];
        const growth = (curr.memory.heapUsed - prev.memory.heapUsed) / 1024 / 1024;
        
        console.log(`${curr.label}: ${growth.toFixed(2)}MB growth`);
      }

      cleanup = core.cleanup;
    });
  });
});