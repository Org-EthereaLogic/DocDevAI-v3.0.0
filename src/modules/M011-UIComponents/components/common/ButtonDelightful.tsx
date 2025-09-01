/**
 * ButtonDelightful - Enhanced button with satisfying micro-interactions
 * 
 * Features:
 * - Multiple hover effects (lift, glow, magnetic)
 * - Click feedback with ripples and morphing
 * - Success/error state celebrations
 * - Loading states with personality
 * - Sound and haptic feedback (optional)
 * - Particle effects for special actions
 */

import React, { useState, useRef, useCallback, MouseEvent } from 'react';
import {
  Button as MuiButton,
  ButtonProps as MuiButtonProps,
  Box,
  CircularProgress,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import { styled, keyframes } from '@mui/material/styles';
import {
  Check as CheckIcon,
  Close as CloseIcon,
  AutoAwesome as SparkleIcon,
} from '@mui/icons-material';

import { 
  delightKeyframes,
  easings,
  feedbackUtils,
  performanceUtils,
  springConfigs,
} from '../../utils/delight-animations';
import { 
  achievementColors,
  colorUtils,
} from '../../utils/delight-themes';

/**
 * Extended button props
 */
interface ButtonDelightfulProps extends Omit<MuiButtonProps, 'variant'> {
  variant?: MuiButtonProps['variant'] | 'gradient' | 'neon' | 'glass';
  hoverEffect?: 'lift' | 'glow' | 'magnetic' | 'pulse' | 'rotate' | 'none';
  clickEffect?: 'ripple' | 'bounce' | 'morph' | 'sparkle' | 'none';
  loading?: boolean;
  success?: boolean;
  error?: boolean;
  showParticles?: boolean;
  enableSound?: boolean;
  enableHaptic?: boolean;
  magneticStrength?: number;
  glowColor?: string;
  gradientColors?: [string, string];
}

/**
 * Ripple animation
 */
const rippleAnimation = keyframes`
  0% {
    transform: scale(0);
    opacity: 1;
  }
  100% {
    transform: scale(4);
    opacity: 0;
  }
`;

/**
 * Success animation
 */
const successAnimation = keyframes`
  0% {
    transform: scale(0) rotate(0deg);
    opacity: 0;
  }
  50% {
    transform: scale(1.2) rotate(180deg);
    opacity: 1;
  }
  100% {
    transform: scale(1) rotate(360deg);
    opacity: 1;
  }
`;

/**
 * Styled button base
 */
const StyledButton = styled(MuiButton, {
  shouldForwardProp: (prop) => 
    !['hoverEffect', 'clickEffect', 'gradientColors', 'glowColor'].includes(prop as string),
})<{
  hoverEffect?: string;
  clickEffect?: string;
  gradientColors?: [string, string];
  glowColor?: string;
}>(({ theme, hoverEffect, glowColor, gradientColors }) => ({
  position: 'relative',
  overflow: 'hidden',
  transition: `all 0.3s ${easings.materialStandard}`,
  ...performanceUtils.gpuAccelerate,
  
  // Hover effects
  ...(hoverEffect === 'lift' && {
    '&:hover': {
      transform: 'translateY(-3px)',
      boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
    },
    '&:active': {
      transform: 'translateY(0)',
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    },
  }),
  
  ...(hoverEffect === 'glow' && {
    '&:hover': {
      boxShadow: `0 0 20px ${glowColor || theme.palette.primary.main}40, 0 0 40px ${glowColor || theme.palette.primary.main}20`,
    },
  }),
  
  ...(hoverEffect === 'pulse' && {
    '&:hover': {
      animation: `${delightKeyframes.pulse} 1s ease-in-out infinite`,
    },
  }),
  
  ...(hoverEffect === 'rotate' && {
    '&:hover': {
      transform: 'rotate(2deg) scale(1.05)',
    },
    '&:active': {
      transform: 'rotate(-2deg) scale(0.95)',
    },
  }),
  
  // Gradient variant
  ...(gradientColors && {
    background: `linear-gradient(135deg, ${gradientColors[0]}, ${gradientColors[1]})`,
    backgroundSize: '200% 200%',
    '&:hover': {
      backgroundPosition: '100% 0',
    },
  }),
}));

/**
 * Glass morphism button
 */
const GlassButton = styled(StyledButton)(({ theme }) => ({
  background: 'rgba(255, 255, 255, 0.1)',
  backdropFilter: 'blur(10px)',
  border: '1px solid rgba(255, 255, 255, 0.2)',
  color: theme.palette.common.white,
  
  '&:hover': {
    background: 'rgba(255, 255, 255, 0.2)',
    backdropFilter: 'blur(15px)',
  },
}));

/**
 * Neon button
 */
const NeonButton = styled(StyledButton)(({ theme }) => ({
  background: 'transparent',
  border: `2px solid ${theme.palette.primary.main}`,
  color: theme.palette.primary.main,
  textShadow: `0 0 10px ${theme.palette.primary.main}`,
  boxShadow: `inset 0 0 10px ${theme.palette.primary.main}20, 0 0 20px ${theme.palette.primary.main}40`,
  
  '&:hover': {
    background: `${theme.palette.primary.main}10`,
    boxShadow: `inset 0 0 20px ${theme.palette.primary.main}40, 0 0 40px ${theme.palette.primary.main}60`,
    textShadow: `0 0 20px ${theme.palette.primary.main}`,
  },
}));

/**
 * Ripple element
 */
const Ripple = styled('span')<{ x: number; y: number; size: number }>(({ x, y, size }) => ({
  position: 'absolute',
  left: x,
  top: y,
  width: size,
  height: size,
  borderRadius: '50%',
  background: 'rgba(255, 255, 255, 0.5)',
  transform: 'scale(0)',
  animation: `${rippleAnimation} 0.6s ease-out`,
  pointerEvents: 'none',
}));

/**
 * Particle element
 */
const Particle = styled('span')<{ delay: number; x: number; y: number }>(({ theme, delay, x, y }) => ({
  position: 'absolute',
  left: '50%',
  top: '50%',
  width: '4px',
  height: '4px',
  borderRadius: '50%',
  background: theme.palette.primary.main,
  transform: `translate(${x}px, ${y}px) scale(0)`,
  animation: `${delightKeyframes.sparkle} 0.8s ${delay}s ease-out`,
  pointerEvents: 'none',
}));

/**
 * Success/Error icon overlay
 */
const StatusIcon = styled(Box)<{ status: 'success' | 'error' }>(({ theme, status }) => ({
  position: 'absolute',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  width: '24px',
  height: '24px',
  borderRadius: '50%',
  background: status === 'success' ? theme.palette.success.main : theme.palette.error.main,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  animation: `${successAnimation} 0.6s ${easings.bouncy}`,
  color: theme.palette.common.white,
}));

/**
 * ButtonDelightful component
 */
const ButtonDelightful: React.FC<ButtonDelightfulProps> = ({
  variant = 'contained',
  hoverEffect = 'lift',
  clickEffect = 'ripple',
  loading = false,
  success = false,
  error = false,
  showParticles = false,
  enableSound = false,
  enableHaptic = true,
  magneticStrength = 0.2,
  glowColor,
  gradientColors,
  children,
  onClick,
  disabled,
  ...props
}) => {
  const theme = useTheme();
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
  
  const buttonRef = useRef<HTMLButtonElement>(null);
  const [ripples, setRipples] = useState<Array<{ x: number; y: number; size: number; id: number }>>([]);
  const [particles, setParticles] = useState<Array<{ x: number; y: number; delay: number; id: number }>>([]);
  const [isHovering, setIsHovering] = useState(false);
  const [magneticOffset, setMagneticOffset] = useState({ x: 0, y: 0 });

  // Handle click with effects
  const handleClick = useCallback((event: MouseEvent<HTMLButtonElement>) => {
    if (disabled || loading) return;
    
    // Create ripple effect
    if (clickEffect === 'ripple' && !prefersReducedMotion) {
      const rect = event.currentTarget.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = event.clientX - rect.left - size / 2;
      const y = event.clientY - rect.top - size / 2;
      
      const newRipple = { x, y, size, id: Date.now() };
      setRipples(prev => [...prev, newRipple]);
      
      setTimeout(() => {
        setRipples(prev => prev.filter(r => r.id !== newRipple.id));
      }, 600);
    }
    
    // Create particle effect
    if ((clickEffect === 'sparkle' || showParticles) && !prefersReducedMotion) {
      const newParticles = Array.from({ length: 8 }, (_, i) => ({
        x: Math.cos((i * Math.PI) / 4) * 30,
        y: Math.sin((i * Math.PI) / 4) * 30,
        delay: i * 0.05,
        id: Date.now() + i,
      }));
      
      setParticles(newParticles);
      
      setTimeout(() => {
        setParticles([]);
      }, 1000);
    }
    
    // Haptic feedback
    if (enableHaptic && !prefersReducedMotion) {
      feedbackUtils.hapticFeedback('light');
    }
    
    // Sound feedback
    if (enableSound && !prefersReducedMotion) {
      feedbackUtils.playSound('click');
    }
    
    // Call original onClick
    if (onClick) {
      onClick(event);
    }
  }, [disabled, loading, clickEffect, showParticles, enableHaptic, enableSound, onClick, prefersReducedMotion]);

  // Handle magnetic hover effect
  const handleMouseMove = useCallback((event: MouseEvent<HTMLButtonElement>) => {
    if (hoverEffect !== 'magnetic' || prefersReducedMotion) return;
    
    const rect = event.currentTarget.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    
    const deltaX = (event.clientX - centerX) * magneticStrength;
    const deltaY = (event.clientY - centerY) * magneticStrength;
    
    setMagneticOffset({ x: deltaX, y: deltaY });
  }, [hoverEffect, magneticStrength, prefersReducedMotion]);

  const handleMouseEnter = () => {
    setIsHovering(true);
    
    if (enableHaptic && !prefersReducedMotion) {
      feedbackUtils.hapticFeedback('light');
    }
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
    setMagneticOffset({ x: 0, y: 0 });
  };

  // Determine which button variant to use
  const getButtonComponent = () => {
    switch (variant) {
      case 'glass':
        return GlassButton;
      case 'neon':
        return NeonButton;
      case 'gradient':
        return StyledButton;
      default:
        return StyledButton;
    }
  };

  const ButtonComponent = getButtonComponent();

  return (
    <ButtonComponent
      ref={buttonRef}
      variant={variant === 'gradient' || variant === 'glass' || variant === 'neon' ? 'contained' : variant}
      hoverEffect={prefersReducedMotion ? 'none' : hoverEffect}
      clickEffect={prefersReducedMotion ? 'none' : clickEffect}
      glowColor={glowColor}
      gradientColors={variant === 'gradient' ? gradientColors : undefined}
      onClick={handleClick}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      disabled={disabled || loading || success || error}
      sx={{
        transform: hoverEffect === 'magnetic' 
          ? `translate(${magneticOffset.x}px, ${magneticOffset.y}px)`
          : undefined,
        transition: hoverEffect === 'magnetic'
          ? `transform 0.1s ${easings.materialStandard}`
          : undefined,
      }}
      {...props}
    >
      {/* Loading state */}
      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={16} color="inherit" />
          Loading...
        </Box>
      )}
      
      {/* Success state */}
      {success && !loading && (
        <>
          <StatusIcon status="success">
            <CheckIcon fontSize="small" />
          </StatusIcon>
          <Box sx={{ opacity: 0 }}>{children}</Box>
        </>
      )}
      
      {/* Error state */}
      {error && !loading && (
        <>
          <StatusIcon status="error">
            <CloseIcon fontSize="small" />
          </StatusIcon>
          <Box sx={{ opacity: 0 }}>{children}</Box>
        </>
      )}
      
      {/* Normal state */}
      {!loading && !success && !error && children}
      
      {/* Hover sparkle effect */}
      {isHovering && showParticles && !prefersReducedMotion && (
        <SparkleIcon
          sx={{
            position: 'absolute',
            top: -8,
            right: -8,
            fontSize: 16,
            color: 'warning.main',
            animation: `${delightKeyframes.sparkle} 1s ease-in-out infinite`,
          }}
        />
      )}
      
      {/* Ripples */}
      {ripples.map(ripple => (
        <Ripple key={ripple.id} {...ripple} />
      ))}
      
      {/* Particles */}
      {particles.map(particle => (
        <Particle key={particle.id} {...particle} />
      ))}
    </ButtonComponent>
  );
};

export default ButtonDelightful;