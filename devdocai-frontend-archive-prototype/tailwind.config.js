/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      // Color System - Based on v3.6.0 Mockups
      colors: {
        // Primary brand colors - DevDocAI purple
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
        // Secondary colors - Success green
        secondary: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10B981', // Secondary brand color
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
          950: '#022c22',
        },
        // Status colors - Health scores and alerts
        status: {
          success: {
            50: '#ecfdf5',
            500: '#10B981',
            600: '#059669',
            700: '#047857',
          },
          warning: {
            50: '#fffbeb',
            500: '#f59e0b',
            600: '#d97706',
            700: '#b45309',
          },
          danger: {
            50: '#fef2f2',
            500: '#ef4444',
            600: '#dc2626',
            700: '#b91c1c',
          },
          info: {
            50: '#eff6ff',
            500: '#3b82f6',
            600: '#2563eb',
            700: '#1d4ed8',
          },
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
        // Accessibility colors - High contrast modes
        accessibility: {
          high: {
            bg: '#000000',
            text: '#ffffff',
            focus: '#00ff00',
          }
        }
      },
      // Typography System - Based on v3.6.0 requirements
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Monaco', 'Cascadia Code', 'Segoe UI Mono', 'Roboto Mono', 'monospace'],
        dyslexic: ['OpenDyslexic', 'Comic Sans MS', 'Verdana', 'Arial', 'sans-serif'],
      },
      fontSize: {
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
      // Spacing System - Based on 8px grid
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      // Motion Design System - Based on v3.6.0 motion guidelines
      transitionDuration: {
        '50': '50ms',
        '200': '200ms',
        '400': '400ms',
        '800': '800ms',
        '1500': '1500ms',
      },
      transitionTimingFunction: {
        'standard': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'decelerate': 'cubic-bezier(0, 0, 0.2, 1)',
        'accelerate': 'cubic-bezier(0.4, 0, 1, 1)',
        'spring': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
      },
      // Animation System - v3.6.0 specifications
      animation: {
        // Standard animations
        'fade-in': 'fadeIn 300ms ease-decelerate',
        'fade-out': 'fadeOut 200ms ease-accelerate',
        'slide-up': 'slideUp 400ms cubic-bezier(0.4, 0, 0.2, 1)',
        'slide-down': 'slideDown 400ms cubic-bezier(0.4, 0, 0.2, 1)',
        'slide-left': 'slideLeft 300ms ease-decelerate',
        'slide-right': 'slideRight 300ms ease-decelerate',
        'scale-in': 'scaleIn 200ms ease-decelerate',
        'scale-out': 'scaleOut 150ms ease-accelerate',
        // Loading animations
        'pulse-soft': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 1.5s linear infinite',
        'spin-slow': 'spin 3s linear infinite',
        // Interactive animations
        'bounce-soft': 'bounceSoft 600ms ease-in-out',
        'glow': 'glow 2s ease-in-out infinite alternate',
        // Progress animations
        'progress-fill': 'progressFill 500ms ease-decelerate',
        'stagger': 'stagger 50ms ease-decelerate',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        slideUp: {
          '0%': { transform: 'translateY(10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideLeft: {
          '0%': { transform: 'translateX(10px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideRight: {
          '0%': { transform: 'translateX(-10px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        scaleOut: {
          '0%': { transform: 'scale(1)', opacity: '1' },
          '100%': { transform: 'scale(0.95)', opacity: '0' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        bounceSoft: {
          '0%, 20%, 53%, 80%, 100%': { transform: 'translateY(0)' },
          '40%, 43%': { transform: 'translateY(-2px)' },
          '70%': { transform: 'translateY(-1px)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(79, 70, 229, 0.3)' },
          '100%': { boxShadow: '0 0 20px rgba(79, 70, 229, 0.6)' },
        },
        progressFill: {
          '0%': { width: '0%' },
          '100%': { width: 'var(--progress-width, 100%)' },
        },
        stagger: {
          '0%': { transform: 'translateY(5px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
      // Shadow System - Elevation and depth
      boxShadow: {
        'none': 'none',
        'xs': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'sm': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
        'DEFAULT': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
        'inner': 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)',
        // DevDocAI specific shadows
        'soft': '0 2px 15px -3px rgba(0, 0, 0, 0.07), 0 10px 20px -2px rgba(0, 0, 0, 0.04)',
        'glow': '0 0 20px rgba(79, 70, 229, 0.3)',
        'glow-green': '0 0 20px rgba(16, 185, 129, 0.3)',
        'glow-red': '0 0 20px rgba(239, 68, 68, 0.3)',
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
        'focus': '0 0 0 3px rgba(79, 70, 229, 0.1)',
        'focus-ring': '0 0 0 2px #ffffff, 0 0 0 4px rgba(79, 70, 229, 0.5)',
      },
      // Border Radius System
      borderRadius: {
        'none': '0',
        'sm': '0.125rem',
        'DEFAULT': '0.25rem',
        'md': '0.375rem',
        'lg': '0.5rem',
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
        'full': '9999px',
      },
      // Accessibility - WCAG 2.1 AA compliance
      ringWidth: {
        '3': '3px',
        '4': '4px',
      },
      ringColor: {
        'focus': 'rgba(79, 70, 229, 0.5)',
        'focus-visible': 'rgba(79, 70, 229, 1)',
      },
      // Responsive breakpoints
      screens: {
        'xs': '375px',
        'sm': '640px',
        'md': '768px',
        'lg': '1024px',
        'xl': '1280px',
        '2xl': '1536px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
    // Custom plugin for component utilities
    function({ addUtilities, theme }) {
      const newUtilities = {
        // Motion utilities for accessibility
        '.motion-safe': {
          '@media (prefers-reduced-motion: no-preference)': {
            // Animation styles will only apply if user hasn't requested reduced motion
          }
        },
        '.motion-reduce': {
          '@media (prefers-reduced-motion: reduce)': {
            'animation-duration': '0.01ms !important',
            'animation-iteration-count': '1 !important',
            'transition-duration': '0.01ms !important',
          }
        },
        // Focus utilities for accessibility
        '.focus-ring': {
          '&:focus': {
            outline: 'none',
            'box-shadow': '0 0 0 2px #ffffff, 0 0 0 4px rgba(79, 70, 229, 0.5)',
          }
        },
        '.focus-ring-inset': {
          '&:focus': {
            outline: 'none',
            'box-shadow': 'inset 0 0 0 2px rgba(79, 70, 229, 0.5)',
          }
        },
        // Skip link utility for accessibility
        '.sr-only-focusable': {
          position: 'absolute',
          left: '-10000px',
          width: '1px',
          height: '1px',
          overflow: 'hidden',
          '&:focus': {
            position: 'static',
            width: 'auto',
            height: 'auto',
            overflow: 'visible',
          }
        }
      }
      addUtilities(newUtilities)
    }
  ],
}
