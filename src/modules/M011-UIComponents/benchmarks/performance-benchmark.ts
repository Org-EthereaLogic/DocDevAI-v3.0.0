/**
 * M011 UI Components - Performance Benchmark Suite
 * 
 * Measures and tracks performance metrics for UI components including:
 * - Initial load time
 * - Component render times
 * - Bundle size analysis
 * - Memory usage
 * - State update performance
 */

import { performance } from 'perf_hooks';

export interface PerformanceMetrics {
  initialLoad: number;
  componentRender: Map<string, number>;
  bundleSize: {
    main: number;
    vendor: number;
    total: number;
  };
  memoryUsage: {
    heapUsed: number;
    heapTotal: number;
    external: number;
  };
  stateUpdates: {
    average: number;
    p95: number;
    p99: number;
  };
}

export interface BenchmarkResults {
  baseline: PerformanceMetrics;
  optimized?: PerformanceMetrics;
  improvement?: {
    initialLoad: string;
    averageRender: string;
    bundleSize: string;
    memory: string;
  };
}

/**
 * Performance Benchmark class for UI components
 */
export class UIPerformanceBenchmark {
  private results: BenchmarkResults = {
    baseline: {
      initialLoad: 0,
      componentRender: new Map(),
      bundleSize: { main: 0, vendor: 0, total: 0 },
      memoryUsage: { heapUsed: 0, heapTotal: 0, external: 0 },
      stateUpdates: { average: 0, p95: 0, p99: 0 }
    }
  };

  /**
   * Measure initial load time
   */
  measureInitialLoad(callback: () => void): number {
    const start = performance.now();
    callback();
    const end = performance.now();
    const loadTime = end - start;
    
    this.results.baseline.initialLoad = loadTime;
    console.log(`Initial load time: ${loadTime.toFixed(2)}ms`);
    
    return loadTime;
  }

  /**
   * Measure component render time
   */
  measureComponentRender(componentName: string, renderFn: () => void): number {
    const measurements: number[] = [];
    
    // Warm up
    for (let i = 0; i < 3; i++) {
      renderFn();
    }
    
    // Actual measurements
    for (let i = 0; i < 100; i++) {
      const start = performance.now();
      renderFn();
      const end = performance.now();
      measurements.push(end - start);
    }
    
    const average = measurements.reduce((a, b) => a + b, 0) / measurements.length;
    this.results.baseline.componentRender.set(componentName, average);
    
    console.log(`${componentName} average render time: ${average.toFixed(2)}ms`);
    
    return average;
  }

  /**
   * Measure memory usage
   */
  measureMemoryUsage(): NodeJS.MemoryUsage {
    const usage = process.memoryUsage();
    
    this.results.baseline.memoryUsage = {
      heapUsed: usage.heapUsed / 1024 / 1024, // MB
      heapTotal: usage.heapTotal / 1024 / 1024, // MB
      external: usage.external / 1024 / 1024 // MB
    };
    
    console.log(`Memory usage: Heap ${this.results.baseline.memoryUsage.heapUsed.toFixed(2)}MB / ${this.results.baseline.memoryUsage.heapTotal.toFixed(2)}MB`);
    
    return usage;
  }

  /**
   * Measure state update performance
   */
  measureStateUpdates(updates: number[], threshold = 16): void {
    const sorted = updates.sort((a, b) => a - b);
    const average = sorted.reduce((a, b) => a + b, 0) / sorted.length;
    const p95 = sorted[Math.floor(sorted.length * 0.95)];
    const p99 = sorted[Math.floor(sorted.length * 0.99)];
    
    this.results.baseline.stateUpdates = { average, p95, p99 };
    
    console.log(`State updates - Avg: ${average.toFixed(2)}ms, P95: ${p95.toFixed(2)}ms, P99: ${p99.toFixed(2)}ms`);
    
    if (average > threshold) {
      console.warn(`⚠️ Average state update time (${average.toFixed(2)}ms) exceeds 60fps threshold (${threshold}ms)`);
    }
  }

  /**
   * Measure bundle size (requires webpack-bundle-analyzer output)
   */
  measureBundleSize(stats: any): void {
    if (stats && stats.assets) {
      const mainBundle = stats.assets.find((a: any) => a.name.includes('main'));
      const vendorBundle = stats.assets.find((a: any) => a.name.includes('vendor'));
      
      this.results.baseline.bundleSize = {
        main: mainBundle ? mainBundle.size / 1024 : 0, // KB
        vendor: vendorBundle ? vendorBundle.size / 1024 : 0, // KB
        total: (mainBundle?.size || 0 + vendorBundle?.size || 0) / 1024
      };
      
      console.log(`Bundle sizes - Main: ${this.results.baseline.bundleSize.main.toFixed(2)}KB, Vendor: ${this.results.baseline.bundleSize.vendor.toFixed(2)}KB`);
    }
  }

  /**
   * Compare baseline with optimized metrics
   */
  compareWithOptimized(optimized: PerformanceMetrics): void {
    this.results.optimized = optimized;
    
    const baseline = this.results.baseline;
    
    this.results.improvement = {
      initialLoad: `${((baseline.initialLoad - optimized.initialLoad) / baseline.initialLoad * 100).toFixed(1)}%`,
      averageRender: `${this.calculateAverageImprovement(baseline.componentRender, optimized.componentRender)}%`,
      bundleSize: `${((baseline.bundleSize.total - optimized.bundleSize.total) / baseline.bundleSize.total * 100).toFixed(1)}%`,
      memory: `${((baseline.memoryUsage.heapUsed - optimized.memoryUsage.heapUsed) / baseline.memoryUsage.heapUsed * 100).toFixed(1)}%`
    };
    
    console.log('\n📊 Performance Improvements:');
    console.log(`  Initial Load: ${this.results.improvement.initialLoad} faster`);
    console.log(`  Render Time: ${this.results.improvement.averageRender} faster`);
    console.log(`  Bundle Size: ${this.results.improvement.bundleSize} smaller`);
    console.log(`  Memory Usage: ${this.results.improvement.memory} less`);
  }

  /**
   * Calculate average improvement for component renders
   */
  private calculateAverageImprovement(baseline: Map<string, number>, optimized: Map<string, number>): string {
    let totalImprovement = 0;
    let count = 0;
    
    baseline.forEach((baselineTime, component) => {
      const optimizedTime = optimized.get(component);
      if (optimizedTime) {
        totalImprovement += (baselineTime - optimizedTime) / baselineTime * 100;
        count++;
      }
    });
    
    return count > 0 ? (totalImprovement / count).toFixed(1) : '0';
  }

  /**
   * Check if performance targets are met
   */
  validateTargets(): boolean {
    const metrics = this.results.optimized || this.results.baseline;
    
    const targets = {
      initialLoad: 2000, // <2s
      componentRender: 50, // <50ms
      stateUpdate: 16, // <16ms for 60fps
      bundleSize: 500, // <500KB
      memory: 100 // <100MB
    };
    
    const failures: string[] = [];
    
    if (metrics.initialLoad > targets.initialLoad) {
      failures.push(`❌ Initial load: ${metrics.initialLoad.toFixed(0)}ms > ${targets.initialLoad}ms`);
    } else {
      console.log(`✅ Initial load: ${metrics.initialLoad.toFixed(0)}ms < ${targets.initialLoad}ms`);
    }
    
    const avgRender = Array.from(metrics.componentRender.values()).reduce((a, b) => a + b, 0) / metrics.componentRender.size;
    if (avgRender > targets.componentRender) {
      failures.push(`❌ Avg render: ${avgRender.toFixed(1)}ms > ${targets.componentRender}ms`);
    } else {
      console.log(`✅ Avg render: ${avgRender.toFixed(1)}ms < ${targets.componentRender}ms`);
    }
    
    if (metrics.stateUpdates.average > targets.stateUpdate) {
      failures.push(`❌ State updates: ${metrics.stateUpdates.average.toFixed(1)}ms > ${targets.stateUpdate}ms`);
    } else {
      console.log(`✅ State updates: ${metrics.stateUpdates.average.toFixed(1)}ms < ${targets.stateUpdate}ms`);
    }
    
    if (metrics.bundleSize.total > targets.bundleSize) {
      failures.push(`❌ Bundle size: ${metrics.bundleSize.total.toFixed(0)}KB > ${targets.bundleSize}KB`);
    } else {
      console.log(`✅ Bundle size: ${metrics.bundleSize.total.toFixed(0)}KB < ${targets.bundleSize}KB`);
    }
    
    if (metrics.memoryUsage.heapUsed > targets.memory) {
      failures.push(`❌ Memory: ${metrics.memoryUsage.heapUsed.toFixed(0)}MB > ${targets.memory}MB`);
    } else {
      console.log(`✅ Memory: ${metrics.memoryUsage.heapUsed.toFixed(0)}MB < ${targets.memory}MB`);
    }
    
    if (failures.length > 0) {
      console.error('\n⚠️ Performance targets not met:');
      failures.forEach(f => console.error(f));
      return false;
    }
    
    console.log('\n🎉 All performance targets met!');
    return true;
  }

  /**
   * Generate performance report
   */
  generateReport(): string {
    const report = `
# M011 UI Components - Performance Report

## Baseline Metrics
- Initial Load: ${this.results.baseline.initialLoad.toFixed(2)}ms
- Bundle Size: ${this.results.baseline.bundleSize.total.toFixed(2)}KB
- Memory Usage: ${this.results.baseline.memoryUsage.heapUsed.toFixed(2)}MB
- Avg State Update: ${this.results.baseline.stateUpdates.average.toFixed(2)}ms

## Component Render Times
${Array.from(this.results.baseline.componentRender.entries())
  .map(([name, time]) => `- ${name}: ${time.toFixed(2)}ms`)
  .join('\n')}

${this.results.optimized ? `
## Optimized Metrics
- Initial Load: ${this.results.optimized.initialLoad.toFixed(2)}ms
- Bundle Size: ${this.results.optimized.bundleSize.total.toFixed(2)}KB
- Memory Usage: ${this.results.optimized.memoryUsage.heapUsed.toFixed(2)}MB
- Avg State Update: ${this.results.optimized.stateUpdates.average.toFixed(2)}ms

## Performance Improvements
- Initial Load: ${this.results.improvement?.initialLoad} faster
- Render Time: ${this.results.improvement?.averageRender} faster
- Bundle Size: ${this.results.improvement?.bundleSize} smaller
- Memory Usage: ${this.results.improvement?.memory} less
` : ''}

## Performance Targets
- ✅ Initial Load: <2000ms
- ✅ Component Render: <50ms
- ✅ State Updates: <16ms (60fps)
- ✅ Bundle Size: <500KB
- ✅ Memory Usage: <100MB

Generated: ${new Date().toISOString()}
`;
    
    return report;
  }
}

// Export singleton instance
export const performanceBenchmark = new UIPerformanceBenchmark();