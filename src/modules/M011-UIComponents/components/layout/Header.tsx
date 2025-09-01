/**
 * Header - Application header with navigation and actions
 * 
 * Provides the main application header with:
 * - Application title and branding
 * - Menu toggle button for sidebar
 * - Action buttons and user menu
 * - Responsive design
 * - Accessibility features
 */

import React from 'react';
import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Box,
  useTheme,
  useMediaQuery,
  Tooltip,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  Menu as MenuIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Accessibility as AccessibilityIcon,
  Settings as SettingsIcon
} from '@mui/icons-material';

import { HeaderProps } from './types';
import { useGlobalState } from '../../core/state-management';
import { uiConfigManager } from '../../core/config';

/**
 * Header component
 */
const Header: React.FC<HeaderProps> = ({
  title = 'DevDocAI',
  showMenuButton = true,
  onMenuClick,
  actions,
  className,
  testId,
  ...props
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const globalState = useGlobalState();
  const state = globalState.getState();

  // Handle theme toggle
  const handleThemeToggle = async () => {
    const newTheme = state.ui.theme === 'light' ? 'dark' : 'light';
    
    globalState.updateUI({ theme: newTheme });
    
    await uiConfigManager.updateConfig({
      theme: {
        ...uiConfigManager.getConfig().theme,
        defaultTheme: newTheme
      }
    });
  };

  // Handle accessibility toggle
  const handleAccessibilityToggle = () => {
    const newHighContrast = !state.ui.accessibility.highContrast;
    
    globalState.updateUI({
      accessibility: {
        ...state.ui.accessibility,
        highContrast: newHighContrast
      }
    });
  };

  return (
    <AppBar
      position="fixed"
      className={className}
      data-testid={testId}
      sx={{
        zIndex: theme.zIndex.drawer + 1,
        backgroundColor: theme.palette.background.paper,
        color: theme.palette.text.primary,
        boxShadow: 1,
        borderBottom: `1px solid ${theme.palette.divider}`,
        
        // High contrast support
        ...(state.ui.accessibility.highContrast && {
          backgroundColor: '#000000',
          color: '#ffffff',
          '& .MuiIconButton-root': {
            color: '#ffffff'
          }
        })
      }}
      {...props}
    >
      <Toolbar>
        {/* Menu button */}
        {showMenuButton && (
          <Tooltip title="Toggle navigation menu">
            <IconButton
              color="inherit"
              aria-label="Open drawer"
              onClick={onMenuClick}
              edge="start"
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          </Tooltip>
        )}

        {/* Application title */}
        <Typography
          variant="h6"
          component="h1"
          noWrap
          sx={{
            flexGrow: 1,
            fontWeight: 600,
            color: theme.palette.primary.main,
            
            ...(state.ui.accessibility.highContrast && {
              color: '#ffffff'
            })
          }}
        >
          {title}
        </Typography>

        {/* Actions section */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* Theme toggle */}
          {!isMobile && (
            <Tooltip title={`Switch to ${state.ui.theme === 'light' ? 'dark' : 'light'} theme`}>
              <IconButton
                color="inherit"
                onClick={handleThemeToggle}
                aria-label={`Switch to ${state.ui.theme === 'light' ? 'dark' : 'light'} theme`}
              >
                {state.ui.theme === 'light' ? <DarkModeIcon /> : <LightModeIcon />}
              </IconButton>
            </Tooltip>
          )}

          {/* Accessibility toggle */}
          <Tooltip title="Toggle high contrast mode">
            <IconButton
              color="inherit"
              onClick={handleAccessibilityToggle}
              aria-label="Toggle high contrast mode"
              sx={{
                ...(state.ui.accessibility.highContrast && {
                  backgroundColor: 'rgba(255, 255, 255, 0.2)'
                })
              }}
            >
              <AccessibilityIcon />
            </IconButton>
          </Tooltip>

          {/* Reduced motion toggle */}
          {!isMobile && (
            <FormControlLabel
              control={
                <Switch
                  checked={state.ui.accessibility.reducedMotion}
                  onChange={(event) => {
                    globalState.updateUI({
                      accessibility: {
                        ...state.ui.accessibility,
                        reducedMotion: event.target.checked
                      }
                    });
                  }}
                  size="small"
                  color="primary"
                />
              }
              label="Reduce motion"
              sx={{
                color: 'text.secondary',
                fontSize: '0.875rem',
                
                ...(state.ui.accessibility.highContrast && {
                  color: '#ffffff'
                })
              }}
            />
          )}

          {/* Settings button */}
          <Tooltip title="Settings">
            <IconButton
              color="inherit"
              aria-label="Settings"
            >
              <SettingsIcon />
            </IconButton>
          </Tooltip>

          {/* Custom actions */}
          {actions}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header;