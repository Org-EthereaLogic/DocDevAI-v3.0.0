/**
 * Delight Themes - Playful color transitions and theme variations
 * 
 * This module provides delightful theme utilities:
 * - Smooth color transitions between themes
 * - Seasonal and contextual themes
 * - Achievement-based color schemes
 * - Animated gradients and color shifts
 * - Accessibility-friendly theme options
 */

import { createTheme, Theme } from '@mui/material/styles';
import { keyframes } from '@mui/material';

/**
 * Animated gradient configurations
 */
export const animatedGradients = {
  // Aurora borealis effect
  aurora: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #fccb90 75%, #667eea 100%)',
    backgroundSize: '400% 400%',
    animation: 'gradientShift 15s ease infinite',
  },
  
  // Sunset gradient
  sunset: {
    background: 'linear-gradient(135deg, #fa709a 0%, #fee140 50%, #fa709a 100%)',
    backgroundSize: '200% 200%',
    animation: 'gradientShift 10s ease infinite',
  },
  
  // Ocean waves
  ocean: {
    background: 'linear-gradient(135deg, #667eea 0%, #66a6ff 50%, #89f7fe 100%)',
    backgroundSize: '200% 200%',
    animation: 'gradientShift 8s ease infinite',
  },
  
  // Success celebration
  success: {
    background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 50%, #11998e 100%)',
    backgroundSize: '200% 200%',
    animation: 'gradientPulse 3s ease infinite',
  },
  
  // Energy boost
  energy: {
    background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 50%, #f093fb 100%)',
    backgroundSize: '200% 200%',
    animation: 'gradientShift 5s ease infinite',
  },
  
  // Calm productivity
  calm: {
    background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 50%, #4facfe 100%)',
    backgroundSize: '200% 200%',
    animation: 'gradientShift 20s ease infinite',
  },
};

/**
 * Gradient animation keyframes
 */
export const gradientKeyframes = keyframes`
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
`;

export const gradientPulseKeyframes = keyframes`
  0%, 100% {
    background-position: 0% 50%;
    filter: brightness(1);
  }
  50% {
    background-position: 100% 50%;
    filter: brightness(1.1);
  }
`;

/**
 * Seasonal theme configurations
 */
export const seasonalThemes = {
  spring: {
    primary: '#4caf50',
    secondary: '#ff9800',
    accent: '#e91e63',
    background: 'linear-gradient(135deg, #e3ffe7 0%, #d9e7ff 100%)',
    particles: ['🌸', '🌺', '🌻', '🦋'],
  },
  
  summer: {
    primary: '#2196f3',
    secondary: '#ffc107',
    accent: '#ff5722',
    background: 'linear-gradient(135deg, #fff5e1 0%, #ffe1cc 100%)',
    particles: ['☀️', '🏖️', '🌊', '🍉'],
  },
  
  autumn: {
    primary: '#ff6f00',
    secondary: '#8d6e63',
    accent: '#d84315',
    background: 'linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%)',
    particles: ['🍂', '🍁', '🎃', '🌰'],
  },
  
  winter: {
    primary: '#3f51b5',
    secondary: '#00bcd4',
    accent: '#9c27b0',
    background: 'linear-gradient(135deg, #e6f2ff 0%, #cfe9ff 100%)',
    particles: ['❄️', '⛄', '🎿', '☃️'],
  },
};

/**
 * Achievement-based color schemes
 */
export const achievementColors = {
  bronze: {
    primary: '#cd7f32',
    glow: 'rgba(205, 127, 50, 0.4)',
    gradient: 'linear-gradient(135deg, #cd7f32, #b87333)',
  },
  
  silver: {
    primary: '#c0c0c0',
    glow: 'rgba(192, 192, 192, 0.4)',
    gradient: 'linear-gradient(135deg, #c0c0c0, #b8b8b8)',
  },
  
  gold: {
    primary: '#ffd700',
    glow: 'rgba(255, 215, 0, 0.4)',
    gradient: 'linear-gradient(135deg, #ffd700, #ffed4e)',
  },
  
  platinum: {
    primary: '#e5e4e2',
    glow: 'rgba(229, 228, 226, 0.5)',
    gradient: 'linear-gradient(135deg, #e5e4e2, #ffffff)',
  },
  
  diamond: {
    primary: '#b9f2ff',
    glow: 'rgba(185, 242, 255, 0.6)',
    gradient: 'linear-gradient(135deg, #b9f2ff, #ffffff, #b9f2ff)',
  },
};

/**
 * Mood-based color transitions
 */
export const moodTransitions = {
  productive: {
    colors: ['#4caf50', '#8bc34a', '#cddc39'],
    duration: '0.5s',
    easing: 'ease-in-out',
  },
  
  focused: {
    colors: ['#2196f3', '#03a9f4', '#00bcd4'],
    duration: '0.6s',
    easing: 'cubic-bezier(0.4, 0, 0.2, 1)',
  },
  
  creative: {
    colors: ['#9c27b0', '#e91e63', '#f44336'],
    duration: '0.8s',
    easing: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  },
  
  relaxed: {
    colors: ['#00bcd4', '#009688', '#4caf50'],
    duration: '1s',
    easing: 'ease-out',
  },
  
  excited: {
    colors: ['#ff5722', '#ff9800', '#ffc107'],
    duration: '0.3s',
    easing: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
};

/**
 * Theme transition utilities
 */
export const themeTransitions = {
  // Smooth color transition
  smoothTransition: (property: string = 'all', duration: string = '0.3s') => ({
    transition: `${property} ${duration} cubic-bezier(0.4, 0, 0.2, 1)`,
  }),
  
  // Fade transition between themes
  fadeTransition: {
    entering: { opacity: 0 },
    entered: { opacity: 1, transition: 'opacity 0.5s ease-in-out' },
    exiting: { opacity: 0, transition: 'opacity 0.3s ease-in-out' },
  },
  
  // Slide transition for theme change
  slideTransition: {
    entering: { transform: 'translateX(100%)', opacity: 0 },
    entered: { 
      transform: 'translateX(0)', 
      opacity: 1,
      transition: 'all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)',
    },
    exiting: { 
      transform: 'translateX(-100%)', 
      opacity: 0,
      transition: 'all 0.3s ease-in-out',
    },
  },
};

/**
 * Accessibility-friendly theme options
 */
export const accessibilityThemes = {
  highContrast: {
    palette: {
      mode: 'light' as const,
      primary: { main: '#000000' },
      secondary: { main: '#0066cc' },
      background: {
        default: '#ffffff',
        paper: '#ffffff',
      },
      text: {
        primary: '#000000',
        secondary: '#000000',
      },
    },
    typography: {
      allVariants: {
        color: '#000000',
        fontWeight: 500,
      },
    },
  },
  
  reducedMotion: {
    transitions: {
      duration: {
        shortest: 0,
        shorter: 0,
        short: 0,
        standard: 0,
        complex: 0,
        enteringScreen: 0,
        leavingScreen: 0,
      },
    },
  },
  
  largeText: {
    typography: {
      fontSize: 18,
      h1: { fontSize: '3.5rem' },
      h2: { fontSize: '2.75rem' },
      h3: { fontSize: '2.25rem' },
      h4: { fontSize: '1.75rem' },
      h5: { fontSize: '1.5rem' },
      h6: { fontSize: '1.25rem' },
      body1: { fontSize: '1.125rem' },
      body2: { fontSize: '1rem' },
    },
  },
  
  colorBlindSafe: {
    palette: {
      primary: { main: '#0066cc' },
      secondary: { main: '#ff9900' },
      error: { main: '#cc0000' },
      warning: { main: '#ffcc00' },
      info: { main: '#0099cc' },
      success: { main: '#339900' },
    },
  },
};

/**
 * Dynamic color utilities
 */
export const colorUtils = {
  // Generate rainbow effect
  rainbow: (duration: number = 5) => ({
    animation: `rainbowShift ${duration}s linear infinite`,
    '@keyframes rainbowShift': {
      '0%': { filter: 'hue-rotate(0deg)' },
      '100%': { filter: 'hue-rotate(360deg)' },
    },
  }),
  
  // Breathing glow effect
  breathingGlow: (color: string, intensity: number = 20) => ({
    animation: 'breathingGlow 3s ease-in-out infinite',
    '@keyframes breathingGlow': {
      '0%, 100%': { 
        boxShadow: `0 0 ${intensity}px ${color}40`,
      },
      '50%': { 
        boxShadow: `0 0 ${intensity * 2}px ${color}60`,
      },
    },
  }),
  
  // Color morphing
  colorMorph: (colors: string[], duration: number = 5) => ({
    animation: `colorMorph ${duration}s ease-in-out infinite`,
    '@keyframes colorMorph': colors.reduce((acc, color, index) => ({
      ...acc,
      [`${(index * 100) / colors.length}%`]: { 
        backgroundColor: color,
      },
    }), {}),
  }),
  
  // Shimmer effect
  shimmer: (baseColor: string, shimmerColor: string) => ({
    background: `linear-gradient(
      90deg,
      ${baseColor} 0%,
      ${shimmerColor} 50%,
      ${baseColor} 100%
    )`,
    backgroundSize: '200% 100%',
    animation: 'shimmer 2s infinite',
    '@keyframes shimmer': {
      '0%': { backgroundPosition: '200% 0' },
      '100%': { backgroundPosition: '-200% 0' },
    },
  }),
};

/**
 * Special effect themes
 */
export const specialEffects = {
  neon: {
    textShadow: '0 0 10px currentColor, 0 0 20px currentColor, 0 0 30px currentColor',
    filter: 'brightness(1.2) contrast(1.2)',
  },
  
  glassmorphism: {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    border: '1px solid rgba(255, 255, 255, 0.2)',
  },
  
  holographic: {
    background: 'linear-gradient(135deg, #ff0080, #ff8c00, #40e0d0, #ff0080)',
    backgroundSize: '300% 300%',
    animation: 'holographic 3s ease infinite',
    '@keyframes holographic': {
      '0%': { backgroundPosition: '0% 50%' },
      '50%': { backgroundPosition: '100% 50%' },
      '100%': { backgroundPosition: '0% 50%' },
    },
  },
  
  retro: {
    textShadow: '3px 3px 0 #ff00ff, 6px 6px 0 #00ffff',
    transform: 'perspective(500px) rotateY(-5deg)',
  },
  
  matrix: {
    color: '#00ff00',
    textShadow: '0 0 5px #00ff00',
    fontFamily: 'monospace',
    background: 'black',
  },
};

/**
 * Theme builder utility
 */
export const buildDelightTheme = (
  baseTheme: Theme,
  options: {
    mood?: keyof typeof moodTransitions;
    season?: keyof typeof seasonalThemes;
    achievement?: keyof typeof achievementColors;
    specialEffect?: keyof typeof specialEffects;
    accessibility?: keyof typeof accessibilityThemes;
  }
): Theme => {
  let theme = { ...baseTheme };
  
  // Apply mood colors
  if (options.mood) {
    const mood = moodTransitions[options.mood];
    theme.palette.primary.main = mood.colors[0];
    theme.palette.secondary.main = mood.colors[1];
  }
  
  // Apply seasonal theme
  if (options.season) {
    const season = seasonalThemes[options.season];
    theme.palette.primary.main = season.primary;
    theme.palette.secondary.main = season.secondary;
  }
  
  // Apply achievement colors
  if (options.achievement) {
    const achievement = achievementColors[options.achievement];
    theme.palette.primary.main = achievement.primary;
  }
  
  // Apply accessibility options
  if (options.accessibility) {
    const accessibilityTheme = accessibilityThemes[options.accessibility];
    theme = createTheme(theme, accessibilityTheme);
  }
  
  return createTheme(theme);
};

/**
 * CSS-in-JS style injection for global animations
 */
export const injectGlobalAnimations = () => {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes gradientShift {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    
    @keyframes gradientPulse {
      0%, 100% { 
        background-position: 0% 50%;
        filter: brightness(1);
      }
      50% { 
        background-position: 100% 50%;
        filter: brightness(1.1);
      }
    }
    
    @keyframes rainbowShift {
      0% { filter: hue-rotate(0deg); }
      100% { filter: hue-rotate(360deg); }
    }
    
    @keyframes breathingGlow {
      0%, 100% { opacity: 0.7; }
      50% { opacity: 1; }
    }
    
    @keyframes holographic {
      0% { background-position: 0% 50%; }
      50% { background-position: 100% 50%; }
      100% { background-position: 0% 50%; }
    }
    
    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
    
    @keyframes colorMorph {
      0%, 100% { filter: hue-rotate(0deg); }
      25% { filter: hue-rotate(90deg); }
      50% { filter: hue-rotate(180deg); }
      75% { filter: hue-rotate(270deg); }
    }
  `;
  document.head.appendChild(style);
};

export default {
  animatedGradients,
  seasonalThemes,
  achievementColors,
  moodTransitions,
  themeTransitions,
  accessibilityThemes,
  colorUtils,
  specialEffects,
  buildDelightTheme,
  injectGlobalAnimations,
};