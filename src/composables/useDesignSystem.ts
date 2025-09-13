import { ref, computed, watch, type Ref } from 'vue';
import { designTokens, themes, type ThemeMode, type Theme } from '../../design-tokens';

/**
 * Vue 3 Composable for DevDocAI Design System
 *
 * Provides theme management, design token access, and utility functions
 * for consistent UI implementation across all components.
 *
 * Features:
 * - Theme switching (light/dark/high-contrast)
 * - Design token access
 * - Responsive breakpoint utilities
 * - Animation control (respects prefers-reduced-motion)
 * - Accessibility helpers
 */

// Global theme state (reactive across all components)
const currentTheme: Ref<ThemeMode> = ref('light');
const systemTheme: Ref<'light' | 'dark'> = ref('light');
const reducedMotion: Ref<boolean> = ref(false);

export function useDesignSystem() {
  // Computed theme object
  const theme = computed<Theme>(() => themes[currentTheme.value]);

  // Theme utilities
  const setTheme = (newTheme: ThemeMode) => {
    currentTheme.value = newTheme;

    // Update HTML class for CSS
    const html = document.documentElement;
    html.classList.remove('light', 'dark', 'high-contrast');

    if (newTheme === 'dark') {
      html.classList.add('dark');
    } else if (newTheme === 'highContrast') {
      html.classList.add('high-contrast', 'dark'); // High contrast uses dark theme base
    } else {
      html.classList.add('light');
    }

    // Store preference
    localStorage.setItem('devdocai-theme', newTheme);
  };

  const toggleTheme = () => {
    const nextTheme: ThemeMode = currentTheme.value === 'light' ? 'dark' : 'light';
    setTheme(nextTheme);
  };

  // Initialize theme from localStorage or system preference
  const initializeTheme = () => {
    // Check for saved theme preference
    const savedTheme = localStorage.getItem('devdocai-theme') as ThemeMode;
    if (savedTheme && ['light', 'dark', 'highContrast'].includes(savedTheme)) {
      setTheme(savedTheme);
      return;
    }

    // Check system preference
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      systemTheme.value = mediaQuery.matches ? 'dark' : 'light';
      setTheme(systemTheme.value);

      // Listen for system theme changes
      mediaQuery.addEventListener('change', (e) => {
        systemTheme.value = e.matches ? 'dark' : 'light';
        // Only update if no manual theme is set
        if (!localStorage.getItem('devdocai-theme')) {
          setTheme(systemTheme.value);
        }
      });
    }
  };

  // Motion preferences
  const initializeMotionPreference = () => {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
      reducedMotion.value = mediaQuery.matches;

      mediaQuery.addEventListener('change', (e) => {
        reducedMotion.value = e.matches;
      });
    }
  };

  // Responsive breakpoint utilities
  const breakpoints = {
    mobile: parseInt(designTokens.breakpoints.mobile),
    tablet: parseInt(designTokens.breakpoints.tablet),
    desktop: parseInt(designTokens.breakpoints.desktop),
    wide: parseInt(designTokens.breakpoints.wide),
    ultrawide: parseInt(designTokens.breakpoints.ultrawide)
  };

  const getBreakpoint = () => {
    if (typeof window === 'undefined') return 'desktop';

    const width = window.innerWidth;

    if (width < breakpoints.mobile) return 'mobile';
    if (width < breakpoints.tablet) return 'tablet';
    if (width < breakpoints.desktop) return 'desktop';
    if (width < breakpoints.wide) return 'wide';
    return 'ultrawide';
  };

  const isBreakpoint = (bp: keyof typeof breakpoints) => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth >= breakpoints[bp];
  };

  const isMobile = computed(() => !isBreakpoint('tablet'));
  const isTablet = computed(() => isBreakpoint('tablet') && !isBreakpoint('desktop'));
  const isDesktop = computed(() => isBreakpoint('desktop'));

  // Color utilities
  const getSemanticColor = (type: 'success' | 'warning' | 'danger' | 'info', shade: number = 500) => {
    return designTokens.colors.semantic[type][shade as keyof typeof designTokens.colors.semantic.success];
  };

  const getHealthColor = (score: number) => {
    if (score >= 85) return designTokens.colors.health.excellent;
    if (score >= 70) return designTokens.colors.health.good;
    return designTokens.colors.health.poor;
  };

  const getHealthClass = (score: number) => {
    if (score >= 85) return 'health-excellent';
    if (score >= 70) return 'health-good';
    return 'health-poor';
  };

  // Animation utilities
  const getAnimationDuration = (type: keyof typeof designTokens.motion.duration) => {
    if (reducedMotion.value) {
      return designTokens.accessibility.reducedMotion.duration;
    }
    return designTokens.motion.duration[type];
  };

  const shouldAnimate = computed(() => !reducedMotion.value);

  // Spacing utilities
  const getSpacing = (size: keyof typeof designTokens.spacing) => {
    return designTokens.spacing[size];
  };

  // Component size utilities
  const getButtonHeight = (size: keyof typeof designTokens.components.button.height) => {
    return designTokens.components.button.height[size];
  };

  const getButtonPadding = (size: keyof typeof designTokens.components.button.padding) => {
    return designTokens.components.button.padding[size];
  };

  // Accessibility utilities
  const getFocusRing = () => ({
    outline: `${designTokens.accessibility.focus.outline.width} ${designTokens.accessibility.focus.outline.style} ${designTokens.accessibility.focus.outline.color}`,
    outlineOffset: designTokens.accessibility.focus.outline.offset
  });

  const getTouchTargetSize = () => designTokens.accessibility.touchTarget.minimum;

  // CSS custom properties for dynamic theming
  const cssVariables = computed(() => {
    const vars: Record<string, string> = {};

    // Theme colors
    Object.entries(theme.value.background).forEach(([key, value]) => {
      vars[`--color-bg-${key}`] = value;
    });

    Object.entries(theme.value.text).forEach(([key, value]) => {
      vars[`--color-text-${key}`] = value;
    });

    Object.entries(theme.value.border).forEach(([key, value]) => {
      vars[`--color-border-${key}`] = value;
    });

    return vars;
  });

  // Apply CSS variables to document
  watch(cssVariables, (vars) => {
    if (typeof document !== 'undefined') {
      Object.entries(vars).forEach(([property, value]) => {
        document.documentElement.style.setProperty(property, value);
      });
    }
  }, { immediate: true });

  // Format utilities for display
  const formatHealthScore = (score: number) => `${Math.round(score)}%`;

  const formatFileSize = (bytes: number) => {
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;

    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024;
      unitIndex++;
    }

    return `${size.toFixed(1)} ${units[unitIndex]}`;
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    if (ms < 3600000) return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
    return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}m`;
  };

  // Status icon mapping
  const getStatusIcon = (status: string) => {
    const icons = {
      online: '✅',
      offline: '⚪',
      pending: '🔄',
      error: '❌',
      processing: '⚡',
      success: '✅',
      warning: '⚠️',
      danger: '🚨',
      info: 'ℹ️'
    };
    return icons[status as keyof typeof icons] || '●';
  };

  // Initialize on first use
  if (typeof window !== 'undefined') {
    initializeTheme();
    initializeMotionPreference();
  }

  return {
    // Theme state
    currentTheme: computed(() => currentTheme.value),
    theme,
    systemTheme: computed(() => systemTheme.value),

    // Theme actions
    setTheme,
    toggleTheme,
    initializeTheme,

    // Design tokens
    tokens: designTokens,
    colors: designTokens.colors,
    typography: designTokens.typography,
    spacing: designTokens.spacing,
    motion: designTokens.motion,
    accessibility: designTokens.accessibility,

    // Responsive utilities
    breakpoints,
    getBreakpoint,
    isBreakpoint,
    isMobile,
    isTablet,
    isDesktop,

    // Color utilities
    getSemanticColor,
    getHealthColor,
    getHealthClass,

    // Animation utilities
    reducedMotion: computed(() => reducedMotion.value),
    shouldAnimate,
    getAnimationDuration,

    // Spacing utilities
    getSpacing,

    // Component utilities
    getButtonHeight,
    getButtonPadding,

    // Accessibility utilities
    getFocusRing,
    getTouchTargetSize,

    // CSS variables
    cssVariables,

    // Format utilities
    formatHealthScore,
    formatFileSize,
    formatDuration,
    getStatusIcon
  };
}

// Export types for external use
export type { ThemeMode, Theme };
export { designTokens, themes };