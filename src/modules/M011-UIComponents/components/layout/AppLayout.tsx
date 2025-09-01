/**
 * AppLayout - Main application layout with responsive sidebar and header
 * 
 * Provides the primary layout structure for DevDocAI dashboard with:
 * - Responsive sidebar navigation
 * - Header with application actions
 * - Main content area
 * - Footer (optional)
 * - WCAG 2.1 AA compliant accessibility
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  CssBaseline,
  useTheme,
  useMediaQuery,
  Toolbar
} from '@mui/material';
import { styled } from '@mui/material/styles';

import Header from './Header';
import Sidebar from './Sidebar';
import MainContent from './MainContent';
import Footer from './Footer';
import { AppLayoutConfig, NavigationItem } from './types';
import { useGlobalState } from '../../core/state-management';
import { accessibilityManager } from '../../core/accessibility';

/**
 * Styled components
 */
const Root = styled(Box)(({ theme }) => ({
  display: 'flex',
  minHeight: '100vh',
  width: '100%',
  backgroundColor: theme.palette.background.default,
  
  // High contrast support
  '@media (prefers-contrast: high)': {
    backgroundColor: '#ffffff',
    color: '#000000',
  },
  
  // Reduced motion support
  '@media (prefers-reduced-motion: reduce)': {
    '& *': {
      animationDuration: '0.01ms !important',
      animationIterationCount: '1 !important',
      transitionDuration: '0.01ms !important',
      scrollBehavior: 'auto !important'
    }
  }
}));

/**
 * Default layout configuration
 */
const DEFAULT_CONFIG: AppLayoutConfig = {
  sidebarWidth: 280,
  headerHeight: 64,
  footerHeight: 48,
  breakpoints: {
    mobile: 600,
    tablet: 960,
    desktop: 1280
  },
  navigation: {
    items: [],
    collapsible: true,
    defaultCollapsed: false
  }
};

/**
 * Default navigation items
 */
const DEFAULT_NAVIGATION: NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    path: '/',
    icon: '📊'
  },
  {
    id: 'documents',
    label: 'Documents',
    path: '/documents',
    icon: '📄'
  },
  {
    id: 'templates',
    label: 'Templates',
    path: '/templates',
    icon: '📝'
  },
  {
    id: 'quality',
    label: 'Quality Analysis',
    path: '/quality',
    icon: '🎯'
  },
  {
    id: 'settings',
    label: 'Settings',
    path: '/settings',
    icon: '⚙️'
  }
];

/**
 * AppLayout props
 */
interface AppLayoutProps {
  children: React.ReactNode;
  config?: Partial<AppLayoutConfig>;
  navigation?: NavigationItem[];
  showFooter?: boolean;
}

/**
 * AppLayout component
 */
const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  config: configOverrides,
  navigation: navigationItems = DEFAULT_NAVIGATION,
  showFooter = false
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const globalState = useGlobalState();
  
  // Merge configuration
  const config = { ...DEFAULT_CONFIG, ...configOverrides };
  
  // State management
  const [sidebarOpen, setSidebarOpen] = useState(!config.navigation.defaultCollapsed && !isMobile);
  const [mounted, setMounted] = useState(false);

  // Effect for mounting and accessibility setup
  useEffect(() => {
    setMounted(true);
    
    // Initialize accessibility features
    const initAccessibility = async () => {
      try {
        await accessibilityManager.initialize();
        
        // Announce app loaded for screen readers
        accessibilityManager.announceToScreenReader('DevDocAI dashboard loaded');
      } catch (error) {
        console.error('Failed to initialize accessibility:', error);
      }
    };

    initAccessibility();
  }, []);

  // Handle sidebar toggle
  const handleSidebarToggle = useCallback(() => {
    setSidebarOpen(prev => !prev);
    
    // Update global state
    globalState.updateUI({ sidebarOpen: !sidebarOpen });
    
    // Announce state change for screen readers
    accessibilityManager.announceToScreenReader(
      sidebarOpen ? 'Sidebar closed' : 'Sidebar opened'
    );
  }, [sidebarOpen, globalState]);

  // Handle sidebar close (for mobile)
  const handleSidebarClose = useCallback(() => {
    setSidebarOpen(false);
    globalState.updateUI({ sidebarOpen: false });
  }, [globalState]);

  // Responsive behavior
  useEffect(() => {
    if (isMobile && sidebarOpen) {
      setSidebarOpen(false);
    }
  }, [isMobile]);

  // Skip rendering until mounted (prevents hydration issues)
  if (!mounted) {
    return null;
  }

  return (
    <Root>
      <CssBaseline />
      
      {/* Header */}
      <Header
        title="DevDocAI"
        showMenuButton={true}
        onMenuClick={handleSidebarToggle}
        className="app-header"
        testId="app-header"
      />
      
      {/* Sidebar */}
      <Sidebar
        open={sidebarOpen}
        onClose={handleSidebarClose}
        width={config.sidebarWidth}
        variant={isMobile ? 'temporary' : 'persistent'}
        navigation={navigationItems}
        className="app-sidebar"
        testId="app-sidebar"
      />
      
      {/* Main content area */}
      <MainContent
        sidebarOpen={sidebarOpen && !isMobile}
        sidebarWidth={config.sidebarWidth}
        className="app-main-content"
        testId="app-main-content"
      >
        {/* Skip link for keyboard navigation */}
        <Box
          component="a"
          href="#main-content"
          sx={{
            position: 'absolute',
            left: '-9999px',
            zIndex: 999,
            padding: 1,
            backgroundColor: 'primary.main',
            color: 'primary.contrastText',
            textDecoration: 'none',
            '&:focus': {
              left: '1rem',
              top: '1rem'
            }
          }}
        >
          Skip to main content
        </Box>
        
        {/* Spacer for fixed header */}
        <Toolbar />
        
        {/* Main content */}
        <Box
          id="main-content"
          component="main"
          role="main"
          aria-label="Main content"
          tabIndex={-1}
          sx={{
            flexGrow: 1,
            padding: 3,
            minHeight: 'calc(100vh - 64px)',
            
            // Focus styles for keyboard navigation
            '&:focus': {
              outline: `2px solid ${theme.palette.primary.main}`,
              outlineOffset: 2
            }
          }}
        >
          {children}
        </Box>
      </MainContent>
      
      {/* Footer */}
      {showFooter && (
        <Footer
          compact={isMobile}
          className="app-footer"
          testId="app-footer"
        />
      )}
    </Root>
  );
};

export default AppLayout;