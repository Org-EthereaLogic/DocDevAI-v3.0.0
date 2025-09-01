/**
 * Performance Monitor - Real-time performance tracking utilities
 * 
 * Features:
 * - React component render tracking
 * - FPS monitoring
 * - Memory usage tracking
 * - Network request monitoring
 * - Performance budgets
 */

import { useEffect, useRef, useCallback, useState } from 'react';

interface PerformanceMetrics {
  fps: number;
  renderTime: number;
  memoryUsage: number;
  networkRequests: number;
  bundleSize?: number;
}

interface PerformanceBudget {
  maxRenderTime: number;
  minFPS: number;
  maxMemoryMB: number;
  maxBundleSizeKB: number;
}

/**
 * Default performance budgets
 */
export const DEFAULT_BUDGETS: PerformanceBudget = {
  maxRenderTime: 50, // 50ms
  minFPS: 30, // 30fps minimum
  maxMemoryMB: 100, // 100MB
  maxBundleSizeKB: 500 // 500KB
};

/**
 * Performance monitoring class
 */
export class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metrics: PerformanceMetrics = {
    fps: 60,
    renderTime: 0,
    memoryUsage: 0,
    networkRequests: 0
  };
  private observers: Set<(metrics: PerformanceMetrics) => void> = new Set();
  private frameCount = 0;
  private lastFrameTime = performance.now();
  private rafId?: number;
  private isMonitoring = false;

  private constructor() {}

  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }

  /**
   * Start monitoring performance
   */
  start(): void {
    if (this.isMonitoring) return;
    
    this.isMonitoring = true;
    this.monitorFPS();
    this.monitorMemory();
    this.monitorNetwork();
  }

  /**
   * Stop monitoring performance
   */
  stop(): void {
    this.isMonitoring = false;
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
    }
  }

  /**
   * Monitor FPS
   */
  private monitorFPS = (): void => {
    if (!this.isMonitoring) return;

    const currentTime = performance.now();
    const delta = currentTime - this.lastFrameTime;
    
    this.frameCount++;
    
    if (delta >= 1000) {
      this.metrics.fps = Math.round((this.frameCount * 1000) / delta);
      this.frameCount = 0;
      this.lastFrameTime = currentTime;
      this.notifyObservers();
    }
    
    this.rafId = requestAnimationFrame(this.monitorFPS);
  };

  /**
   * Monitor memory usage
   */
  private monitorMemory(): void {
    if (!this.isMonitoring) return;

    setInterval(() => {
      if (!this.isMonitoring) return;
      
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        this.metrics.memoryUsage = Math.round(memory.usedJSHeapSize / 1024 / 1024);
        this.notifyObservers();
      }
    }, 2000);
  }

  /**
   * Monitor network requests
   */
  private monitorNetwork(): void {
    if (!this.isMonitoring) return;

    let requestCount = 0;
    
    // Intercept fetch
    const originalFetch = window.fetch;
    window.fetch = async (...args) => {
      requestCount++;
      this.metrics.networkRequests = requestCount;
      this.notifyObservers();
      return originalFetch(...args);
    };

    // Intercept XMLHttpRequest
    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(...args: any) {
      requestCount++;
      PerformanceMonitor.getInstance().metrics.networkRequests = requestCount;
      PerformanceMonitor.getInstance().notifyObservers();
      return originalOpen.apply(this, args as any);
    };
  }

  /**
   * Measure component render time
   */
  measureRender(componentName: string, callback: () => void): number {
    const start = performance.now();
    callback();
    const end = performance.now();
    const renderTime = end - start;
    
    this.metrics.renderTime = renderTime;
    this.notifyObservers();
    
    if (renderTime > DEFAULT_BUDGETS.maxRenderTime) {
      console.warn(`⚠️ ${componentName} render time (${renderTime.toFixed(2)}ms) exceeds budget (${DEFAULT_BUDGETS.maxRenderTime}ms)`);
    }
    
    return renderTime;
  }

  /**
   * Subscribe to metrics updates
   */
  subscribe(callback: (metrics: PerformanceMetrics) => void): () => void {
    this.observers.add(callback);
    return () => this.observers.delete(callback);
  }

  /**
   * Notify all observers
   */
  private notifyObservers(): void {
    this.observers.forEach(callback => callback(this.metrics));
  }

  /**
   * Get current metrics
   */
  getMetrics(): PerformanceMetrics {
    return { ...this.metrics };
  }

  /**
   * Check if metrics meet budgets
   */
  checkBudgets(budgets: PerformanceBudget = DEFAULT_BUDGETS): {
    passed: boolean;
    violations: string[];
  } {
    const violations: string[] = [];
    
    if (this.metrics.fps < budgets.minFPS) {
      violations.push(`FPS (${this.metrics.fps}) below minimum (${budgets.minFPS})`);
    }
    
    if (this.metrics.renderTime > budgets.maxRenderTime) {
      violations.push(`Render time (${this.metrics.renderTime}ms) exceeds budget (${budgets.maxRenderTime}ms)`);
    }
    
    if (this.metrics.memoryUsage > budgets.maxMemoryMB) {
      violations.push(`Memory usage (${this.metrics.memoryUsage}MB) exceeds budget (${budgets.maxMemoryMB}MB)`);
    }
    
    return {
      passed: violations.length === 0,
      violations
    };
  }
}

/**
 * React hook for performance monitoring
 */
export function usePerformanceMonitor() {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    fps: 60,
    renderTime: 0,
    memoryUsage: 0,
    networkRequests: 0
  });
  
  useEffect(() => {
    const monitor = PerformanceMonitor.getInstance();
    monitor.start();
    
    const unsubscribe = monitor.subscribe(setMetrics);
    
    return () => {
      unsubscribe();
    };
  }, []);
  
  return metrics;
}

/**
 * React hook for measuring component render performance
 */
export function useRenderPerformance(componentName: string) {
  const renderCount = useRef(0);
  const renderTimes = useRef<number[]>([]);
  
  useEffect(() => {
    const start = performance.now();
    
    return () => {
      const end = performance.now();
      const renderTime = end - start;
      
      renderCount.current++;
      renderTimes.current.push(renderTime);
      
      // Keep only last 100 render times
      if (renderTimes.current.length > 100) {
        renderTimes.current.shift();
      }
      
      // Log slow renders
      if (renderTime > DEFAULT_BUDGETS.maxRenderTime) {
        console.warn(`⚠️ ${componentName} slow render: ${renderTime.toFixed(2)}ms`);
      }
    };
  });
  
  const getStats = useCallback(() => {
    const times = renderTimes.current;
    if (times.length === 0) return null;
    
    const sorted = [...times].sort((a, b) => a - b);
    const average = times.reduce((a, b) => a + b, 0) / times.length;
    const p50 = sorted[Math.floor(sorted.length * 0.5)];
    const p95 = sorted[Math.floor(sorted.length * 0.95)];
    const p99 = sorted[Math.floor(sorted.length * 0.99)];
    
    return {
      renderCount: renderCount.current,
      average,
      p50,
      p95,
      p99,
      min: sorted[0],
      max: sorted[sorted.length - 1]
    };
  }, []);
  
  return { getStats };
}

/**
 * Performance profiler HOC
 */
export function withPerformanceProfiler<P extends object>(
  Component: React.ComponentType<P>,
  componentName: string
) {
  return (props: P) => {
    const monitor = PerformanceMonitor.getInstance();
    const renderStart = useRef<number>();
    
    useEffect(() => {
      renderStart.current = performance.now();
      
      return () => {
        if (renderStart.current) {
          const renderTime = performance.now() - renderStart.current;
          monitor.measureRender(componentName, () => {});
        }
      };
    });
    
    return <Component {...props} />;
  };
}

/**
 * Export singleton instance
 */
export const performanceMonitor = PerformanceMonitor.getInstance();