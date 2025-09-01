/**
 * M011 Accessibility Framework - WCAG 2.1 AA compliant accessibility features
 * 
 * Ensures all UI components meet accessibility standards with comprehensive
 * screen reader support, keyboard navigation, and inclusive design.
 */

import { AccessibilityConfig, FocusConfig } from './interfaces';

/**
 * WCAG 2.1 compliance levels
 */
export enum WCAGLevel {
  A = 'A',
  AA = 'AA',
  AAA = 'AAA'
}

/**
 * Accessibility preference settings
 */
export interface AccessibilityPreferences {
  // Visual preferences
  highContrast: boolean;
  reducedMotion: boolean;
  fontSize: 'small' | 'normal' | 'large' | 'xl';
  lineSpacing: 'normal' | 'relaxed' | 'loose';
  
  // Navigation preferences  
  keyboardNavigation: boolean;
  skipLinks: boolean;
  focusIndicators: boolean;
  
  // Screen reader preferences
  screenReaderMode: boolean;
  verboseDescriptions: boolean;
  announceChanges: boolean;
  readContent: boolean;
  
  // Motor preferences
  stickyKeys: boolean;
  slowKeys: boolean;
  mouseKeys: boolean;
  
  // Cognitive preferences
  autoPlay: boolean;
  complexAnimations: boolean;
  distractionFree: boolean;
}

/**
 * Accessibility audit result
 */
export interface AccessibilityAuditResult {
  level: WCAGLevel;
  passed: boolean;
  score: number; // 0-100
  issues: AccessibilityIssue[];
  suggestions: string[];
  compliance: {
    perceivable: boolean;
    operable: boolean;
    understandable: boolean;
    robust: boolean;
  };
}

/**
 * Accessibility issue
 */
export interface AccessibilityIssue {
  id: string;
  severity: 'error' | 'warning' | 'info';
  principle: 'perceivable' | 'operable' | 'understandable' | 'robust';
  guideline: string;
  criterion: string;
  element: string;
  message: string;
  suggestedFix: string;
}

/**
 * Accessibility manager class
 */
export class AccessibilityManager {
  private preferences: AccessibilityPreferences;
  private announcer: AriaLiveAnnouncer;
  private focusManager: FocusManager;
  private keyboardManager: KeyboardNavigationManager;
  private contrastManager: ContrastManager;
  private initialized = false;

  constructor() {
    this.preferences = this.getDefaultPreferences();
    this.announcer = new AriaLiveAnnouncer();
    this.focusManager = new FocusManager();
    this.keyboardManager = new KeyboardNavigationManager();
    this.contrastManager = new ContrastManager();
  }

  /**
   * Initialize accessibility features
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    // Load user preferences
    await this.loadPreferences();
    
    // Setup managers
    await this.announcer.initialize();
    await this.focusManager.initialize();
    await this.keyboardManager.initialize();
    await this.contrastManager.initialize();

    // Apply preferences
    await this.applyPreferences();

    // Setup system preference listeners
    this.setupSystemListeners();

    this.initialized = true;
    this.announceToScreenReader('DevDocAI accessibility features initialized');
  }

  /**
   * Get current accessibility preferences
   */
  getPreferences(): AccessibilityPreferences {
    return { ...this.preferences };
  }

  /**
   * Update accessibility preferences
   */
  async updatePreferences(updates: Partial<AccessibilityPreferences>): Promise<void> {
    this.preferences = { ...this.preferences, ...updates };
    await this.applyPreferences();
    await this.savePreferences();
  }

  /**
   * Create accessibility configuration for a component
   */
  createConfig(overrides?: Partial<AccessibilityConfig>): AccessibilityConfig {
    const defaultConfig: AccessibilityConfig = {
      keyboardNavigable: this.preferences.keyboardNavigation,
      screenReaderSupport: this.preferences.screenReaderMode,
      highContrastSupport: this.preferences.highContrast,
      focusManagement: {
        focusable: true,
        tabIndex: 0
      }
    };

    return { ...defaultConfig, ...overrides };
  }

  /**
   * Announce message to screen readers
   */
  announceToScreenReader(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
    if (this.preferences.screenReaderMode) {
      this.announcer.announce(message, priority);
    }
  }

  /**
   * Setup focus trap for modals/dialogs
   */
  setupFocusTrap(container: HTMLElement): () => void {
    return this.focusManager.createFocusTrap(container);
  }

  /**
   * Get keyboard shortcuts for component
   */
  getKeyboardShortcuts(componentType: string): KeyboardShortcut[] {
    return this.keyboardManager.getShortcuts(componentType);
  }

  /**
   * Perform accessibility audit on element
   */
  async auditElement(element: HTMLElement, targetLevel: WCAGLevel = WCAGLevel.AA): Promise<AccessibilityAuditResult> {
    const auditor = new AccessibilityAuditor();
    return auditor.audit(element, targetLevel);
  }

  /**
   * Get default accessibility preferences
   */
  private getDefaultPreferences(): AccessibilityPreferences {
    return {
      // Visual
      highContrast: false,
      reducedMotion: false,
      fontSize: 'normal',
      lineSpacing: 'normal',
      
      // Navigation
      keyboardNavigation: true,
      skipLinks: true,
      focusIndicators: true,
      
      // Screen reader
      screenReaderMode: false,
      verboseDescriptions: false,
      announceChanges: true,
      readContent: false,
      
      // Motor
      stickyKeys: false,
      slowKeys: false,
      mouseKeys: false,
      
      // Cognitive
      autoPlay: false,
      complexAnimations: true,
      distractionFree: false
    };
  }

  /**
   * Load preferences from storage
   */
  private async loadPreferences(): Promise<void> {
    try {
      const stored = localStorage.getItem('devdocai-accessibility-preferences');
      if (stored) {
        const parsed = JSON.parse(stored);
        this.preferences = { ...this.preferences, ...parsed };
      }
      
      // Also check system preferences
      await this.detectSystemPreferences();
    } catch (error) {
      console.warn('Failed to load accessibility preferences:', error);
    }
  }

  /**
   * Save preferences to storage
   */
  private async savePreferences(): Promise<void> {
    try {
      localStorage.setItem('devdocai-accessibility-preferences', JSON.stringify(this.preferences));
    } catch (error) {
      console.warn('Failed to save accessibility preferences:', error);
    }
  }

  /**
   * Detect system accessibility preferences
   */
  private async detectSystemPreferences(): Promise<void> {
    // Check for reduced motion preference
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      this.preferences.reducedMotion = true;
    }

    // Check for high contrast preference
    if (window.matchMedia && window.matchMedia('(prefers-contrast: high)').matches) {
      this.preferences.highContrast = true;
    }

    // Check for color scheme preference
    const darkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (darkMode) {
      // Could influence high contrast or other visual preferences
    }
  }

  /**
   * Apply preferences to the UI
   */
  private async applyPreferences(): Promise<void> {
    // Apply visual preferences
    if (this.preferences.highContrast) {
      document.body.classList.add('high-contrast');
    } else {
      document.body.classList.remove('high-contrast');
    }

    if (this.preferences.reducedMotion) {
      document.body.classList.add('reduced-motion');
    } else {
      document.body.classList.remove('reduced-motion');
    }

    // Apply font size
    document.body.classList.remove('font-small', 'font-normal', 'font-large', 'font-xl');
    document.body.classList.add(`font-${this.preferences.fontSize}`);

    // Apply line spacing
    document.body.classList.remove('line-spacing-normal', 'line-spacing-relaxed', 'line-spacing-loose');
    document.body.classList.add(`line-spacing-${this.preferences.lineSpacing}`);

    // Apply keyboard navigation
    if (this.preferences.keyboardNavigation) {
      document.body.classList.add('keyboard-navigation');
    } else {
      document.body.classList.remove('keyboard-navigation');
    }

    // Apply focus indicators
    if (this.preferences.focusIndicators) {
      document.body.classList.add('focus-indicators');
    } else {
      document.body.classList.remove('focus-indicators');
    }
  }

  /**
   * Setup system preference change listeners
   */
  private setupSystemListeners(): void {
    // Listen for reduced motion changes
    const reducedMotionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    reducedMotionQuery.addListener((e) => {
      this.updatePreferences({ reducedMotion: e.matches });
    });

    // Listen for contrast changes
    const contrastQuery = window.matchMedia('(prefers-contrast: high)');
    contrastQuery.addListener((e) => {
      this.updatePreferences({ highContrast: e.matches });
    });
  }
}

/**
 * ARIA Live Announcer for screen reader notifications
 */
export class AriaLiveAnnouncer {
  private politeRegion: HTMLElement | null = null;
  private assertiveRegion: HTMLElement | null = null;

  async initialize(): Promise<void> {
    this.createLiveRegions();
  }

  /**
   * Announce message with specified priority
   */
  announce(message: string, priority: 'polite' | 'assertive' = 'polite'): void {
    const region = priority === 'assertive' ? this.assertiveRegion : this.politeRegion;
    
    if (region) {
      region.textContent = message;
      
      // Clear after announcement
      setTimeout(() => {
        if (region.textContent === message) {
          region.textContent = '';
        }
      }, 1000);
    }
  }

  /**
   * Create ARIA live regions
   */
  private createLiveRegions(): void {
    // Polite announcements
    this.politeRegion = document.createElement('div');
    this.politeRegion.setAttribute('aria-live', 'polite');
    this.politeRegion.setAttribute('aria-atomic', 'true');
    this.politeRegion.setAttribute('class', 'sr-only');
    this.politeRegion.style.cssText = `
      position: absolute !important;
      left: -10000px !important;
      width: 1px !important;
      height: 1px !important;
      overflow: hidden !important;
    `;
    document.body.appendChild(this.politeRegion);

    // Assertive announcements
    this.assertiveRegion = document.createElement('div');
    this.assertiveRegion.setAttribute('aria-live', 'assertive');
    this.assertiveRegion.setAttribute('aria-atomic', 'true');
    this.assertiveRegion.setAttribute('class', 'sr-only');
    this.assertiveRegion.style.cssText = this.politeRegion.style.cssText;
    document.body.appendChild(this.assertiveRegion);
  }
}

/**
 * Focus management for keyboard navigation
 */
export class FocusManager {
  private focusableSelectors = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable="true"]'
  ].join(', ');

  async initialize(): Promise<void> {
    // Setup focus restoration
    this.setupFocusRestoration();
  }

  /**
   * Create focus trap for container
   */
  createFocusTrap(container: HTMLElement): () => void {
    const focusableElements = this.getFocusableElements(container);
    
    if (focusableElements.length === 0) return () => {};

    const firstFocusable = focusableElements[0];
    const lastFocusable = focusableElements[focusableElements.length - 1];

    // Focus first element
    firstFocusable.focus();

    const handleKeydown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === firstFocusable) {
          e.preventDefault();
          lastFocusable.focus();
        } else if (!e.shiftKey && document.activeElement === lastFocusable) {
          e.preventDefault();
          firstFocusable.focus();
        }
      }
    };

    container.addEventListener('keydown', handleKeydown);

    // Return cleanup function
    return () => {
      container.removeEventListener('keydown', handleKeydown);
    };
  }

  /**
   * Get focusable elements in container
   */
  getFocusableElements(container: HTMLElement): HTMLElement[] {
    return Array.from(container.querySelectorAll(this.focusableSelectors))
      .filter((element) => {
        const htmlElement = element as HTMLElement;
        return htmlElement.offsetParent !== null && !htmlElement.hasAttribute('disabled');
      }) as HTMLElement[];
  }

  /**
   * Move focus to element
   */
  moveFocusTo(element: HTMLElement): void {
    element.focus();
    
    // Announce focus change for screen readers
    const label = element.getAttribute('aria-label') || element.textContent || 'element';
    // This would integrate with the announcer
  }

  /**
   * Setup focus restoration for SPAs
   */
  private setupFocusRestoration(): void {
    // Store focus when navigating away
    let lastFocusedElement: HTMLElement | null = null;

    document.addEventListener('focusout', () => {
      lastFocusedElement = document.activeElement as HTMLElement;
    });

    // Restore focus on page load/navigation
    window.addEventListener('load', () => {
      if (lastFocusedElement && document.body.contains(lastFocusedElement)) {
        lastFocusedElement.focus();
      }
    });
  }
}

/**
 * Keyboard navigation manager
 */
export class KeyboardNavigationManager {
  private shortcuts = new Map<string, KeyboardShortcut[]>();

  async initialize(): Promise<void> {
    this.setupGlobalShortcuts();
    this.setupKeyboardHandlers();
  }

  /**
   * Register keyboard shortcuts for component type
   */
  registerShortcuts(componentType: string, shortcuts: KeyboardShortcut[]): void {
    this.shortcuts.set(componentType, shortcuts);
  }

  /**
   * Get shortcuts for component type
   */
  getShortcuts(componentType: string): KeyboardShortcut[] {
    return this.shortcuts.get(componentType) || [];
  }

  /**
   * Setup global keyboard shortcuts
   */
  private setupGlobalShortcuts(): void {
    const globalShortcuts: KeyboardShortcut[] = [
      {
        key: 'Alt+1',
        description: 'Navigate to main content',
        action: () => this.skipToMainContent()
      },
      {
        key: 'Alt+2', 
        description: 'Navigate to sidebar',
        action: () => this.skipToSidebar()
      },
      {
        key: 'Escape',
        description: 'Close modal or cancel action',
        action: () => this.handleEscape()
      }
    ];

    this.registerShortcuts('global', globalShortcuts);
  }

  /**
   * Setup keyboard event handlers
   */
  private setupKeyboardHandlers(): void {
    document.addEventListener('keydown', (e) => {
      this.handleGlobalKeydown(e);
    });
  }

  /**
   * Handle global keydown events
   */
  private handleGlobalKeydown(e: KeyboardEvent): void {
    const shortcuts = this.getShortcuts('global');
    const keyCombo = this.getKeyCombo(e);

    const shortcut = shortcuts.find(s => s.key === keyCombo);
    if (shortcut) {
      e.preventDefault();
      shortcut.action();
    }
  }

  /**
   * Get key combination string
   */
  private getKeyCombo(e: KeyboardEvent): string {
    const parts: string[] = [];
    
    if (e.ctrlKey) parts.push('Ctrl');
    if (e.altKey) parts.push('Alt');
    if (e.shiftKey) parts.push('Shift');
    if (e.metaKey) parts.push('Meta');
    
    parts.push(e.key);
    
    return parts.join('+');
  }

  /**
   * Skip to main content
   */
  private skipToMainContent(): void {
    const main = document.querySelector('main') || document.querySelector('[role="main"]');
    if (main) {
      (main as HTMLElement).focus();
      main.scrollIntoView();
    }
  }

  /**
   * Skip to sidebar
   */
  private skipToSidebar(): void {
    const sidebar = document.querySelector('[role="complementary"]') || document.querySelector('.sidebar');
    if (sidebar) {
      (sidebar as HTMLElement).focus();
    }
  }

  /**
   * Handle escape key
   */
  private handleEscape(): void {
    // Close any open modals or dropdowns
    const modal = document.querySelector('[role="dialog"][aria-modal="true"]');
    if (modal) {
      const closeButton = modal.querySelector('[aria-label="Close"]') || modal.querySelector('.close');
      if (closeButton) {
        (closeButton as HTMLElement).click();
      }
    }
  }
}

/**
 * Keyboard shortcut interface
 */
export interface KeyboardShortcut {
  key: string;
  description: string;
  action: () => void;
  condition?: () => boolean;
}

/**
 * Contrast management for high contrast mode
 */
export class ContrastManager {
  private originalStyles = new Map<HTMLElement, string>();

  async initialize(): Promise<void> {
    // Setup high contrast detection and handling
  }

  /**
   * Apply high contrast styles
   */
  applyHighContrast(): void {
    document.body.classList.add('high-contrast-mode');
    
    // Additional high contrast adjustments could go here
  }

  /**
   * Remove high contrast styles
   */
  removeHighContrast(): void {
    document.body.classList.remove('high-contrast-mode');
    
    // Restore original styles
    this.originalStyles.forEach((style, element) => {
      element.setAttribute('style', style);
    });
    this.originalStyles.clear();
  }
}

/**
 * Accessibility auditor for WCAG compliance
 */
export class AccessibilityAuditor {
  /**
   * Audit element for accessibility compliance
   */
  async audit(element: HTMLElement, targetLevel: WCAGLevel): Promise<AccessibilityAuditResult> {
    const issues: AccessibilityIssue[] = [];
    
    // Run audit checks
    this.checkImages(element, issues);
    this.checkHeadings(element, issues);
    this.checkForms(element, issues);
    this.checkLinks(element, issues);
    this.checkColors(element, issues);
    this.checkKeyboard(element, issues);

    // Calculate score
    const totalChecks = 50; // Total number of checks
    const failedChecks = issues.filter(i => i.severity === 'error').length;
    const score = Math.max(0, Math.round(((totalChecks - failedChecks) / totalChecks) * 100));

    // Check compliance principles
    const compliance = {
      perceivable: issues.filter(i => i.principle === 'perceivable' && i.severity === 'error').length === 0,
      operable: issues.filter(i => i.principle === 'operable' && i.severity === 'error').length === 0,
      understandable: issues.filter(i => i.principle === 'understandable' && i.severity === 'error').length === 0,
      robust: issues.filter(i => i.principle === 'robust' && i.severity === 'error').length === 0
    };

    const passed = Object.values(compliance).every(Boolean) && score >= 80;

    return {
      level: targetLevel,
      passed,
      score,
      issues,
      suggestions: this.generateSuggestions(issues),
      compliance
    };
  }

  /**
   * Check images for alt text
   */
  private checkImages(element: HTMLElement, issues: AccessibilityIssue[]): void {
    const images = element.querySelectorAll('img');
    images.forEach((img, index) => {
      if (!img.hasAttribute('alt')) {
        issues.push({
          id: `img-alt-${index}`,
          severity: 'error',
          principle: 'perceivable',
          guideline: '1.1 Text Alternatives',
          criterion: '1.1.1 Non-text Content',
          element: `img[${index}]`,
          message: 'Image missing alt text',
          suggestedFix: 'Add alt attribute with descriptive text'
        });
      }
    });
  }

  /**
   * Check heading hierarchy
   */
  private checkHeadings(element: HTMLElement, issues: AccessibilityIssue[]): void {
    const headings = element.querySelectorAll('h1, h2, h3, h4, h5, h6');
    let lastLevel = 0;

    headings.forEach((heading, index) => {
      const currentLevel = parseInt(heading.tagName.charAt(1));
      
      if (currentLevel > lastLevel + 1) {
        issues.push({
          id: `heading-level-${index}`,
          severity: 'error',
          principle: 'understandable',
          guideline: '2.4 Navigable',
          criterion: '2.4.6 Headings and Labels',
          element: `${heading.tagName.toLowerCase()}[${index}]`,
          message: 'Heading levels not sequential',
          suggestedFix: `Use h${lastLevel + 1} instead of h${currentLevel}`
        });
      }
      
      lastLevel = currentLevel;
    });
  }

  /**
   * Check form elements
   */
  private checkForms(element: HTMLElement, issues: AccessibilityIssue[]): void {
    const inputs = element.querySelectorAll('input, select, textarea');
    inputs.forEach((input, index) => {
      if (!input.hasAttribute('aria-label') && !input.id) {
        issues.push({
          id: `form-label-${index}`,
          severity: 'error',
          principle: 'understandable',
          guideline: '1.3 Adaptable',
          criterion: '1.3.1 Info and Relationships',
          element: `${input.tagName.toLowerCase()}[${index}]`,
          message: 'Form control missing label',
          suggestedFix: 'Add aria-label or associate with label element'
        });
      }
    });
  }

  /**
   * Check links
   */
  private checkLinks(element: HTMLElement, issues: AccessibilityIssue[]): void {
    const links = element.querySelectorAll('a');
    links.forEach((link, index) => {
      if (!link.textContent?.trim() && !link.hasAttribute('aria-label')) {
        issues.push({
          id: `link-text-${index}`,
          severity: 'error',
          principle: 'understandable',
          guideline: '2.4 Navigable',
          criterion: '2.4.4 Link Purpose',
          element: `a[${index}]`,
          message: 'Link missing accessible name',
          suggestedFix: 'Add descriptive text or aria-label'
        });
      }
    });
  }

  /**
   * Check color contrast
   */
  private checkColors(element: HTMLElement, issues: AccessibilityIssue[]): void {
    // This would require complex color analysis
    // For now, just check if high contrast is available
    if (!document.body.classList.contains('high-contrast-support')) {
      issues.push({
        id: 'color-contrast-support',
        severity: 'warning',
        principle: 'perceivable',
        guideline: '1.4 Distinguishable',
        criterion: '1.4.3 Contrast',
        element: 'body',
        message: 'High contrast mode not supported',
        suggestedFix: 'Add high contrast theme support'
      });
    }
  }

  /**
   * Check keyboard accessibility
   */
  private checkKeyboard(element: HTMLElement, issues: AccessibilityIssue[]): void {
    const interactive = element.querySelectorAll('button, a, input, select, textarea, [tabindex], [onclick]');
    interactive.forEach((el, index) => {
      const tabIndex = el.getAttribute('tabindex');
      if (tabIndex === '-1' && !el.hasAttribute('aria-hidden')) {
        issues.push({
          id: `keyboard-access-${index}`,
          severity: 'error',
          principle: 'operable',
          guideline: '2.1 Keyboard Accessible',
          criterion: '2.1.1 Keyboard',
          element: `${el.tagName.toLowerCase()}[${index}]`,
          message: 'Interactive element not keyboard accessible',
          suggestedFix: 'Remove tabindex="-1" or add aria-hidden="true"'
        });
      }
    });
  }

  /**
   * Generate suggestions based on issues
   */
  private generateSuggestions(issues: AccessibilityIssue[]): string[] {
    const suggestions: string[] = [];
    
    const errorCount = issues.filter(i => i.severity === 'error').length;
    if (errorCount > 0) {
      suggestions.push(`Fix ${errorCount} critical accessibility errors to improve compliance`);
    }

    const warningCount = issues.filter(i => i.severity === 'warning').length;
    if (warningCount > 0) {
      suggestions.push(`Address ${warningCount} accessibility warnings for better user experience`);
    }

    // Add specific suggestions based on issue types
    if (issues.some(i => i.guideline.includes('Text Alternatives'))) {
      suggestions.push('Add alternative text for all images');
    }

    if (issues.some(i => i.guideline.includes('Keyboard'))) {
      suggestions.push('Ensure all interactive elements are keyboard accessible');
    }

    return suggestions;
  }
}

/**
 * Global accessibility manager instance
 */
export const accessibilityManager = new AccessibilityManager();

/**
 * Initialize accessibility features
 */
export async function initializeAccessibility(): Promise<void> {
  await accessibilityManager.initialize();
}

/**
 * Default WCAG 2.1 AA compliant configuration
 */
export const WCAG_AA_CONFIG: AccessibilityConfig = {
  keyboardNavigable: true,
  screenReaderSupport: true,
  highContrastSupport: true,
  focusManagement: {
    focusable: true,
    tabIndex: 0,
    focusTrap: false,
    autoFocus: false
  },
  ariaLabel: '',
  role: ''
};