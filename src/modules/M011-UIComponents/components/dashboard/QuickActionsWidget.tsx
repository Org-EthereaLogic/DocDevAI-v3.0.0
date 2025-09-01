/**
 * QuickActionsWidget - Quick action buttons and shortcuts
 * 
 * Provides quick access to common actions:
 * - Document generation shortcuts
 * - Analysis tools
 * - Configuration options
 * - Template management
 * - Keyboard shortcuts support
 */

import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  IconButton,
  Tooltip,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  Menu,
  MenuItem,
  useTheme,
  useMediaQuery
} from '@mui/material';
import {
  Add as AddIcon,
  Analytics,
  Settings,
  Description,
  AutoFixHigh,
  Refresh,
  MoreVert,
  Keyboard,
  Speed,
  Assignment,
  CheckCircle,
  School
} from '@mui/icons-material';

import { WidgetProps, QuickAction } from './types';
import { useGlobalState } from '../../core/state-management';
import { eventManager, UIEventType } from '../../core/event-system';
import { accessibilityManager } from '../../core/accessibility';

/**
 * Props interface
 */
interface QuickActionsWidgetProps extends WidgetProps {
  actions?: QuickAction[];
  onActionClick?: (actionId: string) => Promise<void>;
}

/**
 * Default quick actions
 */
const DEFAULT_ACTIONS: QuickAction[] = [
  {
    id: 'generate-doc',
    label: 'Generate Document',
    description: 'Create a new document from template',
    icon: <AddIcon />,
    action: async () => {
      // Mock action
      console.log('Generate document action');
    },
    shortcut: 'Ctrl+N',
    category: 'create'
  },
  {
    id: 'analyze-quality',
    label: 'Analyze Quality',
    description: 'Run quality analysis on documents',
    icon: <Analytics />,
    action: async () => {
      console.log('Analyze quality action');
    },
    shortcut: 'Ctrl+A',
    category: 'analyze'
  },
  {
    id: 'enhance-docs',
    label: 'Enhance Documents',
    description: 'Improve document quality with AI',
    icon: <AutoFixHigh />,
    action: async () => {
      console.log('Enhance documents action');
    },
    shortcut: 'Ctrl+E',
    category: 'enhance'
  },
  {
    id: 'create-suite',
    label: 'Create Suite',
    description: 'Generate complete documentation suite',
    icon: <Assignment />,
    action: async () => {
      console.log('Create suite action');
    },
    category: 'create'
  },
  {
    id: 'batch-process',
    label: 'Batch Process',
    description: 'Process multiple documents at once',
    icon: <Speed />,
    action: async () => {
      console.log('Batch process action');
    },
    shortcut: 'Ctrl+B',
    category: 'process'
  },
  {
    id: 'templates',
    label: 'Manage Templates',
    description: 'Browse and manage document templates',
    icon: <Description />,
    action: async () => {
      console.log('Manage templates action');
    },
    category: 'manage'
  },
  {
    id: 'settings',
    label: 'Settings',
    description: 'Configure DevDocAI preferences',
    icon: <Settings />,
    action: async () => {
      console.log('Settings action');
    },
    shortcut: 'Ctrl+,',
    category: 'settings'
  },
  {
    id: 'help',
    label: 'Help & Tutorial',
    description: 'Learn how to use DevDocAI effectively',
    icon: <School />,
    action: async () => {
      console.log('Help action');
    },
    shortcut: 'F1',
    category: 'help'
  }
];

/**
 * Action category configurations
 */
const CATEGORY_CONFIG = {
  create: { color: '#4caf50', label: 'Create' },
  analyze: { color: '#2196f3', label: 'Analyze' },
  enhance: { color: '#9c27b0', label: 'Enhance' },
  process: { color: '#ff9800', label: 'Process' },
  manage: { color: '#795548', label: 'Manage' },
  settings: { color: '#607d8b', label: 'Settings' },
  help: { color: '#f44336', label: 'Help' }
};

/**
 * QuickActionsWidget component
 */
const QuickActionsWidget: React.FC<QuickActionsWidgetProps> = ({
  actions = DEFAULT_ACTIONS,
  onActionClick,
  loading = false,
  error,
  onRefresh,
  title = 'Quick Actions'
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const globalState = useGlobalState();
  const state = globalState.getState();

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [executingAction, setExecutingAction] = useState<string | null>(null);

  // Handle action execution
  const handleActionClick = async (action: QuickAction) => {
    try {
      setExecutingAction(action.id);

      // Emit user interaction event
      eventManager.emitSimple(UIEventType.USER_ACTION, 'quick-actions', {
        actionId: action.id,
        actionLabel: action.label
      });

      // Execute custom handler if provided, otherwise use action's handler
      if (onActionClick) {
        await onActionClick(action.id);
      } else {
        await action.action();
      }

      // Announce action for screen readers
      accessibilityManager.announceToScreenReader(`${action.label} action completed`);

      // Show success notification
      globalState.addNotification({
        type: 'success',
        title: 'Action Completed',
        message: `${action.label} completed successfully`
      });

    } catch (error) {
      console.error(`Failed to execute action ${action.id}:`, error);
      
      // Show error notification
      globalState.addNotification({
        type: 'error',
        title: 'Action Failed',
        message: `Failed to execute ${action.label}: ${(error as Error).message}`
      });
    } finally {
      setExecutingAction(null);
    }
  };

  // Handle keyboard shortcuts
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Check if any action shortcut matches
      const matchingAction = actions.find(action => {
        if (!action.shortcut) return false;
        
        const shortcut = action.shortcut.toLowerCase();
        const isCtrl = event.ctrlKey || event.metaKey;
        const key = event.key.toLowerCase();
        
        if (shortcut.includes('ctrl+') && isCtrl) {
          return shortcut.endsWith(key);
        }
        
        return shortcut === key;
      });

      if (matchingAction && !executingAction) {
        event.preventDefault();
        handleActionClick(matchingAction);
      }
    };

    // Only attach keyboard listeners if keyboard shortcuts are enabled
    if (state.ui.accessibility.keyboardNavigation) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [actions, executingAction, state.ui.accessibility.keyboardNavigation]);

  // Show error state
  if (error) {
    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" component="h3">
            {title}
          </Typography>
          {onRefresh && (
            <IconButton size="small" onClick={onRefresh} disabled={loading}>
              <Refresh />
            </IconButton>
          )}
        </Box>
        
        <Typography color="error" sx={{ textAlign: 'center', mt: 4 }}>
          Failed to load quick actions: {error}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6" component="h3">
            {title}
          </Typography>
          {state.ui.accessibility.keyboardNavigation && (
            <Tooltip title="Keyboard shortcuts enabled">
              <Keyboard fontSize="small" color="primary" />
            </Tooltip>
          )}
        </Box>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          {onRefresh && (
            <Tooltip title="Refresh actions">
              <IconButton size="small" onClick={onRefresh} disabled={loading}>
                <Refresh />
              </IconButton>
            </Tooltip>
          )}
          
          <IconButton
            size="small"
            onClick={(event) => setAnchorEl(event.currentTarget)}
          >
            <MoreVert />
          </IconButton>
        </Box>
      </Box>

      {/* Actions Grid */}
      <Grid container spacing={2} sx={{ flexGrow: 1 }}>
        {actions.map((action) => {
          const categoryConfig = CATEGORY_CONFIG[action.category as keyof typeof CATEGORY_CONFIG];
          const isExecuting = executingAction === action.id;
          
          return (
            <Grid item xs={6} md={3} key={action.id}>
              <Card
                sx={{
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  cursor: action.disabled ? 'not-allowed' : 'pointer',
                  opacity: action.disabled ? 0.6 : 1,
                  transition: 'all 0.2s ease-in-out',
                  
                  '&:hover': {
                    ...((!action.disabled && !isExecuting) && {
                      transform: 'translateY(-2px)',
                      boxShadow: theme.shadows[4]
                    })
                  },
                  
                  ...(state.ui.accessibility.highContrast && {
                    backgroundColor: '#ffffff',
                    border: '2px solid #000000',
                    color: '#000000',
                    '&:hover': {
                      backgroundColor: '#f0f0f0'
                    }
                  }),
                  
                  ...(isExecuting && {
                    opacity: 0.7,
                    pointerEvents: 'none'
                  })
                }}
                onClick={() => !action.disabled && !isExecuting && handleActionClick(action)}
                role="button"
                tabIndex={action.disabled ? -1 : 0}
                onKeyDown={(e) => {
                  if ((e.key === 'Enter' || e.key === ' ') && !action.disabled && !isExecuting) {
                    e.preventDefault();
                    handleActionClick(action);
                  }
                }}
                aria-label={`${action.label}${action.shortcut ? ` (${action.shortcut})` : ''}`}
              >
                <CardContent sx={{ flexGrow: 1, pb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Box
                      sx={{
                        p: 1,
                        borderRadius: 1,
                        backgroundColor: categoryConfig?.color + '20' || theme.palette.grey[100],
                        color: categoryConfig?.color || theme.palette.text.secondary,
                        mr: 1,
                        
                        ...(state.ui.accessibility.highContrast && {
                          backgroundColor: '#ffffff',
                          border: '1px solid #000000',
                          color: '#000000'
                        })
                      }}
                    >
                      {isExecuting ? <CheckCircle /> : action.icon}
                    </Box>
                    
                    {action.category && (
                      <Chip
                        size="small"
                        label={categoryConfig?.label || action.category}
                        sx={{
                          height: 20,
                          fontSize: '0.6875rem',
                          backgroundColor: categoryConfig?.color + '10',
                          color: categoryConfig?.color,
                          
                          ...(state.ui.accessibility.highContrast && {
                            backgroundColor: '#ffffff',
                            border: '1px solid #000000',
                            color: '#000000'
                          })
                        }}
                      />
                    )}
                  </Box>
                  
                  <Typography
                    variant="subtitle2"
                    gutterBottom
                    sx={{
                      fontWeight: 600,
                      ...(state.ui.accessibility.highContrast && {
                        color: '#000000'
                      })
                    }}
                  >
                    {action.label}
                  </Typography>
                  
                  {!isMobile && action.description && (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                        
                        ...(state.ui.accessibility.highContrast && {
                          color: '#000000'
                        })
                      }}
                    >
                      {action.description}
                    </Typography>
                  )}
                </CardContent>
                
                {action.shortcut && !isMobile && (
                  <CardActions sx={{ pt: 0, px: 2, pb: 2 }}>
                    <Chip
                      size="small"
                      label={action.shortcut}
                      variant="outlined"
                      sx={{
                        fontSize: '0.625rem',
                        height: 20,
                        fontFamily: 'monospace',
                        
                        ...(state.ui.accessibility.highContrast && {
                          backgroundColor: '#ffffff',
                          border: '1px solid #000000',
                          color: '#000000'
                        })
                      }}
                    />
                  </CardActions>
                )}
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {/* Options menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
      >
        <MenuItem onClick={() => setAnchorEl(null)}>
          Customize Actions
        </MenuItem>
        <MenuItem onClick={() => setAnchorEl(null)}>
          Keyboard Shortcuts
        </MenuItem>
        <MenuItem onClick={() => setAnchorEl(null)}>
          Reset to Default
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default QuickActionsWidget;