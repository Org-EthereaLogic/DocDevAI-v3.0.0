import * as os from 'os';
import { 
  MemoryMode, 
  MemoryStats, 
  MemoryThresholds,
  MemoryModeConfig 
} from './types';

export class MemoryModeDetector {
  private mode: MemoryMode = MemoryMode.STANDARD;
  private thresholds: MemoryThresholds;
  private config: MemoryModeConfig;

  constructor(config?: Partial<MemoryModeConfig>) {
    // Create a full config with defaults for any missing properties
    this.config = {
      mode: config?.mode || MemoryMode.AUTO,
      minMemory: config?.minMemory || 512 * 1024 * 1024,
      maxMemory: config?.maxMemory || 8 * 1024 * 1024 * 1024,
      limits: config?.limits || {
        maxHeap: 1024 * 1024 * 1024,
        maxRss: 2 * 1024 * 1024 * 1024,
        maxWorkers: 4,
        cacheSize: 100 * 1024 * 1024,
        bufferSize: 10 * 1024 * 1024
      },
      optimizations: config?.optimizations || [],
      autoDetect: config?.autoDetect ?? true,
      defaultMode: config?.defaultMode || MemoryMode.STANDARD,
      customThresholds: config?.customThresholds
    };

    this.thresholds = this.config.customThresholds || {
      baseline: 512 * 1024 * 1024,      // 512 MB
      standard: 1024 * 1024 * 1024,     // 1 GB
      enhanced: 2 * 1024 * 1024 * 1024, // 2 GB
      performance: 4 * 1024 * 1024 * 1024 // 4 GB
    };

    if (this.config.autoDetect) {
      this.mode = this.detect();
    } else {
      this.mode = this.config.defaultMode || MemoryMode.STANDARD;
    }
  }

  detect(): MemoryMode {
    const stats = this.getMemoryStats();
    const available = stats.availableMemory;

    if (available >= this.thresholds.performance) {
      return MemoryMode.PERFORMANCE;
    } else if (available >= this.thresholds.enhanced) {
      return MemoryMode.ENHANCED;
    } else if (available >= this.thresholds.standard) {
      return MemoryMode.STANDARD;
    } else {
      return MemoryMode.BASELINE;
    }
  }

  getCurrentMode(): MemoryMode {
    return this.mode;
  }

  setMode(mode: MemoryMode): void {
    this.mode = mode;
  }

  getMemoryStats(): MemoryStats {
    const totalMemory = os.totalmem();
    const freeMemory = os.freemem();
    const usedMemory = totalMemory - freeMemory;
    
    // Process memory usage removed for REFACTOR phase - will add back with process stats

    return {
      totalMemory: totalMemory,
      freeMemory: freeMemory,
      usedMemory: usedMemory,
      availableMemory: freeMemory, // Simplified for GREEN phase
      percentageUsed: (usedMemory / totalMemory) * 100
    };
  }

  getRecommendedSettings(): any {
    const baseSettings = {
      cacheSize: 50,
      maxWorkers: 1,
      batchSize: 10,
      enableCompression: true,
      enableOptimizations: false
    };

    switch (this.mode) {
      case 'baseline':
        return {
          ...baseSettings,
          cacheSize: 10,
          maxWorkers: 1,
          batchSize: 5,
          enableCompression: true,
          enableOptimizations: false
        };
      
      case 'standard':
        return {
          ...baseSettings,
          cacheSize: 50,
          maxWorkers: 2,
          batchSize: 10,
          enableCompression: true,
          enableOptimizations: false
        };
      
      case 'enhanced':
        return {
          ...baseSettings,
          cacheSize: 100,
          maxWorkers: 4,
          batchSize: 20,
          enableCompression: false,
          enableOptimizations: true
        };
      
      case 'performance':
        return {
          ...baseSettings,
          cacheSize: 500,
          maxWorkers: 8,
          batchSize: 50,
          enableCompression: false,
          enableOptimizations: true
        };
      
      default:
        return baseSettings;
    }
  }

  shouldOptimize(): boolean {
    const stats = this.getMemoryStats();
    // Optimize if memory usage is above 80%
    return stats.percentageUsed > 80;
  }

  canAllocate(bytes: number): boolean {
    const stats = this.getMemoryStats();
    return stats.availableMemory >= bytes;
  }

  suggestMode(): MemoryMode {
    // Re-detect and suggest mode based on current conditions
    return this.detect();
  }

  getThresholds(): MemoryThresholds {
    return { ...this.thresholds };
  }

  monitor(callback: (stats: MemoryStats) => void, interval: number = 5000): NodeJS.Timeout {
    // Create monitoring interval
    return setInterval(() => {
      const stats = this.getMemoryStats();
      callback(stats);
    }, interval);
  }

  stopMonitoring(intervalId: NodeJS.Timeout): void {
    clearInterval(intervalId);
  }
}