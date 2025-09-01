/**
 * WebviewPanel - VS Code webview integration component
 * 
 * Provides webview panel components for VS Code extension:
 * - Document generation panel
 * - Quality analysis viewer
 * - Template selection interface
 * - Settings configuration panel
 * - Real-time status updates
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  AppBar,
  Toolbar,
  IconButton,
  Button,
  Divider,
  useTheme
} from '@mui/material';
import {
  Close,
  Minimize,
  Settings,
  Refresh,
  Help,
  MoreVert
} from '@mui/icons-material';

import { useGlobalState } from '../../core/state-management';
import { eventManager, UIEventType } from '../../core/event-system';
import { LoadingSpinner, ErrorBoundary } from '../common';

/**
 * Webview panel types
 */
export type WebviewPanelType = 
  | 'document-generator'
  | 'quality-analyzer'
  | 'template-browser'
  | 'settings'
  | 'help'
  | 'status';

/**
 * VS Code API interface
 */
interface VSCodeAPI {
  postMessage: (message: any) => void;
  getState: () => any;
  setState: (state: any) => void;
}

/**
 * Webview message interface
 */
interface WebviewMessage {
  type: string;
  payload?: any;
  requestId?: string;
}

/**
 * Props interface
 */
interface WebviewPanelProps {
  panelType: WebviewPanelType;
  title: string;
  children: React.ReactNode;
  onClose?: () => void;
  onMinimize?: () => void;
  showRefresh?: boolean;
  showSettings?: boolean;
  className?: string;
}

/**
 * Hook to access VS Code API
 */
const useVSCodeAPI = () => {
  const [vscode, setVscode] = useState<VSCodeAPI | null>(null);

  useEffect(() => {
    // Check if running in VS Code webview
    if (typeof acquireVsCodeApi !== 'undefined') {
      const api = acquireVsCodeApi();
      setVscode(api);
    }
  }, []);

  const postMessage = useCallback((message: WebviewMessage) => {
    if (vscode) {
      vscode.postMessage(message);
    } else {
      // Development fallback
      console.log('VS Code message:', message);
    }
  }, [vscode]);

  const getState = useCallback(() => {
    return vscode?.getState() || {};
  }, [vscode]);

  const setState = useCallback((state: any) => {
    if (vscode) {
      vscode.setState(state);
    }
  }, [vscode]);

  return { vscode, postMessage, getState, setState };
};

/**
 * WebviewPanel component
 */
const WebviewPanel: React.FC<WebviewPanelProps> = ({
  panelType,
  title,
  children,
  onClose,
  onMinimize,
  showRefresh = true,
  showSettings = false,
  className
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();
  const { postMessage } = useVSCodeAPI();

  const [isMinimized, setIsMinimized] = useState(false);
  const [loading, setLoading] = useState(false);

  // Handle VS Code messages
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const message: WebviewMessage = event.data;
      
      switch (message.type) {
        case 'panel-refresh':
          handleRefresh();
          break;
        case 'panel-minimize':
          handleMinimize();
          break;
        case 'panel-close':
          handleClose();
          break;
        case 'theme-changed':
          // Handle theme changes from VS Code
          eventManager.emitSimple(UIEventType.THEME_CHANGED, 'vscode', {
            theme: message.payload.theme
          });
          break;
        default:
          // Forward unhandled messages to children
          eventManager.emitSimple(UIEventType.WEBVIEW_MESSAGE, panelType, message);
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('message', handleMessage);
      return () => window.removeEventListener('message', handleMessage);
    }
  }, [panelType]);

  const handleClose = () => {
    postMessage({
      type: 'panel-close-requested',
      payload: { panelType }
    });
    
    if (onClose) {
      onClose();
    }
  };

  const handleMinimize = () => {
    setIsMinimized(!isMinimized);
    
    postMessage({
      type: 'panel-minimize-requested',
      payload: { panelType, minimized: !isMinimized }
    });
    
    if (onMinimize) {
      onMinimize();
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    
    postMessage({
      type: 'panel-refresh-requested',
      payload: { panelType }
    });

    // Emit refresh event
    eventManager.emitSimple(UIEventType.PANEL_REFRESH, panelType, {});

    // Simulate loading for UX
    setTimeout(() => {
      setLoading(false);
    }, 500);
  };

  const handleSettings = () => {
    postMessage({
      type: 'panel-settings-requested',
      payload: { panelType }
    });

    eventManager.emitSimple(UIEventType.SETTINGS_OPEN, panelType, {});
  };

  const handleHelp = () => {
    postMessage({
      type: 'panel-help-requested',
      payload: { panelType }
    });
  };

  return (
    <ErrorBoundary level="component">
      <Box
        className={className}
        sx={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: theme.palette.background.default,
          color: theme.palette.text.primary,
          
          // VS Code theme integration
          ...(state.ui.theme === 'vscode-dark' && {
            backgroundColor: '#1e1e1e',
            color: '#cccccc'
          }),
          
          ...(state.ui.theme === 'vscode-light' && {
            backgroundColor: '#ffffff',
            color: '#333333'
          }),
          
          ...(state.ui.accessibility.highContrast && {
            backgroundColor: '#ffffff',
            color: '#000000',
            border: '2px solid #000000'
          })
        }}
      >
        {/* Panel Header */}
        <AppBar
          position="static"
          elevation={0}
          sx={{
            backgroundColor: theme.palette.background.paper,
            borderBottom: `1px solid ${theme.palette.divider}`,
            
            ...(state.ui.theme === 'vscode-dark' && {
              backgroundColor: '#2d2d30',
              borderBottomColor: '#3e3e42'
            }),
            
            ...(state.ui.theme === 'vscode-light' && {
              backgroundColor: '#f3f3f3',
              borderBottomColor: '#e5e5e5'
            })
          }}
        >
          <Toolbar variant="dense" sx={{ minHeight: 40 }}>
            <Typography
              variant="subtitle2"
              component="h1"
              sx={{
                flexGrow: 1,
                fontWeight: 600,
                color: theme.palette.text.primary,
                
                ...(state.ui.accessibility.highContrast && {
                  color: '#000000'
                })
              }}
            >
              {title}
            </Typography>

            {/* Panel Actions */}
            <Box sx={{ display: 'flex', gap: 0.5 }}>
              {showRefresh && (
                <IconButton
                  size="small"
                  onClick={handleRefresh}
                  disabled={loading}
                  title="Refresh panel"
                  sx={{
                    color: theme.palette.text.secondary,
                    '&:hover': {
                      color: theme.palette.text.primary
                    }
                  }}
                >
                  <Refresh fontSize="small" />
                </IconButton>
              )}

              {showSettings && (
                <IconButton
                  size="small"
                  onClick={handleSettings}
                  title="Panel settings"
                  sx={{
                    color: theme.palette.text.secondary,
                    '&:hover': {
                      color: theme.palette.text.primary
                    }
                  }}
                >
                  <Settings fontSize="small" />
                </IconButton>
              )}

              <IconButton
                size="small"
                onClick={handleHelp}
                title="Help"
                sx={{
                  color: theme.palette.text.secondary,
                  '&:hover': {
                    color: theme.palette.text.primary
                  }
                }}
              >
                <Help fontSize="small" />
              </IconButton>

              <IconButton
                size="small"
                onClick={handleMinimize}
                title={isMinimized ? "Restore" : "Minimize"}
                sx={{
                  color: theme.palette.text.secondary,
                  '&:hover': {
                    color: theme.palette.text.primary
                  }
                }}
              >
                <Minimize fontSize="small" />
              </IconButton>

              {onClose && (
                <IconButton
                  size="small"
                  onClick={handleClose}
                  title="Close panel"
                  sx={{
                    color: theme.palette.text.secondary,
                    '&:hover': {
                      color: theme.palette.error.main
                    }
                  }}
                >
                  <Close fontSize="small" />
                </IconButton>
              )}
            </Box>
          </Toolbar>
        </AppBar>

        {/* Panel Content */}
        <Box
          sx={{
            flexGrow: 1,
            display: isMinimized ? 'none' : 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}
        >
          {loading ? (
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              flexGrow: 1 
            }}>
              <LoadingSpinner message="Refreshing..." />
            </Box>
          ) : (
            children
          )}
        </Box>

        {/* Status Bar */}
        {!isMinimized && (
          <Box
            sx={{
              borderTop: `1px solid ${theme.palette.divider}`,
              px: 1,
              py: 0.5,
              backgroundColor: theme.palette.background.paper,
              
              ...(state.ui.theme === 'vscode-dark' && {
                backgroundColor: '#007acc',
                borderTopColor: '#3e3e42'
              }),
              
              ...(state.ui.theme === 'vscode-light' && {
                backgroundColor: '#007acc',
                borderTopColor: '#e5e5e5'
              })
            }}
          >
            <Typography
              variant="caption"
              sx={{
                color: state.ui.theme?.includes('vscode') 
                  ? '#ffffff' 
                  : theme.palette.text.secondary,
                  
                ...(state.ui.accessibility.highContrast && {
                  color: '#000000'
                })
              }}
            >
              DevDocAI • {panelType.replace('-', ' ')}
            </Typography>
          </Box>
        )}
      </Box>
    </ErrorBoundary>
  );
};

export default WebviewPanel;