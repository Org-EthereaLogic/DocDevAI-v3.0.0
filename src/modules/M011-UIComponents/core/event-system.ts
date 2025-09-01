/**
 * M011 Event System - Type-safe event handling for UI components
 * 
 * Provides a centralized event system that maintains privacy and
 * enables loose coupling between UI components and backend services.
 */

/**
 * Base event interface
 */
export interface BaseEvent {
  type: string;
  timestamp: number;
  source: string;
  data?: any;
}

/**
 * UI-specific event types
 */
export enum UIEventType {
  // Component lifecycle events
  COMPONENT_MOUNTED = 'component_mounted',
  COMPONENT_UNMOUNTED = 'component_unmounted',
  COMPONENT_UPDATED = 'component_updated',
  COMPONENT_ERROR = 'component_error',

  // User interaction events
  USER_ACTION = 'user_action',
  NAVIGATION = 'navigation',
  FORM_SUBMIT = 'form_submit',
  BUTTON_CLICK = 'button_click',

  // Data events
  DATA_LOADED = 'data_loaded',
  DATA_UPDATED = 'data_updated',
  DATA_ERROR = 'data_error',
  DATA_CACHE_HIT = 'data_cache_hit',

  // Quality and analysis events
  QUALITY_ANALYSIS_START = 'quality_analysis_start',
  QUALITY_ANALYSIS_COMPLETE = 'quality_analysis_complete',
  DOCUMENT_GENERATED = 'document_generated',
  DOCUMENT_UPDATED = 'document_updated',

  // UI state events
  THEME_CHANGED = 'theme_changed',
  ACCESSIBILITY_CHANGED = 'accessibility_changed',
  SIDEBAR_TOGGLED = 'sidebar_toggled',
  VIEW_CHANGED = 'view_changed',

  // Performance events
  PERFORMANCE_METRIC = 'performance_metric',
  MEMORY_WARNING = 'memory_warning',
  SLOW_OPERATION = 'slow_operation',

  // Error and notification events
  NOTIFICATION_ADDED = 'notification_added',
  NOTIFICATION_REMOVED = 'notification_removed',
  ERROR_OCCURRED = 'error_occurred',
  ERROR_RESOLVED = 'error_resolved'
}

/**
 * Specific event interfaces
 */
export interface ComponentLifecycleEvent extends BaseEvent {
  type: UIEventType.COMPONENT_MOUNTED | UIEventType.COMPONENT_UNMOUNTED | UIEventType.COMPONENT_UPDATED;
  data: {
    componentId: string;
    componentType: string;
    renderTime?: number;
    props?: any;
  };
}

export interface UserInteractionEvent extends BaseEvent {
  type: UIEventType.USER_ACTION | UIEventType.NAVIGATION | UIEventType.FORM_SUBMIT | UIEventType.BUTTON_CLICK;
  data: {
    action: string;
    target: string;
    value?: any;
    metadata?: any;
  };
}

export interface DataEvent extends BaseEvent {
  type: UIEventType.DATA_LOADED | UIEventType.DATA_UPDATED | UIEventType.DATA_ERROR;
  data: {
    dataType: string;
    operation: 'create' | 'read' | 'update' | 'delete';
    recordId?: string;
    success: boolean;
    error?: string;
    responseTime?: number;
  };
}

export interface QualityEvent extends BaseEvent {
  type: UIEventType.QUALITY_ANALYSIS_START | UIEventType.QUALITY_ANALYSIS_COMPLETE;
  data: {
    documentId: string;
    documentType: string;
    analysisType: string;
    score?: number;
    issues?: any[];
    duration?: number;
  };
}

export interface PerformanceEvent extends BaseEvent {
  type: UIEventType.PERFORMANCE_METRIC | UIEventType.MEMORY_WARNING | UIEventType.SLOW_OPERATION;
  data: {
    metric: string;
    value: number;
    threshold?: number;
    component?: string;
    operation?: string;
  };
}

export interface NotificationEvent extends BaseEvent {
  type: UIEventType.NOTIFICATION_ADDED | UIEventType.NOTIFICATION_REMOVED;
  data: {
    notificationId: string;
    notificationType: 'info' | 'success' | 'warning' | 'error';
    message: string;
    persistent?: boolean;
  };
}

/**
 * Event listener type
 */
export type EventListener<T extends BaseEvent = BaseEvent> = (event: T) => void;

/**
 * Event manager class
 */
export class EventManager {
  private listeners = new Map<string, Set<EventListener>>();
  private globalListeners = new Set<EventListener>();
  private eventHistory: BaseEvent[] = [];
  private maxHistorySize = 1000;
  private debugMode = false;

  /**
   * Enable/disable debug mode
   */
  setDebugMode(enabled: boolean): void {
    this.debugMode = enabled;
  }

  /**
   * Subscribe to specific event type
   */
  on<T extends BaseEvent>(eventType: UIEventType | string, listener: EventListener<T>): () => void {
    const typeStr = eventType.toString();
    
    if (!this.listeners.has(typeStr)) {
      this.listeners.set(typeStr, new Set());
    }

    this.listeners.get(typeStr)!.add(listener as EventListener);

    // Return unsubscribe function
    return () => {
      this.off(eventType, listener);
    };
  }

  /**
   * Subscribe to all events
   */
  onAll(listener: EventListener): () => void {
    this.globalListeners.add(listener);

    return () => {
      this.globalListeners.delete(listener);
    };
  }

  /**
   * Unsubscribe from event type
   */
  off<T extends BaseEvent>(eventType: UIEventType | string, listener: EventListener<T>): void {
    const typeStr = eventType.toString();
    const listeners = this.listeners.get(typeStr);
    
    if (listeners) {
      listeners.delete(listener as EventListener);
      if (listeners.size === 0) {
        this.listeners.delete(typeStr);
      }
    }
  }

  /**
   * Emit an event
   */
  emit<T extends BaseEvent>(event: T): void {
    // Add timestamp if not present
    if (!event.timestamp) {
      event.timestamp = Date.now();
    }

    // Add to history
    this.addToHistory(event);

    // Debug logging
    if (this.debugMode) {
      console.log(`[EventManager] Emitting event:`, event);
    }

    // Notify specific event listeners
    const listeners = this.listeners.get(event.type);
    if (listeners) {
      listeners.forEach(listener => {
        try {
          listener(event);
        } catch (error) {
          console.error(`[EventManager] Error in listener for ${event.type}:`, error);
        }
      });
    }

    // Notify global listeners
    this.globalListeners.forEach(listener => {
      try {
        listener(event);
      } catch (error) {
        console.error(`[EventManager] Error in global listener:`, error);
      }
    });
  }

  /**
   * Emit a simple event with basic data
   */
  emitSimple(type: UIEventType | string, source: string, data?: any): void {
    this.emit({
      type: type.toString(),
      source,
      timestamp: Date.now(),
      data
    });
  }

  /**
   * Get event history
   */
  getHistory(eventType?: UIEventType | string, limit?: number): BaseEvent[] {
    let events = eventType 
      ? this.eventHistory.filter(e => e.type === eventType.toString())
      : this.eventHistory;

    if (limit) {
      events = events.slice(-limit);
    }

    return [...events];
  }

  /**
   * Clear event history
   */
  clearHistory(): void {
    this.eventHistory = [];
  }

  /**
   * Get listener count for event type
   */
  getListenerCount(eventType: UIEventType | string): number {
    const listeners = this.listeners.get(eventType.toString());
    return listeners ? listeners.size : 0;
  }

  /**
   * Get total listener count
   */
  getTotalListenerCount(): number {
    let total = this.globalListeners.size;
    this.listeners.forEach(listeners => {
      total += listeners.size;
    });
    return total;
  }

  /**
   * Remove all listeners
   */
  removeAllListeners(): void {
    this.listeners.clear();
    this.globalListeners.clear();
  }

  /**
   * Add event to history
   */
  private addToHistory(event: BaseEvent): void {
    this.eventHistory.push({ ...event });
    
    // Limit history size
    if (this.eventHistory.length > this.maxHistorySize) {
      this.eventHistory = this.eventHistory.slice(-this.maxHistorySize);
    }
  }
}

/**
 * Global event manager instance
 */
export const eventManager = new EventManager();

/**
 * Convenience functions for common events
 */

/**
 * Emit component lifecycle event
 */
export function emitComponentEvent(
  type: UIEventType.COMPONENT_MOUNTED | UIEventType.COMPONENT_UNMOUNTED | UIEventType.COMPONENT_UPDATED,
  componentId: string,
  componentType: string,
  additionalData?: any
): void {
  eventManager.emit<ComponentLifecycleEvent>({
    type,
    source: `component:${componentId}`,
    timestamp: Date.now(),
    data: {
      componentId,
      componentType,
      ...additionalData
    }
  });
}

/**
 * Emit user interaction event
 */
export function emitUserInteraction(
  action: string,
  target: string,
  value?: any,
  metadata?: any
): void {
  eventManager.emit<UserInteractionEvent>({
    type: UIEventType.USER_ACTION,
    source: `user:${target}`,
    timestamp: Date.now(),
    data: {
      action,
      target,
      value,
      metadata
    }
  });
}

/**
 * Emit data event
 */
export function emitDataEvent(
  type: UIEventType.DATA_LOADED | UIEventType.DATA_UPDATED | UIEventType.DATA_ERROR,
  dataType: string,
  operation: 'create' | 'read' | 'update' | 'delete',
  success: boolean,
  additionalData?: any
): void {
  eventManager.emit<DataEvent>({
    type,
    source: `data:${dataType}`,
    timestamp: Date.now(),
    data: {
      dataType,
      operation,
      success,
      ...additionalData
    }
  });
}

/**
 * Emit quality analysis event
 */
export function emitQualityEvent(
  type: UIEventType.QUALITY_ANALYSIS_START | UIEventType.QUALITY_ANALYSIS_COMPLETE,
  documentId: string,
  documentType: string,
  analysisType: string,
  additionalData?: any
): void {
  eventManager.emit<QualityEvent>({
    type,
    source: `quality:${documentId}`,
    timestamp: Date.now(),
    data: {
      documentId,
      documentType,
      analysisType,
      ...additionalData
    }
  });
}

/**
 * Emit performance event
 */
export function emitPerformanceEvent(
  metric: string,
  value: number,
  component?: string,
  threshold?: number
): void {
  const eventType = threshold && value > threshold 
    ? UIEventType.SLOW_OPERATION 
    : UIEventType.PERFORMANCE_METRIC;

  eventManager.emit<PerformanceEvent>({
    type: eventType,
    source: component ? `performance:${component}` : 'performance:global',
    timestamp: Date.now(),
    data: {
      metric,
      value,
      threshold,
      component
    }
  });
}

/**
 * Hook-like function for event subscription in React components
 */
export function useEventListener<T extends BaseEvent>(
  eventType: UIEventType | string,
  listener: EventListener<T>,
  deps?: any[]
): void {
  // In a real React implementation, this would use useEffect
  // For now, it's a placeholder that components can call in useEffect
  const unsubscribe = eventManager.on(eventType, listener);
  
  // Return cleanup function (would be in useEffect cleanup)
  // return unsubscribe;
}

/**
 * Performance monitoring for event system
 */
export class EventPerformanceMonitor {
  private eventCounts = new Map<string, number>();
  private processingTimes = new Map<string, number[]>();
  private startTime: number = Date.now();

  constructor() {
    // Monitor event processing
    eventManager.onAll((event) => {
      this.recordEvent(event);
    });
  }

  /**
   * Record event for performance monitoring
   */
  private recordEvent(event: BaseEvent): void {
    const eventType = event.type;
    
    // Update event count
    this.eventCounts.set(eventType, (this.eventCounts.get(eventType) || 0) + 1);
    
    // Record processing time
    const processingTime = Date.now() - event.timestamp;
    if (!this.processingTimes.has(eventType)) {
      this.processingTimes.set(eventType, []);
    }
    this.processingTimes.get(eventType)!.push(processingTime);
    
    // Keep only last 100 processing times per event type
    const times = this.processingTimes.get(eventType)!;
    if (times.length > 100) {
      times.splice(0, times.length - 100);
    }
  }

  /**
   * Get performance statistics
   */
  getStats(): any {
    const stats: any = {
      totalEvents: Array.from(this.eventCounts.values()).reduce((sum, count) => sum + count, 0),
      eventTypes: this.eventCounts.size,
      uptime: Date.now() - this.startTime,
      eventCounts: Object.fromEntries(this.eventCounts),
      averageProcessingTimes: {}
    };

    // Calculate average processing times
    this.processingTimes.forEach((times, eventType) => {
      const average = times.reduce((sum, time) => sum + time, 0) / times.length;
      stats.averageProcessingTimes[eventType] = Math.round(average * 100) / 100;
    });

    return stats;
  }

  /**
   * Reset statistics
   */
  reset(): void {
    this.eventCounts.clear();
    this.processingTimes.clear();
    this.startTime = Date.now();
  }
}

/**
 * Global performance monitor instance
 */
export const eventPerformanceMonitor = new EventPerformanceMonitor();