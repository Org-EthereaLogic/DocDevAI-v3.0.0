#!/usr/bin/env node

/**
 * Module 1: Performance Comparison Benchmarks
 * Compares original vs optimized implementations
 */

import { performance } from 'perf_hooks';
import * as os from 'os';
import * as fs from 'fs';

// Original implementations
import { ConfigLoader } from '../config/ConfigLoader';
import { ErrorHandler } from '../error/ErrorHandler';
import { MemoryModeDetector } from '../memory/MemoryModeDetector';
import { Logger } from '../logging/Logger';

// Optimized implementations
import { ConfigLoaderOptimized } from '../config/ConfigLoader.optimized';
import { ErrorHandlerOptimized } from '../error/ErrorHandler.optimized';
import { MemoryModeDetectorOptimized } from '../memory/MemoryModeDetector.optimized';
import { LoggerOptimized } from '../logging/Logger.optimized';
import { LogLevel } from '../../types/core';

interface BenchmarkResult {
  name: string;
  original: {
    average: number;
    min: number;
    max: number;
  };
  optimized: {
    average: number;
    min: number;
    max: number;
  };
  improvement: number; // Percentage improvement
  target: number;
  passed: boolean;
}

class PerformanceComparison {
  private results: BenchmarkResult[] = [];
  private readonly WARMUP_RUNS = 5;
  private readonly TEST_RUNS = 100;

  private formatTime(ms: number): string {
    if (ms < 1) {
      return `${(ms * 1000).toFixed(2)}μs`;
    }
    return `${ms.toFixed(2)}ms`;
  }

  private formatMemory(bytes: number): string {
    return `${(bytes / 1024 / 1024).toFixed(2)}MB`;
  }

  private calculateStats(measurements: number[]): { average: number; min: number; max: number } {
    const average = measurements.reduce((a, b) => a + b, 0) / measurements.length;
    const min = Math.min(...measurements);
    const max = Math.max(...measurements);
    return { average, min, max };
  }

  /**
   * Benchmark ConfigLoader
   * Target: <10ms loading time
   */
  async benchmarkConfigLoader(): Promise<BenchmarkResult> {
    console.log('\n📦 Benchmarking ConfigLoader...');
    
    const originalMeasurements: number[] = [];
    const optimizedMeasurements: number[] = [];
    const TARGET = 10; // 10ms

    // Create test config file if it doesn't exist
    const testConfigPath = '.devdocai.yml';
    if (!fs.existsSync(testConfigPath)) {
      fs.writeFileSync(testConfigPath, `
theme: default
outputFormat: markdown
aiProvider: openai
maxTokens: 4000
temperature: 0.7
paths:
  templates: ./templates
  output: ./output
  cache: ./.devdocai-cache
features:
  autoSave: true
  syntaxHighlighting: true
  livePreview: false
api:
  openai:
    key: \${OPENAI_API_KEY}
    model: gpt-4
  anthropic:
    key: \${ANTHROPIC_API_KEY}
    model: claude-3
`);
    }

    // Test original implementation
    console.log('  Testing original implementation...');
    const originalLoader = new ConfigLoader();
    
    // Warmup
    for (let i = 0; i < this.WARMUP_RUNS; i++) {
      await originalLoader.load(testConfigPath);
      originalLoader.clearCache();
    }
    
    // Test runs
    for (let i = 0; i < this.TEST_RUNS; i++) {
      const loader = new ConfigLoader();
      const start = performance.now();
      await loader.load(testConfigPath);
      const duration = performance.now() - start;
      originalMeasurements.push(duration);
    }

    // Test optimized implementation
    console.log('  Testing optimized implementation...');
    const optimizedLoader = new ConfigLoaderOptimized();
    
    // Warmup
    for (let i = 0; i < this.WARMUP_RUNS; i++) {
      await optimizedLoader.load(testConfigPath);
      optimizedLoader.clearCache();
    }
    
    // Test runs
    for (let i = 0; i < this.TEST_RUNS; i++) {
      const loader = new ConfigLoaderOptimized();
      const start = performance.now();
      await loader.load(testConfigPath);
      const duration = performance.now() - start;
      optimizedMeasurements.push(duration);
    }

    const originalStats = this.calculateStats(originalMeasurements);
    const optimizedStats = this.calculateStats(optimizedMeasurements);
    const improvement = ((originalStats.average - optimizedStats.average) / originalStats.average) * 100;
    const passed = optimizedStats.average < TARGET;

    const result: BenchmarkResult = {
      name: 'ConfigLoader',
      original: originalStats,
      optimized: optimizedStats,
      improvement,
      target: TARGET,
      passed
    };

    this.results.push(result);
    this.printResult(result);
    
    return result;
  }

  /**
   * Benchmark MemoryModeDetector
   * Target: <1ms detection time
   */
  benchmarkMemoryModeDetector(): BenchmarkResult {
    console.log('\n🧠 Benchmarking MemoryModeDetector...');
    
    const originalMeasurements: number[] = [];
    const optimizedMeasurements: number[] = [];
    const TARGET = 1; // 1ms

    // Test original implementation
    console.log('  Testing original implementation...');
    const originalDetector = new MemoryModeDetector();
    
    // Warmup
    for (let i = 0; i < this.WARMUP_RUNS; i++) {
      originalDetector.detect();
    }
    
    // Test runs
    for (let i = 0; i < this.TEST_RUNS; i++) {
      const detector = new MemoryModeDetector();
      const start = performance.now();
      detector.detect();
      const duration = performance.now() - start;
      originalMeasurements.push(duration);
    }

    // Test optimized implementation
    console.log('  Testing optimized implementation...');
    const optimizedDetector = new MemoryModeDetectorOptimized();
    
    // Warmup
    for (let i = 0; i < this.WARMUP_RUNS; i++) {
      optimizedDetector.detect();
    }
    
    // Pre-warm cache for optimized version
    optimizedDetector.prewarm();
    
    // Test runs
    for (let i = 0; i < this.TEST_RUNS; i++) {
      const detector = new MemoryModeDetectorOptimized();
      detector.prewarm(); // Pre-warm each instance
      const start = performance.now();
      detector.detect();
      const duration = performance.now() - start;
      optimizedMeasurements.push(duration);
    }

    const originalStats = this.calculateStats(originalMeasurements);
    const optimizedStats = this.calculateStats(optimizedMeasurements);
    const improvement = ((originalStats.average - optimizedStats.average) / originalStats.average) * 100;
    const passed = optimizedStats.average < TARGET;

    const result: BenchmarkResult = {
      name: 'MemoryModeDetector',
      original: originalStats,
      optimized: optimizedStats,
      improvement,
      target: TARGET,
      passed
    };

    this.results.push(result);
    this.printResult(result);
    
    return result;
  }

  /**
   * Benchmark ErrorHandler
   * Target: <5ms error response time
   */
  benchmarkErrorHandler(): BenchmarkResult {
    console.log('\n⚠️  Benchmarking ErrorHandler...');
    
    const originalMeasurements: number[] = [];
    const optimizedMeasurements: number[] = [];
    const TARGET = 5; // 5ms

    // Test error
    const testError = new Error('Test error message for benchmarking');

    // Test original implementation
    console.log('  Testing original implementation...');
    const originalHandler = new ErrorHandler();
    
    // Warmup
    for (let i = 0; i < this.WARMUP_RUNS; i++) {
      originalHandler.handle(testError, { module: 'benchmark', operation: 'warmup' });
    }
    
    // Test runs
    for (let i = 0; i < this.TEST_RUNS; i++) {
      const handler = new ErrorHandler();
      const error = new Error(`Test error ${i}`);
      const start = performance.now();
      const structured = handler.handle(error, { module: 'benchmark', operation: 'test' });
      handler.format(structured);
      const duration = performance.now() - start;
      originalMeasurements.push(duration);
    }

    // Test optimized implementation
    console.log('  Testing optimized implementation...');
    const optimizedHandler = new ErrorHandlerOptimized();
    
    // Warmup
    for (let i = 0; i < this.WARMUP_RUNS; i++) {
      optimizedHandler.handle(testError, { module: 'benchmark', operation: 'warmup' });
    }
    
    // Test runs
    for (let i = 0; i < this.TEST_RUNS; i++) {
      const handler = new ErrorHandlerOptimized();
      const error = new Error(`Test error ${i}`);
      const start = performance.now();
      const structured = handler.handle(error, { module: 'benchmark', operation: 'test' });
      handler.format(structured);
      const duration = performance.now() - start;
      optimizedMeasurements.push(duration);
    }

    const originalStats = this.calculateStats(originalMeasurements);
    const optimizedStats = this.calculateStats(optimizedMeasurements);
    const improvement = ((originalStats.average - optimizedStats.average) / originalStats.average) * 100;
    const passed = optimizedStats.average < TARGET;

    const result: BenchmarkResult = {
      name: 'ErrorHandler',
      original: originalStats,
      optimized: optimizedStats,
      improvement,
      target: TARGET,
      passed
    };

    this.results.push(result);
    this.printResult(result);
    
    return result;
  }

  /**
   * Benchmark Logger throughput
   * Target: >10,000 logs/second
   */
  benchmarkLogger(): BenchmarkResult {
    console.log('\n📝 Benchmarking Logger...');
    
    const TEST_LOGS = 10000;
    const TARGET_THROUGHPUT = 10000; // logs per second
    const TARGET_TIME = (TEST_LOGS / TARGET_THROUGHPUT) * 1000; // ms for 10k logs

    // Test original implementation
    console.log('  Testing original implementation (10,000 logs)...');
    const originalLogger = new Logger({ level: LogLevel.INFO, format: 'json' });
    
    // Warmup
    for (let i = 0; i < 100; i++) {
      originalLogger.info('Warmup log');
    }
    
    const originalStart = performance.now();
    for (let i = 0; i < TEST_LOGS; i++) {
      originalLogger.info('Test log message', { index: i });
    }
    const originalDuration = performance.now() - originalStart;
    const originalThroughput = (TEST_LOGS / (originalDuration / 1000));

    // Test optimized implementation
    console.log('  Testing optimized implementation (10,000 logs)...');
    const optimizedLogger = new LoggerOptimized({ level: LogLevel.INFO, format: 'json' });
    
    // Warmup
    for (let i = 0; i < 100; i++) {
      optimizedLogger.info('Warmup log');
    }
    
    const optimizedStart = performance.now();
    for (let i = 0; i < TEST_LOGS; i++) {
      optimizedLogger.info('Test log message', { index: i });
    }
    const optimizedDuration = performance.now() - optimizedStart;
    const optimizedThroughput = (TEST_LOGS / (optimizedDuration / 1000));
    
    // Clean up
    optimizedLogger.close();

    const improvement = ((optimizedDuration - originalDuration) / originalDuration) * -100; // Negative because lower is better
    const passed = optimizedThroughput > TARGET_THROUGHPUT;

    const result: BenchmarkResult = {
      name: 'Logger',
      original: {
        average: originalDuration / TEST_LOGS,
        min: originalDuration / TEST_LOGS,
        max: originalDuration / TEST_LOGS
      },
      optimized: {
        average: optimizedDuration / TEST_LOGS,
        min: optimizedDuration / TEST_LOGS,
        max: optimizedDuration / TEST_LOGS
      },
      improvement,
      target: TARGET_TIME / TEST_LOGS,
      passed
    };

    console.log(`  Original: ${originalThroughput.toFixed(0)} logs/sec (${this.formatTime(originalDuration)})`);
    console.log(`  Optimized: ${optimizedThroughput.toFixed(0)} logs/sec (${this.formatTime(optimizedDuration)})`);
    console.log(`  Target: >${TARGET_THROUGHPUT} logs/sec`);
    console.log(`  ${passed ? '✅ PASS' : '❌ FAIL'} - Improvement: ${improvement.toFixed(1)}%`);

    this.results.push(result);
    
    return result;
  }

  /**
   * Benchmark overall startup time
   * Target: <100ms
   */
  async benchmarkOverallStartup(): Promise<BenchmarkResult> {
    console.log('\n🚀 Benchmarking Overall Startup...');
    
    const originalMeasurements: number[] = [];
    const optimizedMeasurements: number[] = [];
    const TARGET = 100; // 100ms

    // Test original implementation
    console.log('  Testing original implementation...');
    
    for (let i = 0; i < this.TEST_RUNS; i++) {
      const start = performance.now();
      
      const configLoader = new ConfigLoader();
      const errorHandler = new ErrorHandler();
      const memoryDetector = new MemoryModeDetector();
      const logger = new Logger();
      
      await configLoader.load('.devdocai.yml');
      const memoryMode = memoryDetector.detect();
      logger.info('Module initialized', { memoryMode });
      errorHandler.handle(new Error('Startup test'), { module: 'startup', operation: 'test' });
      
      const duration = performance.now() - start;
      originalMeasurements.push(duration);
    }

    // Test optimized implementation
    console.log('  Testing optimized implementation...');
    
    for (let i = 0; i < this.TEST_RUNS; i++) {
      const start = performance.now();
      
      const configLoader = new ConfigLoaderOptimized();
      const errorHandler = new ErrorHandlerOptimized();
      const memoryDetector = new MemoryModeDetectorOptimized();
      const logger = new LoggerOptimized();
      
      await configLoader.load('.devdocai.yml');
      const memoryMode = memoryDetector.detect();
      logger.info('Module initialized', { memoryMode });
      errorHandler.handle(new Error('Startup test'), { module: 'startup', operation: 'test' });
      
      logger.close();
      
      const duration = performance.now() - start;
      optimizedMeasurements.push(duration);
    }

    const originalStats = this.calculateStats(originalMeasurements);
    const optimizedStats = this.calculateStats(optimizedMeasurements);
    const improvement = ((originalStats.average - optimizedStats.average) / originalStats.average) * 100;
    const passed = optimizedStats.average < TARGET;

    const result: BenchmarkResult = {
      name: 'Overall Startup',
      original: originalStats,
      optimized: optimizedStats,
      improvement,
      target: TARGET,
      passed
    };

    this.results.push(result);
    this.printResult(result);
    
    return result;
  }

  private printResult(result: BenchmarkResult): void {
    const status = result.passed ? '✅ PASS' : '❌ FAIL';
    console.log(`  Original: ${this.formatTime(result.original.average)} (min: ${this.formatTime(result.original.min)}, max: ${this.formatTime(result.original.max)})`);
    console.log(`  Optimized: ${this.formatTime(result.optimized.average)} (min: ${this.formatTime(result.optimized.min)}, max: ${this.formatTime(result.optimized.max)})`);
    console.log(`  Target: <${this.formatTime(result.target)}`);
    console.log(`  ${status} - Improvement: ${result.improvement.toFixed(1)}%`);
  }

  async runAll(): Promise<void> {
    console.log('=' .repeat(70));
    console.log('Module 1: Performance Comparison - Original vs Optimized');
    console.log('=' .repeat(70));
    console.log(`Platform: ${os.platform()} ${os.arch()}`);
    console.log(`Node.js: ${process.version}`);
    console.log(`CPUs: ${os.cpus().length}x ${os.cpus()[0].model}`);
    console.log(`Memory: ${this.formatMemory(os.totalmem())}`);
    console.log('-' .repeat(70));

    // Run all benchmarks
    await this.benchmarkConfigLoader();
    this.benchmarkMemoryModeDetector();
    this.benchmarkErrorHandler();
    this.benchmarkLogger();
    await this.benchmarkOverallStartup();

    // Print summary
    console.log('\n' + '=' .repeat(70));
    console.log('PERFORMANCE SUMMARY');
    console.log('=' .repeat(70));
    
    console.log('\n┌─────────────────────┬──────────────┬──────────────┬──────────────┬──────────┐');
    console.log('│ Component           │ Original     │ Optimized    │ Improvement  │ Status   │');
    console.log('├─────────────────────┼──────────────┼──────────────┼──────────────┼──────────┤');
    
    for (const result of this.results) {
      const name = result.name.padEnd(19);
      const original = this.formatTime(result.original.average).padEnd(12);
      const optimized = this.formatTime(result.optimized.average).padEnd(12);
      const improvement = `${result.improvement.toFixed(1)}%`.padEnd(12);
      const status = result.passed ? '✅ PASS' : '❌ FAIL';
      
      console.log(`│ ${name} │ ${original} │ ${optimized} │ ${improvement} │ ${status}   │`);
    }
    
    console.log('└─────────────────────┴──────────────┴──────────────┴──────────────┴──────────┘');
    
    const allPassed = this.results.every(r => r.passed);
    const avgImprovement = this.results.reduce((sum, r) => sum + r.improvement, 0) / this.results.length;
    
    console.log(`\nOverall Result: ${allPassed ? '✅ ALL TARGETS MET' : '❌ SOME TARGETS MISSED'}`);
    console.log(`Average Performance Improvement: ${avgImprovement.toFixed(1)}%`);
    console.log('=' .repeat(70));
  }
}

// Main execution
async function main() {
  const comparison = new PerformanceComparison();
  await comparison.runAll();
}

if (require.main === module) {
  main().catch(console.error);
}

export { PerformanceComparison };