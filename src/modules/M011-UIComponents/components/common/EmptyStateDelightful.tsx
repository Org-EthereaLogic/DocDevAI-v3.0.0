/**
 * EmptyStateDelightful - Enhanced empty state with personality
 * 
 * Features:
 * - Animated illustrations
 * - Contextual messages with humor
 * - Interactive elements to engage users
 * - Seasonal variations
 * - Encouraging call-to-actions
 * - Playful animations
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  useTheme,
  useMediaQuery,
  Fade,
  Grow,
  Zoom,
} from '@mui/material';
import { styled, keyframes } from '@mui/material/styles';
import {
  FolderOpen as FolderIcon,
  Search as SearchIcon,
  Add as AddIcon,
  AutoAwesome as SparkleIcon,
  Psychology as BrainIcon,
  Rocket as RocketIcon,
  Coffee as CoffeeIcon,
  Construction as ConstructionIcon,
  Celebration as PartyIcon,
  FilterDrama as CloudIcon,
  WbSunny as SunIcon,
  NightsStay as MoonIcon,
  Article as DocIcon,
} from '@mui/icons-material';

import ButtonDelightful from './ButtonDelightful';
import { 
  delightKeyframes,
  easings,
  performanceUtils,
} from '../../utils/delight-animations';
import { 
  seasonalThemes,
  animatedGradients,
} from '../../utils/delight-themes';

/**
 * Props interface
 */
interface EmptyStateDelightfulProps {
  type?: 'no-data' | 'no-results' | 'error' | 'coming-soon' | 'success' | 'custom';
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  showAnimation?: boolean;
  showEncouragement?: boolean;
  customIllustration?: React.ReactNode;
  className?: string;
}

/**
 * Empty state configurations
 */
const emptyStateConfigs = {
  'no-data': {
    icons: [FolderIcon, DocIcon],
    titles: [
      'Your canvas awaits!',
      'Ready to create something amazing?',
      'A blank slate full of possibilities!',
      "Let's fill this space with greatness!",
    ],
    descriptions: [
      'Start by generating your first document. It only takes a click!',
      'Every great documentation journey starts with a single doc.',
      'Your documentation empire begins here. What will you create?',
      'No documents yet, but that means unlimited potential!',
    ],
    encouragements: [
      'Pro tip: Great documentation saves 30 minutes per developer per day!',
      'Fun fact: Well-documented code is 3x more likely to be reused!',
      'Did you know? Good docs reduce onboarding time by 50%!',
    ],
    actionLabel: 'Create First Document',
  },
  
  'no-results': {
    icons: [SearchIcon],
    titles: [
      'Nothing found... yet!',
      'Your search came up empty',
      'No matches this time',
      'The search continues...',
    ],
    descriptions: [
      'Try adjusting your filters or search terms.',
      'Sometimes the best finds come from unexpected searches.',
      'Maybe try a different keyword? Or browse all documents?',
      'No results, but don\'t give up! Try a broader search.',
    ],
    encouragements: [
      'Tip: Use wildcards (*) for more flexible searches!',
      'Did you know? Searching by tags often yields better results!',
      'Pro tip: Try searching for related terms or synonyms.',
    ],
    actionLabel: 'Clear Filters',
  },
  
  'error': {
    icons: [ConstructionIcon],
    titles: [
      'Oops! Something went wonky',
      'We hit a tiny snag',
      'Technical hiccup detected',
      'Minor turbulence encountered',
    ],
    descriptions: [
      "Don't worry, these things happen! Let's try again.",
      "Even the best systems need a moment sometimes.",
      "We're on it! In the meantime, try refreshing.",
      "A wild bug appeared! But we'll catch it soon.",
    ],
    encouragements: [
      'Fun fact: 99% of errors are just computers being dramatic!',
      'Remember: Every error is a learning opportunity!',
      "It's not a bug, it's an undocumented feature!",
    ],
    actionLabel: 'Try Again',
  },
  
  'coming-soon': {
    icons: [RocketIcon, SparkleIcon],
    titles: [
      'Something awesome is brewing!',
      'Under construction by wizards',
      'Coming soon to a screen near you',
      'Preparing something special',
    ],
    descriptions: [
      "We're working on something amazing. Stay tuned!",
      'Great features take time. This will be worth the wait!',
      'Our team of caffeinated developers is on it!',
      'Currently in the lab, mixing up some magic.',
    ],
    encouragements: [
      'Patience level: Loading... ████████░░ 80%',
      'Good things come to those who wait (and refresh occasionally)!',
      'While you wait, why not grab a coffee? ☕',
    ],
    actionLabel: 'Notify Me',
  },
  
  'success': {
    icons: [PartyIcon],
    titles: [
      'All done! Great job!',
      'Mission accomplished!',
      'Success! You did it!',
      'Nailed it!',
    ],
    descriptions: [
      'Everything is complete and looking fantastic!',
      'You can sit back and admire your work now.',
      'Another successful operation in the books!',
      'High five! Everything went perfectly.',
    ],
    encouragements: [
      'Achievement unlocked: Task Master!',
      'You're on fire today! 🔥',
      'Productivity level: Expert!',
    ],
    actionLabel: 'What\'s Next?',
  },
};

/**
 * Animated illustration components
 */
const FloatingIcon = styled(Box)(({ theme }) => ({
  animation: `${delightKeyframes.float} 6s ease-in-out infinite`,
  ...performanceUtils.gpuAccelerate,
}));

const PulsingIcon = styled(Box)(({ theme }) => ({
  animation: `${delightKeyframes.pulse} 2s ease-in-out infinite`,
}));

const BouncingIcon = styled(Box)(({ theme }) => ({
  animation: `${delightKeyframes.bounceIn} 0.8s ${easings.bouncy}`,
}));

const cloudFloat = keyframes`
  0%, 100% {
    transform: translateX(0) translateY(0);
  }
  25% {
    transform: translateX(20px) translateY(-5px);
  }
  50% {
    transform: translateX(-10px) translateY(5px);
  }
  75% {
    transform: translateX(15px) translateY(-3px);
  }
`;

const CloudContainer = styled(Box)(({ theme }) => ({
  position: 'relative',
  width: '200px',
  height: '150px',
  
  '& .cloud': {
    position: 'absolute',
    animation: `${cloudFloat} 20s ease-in-out infinite`,
    opacity: 0.7,
    
    '&:nth-of-type(1)': {
      top: '10px',
      left: '10px',
      animationDelay: '0s',
      fontSize: '40px',
    },
    '&:nth-of-type(2)': {
      top: '30px',
      right: '20px',
      animationDelay: '5s',
      fontSize: '30px',
    },
    '&:nth-of-type(3)': {
      bottom: '20px',
      left: '30px',
      animationDelay: '10s',
      fontSize: '35px',
    },
  },
}));

const documentStack = keyframes`
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-10px) rotate(2deg);
  }
`;

const DocumentStack = styled(Box)(({ theme }) => ({
  position: 'relative',
  width: '150px',
  height: '150px',
  
  '& .doc': {
    position: 'absolute',
    width: '80px',
    height: '100px',
    background: theme.palette.background.paper,
    border: `2px solid ${theme.palette.divider}`,
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    animation: `${documentStack} 3s ease-in-out infinite`,
    
    '&:nth-of-type(1)': {
      top: '20px',
      left: '20px',
      zIndex: 3,
      animationDelay: '0s',
    },
    '&:nth-of-type(2)': {
      top: '25px',
      left: '35px',
      zIndex: 2,
      animationDelay: '0.2s',
      opacity: 0.8,
    },
    '&:nth-of-type(3)': {
      top: '30px',
      left: '50px',
      zIndex: 1,
      animationDelay: '0.4s',
      opacity: 0.6,
    },
  },
}));

/**
 * Get time-based greeting
 */
const getTimeBasedGreeting = (): { icon: React.ElementType; greeting: string } => {
  const hour = new Date().getHours();
  
  if (hour >= 5 && hour < 12) {
    return { icon: SunIcon, greeting: 'Good morning!' };
  } else if (hour >= 12 && hour < 17) {
    return { icon: SunIcon, greeting: 'Good afternoon!' };
  } else if (hour >= 17 && hour < 21) {
    return { icon: CloudIcon, greeting: 'Good evening!' };
  } else {
    return { icon: MoonIcon, greeting: 'Working late?' };
  }
};

/**
 * Get seasonal decoration
 */
const getSeasonalDecoration = (): string => {
  const month = new Date().getMonth();
  
  if (month >= 2 && month <= 4) return seasonalThemes.spring.particles[0]; // Spring
  if (month >= 5 && month <= 7) return seasonalThemes.summer.particles[0]; // Summer
  if (month >= 8 && month <= 10) return seasonalThemes.autumn.particles[0]; // Autumn
  return seasonalThemes.winter.particles[0]; // Winter
};

/**
 * EmptyStateDelightful component
 */
const EmptyStateDelightful: React.FC<EmptyStateDelightfulProps> = ({
  type = 'no-data',
  title: customTitle,
  description: customDescription,
  icon: customIcon,
  actionLabel: customActionLabel,
  onAction,
  showAnimation = true,
  showEncouragement = true,
  customIllustration,
  className,
}) => {
  const theme = useTheme();
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)');
  
  const [messageIndex, setMessageIndex] = useState(0);
  const [encouragementIndex, setEncouragementIndex] = useState(0);
  const [showContent, setShowContent] = useState(false);
  
  const config = emptyStateConfigs[type] || emptyStateConfigs['no-data'];
  const timeGreeting = getTimeBasedGreeting();
  const seasonalDecor = getSeasonalDecoration();
  
  const displayTitle = customTitle || config.titles[messageIndex % config.titles.length];
  const displayDescription = customDescription || config.descriptions[messageIndex % config.descriptions.length];
  const displayAction = customActionLabel || config.actionLabel;
  const encouragement = config.encouragements[encouragementIndex % config.encouragements.length];
  
  const IconComponent = config.icons[0];
  const TimeIcon = timeGreeting.icon;

  // Rotate messages
  useEffect(() => {
    if (!prefersReducedMotion) {
      const interval = setInterval(() => {
        setMessageIndex(prev => prev + 1);
      }, 8000);
      return () => clearInterval(interval);
    }
  }, [prefersReducedMotion]);

  // Rotate encouragements
  useEffect(() => {
    if (showEncouragement && !prefersReducedMotion) {
      const interval = setInterval(() => {
        setEncouragementIndex(prev => prev + 1);
      }, 10000);
      return () => clearInterval(interval);
    }
  }, [showEncouragement, prefersReducedMotion]);

  // Show content with delay
  useEffect(() => {
    const timer = setTimeout(() => setShowContent(true), 100);
    return () => clearTimeout(timer);
  }, []);

  // Render illustration
  const renderIllustration = () => {
    if (customIllustration) return customIllustration;
    
    if (!showAnimation || prefersReducedMotion) {
      return (
        <IconComponent sx={{ fontSize: 80, color: 'text.secondary', opacity: 0.5 }} />
      );
    }
    
    switch (type) {
      case 'no-data':
        return (
          <DocumentStack>
            <Box className="doc">
              <DocIcon sx={{ fontSize: 40, color: 'text.secondary', opacity: 0.5 }} />
            </Box>
            <Box className="doc">
              <DocIcon sx={{ fontSize: 40, color: 'text.secondary', opacity: 0.5 }} />
            </Box>
            <Box className="doc">
              <DocIcon sx={{ fontSize: 40, color: 'text.secondary', opacity: 0.5 }} />
            </Box>
          </DocumentStack>
        );
      
      case 'no-results':
        return (
          <FloatingIcon>
            <SearchIcon sx={{ fontSize: 80, color: 'text.secondary', opacity: 0.5 }} />
          </FloatingIcon>
        );
      
      case 'coming-soon':
        return (
          <Box sx={{ position: 'relative' }}>
            <BouncingIcon>
              <RocketIcon sx={{ fontSize: 80, color: 'primary.main' }} />
            </BouncingIcon>
            <SparkleIcon
              sx={{
                position: 'absolute',
                top: -10,
                right: -10,
                fontSize: 30,
                color: 'warning.main',
                animation: `${delightKeyframes.sparkle} 2s ease-in-out infinite`,
              }}
            />
          </Box>
        );
      
      case 'error':
        return (
          <PulsingIcon>
            <ConstructionIcon sx={{ fontSize: 80, color: 'warning.main', opacity: 0.8 }} />
          </PulsingIcon>
        );
      
      case 'success':
        return (
          <BouncingIcon>
            <PartyIcon sx={{ fontSize: 80, color: 'success.main' }} />
          </BouncingIcon>
        );
      
      default:
        return (
          <FloatingIcon>
            <IconComponent sx={{ fontSize: 80, color: 'text.secondary', opacity: 0.5 }} />
          </FloatingIcon>
        );
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '400px',
        p: 4,
        textAlign: 'center',
        position: 'relative',
      }}
      className={className}
    >
      {/* Seasonal decoration */}
      {showAnimation && !prefersReducedMotion && (
        <Box
          sx={{
            position: 'absolute',
            top: 20,
            right: 20,
            fontSize: 30,
            animation: `${delightKeyframes.float} 8s ease-in-out infinite`,
          }}
        >
          {seasonalDecor}
        </Box>
      )}
      
      {/* Time-based greeting */}
      {type === 'no-data' && (
        <Fade in={showContent} timeout={600}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, opacity: 0.7 }}>
            <TimeIcon sx={{ fontSize: 20 }} />
            <Typography variant="caption" color="text.secondary">
              {timeGreeting.greeting}
            </Typography>
          </Box>
        </Fade>
      )}
      
      {/* Illustration */}
      <Zoom in={showContent} timeout={800} style={{ transitionDelay: '200ms' }}>
        <Box sx={{ mb: 3 }}>
          {customIcon || renderIllustration()}
        </Box>
      </Zoom>
      
      {/* Title */}
      <Grow in={showContent} timeout={1000} style={{ transitionDelay: '400ms' }}>
        <Typography
          variant="h5"
          sx={{
            fontWeight: 600,
            mb: 2,
            background: showAnimation && !prefersReducedMotion 
              ? animatedGradients.aurora.background 
              : undefined,
            backgroundSize: animatedGradients.aurora.backgroundSize,
            backgroundClip: showAnimation && !prefersReducedMotion ? 'text' : undefined,
            WebkitBackgroundClip: showAnimation && !prefersReducedMotion ? 'text' : undefined,
            WebkitTextFillColor: showAnimation && !prefersReducedMotion ? 'transparent' : undefined,
            animation: showAnimation && !prefersReducedMotion 
              ? 'gradientShift 10s ease infinite' 
              : undefined,
          }}
        >
          {displayTitle}
        </Typography>
      </Grow>
      
      {/* Description */}
      <Fade in={showContent} timeout={1200} style={{ transitionDelay: '600ms' }}>
        <Typography
          variant="body1"
          color="text.secondary"
          sx={{ maxWidth: '500px', mb: 3 }}
        >
          {displayDescription}
        </Typography>
      </Fade>
      
      {/* Encouragement */}
      {showEncouragement && (
        <Fade in={showContent} timeout={1400} style={{ transitionDelay: '800ms' }}>
          <Typography
            variant="caption"
            sx={{
              fontStyle: 'italic',
              opacity: 0.7,
              mb: 3,
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <SparkleIcon sx={{ fontSize: 16 }} />
            {encouragement}
          </Typography>
        </Fade>
      )}
      
      {/* Action button */}
      {onAction && (
        <Zoom in={showContent} timeout={1600} style={{ transitionDelay: '1000ms' }}>
          <Box>
            <ButtonDelightful
              variant="contained"
              size="large"
              onClick={onAction}
              startIcon={<AddIcon />}
              hoverEffect="lift"
              clickEffect="sparkle"
              showParticles
            >
              {displayAction}
            </ButtonDelightful>
          </Box>
        </Zoom>
      )}
      
      {/* Background decoration */}
      {showAnimation && !prefersReducedMotion && type === 'coming-soon' && (
        <CloudContainer sx={{ position: 'absolute', bottom: 0, left: 0, opacity: 0.3 }}>
          <CloudIcon className="cloud" />
          <CloudIcon className="cloud" />
          <CloudIcon className="cloud" />
        </CloudContainer>
      )}
    </Box>
  );
};

export default EmptyStateDelightful;