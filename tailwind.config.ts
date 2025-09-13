import type { Config } from 'tailwindcss';
import { designTokens } from './design-tokens';

/**
 * Tailwind CSS Configuration for DevDocAI v3.6.0
 *
 * This configuration extends Tailwind CSS with our custom design tokens
 * to ensure consistent theming across all Vue 3 components.
 *
 * Based on: design-tokens.ts and v3.6.0 mockup specifications
 */

const config: Config = {
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './components/**/*.{vue,js,ts,jsx,tsx}',
    './layouts/**/*.{vue,js,ts,jsx,tsx}',
    './pages/**/*.{vue,js,ts,jsx,tsx}',
    './app.vue'
  ],

  darkMode: 'class', // Enable class-based dark mode

  theme: {
    // Override default Tailwind theme with our design tokens
    extend: {
      // Colors from design tokens
      colors: {
        // Semantic colors
        success: designTokens.colors.semantic.success,
        warning: designTokens.colors.semantic.warning,
        danger: designTokens.colors.semantic.danger,
        info: designTokens.colors.semantic.info,

        // Primary brand colors
        primary: designTokens.colors.primary,

        // Neutral scale
        neutral: designTokens.colors.neutral,

        // Health score colors (specific to DevDocAI)
        health: designTokens.colors.health,

        // Status colors
        status: designTokens.colors.status,

        // Alias common colors to semantic names
        gray: designTokens.colors.neutral,
        slate: designTokens.colors.primary,
        green: designTokens.colors.semantic.success,
        yellow: designTokens.colors.semantic.warning,
        red: designTokens.colors.semantic.danger,
        blue: designTokens.colors.semantic.info
      },

      // Typography
      fontFamily: designTokens.typography.fontFamily,
      fontSize: designTokens.typography.fontSize,
      fontWeight: designTokens.typography.fontWeight,
      lineHeight: designTokens.typography.lineHeight,
      letterSpacing: designTokens.typography.letterSpacing,

      // Spacing (8px base grid system)
      spacing: designTokens.spacing,

      // Responsive breakpoints
      screens: {
        'mobile': designTokens.breakpoints.mobile,
        'tablet': designTokens.breakpoints.tablet,
        'desktop': designTokens.breakpoints.desktop,
        'wide': designTokens.breakpoints.wide,
        'ultrawide': designTokens.breakpoints.ultrawide,

        // Maintain Tailwind defaults with our custom names
        'sm': designTokens.breakpoints.mobile,
        'md': designTokens.breakpoints.tablet,
        'lg': designTokens.breakpoints.desktop,
        'xl': designTokens.breakpoints.wide,
        '2xl': designTokens.breakpoints.ultrawide
      },

      // Border radius
      borderRadius: designTokens.borderRadius,

      // Box shadows (elevation)
      boxShadow: {
        ...designTokens.elevation,
        // Map to Tailwind naming convention
        'shadow-sm': designTokens.elevation.sm,
        'shadow': designTokens.elevation.md,
        'shadow-md': designTokens.elevation.md,
        'shadow-lg': designTokens.elevation.lg,
        'shadow-xl': designTokens.elevation.xl,
        'shadow-2xl': designTokens.elevation['2xl'],
        'shadow-inner': designTokens.elevation.inner,
        'shadow-none': designTokens.elevation.none
      },

      // Z-index scale
      zIndex: designTokens.zIndex,

      // Animation durations
      transitionDuration: {
        ...designTokens.motion.duration,
        // Map to convenient names
        'instant': designTokens.motion.duration.instant,
        'micro': designTokens.motion.duration.micro,
        'fast': designTokens.motion.duration.fast,
        'normal': designTokens.motion.duration.normal,
        'medium': designTokens.motion.duration.medium,
        'slow': designTokens.motion.duration.slow,
        'slower': designTokens.motion.duration.slower,
        'slowest': designTokens.motion.duration.slowest
      },

      // Animation easing
      transitionTimingFunction: {
        ...designTokens.motion.easing,
        // Custom easing functions
        'standard': designTokens.motion.easing.standard,
        'decelerate': designTokens.motion.easing.decelerate,
        'accelerate': designTokens.motion.easing.accelerate,
        'spring': designTokens.motion.easing.spring
      },

      // Custom utilities for DevDocAI components
      extend: {
        // Component-specific sizes
        height: {
          'button-sm': designTokens.components.button.height.sm,
          'button-md': designTokens.components.button.height.md,
          'button-lg': designTokens.components.button.height.lg,
          'button-xl': designTokens.components.button.height.xl,
          'input-sm': designTokens.components.input.height.sm,
          'input-md': designTokens.components.input.height.md,
          'input-lg': designTokens.components.input.height.lg
        },

        width: {
          'modal-sm': designTokens.components.modal.width.sm,
          'modal-md': designTokens.components.modal.width.md,
          'modal-lg': designTokens.components.modal.width.lg,
          'modal-xl': designTokens.components.modal.width.xl,
          'modal-full': designTokens.components.modal.width.full
        },

        maxHeight: {
          'modal': designTokens.components.modal.maxHeight
        },

        // Touch target sizes for accessibility
        minWidth: {
          'touch': designTokens.accessibility.touchTarget.minimum,
          'touch-recommended': designTokens.accessibility.touchTarget.recommended
        },
        minHeight: {
          'touch': designTokens.accessibility.touchTarget.minimum,
          'touch-recommended': designTokens.accessibility.touchTarget.recommended
        }
      }
    }
  },

  plugins: [
    // Custom plugin for DevDocAI-specific utilities
    function({ addUtilities, addComponents, theme }) {
      // Add component classes
      addComponents({
        // Button variants
        '.btn': {
          '@apply inline-flex items-center justify-center font-medium rounded-md transition-all duration-fast focus:outline-none focus:ring-2 focus:ring-offset-2': {},
          minHeight: designTokens.accessibility.touchTarget.minimum,
          minWidth: designTokens.accessibility.touchTarget.minimum
        },
        '.btn-sm': {
          '@apply text-sm px-3 py-2 h-button-sm': {}
        },
        '.btn-md': {
          '@apply text-base px-4 py-2.5 h-button-md': {}
        },
        '.btn-lg': {
          '@apply text-lg px-6 py-3 h-button-lg': {}
        },
        '.btn-xl': {
          '@apply text-xl px-8 py-4 h-button-xl': {}
        },

        // Button color variants
        '.btn-primary': {
          '@apply bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500': {}
        },
        '.btn-success': {
          '@apply bg-success-600 text-white hover:bg-success-700 focus:ring-success-500': {}
        },
        '.btn-warning': {
          '@apply bg-warning-600 text-white hover:bg-warning-700 focus:ring-warning-500': {}
        },
        '.btn-danger': {
          '@apply bg-danger-600 text-white hover:bg-danger-700 focus:ring-danger-500': {}
        },
        '.btn-info': {
          '@apply bg-info-600 text-white hover:bg-info-700 focus:ring-info-500': {}
        },
        '.btn-ghost': {
          '@apply bg-transparent text-primary-600 hover:bg-primary-50 focus:ring-primary-500': {}
        },
        '.btn-outline': {
          '@apply bg-transparent border border-primary-600 text-primary-600 hover:bg-primary-600 hover:text-white focus:ring-primary-500': {}
        },

        // Input components
        '.input': {
          '@apply block w-full rounded-md border border-neutral-300 px-3 py-2 text-neutral-900 placeholder-neutral-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500': {},
          minHeight: designTokens.accessibility.touchTarget.minimum
        },
        '.input-sm': {
          '@apply text-sm h-input-sm': {}
        },
        '.input-md': {
          '@apply text-base h-input-md': {}
        },
        '.input-lg': {
          '@apply text-lg h-input-lg': {}
        },

        // Card components
        '.card': {
          '@apply bg-white rounded-lg shadow-md border border-neutral-200': {}
        },
        '.card-sm': {
          '@apply p-4': {}
        },
        '.card-md': {
          '@apply p-6': {}
        },
        '.card-lg': {
          '@apply p-8': {}
        },
        '.card-xl': {
          '@apply p-10': {}
        },

        // Health score indicators
        '.health-excellent': {
          '@apply text-health-excellent bg-success-50 border-success-200': {}
        },
        '.health-good': {
          '@apply text-health-good bg-warning-50 border-warning-200': {}
        },
        '.health-poor': {
          '@apply text-health-poor bg-danger-50 border-danger-200': {}
        },

        // Status indicators
        '.status-online': {
          '@apply text-status-online bg-success-50': {}
        },
        '.status-offline': {
          '@apply text-status-offline bg-neutral-50': {}
        },
        '.status-pending': {
          '@apply text-status-pending bg-warning-50': {}
        },
        '.status-error': {
          '@apply text-status-error bg-danger-50': {}
        },
        '.status-processing': {
          '@apply text-status-processing bg-info-50': {}
        }
      });

      // Add custom utilities
      addUtilities({
        // Focus ring utilities for accessibility
        '.focus-ring': {
          '&:focus': {
            outline: `${designTokens.accessibility.focus.outline.width} ${designTokens.accessibility.focus.outline.style} ${designTokens.accessibility.focus.outline.color}`,
            outlineOffset: designTokens.accessibility.focus.outline.offset
          }
        },
        '.focus-ring-inset': {
          '&:focus': {
            outline: `${designTokens.accessibility.focus.outline.width} ${designTokens.accessibility.focus.outline.style} ${designTokens.accessibility.focus.outline.color}`,
            outlineOffset: `-${designTokens.accessibility.focus.outline.width}`
          }
        },

        // Animation utilities
        '.animate-shimmer': {
          background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite linear'
        },
        '.animate-pulse-soft': {
          animation: 'pulse 2s infinite ease-in-out'
        },

        // Touch target utilities
        '.touch-target': {
          minWidth: designTokens.accessibility.touchTarget.minimum,
          minHeight: designTokens.accessibility.touchTarget.minimum
        },
        '.touch-target-recommended': {
          minWidth: designTokens.accessibility.touchTarget.recommended,
          minHeight: designTokens.accessibility.touchTarget.recommended
        }
      });

      // Add keyframe animations
      addUtilities({
        '@keyframes shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' }
        },
        '@keyframes pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' }
        },
        '@keyframes fadeIn': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' }
        },
        '@keyframes slideIn': {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(0)' }
        }
      });
    },

    // Accessibility plugin for reduced motion
    function({ addVariant }) {
      addVariant('reduce-motion', '@media (prefers-reduced-motion: reduce)');
      addVariant('motion-safe', '@media (prefers-reduced-motion: no-preference)');
    }
  ],

  // Safelist classes that might be generated dynamically
  safelist: [
    // Health score classes
    'health-excellent',
    'health-good',
    'health-poor',
    // Status classes
    'status-online',
    'status-offline',
    'status-pending',
    'status-error',
    'status-processing',
    // Button variants
    'btn-primary',
    'btn-success',
    'btn-warning',
    'btn-danger',
    'btn-info',
    'btn-ghost',
    'btn-outline',
    // Component sizes
    'btn-sm',
    'btn-md',
    'btn-lg',
    'btn-xl',
    'input-sm',
    'input-md',
    'input-lg',
    'card-sm',
    'card-md',
    'card-lg',
    'card-xl',
    // Animation classes
    'animate-shimmer',
    'animate-pulse-soft',
    // Accessibility
    'focus-ring',
    'focus-ring-inset',
    'touch-target',
    'touch-target-recommended'
  ]
};

export default config;