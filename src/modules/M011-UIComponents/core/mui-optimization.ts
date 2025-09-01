/**
 * Material-UI Performance Optimizations
 * 
 * Features:
 * - Optimized theme configuration
 * - Minimized CSS-in-JS overhead
 * - Cached styled components
 * - Tree-shaken imports
 * - Production build optimizations
 */

import { createTheme, ThemeOptions, Theme } from '@mui/material/styles';
import { unstable_ClassNameGenerator as ClassNameGenerator } from '@mui/material/className';
import { cache } from '@emotion/css';
import createCache from '@emotion/cache';

/**
 * Configure class name generation for smaller bundle size
 */
ClassNameGenerator.configure((componentName) => {
  // Use shorter class names in production
  if (process.env.NODE_ENV === 'production') {
    const hash = componentName
      .split('')
      .reduce((acc, char) => (acc * 33) ^ char.charCodeAt(0), 5381)
      .toString(36);
    return `m${hash}`;
  }
  return `DevDocAI-${componentName}`;
});

/**
 * Create Emotion cache with optimizations
 */
export const createOptimizedEmotionCache = () => {
  return createCache({
    key: 'mui',
    prepend: true,
    // Optimize for production
    ...(process.env.NODE_ENV === 'production' && {
      stylisPlugins: [],
      speedy: true
    })
  });
};

/**
 * Optimized theme configuration
 */
export const createOptimizedTheme = (options?: ThemeOptions): Theme => {
  return createTheme({
    ...options,
    // Optimize component defaults
    components: {
      ...options?.components,
      
      // Disable ripple in production for better performance
      MuiButtonBase: {
        defaultProps: {
          disableRipple: process.env.NODE_ENV === 'production'
        },
        ...options?.components?.MuiButtonBase
      },
      
      // Optimize Paper elevation
      MuiPaper: {
        defaultProps: {
          elevation: 1 // Lower default elevation
        },
        styleOverrides: {
          root: {
            // Use CSS transitions instead of box-shadow for elevation changes
            transition: 'transform 0.2s ease-in-out',
            '&:hover': {
              transform: 'translateY(-2px)'
            }
          }
        },
        ...options?.components?.MuiPaper
      },
      
      // Optimize Typography
      MuiTypography: {
        styleOverrides: {
          root: {
            // Prevent layout shift with font loading
            fontDisplay: 'swap'
          }
        },
        ...options?.components?.MuiTypography
      },
      
      // Optimize Grid
      MuiGrid: {
        defaultProps: {
          // Use CSS Grid for better performance
          container: true
        },
        ...options?.components?.MuiGrid
      },
      
      // Optimize Skeleton
      MuiSkeleton: {
        defaultProps: {
          animation: 'wave' // More performant than pulse
        },
        ...options?.components?.MuiSkeleton
      }
    },
    
    // Optimize palette
    palette: {
      ...options?.palette,
      mode: options?.palette?.mode || 'light',
      // Reduce color variations for smaller CSS
      ...(process.env.NODE_ENV === 'production' && {
        tonalOffset: 0.1 // Reduce tonal variations
      })
    },
    
    // Optimize typography
    typography: {
      ...options?.typography,
      // Use system fonts for better performance
      fontFamily: [
        '-apple-system',
        'BlinkMacSystemFont',
        '"Segoe UI"',
        'Roboto',
        '"Helvetica Neue"',
        'Arial',
        'sans-serif'
      ].join(','),
      // Reduce font weight variations
      fontWeightLight: 300,
      fontWeightRegular: 400,
      fontWeightMedium: 500,
      fontWeightBold: 700
    },
    
    // Optimize spacing
    spacing: options?.spacing || 8,
    
    // Optimize shape
    shape: {
      ...options?.shape,
      borderRadius: options?.shape?.borderRadius || 4
    },
    
    // Optimize transitions
    transitions: {
      ...options?.transitions,
      // Faster transitions for snappier feel
      duration: {
        shortest: 150,
        shorter: 200,
        short: 250,
        standard: 300,
        complex: 375,
        enteringScreen: 225,
        leavingScreen: 195,
        ...options?.transitions?.duration
      },
      // Use GPU-accelerated properties
      create: (props = ['all'], options = {}) => {
        const {
          duration = 300,
          easing = 'cubic-bezier(0.4, 0, 0.2, 1)',
          delay = 0
        } = options;
        
        const animatedProps = Array.isArray(props) ? props : [props];
        const gpuProps = animatedProps.map(prop => {
          // Convert to GPU-accelerated properties where possible
          if (prop === 'margin' || prop === 'padding') {
            return 'transform';
          }
          return prop;
        });
        
        return gpuProps
          .map(prop => `${prop} ${duration}ms ${easing} ${delay}ms`)
          .join(',');
      }
    }
  });
};

/**
 * Optimized styled component factory
 */
import { styled as muiStyled } from '@mui/material/styles';

const styledCache = new Map<string, any>();

export function optimizedStyled<T extends object>(
  Component: React.ComponentType<T>,
  options?: { name?: string; slot?: string }
) {
  const cacheKey = `${Component.displayName || Component.name}-${options?.name || ''}-${options?.slot || ''}`;
  
  if (styledCache.has(cacheKey)) {
    return styledCache.get(cacheKey);
  }
  
  const StyledComponent = muiStyled(Component, options);
  styledCache.set(cacheKey, StyledComponent);
  
  return StyledComponent;
}

/**
 * Batch DOM updates for Material-UI components
 */
export const batchedUpdates = (callback: () => void): void => {
  if ('requestIdleCallback' in window) {
    requestIdleCallback(callback, { timeout: 16 });
  } else {
    requestAnimationFrame(callback);
  }
};

/**
 * Optimize Material-UI icons imports
 */
export const lazyIcon = (iconName: string) => {
  return import(`@mui/icons-material/${iconName}`).then(module => ({
    default: module.default
  }));
};

/**
 * Performance-optimized theme provider wrapper
 */
import React, { useMemo, PropsWithChildren } from 'react';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { CacheProvider } from '@emotion/react';

interface OptimizedThemeProviderProps extends PropsWithChildren {
  theme?: ThemeOptions;
}

export const OptimizedThemeProvider: React.FC<OptimizedThemeProviderProps> = ({
  children,
  theme
}) => {
  const emotionCache = useMemo(() => createOptimizedEmotionCache(), []);
  const optimizedTheme = useMemo(() => createOptimizedTheme(theme), [theme]);
  
  return (
    <CacheProvider value={emotionCache}>
      <ThemeProvider theme={optimizedTheme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </CacheProvider>
  );
};

/**
 * Hook for lazy loading Material-UI components
 */
export function useLazyMuiComponent<T>(
  loader: () => Promise<{ default: React.ComponentType<T> }>
): React.ComponentType<T> | null {
  const [Component, setComponent] = React.useState<React.ComponentType<T> | null>(null);
  
  React.useEffect(() => {
    loader().then(module => {
      setComponent(() => module.default);
    });
  }, []);
  
  return Component;
}

/**
 * Export optimized imports helper
 */
export const muiOptimizedImports = {
  // Core components - use specific imports
  Box: () => import('@mui/material/Box'),
  Button: () => import('@mui/material/Button'),
  Typography: () => import('@mui/material/Typography'),
  Grid: () => import('@mui/material/Grid'),
  Paper: () => import('@mui/material/Paper'),
  
  // Icons - use specific imports
  RefreshIcon: () => import('@mui/icons-material/Refresh'),
  SettingsIcon: () => import('@mui/icons-material/Settings'),
  AddIcon: () => import('@mui/icons-material/Add'),
  
  // Data display - lazy load
  DataGrid: () => import('@mui/x-data-grid/DataGrid'),
  Charts: () => import('@mui/x-charts')
};