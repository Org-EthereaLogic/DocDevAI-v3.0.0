/**
 * Simplified App Component for Testing
 * Now includes Dashboard component to test full functionality
 */

import React, { useState } from 'react';
import { 
  ThemeProvider, 
  CssBaseline, 
  createTheme,
  Box,
  PaletteMode
} from '@mui/material';
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './components/Dashboard';

interface AppState {
  theme: PaletteMode;
  moduleStatus: Record<string, boolean>;
}

const AppSimple: React.FC = () => {
  console.log('AppSimple component rendering with Dashboard...');
  
  const [state] = useState<AppState>({
    theme: 'light',
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

  const theme = createTheme({
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
  });

  return (
    <ErrorBoundary>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
          <Dashboard moduleStatus={state.moduleStatus} />
        </Box>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default AppSimple;