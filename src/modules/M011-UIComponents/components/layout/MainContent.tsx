/**
 * MainContent - Main content area with responsive layout
 * 
 * Provides the main content container with:
 * - Responsive width adjustment based on sidebar state
 * - Proper spacing and padding
 * - Accessibility features
 * - Smooth transitions
 */

import React from 'react';
import { Box, useTheme } from '@mui/material';
import { styled } from '@mui/material/styles';

import { MainContentProps } from './types';
import { useGlobalState } from '../../core/state-management';

/**
 * Styled main content container
 */
const MainContentContainer = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'sidebarOpen' && prop !== 'sidebarWidth'
})<{ sidebarOpen?: boolean; sidebarWidth?: number }>(({ theme, sidebarOpen, sidebarWidth }) => ({
  flexGrow: 1,
  display: 'flex',
  flexDirection: 'column',
  transition: theme.transitions.create(['margin', 'width'], {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  
  // Adjust margin when sidebar is open
  ...(sidebarOpen && {
    marginLeft: sidebarWidth || 280,
    width: `calc(100% - ${sidebarWidth || 280}px)`,
    transition: theme.transitions.create(['margin', 'width'], {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
  }),
  
  // Responsive adjustments
  [theme.breakpoints.down('md')]: {
    marginLeft: 0,
    width: '100%'
  },
  
  // High contrast support
  '@media (prefers-contrast: high)': {
    backgroundColor: '#ffffff',
    '& *': {
      borderColor: '#000000 !important'
    }
  },
  
  // Reduced motion support
  '@media (prefers-reduced-motion: reduce)': {
    transition: 'none !important'
  }
}));

/**
 * MainContent component
 */
const MainContent: React.FC<MainContentProps> = ({
  children,
  sidebarOpen = false,
  sidebarWidth = 280,
  className,
  testId,
  style,
  ...props
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();

  return (
    <MainContentContainer
      component="div"
      role="main"
      sidebarOpen={sidebarOpen}
      sidebarWidth={sidebarWidth}
      className={className}
      data-testid={testId}
      style={style}
      sx={{
        backgroundColor: theme.palette.background.default,
        minHeight: '100vh',
        position: 'relative',
        
        // Accessibility: Focus management
        '&:focus-within': {
          outline: 'none'
        },
        
        // High contrast adjustments
        ...(state.ui.accessibility.highContrast && {
          backgroundColor: '#ffffff',
          color: '#000000',
          
          '& *': {
            borderColor: '#000000'
          }
        }),
        
        // Custom styles
        ...style
      }}
      {...props}
    >
      {children}
    </MainContentContainer>
  );
};

export default MainContent;