/**
 * LoadingSpinner - Accessible loading spinner component
 * 
 * Provides loading indicators with various sizes and styles:
 * - Circular spinner with accessibility support
 * - Size variants (small, medium, large)
 * - Color customization
 * - Screen reader announcements
 */

import React from 'react';
import {
  Box,
  CircularProgress,
  Typography,
  useTheme
} from '@mui/material';

import { useGlobalState } from '../../core/state-management';

/**
 * Props interface
 */
interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large';
  color?: 'primary' | 'secondary' | 'inherit';
  message?: string;
  fullScreen?: boolean;
  overlay?: boolean;
  className?: string;
}

/**
 * Size configuration
 */
const SIZE_CONFIG = {
  small: 20,
  medium: 40,
  large: 60
};

/**
 * LoadingSpinner component
 */
const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'medium',
  color = 'primary',
  message = 'Loading...',
  fullScreen = false,
  overlay = false,
  className
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();

  const spinnerSize = SIZE_CONFIG[size];

  const spinnerElement = (
    <CircularProgress
      size={spinnerSize}
      color={color}
      thickness={4}
      sx={{
        ...(state.ui.accessibility.highContrast && {
          color: '#000000',
          '& .MuiCircularProgress-circle': {
            stroke: '#000000',
            strokeWidth: 6
          }
        })
      }}
    />
  );

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
          border: '2px solid #000000'
        })
      }}
      role="status"
      aria-live="polite"
      aria-label={message}
      className={className}
    >
      {spinnerElement}
      
      {message && (
        <Typography
          variant={size === 'small' ? 'caption' : 'body2'}
          color="text.secondary"
          sx={{
            textAlign: 'center',
            ...(state.ui.accessibility.highContrast && {
              color: '#000000'
            })
          }}
        >
          {message}
        </Typography>
      )}
    </Box>
  );

  if (fullScreen) {
    return (
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
          backgroundColor: overlay ? 'rgba(255, 255, 255, 0.8)' : 'transparent',
          zIndex: theme.zIndex.modal,
          
          ...(state.ui.accessibility.highContrast && overlay && {
            backgroundColor: 'rgba(255, 255, 255, 0.95)'
          })
        }}
      >
        {contentElement}
      </Box>
    );
  }

  if (overlay) {
    return (
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
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          borderRadius: 'inherit',
          zIndex: 1,
          
          ...(state.ui.accessibility.highContrast && {
            backgroundColor: 'rgba(255, 255, 255, 0.95)'
          })
        }}
      >
        {contentElement}
      </Box>
    );
  }

  return contentElement;
};

export default LoadingSpinner;