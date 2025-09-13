import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useNotificationStore = defineStore('notification', () => {
  // State
  const notifications = ref([]);
  const maxNotifications = ref(5);
  const defaultDuration = ref(5000); // 5 seconds
  let notificationId = 0;

  // Notification types
  const types = {
    SUCCESS: 'success',
    ERROR: 'error',
    WARNING: 'warning',
    INFO: 'info'
  };

  // Computed
  const activeNotifications = computed(() =>
    notifications.value.filter(n => !n.dismissed)
  );

  const hasNotifications = computed(() =>
    activeNotifications.value.length > 0
  );

  const latestNotification = computed(() =>
    activeNotifications.value[activeNotifications.value.length - 1]
  );

  // Actions
  const addNotification = (notification) => {
    const id = ++notificationId;

    const newNotification = {
      id,
      type: notification.type || types.INFO,
      title: notification.title || '',
      message: notification.message || '',
      duration: notification.duration !== undefined ? notification.duration : defaultDuration.value,
      timestamp: new Date().toISOString(),
      dismissed: false,
      actions: notification.actions || [],
      persistent: notification.persistent || false,
      icon: notification.icon || null
    };

    // Add to notifications array
    notifications.value.push(newNotification);

    // Limit number of notifications
    if (notifications.value.length > maxNotifications.value) {
      notifications.value = notifications.value.slice(-maxNotifications.value);
    }

    // Auto-dismiss after duration (unless persistent)
    if (!newNotification.persistent && newNotification.duration > 0) {
      setTimeout(() => {
        dismissNotification(id);
      }, newNotification.duration);
    }

    return id;
  };

  const addSuccess = (title, message, options = {}) => {
    return addNotification({
      ...options,
      type: types.SUCCESS,
      title,
      message,
      icon: options.icon || 'check-circle'
    });
  };

  const addError = (title, message, options = {}) => {
    return addNotification({
      ...options,
      type: types.ERROR,
      title,
      message,
      duration: options.duration || 10000, // Errors stay longer
      icon: options.icon || 'x-circle'
    });
  };

  const addWarning = (title, message, options = {}) => {
    return addNotification({
      ...options,
      type: types.WARNING,
      title,
      message,
      icon: options.icon || 'exclamation-triangle'
    });
  };

  const addInfo = (title, message, options = {}) => {
    return addNotification({
      ...options,
      type: types.INFO,
      title,
      message,
      icon: options.icon || 'information-circle'
    });
  };

  const dismissNotification = (id) => {
    const notification = notifications.value.find(n => n.id === id);
    if (notification) {
      notification.dismissed = true;

      // Remove from array after animation
      setTimeout(() => {
        notifications.value = notifications.value.filter(n => n.id !== id);
      }, 300);
    }
  };

  const dismissAll = () => {
    notifications.value.forEach(n => {
      n.dismissed = true;
    });

    // Clear array after animation
    setTimeout(() => {
      notifications.value = [];
    }, 300);
  };

  const clearNotifications = () => {
    notifications.value = [];
  };

  // Action handlers for notifications with actions
  const handleAction = (notificationId, actionIndex) => {
    const notification = notifications.value.find(n => n.id === notificationId);
    if (notification && notification.actions[actionIndex]) {
      const action = notification.actions[actionIndex];

      // Execute action callback if provided
      if (action.callback && typeof action.callback === 'function') {
        action.callback();
      }

      // Dismiss notification if action specifies
      if (action.dismiss !== false) {
        dismissNotification(notificationId);
      }
    }
  };

  // Progress notification for long-running operations
  const addProgressNotification = (title, initialMessage = 'Starting...') => {
    const id = addNotification({
      type: types.INFO,
      title,
      message: initialMessage,
      persistent: true,
      progress: 0
    });

    return {
      id,
      update: (progress, message) => {
        const notification = notifications.value.find(n => n.id === id);
        if (notification) {
          notification.progress = progress;
          if (message) {
            notification.message = message;
          }
        }
      },
      complete: (message = 'Complete!') => {
        const notification = notifications.value.find(n => n.id === id);
        if (notification) {
          notification.type = types.SUCCESS;
          notification.message = message;
          notification.progress = 100;
          notification.persistent = false;

          // Auto-dismiss after showing complete
          setTimeout(() => {
            dismissNotification(id);
          }, 3000);
        }
      },
      error: (message = 'Operation failed') => {
        const notification = notifications.value.find(n => n.id === id);
        if (notification) {
          notification.type = types.ERROR;
          notification.message = message;
          notification.persistent = false;

          // Keep error visible longer
          setTimeout(() => {
            dismissNotification(id);
          }, 10000);
        }
      }
    };
  };

  // Settings
  const updateSettings = (settings) => {
    if (settings.maxNotifications !== undefined) {
      maxNotifications.value = settings.maxNotifications;
    }
    if (settings.defaultDuration !== undefined) {
      defaultDuration.value = settings.defaultDuration;
    }
  };

  // Reset store
  const $reset = () => {
    notifications.value = [];
    notificationId = 0;
  };

  return {
    // State
    notifications,
    maxNotifications,
    defaultDuration,
    types,

    // Computed
    activeNotifications,
    hasNotifications,
    latestNotification,

    // Actions
    addNotification,
    addSuccess,
    addError,
    addWarning,
    addInfo,
    dismissNotification,
    dismissAll,
    clearNotifications,
    handleAction,
    addProgressNotification,
    updateSettings,
    $reset
  };
});
