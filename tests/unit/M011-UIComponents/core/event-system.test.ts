/**
 * Event System Tests
 * 
 * Tests for the core event system including:
 * - EventManager functionality
 * - Event subscription and emission
 * - Event filtering and validation
 * - Performance monitoring
 * - Error handling
 */

import { 
  EventManager, 
  UIEventType, 
  eventManager 
} from '../../../../src/modules/M011-UIComponents/core/event-system';
import type { 
  UIEvent, 
  EventSubscription, 
  EventFilter 
} from '../../../../src/modules/M011-UIComponents/core/event-system';

describe('EventManager', () => {
  let manager: EventManager;

  beforeEach(() => {
    manager = new EventManager();
  });

  describe('basic event operations', () => {
    test('should emit and receive simple events', () => {
      const listener = jest.fn();
      const unsubscribe = manager.subscribe(UIEventType.USER_ACTION, listener);

      manager.emitSimple(UIEventType.USER_ACTION, 'test-component', { action: 'click' });

      expect(listener).toHaveBeenCalledTimes(1);
      expect(listener).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'click'
        })
      );

      unsubscribe();
    });

    test('should emit and receive full events', () => {
      const listener = jest.fn();
      const unsubscribe = manager.subscribe(UIEventType.COMPONENT_LOADED, listener);

      const event: UIEvent = {
        id: 'test-event',
        type: UIEventType.COMPONENT_LOADED,
        source: 'test-component',
        timestamp: new Date(),
        data: { componentId: 'test-123' },
        metadata: {
          version: '1.0.0',
          user: 'test-user'
        }
      };

      manager.emit(event);

      expect(listener).toHaveBeenCalledTimes(1);
      expect(listener).toHaveBeenCalledWith(event.data);

      unsubscribe();
    });

    test('should handle multiple subscribers for same event type', () => {
      const listener1 = jest.fn();
      const listener2 = jest.fn();
      const listener3 = jest.fn();

      const unsubscribe1 = manager.subscribe(UIEventType.USER_ACTION, listener1);
      const unsubscribe2 = manager.subscribe(UIEventType.USER_ACTION, listener2);
      const unsubscribe3 = manager.subscribe(UIEventType.USER_ACTION, listener3);

      manager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'click' });

      expect(listener1).toHaveBeenCalledTimes(1);
      expect(listener2).toHaveBeenCalledTimes(1);
      expect(listener3).toHaveBeenCalledTimes(1);

      unsubscribe1();
      unsubscribe2();
      unsubscribe3();
    });

    test('should not call unsubscribed listeners', () => {
      const listener = jest.fn();
      const unsubscribe = manager.subscribe(UIEventType.USER_ACTION, listener);

      // Emit before unsubscribe
      manager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'click' });
      expect(listener).toHaveBeenCalledTimes(1);

      // Unsubscribe and emit again
      unsubscribe();
      manager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'click' });
      expect(listener).toHaveBeenCalledTimes(1); // Still 1, not 2
    });
  });

  describe('event filtering', () => {
    test('should filter events by source', () => {
      const listener = jest.fn();
      const filter: EventFilter = {
        source: 'dashboard'
      };

      const unsubscribe = manager.subscribe(UIEventType.USER_ACTION, listener, filter);

      // Should receive this event
      manager.emitSimple(UIEventType.USER_ACTION, 'dashboard', { action: 'click' });
      
      // Should not receive this event
      manager.emitSimple(UIEventType.USER_ACTION, 'sidebar', { action: 'click' });

      expect(listener).toHaveBeenCalledTimes(1);

      unsubscribe();
    });

    test('should filter events by data properties', () => {
      const listener = jest.fn();
      const filter: EventFilter = {
        data: { severity: 'high' }
      };

      const unsubscribe = manager.subscribe(UIEventType.ERROR_OCCURRED, listener, filter);

      // Should receive this event
      manager.emitSimple(UIEventType.ERROR_OCCURRED, 'test', { 
        message: 'Error 1',
        severity: 'high' 
      });
      
      // Should not receive this event
      manager.emitSimple(UIEventType.ERROR_OCCURRED, 'test', { 
        message: 'Error 2',
        severity: 'low' 
      });

      expect(listener).toHaveBeenCalledTimes(1);

      unsubscribe();
    });

    test('should filter events with custom filter function', () => {
      const listener = jest.fn();
      const filter: EventFilter = {
        custom: (event) => event.data.priority > 5
      };

      const unsubscribe = manager.subscribe(UIEventType.NOTIFICATION_SENT, listener, filter);

      // Should receive this event
      manager.emitSimple(UIEventType.NOTIFICATION_SENT, 'test', { priority: 8 });
      
      // Should not receive this event
      manager.emitSimple(UIEventType.NOTIFICATION_SENT, 'test', { priority: 3 });

      expect(listener).toHaveBeenCalledTimes(1);

      unsubscribe();
    });
  });

  describe('event validation', () => {
    test('should validate event data', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();

      // Test invalid event type
      manager.emitSimple('invalid-type' as UIEventType, 'test', {});

      expect(consoleSpy).toHaveBeenCalledWith(
        'Invalid event type:', 'invalid-type'
      );

      consoleSpy.mockRestore();
    });

    test('should handle missing event data gracefully', () => {
      const listener = jest.fn();
      const unsubscribe = manager.subscribe(UIEventType.USER_ACTION, listener);

      // Emit event with null data
      manager.emitSimple(UIEventType.USER_ACTION, 'test', null);

      expect(listener).toHaveBeenCalledWith(null);

      unsubscribe();
    });
  });

  describe('performance monitoring', () => {
    test('should track event statistics', () => {
      manager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'click' });
      manager.emitSimple(UIEventType.COMPONENT_LOADED, 'test', { id: '1' });
      manager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'scroll' });

      const stats = manager.getStats();

      expect(stats.totalEmitted).toBe(3);
      expect(stats.byType[UIEventType.USER_ACTION]).toBe(2);
      expect(stats.byType[UIEventType.COMPONENT_LOADED]).toBe(1);
    });

    test('should track subscriber count', () => {
      const listener1 = jest.fn();
      const listener2 = jest.fn();

      const unsubscribe1 = manager.subscribe(UIEventType.USER_ACTION, listener1);
      const unsubscribe2 = manager.subscribe(UIEventType.COMPONENT_LOADED, listener2);

      const stats = manager.getStats();
      expect(stats.totalSubscribers).toBe(2);

      unsubscribe1();
      
      const statsAfterUnsubscribe = manager.getStats();
      expect(statsAfterUnsubscribe.totalSubscribers).toBe(1);

      unsubscribe2();
    });

    test('should reset statistics', () => {
      manager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'click' });
      manager.emitSimple(UIEventType.COMPONENT_LOADED, 'test', { id: '1' });

      let stats = manager.getStats();
      expect(stats.totalEmitted).toBe(2);

      manager.resetStats();
      
      stats = manager.getStats();
      expect(stats.totalEmitted).toBe(0);
      expect(stats.byType).toEqual({});
    });
  });

  describe('error handling', () => {
    test('should handle listener errors gracefully', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      const goodListener = jest.fn();
      const badListener = jest.fn(() => {
        throw new Error('Listener error');
      });

      const unsubscribe1 = manager.subscribe(UIEventType.USER_ACTION, goodListener);
      const unsubscribe2 = manager.subscribe(UIEventType.USER_ACTION, badListener);

      manager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'click' });

      // Good listener should still be called
      expect(goodListener).toHaveBeenCalledTimes(1);
      // Error should be logged
      expect(consoleSpy).toHaveBeenCalledWith(
        'Error in event listener:',
        expect.any(Error)
      );

      unsubscribe1();
      unsubscribe2();
      consoleSpy.mockRestore();
    });

    test('should emit error events for listener errors', () => {
      const errorListener = jest.fn();
      const badListener = jest.fn(() => {
        throw new Error('Listener error');
      });

      const unsubscribeError = manager.subscribe(UIEventType.ERROR_OCCURRED, errorListener);
      const unsubscribeBad = manager.subscribe(UIEventType.USER_ACTION, badListener);

      manager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'click' });

      // Error event should be emitted
      expect(errorListener).toHaveBeenCalledWith(
        expect.objectContaining({
          message: expect.stringContaining('Event listener error'),
          error: expect.any(Error)
        })
      );

      unsubscribeError();
      unsubscribeBad();
    });
  });

  describe('cleanup and memory management', () => {
    test('should clean up all subscriptions', () => {
      const listener1 = jest.fn();
      const listener2 = jest.fn();

      manager.subscribe(UIEventType.USER_ACTION, listener1);
      manager.subscribe(UIEventType.COMPONENT_LOADED, listener2);

      let stats = manager.getStats();
      expect(stats.totalSubscribers).toBe(2);

      manager.cleanup();

      stats = manager.getStats();
      expect(stats.totalSubscribers).toBe(0);

      // Events should no longer be delivered
      manager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'click' });
      expect(listener1).not.toHaveBeenCalled();
    });
  });
});

describe('Global event manager', () => {
  test('should provide singleton event manager', () => {
    expect(eventManager).toBeInstanceOf(EventManager);
  });

  test('should maintain state across imports', () => {
    const listener = jest.fn();
    const unsubscribe = eventManager.subscribe(UIEventType.USER_ACTION, listener);

    eventManager.emitSimple(UIEventType.USER_ACTION, 'test', { action: 'click' });

    expect(listener).toHaveBeenCalledTimes(1);

    unsubscribe();
  });
});

describe('UIEventType enum', () => {
  test('should contain all expected event types', () => {
    const expectedTypes = [
      'USER_ACTION',
      'COMPONENT_LOADED',
      'COMPONENT_UPDATED', 
      'COMPONENT_DESTROYED',
      'NOTIFICATION_SENT',
      'NOTIFICATION_DISMISSED',
      'ERROR_OCCURRED',
      'WARNING_ISSUED',
      'DATA_LOADED',
      'DATA_SAVED',
      'SETTINGS_CHANGED',
      'THEME_CHANGED',
      'LAYOUT_CHANGED',
      'PANEL_OPENED',
      'PANEL_CLOSED',
      'PANEL_REFRESH',
      'DOCUMENT_GENERATED',
      'QUALITY_ANALYZED',
      'TEMPLATE_SELECTED',
      'SETTINGS_OPEN',
      'WEBVIEW_MESSAGE',
      'BACKGROUND_TASK',
      'STATUS_UPDATE',
      'QUICK_ACTION'
    ];

    expectedTypes.forEach(type => {
      expect(UIEventType[type as keyof typeof UIEventType]).toBeDefined();
    });
  });
});