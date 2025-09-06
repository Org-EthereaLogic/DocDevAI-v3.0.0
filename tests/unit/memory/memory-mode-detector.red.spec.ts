/**
 * MemoryModeDetector RED Phase Tests
 * These tests are written FIRST and will FAIL initially
 * Following TDD methodology: RED → GREEN → REFACTOR
 */

import { MemoryModeDetector } from '../../../src/cli/core/memory/MemoryModeDetector';
import { MemoryMode, SystemMemoryInfo, MemoryModeRecommendation } from '../../../src/cli/types/core';
import { MemoryLimits } from '../../../src/cli/core/memory/types';
import * as os from 'os';

describe('MemoryModeDetector - RED Phase (Failing Tests)', () => {
  let detector: MemoryModeDetector;
  const originalFreemem = os.freemem;
  const originalTotalmem = os.totalmem;

  beforeEach(() => {
    // This will fail - MemoryModeDetector doesn't exist yet
    detector = new MemoryModeDetector();
  });

  afterEach(() => {
    // Restore original functions
    os.freemem = originalFreemem;
    os.totalmem = originalTotalmem;
  });

  describe('Memory Detection', () => {
    it('should detect baseline mode for <2GB RAM', () => {
      // Arrange: Mock system with <2GB RAM
      os.totalmem = jest.fn(() => 1.5 * 1024 * 1024 * 1024); // 1.5GB
      os.freemem = jest.fn(() => 0.5 * 1024 * 1024 * 1024); // 0.5GB

      // Act: Detect memory mode
      const mode = detector.detect();

      // Assert: Baseline mode selected
      expect(mode).toBe(MemoryMode.BASELINE);
    });

    it('should detect standard mode for 2-4GB RAM', () => {
      // Arrange: Mock system with 3GB RAM
      os.totalmem = jest.fn(() => 3 * 1024 * 1024 * 1024); // 3GB
      os.freemem = jest.fn(() => 1 * 1024 * 1024 * 1024); // 1GB

      // Act: Detect memory mode
      const mode = detector.detect();

      // Assert: Standard mode selected
      expect(mode).toBe(MemoryMode.STANDARD);
    });

    it('should detect enhanced mode for 4-8GB RAM', () => {
      // Arrange: Mock system with 6GB RAM
      os.totalmem = jest.fn(() => 6 * 1024 * 1024 * 1024); // 6GB
      os.freemem = jest.fn(() => 3 * 1024 * 1024 * 1024); // 3GB

      // Act: Detect memory mode
      const mode = detector.detect();

      // Assert: Enhanced mode selected
      expect(mode).toBe(MemoryMode.ENHANCED);
    });

    it('should detect performance mode for >8GB RAM', () => {
      // Arrange: Mock system with 16GB RAM
      os.totalmem = jest.fn(() => 16 * 1024 * 1024 * 1024); // 16GB
      os.freemem = jest.fn(() => 8 * 1024 * 1024 * 1024); // 8GB

      // Act: Detect memory mode
      const mode = detector.detect();

      // Assert: Performance mode selected
      expect(mode).toBe(MemoryMode.PERFORMANCE);
    });

    it('should meet performance target of <1ms detection time', () => {
      // Arrange: Mock system memory
      os.totalmem = jest.fn(() => 8 * 1024 * 1024 * 1024);
      os.freemem = jest.fn(() => 4 * 1024 * 1024 * 1024);

      // Act: Measure detection time
      const startTime = performance.now();
      detector.detect();
      const endTime = performance.now();
      const detectionTime = endTime - startTime;

      // Assert: Detection time under 1ms
      expect(detectionTime).toBeLessThan(1);
    });
  });

  describe('System Memory Information', () => {
    it('should provide accurate system memory information', () => {
      // Arrange: Mock system memory
      const totalMemory = 8 * 1024 * 1024 * 1024; // 8GB
      const freeMemory = 3 * 1024 * 1024 * 1024; // 3GB
      os.totalmem = jest.fn(() => totalMemory);
      os.freemem = jest.fn(() => freeMemory);

      // Act: Get system memory info
      const memInfo = detector.getSystemMemory();

      // Assert: Correct memory information
      expect(memInfo.total).toBe(totalMemory);
      expect(memInfo.free).toBe(freeMemory);
      expect(memInfo.used).toBe(totalMemory - freeMemory);
      expect(memInfo.available).toBeGreaterThanOrEqual(freeMemory);
      expect(memInfo.percentage).toBeCloseTo((totalMemory - freeMemory) / totalMemory * 100, 1);
    });

    it('should handle process memory usage', () => {
      // Act: Get system memory including process info
      const memInfo = detector.getSystemMemory();

      // Assert: Process memory included
      expect(memInfo).toBeDefined();
      expect(memInfo.total).toBeGreaterThan(0);
      expect(memInfo.percentage).toBeGreaterThanOrEqual(0);
      expect(memInfo.percentage).toBeLessThanOrEqual(100);
    });

    it('should cache memory information briefly', () => {
      // Arrange: Mock changing memory
      let callCount = 0;
      os.totalmem = jest.fn(() => 8 * 1024 * 1024 * 1024);
      os.freemem = jest.fn(() => {
        callCount++;
        return (4 - callCount * 0.1) * 1024 * 1024 * 1024;
      });

      // Act: Get memory info twice quickly
      const memInfo1 = detector.getSystemMemory();
      const memInfo2 = detector.getSystemMemory();

      // Assert: Same values (cached)
      expect(memInfo1).toEqual(memInfo2);
      expect(callCount).toBe(1); // Only called once due to caching
    });
  });

  describe('Memory Mode Recommendations', () => {
    it('should recommend appropriate mode with reasoning', () => {
      // Arrange: Mock low memory system
      os.totalmem = jest.fn(() => 1.5 * 1024 * 1024 * 1024); // 1.5GB
      os.freemem = jest.fn(() => 0.2 * 1024 * 1024 * 1024); // 200MB

      // Act: Get recommendation
      const recommendation = detector.recommendMode();

      // Assert: Appropriate recommendation
      expect(recommendation.recommended).toBe(MemoryMode.BASELINE);
      expect(recommendation.reason).toContain('Limited system memory');
      expect(recommendation.systemMemory).toBeDefined();
      expect(recommendation.optimizations).toContain('Reduced cache size');
    });

    it('should consider available memory in recommendations', () => {
      // Arrange: High total but low available memory
      os.totalmem = jest.fn(() => 16 * 1024 * 1024 * 1024); // 16GB
      os.freemem = jest.fn(() => 0.5 * 1024 * 1024 * 1024); // 500MB

      // Act: Get recommendation
      const recommendation = detector.recommendMode();

      // Assert: Conservative recommendation due to low available memory
      expect(recommendation.recommended).not.toBe(MemoryMode.PERFORMANCE);
      expect(recommendation.reason).toContain('available memory');
    });

    it('should provide optimization suggestions for each mode', () => {
      // Test each mode
      const modes = [
        MemoryMode.BASELINE,
        MemoryMode.STANDARD,
        MemoryMode.ENHANCED,
        MemoryMode.PERFORMANCE
      ];

      modes.forEach(mode => {
        // Arrange: Mock memory for each mode
        const memoryMap = {
          [MemoryMode.BASELINE]: 1 * 1024 * 1024 * 1024,
          [MemoryMode.STANDARD]: 3 * 1024 * 1024 * 1024,
          [MemoryMode.ENHANCED]: 6 * 1024 * 1024 * 1024,
          [MemoryMode.PERFORMANCE]: 12 * 1024 * 1024 * 1024
        };
        
        os.totalmem = jest.fn(() => memoryMap[mode]);
        os.freemem = jest.fn(() => memoryMap[mode] * 0.5);

        // Act: Get recommendation
        const recommendation = detector.recommendMode();

        // Assert: Has optimizations
        expect(recommendation.optimizations).toBeDefined();
        expect(recommendation.optimizations.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Mode Resolution', () => {
    it('should resolve mode from override string', () => {
      // Act: Resolve with override
      const mode = detector.resolveMode('performance');

      // Assert: Override respected
      expect(mode).toBe(MemoryMode.PERFORMANCE);
    });

    it('should auto-detect when override is "auto"', () => {
      // Arrange: Mock system memory
      os.totalmem = jest.fn(() => 3 * 1024 * 1024 * 1024); // 3GB

      // Act: Resolve with auto
      const mode = detector.resolveMode('auto');

      // Assert: Auto-detected
      expect(mode).toBe(MemoryMode.STANDARD);
    });

    it('should auto-detect when no override provided', () => {
      // Arrange: Mock system memory
      os.totalmem = jest.fn(() => 6 * 1024 * 1024 * 1024); // 6GB

      // Act: Resolve without override
      const mode = detector.resolveMode();

      // Assert: Auto-detected
      expect(mode).toBe(MemoryMode.ENHANCED);
    });

    it('should validate override values', () => {
      // Act & Assert: Invalid override throws or returns auto
      const mode = detector.resolveMode('invalid-mode');
      expect([MemoryMode.AUTO, MemoryMode.BASELINE]).toContain(mode);
    });

    it('should handle case-insensitive overrides', () => {
      // Act: Resolve with different cases
      const mode1 = detector.resolveMode('PERFORMANCE');
      const mode2 = detector.resolveMode('Performance');
      const mode3 = detector.resolveMode('pErFoRmAnCe');

      // Assert: All resolve to same mode
      expect(mode1).toBe(MemoryMode.PERFORMANCE);
      expect(mode2).toBe(MemoryMode.PERFORMANCE);
      expect(mode3).toBe(MemoryMode.PERFORMANCE);
    });
  });

  describe('Memory Optimizations', () => {
    it('should apply optimizations for baseline mode', () => {
      // Arrange: Spy on process settings
      const originalMaxOldSpace = process.execArgv;
      
      // Act: Apply baseline optimizations
      detector.applyOptimizations(MemoryMode.BASELINE);

      // Assert: Conservative settings applied
      const limits = detector.getModeLimits(MemoryMode.BASELINE);
      expect(limits.maxHeap).toBeLessThanOrEqual(512 * 1024 * 1024); // <=512MB
      expect(limits.maxWorkers).toBeLessThanOrEqual(2);
      expect(limits.cacheSize).toBeLessThanOrEqual(64 * 1024 * 1024); // <=64MB
    });

    it('should apply optimizations for performance mode', () => {
      // Act: Apply performance optimizations
      detector.applyOptimizations(MemoryMode.PERFORMANCE);

      // Assert: Generous settings applied
      const limits = detector.getModeLimits(MemoryMode.PERFORMANCE);
      expect(limits.maxHeap).toBeGreaterThanOrEqual(2 * 1024 * 1024 * 1024); // >=2GB
      expect(limits.maxWorkers).toBeGreaterThanOrEqual(4);
      expect(limits.cacheSize).toBeGreaterThanOrEqual(256 * 1024 * 1024); // >=256MB
    });

    it('should apply reversible optimizations', () => {
      // Act: Apply and get initial limits
      detector.applyOptimizations(MemoryMode.BASELINE);
      const baselineLimits = detector.getModeLimits(MemoryMode.BASELINE);

      // Apply different mode
      detector.applyOptimizations(MemoryMode.PERFORMANCE);
      const performanceLimits = detector.getModeLimits(MemoryMode.PERFORMANCE);

      // Assert: Different limits applied
      expect(performanceLimits.maxHeap).toBeGreaterThan(baselineLimits.maxHeap);
      expect(performanceLimits.maxWorkers).toBeGreaterThan(baselineLimits.maxWorkers);
    });

    it('should optimize garbage collection settings', () => {
      // Act: Apply optimizations for each mode
      const modes = [
        MemoryMode.BASELINE,
        MemoryMode.STANDARD,
        MemoryMode.ENHANCED,
        MemoryMode.PERFORMANCE
      ];

      modes.forEach(mode => {
        detector.applyOptimizations(mode);
        const limits = detector.getModeLimits(mode);
        
        // Assert: GC settings appropriate for mode
        expect(limits).toBeDefined();
        expect(limits.maxHeap).toBeGreaterThan(0);
      });
    });
  });

  describe('Memory Limits', () => {
    it('should check if current usage is within limits', () => {
      // Arrange: Mock current memory usage
      const memUsage = process.memoryUsage();
      
      // Act: Check limits for different modes
      const withinBaseline = detector.isWithinLimits(MemoryMode.BASELINE);
      const withinPerformance = detector.isWithinLimits(MemoryMode.PERFORMANCE);

      // Assert: Logical results
      expect(typeof withinBaseline).toBe('boolean');
      expect(typeof withinPerformance).toBe('boolean');
      // Performance mode should be more permissive
      if (!withinBaseline) {
        expect(withinPerformance).toBe(true);
      }
    });

    it('should provide different limits for each mode', () => {
      // Act: Get limits for all modes
      const baselineLimits = detector.getModeLimits(MemoryMode.BASELINE);
      const standardLimits = detector.getModeLimits(MemoryMode.STANDARD);
      const enhancedLimits = detector.getModeLimits(MemoryMode.ENHANCED);
      const performanceLimits = detector.getModeLimits(MemoryMode.PERFORMANCE);

      // Assert: Progressive limits
      expect(baselineLimits.maxHeap).toBeLessThan(standardLimits.maxHeap);
      expect(standardLimits.maxHeap).toBeLessThan(enhancedLimits.maxHeap);
      expect(enhancedLimits.maxHeap).toBeLessThan(performanceLimits.maxHeap);

      expect(baselineLimits.maxWorkers).toBeLessThanOrEqual(standardLimits.maxWorkers);
      expect(standardLimits.maxWorkers).toBeLessThanOrEqual(enhancedLimits.maxWorkers);
      expect(enhancedLimits.maxWorkers).toBeLessThanOrEqual(performanceLimits.maxWorkers);
    });

    it('should include buffer sizes in limits', () => {
      // Act: Get limits
      const limits = detector.getModeLimits(MemoryMode.STANDARD);

      // Assert: All limit properties defined
      expect(limits.maxHeap).toBeDefined();
      expect(limits.maxRss).toBeDefined();
      expect(limits.maxWorkers).toBeDefined();
      expect(limits.cacheSize).toBeDefined();
      expect(limits.bufferSize).toBeDefined();
    });
  });

  describe('Edge Cases', () => {
    it('should handle systems with very low memory', () => {
      // Arrange: Mock extremely low memory
      os.totalmem = jest.fn(() => 512 * 1024 * 1024); // 512MB
      os.freemem = jest.fn(() => 64 * 1024 * 1024); // 64MB

      // Act: Detect mode
      const mode = detector.detect();
      const recommendation = detector.recommendMode();

      // Assert: Baseline with warnings
      expect(mode).toBe(MemoryMode.BASELINE);
      expect(recommendation.reason).toContain('Very limited');
    });

    it('should handle systems with very high memory', () => {
      // Arrange: Mock very high memory
      os.totalmem = jest.fn(() => 256 * 1024 * 1024 * 1024); // 256GB
      os.freemem = jest.fn(() => 128 * 1024 * 1024 * 1024); // 128GB

      // Act: Detect mode
      const mode = detector.detect();

      // Assert: Performance mode
      expect(mode).toBe(MemoryMode.PERFORMANCE);
    });

    it('should handle memory pressure situations', () => {
      // Arrange: High total but very low free memory
      os.totalmem = jest.fn(() => 8 * 1024 * 1024 * 1024); // 8GB
      os.freemem = jest.fn(() => 100 * 1024 * 1024); // 100MB

      // Act: Get recommendation
      const recommendation = detector.recommendMode();

      // Assert: Conservative recommendation
      expect(recommendation.recommended).not.toBe(MemoryMode.PERFORMANCE);
      expect(recommendation.recommended).not.toBe(MemoryMode.ENHANCED);
      expect(recommendation.reason).toContain('memory pressure');
    });

    it('should handle memory info retrieval failures gracefully', () => {
      // Arrange: Mock memory functions to throw
      os.totalmem = jest.fn(() => {
        throw new Error('Cannot get memory info');
      });

      // Act & Assert: Should not throw
      expect(() => {
        const mode = detector.detect();
        expect(mode).toBe(MemoryMode.BASELINE); // Safe default
      }).not.toThrow();
    });
  });

  describe('Memory Mode Thresholds', () => {
    it('should handle boundary values correctly', () => {
      // Test exact boundary values
      const boundaries = [
        { memory: 2 * 1024 * 1024 * 1024, expected: MemoryMode.STANDARD }, // Exactly 2GB
        { memory: 4 * 1024 * 1024 * 1024, expected: MemoryMode.ENHANCED }, // Exactly 4GB
        { memory: 8 * 1024 * 1024 * 1024, expected: MemoryMode.ENHANCED }, // Exactly 8GB
        { memory: 8 * 1024 * 1024 * 1024 + 1, expected: MemoryMode.PERFORMANCE } // Just over 8GB
      ];

      boundaries.forEach(({ memory, expected }) => {
        os.totalmem = jest.fn(() => memory);
        os.freemem = jest.fn(() => memory * 0.5);
        
        const mode = detector.detect();
        expect(mode).toBe(expected);
      });
    });
  });
});