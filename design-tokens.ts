/**
 * DevDocAI v3.6.0 Design System Tokens
 *
 * Comprehensive design token system extracted from v3.6.0 mockups and wireframes.
 * This serves as the single source of truth for all visual design elements.
 *
 * Based on: docs/02-design/mockups/DESIGN-devdocai-mockups.md
 * Technology: Vue 3 + Vite + Tailwind CSS + TypeScript
 * Accessibility: WCAG 2.1 AA compliant
 */

export const designTokens = {
  /**
   * COLOR PALETTE
   * Semantic color system with accessibility-compliant contrast ratios
   */
  colors: {
    // Semantic Colors (from mockups)
    semantic: {
      success: {
        50: '#f0fdf4',
        100: '#dcfce7',
        500: '#10b981', // Primary success color (4.5:1 contrast)
        600: '#059669',
        700: '#047857',
        900: '#064e3b'
      },
      warning: {
        50: '#fffbeb',
        100: '#fef3c7',
        500: '#f59e0b', // Primary warning color
        600: '#d97706',
        700: '#b45309',
        900: '#78350f'
      },
      danger: {
        50: '#fef2f2',
        100: '#fee2e2',
        500: '#ef4444', // Primary danger color
        600: '#dc2626',
        700: '#b91c1c',
        900: '#7f1d1d'
      },
      info: {
        50: '#eff6ff',
        100: '#dbeafe',
        500: '#3b82f6', // Primary info color
        600: '#2563eb',
        700: '#1d4ed8',
        900: '#1e3a8a'
      }
    },

    // Primary Brand Colors
    primary: {
      50: '#f8fafc',
      100: '#f1f5f9',
      200: '#e2e8f0',
      300: '#cbd5e1',
      400: '#94a3b8',
      500: '#64748b', // Primary brand color
      600: '#475569',
      700: '#334155',
      800: '#1e293b',
      900: '#0f172a'
    },

    // Neutral Scale (for text, backgrounds, borders)
    neutral: {
      0: '#ffffff',
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
      1000: '#000000'
    },

    // Health Score Colors (from mockups)
    health: {
      excellent: '#10b981', // 85%+ (green)
      good: '#f59e0b',      // 70-84% (yellow/amber)
      poor: '#ef4444'       // <70% (red)
    },

    // Status Colors
    status: {
      online: '#10b981',
      offline: '#6b7280',
      pending: '#f59e0b',
      error: '#ef4444',
      processing: '#3b82f6'
    }
  },

  /**
   * TYPOGRAPHY SYSTEM
   * Professional font hierarchy with accessibility considerations
   */
  typography: {
    fontFamily: {
      sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      dyslexic: ['OpenDyslexic', 'Comic Sans MS', 'sans-serif'] // Accessibility option
    },

    fontSize: {
      xs: ['0.75rem', { lineHeight: '1rem' }],      // 12px
      sm: ['0.875rem', { lineHeight: '1.25rem' }],  // 14px
      base: ['1rem', { lineHeight: '1.5rem' }],     // 16px (body text)
      lg: ['1.125rem', { lineHeight: '1.75rem' }],  // 18px
      xl: ['1.25rem', { lineHeight: '1.75rem' }],   // 20px
      '2xl': ['1.5rem', { lineHeight: '2rem' }],    // 24px (headings)
      '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 30px
      '4xl': ['2.25rem', { lineHeight: '2.5rem' }],   // 36px
      '5xl': ['3rem', { lineHeight: '1' }]            // 48px (hero text)
    },

    fontWeight: {
      normal: '400',
      medium: '500',
      semibold: '600',
      bold: '700',
      extrabold: '800'
    },

    lineHeight: {
      tight: '1.25',
      normal: '1.5',  // Default for accessibility
      relaxed: '1.625',
      loose: '2'
    },

    letterSpacing: {
      tight: '-0.025em',
      normal: '0em',
      wide: '0.025em'
    }
  },

  /**
   * SPACING SYSTEM
   * 8px base grid system for consistent layouts
   */
  spacing: {
    0: '0rem',
    0.5: '0.125rem', // 2px
    1: '0.25rem',    // 4px
    1.5: '0.375rem', // 6px
    2: '0.5rem',     // 8px (base unit)
    2.5: '0.625rem', // 10px
    3: '0.75rem',    // 12px
    3.5: '0.875rem', // 14px
    4: '1rem',       // 16px
    5: '1.25rem',    // 20px
    6: '1.5rem',     // 24px
    7: '1.75rem',    // 28px
    8: '2rem',       // 32px
    9: '2.25rem',    // 36px
    10: '2.5rem',    // 40px
    11: '2.75rem',   // 44px
    12: '3rem',      // 48px
    14: '3.5rem',    // 56px
    16: '4rem',      // 64px
    20: '5rem',      // 80px
    24: '6rem',      // 96px
    28: '7rem',      // 112px
    32: '8rem',      // 128px
    36: '9rem',      // 144px
    40: '10rem',     // 160px
    44: '11rem',     // 176px
    48: '12rem',     // 192px
    52: '13rem',     // 208px
    56: '14rem',     // 224px
    60: '15rem',     // 240px
    64: '16rem',     // 256px
    72: '18rem',     // 288px
    80: '20rem',     // 320px
    96: '24rem'      // 384px
  },

  /**
   * COMPONENT SIZES
   * Standardized sizing for UI components
   */
  components: {
    button: {
      height: {
        sm: '2rem',    // 32px
        md: '2.5rem',  // 40px (default)
        lg: '3rem',    // 48px
        xl: '3.5rem'   // 56px
      },
      padding: {
        sm: '0.5rem 0.75rem',
        md: '0.625rem 1rem',
        lg: '0.75rem 1.25rem',
        xl: '1rem 1.5rem'
      },
      borderRadius: {
        sm: '0.25rem',
        md: '0.375rem',
        lg: '0.5rem',
        xl: '0.75rem'
      }
    },

    input: {
      height: {
        sm: '2rem',
        md: '2.5rem',
        lg: '3rem'
      },
      padding: {
        sm: '0.5rem 0.75rem',
        md: '0.625rem 0.875rem',
        lg: '0.75rem 1rem'
      }
    },

    card: {
      padding: {
        sm: '1rem',
        md: '1.5rem',
        lg: '2rem',
        xl: '2.5rem'
      },
      borderRadius: {
        sm: '0.5rem',
        md: '0.75rem',
        lg: '1rem'
      }
    },

    modal: {
      width: {
        sm: '24rem',    // 384px
        md: '32rem',    // 512px
        lg: '48rem',    // 768px
        xl: '64rem',    // 1024px
        full: '90vw'
      },
      maxHeight: '90vh',
      borderRadius: '0.75rem'
    }
  },

  /**
   * RESPONSIVE BREAKPOINTS
   * Mobile-first responsive design breakpoints
   */
  breakpoints: {
    mobile: '375px',   // Mobile phones
    tablet: '768px',   // Tablets
    desktop: '1024px', // Laptops
    wide: '1280px',    // Large screens
    ultrawide: '1536px' // Ultra-wide displays
  },

  /**
   * MOTION DESIGN SYSTEM
   * Animation timing and easing functions from mockups
   */
  motion: {
    // Timing Standards (from motion design guidelines)
    duration: {
      instant: '0ms',
      micro: '100ms',    // Hover, focus states
      fast: '150ms',     // Button highlights, checkbox animations
      normal: '200ms',   // Tab transitions, tooltips
      medium: '300ms',   // Modal enter/exit, notifications
      slow: '400ms',     // Complex animations, graph rendering
      slower: '500ms',   // Page transitions
      slowest: '800ms'   // Complex animations
    },

    // Easing Functions (from CSS specifications)
    easing: {
      linear: 'linear',
      ease: 'ease',
      easeIn: 'ease-in',
      easeOut: 'ease-out',
      easeInOut: 'ease-in-out',
      // Custom easing functions from mockups
      standard: 'cubic-bezier(0.4, 0, 0.2, 1)',      // Standard animations
      decelerate: 'cubic-bezier(0, 0, 0.2, 1)',      // Entering elements
      accelerate: 'cubic-bezier(0.4, 0, 1, 1)',      // Exiting elements
      spring: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)' // Playful elements
    },

    // Component-specific animations
    components: {
      button: {
        hover: {
          scale: '1.05',
          duration: '150ms',
          easing: 'ease'
        },
        active: {
          scale: '0.95',
          duration: '100ms',
          easing: 'ease'
        }
      },
      modal: {
        enter: {
          scale: { from: '0.95', to: '1' },
          opacity: { from: '0', to: '1' },
          duration: '300ms',
          easing: 'cubic-bezier(0, 0, 0.2, 1)'
        },
        exit: {
          scale: { from: '1', to: '0.95' },
          opacity: { from: '1', to: '0' },
          duration: '200ms',
          easing: 'cubic-bezier(0.4, 0, 1, 1)'
        }
      },
      tooltip: {
        show: {
          opacity: { from: '0', to: '1' },
          transform: { from: 'translateY(5px)', to: 'translateY(0)' },
          duration: '200ms',
          easing: 'cubic-bezier(0, 0, 0.2, 1)',
          delay: '500ms'
        },
        hide: {
          opacity: { from: '1', to: '0' },
          duration: '150ms',
          easing: 'cubic-bezier(0.4, 0, 1, 1)',
          delay: '0ms'
        }
      },
      progressBar: {
        fill: {
          duration: '500ms',
          easing: 'cubic-bezier(0.4, 0, 0.2, 1)'
        },
        indeterminate: {
          duration: '1500ms',
          easing: 'linear',
          iteration: 'infinite'
        }
      },
      skeleton: {
        shimmer: {
          duration: '1500ms',
          easing: 'linear',
          iteration: 'infinite'
        },
        pulse: {
          duration: '1000ms',
          easing: 'ease-in-out',
          iteration: 'infinite'
        }
      }
    }
  },

  /**
   * ACCESSIBILITY STANDARDS
   * WCAG 2.1 AA compliance tokens
   */
  accessibility: {
    // Contrast Ratios (WCAG 2.1 AA requirement: 4.5:1 for normal text)
    contrast: {
      minimum: '4.5:1',  // AA standard
      enhanced: '7:1'    // AAA standard
    },

    // Focus Indicators
    focus: {
      outline: {
        width: '2px',
        style: 'solid',
        color: '#3b82f6', // Info blue
        offset: '2px'
      },
      ring: {
        width: '3px',
        color: 'rgba(59, 130, 246, 0.5)',
        borderRadius: '0.375rem'
      }
    },

    // Minimum Touch Targets (44px minimum)
    touchTarget: {
      minimum: '44px',
      recommended: '48px'
    },

    // Animation Preferences
    reducedMotion: {
      // Applied when user prefers reduced motion
      duration: '0.01ms',
      iteration: '1'
    }
  },

  /**
   * ELEVATION & SHADOWS
   * Consistent shadow system for depth
   */
  elevation: {
    none: 'none',
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    '2xl': '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    inner: 'inset 0 2px 4px 0 rgba(0, 0, 0, 0.06)'
  },

  /**
   * BORDER RADIUS
   * Consistent border radius system
   */
  borderRadius: {
    none: '0',
    xs: '0.125rem',   // 2px
    sm: '0.25rem',    // 4px
    md: '0.375rem',   // 6px (default)
    lg: '0.5rem',     // 8px
    xl: '0.75rem',    // 12px
    '2xl': '1rem',    // 16px
    '3xl': '1.5rem',  // 24px
    full: '9999px'    // Pill shape
  },

  /**
   * Z-INDEX SCALE
   * Consistent layering system
   */
  zIndex: {
    auto: 'auto',
    0: '0',
    10: '10',         // Regular content
    20: '20',         // Dropdowns
    30: '30',         // Sticky headers
    40: '40',         // Fixed elements
    50: '50',         // Modals/overlays
    tooltip: '60',    // Tooltips
    popover: '70',    // Popovers
    modal: '80',      // Modal dialogs
    notification: '90', // Toast notifications
    max: '999'        // Emergency high priority
  }
} as const;

/**
 * THEME VARIANTS
 * Light and dark theme color mappings
 */
export const themes = {
  light: {
    background: {
      primary: designTokens.colors.neutral[0],      // Pure white
      secondary: designTokens.colors.neutral[50],   // Off-white
      tertiary: designTokens.colors.neutral[100]    // Light gray
    },
    text: {
      primary: designTokens.colors.neutral[900],    // Near black
      secondary: designTokens.colors.neutral[700],  // Dark gray
      tertiary: designTokens.colors.neutral[500],   // Medium gray
      inverse: designTokens.colors.neutral[0]       // White (on dark backgrounds)
    },
    border: {
      primary: designTokens.colors.neutral[200],    // Light border
      secondary: designTokens.colors.neutral[300],  // Medium border
      strong: designTokens.colors.neutral[400]      // Strong border
    }
  },
  dark: {
    background: {
      primary: designTokens.colors.neutral[900],    // Dark background
      secondary: designTokens.colors.neutral[800],  // Darker background
      tertiary: designTokens.colors.neutral[700]    // Medium dark
    },
    text: {
      primary: designTokens.colors.neutral[100],    // Light text
      secondary: designTokens.colors.neutral[300],  // Medium light
      tertiary: designTokens.colors.neutral[400],   // Medium text
      inverse: designTokens.colors.neutral[900]     // Dark (on light backgrounds)
    },
    border: {
      primary: designTokens.colors.neutral[700],    // Dark border
      secondary: designTokens.colors.neutral[600],  // Medium border
      strong: designTokens.colors.neutral[500]      // Strong border
    }
  },
  highContrast: {
    // High contrast theme for accessibility
    background: {
      primary: designTokens.colors.neutral[1000],   // Pure black
      secondary: designTokens.colors.neutral[900],  // Near black
      tertiary: designTokens.colors.neutral[800]    // Dark gray
    },
    text: {
      primary: designTokens.colors.neutral[0],      // Pure white
      secondary: designTokens.colors.neutral[100],  // Near white
      tertiary: designTokens.colors.neutral[200],   // Light gray
      inverse: designTokens.colors.neutral[1000]    // Black
    },
    border: {
      primary: designTokens.colors.neutral[0],      // White border
      secondary: designTokens.colors.neutral[300],  // Light border
      strong: designTokens.colors.neutral[0]        // White border
    }
  }
} as const;

/**
 * TYPE DEFINITIONS
 * TypeScript types for design tokens
 */
export type DesignTokens = typeof designTokens;
export type ColorPalette = typeof designTokens.colors;
export type Typography = typeof designTokens.typography;
export type Spacing = typeof designTokens.spacing;
export type Motion = typeof designTokens.motion;
export type Theme = typeof themes.light;
export type ThemeMode = keyof typeof themes;

// Export individual token categories for easier imports
export const { colors, typography, spacing, motion, accessibility, elevation, borderRadius, zIndex } = designTokens;
export { designTokens as tokens };

// Default export
export default designTokens;