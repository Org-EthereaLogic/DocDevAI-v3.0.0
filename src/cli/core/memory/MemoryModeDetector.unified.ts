/**
 * @fileoverview Unified Memory Mode Detector with mode-based behavior
 * @module @cli/core/memory/MemoryModeDetector.unified
 * @version 1.0.0
 * @performance <1ms detection time in all modes
 * @security Input validation and audit logging
 */

import * as os from 'os';
import { SecurityService, SecurityMode } from '../security/SecurityService.unified';

/**
 * Memory modes for the application
 */
export enum MemoryMode {
  BASELINE = 'baseline',      // <512MB RAM
  STANDARD = 'standard',       // 512MB-2GB RAM
  ENHANCED = 'enhanced',       // 2GB-8GB RAM
  PERFORMANCE = 'performance'  // >8GB RAM
}

/**
 * Detector operation mode
 */
export enum DetectorMode {
  BASIC = 'basic',          // Simple detection
  OPTIMIZED = 'optimized',  // Cached, efficient detection
  SECURE = 'secure',        // Validated, audited detection
  ENTERPRISE = 'enterprise' // All features enabled
}

/**
 * Memory detection result
 */
export interface MemoryDetectionResult {
  mode: MemoryMode;
  totalMemory: number;
  freeMemory: number;
  usedMemory: number;
  percentageUsed: number;
  recommendations: string[];
  features: {
    caching: boolean;
    parallelProcessing: boolean;
    advancedOptimization: boolean;
    unlimitedBuffers: boolean;
  };
  limits: {
    maxCacheSize: number;
    maxBufferSize: number;
    maxConcurrency: number;
    maxFileSize: number;
  };
}

/**
 * Detector configuration
 */
export interface DetectorConfig {
  mode?: DetectorMode;
  security?: SecurityService;
  thresholds?: {
    baseline?: number;
    standard?: number;
    enhanced?: number;
  };
  performance?: {
    caching?: boolean;
    cacheTtl?: number;
    monitoring?: boolean;
  };
  features?: {
    recommendations?: boolean;
    autoAdjust?: boolean;
    audit?: boolean;
  };
}

/**
 * Unified Memory Mode Detector
 * Combines basic, optimized, and secure detection with configurable behavior
 */
export class UnifiedMemoryModeDetector {
  private mode: DetectorMode;
  private security: SecurityService;
  private config: Required<DetectorConfig>;
  private cache?: MemoryDetectionResult;
  private cacheTimestamp?: number;
  private monitoringInterval?: NodeJS.Timer;
  private metrics = {
    detections: 0,
    cacheHits: 0,
    cacheMisses: 0,
    averageDetectionTime: 0,
    modeChanges: 0
  };

  // Memory thresholds in bytes
  private static readonly DEFAULT_THRESHOLDS = {
    baseline: 512 * 1024 * 1024,      // 512MB
    standard: 2 * 1024 * 1024 * 1024,  // 2GB
    enhanced: 8 * 1024 * 1024 * 1024   // 8GB
  };

  // Feature recommendations by mode
  private static readonly MODE_RECOMMENDATIONS = {
    [MemoryMode.BASELINE]: [
      'Minimal caching enabled to conserve memory',
      'Single-threaded processing recommended',
      'Consider upgrading system memory for better performance',
      'Frequent garbage collection may occur'
    ],
    [MemoryMode.STANDARD]: [
      'Moderate caching enabled for balanced performance',
      'Limited parallel processing available',
      'Standard optimization features active',
      'Suitable for most documentation tasks'
    ],
    [MemoryMode.ENHANCED]: [
      'Full caching enabled for improved performance',
      'Multi-threaded processing available',
      'Advanced optimization features active',
      'Recommended for large projects'
    ],
    [MemoryMode.PERFORMANCE]: [
      'Maximum caching with no limits',
      'Full parallel processing capabilities',
      'All optimization features enabled',
      'Optimal for enterprise-scale operations'
    ]
  };

  constructor(config?: DetectorConfig) {
    this.mode = config?.mode || DetectorMode.BASIC;
    this.config = this.normalizeConfig(config);
    this.security = config?.security || new SecurityService({
      mode: this.getSecurityMode(this.mode)
    });

    this.initialize();
  }

  /**
   * Normalize configuration based on mode
   */
  private normalizeConfig(config?: DetectorConfig): Required<DetectorConfig> {
    const mode = config?.mode || DetectorMode.BASIC;
    const modeDefaults = this.getModeDefaults(mode);

    return {
      mode,
      security: config?.security || new SecurityService({
        mode: this.getSecurityMode(mode)
      }),
      thresholds: {
        ...UnifiedMemoryModeDetector.DEFAULT_THRESHOLDS,
        ...config?.thresholds
      },
      performance: {
        caching: mode === DetectorMode.OPTIMIZED || mode === DetectorMode.ENTERPRISE,
        cacheTtl: 60000, // 1 minute
        monitoring: mode === DetectorMode.ENTERPRISE,
        ...modeDefaults.performance,
        ...config?.performance
      },
      features: {
        recommendations: true,
        autoAdjust: mode === DetectorMode.ENTERPRISE,
        audit: mode === DetectorMode.SECURE || mode === DetectorMode.ENTERPRISE,
        ...modeDefaults.features,
        ...config?.features
      }
    };
  }

  /**
   * Get mode-specific defaults
   */
  private getModeDefaults(mode: DetectorMode): Partial<DetectorConfig> {
    switch (mode) {
      case DetectorMode.BASIC:
        return {
          performance: { caching: false, monitoring: false },
          features: { recommendations: true, audit: false }
        };
      
      case DetectorMode.OPTIMIZED:
        return {
          performance: { caching: true, cacheTtl: 60000 },
          features: { recommendations: true }
        };
      
      case DetectorMode.SECURE:
        return {
          performance: { caching: false },
          features: { audit: true, recommendations: true }
        };
      
      case DetectorMode.ENTERPRISE:
        return {
          performance: { caching: true, cacheTtl: 30000, monitoring: true },
          features: { recommendations: true, autoAdjust: true, audit: true }
        };
      
      default:
        return {};
    }
  }

  /**
   * Map detector mode to security mode
   */
  private getSecurityMode(mode: DetectorMode): SecurityMode {
    switch (mode) {
      case DetectorMode.BASIC:
        return SecurityMode.BASIC;
      case DetectorMode.OPTIMIZED:
        return SecurityMode.STANDARD;
      case DetectorMode.SECURE:
        return SecurityMode.SECURE;
      case DetectorMode.ENTERPRISE:
        return SecurityMode.ENTERPRISE;
      default:
        return SecurityMode.STANDARD;
    }
  }

  /**
   * Initialize detector
   */
  private initialize(): void {
    // Setup monitoring if enabled
    if (this.config.performance.monitoring) {
      this.startMonitoring();
    }
  }

  /**
   * Detect memory mode
   */
  async detect(): Promise<MemoryDetectionResult> {
    const startTime = Date.now();
    this.metrics.detections++;

    try {
      // Check cache if enabled
      if (this.config.performance.caching && this.isCacheValid()) {
        this.metrics.cacheHits++;
        this.metrics.averageDetectionTime = this.updateAverageTime(startTime);
        return this.cache!;
      }
      this.metrics.cacheMisses++;

      // Get system memory information
      const totalMemory = os.totalmem();
      const freeMemory = os.freemem();
      const usedMemory = totalMemory - freeMemory;
      const percentageUsed = (usedMemory / totalMemory) * 100;

      // Validate if secure mode
      if (this.config.features.audit) {
        const validation = await this.security.validate(
          { totalMemory, freeMemory },
          { type: 'memory_detection', context: 'system_check' }
        );
        
        if (!validation.valid) {
          throw new Error(`Memory detection validation failed: ${validation.errors?.join(', ')}`);
        }
      }

      // Determine memory mode
      const mode = this.determineMode(totalMemory);

      // Check for mode change
      if (this.cache && this.cache.mode !== mode) {
        this.metrics.modeChanges++;
        
        if (this.config.features.audit) {
          await this.security.audit('memory_mode_changed', {
            previousMode: this.cache.mode,
            newMode: mode,
            totalMemory,
            freeMemory
          });
        }
      }

      // Create detection result
      const result: MemoryDetectionResult = {
        mode,
        totalMemory,
        freeMemory,
        usedMemory,
        percentageUsed,
        recommendations: this.config.features.recommendations ? 
          this.getRecommendations(mode, percentageUsed) : [],
        features: this.getFeatures(mode),
        limits: this.getLimits(mode, totalMemory)
      };

      // Cache result if enabled
      if (this.config.performance.caching) {
        this.cache = result;
        this.cacheTimestamp = Date.now();
      }

      // Audit if enabled
      if (this.config.features.audit) {
        await this.security.audit('memory_detected', {
          mode,
          totalMemory,
          freeMemory,
          percentageUsed
        });
      }

      this.metrics.averageDetectionTime = this.updateAverageTime(startTime);
      return result;

    } catch (error) {
      this.metrics.averageDetectionTime = this.updateAverageTime(startTime);
      
      if (this.config.features.audit) {
        await this.security.audit('memory_detection_error', {
          error: error.message
        });
      }
      
      throw error;
    }
  }

  /**
   * Determine memory mode based on total memory
   */
  private determineMode(totalMemory: number): MemoryMode {
    if (totalMemory < this.config.thresholds.baseline!) {
      return MemoryMode.BASELINE;
    } else if (totalMemory < this.config.thresholds.standard!) {
      return MemoryMode.STANDARD;
    } else if (totalMemory < this.config.thresholds.enhanced!) {
      return MemoryMode.ENHANCED;
    } else {
      return MemoryMode.PERFORMANCE;
    }
  }

  /**
   * Get recommendations for memory mode
   */
  private getRecommendations(mode: MemoryMode, percentageUsed: number): string[] {
    const recommendations = [...UnifiedMemoryModeDetector.MODE_RECOMMENDATIONS[mode]];

    // Add usage-based recommendations
    if (percentageUsed > 90) {
      recommendations.push('⚠️ Memory usage critical - consider closing other applications');
    } else if (percentageUsed > 75) {
      recommendations.push('⚠️ Memory usage high - performance may be affected');
    } else if (percentageUsed < 25) {
      recommendations.push('✅ Plenty of memory available - all features can be enabled');
    }

    return recommendations;
  }

  /**
   * Get features for memory mode
   */
  private getFeatures(mode: MemoryMode): MemoryDetectionResult['features'] {
    switch (mode) {
      case MemoryMode.BASELINE:
        return {
          caching: false,
          parallelProcessing: false,
          advancedOptimization: false,
          unlimitedBuffers: false
        };
      
      case MemoryMode.STANDARD:
        return {
          caching: true,
          parallelProcessing: false,
          advancedOptimization: false,
          unlimitedBuffers: false
        };
      
      case MemoryMode.ENHANCED:
        return {
          caching: true,
          parallelProcessing: true,
          advancedOptimization: true,
          unlimitedBuffers: false
        };
      
      case MemoryMode.PERFORMANCE:
        return {
          caching: true,
          parallelProcessing: true,
          advancedOptimization: true,
          unlimitedBuffers: true
        };
      
      default:
        return {
          caching: false,
          parallelProcessing: false,
          advancedOptimization: false,
          unlimitedBuffers: false
        };
    }
  }

  /**
   * Get limits for memory mode
   */
  private getLimits(mode: MemoryMode, totalMemory: number): MemoryDetectionResult['limits'] {
    const baseLimit = Math.floor(totalMemory * 0.1); // 10% of total memory

    switch (mode) {
      case MemoryMode.BASELINE:
        return {
          maxCacheSize: Math.min(50 * 1024 * 1024, baseLimit),      // 50MB max
          maxBufferSize: Math.min(10 * 1024 * 1024, baseLimit),     // 10MB max
          maxConcurrency: 1,
          maxFileSize: Math.min(5 * 1024 * 1024, baseLimit)         // 5MB max
        };
      
      case MemoryMode.STANDARD:
        return {
          maxCacheSize: Math.min(200 * 1024 * 1024, baseLimit * 2),  // 200MB max
          maxBufferSize: Math.min(50 * 1024 * 1024, baseLimit),      // 50MB max
          maxConcurrency: 2,
          maxFileSize: Math.min(20 * 1024 * 1024, baseLimit)         // 20MB max
        };
      
      case MemoryMode.ENHANCED:
        return {
          maxCacheSize: Math.min(1024 * 1024 * 1024, baseLimit * 4), // 1GB max
          maxBufferSize: Math.min(200 * 1024 * 1024, baseLimit * 2), // 200MB max
          maxConcurrency: 4,
          maxFileSize: Math.min(100 * 1024 * 1024, baseLimit * 2)    // 100MB max
        };
      
      case MemoryMode.PERFORMANCE:
        return {
          maxCacheSize: -1,  // Unlimited
          maxBufferSize: -1, // Unlimited
          maxConcurrency: os.cpus().length,
          maxFileSize: -1    // Unlimited
        };
      
      default:
        return {
          maxCacheSize: 50 * 1024 * 1024,
          maxBufferSize: 10 * 1024 * 1024,
          maxConcurrency: 1,
          maxFileSize: 5 * 1024 * 1024
        };
    }
  }

  /**
   * Check if cache is valid
   */
  private isCacheValid(): boolean {
    if (!this.cache || !this.cacheTimestamp) {
      return false;
    }

    const age = Date.now() - this.cacheTimestamp;
    return age < this.config.performance.cacheTtl!;
  }

  /**
   * Update average detection time
   */
  private updateAverageTime(startTime: number): number {
    const detectionTime = Date.now() - startTime;
    const prevAvg = this.metrics.averageDetectionTime;
    const count = this.metrics.detections;
    
    return (prevAvg * (count - 1) + detectionTime) / count;
  }

  /**
   * Start memory monitoring
   */
  private startMonitoring(): void {
    this.monitoringInterval = setInterval(async () => {
      const result = await this.detect();
      
      // Auto-adjust if enabled and memory pressure detected
      if (this.config.features.autoAdjust && result.percentageUsed > 80) {
        await this.autoAdjust(result);
      }
    }, 30000); // Check every 30 seconds
  }

  /**
   * Auto-adjust based on memory pressure
   */
  private async autoAdjust(result: MemoryDetectionResult): Promise<void> {
    // Downgrade features if memory pressure is high
    if (result.percentageUsed > 90 && result.mode !== MemoryMode.BASELINE) {
      if (this.config.features.audit) {
        await this.security.audit('memory_auto_adjust', {
          reason: 'high_memory_pressure',
          percentageUsed: result.percentageUsed,
          action: 'downgrade_features'
        });
      }
      
      // Force garbage collection if available
      if (global.gc) {
        global.gc();
      }
    }
  }

  /**
   * Get current memory mode without full detection
   */
  getCurrentMode(): MemoryMode | null {
    return this.cache?.mode || null;
  }

  /**
   * Get detector metrics
   */
  getMetrics(): typeof this.metrics {
    return { ...this.metrics };
  }

  /**
   * Force cache invalidation
   */
  invalidateCache(): void {
    this.cache = undefined;
    this.cacheTimestamp = undefined;
  }

  /**
   * Update detector configuration
   */
  updateConfig(config: Partial<DetectorConfig>): void {
    this.config = this.normalizeConfig({
      ...this.config,
      ...config
    });

    // Reinitialize if mode changed
    if (config.mode) {
      this.mode = config.mode;
      this.cleanup();
      this.initialize();
    }
  }

  /**
   * Cleanup resources
   */
  async cleanup(): Promise<void> {
    if (this.monitoringInterval) {
      clearInterval(this.monitoringInterval);
    }

    this.invalidateCache();
    await this.security.cleanup();
  }
}

// Export factory function
export function createMemoryModeDetector(config?: DetectorConfig): UnifiedMemoryModeDetector {
  return new UnifiedMemoryModeDetector(config);
}

// Export default instance
export const memoryModeDetector = new UnifiedMemoryModeDetector({ mode: DetectorMode.BASIC });