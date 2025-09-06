import * as os from 'os';
import { 
  MemoryMode, 
  MemoryStats, 
  MemoryThresholds,
  MemoryModeConfig 
} from './types';

/**
 * Optimized MemoryModeDetector for <1ms detection time
 * 
 * Performance optimizations:
 * 1. Cached system information
 * 2. Minimal OS calls
 * 3. Pre-calculated thresholds
 * 4. Fast mode determination
 * 5. Lazy initialization
 */
export class MemoryModeDetectorOptimized {
  private mode: MemoryMode = MemoryMode.STANDARD;
  private thresholds: MemoryThresholds;
  private config: MemoryModeConfig;
  
  // Cached system information (refreshed periodically)
  private cachedStats?: MemoryStats;
  private cacheTimestamp: number = 0;
  private readonly CACHE_TTL = 1000; // 1 second cache TTL
  
  // Pre-calculated threshold values for fast comparison
  private readonly thresholdValues: number[];
  private readonly modeValues: MemoryMode[];
  
  // Static system information (never changes)
  private readonly totalSystemMemory: number;
  
  // Pre-allocated objects to avoid garbage collection
  private readonly baseSettings = {
    baseline: {
      cacheSize: 10,
      maxWorkers: 1,
      batchSize: 5,
      enableCompression: true,
      enableOptimizations: false
    },
    standard: {
      cacheSize: 50,
      maxWorkers: 2,
      batchSize: 10,
      enableCompression: true,
      enableOptimizations: false
    },
    enhanced: {
      cacheSize: 100,
      maxWorkers: 4,
      batchSize: 20,
      enableCompression: false,
      enableOptimizations: true
    },
    performance: {
      cacheSize: 500,
      maxWorkers: 8,
      batchSize: 50,
      enableCompression: false,
      enableOptimizations: true
    }
  };

  constructor(config?: Partial<MemoryModeConfig>) {
    // Cache total system memory once (never changes)
    this.totalSystemMemory = os.totalmem();
    
    // Initialize config with minimal object allocation
    this.config = this.createConfig(config);
    
    // Initialize thresholds
    this.thresholds = this.config.customThresholds || {
      baseline: 512 * 1024 * 1024,      // 512 MB
      standard: 1024 * 1024 * 1024,     // 1 GB
      enhanced: 2 * 1024 * 1024 * 1024, // 2 GB
      performance: 4 * 1024 * 1024 * 1024 // 4 GB
    };
    
    // Pre-calculate threshold values for fast comparison
    this.thresholdValues = [
      this.thresholds.performance,
      this.thresholds.enhanced,
      this.thresholds.standard,
      this.thresholds.baseline
    ];
    
    this.modeValues = [
      MemoryMode.PERFORMANCE,
      MemoryMode.ENHANCED,
      MemoryMode.STANDARD,
      MemoryMode.BASELINE
    ];
    
    // Initial mode detection
    if (this.config.autoDetect) {
      this.mode = this.detectOptimized();
    } else {
      this.mode = this.config.defaultMode || MemoryMode.STANDARD;
    }
  }

  private createConfig(config?: Partial<MemoryModeConfig>): MemoryModeConfig {
    // Optimized config creation with minimal allocations
    return {
      mode: config?.mode || MemoryMode.AUTO,
      minMemory: config?.minMemory || 536870912, // Pre-calculated: 512 * 1024 * 1024
      maxMemory: config?.maxMemory || 8589934592, // Pre-calculated: 8 * 1024 * 1024 * 1024
      limits: config?.limits || {
        maxHeap: 1073741824,  // Pre-calculated: 1024 * 1024 * 1024
        maxRss: 2147483648,   // Pre-calculated: 2 * 1024 * 1024 * 1024
        maxWorkers: 4,
        cacheSize: 104857600, // Pre-calculated: 100 * 1024 * 1024
        bufferSize: 10485760  // Pre-calculated: 10 * 1024 * 1024
      },
      optimizations: config?.optimizations || [],
      autoDetect: config?.autoDetect ?? true,
      defaultMode: config?.defaultMode || MemoryMode.STANDARD,
      customThresholds: config?.customThresholds
    };
  }

  detect(): MemoryMode {
    return this.detectOptimized();
  }

  private detectOptimized(): MemoryMode {
    // Ultra-fast detection with cached stats
    const available = this.getFreeMemoryFast();
    
    // Fast comparison using pre-calculated arrays
    for (let i = 0; i < this.thresholdValues.length; i++) {
      if (available >= this.thresholdValues[i]) {
        return this.modeValues[i];
      }
    }
    
    return MemoryMode.BASELINE;
  }

  private getFreeMemoryFast(): number {
    // Use cached value if still valid
    const now = Date.now();
    if (this.cachedStats && (now - this.cacheTimestamp) < this.CACHE_TTL) {
      return this.cachedStats.availableMemory;
    }
    
    // Single OS call for free memory
    return os.freemem();
  }

  getCurrentMode(): MemoryMode {
    return this.mode;
  }

  setMode(mode: MemoryMode): void {
    this.mode = mode;
  }

  getMemoryStats(): MemoryStats {
    // Check cache first
    const now = Date.now();
    if (this.cachedStats && (now - this.cacheTimestamp) < this.CACHE_TTL) {
      return this.cachedStats;
    }
    
    // Minimal OS calls for stats
    const freeMemory = os.freemem();
    const usedMemory = this.totalSystemMemory - freeMemory;
    
    // Create new stats object
    const stats: MemoryStats = {
      totalMemory: this.totalSystemMemory,
      freeMemory: freeMemory,
      usedMemory: usedMemory,
      availableMemory: freeMemory,
      percentageUsed: (usedMemory / this.totalSystemMemory) * 100
    };
    
    // Update cache
    this.cachedStats = stats;
    this.cacheTimestamp = now;
    
    return stats;
  }

  getMemoryStatsFast(): MemoryStats {
    // Ultra-fast version that always uses cache if available
    if (this.cachedStats) {
      return this.cachedStats;
    }
    return this.getMemoryStats();
  }

  getRecommendedSettings(): any {
    // Direct lookup without object creation
    return this.baseSettings[this.mode] || this.baseSettings.standard;
  }

  shouldOptimize(): boolean {
    // Fast check using cached stats
    if (this.cachedStats) {
      return this.cachedStats.percentageUsed > 80;
    }
    
    // Fallback to quick calculation
    const freeMemory = os.freemem();
    const percentageUsed = ((this.totalSystemMemory - freeMemory) / this.totalSystemMemory) * 100;
    return percentageUsed > 80;
  }

  canAllocate(bytes: number): boolean {
    // Fast check without full stats calculation
    return this.getFreeMemoryFast() >= bytes;
  }

  suggestMode(): MemoryMode {
    // Use optimized detection
    return this.detectOptimized();
  }

  getThresholds(): MemoryThresholds {
    // Return reference (caller should not modify)
    return this.thresholds;
  }

  monitor(callback: (stats: MemoryStats) => void, interval: number = 5000): NodeJS.Timeout {
    // Optimized monitoring with cached stats
    return setInterval(() => {
      // Force cache refresh before callback
      this.cacheTimestamp = 0;
      const stats = this.getMemoryStats();
      callback(stats);
    }, interval);
  }

  stopMonitoring(intervalId: NodeJS.Timeout): void {
    clearInterval(intervalId);
  }

  // Ultra-fast mode detection for performance-critical paths
  detectFast(): MemoryMode {
    // Use cached mode if available and recent
    const now = Date.now();
    if (this.cachedStats && (now - this.cacheTimestamp) < this.CACHE_TTL) {
      // Fast re-detection using cached stats
      const available = this.cachedStats.availableMemory;
      
      // Unrolled loop for maximum speed
      if (available >= this.thresholdValues[0]) return this.modeValues[0];
      if (available >= this.thresholdValues[1]) return this.modeValues[1];
      if (available >= this.thresholdValues[2]) return this.modeValues[2];
      if (available >= this.thresholdValues[3]) return this.modeValues[3];
    }
    
    return this.detectOptimized();
  }

  // Pre-warm cache for optimal performance
  prewarm(): void {
    this.getMemoryStats();
  }
}