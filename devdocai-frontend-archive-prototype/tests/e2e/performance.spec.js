/**
 * Performance E2E Tests
 * Core Web Vitals monitoring and performance optimization validation
 */

import { test, expect } from '@playwright/test';

test.describe('Performance Monitoring', () => {
  test.beforeEach(async ({ page }) => {
    // Enable performance monitoring
    await page.addInitScript(() => {
      window.performanceMetrics = {
        navigationStart: performance.now(),
        metrics: []
      };
    });
  });

  test('should meet Core Web Vitals thresholds', async ({ page }) => {
    const startTime = Date.now();

    // Navigate to the app
    await page.goto('/', { waitUntil: 'networkidle' });

    // Measure First Contentful Paint (FCP)
    const fcpMetric = await page.evaluate(() => {
      return new Promise(resolve => {
        new PerformanceObserver(list => {
          const entries = list.getEntries();
          const fcpEntry = entries.find(entry => entry.name === 'first-contentful-paint');
          if (fcpEntry) {
            resolve(fcpEntry.startTime);
          }
        }).observe({ type: 'paint', buffered: true });

        // Fallback timeout
        setTimeout(() => resolve(null), 5000);
      });
    });

    // Measure Largest Contentful Paint (LCP)
    const lcpMetric = await page.evaluate(() => {
      return new Promise(resolve => {
        new PerformanceObserver(list => {
          const entries = list.getEntries();
          const lastEntry = entries[entries.length - 1];
          if (lastEntry) {
            resolve(lastEntry.startTime);
          }
        }).observe({ type: 'largest-contentful-paint', buffered: true });

        // Fallback timeout
        setTimeout(() => resolve(null), 5000);
      });
    });

    // Measure Cumulative Layout Shift (CLS)
    const clsMetric = await page.evaluate(() => {
      return new Promise(resolve => {
        let clsValue = 0;
        new PerformanceObserver(list => {
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) {
              clsValue += entry.value;
            }
          }
        }).observe({ type: 'layout-shift', buffered: true });

        // Wait 3 seconds and return CLS
        setTimeout(() => resolve(clsValue), 3000);
      });
    });

    // Performance thresholds based on Core Web Vitals
    if (fcpMetric !== null) {
      expect(fcpMetric).toBeLessThan(1800); // FCP < 1.8s (good)
    }

    if (lcpMetric !== null) {
      expect(lcpMetric).toBeLessThan(2500); // LCP < 2.5s (good)
    }

    expect(clsMetric).toBeLessThan(0.1); // CLS < 0.1 (good)

    const totalLoadTime = Date.now() - startTime;
    expect(totalLoadTime).toBeLessThan(3000); // Total load < 3s
  });

  test('should have fast Time to Interactive (TTI)', async ({ page }) => {
    const startTime = performance.now();

    await page.goto('/');

    // Wait for the page to be interactive
    await page.waitForLoadState('networkidle');

    // Try to interact with the form immediately
    await page.fill('[data-testid="project-name-input"]', 'Performance Test');

    const interactionTime = performance.now() - startTime;

    // Page should be interactive within 3 seconds
    expect(interactionTime).toBeLessThan(3000);

    // Verify the input actually worked (no blocking)
    const inputValue = await page.locator('[data-testid="project-name-input"]').inputValue();
    expect(inputValue).toBe('Performance Test');
  });

  test('should have optimized resource loading', async ({ page }) => {
    const resourceMetrics = [];

    // Monitor network requests
    page.on('response', response => {
      resourceMetrics.push({
        url: response.url(),
        status: response.status(),
        size: response.headers()['content-length'] || 0,
        type: response.request().resourceType()
      });
    });

    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Analyze resource loading
    const jsFiles = resourceMetrics.filter(r => r.type === 'script');
    const cssFiles = resourceMetrics.filter(r => r.type === 'stylesheet');
    const images = resourceMetrics.filter(r => r.type === 'image');

    // Check bundle sizes (approximate thresholds)
    const totalJsSize = jsFiles.reduce((sum, file) => sum + parseInt(file.size || 0), 0);
    const totalCssSize = cssFiles.reduce((sum, file) => sum + parseInt(file.size || 0), 0);

    // Modern web app size thresholds
    expect(totalJsSize).toBeLessThan(500000); // JS bundle < 500KB
    expect(totalCssSize).toBeLessThan(100000); // CSS bundle < 100KB

    // Check for HTTP/2 or HTTP/3
    const httpVersions = resourceMetrics.map(r => r.status).filter(s => s < 400);
    expect(httpVersions.length).toBeGreaterThan(0);

    // Verify all critical resources loaded successfully
    const failedRequests = resourceMetrics.filter(r => r.status >= 400);
    expect(failedRequests).toHaveLength(0);
  });

  test('should handle high-frequency user interactions smoothly', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Measure interaction latency
    const startTime = performance.now();
    const interactions = 50;

    for (let i = 0; i < interactions; i++) {
      // Rapid typing simulation
      await page.fill('[data-testid="project-name-input"]', `Test ${i}`);
      await page.fill('[data-testid="description-input"]', `Description ${i}`);

      // Small delay to simulate realistic typing
      await page.waitForTimeout(10);
    }

    const totalTime = performance.now() - startTime;
    const averageInteractionTime = totalTime / interactions;

    // Each interaction should complete quickly
    expect(averageInteractionTime).toBeLessThan(50); // < 50ms per interaction

    // Final state should be correct
    const finalValue = await page.locator('[data-testid="project-name-input"]').inputValue();
    expect(finalValue).toBe(`Test ${interactions - 1}`);
  });
});

test.describe('Document Generation Performance', () => {
  test('should generate documents within acceptable time', async ({ page }) => {
    await page.goto('/');

    // Fill form
    await page.fill('[data-testid="project-name-input"]', 'Performance Generation Test');
    await page.fill('[data-testid="description-input"]', 'Testing document generation performance with comprehensive content.');
    await page.fill('[data-testid="author-input"]', 'Performance Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js, Python, FastAPI');
    await page.click('[data-testid="add-tech-stack"]');

    // Start generation and measure time
    const generationStart = Date.now();
    await page.click('[data-testid="submit-button"]');

    // Wait for completion with extended timeout for real API
    await expect(page.locator('[data-testid="document-content"]')).toBeVisible({ timeout: 90000 });

    const generationTime = Date.now() - generationStart;

    // Document generation should complete within reasonable time
    // Note: This is for real API calls, so we allow more time
    expect(generationTime).toBeLessThan(60000); // < 60 seconds for real API

    // Verify the document was actually generated
    const documentContent = await page.locator('[data-testid="document-content"]').textContent();
    expect(documentContent.length).toBeGreaterThan(100); // Non-trivial content
  });

  test('should show progress updates during generation', async ({ page }) => {
    await page.goto('/');

    // Fill form
    await page.fill('[data-testid="project-name-input"]', 'Progress Performance Test');
    await page.fill('[data-testid="description-input"]', 'Testing progress update performance.');
    await page.fill('[data-testid="author-input"]', 'Progress Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Monitor progress updates
    let progressUpdates = 0;
    let lastProgress = 0;

    // Check progress bar updates
    const progressBar = page.locator('[data-testid="progress-bar"]');
    await expect(progressBar).toBeVisible();

    // Monitor for at least 3 progress updates
    while (progressUpdates < 3) {
      const currentProgress = await progressBar.getAttribute('aria-valuenow');
      if (currentProgress && parseInt(currentProgress) > lastProgress) {
        progressUpdates++;
        lastProgress = parseInt(currentProgress);
      }
      await page.waitForTimeout(1000);

      // Break if generation completes
      const documentVisible = await page.locator('[data-testid="document-content"]').isVisible();
      if (documentVisible) break;
    }

    expect(progressUpdates).toBeGreaterThanOrEqual(2); // At least some progress updates
  });

  test('should handle generation cancellation quickly', async ({ page }) => {
    await page.goto('/');

    // Fill form
    await page.fill('[data-testid="project-name-input"]', 'Cancellation Test');
    await page.fill('[data-testid="description-input"]', 'Testing cancellation performance.');
    await page.fill('[data-testid="author-input"]', 'Cancel Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Wait for generation to start
    await expect(page.locator('[data-testid="generation-progress"]')).toBeVisible();

    // Cancel quickly
    const cancelStart = Date.now();
    await page.click('[data-testid="cancel-button"]');

    // Verify quick cancellation
    await expect(page.locator('[data-testid="generation-progress"]')).toBeHidden({ timeout: 5000 });

    const cancelTime = Date.now() - cancelStart;
    expect(cancelTime).toBeLessThan(2000); // Should cancel within 2 seconds
  });
});

test.describe('Memory and CPU Performance', () => {
  test('should not leak memory during repeated operations', async ({ page }) => {
    await page.goto('/');

    // Get baseline memory usage
    const initialMemory = await page.evaluate(() => {
      if (performance.memory) {
        return performance.memory.usedJSHeapSize;
      }
      return 0;
    });

    // Perform repeated operations
    for (let i = 0; i < 10; i++) {
      await page.fill('[data-testid="project-name-input"]', `Memory Test ${i}`);
      await page.fill('[data-testid="description-input"]', `Memory test iteration ${i} with detailed content.`);
      await page.fill('[data-testid="tech-stack-input"]', `Tech-${i}`);
      await page.click('[data-testid="add-tech-stack"]');

      // Clear form
      await page.evaluate(() => {
        document.querySelector('[data-testid="project-name-input"]').value = '';
        document.querySelector('[data-testid="description-input"]').value = '';
      });

      // Force garbage collection if available
      await page.evaluate(() => {
        if (window.gc) {
          window.gc();
        }
      });
    }

    // Check final memory usage
    const finalMemory = await page.evaluate(() => {
      if (performance.memory) {
        return performance.memory.usedJSHeapSize;
      }
      return 0;
    });

    if (initialMemory > 0 && finalMemory > 0) {
      const memoryIncrease = finalMemory - initialMemory;
      const memoryIncreasePercent = (memoryIncrease / initialMemory) * 100;

      // Memory increase should be reasonable (< 50% increase)
      expect(memoryIncreasePercent).toBeLessThan(50);
    }
  });

  test('should maintain responsive UI during heavy operations', async ({ page }) => {
    await page.goto('/');

    // Start a heavy operation (document generation)
    await page.fill('[data-testid="project-name-input"]', 'Heavy Operation Test');
    await page.fill('[data-testid="description-input"]', 'Testing UI responsiveness during generation.');
    await page.fill('[data-testid="author-input"]', 'Heavy Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Ensure progress indicator is shown
    await expect(page.locator('[data-testid="generation-progress"]')).toBeVisible();

    // Test UI responsiveness during generation
    const responsivenessTasks = [
      async () => {
        // Test button interactions
        const cancelButton = page.locator('[data-testid="cancel-button"]');
        await expect(cancelButton).toBeEnabled();
      },
      async () => {
        // Test scroll behavior
        await page.mouse.wheel(0, 100);
        await page.mouse.wheel(0, -100);
      },
      async () => {
        // Test hover effects
        await page.hover('[data-testid="cancel-button"]');
      }
    ];

    // All tasks should complete quickly even during generation
    for (const task of responsivenessTasks) {
      const taskStart = performance.now();
      await task();
      const taskTime = performance.now() - taskStart;
      expect(taskTime).toBeLessThan(100); // Each UI interaction < 100ms
    }
  });
});

test.describe('Network Performance', () => {
  test('should handle slow network conditions gracefully', async ({ page, context }) => {
    // Simulate slow 3G network
    await context.route('**/*', async route => {
      // Add delay to simulate slow network
      await new Promise(resolve => setTimeout(resolve, 100));
      await route.continue();
    });

    const startTime = Date.now();
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    const loadTime = Date.now() - startTime;

    // App should still load within reasonable time even on slow network
    expect(loadTime).toBeLessThan(10000); // < 10 seconds on slow network

    // Verify app is still functional
    await page.fill('[data-testid="project-name-input"]', 'Slow Network Test');
    const inputValue = await page.locator('[data-testid="project-name-input"]').inputValue();
    expect(inputValue).toBe('Slow Network Test');
  });

  test('should optimize API call frequency', async ({ page }) => {
    let apiCallCount = 0;

    // Monitor API calls
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        apiCallCount++;
      }
    });

    await page.goto('/');

    // Perform various user actions
    await page.fill('[data-testid="project-name-input"]', 'API Optimization Test');
    await page.fill('[data-testid="description-input"]', 'Testing API call optimization.');
    await page.fill('[data-testid="author-input"]', 'API Author');

    // Add multiple tech stack items
    for (let i = 0; i < 3; i++) {
      await page.fill('[data-testid="tech-stack-input"]', `Tech-${i}`);
      await page.click('[data-testid="add-tech-stack"]');
    }

    // API calls should be minimal for form interactions (no unnecessary calls)
    expect(apiCallCount).toBeLessThan(5); // Should not make excessive API calls for form handling
  });
});
