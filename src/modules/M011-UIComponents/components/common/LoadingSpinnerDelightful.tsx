/**
 * LoadingSpinnerDelightful - Enhanced loading spinner with personality
 * 
 * Features:
 * - Multiple loading animation styles
 * - Playful loading messages
 * - Progress indicators with character
 * - Smooth transitions between states
 * - Fun facts during long loads
 * - Accessibility support maintained
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  CircularProgress,
  Typography,
  useTheme,
  LinearProgress,
  Fade,
  useMediaQuery,
} from '@mui/material';
import { styled, keyframes } from '@mui/material/styles';
import {
  AutoAwesome as SparkleIcon,
  Psychology as BrainIcon,
  Rocket as RocketIcon,
  Coffee as CoffeeIcon,
  Code as CodeIcon,
  DocumentScanner as DocIcon,
} from '@mui/icons-material';

import { useGlobalState } from '../../core/state-management';
import { 
  delightKeyframes, 
  easings,
  performanceUtils,
  loadingAnimations,
} from '../../utils/delight-animations';
import { animatedGradients } from '../../utils/delight-themes';

/**
 * Props interface
 */
interface LoadingSpinnerDelightfulProps {
  size?: 'small' | 'medium' | 'large';
  variant?: 'circular' | 'dots' | 'pulse' | 'orbit' | 'morphing' | 'text';
  color?: 'primary' | 'secondary' | 'inherit' | 'rainbow';
  message?: string;
  showMessage?: boolean;
  showProgress?: boolean;
  progress?: number;
  fullScreen?: boolean;
  overlay?: boolean;
  showFunFacts?: boolean;
  className?: string;
}

/**
 * Size configuration
 */
const SIZE_CONFIG = {
  small: { spinner: 20, icon: 16, font: 'caption' as const },
  medium: { spinner: 40, icon: 24, font: 'body2' as const },
  large: { spinner: 60, icon: 32, font: 'body1' as const },
};

/**
 * Fun loading messages
 */
const funMessages = [
  { text: 'Organizing bits and bytes...', icon: CodeIcon },
  { text: 'Teaching AI to understand your docs...', icon: BrainIcon },
  { text: 'Launching documentation rockets...', icon: RocketIcon },
  { text: 'Brewing fresh insights...', icon: CoffeeIcon },
  { text: 'Sprinkling magic dust...', icon: SparkleIcon },
  { text: 'Scanning the doc-verse...', icon: DocIcon },
];

/**
 * Fun facts for long loads
 */
const funFacts = [
  'Did you know? Good documentation can reduce support tickets by 50%!',
  'Fun fact: The average developer spends 75% of their time reading code!',
  'Pro tip: Clear docs save 30 minutes per developer per day!',
  'Quick fact: Well-documented APIs have 3x faster adoption rates!',
  'Did you know? Documentation is the #1 factor in tool adoption!',
];

/**
 * Styled components
 */
const DotsContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: theme.spacing(1),
  alignItems: 'center',
  justifyContent: 'center',
  
  '& .dot': {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    background: theme.palette.primary.main,
    animation: `${delightKeyframes.pulse} 1.4s ease-in-out infinite`,
    
    '&:nth-of-type(1)': {
      animationDelay: '0s',
    },
    '&:nth-of-type(2)': {
      animationDelay: '0.2s',
    },
    '&:nth-of-type(3)': {
      animationDelay: '0.4s',
    },
  },
}));

const PulseContainer = styled(Box)(({ theme }) => ({
  position: 'relative',
  display: 'inline-flex',
  
  '& .pulse-ring': {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: '100%',
    height: '100%',
    borderRadius: '50%',
    border: `2px solid ${theme.palette.primary.main}`,
    animation: `${delightKeyframes.ripple} 1.5s ease-out infinite`,
  },
  
  '& .pulse-ring:nth-of-type(2)': {
    animationDelay: '0.5s',
  },
}));

const orbitKeyframes = keyframes`
  0% {
    transform: rotate(0deg) translateX(30px) rotate(0deg);
  }
  100% {
    transform: rotate(360deg) translateX(30px) rotate(-360deg);
  }
`;

const OrbitContainer = styled(Box)(({ theme }) => ({
  position: 'relative',
  width: '80px',
  height: '80px',
  
  '& .orbit-center': {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    background: theme.palette.primary.main,
  },
  
  '& .orbit-dot': {
    position: 'absolute',
    top: '50%',
    left: '50%',
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    background: theme.palette.secondary.main,
    animation: `${orbitKeyframes} 2s linear infinite`,
    
    '&:nth-of-type(2)': {
      animationDelay: '0.5s',
      background: theme.palette.primary.light,
    },
    '&:nth-of-type(3)': {
      animationDelay: '1s',
      background: theme.palette.primary.dark,
    },
    '&:nth-of-type(4)': {
      animationDelay: '1.5s',
      background: theme.palette.secondary.light,
    },
  },
}));

const morphingKeyframes = keyframes`
  0%, 100% {
    border-radius: 50%;
    transform: rotate(0deg) scale(1);
  }
  25% {
    border-radius: 0%;
    transform: rotate(90deg) scale(1.1);
  }
  50% {
    border-radius: 50%;
    transform: rotate(180deg) scale(1);
  }
  75% {
    border-radius: 10%;
    transform: rotate(270deg) scale(0.9);
  }
`;

const MorphingBox = styled(Box)(({ theme }) => ({
  width: '50px',
  height: '50px',
  background: theme.palette.primary.main,
  animation: `${morphingKeyframes} 2s ease-in-out infinite`,
  ...performanceUtils.gpuAccelerate,
}));

const RainbowProgress = styled(CircularProgress)(({ theme }) => ({
  background: animatedGradients.aurora.background,
  backgroundSize: animatedGradients.aurora.backgroundSize,
  borderRadius: '50%',
  padding: '2px',
  animation: 'gradientShift 3s ease infinite',
  
  '& .MuiCircularProgress-circle': {
    stroke: 'url(#rainbow-gradient)',
  },
}));

const AnimatedLinearProgress = styled(LinearProgress)(({ theme }) => ({
  height: '6px',
  borderRadius: '3px',
  backgroundColor: theme.palette.grey[200],
  
  '& .MuiLinearProgress-bar': {
    borderRadius: '3px',
    background: animatedGradients.energy.background,
    backgroundSize: animatedGradients.energy.backgroundSize,
    animation: 'gradientShift 2s ease infinite',
  },
}));

const TextAnimation = styled(Typography)(({ theme }) => ({
  background: animatedGradients.aurora.background,
  backgroundSize: animatedGradients.aurora.backgroundSize,
  backgroundClip: 'text',
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  animation: 'gradientShift 3s ease infinite',
  fontWeight: 'bold',
}));

/**
 * LoadingSpinnerDelightful component
 */
const LoadingSpinnerDelightful: React.FC<LoadingSpinnerDelightfulProps> = ({
  size = 'medium',
  variant = 'circular',
  color = 'primary',
  message: customMessage,
  showMessage = true,
  showProgress = false,
  progress = 0,
  fullScreen = false,
  overlay = false,
  showFunFacts = false,
  className,
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
  
  const [currentMessage, setCurrentMessage] = useState(funMessages[0]);
  const [currentFact, setCurrentFact] = useState(funFacts[0]);
  const [messageIndex, setMessageIndex] = useState(0);
  
  const config = SIZE_CONFIG[size];
  const displayMessage = customMessage || currentMessage.text;
  const MessageIcon = currentMessage.icon;

  // Rotate messages
  useEffect(() => {
    if (!customMessage && showMessage && !prefersReducedMotion) {
      const interval = setInterval(() => {
        setMessageIndex(prev => (prev + 1) % funMessages.length);
        setCurrentMessage(funMessages[messageIndex]);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [customMessage, showMessage, messageIndex, prefersReducedMotion]);

  // Rotate fun facts
  useEffect(() => {
    if (showFunFacts && !prefersReducedMotion) {
      const interval = setInterval(() => {
        setCurrentFact(funFacts[Math.floor(Math.random() * funFacts.length)]);
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [showFunFacts, prefersReducedMotion]);

  // Render loading animation based on variant
  const renderLoadingAnimation = () => {
    if (prefersReducedMotion) {
      return <CircularProgress size={config.spinner} color={color === 'rainbow' ? 'primary' : color} />;
    }

    switch (variant) {
      case 'dots':
        return (
          <DotsContainer>
            <div className="dot" />
            <div className="dot" />
            <div className="dot" />
          </DotsContainer>
        );
      
      case 'pulse':
        return (
          <PulseContainer sx={{ width: config.spinner, height: config.spinner }}>
            <div className="pulse-ring" />
            <div className="pulse-ring" />
            <Box
              sx={{
                width: config.spinner,
                height: config.spinner,
                borderRadius: '50%',
                backgroundColor: 'primary.main',
                animation: `${delightKeyframes.pulse} 2s ease-in-out infinite`,
              }}
            />
          </PulseContainer>
        );
      
      case 'orbit':
        return (
          <OrbitContainer sx={{ transform: `scale(${config.spinner / 60})` }}>
            <div className="orbit-center" />
            <div className="orbit-dot" />
            <div className="orbit-dot" />
            <div className="orbit-dot" />
            <div className="orbit-dot" />
          </OrbitContainer>
        );
      
      case 'morphing':
        return (
          <MorphingBox sx={{ 
            width: config.spinner, 
            height: config.spinner,
            background: color === 'rainbow' 
              ? animatedGradients.aurora.background 
              : theme.palette[color === 'inherit' ? 'text' : color].main,
          }} />
        );
      
      case 'text':
        return (
          <TextAnimation variant="h4" sx={{ fontSize: config.spinner / 2 }}>
            Loading...
          </TextAnimation>
        );
      
      case 'circular':
      default:
        return color === 'rainbow' ? (
          <>
            <svg width="0" height="0">
              <defs>
                <linearGradient id="rainbow-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#ff0080" />
                  <stop offset="33%" stopColor="#ff8c00" />
                  <stop offset="66%" stopColor="#40e0d0" />
                  <stop offset="100%" stopColor="#ff0080" />
                </linearGradient>
              </defs>
            </svg>
            <RainbowProgress
              size={config.spinner}
              thickness={4}
              sx={{
                animation: `${delightKeyframes.float} 3s ease-in-out infinite`,
              }}
            />
          </>
        ) : (
          <CircularProgress
            size={config.spinner}
            color={color === 'inherit' ? 'inherit' : color}
            thickness={4}
            sx={{
              animation: `${delightKeyframes.float} 3s ease-in-out infinite`,
              ...(state.ui.accessibility.highContrast && {
                color: '#000000',
                '& .MuiCircularProgress-circle': {
                  stroke: '#000000',
                  strokeWidth: 6,
                },
              }),
            }}
          />
        );
    }
  };

  const contentElement = (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        p: 2,
        
        ...(state.ui.accessibility.highContrast && {
          backgroundColor: '#ffffff',
          color: '#000000',
          border: '2px solid #000000',
        }),
        
        ...(prefersReducedMotion && performanceUtils.reduceMotion(true)),
      }}
      role="status"
      aria-live="polite"
      aria-label={displayMessage}
      className={className}
    >
      <Fade in={true} timeout={600}>
        <Box sx={{ position: 'relative' }}>
          {renderLoadingAnimation()}
        </Box>
      </Fade>
      
      {showMessage && (
        <Fade in={true} timeout={800} style={{ transitionDelay: '200ms' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {!customMessage && (
              <MessageIcon 
                sx={{ 
                  fontSize: config.icon,
                  animation: `${delightKeyframes.wiggle} 2s ease-in-out infinite`,
                  color: 'primary.main',
                }}
              />
            )}
            <Typography
              variant={config.font}
              color="text.secondary"
              sx={{
                textAlign: 'center',
                animation: `${delightKeyframes.slideUp} 0.6s ${easings.entranceEasing}`,
                ...(state.ui.accessibility.highContrast && {
                  color: '#000000',
                }),
              }}
            >
              {displayMessage}
            </Typography>
          </Box>
        </Fade>
      )}
      
      {showProgress && (
        <Fade in={true} timeout={1000} style={{ transitionDelay: '400ms' }}>
          <Box sx={{ width: '200px' }}>
            <AnimatedLinearProgress
              variant="determinate"
              value={progress}
              sx={{
                animation: `${delightKeyframes.slideUp} 0.8s ${easings.entranceEasing}`,
              }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, textAlign: 'center' }}>
              {Math.round(progress)}%
            </Typography>
          </Box>
        </Fade>
      )}
      
      {showFunFacts && size === 'large' && (
        <Fade in={true} timeout={1200} style={{ transitionDelay: '600ms' }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              maxWidth: '300px',
              textAlign: 'center',
              fontStyle: 'italic',
              opacity: 0.8,
              animation: `${delightKeyframes.slideUp} 1s ${easings.entranceEasing}`,
            }}
          >
            {currentFact}
          </Typography>
        </Fade>
      )}
    </Box>
  );

  if (fullScreen) {
    return (
      <Fade in={true}>
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: overlay ? 'rgba(255, 255, 255, 0.95)' : 'transparent',
            backdropFilter: overlay ? 'blur(10px)' : 'none',
            zIndex: theme.zIndex.modal,
            
            ...(state.ui.accessibility.highContrast && overlay && {
              backgroundColor: 'rgba(255, 255, 255, 0.98)',
            }),
          }}
        >
          {contentElement}
        </Box>
      </Fade>
    );
  }

  if (overlay) {
    return (
      <Fade in={true}>
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(5px)',
            borderRadius: 'inherit',
            zIndex: 1,
            
            ...(state.ui.accessibility.highContrast && {
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
            }),
          }}
        >
          {contentElement}
        </Box>
      </Fade>
    );
  }

  return contentElement;
};

export default LoadingSpinnerDelightful;