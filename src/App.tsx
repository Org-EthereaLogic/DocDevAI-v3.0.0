/**
 * DevDocAI v3.0.0 - Main Application
 * 
 * Full application for AI-powered documentation generation and analysis
 * Integrates all 13 completed modules (M001-M013) with React Router
 */

import React, { useState, useEffect } from 'react';
import { BrowserRouter, useLocation } from 'react-router-dom';
import {
  ThemeProvider,
  CssBaseline,
  Box,
  createTheme,
  PaletteMode,
} from '@mui/material';
import ErrorBoundary from './components/ErrorBoundary';

// Import routing
import AppRoutes, { getCurrentRoute } from './routes/AppRoutes';
import AppLayout from './components/layout/AppLayout';

// Import services
import { ConfigurationService } from './services/ConfigurationService';
import { StorageService } from './services/StorageService';
import { MIAIRService } from './services/MIAIRService';
import { NotificationService } from './services/NotificationService';

// Import hooks
import { usePersistedState } from './hooks/usePersistedState';

// Types
interface AppState {
  theme: PaletteMode;
  notifications: any[];
  userPreferences: any;
  moduleStatus: Record<string, boolean>;
}

// AppContent component to access router location
const AppContent: React.FC = () => {
  const location = useLocation();
  console.log('App component rendering for route:', location.pathname);
  
  // Use persisted state for theme preference
  const [theme, setTheme] = usePersistedState<PaletteMode>('devdocai_theme', 'light');
  
  const [state, setState] = useState<AppState>({
    theme,
    notifications: [],
    userPreferences: {},
    moduleStatus: {
      M001: true,  // Configuration Manager - COMPLETE
      M002: true,  // Local Storage - COMPLETE
      M003: true,  // MIAIR Engine - COMPLETE
      M004: true,  // Document Generator - COMPLETE
      M005: true,  // Quality Engine - COMPLETE
      M006: true,  // Template Registry - COMPLETE
      M007: true,  // Review Engine - COMPLETE
      M008: true,  // LLM Adapter - COMPLETE
      M009: true,  // Enhancement Pipeline - COMPLETE
      M010: true,  // Security Module - COMPLETE
      M011: true,  // UI Components - COMPLETE
      M012: true,  // CLI Interface - COMPLETE
      M013: true,  // VS Code Extension - COMPLETE
    }
  });

  // Update state when theme changes
  useEffect(() => {
    setState(prev => ({ ...prev, theme }));
  }, [theme]);

  // Initialize services
  useEffect(() => {
    console.log('Starting app initialization...');
    const initializeApp = async () => {
      let serviceErrors = [];
      
      // Log environment info
      console.log('Environment:', {
        NODE_ENV: process.env.NODE_ENV,
        localStorage: typeof localStorage !== 'undefined',
        window: typeof window !== 'undefined',
        document: typeof document !== 'undefined'
      });
      
      // Initialize each service with individual error handling
      try {
        console.log('Initializing ConfigurationService...');
        await ConfigurationService.initialize();
        console.log('ConfigurationService initialized successfully');
      } catch (error) {
        console.error('ConfigurationService initialization failed:', error);
        console.error('Error details:', {
          message: error instanceof Error ? error.message : 'Unknown error',
          stack: error instanceof Error ? error.stack : undefined
        });
        serviceErrors.push({ service: 'Configuration', error });
      }
      
      try {
        console.log('Initializing StorageService...');
        await StorageService.initialize();
        console.log('StorageService initialized successfully');
        
        // Try to load user preferences
        try {
          const prefs = await StorageService.getUserPreferences();
          setState(prev => ({ ...prev, userPreferences: prefs }));
          console.log('User preferences loaded');
        } catch (error) {
          console.warn('Failed to load user preferences:', error);
        }
      } catch (error) {
        console.error('StorageService initialization failed:', error);
        console.error('Error details:', {
          message: error instanceof Error ? error.message : 'Unknown error',
          stack: error instanceof Error ? error.stack : undefined
        });
        serviceErrors.push({ service: 'Storage', error });
      }
      
      try {
        console.log('Initializing MIAIR engine...');
        await MIAIRService.initialize();
        console.log('MIAIR engine initialized successfully');
      } catch (error) {
        console.error('MIAIR initialization failed:', error);
        console.error('Error details:', {
          message: error instanceof Error ? error.message : 'Unknown error',
          stack: error instanceof Error ? error.stack : undefined
        });
        serviceErrors.push({ service: 'MIAIR', error });
      }
      
      try {
        console.log('Initializing NotificationService...');
        await NotificationService.initialize();
        
        // Setup notification subscription
        NotificationService.subscribe((notification) => {
          setState(prev => ({
            ...prev,
            notifications: [...prev.notifications, notification]
          }));
        });
        console.log('NotificationService initialized successfully');
      } catch (error) {
        console.error('NotificationService initialization failed:', error);
        console.error('Error details:', {
          message: error instanceof Error ? error.message : 'Unknown error',
          stack: error instanceof Error ? error.stack : undefined
        });
        serviceErrors.push({ service: 'Notification', error });
      }

      if (serviceErrors.length > 0) {
        console.warn(`DevDocAI initialized with ${serviceErrors.length} service errors:`, serviceErrors);
        console.log('App will continue with limited functionality');
      } else {
        console.log('DevDocAI initialized successfully - all services ready');
      }
    };

    initializeApp().catch(error => {
      console.error('Fatal error during app initialization:', error);
      console.error('Full error:', error);
    });
  }, []);

  // Get current route info for navigation
  const currentRoute = getCurrentRoute(location.pathname);
  const currentView = currentRoute?.id || 'dashboard';

  // Create theme
  const muiTheme = React.useMemo(
    () =>
      createTheme({
        palette: {
          mode: state.theme,
          primary: {
            main: '#667eea',
          },
          secondary: {
            main: '#764ba2',
          },
          background: {
            default: state.theme === 'light' ? '#f5f5f5' : '#121212',
          },
        },
        typography: {
          fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
          h1: {
            fontSize: '2.5rem',
            fontWeight: 600,
          },
          h2: {
            fontSize: '2rem',
            fontWeight: 500,
          },
        },
        shape: {
          borderRadius: 8,
        },
      }),
    [state.theme]
  );

  // Handle theme toggle with persisted state
  const handleThemeToggle = () => {
    const newTheme = state.theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
  };

  return (
    <ErrorBoundary>
      <ThemeProvider theme={muiTheme}>
        <CssBaseline />
        <Box sx={{ display: 'flex', minHeight: '100vh' }}>
          <AppLayout
            currentView={currentView}
            onThemeToggle={handleThemeToggle}
            theme={state.theme}
            notifications={state.notifications}
            moduleStatus={state.moduleStatus}
          >
            <AppRoutes moduleStatus={state.moduleStatus} />
          </AppLayout>
        </Box>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

// Main App component with Router wrapper
const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
};

export default App;