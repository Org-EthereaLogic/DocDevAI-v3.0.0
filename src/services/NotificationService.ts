/**
 * DevDocAI v3.0.0 - Notification Service
 * 
 * Service layer for application-wide notifications, alerts, and user communication
 * Provides real-time notifications, toast messages, and system alerts.
 */

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  persistent: boolean; // Whether notification should persist until manually dismissed
  category: string;
  actions?: NotificationAction[];
  metadata?: Record<string, any>;
}

export interface NotificationAction {
  id: string;
  label: string;
  type: 'primary' | 'secondary' | 'danger';
  action: () => void;
}

export interface NotificationPreferences {
  enabled: boolean;
  showToasts: boolean;
  showDesktopNotifications: boolean;
  showEmailAlerts: boolean;
  categories: {
    system: boolean;
    security: boolean;
    generation: boolean;
    analysis: boolean;
    storage: boolean;
  };
  soundEnabled: boolean;
  maxNotifications: number;
}

export interface NotificationStats {
  total: number;
  unread: number;
  byType: Record<string, number>;
  byCategory: Record<string, number>;
  recentActivity: number; // notifications in last 24h
}

type NotificationSubscriber = (notification: Notification) => void;
type NotificationUpdateSubscriber = (notifications: Notification[]) => void;

class NotificationServiceImpl {
  private notifications: Notification[] = [];
  private subscribers: NotificationSubscriber[] = [];
  private updateSubscribers: NotificationUpdateSubscriber[] = [];
  private preferences: NotificationPreferences;
  private initialized = false;

  constructor() {
    this.preferences = {
      enabled: true,
      showToasts: true,
      showDesktopNotifications: false,
      showEmailAlerts: false,
      categories: {
        system: true,
        security: true,
        generation: true,
        analysis: true,
        storage: true,
      },
      soundEnabled: true,
      maxNotifications: 100,
    };
  }

  async initialize(): Promise<void> {
    try {
      console.log('Initializing Notification Service...');
      
      // Load preferences
      await this.loadPreferences();
      
      // Load persisted notifications
      await this.loadNotifications();
      
      // Request desktop notification permission
      await this.requestPermissions();
      
      // Setup cleanup interval
      this.setupCleanupInterval();
      
      this.initialized = true;
      console.log('Notification Service initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Notification Service:', error);
      // Set initialized to true anyway to allow app to continue
      this.initialized = true;
      // Ensure we have default data structures
      if (!this.notifications) {
        this.notifications = [];
      }
      if (!this.subscribers) {
        this.subscribers = [];
      }
      if (!this.updateSubscribers) {
        this.updateSubscribers = [];
      }
      console.log('Notification Service using defaults due to initialization error');
    }
  }

  private async loadPreferences(): Promise<void> {
    try {
      // Safely check if localStorage is available
      if (typeof localStorage !== 'undefined' && localStorage !== null) {
        try {
          const saved = localStorage.getItem('devdocai-notification-prefs');
          if (saved) {
            this.preferences = { ...this.preferences, ...JSON.parse(saved) };
          }
        } catch (storageError) {
          console.warn('localStorage access failed:', storageError);
        }
      }
    } catch (error) {
      console.warn('Failed to load notification preferences:', error);
    }
  }

  private async savePreferences(): Promise<void> {
    try {
      // Safely check if localStorage is available
      if (typeof localStorage !== 'undefined' && localStorage !== null) {
        try {
          localStorage.setItem('devdocai-notification-prefs', JSON.stringify(this.preferences));
        } catch (storageError) {
          console.warn('localStorage save failed:', storageError);
        }
      }
    } catch (error) {
      console.error('Failed to save notification preferences:', error);
    }
  }

  private async loadNotifications(): Promise<void> {
    try {
      // Safely check if localStorage is available
      if (typeof localStorage !== 'undefined' && localStorage !== null) {
        try {
          const saved = localStorage.getItem('devdocai-notifications');
          if (saved) {
            const loadedNotifications = JSON.parse(saved);
            this.notifications = loadedNotifications.map((n: any) => ({
              ...n,
              timestamp: new Date(n.timestamp),
            }));
            
            // Remove old notifications
            const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
            this.notifications = this.notifications.filter(n => 
              n.persistent || n.timestamp > oneDayAgo
            );
          }
        } catch (storageError) {
          console.warn('localStorage access failed:', storageError);
          this.notifications = [];
        }
      }
    } catch (error) {
      console.warn('Failed to load notifications:', error);
      this.notifications = [];
    }
  }

  private async saveNotifications(): Promise<void> {
    try {
      // Safely check if localStorage is available
      if (typeof localStorage !== 'undefined' && localStorage !== null) {
        try {
          localStorage.setItem('devdocai-notifications', JSON.stringify(this.notifications));
        } catch (storageError) {
          console.warn('localStorage save failed:', storageError);
        }
      }
    } catch (error) {
      console.error('Failed to save notifications:', error);
    }
  }

  private async requestPermissions(): Promise<void> {
    try {
      if (this.preferences.showDesktopNotifications && typeof window !== 'undefined' && 'Notification' in window) {
        try {
          const permission = await Notification.requestPermission();
          if (permission === 'granted') {
            console.log('Desktop notification permission granted');
          } else {
            console.warn('Desktop notification permission denied');
            this.preferences.showDesktopNotifications = false;
          }
        } catch (error) {
          console.warn('Failed to request notification permission:', error);
          this.preferences.showDesktopNotifications = false;
        }
      }
    } catch (error) {
      console.warn('Failed to check notification permissions:', error);
      this.preferences.showDesktopNotifications = false;
    }
  }

  private setupCleanupInterval(): void {
    // Clean up old notifications every hour
    setInterval(() => {
      this.cleanupOldNotifications();
    }, 60 * 60 * 1000);
  }

  private cleanupOldNotifications(): void {
    const before = this.notifications.length;
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    
    this.notifications = this.notifications.filter(n => 
      n.persistent || n.timestamp > oneDayAgo
    );
    
    // Limit total notifications
    if (this.notifications.length > this.preferences.maxNotifications) {
      this.notifications = this.notifications
        .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
        .slice(0, this.preferences.maxNotifications);
    }
    
    if (before > this.notifications.length) {
      console.log(`Cleaned up ${before - this.notifications.length} old notifications`);
      this.saveNotifications();
      this.notifyUpdateSubscribers();
    }
  }

  notify(
    type: Notification['type'],
    title: string,
    message: string,
    options: {
      category?: string;
      persistent?: boolean;
      actions?: NotificationAction[];
      metadata?: Record<string, any>;
    } = {}
  ): string {
    if (!this.preferences.enabled) {
      return '';
    }

    const category = options.category || 'system';
    
    // Check if category is enabled
    if (!this.preferences.categories[category as keyof typeof this.preferences.categories]) {
      return '';
    }

    const notification: Notification = {
      id: `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      title,
      message,
      timestamp: new Date(),
      read: false,
      persistent: options.persistent || false,
      category,
      actions: options.actions,
      metadata: options.metadata,
    };

    // Add to notifications list
    this.notifications.unshift(notification);

    // Save notifications
    this.saveNotifications();

    // Notify subscribers
    this.subscribers.forEach(callback => {
      try {
        callback(notification);
      } catch (error) {
        console.error('Error in notification subscriber:', error);
      }
    });

    this.notifyUpdateSubscribers();

    // Show toast notification
    if (this.preferences.showToasts) {
      this.showToastNotification(notification);
    }

    // Show desktop notification
    if (this.preferences.showDesktopNotifications) {
      this.showDesktopNotification(notification);
    }

    // Play sound
    if (this.preferences.soundEnabled) {
      this.playNotificationSound(type);
    }

    console.log(`Notification sent: ${type} - ${title}`);
    return notification.id;
  }

  private showToastNotification(notification: Notification): void {
    // In a real implementation, this would integrate with a toast library
    // For now, just log the notification
    console.log('Toast notification:', {
      type: notification.type,
      title: notification.title,
      message: notification.message,
    });
  }

  private showDesktopNotification(notification: Notification): void {
    try {
      if (typeof window !== 'undefined' && 'Notification' in window && Notification.permission === 'granted') {
        try {
          const desktopNotification = new Notification(notification.title, {
            body: notification.message,
            icon: '/favicon.ico',
            tag: notification.id,
          });

          desktopNotification.onclick = () => {
            window.focus();
            this.markAsRead(notification.id);
            desktopNotification.close();
          };

          // Auto-close after 5 seconds
          setTimeout(() => {
            desktopNotification.close();
          }, 5000);
        } catch (error) {
          console.error('Failed to show desktop notification:', error);
        }
      }
    } catch (error) {
      console.warn('Desktop notifications not available:', error);
    }
  }

  private playNotificationSound(type: Notification['type']): void {
    // In a real implementation, this would play different sounds for different types
    // For now, just use the default browser sound
    try {
      if (typeof window !== 'undefined' && 'Audio' in window) {
        try {
          // Different sounds for different notification types
          const soundFile = type === 'error' ? 'error.mp3' : 
                            type === 'success' ? 'success.mp3' : 'notification.mp3';
          
          const audio = new Audio(`/sounds/${soundFile}`);
          audio.volume = 0.3;
          audio.play().catch(() => {
            // Silently fail if audio can't be played
          });
        } catch (error) {
          // Silently fail
        }
      }
    } catch (error) {
      // Silently fail - audio not available
    }
  }

  // Convenience methods for different notification types
  info(title: string, message: string, options?: Parameters<typeof this.notify>[3]): string {
    return this.notify('info', title, message, options);
  }

  success(title: string, message: string, options?: Parameters<typeof this.notify>[3]): string {
    return this.notify('success', title, message, options);
  }

  warning(title: string, message: string, options?: Parameters<typeof this.notify>[3]): string {
    return this.notify('warning', title, message, options);
  }

  error(title: string, message: string, options?: Parameters<typeof this.notify>[3]): string {
    return this.notify('error', title, message, options);
  }

  // System-specific notification methods
  systemNotification(title: string, message: string, persistent = false): string {
    return this.notify('info', title, message, { category: 'system', persistent });
  }

  securityAlert(title: string, message: string, actions?: NotificationAction[]): string {
    return this.notify('warning', title, message, { 
      category: 'security', 
      persistent: true, 
      actions 
    });
  }

  generationComplete(documentName: string): string {
    return this.notify('success', 'Generation Complete', 
      `Document "${documentName}" has been generated successfully.`, 
      { category: 'generation' }
    );
  }

  analysisComplete(documentName: string, score: number): string {
    const type = score >= 80 ? 'success' : score >= 60 ? 'warning' : 'error';
    return this.notify(type, 'Analysis Complete',
      `Document "${documentName}" analysis finished with score: ${score}/100`,
      { category: 'analysis', metadata: { score } }
    );
  }

  // Notification management
  markAsRead(notificationId: string): boolean {
    const notification = this.notifications.find(n => n.id === notificationId);
    if (notification && !notification.read) {
      notification.read = true;
      this.saveNotifications();
      this.notifyUpdateSubscribers();
      return true;
    }
    return false;
  }

  markAllAsRead(): void {
    let hasChanges = false;
    this.notifications.forEach(n => {
      if (!n.read) {
        n.read = true;
        hasChanges = true;
      }
    });

    if (hasChanges) {
      this.saveNotifications();
      this.notifyUpdateSubscribers();
    }
  }

  dismiss(notificationId: string): boolean {
    const index = this.notifications.findIndex(n => n.id === notificationId);
    if (index !== -1) {
      this.notifications.splice(index, 1);
      this.saveNotifications();
      this.notifyUpdateSubscribers();
      return true;
    }
    return false;
  }

  dismissAll(): void {
    if (this.notifications.length > 0) {
      this.notifications = [];
      this.saveNotifications();
      this.notifyUpdateSubscribers();
    }
  }

  getNotifications(): Notification[] {
    return [...this.notifications];
  }

  getUnreadNotifications(): Notification[] {
    return this.notifications.filter(n => !n.read);
  }

  getNotificationStats(): NotificationStats {
    const total = this.notifications.length;
    const unread = this.notifications.filter(n => !n.read).length;
    
    const byType: Record<string, number> = {};
    const byCategory: Record<string, number> = {};
    
    this.notifications.forEach(n => {
      byType[n.type] = (byType[n.type] || 0) + 1;
      byCategory[n.category] = (byCategory[n.category] || 0) + 1;
    });

    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const recentActivity = this.notifications.filter(n => n.timestamp > oneDayAgo).length;

    return { total, unread, byType, byCategory, recentActivity };
  }

  // Subscription management
  subscribe(callback: NotificationSubscriber): () => void {
    this.subscribers.push(callback);
    return () => {
      const index = this.subscribers.indexOf(callback);
      if (index !== -1) {
        this.subscribers.splice(index, 1);
      }
    };
  }

  subscribeToUpdates(callback: NotificationUpdateSubscriber): () => void {
    this.updateSubscribers.push(callback);
    return () => {
      const index = this.updateSubscribers.indexOf(callback);
      if (index !== -1) {
        this.updateSubscribers.splice(index, 1);
      }
    };
  }

  private notifyUpdateSubscribers(): void {
    this.updateSubscribers.forEach(callback => {
      try {
        callback([...this.notifications]);
      } catch (error) {
        console.error('Error in notification update subscriber:', error);
      }
    });
  }

  // Preferences management
  getPreferences(): NotificationPreferences {
    return { ...this.preferences };
  }

  updatePreferences(updates: Partial<NotificationPreferences>): void {
    this.preferences = { ...this.preferences, ...updates };
    this.savePreferences();
    
    // Re-request desktop permission if enabled
    if (updates.showDesktopNotifications && !this.preferences.showDesktopNotifications) {
      this.requestPermissions();
    }
    
    console.log('Notification preferences updated:', updates);
  }

  isInitialized(): boolean {
    return this.initialized;
  }
}

// Export singleton instance
export const NotificationService = new NotificationServiceImpl();
export default NotificationService;