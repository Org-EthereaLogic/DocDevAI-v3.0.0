/**
 * M011 Configuration System - UI component configuration management
 * 
 * Provides centralized configuration for UI components with privacy-first
 * defaults and integration with the M001 Configuration Manager.
 */

import { UITheme, ColorPalette, TypographyConfig, SpacingConfig, BreakpointConfig } from './interfaces';
import { AccessibilityPreferences } from './accessibility';

/**
 * UI component configuration interface
 */
export interface UIComponentConfig {
  // Theme and visual settings
  theme: UIThemeConfig;
  
  // Accessibility settings
  accessibility: AccessibilityPreferences;
  
  // Performance settings
  performance: UIPerformanceConfig;
  
  // Feature flags
  features: UIFeatureFlags;
  
  // Integration settings
  integration: UIIntegrationConfig;
  
  // Development settings
  development: UIDevelopmentConfig;
}

/**
 * UI theme configuration
 */
export interface UIThemeConfig {
  defaultTheme: 'light' | 'dark' | 'high-contrast';
  allowThemeSwitch: boolean;
  respectSystemTheme: boolean;
  customThemes: UITheme[];
}

/**
 * UI performance configuration
 */
export interface UIPerformanceConfig {
  // Rendering performance
  enableVirtualization: boolean;
  lazyLoadThreshold: number;
  debounceDelay: number;
  
  // Caching
  enableComponentCache: boolean;
  cacheSize: number;
  cacheTTL: number;
  
  // Animation performance
  enableAnimations: boolean;
  reducedMotion: boolean;
  animationDuration: number;
  
  // Memory management
  maxComponents: number;
  cleanupInterval: number;
}

/**
 * UI feature flags
 */
export interface UIFeatureFlags {
  // Core features
  enableDashboard: boolean;
  enableVSCodeExtension: boolean;
  enableMobileView: boolean;
  
  // Advanced features
  enableRealTimeUpdates: boolean;
  enableOfflineMode: boolean;
  enableExperimentalFeatures: boolean;
  
  // Visualization features
  enableAdvancedCharts: boolean;
  enable3DVisualizations: boolean;
  enableInteractiveGraphs: boolean;
  
  // Accessibility features
  enableKeyboardShortcuts: boolean;
  enableScreenReaderMode: boolean;
  enableHighContrastMode: boolean;
  
  // Developer features
  enableDebugMode: boolean;
  enablePerformanceMonitoring: boolean;
  enableA11yAuditing: boolean;
}

/**
 * UI integration configuration
 */
export interface UIIntegrationConfig {
  // Python backend integration
  backendEndpoint: string;
  enableBackendCache: boolean;
  requestTimeout: number;
  retryAttempts: number;
  
  // VS Code integration
  vscodeApiVersion: string;
  enableWebviewPersistence: boolean;
  enableCommandPalette: boolean;
  
  // External integrations
  enableAnalytics: boolean;
  enableErrorReporting: boolean;
  enableUsageTelemetry: boolean;
}

/**
 * UI development configuration
 */
export interface UIDevelopmentConfig {
  // Debug settings
  enableConsoleLogging: boolean;
  logLevel: 'debug' | 'info' | 'warn' | 'error';
  enableReduxDevTools: boolean;
  
  // Testing settings
  enableTestIds: boolean;
  enableAccessibilityAuditing: boolean;
  enablePerformanceProfiling: boolean;
  
  // Hot reload settings
  enableHotReload: boolean;
  hotReloadPort: number;
}

/**
 * Default light theme
 */
export const DEFAULT_LIGHT_THEME: UITheme = {
  name: 'DevDocAI Light',
  colors: {
    primary: '#2563eb',
    secondary: '#64748b',
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    background: '#ffffff',
    surface: '#f8fafc',
    text: {
      primary: '#1e293b',
      secondary: '#64748b',
      disabled: '#94a3b8'
    }
  },
  typography: {
    fontFamily: {
      primary: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
      monospace: '"SF Mono", "Monaco", "Inconsolata", "Roboto Mono", "Source Code Pro", monospace',
      dyslexicFriendly: '"OpenDyslexic", sans-serif'
    },
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem',
      '3xl': '1.875rem'
    },
    fontWeight: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    },
    lineHeight: {
      tight: 1.25,
      normal: 1.5,
      relaxed: 1.75
    }
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem',
    '3xl': '4rem'
  },
  breakpoints: {
    mobile: '320px',
    tablet: '768px',
    desktop: '1024px',
    wide: '1440px'
  },
  accessibility: {
    focusIndicator: '#3b82f6',
    contrastRatio: 4.5,
    reducedMotion: false
  }
};

/**
 * Default dark theme
 */
export const DEFAULT_DARK_THEME: UITheme = {
  ...DEFAULT_LIGHT_THEME,
  name: 'DevDocAI Dark',
  colors: {
    primary: '#3b82f6',
    secondary: '#64748b',
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#3b82f6',
    background: '#0f172a',
    surface: '#1e293b',
    text: {
      primary: '#f1f5f9',
      secondary: '#94a3b8',
      disabled: '#64748b'
    }
  }
};

/**
 * High contrast theme
 */
export const HIGH_CONTRAST_THEME: UITheme = {
  ...DEFAULT_LIGHT_THEME,
  name: 'DevDocAI High Contrast',
  colors: {
    primary: '#0000ff',
    secondary: '#000000',
    success: '#008000',
    warning: '#ff8c00',
    error: '#ff0000',
    info: '#0000ff',
    background: '#ffffff',
    surface: '#ffffff',
    text: {
      primary: '#000000',
      secondary: '#000000',
      disabled: '#808080'
    }
  },
  accessibility: {
    focusIndicator: '#ff0000',
    contrastRatio: 7,
    reducedMotion: true,
    highContrast: {
      primary: '#ffffff',
      secondary: '#000000',
      success: '#ffffff',
      warning: '#000000',
      error: '#ffffff',
      info: '#ffffff',
      background: '#000000',
      surface: '#000000',
      text: {
        primary: '#ffffff',
        secondary: '#ffffff',
        disabled: '#cccccc'
      }
    }
  }
};

/**
 * Default UI component configuration
 */
export const DEFAULT_UI_CONFIG: UIComponentConfig = {
  theme: {
    defaultTheme: 'light',
    allowThemeSwitch: true,
    respectSystemTheme: true,
    customThemes: [DEFAULT_LIGHT_THEME, DEFAULT_DARK_THEME, HIGH_CONTRAST_THEME]
  },
  
  accessibility: {
    // Visual preferences
    highContrast: false,
    reducedMotion: false,
    fontSize: 'normal',
    lineSpacing: 'normal',
    
    // Navigation preferences  
    keyboardNavigation: true,
    skipLinks: true,
    focusIndicators: true,
    
    // Screen reader preferences
    screenReaderMode: false,
    verboseDescriptions: false,
    announceChanges: true,
    readContent: false,
    
    // Motor preferences
    stickyKeys: false,
    slowKeys: false,
    mouseKeys: false,
    
    // Cognitive preferences
    autoPlay: false,
    complexAnimations: true,
    distractionFree: false
  },
  
  performance: {
    // Rendering performance
    enableVirtualization: true,
    lazyLoadThreshold: 100,
    debounceDelay: 300,
    
    // Caching
    enableComponentCache: true,
    cacheSize: 100,
    cacheTTL: 300000, // 5 minutes
    
    // Animation performance
    enableAnimations: true,
    reducedMotion: false,
    animationDuration: 200,
    
    // Memory management
    maxComponents: 1000,
    cleanupInterval: 60000 // 1 minute
  },
  
  features: {
    // Core features
    enableDashboard: true,
    enableVSCodeExtension: true,
    enableMobileView: true,
    
    // Advanced features
    enableRealTimeUpdates: true,
    enableOfflineMode: true,
    enableExperimentalFeatures: false,
    
    // Visualization features
    enableAdvancedCharts: true,
    enable3DVisualizations: false,
    enableInteractiveGraphs: true,
    
    // Accessibility features
    enableKeyboardShortcuts: true,
    enableScreenReaderMode: true,
    enableHighContrastMode: true,
    
    // Developer features
    enableDebugMode: process.env.NODE_ENV === 'development',
    enablePerformanceMonitoring: true,
    enableA11yAuditing: process.env.NODE_ENV === 'development'
  },
  
  integration: {
    // Python backend integration
    backendEndpoint: 'http://localhost:8000',
    enableBackendCache: true,
    requestTimeout: 5000,
    retryAttempts: 3,
    
    // VS Code integration
    vscodeApiVersion: '1.74.0',
    enableWebviewPersistence: true,
    enableCommandPalette: true,
    
    // External integrations (privacy-first defaults)
    enableAnalytics: false,
    enableErrorReporting: false,
    enableUsageTelemetry: false
  },
  
  development: {
    // Debug settings
    enableConsoleLogging: process.env.NODE_ENV === 'development',
    logLevel: process.env.NODE_ENV === 'development' ? 'debug' : 'warn',
    enableReduxDevTools: process.env.NODE_ENV === 'development',
    
    // Testing settings
    enableTestIds: process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test',
    enableAccessibilityAuditing: true,
    enablePerformanceProfiling: process.env.NODE_ENV === 'development',
    
    // Hot reload settings
    enableHotReload: process.env.NODE_ENV === 'development',
    hotReloadPort: 3000
  }
};

/**
 * UI Configuration Manager
 */
export class UIConfigManager {
  private config: UIComponentConfig;
  private callbacks = new Set<(config: UIComponentConfig) => void>();
  private initialized = false;

  constructor(initialConfig?: Partial<UIComponentConfig>) {
    this.config = { ...DEFAULT_UI_CONFIG, ...initialConfig };
  }

  /**
   * Initialize configuration manager
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    // Load configuration from storage
    await this.loadConfiguration();
    
    // Apply initial configuration
    this.applyConfiguration();
    
    this.initialized = true;
  }

  /**
   * Get current configuration
   */
  getConfig(): UIComponentConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  async updateConfig(updates: Partial<UIComponentConfig>): Promise<void> {
    this.config = this.mergeConfig(this.config, updates);
    
    // Apply configuration changes
    this.applyConfiguration();
    
    // Save to storage
    await this.saveConfiguration();
    
    // Notify subscribers
    this.notifyCallbacks();
  }

  /**
   * Get theme by name
   */
  getTheme(name: string): UITheme | undefined {
    return this.config.theme.customThemes.find(theme => theme.name === name);
  }

  /**
   * Add custom theme
   */
  async addTheme(theme: UITheme): Promise<void> {
    const themes = [...this.config.theme.customThemes];
    const existingIndex = themes.findIndex(t => t.name === theme.name);
    
    if (existingIndex >= 0) {
      themes[existingIndex] = theme;
    } else {
      themes.push(theme);
    }

    await this.updateConfig({
      theme: {
        ...this.config.theme,
        customThemes: themes
      }
    });
  }

  /**
   * Subscribe to configuration changes
   */
  subscribe(callback: (config: UIComponentConfig) => void): () => void {
    this.callbacks.add(callback);
    
    // Return unsubscribe function
    return () => {
      this.callbacks.delete(callback);
    };
  }

  /**
   * Load configuration from storage
   */
  private async loadConfiguration(): Promise<void> {
    try {
      const stored = localStorage.getItem('devdocai-ui-config');
      if (stored) {
        const parsed = JSON.parse(stored);
        this.config = this.mergeConfig(this.config, parsed);
      }
    } catch (error) {
      console.warn('Failed to load UI configuration:', error);
    }
  }

  /**
   * Save configuration to storage
   */
  private async saveConfiguration(): Promise<void> {
    try {
      // Only save user preferences, not system defaults
      const configToSave = {
        theme: this.config.theme,
        accessibility: this.config.accessibility,
        performance: {
          enableAnimations: this.config.performance.enableAnimations,
          reducedMotion: this.config.performance.reducedMotion
        }
      };
      
      localStorage.setItem('devdocai-ui-config', JSON.stringify(configToSave));
    } catch (error) {
      console.warn('Failed to save UI configuration:', error);
    }
  }

  /**
   * Apply configuration to the UI
   */
  private applyConfiguration(): void {
    // Apply theme
    this.applyTheme();
    
    // Apply accessibility settings
    this.applyAccessibilitySettings();
    
    // Apply performance settings
    this.applyPerformanceSettings();
    
    // Apply feature flags
    this.applyFeatureFlags();
  }

  /**
   * Apply theme settings
   */
  private applyTheme(): void {
    const theme = this.getTheme(this.config.theme.defaultTheme) || DEFAULT_LIGHT_THEME;
    
    // Set CSS custom properties
    const root = document.documentElement;
    
    // Colors
    root.style.setProperty('--color-primary', theme.colors.primary);
    root.style.setProperty('--color-secondary', theme.colors.secondary);
    root.style.setProperty('--color-success', theme.colors.success);
    root.style.setProperty('--color-warning', theme.colors.warning);
    root.style.setProperty('--color-error', theme.colors.error);
    root.style.setProperty('--color-info', theme.colors.info);
    root.style.setProperty('--color-background', theme.colors.background);
    root.style.setProperty('--color-surface', theme.colors.surface);
    root.style.setProperty('--color-text-primary', theme.colors.text.primary);
    root.style.setProperty('--color-text-secondary', theme.colors.text.secondary);
    root.style.setProperty('--color-text-disabled', theme.colors.text.disabled);
    
    // Typography
    root.style.setProperty('--font-family-primary', theme.typography.fontFamily.primary);
    root.style.setProperty('--font-family-monospace', theme.typography.fontFamily.monospace);
    
    // Focus indicator
    root.style.setProperty('--focus-indicator', theme.accessibility.focusIndicator);
    
    // Add theme class to body
    document.body.className = document.body.className.replace(/theme-\w+/, '');
    document.body.classList.add(`theme-${this.config.theme.defaultTheme}`);
  }

  /**
   * Apply accessibility settings
   */
  private applyAccessibilitySettings(): void {
    const { accessibility } = this.config;
    
    // High contrast
    document.body.classList.toggle('high-contrast', accessibility.highContrast);
    
    // Reduced motion
    document.body.classList.toggle('reduced-motion', accessibility.reducedMotion);
    
    // Font size
    document.body.classList.remove('font-small', 'font-normal', 'font-large', 'font-xl');
    document.body.classList.add(`font-${accessibility.fontSize}`);
    
    // Keyboard navigation
    document.body.classList.toggle('keyboard-navigation', accessibility.keyboardNavigation);
  }

  /**
   * Apply performance settings
   */
  private applyPerformanceSettings(): void {
    const { performance } = this.config;
    
    // Animations
    document.body.classList.toggle('no-animations', !performance.enableAnimations);
    
    // Set animation duration
    document.documentElement.style.setProperty(
      '--animation-duration', 
      `${performance.animationDuration}ms`
    );
  }

  /**
   * Apply feature flags
   */
  private applyFeatureFlags(): void {
    const { features } = this.config;
    
    // Add feature classes to body
    Object.entries(features).forEach(([key, enabled]) => {
      const className = `feature-${key.replace(/([A-Z])/g, '-$1').toLowerCase()}`;
      document.body.classList.toggle(className, enabled);
    });
  }

  /**
   * Deep merge configuration objects
   */
  private mergeConfig(base: UIComponentConfig, updates: Partial<UIComponentConfig>): UIComponentConfig {
    const merged = { ...base };
    
    Object.entries(updates).forEach(([key, value]) => {
      if (value && typeof value === 'object' && !Array.isArray(value)) {
        merged[key as keyof UIComponentConfig] = {
          ...base[key as keyof UIComponentConfig],
          ...value
        } as any;
      } else {
        merged[key as keyof UIComponentConfig] = value as any;
      }
    });
    
    return merged;
  }

  /**
   * Notify configuration change callbacks
   */
  private notifyCallbacks(): void {
    this.callbacks.forEach(callback => {
      try {
        callback(this.config);
      } catch (error) {
        console.error('Error in configuration change callback:', error);
      }
    });
  }
}

/**
 * Global UI configuration manager instance
 */
export const uiConfigManager = new UIConfigManager();

/**
 * Initialize UI configuration
 */
export async function initializeUIConfig(initialConfig?: Partial<UIComponentConfig>): Promise<void> {
  if (initialConfig) {
    await uiConfigManager.updateConfig(initialConfig);
  }
  
  await uiConfigManager.initialize();
}