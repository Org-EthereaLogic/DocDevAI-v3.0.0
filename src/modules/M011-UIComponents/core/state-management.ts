/**
 * M011 State Management - Centralized state management for UI components
 * 
 * Provides a privacy-first state management solution that keeps all data
 * local and integrates with the Python backend modules M001-M010.
 */

import { IStateManager } from './interfaces';

/**
 * Type-safe state manager implementation
 */
export class StateManager<T> implements IStateManager {
  private state: T;
  private subscribers = new Set<(state: T) => void>();
  private readonly stateKey: string;

  constructor(initialState: T, stateKey: string) {
    this.state = initialState;
    this.stateKey = stateKey;
  }

  /**
   * Get current state
   */
  public getState<U = T>(): U {
    return this.state as unknown as U;
  }

  /**
   * Update state and notify subscribers
   */
  public setState<U = T>(newState: Partial<U>): void {
    this.state = { ...this.state, ...newState } as T;
    this.notifySubscribers();
  }

  /**
   * Subscribe to state changes
   */
  public subscribe<U = T>(callback: (state: U) => void): () => void {
    const wrappedCallback = (state: T) => callback(state as unknown as U);
    this.subscribers.add(wrappedCallback);

    // Return unsubscribe function
    return () => {
      this.subscribers.delete(wrappedCallback);
    };
  }

  /**
   * Clear all state
   */
  public clear(): void {
    this.state = {} as T;
    this.notifySubscribers();
  }

  /**
   * Notify all subscribers of state changes
   */
  private notifySubscribers(): void {
    this.subscribers.forEach(callback => {
      try {
        callback(this.state);
      } catch (error) {
        console.error(`[StateManager:${this.stateKey}] Subscriber error:`, error);
      }
    });
  }

  /**
   * Get number of subscribers
   */
  public getSubscriberCount(): number {
    return this.subscribers.size;
  }
}

/**
 * Application-wide state interface
 */
export interface AppState {
  // User interface state
  ui: UIState;
  
  // Backend integration state
  backend: BackendState;
  
  // Document and project state
  documents: DocumentState;
  
  // Settings and configuration
  settings: SettingsState;
  
  // Error and notification state
  notifications: NotificationState;
}

/**
 * UI-specific state
 */
export interface UIState {
  theme: 'light' | 'dark' | 'high-contrast';
  sidebarOpen: boolean;
  activeView: string;
  loading: boolean;
  accessibility: {
    reducedMotion: boolean;
    highContrast: boolean;
    fontSize: 'small' | 'normal' | 'large' | 'xl';
    keyboardNavigation: boolean;
  };
  responsive: {
    breakpoint: 'mobile' | 'tablet' | 'desktop' | 'wide';
    orientation: 'portrait' | 'landscape';
  };
}

/**
 * Backend integration state
 */
export interface BackendState {
  connectionStatus: 'connected' | 'connecting' | 'disconnected' | 'error';
  moduleStatus: {
    [moduleName: string]: {
      available: boolean;
      version: string;
      health: 'healthy' | 'degraded' | 'error';
      lastCheck: number;
    };
  };
  pendingRequests: number;
  lastSyncTime: number;
}

/**
 * Document and project state
 */
export interface DocumentState {
  activeProject?: string;
  documents: {
    [documentId: string]: {
      id: string;
      name: string;
      type: string;
      status: 'draft' | 'ready' | 'error';
      qualityScore: number;
      lastModified: number;
      content?: string;
    };
  };
  documentHealth: {
    overall: number;
    byType: { [type: string]: number };
    trending: 'up' | 'down' | 'stable';
  };
  trackingMatrix: {
    nodes: any[];
    edges: any[];
    lastUpdated: number;
  };
}

/**
 * Settings and configuration state
 */
export interface SettingsState {
  privacy: {
    mode: 'local_only' | 'hybrid' | 'cloud';
    telemetryEnabled: boolean;
    cloudFeaturesEnabled: boolean;
  };
  performance: {
    memoryMode: 'baseline' | 'standard' | 'enhanced' | 'performance';
    cacheEnabled: boolean;
    batchSize: number;
  };
  quality: {
    qualityGate: number;
    autoEnhancement: boolean;
    qualityTarget: number;
  };
  integration: {
    vscodeEnabled: boolean;
    gitIntegration: boolean;
    autoSave: boolean;
  };
}

/**
 * Notification and error state
 */
export interface NotificationState {
  notifications: Notification[];
  errors: ErrorInfo[];
  lastCleared: number;
}

/**
 * Notification interface
 */
export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: number;
  persistent?: boolean;
  actions?: NotificationAction[];
}

/**
 * Notification action
 */
export interface NotificationAction {
  label: string;
  action: string;
  primary?: boolean;
}

/**
 * Error information
 */
export interface ErrorInfo {
  id: string;
  message: string;
  stack?: string;
  module?: string;
  timestamp: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  context?: any;
}

/**
 * Global state manager instance
 */
export class GlobalStateManager {
  private static instance: GlobalStateManager;
  private stateManager: StateManager<AppState>;
  private initialized = false;

  private constructor() {
    const initialState: AppState = this.getInitialState();
    this.stateManager = new StateManager(initialState, 'app');
  }

  /**
   * Get singleton instance
   */
  public static getInstance(): GlobalStateManager {
    if (!GlobalStateManager.instance) {
      GlobalStateManager.instance = new GlobalStateManager();
    }
    return GlobalStateManager.instance;
  }

  /**
   * Initialize state manager
   */
  public initialize(): void {
    if (this.initialized) return;

    // Load persisted state if available (respecting privacy settings)
    this.loadPersistedState();
    
    // Setup auto-save for non-sensitive state
    this.setupAutoSave();
    
    this.initialized = true;
  }

  /**
   * Get current application state
   */
  public getState(): AppState {
    return this.stateManager.getState();
  }

  /**
   * Update application state
   */
  public setState(updates: Partial<AppState>): void {
    this.stateManager.setState(updates);
  }

  /**
   * Subscribe to state changes
   */
  public subscribe(callback: (state: AppState) => void): () => void {
    return this.stateManager.subscribe(callback);
  }

  /**
   * Update UI state
   */
  public updateUI(updates: Partial<UIState>): void {
    const currentState = this.getState();
    this.setState({
      ui: { ...currentState.ui, ...updates }
    });
  }

  /**
   * Update backend state
   */
  public updateBackend(updates: Partial<BackendState>): void {
    const currentState = this.getState();
    this.setState({
      backend: { ...currentState.backend, ...updates }
    });
  }

  /**
   * Update document state
   */
  public updateDocuments(updates: Partial<DocumentState>): void {
    const currentState = this.getState();
    this.setState({
      documents: { ...currentState.documents, ...updates }
    });
  }

  /**
   * Add notification
   */
  public addNotification(notification: Omit<Notification, 'id' | 'timestamp'>): void {
    const currentState = this.getState();
    const newNotification: Notification = {
      ...notification,
      id: `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now()
    };

    this.setState({
      notifications: {
        ...currentState.notifications,
        notifications: [...currentState.notifications.notifications, newNotification]
      }
    });
  }

  /**
   * Remove notification
   */
  public removeNotification(id: string): void {
    const currentState = this.getState();
    this.setState({
      notifications: {
        ...currentState.notifications,
        notifications: currentState.notifications.notifications.filter(n => n.id !== id)
      }
    });
  }

  /**
   * Add error
   */
  public addError(error: Omit<ErrorInfo, 'id' | 'timestamp'>): void {
    const currentState = this.getState();
    const newError: ErrorInfo = {
      ...error,
      id: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now()
    };

    this.setState({
      notifications: {
        ...currentState.notifications,
        errors: [...currentState.notifications.errors, newError]
      }
    });
  }

  /**
   * Clear all notifications and errors
   */
  public clearNotifications(): void {
    this.setState({
      notifications: {
        notifications: [],
        errors: [],
        lastCleared: Date.now()
      }
    });
  }

  /**
   * Get initial application state
   */
  private getInitialState(): AppState {
    return {
      ui: {
        theme: 'light',
        sidebarOpen: true,
        activeView: 'dashboard',
        loading: false,
        accessibility: {
          reducedMotion: false,
          highContrast: false,
          fontSize: 'normal',
          keyboardNavigation: true
        },
        responsive: {
          breakpoint: 'desktop',
          orientation: 'landscape'
        }
      },
      backend: {
        connectionStatus: 'disconnected',
        moduleStatus: {},
        pendingRequests: 0,
        lastSyncTime: 0
      },
      documents: {
        documents: {},
        documentHealth: {
          overall: 0,
          byType: {},
          trending: 'stable'
        },
        trackingMatrix: {
          nodes: [],
          edges: [],
          lastUpdated: 0
        }
      },
      settings: {
        privacy: {
          mode: 'local_only',
          telemetryEnabled: false,
          cloudFeaturesEnabled: false
        },
        performance: {
          memoryMode: 'standard',
          cacheEnabled: true,
          batchSize: 10
        },
        quality: {
          qualityGate: 85,
          autoEnhancement: false,
          qualityTarget: 90
        },
        integration: {
          vscodeEnabled: true,
          gitIntegration: true,
          autoSave: true
        }
      },
      notifications: {
        notifications: [],
        errors: [],
        lastCleared: Date.now()
      }
    };
  }

  /**
   * Load persisted state (only non-sensitive data)
   */
  private loadPersistedState(): void {
    try {
      const persistedData = localStorage.getItem('devdocai-ui-state');
      if (persistedData) {
        const parsed = JSON.parse(persistedData);
        
        // Only load UI preferences, not sensitive data
        if (parsed.ui) {
          this.updateUI(parsed.ui);
        }
        
        if (parsed.settings?.performance) {
          const currentState = this.getState();
          this.setState({
            settings: {
              ...currentState.settings,
              performance: parsed.settings.performance
            }
          });
        }
      }
    } catch (error) {
      console.warn('Failed to load persisted state:', error);
    }
  }

  /**
   * Setup automatic saving of non-sensitive state
   */
  private setupAutoSave(): void {
    this.subscribe((state) => {
      try {
        // Only save UI preferences and performance settings
        const dataToSave = {
          ui: state.ui,
          settings: {
            performance: state.settings.performance
          }
        };
        
        localStorage.setItem('devdocai-ui-state', JSON.stringify(dataToSave));
      } catch (error) {
        console.warn('Failed to save state:', error);
      }
    });
  }
}

/**
 * Hook-like function for getting state manager
 */
export function useGlobalState(): GlobalStateManager {
  return GlobalStateManager.getInstance();
}