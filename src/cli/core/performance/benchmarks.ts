/**
 * Module 1: Core Infrastructure - Performance Benchmarking Suite
 * 
 * Performance Targets:
 * - ConfigLoader: <10ms loading time
 * - ErrorHandler: <5ms error response time
 * - MemoryModeDetector: <1ms detection time
 * - Logger: High-throughput (>10k logs/sec)
 * - Overall startup: <100ms
 * - Memory usage: <50MB baseline mode
 */

import { performance } from 'perf_hooks';
import { ConfigLoader } from '../config/ConfigLoader';
import { ErrorHandler } from '../error/ErrorHandler';
import { MemoryModeDetector } from '../memory/MemoryModeDetector';
import { Logger } from '../logging/Logger';
import * as os from 'os';
import * as v8 from 'v8';

// Performance utilities
export class PerformanceUtils {
  private static formatMemory(bytes: number): string {
    return `${(bytes / 1024 / 1024).toFixed(2)}MB`;
  }

  private static formatTime(ms: number): string {
    if (ms < 1) {
      return `${(ms * 1000).toFixed(2)}μs`;
    }
    return `${ms.toFixed(2)}ms`;
  }

  static measureTime<T>(fn: () => T): { result: T; duration: number } {
    const start = performance.now();
    const result = fn();
    const duration = performance.now() - start;
    return { result, duration };
  }

  static async measureTimeAsync<T>(fn: () => Promise<T>): Promise<{ result: T; duration: number }> {
    const start = performance.now();
    const result = await fn();
    const duration = performance.now() - start;
    return { result, duration };
  }

  static getMemoryUsage(): { rss: number; heapUsed: number; heapTotal: number; external: number } {
    const mem = process.memoryUsage();
    return {
      rss: mem.rss,
      heapUsed: mem.heapUsed,
      heapTotal: mem.heapTotal,
      external: mem.external,
    };
  }

  static getHeapStatistics() {
    return v8.getHeapStatistics();
  }

  static printBenchmarkResult(name: string, duration: number, target: number, passed: boolean) {
    const status = passed ? '✅ PASS' : '❌ FAIL';
    const percentage = ((duration / target) * 100).toFixed(0);
    console.log(
      `${status} ${name}: ${PerformanceUtils.formatTime(duration)} ` +
      `(target: <${PerformanceUtils.formatTime(target)}, ${percentage}%)`
    );
  }

  static printMemoryResult(name: string, memory: number, target: number, passed: boolean) {
    const status = passed ? '✅ PASS' : '❌ FAIL';
    const percentage = ((memory / target) * 100).toFixed(0);
    console.log(
      `${status} ${name}: ${PerformanceUtils.formatMemory(memory)} ` +
      `(target: <${PerformanceUtils.formatMemory(target)}, ${percentage}%)`
    );
  }
}

// Benchmark configuration
export interface BenchmarkConfig {
  warmupRuns: number;
  testRuns: number;
  verbose: boolean;
}

export const DEFAULT_BENCHMARK_CONFIG: BenchmarkConfig = {
  warmupRuns: 3,
  testRuns: 100,
  verbose: false,
};

// Individual component benchmarks
export class ComponentBenchmarks {
  private config: BenchmarkConfig;

  constructor(config: BenchmarkConfig = DEFAULT_BENCHMARK_CONFIG) {
    this.config = config;
  }

  /**
   * Benchmark ConfigLoader
   * Target: <10ms loading time
   */
  async benchmarkConfigLoader(): Promise<{ average: number; min: number; max: number; passed: boolean }> {
    const configLoader = new ConfigLoader();
    const testConfigPath = '.devdocai.yml';
    const TARGET = 10; // 10ms

    const results: number[] = [];

    // Warmup runs
    for (let i = 0; i < this.config.warmupRuns; i++) {
      await configLoader.load(testConfigPath);
    }

    // Test runs
    for (let i = 0; i < this.config.testRuns; i++) {
      // Clear any cache between runs for accurate measurement
      const loader = new ConfigLoader();
      const { duration } = await PerformanceUtils.measureTimeAsync(
        () => loader.load(testConfigPath)
      );
      results.push(duration);
    }

    const average = results.reduce((a, b) => a + b, 0) / results.length;
    const min = Math.min(...results);
    const max = Math.max(...results);
    const passed = average < TARGET;

    PerformanceUtils.printBenchmarkResult('ConfigLoader', average, TARGET, passed);

    return { average, min, max, passed };
  }

  /**
   * Benchmark ErrorHandler
   * Target: <5ms error response time
   */
  benchmarkErrorHandler(): { average: number; min: number; max: number; passed: boolean } {
    const errorHandler = new ErrorHandler();
    const TARGET = 5; // 5ms

    const results: number[] = [];
    const testError = new Error('Test error');

    // Warmup runs
    for (let i = 0; i < this.config.warmupRuns; i++) {
      errorHandler.handle(testError, 'ERR_001');
    }

    // Test runs
    for (let i = 0; i < this.config.testRuns; i++) {
      const { duration } = PerformanceUtils.measureTime(
        () => errorHandler.handle(testError, 'ERR_001')
      );
      results.push(duration);
    }

    const average = results.reduce((a, b) => a + b, 0) / results.length;
    const min = Math.min(...results);
    const max = Math.max(...results);
    const passed = average < TARGET;

    PerformanceUtils.printBenchmarkResult('ErrorHandler', average, TARGET, passed);

    return { average, min, max, passed };
  }

  /**
   * Benchmark MemoryModeDetector
   * Target: <1ms detection time
   */
  benchmarkMemoryModeDetector(): { average: number; min: number; max: number; passed: boolean } {
    const detector = new MemoryModeDetector();
    const TARGET = 1; // 1ms

    const results: number[] = [];

    // Warmup runs
    for (let i = 0; i < this.config.warmupRuns; i++) {
      detector.detect();
    }

    // Test runs
    for (let i = 0; i < this.config.testRuns; i++) {
      const { duration } = PerformanceUtils.measureTime(
        () => detector.detect()
      );
      results.push(duration);
    }

    const average = results.reduce((a, b) => a + b, 0) / results.length;
    const min = Math.min(...results);
    const max = Math.max(...results);
    const passed = average < TARGET;

    PerformanceUtils.printBenchmarkResult('MemoryModeDetector', average, TARGET, passed);

    return { average, min, max, passed };
  }

  /**
   * Benchmark Logger throughput
   * Target: >10,000 logs/second
   */
  benchmarkLogger(): { throughput: number; average: number; passed: boolean } {
    const logger = new Logger({ level: 'info', pretty: false });
    const TARGET_THROUGHPUT = 10000; // logs per second
    const TEST_LOGS = 10000;

    // Warmup
    for (let i = 0; i < 100; i++) {
      logger.info('Warmup log message');
    }

    // Throughput test
    const start = performance.now();
    for (let i = 0; i < TEST_LOGS; i++) {
      logger.info('Test log message', { index: i });
    }
    const duration = performance.now() - start;

    const throughput = (TEST_LOGS / (duration / 1000)); // logs per second
    const average = duration / TEST_LOGS; // ms per log
    const passed = throughput > TARGET_THROUGHPUT;

    console.log(
      `${passed ? '✅ PASS' : '❌ FAIL'} Logger: ${throughput.toFixed(0)} logs/sec ` +
      `(target: >${TARGET_THROUGHPUT} logs/sec, ${PerformanceUtils.formatTime(average)}/log)`
    );

    return { throughput, average, passed };
  }

  /**
   * Benchmark overall module startup
   * Target: <100ms total startup time
   */
  async benchmarkOverallStartup(): Promise<{ duration: number; passed: boolean }> {
    const TARGET = 100; // 100ms

    const { duration } = await PerformanceUtils.measureTimeAsync(async () => {
      // Simulate full module initialization
      const configLoader = new ConfigLoader();
      const errorHandler = new ErrorHandler();
      const memoryDetector = new MemoryModeDetector();
      const logger = new Logger();

      // Initialize all components
      await configLoader.load('.devdocai.yml');
      const memoryMode = memoryDetector.detect();
      logger.info('Module initialized', { memoryMode });
      errorHandler.handle(new Error('Startup test'), 'STARTUP_TEST');
    });

    const passed = duration < TARGET;
    PerformanceUtils.printBenchmarkResult('Overall Startup', duration, TARGET, passed);

    return { duration, passed };
  }

  /**
   * Benchmark memory usage
   * Target: <50MB in baseline mode
   */
  async benchmarkMemoryUsage(): Promise<{ memory: number; passed: boolean }> {
    const TARGET = 50 * 1024 * 1024; // 50MB

    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }

    const beforeMem = PerformanceUtils.getMemoryUsage();

    // Initialize all components
    const configLoader = new ConfigLoader();
    const errorHandler = new ErrorHandler();
    const memoryDetector = new MemoryModeDetector();
    const logger = new Logger();

    await configLoader.load('.devdocai.yml');
    memoryDetector.detect();

    // Simulate some usage
    for (let i = 0; i < 100; i++) {
      logger.info('Test log', { index: i });
      errorHandler.handle(new Error(`Test error ${i}`), 'TEST');
    }

    const afterMem = PerformanceUtils.getMemoryUsage();
    const memoryUsed = afterMem.heapUsed - beforeMem.heapUsed;

    const passed = memoryUsed < TARGET;
    PerformanceUtils.printMemoryResult('Memory Usage', memoryUsed, TARGET, passed);

    return { memory: memoryUsed, passed };
  }
}

// Main benchmark runner
export class BenchmarkRunner {
  private benchmarks: ComponentBenchmarks;
  private results: Map<string, any> = new Map();

  constructor(config: BenchmarkConfig = DEFAULT_BENCHMARK_CONFIG) {
    this.benchmarks = new ComponentBenchmarks(config);
  }

  async runAll(): Promise<{ allPassed: boolean; results: Map<string, any> }> {
    console.log('='.repeat(60));
    console.log('Module 1: Core Infrastructure - Performance Benchmarks');
    console.log('='.repeat(60));
    console.log(`Platform: ${os.platform()} ${os.arch()}`);
    console.log(`Node.js: ${process.version}`);
    console.log(`CPUs: ${os.cpus().length}x ${os.cpus()[0].model}`);
    console.log(`Memory: ${PerformanceUtils.formatMemory(os.totalmem())}`);
    console.log('-'.repeat(60));

    // Run individual benchmarks
    const configResult = await this.benchmarks.benchmarkConfigLoader();
    this.results.set('ConfigLoader', configResult);

    const errorResult = this.benchmarks.benchmarkErrorHandler();
    this.results.set('ErrorHandler', errorResult);

    const memoryModeResult = this.benchmarks.benchmarkMemoryModeDetector();
    this.results.set('MemoryModeDetector', memoryModeResult);

    const loggerResult = this.benchmarks.benchmarkLogger();
    this.results.set('Logger', loggerResult);

    const startupResult = await this.benchmarks.benchmarkOverallStartup();
    this.results.set('OverallStartup', startupResult);

    const memoryResult = await this.benchmarks.benchmarkMemoryUsage();
    this.results.set('MemoryUsage', memoryResult);

    console.log('-'.repeat(60));

    // Check if all benchmarks passed
    const allPassed = 
      configResult.passed &&
      errorResult.passed &&
      memoryModeResult.passed &&
      loggerResult.passed &&
      startupResult.passed &&
      memoryResult.passed;

    console.log(`Overall Result: ${allPassed ? '✅ ALL TESTS PASSED' : '❌ SOME TESTS FAILED'}`);
    console.log('='.repeat(60));

    return { allPassed, results: this.results };
  }

  async runBaseline(): Promise<Map<string, any>> {
    console.log('Running baseline performance measurements...');
    return (await this.runAll()).results;
  }
}

// Export for CLI usage
export async function runBenchmarks(verbose: boolean = false): Promise<boolean> {
  const runner = new BenchmarkRunner({ 
    warmupRuns: 3, 
    testRuns: 100, 
    verbose 
  });
  const { allPassed } = await runner.runAll();
  return allPassed;
}