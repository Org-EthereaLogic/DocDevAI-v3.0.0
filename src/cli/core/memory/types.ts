/**
 * MemoryModeDetector specific types
 * Module 1: Core Infrastructure - Memory Management
 */

import { MemoryMode, SystemMemoryInfo, MemoryModeRecommendation } from '../../types/core';

// Re-export types from core
export { MemoryMode, SystemMemoryInfo, MemoryModeRecommendation } from '../../types/core';

export interface MemoryStats {
  totalMemory: number;
  freeMemory: number;
  usedMemory: number;
  availableMemory: number;
  percentageUsed: number;
}

export interface MemoryThresholds {
  baseline: number;
  standard: number;
  enhanced: number;
  performance: number;
}

export interface IMemoryModeDetector {
  /**
   * Detect the appropriate memory mode based on system resources
   * @returns The detected memory mode
   */
  detect(): MemoryMode;

  /**
   * Get current system memory information
   * @returns System memory statistics
   */
  getSystemMemory(): SystemMemoryInfo;

  /**
   * Recommend memory mode with reasoning
   * @returns Memory mode recommendation with details
   */
  recommendMode(): MemoryModeRecommendation;

  /**
   * Apply optimizations for the specified memory mode
   * @param mode - The memory mode to optimize for
   */
  applyOptimizations(mode: MemoryMode): void;

  /**
   * Get memory mode from override or auto-detect
   * @param override - Optional memory mode override
   * @returns Resolved memory mode
   */
  resolveMode(override?: string): MemoryMode;

  /**
   * Check if current memory usage is within limits
   * @param mode - The memory mode to check against
   * @returns True if within limits
   */
  isWithinLimits(mode: MemoryMode): boolean;

  /**
   * Get memory limits for a specific mode
   * @param mode - The memory mode
   * @returns Memory limits configuration
   */
  getModeLimits(mode: MemoryMode): MemoryLimits;
}

export interface MemoryLimits {
  maxHeap: number;
  maxRss: number;
  maxWorkers: number;
  cacheSize: number;
  bufferSize: number;
}

export interface MemoryOptimization {
  name: string;
  description: string;
  apply: () => void;
  revert: () => void;
}

export interface MemoryModeConfig {
  mode: MemoryMode;
  minMemory: number;  // Minimum RAM in bytes
  maxMemory: number;  // Maximum RAM in bytes
  limits: MemoryLimits;
  optimizations: string[];
  autoDetect?: boolean;  // Auto-detect memory mode
  defaultMode?: MemoryMode;  // Default mode if auto-detect fails
  customThresholds?: MemoryThresholds;  // Custom memory thresholds
}