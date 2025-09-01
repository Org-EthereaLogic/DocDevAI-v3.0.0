/**
 * StatusBarProvider - VS Code status bar integration
 * 
 * Provides status bar updates and controls:
 * - Real-time generation status
 * - Quality analysis progress
 * - Quick action buttons
 * - System health indicators
 * - Background task monitoring
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Chip,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  Badge
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Info,
  PlayArrow,
  Pause,
  Stop,
  MoreHoriz,
  Refresh,
  Settings,
  Notifications
} from '@mui/icons-material';

import { useGlobalState } from '../../core/state-management';
import { eventManager, UIEventType } from '../../core/event-system';

/**
 * Status types
 */
export type StatusType = 'idle' | 'generating' | 'analyzing' | 'processing' | 'error' | 'warning';

/**
 * Status item interface
 */
interface StatusItem {
  id: string;
  type: StatusType;
  message: string;
  progress?: number;
  timestamp: Date;
  details?: string;
  actions?: Array<{
    label: string;
    action: () => void;
  }>;
}

/**
 * Background task interface
 */
interface BackgroundTask {
  id: string;
  name: string;
  status: 'running' | 'completed' | 'failed' | 'paused';
  progress: number;
  startTime: Date;
  estimatedDuration?: number;
}

/**
 * StatusBarProvider component
 */
const StatusBarProvider: React.FC = () => {
  const globalState = useGlobalState();
  const state = globalState.getState();

  const [currentStatus, setCurrentStatus] = useState<StatusItem>({
    id: 'initial',
    type: 'idle',
    message: 'DevDocAI Ready',
    timestamp: new Date()
  });

  const [backgroundTasks, setBackgroundTasks] = useState<BackgroundTask[]>([]);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [notifications, setNotifications] = useState<number>(0);

  // Listen for status updates
  useEffect(() => {
    const unsubscribeStatus = eventManager.subscribe(UIEventType.STATUS_UPDATE, (data) => {
      const statusData = data as Partial<StatusItem>;
      setCurrentStatus(prev => ({
        ...prev,
        ...statusData,
        id: statusData.id || `status-${Date.now()}`,
        timestamp: new Date()
      }));
    });

    const unsubscribeTask = eventManager.subscribe(UIEventType.BACKGROUND_TASK, (data) => {
      const taskData = data as BackgroundTask;
      setBackgroundTasks(prev => {
        const existing = prev.find(t => t.id === taskData.id);
        if (existing) {
          return prev.map(t => t.id === taskData.id ? { ...t, ...taskData } : t);
        }
        return [...prev, taskData];
      });
    });

    return () => {
      unsubscribeStatus();
      unsubscribeTask();
    };
  }, []);

  // Monitor notifications
  useEffect(() => {
    setNotifications(state.ui.notifications.length);
  }, [state.ui.notifications.length]);

  // Clean up completed tasks
  useEffect(() => {
    const cleanupTimer = setInterval(() => {
      setBackgroundTasks(prev => 
        prev.filter(task => 
          task.status !== 'completed' || 
          Date.now() - task.startTime.getTime() < 30000 // Keep completed for 30s
        )
      );
    }, 10000);

    return () => clearInterval(cleanupTimer);
  }, []);

  const getStatusIcon = (type: StatusType) => {
    switch (type) {
      case 'generating':
      case 'analyzing':
      case 'processing':
        return <PlayArrow fontSize="small" />;
      case 'error':
        return <Error fontSize="small" color="error" />;
      case 'warning':
        return <Warning fontSize="small" color="warning" />;
      case 'idle':
      default:
        return <CheckCircle fontSize="small" color="success" />;
    }
  };

  const getStatusColor = (type: StatusType): 'default' | 'primary' | 'success' | 'warning' | 'error' => {
    switch (type) {
      case 'generating':
      case 'analyzing':
      case 'processing':
        return 'primary';
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'idle':
        return 'success';
      default:
        return 'default';
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleQuickAction = (action: string) => {
    switch (action) {
      case 'generate':
        eventManager.emitSimple(UIEventType.QUICK_ACTION, 'status-bar', { action: 'generate' });
        break;
      case 'analyze':
        eventManager.emitSimple(UIEventType.QUICK_ACTION, 'status-bar', { action: 'analyze' });
        break;
      case 'refresh':
        eventManager.emitSimple(UIEventType.QUICK_ACTION, 'status-bar', { action: 'refresh' });
        break;
      case 'settings':
        eventManager.emitSimple(UIEventType.QUICK_ACTION, 'status-bar', { action: 'settings' });
        break;
    }
    handleMenuClose();
  };

  const formatDuration = (ms: number): string => {
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ${seconds % 60}s`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ${minutes % 60}m`;
  };

  // Post message to VS Code extension
  const postStatusToVSCode = useCallback((status: StatusItem) => {
    if (typeof acquireVsCodeApi !== 'undefined') {
      const vscode = acquireVsCodeApi();
      vscode.postMessage({
        type: 'status-update',
        payload: {
          text: status.message,
          tooltip: status.details || status.message,
          color: getStatusColor(status.type),
          progress: status.progress
        }
      });
    }
  }, []);

  // Update VS Code status bar when status changes
  useEffect(() => {
    postStatusToVSCode(currentStatus);
  }, [currentStatus, postStatusToVSCode]);

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        px: 1,
        py: 0.5,
        backgroundColor: 'background.paper',
        borderTop: 1,
        borderColor: 'divider',
        minHeight: 24
      }}
    >
      {/* Current Status */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0, flexGrow: 1 }}>
        {getStatusIcon(currentStatus.type)}
        
        <Typography
          variant="caption"
          sx={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            minWidth: 0
          }}
        >
          {currentStatus.message}
        </Typography>

        {currentStatus.progress !== undefined && (
          <Box sx={{ minWidth: 60, maxWidth: 100 }}>
            <LinearProgress
              variant="determinate"
              value={currentStatus.progress}
              size="small"
              sx={{ height: 4, borderRadius: 2 }}
            />
          </Box>
        )}
      </Box>

      {/* Background Tasks */}
      {backgroundTasks.length > 0 && (
        <Tooltip
          title={
            <Box>
              <Typography variant="caption" gutterBottom>
                Background Tasks:
              </Typography>
              {backgroundTasks.map(task => (
                <Box key={task.id} sx={{ mb: 0.5 }}>
                  <Typography variant="caption">
                    {task.name}: {task.progress}%
                  </Typography>
                  {task.estimatedDuration && (
                    <Typography variant="caption" color="text.secondary">
                      {' '}({formatDuration(task.estimatedDuration)})
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>
          }
        >
          <Chip
            size="small"
            label={backgroundTasks.length}
            color="primary"
            variant="outlined"
            sx={{ height: 20, fontSize: '0.7rem' }}
          />
        </Tooltip>
      )}

      {/* Notifications */}
      {notifications > 0 && (
        <Tooltip title={`${notifications} notifications`}>
          <IconButton size="small">
            <Badge badgeContent={notifications} color="error" max={99}>
              <Notifications fontSize="inherit" />
            </Badge>
          </IconButton>
        </Tooltip>
      )}

      {/* Quick Actions Menu */}
      <Tooltip title="Quick Actions">
        <IconButton size="small" onClick={handleMenuOpen}>
          <MoreHoriz fontSize="inherit" />
        </IconButton>
      </Tooltip>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: { minWidth: 150 }
        }}
      >
        <MenuItem onClick={() => handleQuickAction('generate')}>
          <PlayArrow fontSize="small" sx={{ mr: 1 }} />
          Generate Docs
        </MenuItem>
        <MenuItem onClick={() => handleQuickAction('analyze')}>
          <CheckCircle fontSize="small" sx={{ mr: 1 }} />
          Analyze Quality
        </MenuItem>
        <MenuItem onClick={() => handleQuickAction('refresh')}>
          <Refresh fontSize="small" sx={{ mr: 1 }} />
          Refresh
        </MenuItem>
        <MenuItem onClick={() => handleQuickAction('settings')}>
          <Settings fontSize="small" sx={{ mr: 1 }} />
          Settings
        </MenuItem>
      </Menu>

      {/* Hidden element for VS Code communication */}
      <div 
        id="devdocai-status" 
        data-status={JSON.stringify(currentStatus)}
        style={{ display: 'none' }}
      />
    </Box>
  );
};

export default StatusBarProvider;