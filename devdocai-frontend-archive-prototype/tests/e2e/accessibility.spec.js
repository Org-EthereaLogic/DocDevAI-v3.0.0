/**
 * Accessibility E2E Tests
 * Comprehensive WCAG 2.1 AA compliance testing using automated tools
 */

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Compliance', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should pass automated accessibility scan on homepage', async ({ page }) => {
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .exclude('#third-party-ads') // Exclude third-party content
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    const headings = await page.locator('h1, h2, h3, h4, h5, h6').all();

    // Should have exactly one h1
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBe(1);

    // Check heading order (h1 -> h2 -> h3, etc.)
    for (let i = 0; i < headings.length - 1; i++) {
      const currentLevel = parseInt(await headings[i].evaluate(el => el.tagName.slice(1)));
      const nextLevel = parseInt(await headings[i + 1].evaluate(el => el.tagName.slice(1)));

      // Next heading should not skip levels (e.g., h2 -> h4)
      expect(nextLevel - currentLevel).toBeLessThanOrEqual(1);
    }
  });

  test('should have accessible form labels', async ({ page }) => {
    // Check all form inputs have labels
    const inputs = await page.locator('input, textarea, select').all();

    for (const input of inputs) {
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledBy = await input.getAttribute('aria-labelledby');

      if (id) {
        // Check for associated label
        const label = await page.locator(`label[for="${id}"]`).count();
        const hasLabel = label > 0 || ariaLabel || ariaLabelledBy;
        expect(hasLabel).toBe(true);
      } else {
        // Must have aria-label if no id/label association
        expect(ariaLabel || ariaLabelledBy).toBeTruthy();
      }
    }
  });

  test('should support keyboard navigation', async ({ page }) => {
    // Start from the first interactive element
    await page.keyboard.press('Tab');

    const focusableElements = await page.locator(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ).all();

    // Tab through all focusable elements
    for (let i = 0; i < focusableElements.length; i++) {
      const activeElement = await page.evaluate(() => document.activeElement);
      expect(activeElement).toBeTruthy();

      // Move to next element
      await page.keyboard.press('Tab');
    }

    // Test reverse tab navigation
    await page.keyboard.press('Shift+Tab');
    const backElement = await page.evaluate(() => document.activeElement);
    expect(backElement).toBeTruthy();
  });

  test('should have sufficient color contrast', async ({ page }) => {
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .include('[data-testid]') // Focus on our components
      .analyze();

    const colorContrastViolations = accessibilityScanResults.violations.filter(
      violation => violation.id === 'color-contrast'
    );

    expect(colorContrastViolations).toEqual([]);
  });

  test('should have proper ARIA attributes', async ({ page }) => {
    // Check for required ARIA attributes
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withRules(['aria-required-attr', 'aria-valid-attr', 'aria-valid-attr-value'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);
  });

  test('should have accessible error messages', async ({ page }) => {
    // Trigger validation errors
    await page.click('[data-testid="submit-button"]');

    // Wait for error messages to appear
    await expect(page.locator('[data-testid="project-name-error"]')).toBeVisible();

    // Check that errors are properly associated with inputs
    const projectNameInput = page.locator('[data-testid="project-name-input"]');
    const ariaDescribedBy = await projectNameInput.getAttribute('aria-describedby');

    expect(ariaDescribedBy).toBeTruthy();

    // Verify the error message has the correct id
    const errorMessage = page.locator('[data-testid="project-name-error"]');
    const errorId = await errorMessage.getAttribute('id');

    expect(ariaDescribedBy).toContain(errorId);
  });

  test('should announce dynamic content changes', async ({ page }) => {
    // Fill form and submit to trigger dynamic content
    await page.fill('[data-testid="project-name-input"]', 'Accessibility Test');
    await page.fill('[data-testid="description-input"]', 'Testing accessibility announcements.');
    await page.fill('[data-testid="author-input"]', 'A11y Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Check for live regions
    const liveRegions = await page.locator('[aria-live]').all();
    expect(liveRegions.length).toBeGreaterThan(0);

    // Verify progress announcements
    const progressRegion = page.locator('[data-testid="generation-progress"]');
    const ariaLive = await progressRegion.getAttribute('aria-live');
    expect(['polite', 'assertive']).toContain(ariaLive);
  });

  test('should support screen reader navigation', async ({ page }) => {
    // Test landmark navigation
    const landmarks = await page.locator('[role="main"], [role="banner"], [role="navigation"], [role="contentinfo"]').all();
    expect(landmarks.length).toBeGreaterThan(0);

    // Test skip links
    await page.keyboard.press('Tab');
    const firstFocusable = await page.evaluate(() => document.activeElement);
    const isSkipLink = await page.evaluate(el =>
      el.textContent.toLowerCase().includes('skip') ||
      el.getAttribute('class')?.includes('skip'), firstFocusable);

    if (isSkipLink) {
      // Activate skip link
      await page.keyboard.press('Enter');
      const afterSkip = await page.evaluate(() => document.activeElement);
      expect(afterSkip).not.toBe(firstFocusable);
    }
  });
});

test.describe('Accessibility During Document Generation', () => {
  test('should maintain accessibility during loading states', async ({ page }) => {
    await page.goto('/');

    // Fill form
    await page.fill('[data-testid="project-name-input"]', 'Loading A11y Test');
    await page.fill('[data-testid="description-input"]', 'Testing accessibility during loading states.');
    await page.fill('[data-testid="author-input"]', 'Loading Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Check accessibility during loading
    await expect(page.locator('[data-testid="generation-progress"]')).toBeVisible();

    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);

    // Verify loading indicators have proper attributes
    const progressBar = page.locator('[data-testid="progress-bar"]');
    const ariaValueNow = await progressBar.getAttribute('aria-valuenow');
    const ariaValueMin = await progressBar.getAttribute('aria-valuemin');
    const ariaValueMax = await progressBar.getAttribute('aria-valuemax');

    expect(ariaValueMin).toBe('0');
    expect(ariaValueMax).toBe('100');
    expect(parseInt(ariaValueNow)).toBeGreaterThanOrEqual(0);
    expect(parseInt(ariaValueNow)).toBeLessThanOrEqual(100);
  });

  test('should announce generation completion', async ({ page }) => {
    await page.goto('/');

    // Fill and submit form
    await page.fill('[data-testid="project-name-input"]', 'Completion A11y Test');
    await page.fill('[data-testid="description-input"]', 'Testing completion announcements.');
    await page.fill('[data-testid="author-input"]', 'Completion Author');
    await page.fill('[data-testid="tech-stack-input"]', 'Vue.js');
    await page.click('[data-testid="add-tech-stack"]');

    await page.click('[data-testid="submit-button"]');

    // Wait for completion
    await expect(page.locator('[data-testid="document-content"]')).toBeVisible({ timeout: 60000 });

    // Check for completion announcement
    const completionMessage = page.locator('[data-testid="completion-announcement"]');
    if (await completionMessage.count() > 0) {
      const ariaLive = await completionMessage.getAttribute('aria-live');
      expect(['polite', 'assertive']).toContain(ariaLive);
    }
  });
});

test.describe('Mobile Accessibility', () => {
  test('should be accessible on mobile devices', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/');

    // Run accessibility scan on mobile
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);

    // Test touch target sizes
    const touchTargets = await page.locator('button, [role="button"], a, input[type="checkbox"], input[type="radio"]').all();

    for (const target of touchTargets) {
      const box = await target.boundingBox();
      if (box) {
        // WCAG 2.1 AA: Touch targets should be at least 44x44px
        expect(box.width).toBeGreaterThanOrEqual(44);
        expect(box.height).toBeGreaterThanOrEqual(44);
      }
    }
  });

  test('should support zoom up to 200%', async ({ page }) => {
    await page.goto('/');

    // Set zoom to 200%
    await page.setViewportSize({ width: 640, height: 480 }); // Simulate 200% zoom
    await page.evaluate(() => {
      document.body.style.zoom = '2';
    });

    // Content should still be accessible
    const accessibilityScanResults = await new AxeBuilder({ page })
      .withTags(['wcag2aa'])
      .analyze();

    expect(accessibilityScanResults.violations).toEqual([]);

    // Verify form is still usable
    await page.fill('[data-testid="project-name-input"]', 'Zoom Test');
    const inputValue = await page.locator('[data-testid="project-name-input"]').inputValue();
    expect(inputValue).toBe('Zoom Test');
  });
});

test.describe('Keyboard Accessibility', () => {
  test('should support all functionality via keyboard', async ({ page }) => {
    await page.goto('/');

    // Navigate using only keyboard
    await page.keyboard.press('Tab'); // First interactive element

    // Fill form using keyboard
    await page.keyboard.type('Keyboard Test Project');
    await page.keyboard.press('Tab');
    await page.keyboard.type('Testing keyboard-only accessibility.');
    await page.keyboard.press('Tab');
    await page.keyboard.type('Keyboard Author');
    await page.keyboard.press('Tab');
    await page.keyboard.type('Vue.js');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter'); // Add tech stack

    // Navigate to submit button and activate
    while (true) {
      const activeElement = await page.evaluate(() => document.activeElement);
      const testId = await page.evaluate(el => el.getAttribute('data-testid'), activeElement);

      if (testId === 'submit-button') {
        break;
      }
      await page.keyboard.press('Tab');
    }

    await page.keyboard.press('Enter');

    // Verify generation starts
    await expect(page.locator('[data-testid="generation-progress"]')).toBeVisible();
  });

  test('should provide visible focus indicators', async ({ page }) => {
    await page.goto('/');

    // Tab through interactive elements and check focus styles
    const focusableElements = await page.locator(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ).all();

    for (let i = 0; i < Math.min(focusableElements.length, 5); i++) {
      await page.keyboard.press('Tab');

      const activeElement = await page.evaluate(() => document.activeElement);
      const computedStyle = await page.evaluate(el => {
        const style = window.getComputedStyle(el);
        return {
          outline: style.outline,
          outlineWidth: style.outlineWidth,
          outlineStyle: style.outlineStyle,
          boxShadow: style.boxShadow
        };
      }, activeElement);

      // Should have visible focus indicator
      const hasFocusIndicator =
        computedStyle.outline !== 'none' ||
        computedStyle.outlineWidth !== '0px' ||
        computedStyle.boxShadow !== 'none';

      expect(hasFocusIndicator).toBe(true);
    }
  });
});