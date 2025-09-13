/**
 * DevDocAI v3.6.0 Design Tokens
 *
 * Centralized design system tokens extracted from v3.6.0 mockups
 * and integrated with Tailwind CSS configuration.
 */

// Color System
export const colors = {
  // Primary brand colors (DevDocAI purple)
  primary: {
    50: '#eef2ff',
    100: '#e0e7ff',
    200: '#c7d2fe',
    300: '#a5b4fc',
    400: '#818cf8',
    500: '#6366f1',
    600: '#4F46E5', // Main brand color
    700: '#4338ca',
    800: '#3730a3',
    900: '#312e81',
    950: '#1e1b4b',
  },

  // Status colors - Health scores and alerts
  status: {
    success: {
      light: '#ecfdf5',
      base: '#10B981',
      dark: '#047857',
    },
    warning: {
      light: '#fffbeb',
      base: '#f59e0b',
      dark: '#b45309',
    },
    danger: {
      light: '#fef2f2',
      base: '#ef4444',
      dark: '#b91c1c',
    },
    info: {
      light: '#eff6ff',
      base: '#3b82f6',
      dark: '#1d4ed8',
    },
  },

  // Health score color mapping
  healthColors: {
    excellent: '#10B981', // 90%+
    good: '#3b82f6',      // 80-89%
    fair: '#f59e0b',      // 70-79%
    poor: '#ef4444',      // <70%
  },

  // Neutral colors for UI elements
  neutral: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
    950: '#030712',
  },
}

// Typography System
export const typography = {
  fontFamilies: {
    sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
    mono: ['JetBrains Mono', 'Monaco', 'Cascadia Code', 'Segoe UI Mono', 'Roboto Mono', 'monospace'],
    dyslexic: ['OpenDyslexic', 'Comic Sans MS', 'Verdana', 'Arial', 'sans-serif'],
  },

  fontSizes: {
    '2xs': ['0.625rem', { lineHeight: '0.75rem' }],
    'xs': ['0.75rem', { lineHeight: '1rem' }],
    'sm': ['0.875rem', { lineHeight: '1.25rem' }],
    'base': ['1rem', { lineHeight: '1.5rem' }],
    'lg': ['1.125rem', { lineHeight: '1.75rem' }],
    'xl': ['1.25rem', { lineHeight: '1.75rem' }],
    '2xl': ['1.5rem', { lineHeight: '2rem' }],
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
    '5xl': ['3rem', { lineHeight: '1' }],
  },

  fontWeights: {
    thin: '100',
    extralight: '200',
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    extrabold: '800',
    black: '900',
  },
}

// Spacing System (8px grid)
export const spacing = {
  0: '0',
  1: '0.25rem',   // 4px
  2: '0.5rem',    // 8px
  3: '0.75rem',   // 12px
  4: '1rem',      // 16px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  8: '2rem',      // 32px
  10: '2.5rem',   // 40px
  12: '3rem',     // 48px
  16: '4rem',     // 64px
  20: '5rem',     // 80px
  24: '6rem',     // 96px
  32: '8rem',     // 128px
}

// Component sizes
export const sizes = {
  button: {
    sm: {
      height: '2rem',      // 32px
      padding: '0.5rem 0.75rem',
      fontSize: 'sm',
    },
    md: {
      height: '2.5rem',    // 40px
      padding: '0.75rem 1rem',
      fontSize: 'base',
    },
    lg: {
      height: '3rem',      // 48px
      padding: '0.875rem 1.25rem',
      fontSize: 'lg',
    },
    xl: {
      height: '3.5rem',    // 56px
      padding: '1rem 1.5rem',
      fontSize: 'xl',
    },
  },

  input: {
    sm: {
      height: '2rem',
      padding: '0.375rem 0.75rem',
      fontSize: 'sm',
    },
    md: {
      height: '2.5rem',
      padding: '0.5rem 0.875rem',
      fontSize: 'base',
    },
    lg: {
      height: '3rem',
      padding: '0.75rem 1rem',
      fontSize: 'lg',
    },
  },

  avatar: {
    xs: '1.5rem',   // 24px
    sm: '2rem',     // 32px
    md: '2.5rem',   // 40px
    lg: '3rem',     // 48px
    xl: '4rem',     // 64px
    '2xl': '5rem',  // 80px
  },
}

// Shadow System
export const shadows = {
  none: 'none',
  xs: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  sm: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
  md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
  lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
  xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
  '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',

  // DevDocAI specific shadows
  soft: '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
  glow: '0 0 20px rgba(79, 70, 229, 0.3)',
  'glow-green': '0 0 20px rgba(16, 185, 129, 0.3)',
  'glow-red': '0 0 20px rgba(239, 68, 68, 0.3)',
  focus: '0 0 0 3px rgba(79, 70, 229, 0.1)',
  'focus-ring': '0 0 0 2px #ffffff, 0 0 0 4px rgba(79, 70, 229, 0.5)',
}

// Border Radius System
export const borderRadius = {
  none: '0',
  sm: '0.125rem',
  md: '0.375rem',
  lg: '0.5rem',
  xl: '0.75rem',
  '2xl': '1rem',
  '3xl': '1.5rem',
  full: '9999px',
}

// Motion Design Tokens
export const motion = {
  // Duration tokens
  durations: {
    instant: '0ms',
    fast: '150ms',
    normal: '300ms',
    slow: '500ms',
    slower: '800ms',
  },

  // Easing functions from v3.6.0 specs
  easings: {
    standard: 'cubic-bezier(0.4, 0, 0.2, 1)',
    decelerate: 'cubic-bezier(0, 0, 0.2, 1)',
    accelerate: 'cubic-bezier(0.4, 0, 1, 1)',
    spring: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  },

  // Predefined animations
  animations: {
    // Micro-interactions
    hover: {
      duration: '150ms',
      easing: 'ease-standard',
    },
    focus: {
      duration: '100ms',
      easing: 'ease-standard',
    },
    press: {
      duration: '100ms',
      easing: 'ease-accelerate',
    },

    // State transitions
    fadeIn: {
      duration: '300ms',
      easing: 'ease-decelerate',
    },
    slideUp: {
      duration: '400ms',
      easing: 'standard',
    },
    scaleIn: {
      duration: '200ms',
      easing: 'ease-decelerate',
    },

    // Loading states
    shimmer: {
      duration: '1500ms',
      easing: 'linear',
      iterationCount: 'infinite',
    },
    pulse: {
      duration: '2000ms',
      easing: 'ease-in-out',
      iterationCount: 'infinite',
    },
  },
}

// Z-index System
export const zIndex = {
  base: 0,
  dropdown: 10,
  sticky: 20,
  fixed: 30,
  modal: 40,
  popover: 50,
  tooltip: 60,
  toast: 70,
  overlay: 80,
  max: 9999,
}

// Breakpoint System
export const breakpoints = {
  xs: '375px',
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1536px',
}

// Component variants
export const variants = {
  button: {
    primary: {
      bg: colors.primary[600],
      bgHover: colors.primary[700],
      text: '#ffffff',
      border: 'transparent',
    },
    secondary: {
      bg: colors.neutral[100],
      bgHover: colors.neutral[200],
      text: colors.neutral[900],
      border: colors.neutral[300],
    },
    ghost: {
      bg: 'transparent',
      bgHover: colors.neutral[100],
      text: colors.neutral[700],
      border: 'transparent',
    },
    danger: {
      bg: colors.status.danger.base,
      bgHover: colors.status.danger.dark,
      text: '#ffffff',
      border: 'transparent',
    },
  },

  badge: {
    success: {
      bg: colors.status.success.light,
      text: colors.status.success.dark,
      border: colors.status.success.base,
    },
    warning: {
      bg: colors.status.warning.light,
      text: colors.status.warning.dark,
      border: colors.status.warning.base,
    },
    danger: {
      bg: colors.status.danger.light,
      text: colors.status.danger.dark,
      border: colors.status.danger.base,
    },
    info: {
      bg: colors.status.info.light,
      text: colors.status.info.dark,
      border: colors.status.info.base,
    },
  },
}

// Accessibility tokens
export const a11y = {
  // Focus ring specifications
  focusRing: {
    width: '2px',
    offset: '2px',
    color: colors.primary[600],
    style: 'solid',
  },

  // High contrast mode colors
  highContrast: {
    bg: '#000000',
    text: '#ffffff',
    accent: '#00ff00',
  },

  // Minimum touch target size (44px)
  minTouchTarget: '2.75rem',

  // WCAG contrast ratios
  contrastRatios: {
    aa: '4.5:1',    // WCAG AA standard
    aaa: '7:1',     // WCAG AAA standard
  },
}

// Export all tokens as a unified system
export default {
  colors,
  typography,
  spacing,
  sizes,
  shadows,
  borderRadius,
  motion,
  zIndex,
  breakpoints,
  variants,
  a11y,
}
