/**
 * State Management Tests
 * 
 * Tests for the core state management system including:
 * - StateManager functionality
 * - Global state operations
 * - State persistence
 * - Subscription mechanisms
 * - Notification management
 */

import { StateManager, useGlobalState } from '../../../../src/modules/M011-UIComponents/core/state-management';
import type { 
  UIState, 
  ComponentState, 
  ComponentData,
  ToastNotification 
} from '../../../../src/modules/M011-UIComponents/core/interfaces';
import { renderHook, act } from '@testing-library/react';

describe('StateManager', () => {
  let stateManager: StateManager;

  beforeEach(() => {
    stateManager = new StateManager();
  });

  afterEach(() => {
    // Clear localStorage after each test
    localStorage.clear();
  });

  describe('initialization', () => {
    test('should initialize with default state', () => {
      const state = stateManager.getState();
      
      expect(state).toEqual({
        ui: expect.objectContaining({
          theme: 'light',
          layout: 'dashboard',
          sidebarOpen: true,
          loading: false,
          error: null,
          notifications: [],
          accessibility: expect.objectContaining({
            highContrast: false,
            reduceMotion: false,
            keyboardNavigation: true,
            enhancedSupport: false
          })
        }),
        components: {},
        backend: {
          connection: 'connected',
          lastSync: expect.any(Date),
          errors: []
        }
      });
    });

    test('should load persisted state from localStorage', () => {
      const persistedState: Partial<UIState> = {
        ui: {
          theme: 'dark',
          layout: 'minimal',
          sidebarOpen: false,
          loading: false,
          error: null,
          notifications: [],
          accessibility: {
            highContrast: true,
            reduceMotion: true,
            keyboardNavigation: true,
            enhancedSupport: true
          }
        },
        components: {},
        backend: {
          connection: 'connected',
          lastSync: new Date(),
          errors: []
        }
      };

      localStorage.setItem('devdocai-ui-state', JSON.stringify(persistedState));
      
      const newStateManager = new StateManager();
      const state = newStateManager.getState();
      
      expect(state.ui.theme).toBe('dark');
      expect(state.ui.layout).toBe('minimal');
      expect(state.ui.sidebarOpen).toBe(false);
      expect(state.ui.accessibility.highContrast).toBe(true);
    });

    test('should handle invalid persisted state gracefully', () => {
      localStorage.setItem('devdocai-ui-state', 'invalid-json');
      
      const newStateManager = new StateManager();
      const state = newStateManager.getState();
      
      // Should fall back to default state
      expect(state.ui.theme).toBe('light');
      expect(state.ui.sidebarOpen).toBe(true);
    });
  });

  describe('state updates', () => {
    test('should update UI state', () => {
      stateManager.updateUIState({
        theme: 'dark',
        sidebarOpen: false
      });

      const state = stateManager.getState();
      expect(state.ui.theme).toBe('dark');
      expect(state.ui.sidebarOpen).toBe(false);
    });

    test('should update component state', () => {
      const componentId = 'test-component';
      const componentData: ComponentData = {
        data: { value: 'test' },
        loading: false,
        error: null,
        lastUpdated: new Date()
      };

      stateManager.updateComponentState(componentId, componentData);

      const state = stateManager.getState();
      expect(state.components[componentId]).toEqual(componentData);
    });

    test('should persist state to localStorage', () => {
      stateManager.updateUIState({ theme: 'dark' });
      
      const persistedState = JSON.parse(
        localStorage.getItem('devdocai-ui-state') || '{}'
      );
      
      expect(persistedState.ui.theme).toBe('dark');
    });

    test('should notify subscribers of state changes', () => {
      const subscriber = jest.fn();
      const unsubscribe = stateManager.subscribe(subscriber);

      stateManager.updateUIState({ theme: 'dark' });

      expect(subscriber).toHaveBeenCalledWith(
        expect.objectContaining({
          ui: expect.objectContaining({
            theme: 'dark'
          })
        })
      );

      unsubscribe();
    });
  });

  describe('notifications', () => {
    test('should add notification', () => {
      const notification: ToastNotification = {
        id: 'test-notification',
        type: 'success',
        title: 'Test',
        message: 'Test message'
      };

      stateManager.addNotification(notification);

      const state = stateManager.getState();
      expect(state.ui.notifications).toContain(notification);
    });

    test('should generate ID for notification without one', () => {
      const notification = {
        type: 'info' as const,
        title: 'Test',
        message: 'Test message'
      };

      stateManager.addNotification(notification);

      const state = stateManager.getState();
      expect(state.ui.notifications[0].id).toBeTruthy();
      expect(typeof state.ui.notifications[0].id).toBe('string');
    });

    test('should remove notification', () => {
      const notification: ToastNotification = {
        id: 'test-notification',
        type: 'success',
        title: 'Test',
        message: 'Test message'
      };

      stateManager.addNotification(notification);
      stateManager.removeNotification('test-notification');

      const state = stateManager.getState();
      expect(state.ui.notifications).not.toContain(notification);
    });

    test('should clear all notifications', () => {
      stateManager.addNotification({
        id: 'notification-1',
        type: 'success',
        title: 'Test 1',
        message: 'Message 1'
      });

      stateManager.addNotification({
        id: 'notification-2',
        type: 'error',
        title: 'Test 2',
        message: 'Message 2'
      });

      stateManager.clearNotifications();

      const state = stateManager.getState();
      expect(state.ui.notifications).toHaveLength(0);
    });
  });

  describe('component data management', () => {
    test('should get component data', () => {
      const componentId = 'test-component';
      const componentData: ComponentData = {
        data: { value: 'test' },
        loading: false,
        error: null,
        lastUpdated: new Date()
      };

      stateManager.updateComponentState(componentId, componentData);
      const retrievedData = stateManager.getComponentData(componentId);

      expect(retrievedData).toEqual(componentData);
    });

    test('should return null for non-existent component', () => {
      const retrievedData = stateManager.getComponentData('non-existent');
      expect(retrievedData).toBeNull();
    });

    test('should clear component data', () => {
      const componentId = 'test-component';
      const componentData: ComponentData = {
        data: { value: 'test' },
        loading: false,
        error: null,
        lastUpdated: new Date()
      };

      stateManager.updateComponentState(componentId, componentData);
      stateManager.clearComponentData(componentId);

      const retrievedData = stateManager.getComponentData(componentId);
      expect(retrievedData).toBeNull();
    });
  });

  describe('reset functionality', () => {
    test('should reset to default state', () => {
      // Modify state
      stateManager.updateUIState({
        theme: 'dark',
        sidebarOpen: false,
        loading: true
      });

      stateManager.addNotification({
        id: 'test',
        type: 'success',
        title: 'Test',
        message: 'Message'
      });

      // Reset
      stateManager.reset();

      const state = stateManager.getState();
      expect(state.ui.theme).toBe('light');
      expect(state.ui.sidebarOpen).toBe(true);
      expect(state.ui.loading).toBe(false);
      expect(state.ui.notifications).toHaveLength(0);
    });
  });
});

describe('useGlobalState hook', () => {
  beforeEach(() => {
    // Reset the global state manager before each test
    jest.clearAllMocks();
  });

  test('should return global state manager', () => {
    const { result } = renderHook(() => useGlobalState());
    
    expect(result.current).toBeDefined();
    expect(typeof result.current.getState).toBe('function');
    expect(typeof result.current.updateUIState).toBe('function');
    expect(typeof result.current.subscribe).toBe('function');
  });

  test('should provide access to current state', () => {
    const { result } = renderHook(() => useGlobalState());
    
    const state = result.current.getState();
    expect(state).toHaveProperty('ui');
    expect(state).toHaveProperty('components');
    expect(state).toHaveProperty('backend');
  });

  test('should allow state updates through hook', () => {
    const { result } = renderHook(() => useGlobalState());
    
    act(() => {
      result.current.updateUIState({ theme: 'dark' });
    });

    const state = result.current.getState();
    expect(state.ui.theme).toBe('dark');
  });

  test('should handle notifications through hook', () => {
    const { result } = renderHook(() => useGlobalState());
    
    act(() => {
      result.current.addNotification({
        type: 'success',
        title: 'Test',
        message: 'Test message'
      });
    });

    const state = result.current.getState();
    expect(state.ui.notifications).toHaveLength(1);
    expect(state.ui.notifications[0].message).toBe('Test message');
  });
});