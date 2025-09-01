/**
 * M011 Unified Configuration System
 * 
 * Central configuration for all UI component operation modes.
 * Supports runtime switching between BASIC, PERFORMANCE, SECURE, DELIGHTFUL, and ENTERPRISE modes.
 * 
 * This configuration drives behavior across all unified components, eliminating duplication
 * while preserving all functionality from previous passes.
 */

/**
 * Operation modes for UI components
 */
export enum OperationMode {
  BASIC = 'BASIC',                 // Minimal features, fastest load
  PERFORMANCE = 'PERFORMANCE',     // Optimized rendering, caching, virtual scrolling
  SECURE = 'SECURE',              // Encryption, sanitization, audit logging
  DELIGHTFUL = 'DELIGHTFUL',      // Animations, celebrations, enhanced UX
  ENTERPRISE = 'ENTERPRISE'        // All features enabled
}

/**
 * Feature flags for granular control
 */
export interface FeatureFlags {
  // Performance features
  virtualScrolling: boolean;
  lazyLoading: boolean;
  memoization: boolean;
  debouncing: boolean;
  throttling: boolean;
  caching: boolean;
  batchUpdates: boolean;
  webWorkers: boolean;
  
  // Security features
  encryption: boolean;
  sanitization: boolean;
  auditLogging: boolean;
  sessionManagement: boolean;
  rbac: boolean;
  piiDetection: boolean;
  csrfProtection: boolean;
  
  // Delight features
  animations: boolean;
  celebrations: boolean;
  soundEffects: boolean;
  hapticFeedback: boolean;
  microInteractions: boolean;
  advancedThemes: boolean;
  emotionalDesign: boolean;
  
  // Core features
  errorBoundaries: boolean;
  accessibility: boolean;
  responsiveDesign: boolean;
  darkMode: boolean;
  internationalization: boolean;
  offlineSupport: boolean;
}

/**
 * Performance configuration
 */
export interface PerformanceConfig {
  virtualListThreshold: number;    // Items before virtual scrolling
  debounceDelay: number;           // ms delay for debouncing
  throttleDelay: number;           // ms delay for throttling
  cacheSize: number;               // Max cache entries
  cacheTTL: number;                // Cache time-to-live in ms
  batchSize: number;               // Batch update size
  workerPoolSize: number;          // Web worker pool size
  renderBudget: number;            // ms budget per frame
}

/**
 * Security configuration
 */
export interface SecurityConfig {
  encryptionAlgorithm: string;     // AES-256-GCM
  encryptionKeySize: number;       // 256 bits
  saltLength: number;              // 32 bytes
  iterations: number;              // PBKDF2 iterations
  sessionTimeout: number;          // ms before session expires
  maxLoginAttempts: number;        // Before lockout
  auditRetentionDays: number;     // Audit log retention
  csrfTokenLength: number;         // CSRF token bytes
}

/**
 * Delight configuration
 */
export interface DelightConfig {
  animationDuration: number;       // Default animation ms
  celebrationDuration: number;     // Celebration effect ms
  soundVolume: number;             // 0-1 volume level
  hapticIntensity: number;         // 0-1 haptic strength
  particleCount: number;           // Celebration particles
  confettiColors: string[];        // Celebration colors
  microInteractionDelay: number;   // Hover effect delay
  emotionalTriggers: string[];     // Success trigger words
}

/**
 * Complete unified configuration
 */
export interface UnifiedConfig {
  mode: OperationMode;
  features: FeatureFlags;
  performance: PerformanceConfig;
  security: SecurityConfig;
  delight: DelightConfig;
}

/**
 * Default configurations for each mode
 */
export const MODE_CONFIGS: Record<OperationMode, UnifiedConfig> = {
  [OperationMode.BASIC]: {
    mode: OperationMode.BASIC,
    features: {
      // Only essential features
      virtualScrolling: false,
      lazyLoading: false,
      memoization: false,
      debouncing: false,
      throttling: false,
      caching: false,
      batchUpdates: false,
      webWorkers: false,
      encryption: false,
      sanitization: true,  // Basic XSS protection
      auditLogging: false,
      sessionManagement: false,
      rbac: false,
      piiDetection: false,
      csrfProtection: false,
      animations: false,
      celebrations: false,
      soundEffects: false,
      hapticFeedback: false,
      microInteractions: false,
      advancedThemes: false,
      emotionalDesign: false,
      errorBoundaries: true,
      accessibility: true,
      responsiveDesign: true,
      darkMode: false,
      internationalization: false,
      offlineSupport: false
    },
    performance: {
      virtualListThreshold: 1000,
      debounceDelay: 0,
      throttleDelay: 0,
      cacheSize: 0,
      cacheTTL: 0,
      batchSize: 1,
      workerPoolSize: 0,
      renderBudget: 16
    },
    security: {
      encryptionAlgorithm: 'none',
      encryptionKeySize: 0,
      saltLength: 0,
      iterations: 0,
      sessionTimeout: 3600000,
      maxLoginAttempts: 5,
      auditRetentionDays: 0,
      csrfTokenLength: 0
    },
    delight: {
      animationDuration: 0,
      celebrationDuration: 0,
      soundVolume: 0,
      hapticIntensity: 0,
      particleCount: 0,
      confettiColors: [],
      microInteractionDelay: 0,
      emotionalTriggers: []
    }
  },
  
  [OperationMode.PERFORMANCE]: {
    mode: OperationMode.PERFORMANCE,
    features: {
      // Performance features enabled
      virtualScrolling: true,
      lazyLoading: true,
      memoization: true,
      debouncing: true,
      throttling: true,
      caching: true,
      batchUpdates: true,
      webWorkers: true,
      encryption: false,
      sanitization: true,
      auditLogging: false,
      sessionManagement: false,
      rbac: false,
      piiDetection: false,
      csrfProtection: false,
      animations: false,
      celebrations: false,
      soundEffects: false,
      hapticFeedback: false,
      microInteractions: false,
      advancedThemes: false,
      emotionalDesign: false,
      errorBoundaries: true,
      accessibility: true,
      responsiveDesign: true,
      darkMode: true,
      internationalization: false,
      offlineSupport: true
    },
    performance: {
      virtualListThreshold: 50,
      debounceDelay: 300,
      throttleDelay: 100,
      cacheSize: 100,
      cacheTTL: 300000,  // 5 minutes
      batchSize: 50,
      workerPoolSize: 4,
      renderBudget: 16
    },
    security: {
      encryptionAlgorithm: 'none',
      encryptionKeySize: 0,
      saltLength: 0,
      iterations: 0,
      sessionTimeout: 3600000,
      maxLoginAttempts: 5,
      auditRetentionDays: 0,
      csrfTokenLength: 0
    },
    delight: {
      animationDuration: 0,
      celebrationDuration: 0,
      soundVolume: 0,
      hapticIntensity: 0,
      particleCount: 0,
      confettiColors: [],
      microInteractionDelay: 0,
      emotionalTriggers: []
    }
  },
  
  [OperationMode.SECURE]: {
    mode: OperationMode.SECURE,
    features: {
      // Security features enabled
      virtualScrolling: false,
      lazyLoading: false,
      memoization: true,
      debouncing: true,
      throttling: true,
      caching: true,  // Encrypted cache
      batchUpdates: false,
      webWorkers: false,
      encryption: true,
      sanitization: true,
      auditLogging: true,
      sessionManagement: true,
      rbac: true,
      piiDetection: true,
      csrfProtection: true,
      animations: false,
      celebrations: false,
      soundEffects: false,
      hapticFeedback: false,
      microInteractions: false,
      advancedThemes: false,
      emotionalDesign: false,
      errorBoundaries: true,
      accessibility: true,
      responsiveDesign: true,
      darkMode: true,
      internationalization: false,
      offlineSupport: false  // Disabled for security
    },
    performance: {
      virtualListThreshold: 1000,
      debounceDelay: 500,  // Slower for security
      throttleDelay: 200,
      cacheSize: 50,       // Smaller encrypted cache
      cacheTTL: 60000,     // 1 minute
      batchSize: 1,
      workerPoolSize: 0,
      renderBudget: 16
    },
    security: {
      encryptionAlgorithm: 'AES-256-GCM',
      encryptionKeySize: 256,
      saltLength: 32,
      iterations: 100000,
      sessionTimeout: 900000,  // 15 minutes
      maxLoginAttempts: 3,
      auditRetentionDays: 90,
      csrfTokenLength: 32
    },
    delight: {
      animationDuration: 0,
      celebrationDuration: 0,
      soundVolume: 0,
      hapticIntensity: 0,
      particleCount: 0,
      confettiColors: [],
      microInteractionDelay: 0,
      emotionalTriggers: []
    }
  },
  
  [OperationMode.DELIGHTFUL]: {
    mode: OperationMode.DELIGHTFUL,
    features: {
      // Delight features enabled
      virtualScrolling: false,
      lazyLoading: true,
      memoization: true,
      debouncing: true,
      throttling: true,
      caching: true,
      batchUpdates: true,
      webWorkers: false,
      encryption: false,
      sanitization: true,
      auditLogging: false,
      sessionManagement: false,
      rbac: false,
      piiDetection: false,
      csrfProtection: false,
      animations: true,
      celebrations: true,
      soundEffects: true,
      hapticFeedback: true,
      microInteractions: true,
      advancedThemes: true,
      emotionalDesign: true,
      errorBoundaries: true,
      accessibility: true,
      responsiveDesign: true,
      darkMode: true,
      internationalization: true,
      offlineSupport: true
    },
    performance: {
      virtualListThreshold: 100,
      debounceDelay: 200,
      throttleDelay: 50,
      cacheSize: 100,
      cacheTTL: 300000,
      batchSize: 25,
      workerPoolSize: 0,
      renderBudget: 16
    },
    security: {
      encryptionAlgorithm: 'none',
      encryptionKeySize: 0,
      saltLength: 0,
      iterations: 0,
      sessionTimeout: 3600000,
      maxLoginAttempts: 5,
      auditRetentionDays: 0,
      csrfTokenLength: 0
    },
    delight: {
      animationDuration: 300,
      celebrationDuration: 2000,
      soundVolume: 0.5,
      hapticIntensity: 0.7,
      particleCount: 100,
      confettiColors: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FED766', '#2AB7CA'],
      microInteractionDelay: 100,
      emotionalTriggers: ['success', 'complete', 'awesome', 'great', 'perfect']
    }
  },
  
  [OperationMode.ENTERPRISE]: {
    mode: OperationMode.ENTERPRISE,
    features: {
      // All features enabled
      virtualScrolling: true,
      lazyLoading: true,
      memoization: true,
      debouncing: true,
      throttling: true,
      caching: true,
      batchUpdates: true,
      webWorkers: true,
      encryption: true,
      sanitization: true,
      auditLogging: true,
      sessionManagement: true,
      rbac: true,
      piiDetection: true,
      csrfProtection: true,
      animations: true,
      celebrations: true,
      soundEffects: true,
      hapticFeedback: true,
      microInteractions: true,
      advancedThemes: true,
      emotionalDesign: true,
      errorBoundaries: true,
      accessibility: true,
      responsiveDesign: true,
      darkMode: true,
      internationalization: true,
      offlineSupport: true
    },
    performance: {
      virtualListThreshold: 50,
      debounceDelay: 250,
      throttleDelay: 100,
      cacheSize: 200,
      cacheTTL: 600000,  // 10 minutes
      batchSize: 50,
      workerPoolSize: 8,
      renderBudget: 16
    },
    security: {
      encryptionAlgorithm: 'AES-256-GCM',
      encryptionKeySize: 256,
      saltLength: 32,
      iterations: 100000,
      sessionTimeout: 1800000,  // 30 minutes
      maxLoginAttempts: 3,
      auditRetentionDays: 365,
      csrfTokenLength: 32
    },
    delight: {
      animationDuration: 300,
      celebrationDuration: 2000,
      soundVolume: 0.3,
      hapticIntensity: 0.5,
      particleCount: 75,
      confettiColors: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FED766', '#2AB7CA'],
      microInteractionDelay: 100,
      emotionalTriggers: ['success', 'complete', 'awesome', 'great', 'perfect']
    }
  }
};

/**
 * Configuration manager singleton
 */
export class ConfigurationManager {
  private static instance: ConfigurationManager;
  private currentConfig: UnifiedConfig;
  private subscribers = new Set<(config: UnifiedConfig) => void>();
  
  private constructor() {
    // Start with BASIC mode by default
    this.currentConfig = MODE_CONFIGS[OperationMode.BASIC];
    
    // Load saved mode from localStorage if available
    if (typeof window !== 'undefined' && window.localStorage) {
      const savedMode = localStorage.getItem('ui-operation-mode') as OperationMode;
      if (savedMode && MODE_CONFIGS[savedMode]) {
        this.currentConfig = MODE_CONFIGS[savedMode];
      }
    }
  }
  
  /**
   * Get singleton instance
   */
  static getInstance(): ConfigurationManager {
    if (!ConfigurationManager.instance) {
      ConfigurationManager.instance = new ConfigurationManager();
    }
    return ConfigurationManager.instance;
  }
  
  /**
   * Get current configuration
   */
  getConfig(): UnifiedConfig {
    return this.currentConfig;
  }
  
  /**
   * Set operation mode
   */
  setMode(mode: OperationMode): void {
    if (MODE_CONFIGS[mode]) {
      this.currentConfig = MODE_CONFIGS[mode];
      this.notifySubscribers();
      
      // Persist to localStorage
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem('ui-operation-mode', mode);
      }
    }
  }
  
  /**
   * Update specific feature flags
   */
  updateFeatures(features: Partial<FeatureFlags>): void {
    this.currentConfig.features = {
      ...this.currentConfig.features,
      ...features
    };
    this.notifySubscribers();
  }
  
  /**
   * Check if a feature is enabled
   */
  isFeatureEnabled(feature: keyof FeatureFlags): boolean {
    return this.currentConfig.features[feature];
  }
  
  /**
   * Subscribe to configuration changes
   */
  subscribe(callback: (config: UnifiedConfig) => void): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }
  
  /**
   * Notify all subscribers of configuration changes
   */
  private notifySubscribers(): void {
    this.subscribers.forEach(callback => callback(this.currentConfig));
  }
  
  /**
   * Get performance metrics for current mode
   */
  getPerformanceMetrics(): PerformanceConfig {
    return this.currentConfig.performance;
  }
  
  /**
   * Get security settings for current mode
   */
  getSecuritySettings(): SecurityConfig {
    return this.currentConfig.security;
  }
  
  /**
   * Get delight settings for current mode
   */
  getDelightSettings(): DelightConfig {
    return this.currentConfig.delight;
  }
}

// Export singleton instance
export const configManager = ConfigurationManager.getInstance();