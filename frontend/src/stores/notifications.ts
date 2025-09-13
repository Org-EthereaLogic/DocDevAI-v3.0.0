// Notifications Store - Global Notification System

import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface Notification {
  id: string;
  type: NotificationType;
  title?: string;
  message: string;
  description?: string;
  duration?: number;
  persistent?: boolean;
  actions?: NotificationAction[];
  metadata?: Record<string, any>;
  createdAt: Date;
  readAt?: Date;
  dismissedAt?: Date;
}

export interface NotificationAction {
  label: string;
  action: () => void | Promise<void>;
  style?: 'primary' | 'secondary' | 'danger';
  loading?: boolean;
}

export interface NotificationOptions {
  type?: NotificationType;
  title?: string;
  description?: string;
  duration?: number;
  persistent?: boolean;
  actions?: NotificationAction[];
  metadata?: Record<string, any>;
  playSound?: boolean;
}

export const useNotificationsStore = defineStore('notifications', () => {
  // State
  const notifications = ref<Notification[]>([]);
  const maxNotifications = ref(50);
  const defaultDuration = ref(5000);
  const soundEnabled = ref(false);

  // Getters
  const activeNotifications = computed(() =>
    notifications.value.filter(n => !n.dismissedAt)
  );

  const unreadNotifications = computed(() =>
    notifications.value.filter(n => !n.readAt && !n.dismissedAt)
  );

  const persistentNotifications = computed(() =>
    activeNotifications.value.filter(n => n.persistent)
  );

  const temporaryNotifications = computed(() =>
    activeNotifications.value.filter(n => !n.persistent)
  );

  const notificationsByType = computed(() => {
    const byType: Record<NotificationType, Notification[]> = {
      info: [],
      success: [],
      warning: [],
      error: [],
    };

    activeNotifications.value.forEach(notification => {
      byType[notification.type].push(notification);
    });

    return byType;
  });

  const unreadCount = computed(() => unreadNotifications.value.length);

  const hasUnread = computed(() => unreadCount.value > 0);

  const recentNotifications = computed(() =>
    notifications.value
      .filter(n => !n.dismissedAt)
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
      .slice(0, 10)
  );

  // Actions
  const generateId = (): string => {
    return `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  const addNotification = (
    message: string,
    options: NotificationOptions = {}
  ): Notification => {
    const notification: Notification = {
      id: generateId(),
      type: options.type || 'info',
      title: options.title,
      message,
      description: options.description,
      duration: options.duration ?? defaultDuration.value,
      persistent: options.persistent || false,
      actions: options.actions || [],
      metadata: options.metadata || {},
      createdAt: new Date(),
    };

    notifications.value.unshift(notification);

    // Trim notifications if exceeding max
    if (notifications.value.length > maxNotifications.value) {
      notifications.value = notifications.value.slice(0, maxNotifications.value);
    }

    // Auto-dismiss non-persistent notifications
    if (!notification.persistent && notification.duration > 0) {
      setTimeout(() => {
        dismissNotification(notification.id);
      }, notification.duration);
    }

    // Play sound if enabled
    if (soundEnabled.value && options.playSound !== false) {
      playNotificationSound(notification.type);
    }

    return notification;
  };

  // Convenience methods for different types
  const info = (message: string, options: Omit<NotificationOptions, 'type'> = {}) =>
    addNotification(message, { ...options, type: 'info' });

  const success = (message: string, options: Omit<NotificationOptions, 'type'> = {}) =>
    addNotification(message, { ...options, type: 'success' });

  const warning = (message: string, options: Omit<NotificationOptions, 'type'> = {}) =>
    addNotification(message, { ...options, type: 'warning' });

  const error = (message: string, options: Omit<NotificationOptions, 'type'> = {}) =>
    addNotification(message, { ...options, type: 'error', persistent: true });

  // Management actions
  const getNotification = (id: string): Notification | undefined => {
    return notifications.value.find(n => n.id === id);
  };

  const markAsRead = (id: string) => {
    const notification = getNotification(id);
    if (notification && !notification.readAt) {
      notification.readAt = new Date();
    }
  };

  const markAllAsRead = () => {
    const now = new Date();
    notifications.value.forEach(notification => {
      if (!notification.readAt && !notification.dismissedAt) {
        notification.readAt = now;
      }
    });
  };

  const dismissNotification = (id: string) => {
    const notification = getNotification(id);
    if (notification && !notification.dismissedAt) {
      notification.dismissedAt = new Date();
      if (!notification.readAt) {
        notification.readAt = new Date();
      }
    }
  };

  const dismissAll = () => {
    const now = new Date();
    notifications.value.forEach(notification => {
      if (!notification.dismissedAt) {
        notification.dismissedAt = now;
        if (!notification.readAt) {
          notification.readAt = now;
        }
      }
    });
  };

  const dismissByType = (type: NotificationType) => {
    const now = new Date();
    notifications.value
      .filter(n => n.type === type && !n.dismissedAt)
      .forEach(notification => {
        notification.dismissedAt = now;
        if (!notification.readAt) {
          notification.readAt = now;
        }
      });
  };

  const removeNotification = (id: string) => {
    const index = notifications.value.findIndex(n => n.id === id);
    if (index !== -1) {
      notifications.value.splice(index, 1);
    }
  };

  const clearAll = () => {
    notifications.value = [];
  };

  const clearRead = () => {
    notifications.value = notifications.value.filter(n => !n.readAt || !n.dismissedAt);
  };

  const clearOlderThan = (hours: number) => {
    const cutoff = new Date(Date.now() - hours * 60 * 60 * 1000);
    notifications.value = notifications.value.filter(n => n.createdAt >= cutoff);
  };

  // Sound management
  const setSoundEnabled = (enabled: boolean) => {
    soundEnabled.value = enabled;
  };

  const playNotificationSound = (type: NotificationType) => {
    if (!soundEnabled.value) return;

    // Simple audio feedback using Web Audio API
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      // Different frequencies for different types
      const frequencies = {
        info: 800,
        success: 1000,
        warning: 600,
        error: 400,
      };

      oscillator.frequency.setValueAtTime(frequencies[type], audioContext.currentTime);
      oscillator.type = 'sine';

      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
      console.warn('Failed to play notification sound:', error);
    }
  };

  // Configuration
  const setMaxNotifications = (max: number) => {
    maxNotifications.value = max;
    if (notifications.value.length > max) {
      notifications.value = notifications.value.slice(0, max);
    }
  };

  const setDefaultDuration = (duration: number) => {
    defaultDuration.value = duration;
  };

  // Batch operations
  const addBatch = (items: Array<{ message: string; options?: NotificationOptions }>) => {
    items.forEach(item => addNotification(item.message, item.options));
  };

  // Error handling helpers
  const handleApiError = (error: any, context?: string) => {
    const message = error?.message || 'An unexpected error occurred';
    const title = context ? `Error in ${context}` : 'Error';

    addNotification(message, {
      type: 'error',
      title,
      persistent: true,
      actions: [
        {
          label: 'Retry',
          action: () => {
            // This would be implemented by the calling component
            console.log('Retry action triggered');
          },
          style: 'primary',
        },
        {
          label: 'Report Issue',
          action: () => {
            // This would open a support/feedback form
            console.log('Report issue action triggered');
          },
          style: 'secondary',
        },
      ],
      metadata: {
        error: error,
        context: context,
        timestamp: new Date().toISOString(),
      },
    });
  };

  const handleSuccess = (message: string, context?: string) => {
    addNotification(message, {
      type: 'success',
      title: context ? `${context} Successful` : undefined,
      duration: 3000,
    });
  };

  return {
    // State
    notifications: readonly(notifications),
    maxNotifications: readonly(maxNotifications),
    defaultDuration: readonly(defaultDuration),
    soundEnabled: readonly(soundEnabled),

    // Getters
    activeNotifications,
    unreadNotifications,
    persistentNotifications,
    temporaryNotifications,
    notificationsByType,
    unreadCount,
    hasUnread,
    recentNotifications,

    // Actions
    addNotification,
    info,
    success,
    warning,
    error,
    getNotification,
    markAsRead,
    markAllAsRead,
    dismissNotification,
    dismissAll,
    dismissByType,
    removeNotification,
    clearAll,
    clearRead,
    clearOlderThan,
    setSoundEnabled,
    setMaxNotifications,
    setDefaultDuration,
    addBatch,
    handleApiError,
    handleSuccess,
  };
});

// Readonly helper
function readonly<T>(ref: Ref<T>): Readonly<Ref<T>> {
  return ref as Readonly<Ref<T>>;
}

export type NotificationsStore = ReturnType<typeof useNotificationsStore>;