/**
 * ToastNotification - Toast notifications and alert systems
 * 
 * Provides user feedback through:
 * - Toast notifications with auto-dismiss
 * - Alert banners for persistent messages
 * - Action confirmations
 * - System status updates
 * - Accessibility announcements
 */

import React, { useState, useEffect } from 'react';
import {
  Snackbar,
  Alert,
  AlertTitle,
  IconButton,
  Slide,
  SlideProps,
  useTheme
} from '@mui/material';
import {
  Close,
  CheckCircle,
  Error,
  Warning,
  Info
} from '@mui/icons-material';

import { useGlobalState } from '../../core/state-management';
import { eventManager, UIEventType } from '../../core/event-system';
import { accessibilityManager } from '../../core/accessibility';

/**
 * Toast notification types
 */
export type ToastType = 'success' | 'error' | 'warning' | 'info';

/**
 * Toast notification interface
 */
export interface ToastNotification {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
  persistent?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
  onClose?: () => void;
}

/**
 * Props interface
 */
interface ToastNotificationProps {
  notification: ToastNotification;
  onClose: (id: string) => void;
}

/**
 * Slide transition component
 */
const SlideTransition = (props: SlideProps) => {
  return <Slide {...props} direction="up" />;
};

/**
 * Get icon for notification type
 */
const getNotificationIcon = (type: ToastType) => {
  switch (type) {
    case 'success':
      return <CheckCircle />;
    case 'error':
      return <Error />;
    case 'warning':
      return <Warning />;
    case 'info':
    default:
      return <Info />;
  }
};

/**
 * Single toast notification component
 */
const SingleToastNotification: React.FC<ToastNotificationProps> = ({
  notification,
  onClose
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();

  const [open, setOpen] = useState(true);

  // Auto-dismiss after duration
  useEffect(() => {
    if (!notification.persistent && notification.duration !== 0) {
      const duration = notification.duration || 5000;
      const timer = setTimeout(() => {
        handleClose();
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [notification.duration, notification.persistent]);

  // Announce to screen reader
  useEffect(() => {
    if (open) {
      const message = notification.title 
        ? `${notification.title}: ${notification.message}`
        : notification.message;
      
      accessibilityManager.announceToScreenReader(message, notification.type);
    }
  }, [open, notification]);

  const handleClose = (event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }

    setOpen(false);
    
    // Call notification's onClose callback
    if (notification.onClose) {
      notification.onClose();
    }
    
    // Emit close event
    eventManager.emitSimple(UIEventType.NOTIFICATION_DISMISSED, 'toast', {
      notificationId: notification.id,
      type: notification.type
    });

    // Remove from global state after animation
    setTimeout(() => {
      onClose(notification.id);
    }, 150);
  };

  const handleAction = () => {
    if (notification.action) {
      notification.action.onClick();
    }
    handleClose();
  };

  return (
    <Snackbar
      open={open}
      autoHideDuration={notification.persistent ? null : (notification.duration || 5000)}
      onClose={handleClose}
      TransitionComponent={SlideTransition}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      sx={{
        // Reduce motion for accessibility
        ...(state.ui.accessibility.reduceMotion && {
          '& .MuiSnackbar-root': {
            transition: 'none'
          }
        })
      }}
    >
      <Alert
        severity={notification.type}
        icon={state.ui.accessibility.enhancedSupport ? getNotificationIcon(notification.type) : undefined}
        action={
          <>
            {notification.action && (
              <IconButton
                color="inherit"
                size="small"
                onClick={handleAction}
                aria-label={notification.action.label}
              >
                {notification.action.label}
              </IconButton>
            )}
            <IconButton
              color="inherit"
              size="small"
              onClick={handleClose}
              aria-label="Close notification"
            >
              <Close fontSize="inherit" />
            </IconButton>
          </>
        }
        sx={{
          width: '100%',
          maxWidth: 400,
          
          ...(state.ui.accessibility.highContrast && {
            backgroundColor: notification.type === 'error' ? '#ffcccc' : '#ffffff',
            color: '#000000',
            border: '2px solid #000000',
            '& .MuiAlert-icon': {
              color: '#000000'
            }
          })
        }}
      >
        {notification.title && (
          <AlertTitle>{notification.title}</AlertTitle>
        )}
        {notification.message}
      </Alert>
    </Snackbar>
  );
};

/**
 * Toast notification manager component
 */
const ToastNotificationManager: React.FC = () => {
  const globalState = useGlobalState();
  const [notifications, setNotifications] = useState<ToastNotification[]>([]);

  useEffect(() => {
    // Subscribe to global state notifications
    const unsubscribe = globalState.subscribe((state) => {
      if (state.ui.notifications.length !== notifications.length) {
        setNotifications([...state.ui.notifications]);
      }
    });

    return unsubscribe;
  }, [globalState, notifications.length]);

  const handleCloseNotification = (id: string) => {
    globalState.removeNotification(id);
  };

  return (
    <>
      {notifications.map((notification) => (
        <SingleToastNotification
          key={notification.id}
          notification={notification}
          onClose={handleCloseNotification}
        />
      ))}
    </>
  );
};

export default ToastNotificationManager;