/**
 * Delight Animations - Reusable micro-interaction utilities
 * 
 * This module provides delightful animation utilities for micro-interactions:
 * - Spring configurations for natural motion
 * - Easing functions for smooth transitions
 * - Animation hooks for React components
 * - Celebration effects and particles
 * - Performance-optimized GPU animations
 */

import { keyframes } from '@mui/material';

/**
 * Spring configurations for natural, physics-based animations
 */
export const springConfigs = {
  // Gentle spring for subtle interactions
  gentle: {
    tension: 280,
    friction: 60,
    mass: 0.7,
  },
  
  // Bouncy spring for playful feedback
  bouncy: {
    tension: 300,
    friction: 10,
    mass: 0.5,
  },
  
  // Snappy spring for quick responses
  snappy: {
    tension: 400,
    friction: 25,
    mass: 0.9,
  },
  
  // Smooth spring for elegant transitions
  smooth: {
    tension: 180,
    friction: 30,
    mass: 1,
  },
  
  // Elastic spring for dramatic effects
  elastic: {
    tension: 200,
    friction: 5,
    mass: 0.4,
  }
};

/**
 * Custom easing functions for delightful motion
 */
export const easings = {
  // Natural easing with slight overshoot
  delightfulEaseOut: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
  
  // Smooth entrance with subtle bounce
  entranceEasing: 'cubic-bezier(0.22, 1.28, 0.36, 1)',
  
  // Quick but smooth exit
  exitEasing: 'cubic-bezier(0.4, 0, 1, 1)',
  
  // Elastic bounce for playful elements
  elasticOut: 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  
  // Smooth curve for data animations
  dataEasing: 'cubic-bezier(0.65, 0, 0.35, 1)',
  
  // Material Design standard easing
  materialStandard: 'cubic-bezier(0.4, 0, 0.2, 1)',
  
  // Emphasized deceleration
  emphasizedDecelerate: 'cubic-bezier(0.05, 0.7, 0.1, 1)',
};

/**
 * Keyframe animations for various micro-interactions
 */
export const delightKeyframes = {
  // Pulse animation for attention
  pulse: keyframes`
    0% {
      transform: scale(1);
      opacity: 1;
    }
    50% {
      transform: scale(1.05);
      opacity: 0.9;
    }
    100% {
      transform: scale(1);
      opacity: 1;
    }
  `,
  
  // Gentle float for idle states
  float: keyframes`
    0%, 100% {
      transform: translateY(0px) rotate(0deg);
    }
    33% {
      transform: translateY(-6px) rotate(-1deg);
    }
    66% {
      transform: translateY(-3px) rotate(1deg);
    }
  `,
  
  // Wiggle for playful feedback
  wiggle: keyframes`
    0%, 100% {
      transform: rotate(0deg);
    }
    25% {
      transform: rotate(-3deg);
    }
    75% {
      transform: rotate(3deg);
    }
  `,
  
  // Slide up entrance
  slideUp: keyframes`
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  `,
  
  // Scale entrance with bounce
  bounceIn: keyframes`
    0% {
      opacity: 0;
      transform: scale(0.3);
    }
    50% {
      opacity: 1;
      transform: scale(1.05);
    }
    70% {
      transform: scale(0.95);
    }
    100% {
      transform: scale(1);
    }
  `,
  
  // Shimmer effect for loading
  shimmer: keyframes`
    0% {
      background-position: -1000px 0;
    }
    100% {
      background-position: 1000px 0;
    }
  `,
  
  // Ripple effect for clicks
  ripple: keyframes`
    0% {
      transform: scale(0);
      opacity: 1;
    }
    100% {
      transform: scale(4);
      opacity: 0;
    }
  `,
  
  // Celebration confetti fall
  confettiFall: keyframes`
    0% {
      transform: translateY(-100vh) rotate(0deg);
      opacity: 1;
    }
    100% {
      transform: translateY(100vh) rotate(720deg);
      opacity: 0;
    }
  `,
  
  // Success checkmark draw
  checkmarkDraw: keyframes`
    0% {
      stroke-dashoffset: 100;
    }
    100% {
      stroke-dashoffset: 0;
    }
  `,
  
  // Sparkle effect
  sparkle: keyframes`
    0%, 100% {
      opacity: 0;
      transform: scale(0) rotate(0deg);
    }
    50% {
      opacity: 1;
      transform: scale(1) rotate(180deg);
    }
  `
};

/**
 * Stagger configurations for sequential animations
 */
export const staggerConfigs = {
  // Fast stagger for lists
  fast: {
    delay: 0.03,
    duration: 0.3,
  },
  
  // Standard stagger for cards
  standard: {
    delay: 0.05,
    duration: 0.4,
  },
  
  // Slow stagger for dramatic reveals
  slow: {
    delay: 0.08,
    duration: 0.5,
  },
  
  // Cascade effect
  cascade: {
    delay: 0.02,
    duration: 0.6,
    easing: easings.entranceEasing,
  },
};

/**
 * Animation variants for different interaction states
 */
export const interactionVariants = {
  // Button interactions
  button: {
    rest: {
      scale: 1,
      rotate: 0,
    },
    hover: {
      scale: 1.05,
      rotate: 0,
      transition: {
        type: 'spring',
        ...springConfigs.gentle,
      },
    },
    tap: {
      scale: 0.95,
      rotate: 0,
    },
    success: {
      scale: [1, 1.2, 1],
      rotate: [0, 10, -10, 0],
    },
  },
  
  // Card interactions
  card: {
    rest: {
      y: 0,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    },
    hover: {
      y: -4,
      boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
      transition: {
        type: 'spring',
        ...springConfigs.smooth,
      },
    },
    tap: {
      y: 0,
      boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
    },
  },
  
  // Icon interactions
  icon: {
    rest: {
      rotate: 0,
    },
    hover: {
      rotate: 15,
      transition: {
        type: 'spring',
        ...springConfigs.bouncy,
      },
    },
    tap: {
      rotate: -15,
    },
    spin: {
      rotate: 360,
      transition: {
        duration: 0.6,
        ease: easings.materialStandard,
      },
    },
  },
};

/**
 * Performance-optimized animation utilities
 */
export const performanceUtils = {
  // Use GPU acceleration
  gpuAccelerate: {
    transform: 'translateZ(0)',
    willChange: 'transform',
    backfaceVisibility: 'hidden',
    perspective: 1000,
  },
  
  // Reduce motion for accessibility
  reduceMotion: (prefersReducedMotion: boolean) => ({
    transition: prefersReducedMotion ? 'none' : undefined,
    animation: prefersReducedMotion ? 'none' : undefined,
  }),
  
  // Optimize for 60fps
  optimize60fps: {
    transform: 'translateZ(0)',
    willChange: 'auto',
  },
};

/**
 * Celebration effect configurations
 */
export const celebrationEffects = {
  confetti: {
    particleCount: 100,
    spread: 70,
    origin: { y: 0.6 },
    colors: ['#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3'],
  },
  
  fireworks: {
    particleCount: 30,
    spread: 360,
    ticks: 60,
    origin: { x: 0.5, y: 0.5 },
    gravity: 0.5,
  },
  
  stars: {
    particleCount: 20,
    shapes: ['star'],
    spread: 60,
    scalar: 1.2,
  },
  
  achievement: {
    particleCount: 50,
    startVelocity: 30,
    spread: 360,
    ticks: 60,
    shapes: ['circle', 'square'],
    colors: ['#ffd700', '#ffed4e', '#fff'],
  },
};

/**
 * Hover effect utilities
 */
export const hoverEffects = {
  // Glow effect on hover
  glow: (color: string = '#2196f3') => ({
    '&:hover': {
      boxShadow: `0 0 20px ${color}40, 0 0 40px ${color}20`,
      transition: 'box-shadow 0.3s ease',
    },
  }),
  
  // Lift effect on hover
  lift: {
    '&:hover': {
      transform: 'translateY(-4px)',
      boxShadow: '0 12px 24px rgba(0,0,0,0.15)',
      transition: 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)',
    },
  },
  
  // Tilt effect on hover
  tilt: {
    '&:hover': {
      transform: 'perspective(1000px) rotateX(-10deg) rotateY(10deg)',
      transition: 'transform 0.3s ease',
    },
  },
  
  // Color shift on hover
  colorShift: (fromColor: string, toColor: string) => ({
    background: `linear-gradient(135deg, ${fromColor}, ${toColor})`,
    backgroundSize: '200% 200%',
    animation: 'gradientShift 3s ease infinite',
    '&:hover': {
      animationDuration: '1s',
    },
  }),
};

/**
 * Loading animation utilities
 */
export const loadingAnimations = {
  // Dots animation
  dots: {
    animation: 'dots 1.4s infinite ease-in-out both',
    '@keyframes dots': {
      '0%, 80%, 100%': {
        transform: 'scale(0)',
      },
      '40%': {
        transform: 'scale(1)',
      },
    },
  },
  
  // Skeleton pulse
  skeleton: {
    background: 'linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%)',
    backgroundSize: '200% 100%',
    animation: `${delightKeyframes.shimmer} 1.5s infinite`,
  },
  
  // Progress bar wave
  progressWave: {
    background: 'linear-gradient(45deg, transparent 33%, rgba(255,255,255,0.2) 33%, rgba(255,255,255,0.2) 66%, transparent 66%)',
    backgroundSize: '20px 40px',
    animation: 'progressWave 1s linear infinite',
    '@keyframes progressWave': {
      '0%': {
        backgroundPosition: '0 0',
      },
      '100%': {
        backgroundPosition: '20px 40px',
      },
    },
  },
};

/**
 * Transition utilities for smooth state changes
 */
export const transitions = {
  // Page transition
  page: {
    entering: {
      opacity: 0,
      transform: 'translateX(20px)',
    },
    entered: {
      opacity: 1,
      transform: 'translateX(0)',
      transition: `all 0.3s ${easings.materialStandard}`,
    },
    exiting: {
      opacity: 0,
      transform: 'translateX(-20px)',
      transition: `all 0.2s ${easings.exitEasing}`,
    },
  },
  
  // Modal transition
  modal: {
    entering: {
      opacity: 0,
      transform: 'scale(0.9) translateY(20px)',
    },
    entered: {
      opacity: 1,
      transform: 'scale(1) translateY(0)',
      transition: `all 0.3s ${easings.entranceEasing}`,
    },
    exiting: {
      opacity: 0,
      transform: 'scale(0.9) translateY(20px)',
      transition: `all 0.2s ${easings.exitEasing}`,
    },
  },
  
  // Collapse transition
  collapse: {
    entering: {
      height: 0,
      opacity: 0,
    },
    entered: {
      height: 'auto',
      opacity: 1,
      transition: `all 0.3s ${easings.materialStandard}`,
    },
    exiting: {
      height: 0,
      opacity: 0,
      transition: `all 0.2s ${easings.exitEasing}`,
    },
  },
};

/**
 * Interactive feedback utilities
 */
export const feedbackUtils = {
  // Ripple effect on click
  createRipple: (event: React.MouseEvent<HTMLElement>) => {
    const button = event.currentTarget;
    const rect = button.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    return {
      size,
      x,
      y,
      animation: `${delightKeyframes.ripple} 0.6s ease-out`,
    };
  },
  
  // Haptic feedback simulation
  hapticFeedback: (intensity: 'light' | 'medium' | 'heavy' = 'medium') => {
    const durations = { light: 10, medium: 20, heavy: 30 };
    if ('vibrate' in navigator) {
      navigator.vibrate(durations[intensity]);
    }
  },
  
  // Sound feedback (optional)
  playSound: (type: 'click' | 'success' | 'error' | 'notification') => {
    // Only play if sounds are enabled in settings
    const sounds = {
      click: '/sounds/click.mp3',
      success: '/sounds/success.mp3',
      error: '/sounds/error.mp3',
      notification: '/sounds/notification.mp3',
    };
    
    // Implementation would check user preferences
    // and play the appropriate sound
  },
};

/**
 * Animation hook for React components
 */
export const useDelightAnimation = (
  type: keyof typeof interactionVariants,
  options?: {
    reduceMotion?: boolean;
    delay?: number;
    duration?: number;
  }
) => {
  const prefersReducedMotion = options?.reduceMotion ?? false;
  
  if (prefersReducedMotion) {
    return {
      initial: {},
      animate: {},
      exit: {},
      whileHover: {},
      whileTap: {},
    };
  }
  
  const variants = interactionVariants[type];
  
  return {
    initial: variants.rest,
    animate: variants.rest,
    whileHover: variants.hover,
    whileTap: variants.tap,
    transition: {
      delay: options?.delay ?? 0,
      duration: options?.duration ?? 0.3,
    },
  };
};

export default {
  springConfigs,
  easings,
  delightKeyframes,
  staggerConfigs,
  interactionVariants,
  performanceUtils,
  celebrationEffects,
  hoverEffects,
  loadingAnimations,
  transitions,
  feedbackUtils,
  useDelightAnimation,
};