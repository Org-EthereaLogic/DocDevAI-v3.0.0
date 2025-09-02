/**
 * DevDocAI v3.0.0 - Main Application
 * 
 * Full application for AI-powered documentation generation and analysis
 * Integrates all 12 completed modules (M001-M011)
 */

import React, { useState, useEffect } from 'react';
import {
  ThemeProvider,
  CssBaseline,
  Box,
  createTheme,
  PaletteMode,
} from '@mui/material';
import ErrorBoundary from './components/ErrorBoundary';

// Import core components
import AppLayout from './components/layout/AppLayout';
import Dashboard from './components/Dashboard';
import DocumentGenerator from './components/DocumentGenerator';
import QualityAnalyzer from './components/QualityAnalyzer';
import TemplateManager from './components/TemplateManager';
import SecurityDashboard from './components/SecurityDashboard';
import EnhancementPipeline from './components/EnhancementPipeline';
import ReviewEngine from './components/ReviewEngine';
import ConfigurationPanel from './components/ConfigurationPanel';

// Import services
import { ConfigurationService } from './services/ConfigurationService';
import { StorageService } from './services/StorageService';
import { MIAIRService } from './services/MIAIRService';
import { NotificationService } from './services/NotificationService';

// Types
interface AppState {
  currentView: string;
  theme: PaletteMode;
  notifications: any[];
  userPreferences: any;
  moduleStatus: Record<string, boolean>;
}

const App: React.FC = () => {
  console.log('App component rendering...');
  const [state, setState] = useState<AppState>({
    currentView: 'dashboard',
    theme: 'light',
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

  // Initialize services
  useEffect(() => {
    console.log('Starting app initialization...');
    const initializeApp = async () => {
      let serviceErrors = [];
      
      // Initialize each service with individual error handling
      try {
        console.log('Initializing ConfigurationService...');
        await ConfigurationService.initialize();
        console.log('ConfigurationService initialized successfully');
      } catch (error) {
        console.error('ConfigurationService initialization failed:', error);
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
        serviceErrors.push({ service: 'Storage', error });
      }
      
      try {
        console.log('Initializing MIAIR engine...');
        await MIAIRService.initialize();
        console.log('MIAIR engine initialized successfully');
      } catch (error) {
        console.error('MIAIR initialization failed:', error);
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
        serviceErrors.push({ service: 'Notification', error });
      }

      if (serviceErrors.length > 0) {
        console.warn(`DevDocAI initialized with ${serviceErrors.length} service errors:`, serviceErrors);
        console.log('App will continue with limited functionality');
      } else {
        console.log('DevDocAI initialized successfully - all services ready');
      }
    };

    initializeApp();
  }, []);

  // Create theme
  const theme = React.useMemo(
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

  // Handle view changes
  const handleViewChange = (view: string) => {
    setState(prev => ({ ...prev, currentView: view }));
  };

  // Handle theme toggle
  const handleThemeToggle = () => {
    setState(prev => ({
      ...prev,
      theme: prev.theme === 'light' ? 'dark' : 'light'
    }));
  };

  // Render current view
  const renderView = () => {
    switch (state.currentView) {
      case 'dashboard':
        return <Dashboard moduleStatus={state.moduleStatus} />;
      case 'generator':
        return <DocumentGenerator />;
      case 'quality':
        return <QualityAnalyzer />;
      case 'templates':
        return <TemplateManager />;
      case 'security':
        return <SecurityDashboard />;
      case 'enhancement':
        return <EnhancementPipeline />;
      case 'review':
        return <ReviewEngine />;
      case 'config':
        return <ConfigurationPanel />;
      default:
        return <Dashboard moduleStatus={state.moduleStatus} />;
    }
  };

  return (
    <ErrorBoundary>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box sx={{ display: 'flex', minHeight: '100vh' }}>
          <AppLayout
            currentView={state.currentView}
            onViewChange={handleViewChange}
            onThemeToggle={handleThemeToggle}
            theme={state.theme}
            notifications={state.notifications}
            moduleStatus={state.moduleStatus}
          >
            {renderView()}
          </AppLayout>
        </Box>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;