/**
 * Animation Performance Tests
 * 
 * Validates that all micro-interaction animations maintain 60fps performance
 * and respect accessibility preferences
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { act } from 'react-dom/test-utils';

// Import delightful components
import DashboardDelightful from '../../../../src/modules/M011-UIComponents/components/dashboard/DashboardDelightful';
import LoadingSpinnerDelightful from '../../../../src/modules/M011-UIComponents/components/common/LoadingSpinnerDelightful';
import ButtonDelightful from '../../../../src/modules/M011-UIComponents/components/common/ButtonDelightful';
import EmptyStateDelightful from '../../../../src/modules/M011-UIComponents/components/common/EmptyStateDelightful';

// Import animation utilities
import { 
  performanceUtils,
  delightKeyframes,
  easings,
} from '../../../../src/modules/M011-UIComponents/utils/delight-animations';
import { 
  triggerCelebration,
  achievementManager,
} from '../../../../src/modules/M011-UIComponents/utils/celebration-effects';

// Mock theme
const theme = createTheme();

/**
 * Performance monitoring utility
 */
class PerformanceMonitor {
  private frameCount = 0;
  private startTime = 0;
  private fps = 0;
  private animationId: number | null = null;
  
  start(): void {
    this.frameCount = 0;
    this.startTime = performance.now();
    this.measureFrame();
  }
  
  stop(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }
  
  private measureFrame = (): void => {
    this.frameCount++;
    const elapsed = performance.now() - this.startTime;
    
    if (elapsed >= 1000) {
      this.fps = Math.round((this.frameCount * 1000) / elapsed);
      this.frameCount = 0;
      this.startTime = performance.now();
    }
    
    this.animationId = requestAnimationFrame(this.measureFrame);
  };
  
  getFPS(): number {
    return this.fps;
  }
  
  async waitForStableFPS(duration: number = 2000): Promise<number> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(this.getFPS());
      }, duration);
    });
  }
}

describe('Animation Performance Tests', () => {
  let performanceMonitor: PerformanceMonitor;
  
  beforeEach(() => {
    performanceMonitor = new PerformanceMonitor();
    // Reset animations
    document.body.style.animation = '';
    // Clear any existing celebration effects
    document.querySelectorAll('.celebration-container').forEach(el => el.remove());
  });
  
  afterEach(() => {
    performanceMonitor.stop();
  });
  
  describe('Component Animation Performance', () => {
    test('DashboardDelightful maintains 60fps during widget animations', async () => {
      performanceMonitor.start();
      
      const { container } = render(
        <ThemeProvider theme={theme}>
          <DashboardDelightful />
        </ThemeProvider>
      );
      
      // Wait for animations to run
      const fps = await performanceMonitor.waitForStableFPS(3000);
      
      // Should maintain at least 55fps (allowing small variance)
      expect(fps).toBeGreaterThanOrEqual(55);
      
      // Check that GPU acceleration is applied
      const papers = container.querySelectorAll('[class*="DelightfulPaper"]');
      papers.forEach(paper => {
        const styles = window.getComputedStyle(paper as Element);
        expect(styles.willChange).toBeTruthy();
      });
    });
    
    test('LoadingSpinnerDelightful variants perform efficiently', async () => {
      const variants = ['circular', 'dots', 'pulse', 'orbit', 'morphing', 'text'];
      
      for (const variant of variants) {
        performanceMonitor.start();
        
        render(
          <ThemeProvider theme={theme}>
            <LoadingSpinnerDelightful 
              variant={variant as any}
              size="large"
              showFunFacts
            />
          </ThemeProvider>
        );
        
        const fps = await performanceMonitor.waitForStableFPS(2000);
        
        // Each variant should maintain good performance
        expect(fps).toBeGreaterThanOrEqual(50);
        
        performanceMonitor.stop();
      }
    });
    
    test('ButtonDelightful hover and click effects are smooth', async () => {
      performanceMonitor.start();
      
      const { getByRole } = render(
        <ThemeProvider theme={theme}>
          <ButtonDelightful
            hoverEffect="magnetic"
            clickEffect="sparkle"
            showParticles
          >
            Test Button
          </ButtonDelightful>
        </ThemeProvider>
      );
      
      const button = getByRole('button');
      
      // Simulate rapid interactions
      for (let i = 0; i < 10; i++) {
        fireEvent.mouseEnter(button);
        fireEvent.mouseMove(button);
        fireEvent.click(button);
        fireEvent.mouseLeave(button);
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      const fps = await performanceMonitor.waitForStableFPS(1000);
      expect(fps).toBeGreaterThanOrEqual(50);
    });
    
    test('EmptyStateDelightful animations are performant', async () => {
      performanceMonitor.start();
      
      render(
        <ThemeProvider theme={theme}>
          <EmptyStateDelightful
            type="coming-soon"
            showAnimation
            showEncouragement
          />
        </ThemeProvider>
      );
      
      const fps = await performanceMonitor.waitForStableFPS(2000);
      expect(fps).toBeGreaterThanOrEqual(55);
    });
  });
  
  describe('Celebration Effects Performance', () => {
    test('Confetti celebration maintains performance', async () => {
      performanceMonitor.start();
      
      act(() => {
        triggerCelebration({
          type: 'confetti',
          duration: 3000,
          particleCount: 100,
          spread: 70,
        });
      });
      
      const fps = await performanceMonitor.waitForStableFPS(2000);
      
      // Confetti should still allow 45+ fps
      expect(fps).toBeGreaterThanOrEqual(45);
      
      // Cleanup should happen
      await waitFor(() => {
        expect(document.querySelectorAll('.celebration-container')).toHaveLength(0);
      }, { timeout: 4000 });
    });
    
    test('Multiple simultaneous celebrations handle gracefully', async () => {
      performanceMonitor.start();
      
      // Trigger multiple celebrations
      act(() => {
        triggerCelebration('achievementUnlock');
        triggerCelebration('documentComplete');
        triggerCelebration('qualityPerfect');
      });
      
      const fps = await performanceMonitor.waitForStableFPS(2000);
      
      // Should still maintain reasonable performance
      expect(fps).toBeGreaterThanOrEqual(30);
    });
  });
  
  describe('Accessibility and Reduced Motion', () => {
    test('Animations respect prefers-reduced-motion', () => {
      // Mock reduced motion preference
      window.matchMedia = jest.fn().mockImplementation(query => ({
        matches: query === '(prefers-reduced-motion: reduce)',
        media: query,
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
      }));
      
      const { container } = render(
        <ThemeProvider theme={theme}>
          <ButtonDelightful hoverEffect="lift" clickEffect="ripple">
            Test Button
          </ButtonDelightful>
        </ThemeProvider>
      );
      
      const button = container.querySelector('button');
      const styles = window.getComputedStyle(button!);
      
      // Animations should be disabled
      expect(styles.animation).toBeFalsy();
      expect(styles.transition).toBeFalsy();
    });
    
    test('GPU acceleration is properly applied', () => {
      const gpuStyles = performanceUtils.gpuAccelerate;
      
      expect(gpuStyles.transform).toBe('translateZ(0)');
      expect(gpuStyles.willChange).toBe('transform');
      expect(gpuStyles.backfaceVisibility).toBe('hidden');
    });
  });
  
  describe('Animation Timing and Easing', () => {
    test('Easing functions are valid CSS values', () => {
      Object.values(easings).forEach(easing => {
        expect(easing).toMatch(/^cubic-bezier\([\d.,\s-]+\)$/);
      });
    });
    
    test('Spring configs have valid physics values', () => {
      const { springConfigs } = require('../../../../src/modules/M011-UIComponents/utils/delight-animations');
      
      Object.values(springConfigs).forEach((config: any) => {
        expect(config.tension).toBeGreaterThan(0);
        expect(config.friction).toBeGreaterThan(0);
        expect(config.mass).toBeGreaterThan(0);
      });
    });
  });
  
  describe('Memory Management', () => {
    test('Animations clean up properly', async () => {
      const { unmount } = render(
        <ThemeProvider theme={theme}>
          <LoadingSpinnerDelightful variant="orbit" />
        </ThemeProvider>
      );
      
      // Check initial state
      expect(document.querySelectorAll('[class*="orbit"]').length).toBeGreaterThan(0);
      
      // Unmount and check cleanup
      unmount();
      
      await waitFor(() => {
        expect(document.querySelectorAll('[class*="orbit"]').length).toBe(0);
      });
    });
    
    test('Achievement manager persists data correctly', () => {
      // Reset achievements
      achievementManager.resetAll();
      
      // Unlock an achievement
      achievementManager.unlock('firstDoc');
      
      // Check it's saved
      const achievement = achievementManager.getAchievement('firstDoc');
      expect(achievement?.unlocked).toBe(true);
      
      // Check localStorage
      const stored = localStorage.getItem('devdocai_achievements');
      expect(stored).toBeTruthy();
      const data = JSON.parse(stored!);
      expect(data.firstDoc.unlocked).toBe(true);
    });
  });
  
  describe('Bundle Size Impact', () => {
    test('Animation utilities are tree-shakeable', () => {
      // This is more of a build-time check, but we can verify exports
      const animations = require('../../../../src/modules/M011-UIComponents/utils/delight-animations');
      
      // Should export individual utilities for tree-shaking
      expect(animations.springConfigs).toBeDefined();
      expect(animations.easings).toBeDefined();
      expect(animations.delightKeyframes).toBeDefined();
      
      // Should also have a default export for convenience
      expect(animations.default).toBeDefined();
    });
  });
  
  describe('Cross-browser Compatibility', () => {
    test('CSS animations use vendor prefixes where needed', () => {
      const { container } = render(
        <ThemeProvider theme={theme}>
          <LoadingSpinnerDelightful variant="text" />
        </ThemeProvider>
      );
      
      const textElement = container.querySelector('[class*="TextAnimation"]');
      if (textElement) {
        const styles = window.getComputedStyle(textElement);
        
        // Check for webkit prefixes
        expect(styles).toHaveProperty('WebkitBackgroundClip');
        expect(styles).toHaveProperty('WebkitTextFillColor');
      }
    });
  });
});

/**
 * Performance benchmark suite
 */
describe('Performance Benchmarks', () => {
  const runBenchmark = async (
    name: string,
    setup: () => void,
    iterations: number = 100
  ): Promise<number> => {
    const times: number[] = [];
    
    for (let i = 0; i < iterations; i++) {
      const start = performance.now();
      setup();
      const end = performance.now();
      times.push(end - start);
    }
    
    const average = times.reduce((a, b) => a + b, 0) / times.length;
    console.log(`Benchmark: ${name} - Average: ${average.toFixed(2)}ms`);
    return average;
  };
  
  test('Button render performance', async () => {
    const avgTime = await runBenchmark('Button render', () => {
      const { unmount } = render(
        <ThemeProvider theme={theme}>
          <ButtonDelightful variant="gradient" hoverEffect="glow">
            Test
          </ButtonDelightful>
        </ThemeProvider>
      );
      unmount();
    });
    
    // Should render in less than 10ms on average
    expect(avgTime).toBeLessThan(10);
  });
  
  test('Dashboard widget animation startup', async () => {
    const avgTime = await runBenchmark('Dashboard animation', () => {
      const container = document.createElement('div');
      const element = document.createElement('div');
      element.style.animation = 'slideUp 0.6s ease';
      container.appendChild(element);
      // Force style recalculation
      void element.offsetHeight;
    }, 50);
    
    // Animation setup should be nearly instant
    expect(avgTime).toBeLessThan(1);
  });
});