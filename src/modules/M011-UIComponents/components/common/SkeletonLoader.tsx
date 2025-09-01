/**
 * SkeletonLoader - Skeleton loading screens for better UX
 * 
 * Provides skeleton loading patterns for different content types:
 * - Card skeletons for dashboard widgets
 * - List skeletons for activity feeds
 * - Text skeletons for content loading
 * - Custom skeleton patterns
 */

import React from 'react';
import {
  Box,
  Skeleton,
  Card,
  CardContent,
  useTheme
} from '@mui/material';

import { useGlobalState } from '../../core/state-management';

/**
 * Props interface
 */
interface SkeletonLoaderProps {
  variant: 'card' | 'list' | 'text' | 'custom';
  count?: number;
  height?: number | string;
  width?: number | string;
  animation?: 'pulse' | 'wave' | false;
  className?: string;
}

/**
 * Card skeleton component
 */
const CardSkeleton: React.FC<{ height?: number | string }> = ({ height = 200 }) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();

  return (
    <Card
      sx={{
        height,
        ...(state.ui.accessibility.highContrast && {
          backgroundColor: '#ffffff',
          border: '2px solid #000000'
        })
      }}
    >
      <CardContent sx={{ p: 2 }}>
        {/* Header skeleton */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Skeleton
            variant="circular"
            width={24}
            height={24}
            sx={{
              mr: 1,
              ...(state.ui.accessibility.highContrast && {
                backgroundColor: '#cccccc'
              })
            }}
          />
          <Skeleton
            variant="text"
            width="40%"
            height={20}
            sx={{
              ...(state.ui.accessibility.highContrast && {
                backgroundColor: '#cccccc'
              })
            }}
          />
        </Box>
        
        {/* Content skeleton */}
        <Skeleton
          variant="rectangular"
          width="100%"
          height={60}
          sx={{
            mb: 2,
            borderRadius: 1,
            ...(state.ui.accessibility.highContrast && {
              backgroundColor: '#cccccc'
            })
          }}
        />
        
        {/* Text lines */}
        <Skeleton
          variant="text"
          width="80%"
          height={16}
          sx={{
            mb: 1,
            ...(state.ui.accessibility.highContrast && {
              backgroundColor: '#cccccc'
            })
          }}
        />
        <Skeleton
          variant="text"
          width="60%"
          height={16}
          sx={{
            ...(state.ui.accessibility.highContrast && {
              backgroundColor: '#cccccc'
            })
          }}
        />
      </CardContent>
    </Card>
  );
};

/**
 * List skeleton component
 */
const ListSkeleton: React.FC<{ count: number }> = ({ count }) => {
  const globalState = useGlobalState();
  const state = globalState.getState();

  return (
    <Box>
      {Array.from({ length: count }).map((_, index) => (
        <Box
          key={index}
          sx={{
            display: 'flex',
            alignItems: 'center',
            py: 1.5,
            px: 1,
            borderBottom: index < count - 1 ? '1px solid' : 'none',
            borderColor: 'divider',
            
            ...(state.ui.accessibility.highContrast && {
              borderColor: '#000000'
            })
          }}
        >
          {/* Avatar */}
          <Skeleton
            variant="circular"
            width={40}
            height={40}
            sx={{
              mr: 2,
              flexShrink: 0,
              ...(state.ui.accessibility.highContrast && {
                backgroundColor: '#cccccc'
              })
            }}
          />
          
          {/* Content */}
          <Box sx={{ flexGrow: 1 }}>
            <Skeleton
              variant="text"
              width="70%"
              height={20}
              sx={{
                mb: 0.5,
                ...(state.ui.accessibility.highContrast && {
                  backgroundColor: '#cccccc'
                })
              }}
            />
            <Skeleton
              variant="text"
              width="50%"
              height={16}
              sx={{
                ...(state.ui.accessibility.highContrast && {
                  backgroundColor: '#cccccc'
                })
              }}
            />
          </Box>
          
          {/* Action */}
          <Skeleton
            variant="rectangular"
            width={24}
            height={24}
            sx={{
              ml: 1,
              borderRadius: 0.5,
              ...(state.ui.accessibility.highContrast && {
                backgroundColor: '#cccccc'
              })
            }}
          />
        </Box>
      ))}
    </Box>
  );
};

/**
 * Text skeleton component
 */
const TextSkeleton: React.FC<{ 
  count: number; 
  height?: number; 
  width?: string | number;
}> = ({ count, height = 16, width = '100%' }) => {
  const globalState = useGlobalState();
  const state = globalState.getState();

  return (
    <Box>
      {Array.from({ length: count }).map((_, index) => (
        <Skeleton
          key={index}
          variant="text"
          width={index === count - 1 ? '60%' : width}
          height={height}
          sx={{
            mb: index < count - 1 ? 1 : 0,
            ...(state.ui.accessibility.highContrast && {
              backgroundColor: '#cccccc'
            })
          }}
        />
      ))}
    </Box>
  );
};

/**
 * SkeletonLoader component
 */
const SkeletonLoader: React.FC<SkeletonLoaderProps> = ({
  variant,
  count = 1,
  height,
  width,
  animation = 'wave',
  className
}) => {
  const globalState = useGlobalState();
  const state = globalState.getState();

  // Disable animation for reduced motion
  const effectiveAnimation = state.ui.accessibility.reduceMotion ? false : animation;

  const renderSkeleton = () => {
    switch (variant) {
      case 'card':
        return (
          <Box className={className}>
            {Array.from({ length: count }).map((_, index) => (
              <Box key={index} sx={{ mb: index < count - 1 ? 2 : 0 }}>
                <CardSkeleton height={height} />
              </Box>
            ))}
          </Box>
        );

      case 'list':
        return (
          <Box className={className}>
            <ListSkeleton count={count} />
          </Box>
        );

      case 'text':
        return (
          <Box className={className}>
            <TextSkeleton count={count} height={height as number} width={width} />
          </Box>
        );

      case 'custom':
        return (
          <Box className={className}>
            {Array.from({ length: count }).map((_, index) => (
              <Skeleton
                key={index}
                variant="rectangular"
                width={width || '100%'}
                height={height || 100}
                animation={effectiveAnimation}
                sx={{
                  mb: index < count - 1 ? 2 : 0,
                  borderRadius: 1,
                  ...(state.ui.accessibility.highContrast && {
                    backgroundColor: '#cccccc'
                  })
                }}
              />
            ))}
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Box
      role="status"
      aria-label="Loading content"
      sx={{
        '& .MuiSkeleton-root': {
          animation: effectiveAnimation === false ? 'none' : undefined
        }
      }}
    >
      {renderSkeleton()}
    </Box>
  );
};

export default SkeletonLoader;