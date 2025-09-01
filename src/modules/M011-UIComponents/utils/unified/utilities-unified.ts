/**
 * M011 Unified Utilities
 * 
 * Consolidates utility functions from:
 * - performance-monitor.ts (Performance tracking)
 * - delight-animations.ts (Animation utilities)
 * - delight-themes.ts (Theme utilities)
 * - celebration-effects.ts (Celebration effects)
 * - security-utils.ts (Security utilities)
 * 
 * Single unified utility module with mode-based features
 * Reduction: ~5 files → 1 file
 */

import { configManager, OperationMode } from '../../config/unified-config';
import confetti from 'canvas-confetti';
import CryptoJS from 'crypto-js';

/**
 * Performance Monitoring Utilities
 * Active in PERFORMANCE and ENTERPRISE modes
 */
export class PerformanceMonitor {
  private static instance: PerformanceMonitor;
  private metrics: Map<string, number[]> = new Map();
  private observers: Map<string, PerformanceObserver> = new Map();
  
  private constructor() {
    if (configManager.isFeatureEnabled('webWorkers')) {
      this.initializeObservers();
    }
  }
  
  static getInstance(): PerformanceMonitor {
    if (!PerformanceMonitor.instance) {
      PerformanceMonitor.instance = new PerformanceMonitor();
    }
    return PerformanceMonitor.instance;
  }
  
  /**
   * Initialize performance observers
   */
  private initializeObservers(): void {
    // Layout shift observer
    if ('PerformanceObserver' in window) {
      try {
        const cls = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if ('value' in entry) {
              this.recordMetric('cls', (entry as any).value);
            }
          }
        });
        cls.observe({ entryTypes: ['layout-shift'] });
        this.observers.set('cls', cls);
      } catch (e) {
        console.debug('CLS observer not supported');
      }
      
      // First input delay
      try {
        const fid = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if ('processingStart' in entry && 'startTime' in entry) {
              const delay = (entry as any).processingStart - entry.startTime;
              this.recordMetric('fid', delay);
            }
          }
        });
        fid.observe({ entryTypes: ['first-input'] });
        this.observers.set('fid', fid);
      } catch (e) {
        console.debug('FID observer not supported');
      }
    }
  }
  
  /**
   * Start performance measurement
   */
  startMeasure(name: string): void {
    if (!configManager.isFeatureEnabled('webWorkers')) return;
    performance.mark(`${name}-start`);
  }
  
  /**
   * End performance measurement
   */
  endMeasure(name: string): number {
    if (!configManager.isFeatureEnabled('webWorkers')) return 0;
    
    performance.mark(`${name}-end`);
    performance.measure(name, `${name}-start`, `${name}-end`);
    
    const measure = performance.getEntriesByName(name)[0];
    if (measure) {
      this.recordMetric(name, measure.duration);
      return measure.duration;
    }
    return 0;
  }
  
  /**
   * Record a metric value
   */
  recordMetric(name: string, value: number): void {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, []);
    }
    const values = this.metrics.get(name)!;
    values.push(value);
    
    // Keep only last 100 values
    if (values.length > 100) {
      values.shift();
    }
  }
  
  /**
   * Get metric statistics
   */
  getMetricStats(name: string): {
    avg: number;
    min: number;
    max: number;
    p50: number;
    p95: number;
  } | null {
    const values = this.metrics.get(name);
    if (!values || values.length === 0) return null;
    
    const sorted = [...values].sort((a, b) => a - b);
    const sum = sorted.reduce((a, b) => a + b, 0);
    
    return {
      avg: sum / sorted.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      p50: sorted[Math.floor(sorted.length * 0.5)],
      p95: sorted[Math.floor(sorted.length * 0.95)]
    };
  }
  
  /**
   * Get all metrics
   */
  getAllMetrics(): Record<string, any> {
    const result: Record<string, any> = {};
    for (const [name, values] of this.metrics) {
      result[name] = this.getMetricStats(name);
    }
    return result;
  }
  
  /**
   * Clean up observers
   */
  destroy(): void {
    for (const observer of this.observers.values()) {
      observer.disconnect();
    }
    this.observers.clear();
    this.metrics.clear();
  }
}

/**
 * Animation Utilities
 * Active in DELIGHTFUL and ENTERPRISE modes
 */
export const AnimationUtils = {
  /**
   * Spring animation presets
   */
  springs: {
    gentle: { type: 'spring', stiffness: 100, damping: 15 },
    bouncy: { type: 'spring', stiffness: 400, damping: 10 },
    stiff: { type: 'spring', stiffness: 700, damping: 30 },
    slow: { type: 'spring', stiffness: 50, damping: 20 }
  },
  
  /**
   * Common animation variants
   */
  variants: {
    fadeIn: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 }
    },
    slideUp: {
      initial: { opacity: 0, y: 20 },
      animate: { opacity: 1, y: 0 },
      exit: { opacity: 0, y: -20 }
    },
    slideDown: {
      initial: { opacity: 0, y: -20 },
      animate: { opacity: 1, y: 0 },
      exit: { opacity: 0, y: 20 }
    },
    scaleIn: {
      initial: { opacity: 0, scale: 0.8 },
      animate: { opacity: 1, scale: 1 },
      exit: { opacity: 0, scale: 0.8 }
    },
    rotate: {
      initial: { rotate: -180 },
      animate: { rotate: 0 },
      exit: { rotate: 180 }
    }
  },
  
  /**
   * Stagger children animation
   */
  staggerChildren: (delay = 0.1) => ({
    animate: {
      transition: {
        staggerChildren: delay
      }
    }
  }),
  
  /**
   * Page transition
   */
  pageTransition: {
    initial: { opacity: 0, x: -20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 20 },
    transition: { duration: 0.3 }
  },
  
  /**
   * Check if animations are enabled
   */
  isEnabled: () => configManager.isFeatureEnabled('animations'),
  
  /**
   * Get animation duration
   */
  getDuration: () => configManager.getDelightSettings().animationDuration
};

/**
 * Theme Utilities
 * Active in DELIGHTFUL and ENTERPRISE modes
 */
export const ThemeUtils = {
  /**
   * Delightful color palettes
   */
  palettes: {
    rainbow: ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'],
    pastel: ['#FFE5E5', '#E5F3FF', '#E5FFE5', '#FFF5E5', '#F5E5FF', '#E5FFF5'],
    neon: ['#FF00FF', '#00FFFF', '#FFFF00', '#FF00AA', '#00FF00', '#FF5500'],
    earth: ['#8B7355', '#A0826D', '#C19A6B', '#D2B48C', '#DEB887', '#F5DEB3'],
    ocean: ['#006994', '#0099CC', '#00B4D8', '#00C9FF', '#90E0EF', '#CAF0F8']
  },
  
  /**
   * Gradient generators
   */
  gradients: {
    linear: (colors: string[], angle = 45) => 
      `linear-gradient(${angle}deg, ${colors.join(', ')})`,
    radial: (colors: string[]) => 
      `radial-gradient(circle, ${colors.join(', ')})`,
    conic: (colors: string[]) => 
      `conic-gradient(${colors.join(', ')})`
  },
  
  /**
   * Shadow presets
   */
  shadows: {
    soft: '0 2px 8px rgba(0,0,0,0.08)',
    medium: '0 4px 16px rgba(0,0,0,0.12)',
    strong: '0 8px 32px rgba(0,0,0,0.16)',
    colored: (color: string) => `0 4px 16px ${color}33`,
    glow: (color: string) => `0 0 20px ${color}66`
  },
  
  /**
   * Get theme for current mode
   */
  getThemeVariant: () => {
    const mode = configManager.getConfig().mode;
    switch (mode) {
      case OperationMode.DELIGHTFUL:
        return 'playful';
      case OperationMode.SECURE:
        return 'professional';
      case OperationMode.ENTERPRISE:
        return 'sophisticated';
      default:
        return 'standard';
    }
  },
  
  /**
   * Check if advanced themes are enabled
   */
  isAdvancedThemesEnabled: () => configManager.isFeatureEnabled('advancedThemes')
};

/**
 * Celebration Effects
 * Active in DELIGHTFUL and ENTERPRISE modes
 */
export const CelebrationEffects = {
  /**
   * Confetti celebration
   */
  confetti: (options: Partial<confetti.Options> = {}) => {
    if (!configManager.isFeatureEnabled('celebrations')) return;
    
    const config = configManager.getDelightSettings();
    confetti({
      particleCount: config.particleCount,
      spread: 70,
      origin: { y: 0.6 },
      colors: config.confettiColors,
      ...options
    });
  },
  
  /**
   * Fireworks effect
   */
  fireworks: () => {
    if (!configManager.isFeatureEnabled('celebrations')) return;
    
    const config = configManager.getDelightSettings();
    const duration = config.celebrationDuration;
    const end = Date.now() + duration;
    
    const frame = () => {
      confetti({
        particleCount: 2,
        angle: 60,
        spread: 55,
        origin: { x: 0 },
        colors: config.confettiColors
      });
      confetti({
        particleCount: 2,
        angle: 120,
        spread: 55,
        origin: { x: 1 },
        colors: config.confettiColors
      });
      
      if (Date.now() < end) {
        requestAnimationFrame(frame);
      }
    };
    
    frame();
  },
  
  /**
   * Snow effect
   */
  snow: () => {
    if (!configManager.isFeatureEnabled('celebrations')) return;
    
    const config = configManager.getDelightSettings();
    const duration = config.celebrationDuration;
    const end = Date.now() + duration;
    
    const frame = () => {
      confetti({
        particleCount: 1,
        startVelocity: 0,
        ticks: 200,
        gravity: 0.3,
        origin: {
          x: Math.random(),
          y: 0
        },
        colors: ['#ffffff'],
        shapes: ['circle']
      });
      
      if (Date.now() < end) {
        requestAnimationFrame(frame);
      }
    };
    
    frame();
  },
  
  /**
   * Custom celebration
   */
  custom: (type: string) => {
    const celebrations: Record<string, () => void> = {
      success: () => CelebrationEffects.confetti({ colors: ['#4CAF50', '#8BC34A'] }),
      error: () => CelebrationEffects.confetti({ colors: ['#F44336', '#FF5722'] }),
      warning: () => CelebrationEffects.confetti({ colors: ['#FF9800', '#FFC107'] }),
      info: () => CelebrationEffects.confetti({ colors: ['#2196F3', '#03A9F4'] })
    };
    
    if (celebrations[type]) {
      celebrations[type]();
    }
  }
};

/**
 * Security Utilities
 * Active in SECURE and ENTERPRISE modes
 */
export const SecurityUtils = {
  /**
   * Sanitize HTML content
   */
  sanitizeHTML: (html: string): string => {
    if (!configManager.isFeatureEnabled('sanitization')) return html;
    
    // Remove script tags
    html = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    
    // Remove event handlers
    html = html.replace(/on\w+="[^"]*"/gi, '');
    html = html.replace(/on\w+='[^']*'/gi, '');
    
    // Remove javascript: protocol
    html = html.replace(/javascript:/gi, '');
    
    return html;
  },
  
  /**
   * Validate input against XSS patterns
   */
  validateInput: (input: string): boolean => {
    if (!configManager.isFeatureEnabled('sanitization')) return true;
    
    const xssPatterns = [
      /<script/i,
      /javascript:/i,
      /on\w+=/i,
      /<iframe/i,
      /<object/i,
      /<embed/i,
      /<link/i
    ];
    
    return !xssPatterns.some(pattern => pattern.test(input));
  },
  
  /**
   * Generate CSRF token
   */
  generateCSRFToken: (): string => {
    if (!configManager.isFeatureEnabled('csrfProtection')) return '';
    
    const tokenLength = configManager.getSecuritySettings().csrfTokenLength;
    return CryptoJS.lib.WordArray.random(tokenLength).toString();
  },
  
  /**
   * Hash sensitive data
   */
  hashData: (data: string): string => {
    if (!configManager.isFeatureEnabled('encryption')) return data;
    
    return CryptoJS.SHA256(data).toString();
  },
  
  /**
   * Mask PII data
   */
  maskPII: (text: string): string => {
    if (!configManager.isFeatureEnabled('piiDetection')) return text;
    
    // Email
    text = text.replace(/([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g, 
      (match, p1, p2) => `${p1.charAt(0)}***@${p2}`);
    
    // Phone
    text = text.replace(/\b(\d{3})[-.]?(\d{3})[-.]?(\d{4})\b/g, '***-***-$3');
    
    // SSN
    text = text.replace(/\b(\d{3})-(\d{2})-(\d{4})\b/g, '***-**-$3');
    
    // Credit Card
    text = text.replace(/\b(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})\b/g, 
      '$1 **** **** ****');
    
    return text;
  },
  
  /**
   * Log security event
   */
  logSecurityEvent: (event: string, data?: any): void => {
    if (!configManager.isFeatureEnabled('auditLogging')) return;
    
    const logEntry = {
      timestamp: Date.now(),
      event,
      data: data ? SecurityUtils.maskPII(JSON.stringify(data)) : undefined,
      user: globalStateManager?.getState()?.user?.id || 'anonymous'
    };
    
    // Store in localStorage or send to backend
    const logs = JSON.parse(localStorage.getItem('security-logs') || '[]');
    logs.push(logEntry);
    
    // Keep only last 1000 entries
    if (logs.length > 1000) {
      logs.shift();
    }
    
    localStorage.setItem('security-logs', JSON.stringify(logs));
  }
};

/**
 * Utility Helpers
 */
export const UtilityHelpers = {
  /**
   * Debounce function
   */
  debounce: <T extends (...args: any[]) => any>(
    func: T,
    delay: number
  ): ((...args: Parameters<T>) => void) => {
    let timeoutId: NodeJS.Timeout;
    return (...args: Parameters<T>) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func(...args), delay);
    };
  },
  
  /**
   * Throttle function
   */
  throttle: <T extends (...args: any[]) => any>(
    func: T,
    delay: number
  ): ((...args: Parameters<T>) => void) => {
    let lastCall = 0;
    return (...args: Parameters<T>) => {
      const now = Date.now();
      if (now - lastCall >= delay) {
        lastCall = now;
        func(...args);
      }
    };
  },
  
  /**
   * Deep clone object
   */
  deepClone: <T>(obj: T): T => {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime()) as any;
    if (obj instanceof Array) return obj.map(item => UtilityHelpers.deepClone(item)) as any;
    
    const cloned = {} as T;
    for (const key in obj) {
      cloned[key] = UtilityHelpers.deepClone(obj[key]);
    }
    return cloned;
  },
  
  /**
   * Format file size
   */
  formatFileSize: (bytes: number): string => {
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`;
  },
  
  /**
   * Generate unique ID
   */
  generateId: (): string => {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }
};

// Import statement for backward compatibility
import { globalStateManager } from '../../core/unified/state-management-unified';

/**
 * Export all utilities
 */
export default {
  performanceMonitor: PerformanceMonitor.getInstance(),
  animation: AnimationUtils,
  theme: ThemeUtils,
  celebration: CelebrationEffects,
  security: SecurityUtils,
  helpers: UtilityHelpers
};