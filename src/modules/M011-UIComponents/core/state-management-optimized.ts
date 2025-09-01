/**
 * Optimized State Management with Performance Enhancements
 * 
 * Features:
 * - Selective subscriptions to reduce re-renders
 * - State normalization for complex data
 * - Debouncing/throttling for frequent updates
 * - LocalStorage performance optimization
 * - Immutable updates with structural sharing
 */

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';

/**
 * State slice selectors for selective subscriptions
 */
export type StateSelector<T, R> = (state: T) => R;

/**
 * Subscription options
 */
export interface SubscriptionOptions {
  debounce?: number;
  throttle?: number;
  immediate?: boolean;
  equalityFn?: (a: any, b: any) => boolean;
}

/**
 * Default equality function using shallow comparison
 */
const defaultEqualityFn = (a: any, b: any): boolean => {
  if (a === b) return true;
  if (typeof a !== 'object' || typeof b !== 'object') return false;
  
  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  
  if (keysA.length !== keysB.length) return false;
  
  return keysA.every(key => a[key] === b[key]);
};

/**
 * Optimized state store with performance features
 */
export class OptimizedStateStore<T extends object> {
  private state: T;
  private listeners = new Map<symbol, {
    selector?: StateSelector<T, any>;
    callback: (state: any) => void;
    options?: SubscriptionOptions;
    lastValue?: any;
    timeoutId?: NodeJS.Timeout;
    lastCall?: number;
  }>();
  private persistKey?: string;
  private persistDebounceId?: NodeJS.Timeout;
  private stateCache = new WeakMap<object, any>();

  constructor(initialState: T, persistKey?: string) {
    this.state = initialState;
    this.persistKey = persistKey;
    
    if (persistKey) {
      this.loadFromStorage();
    }
  }

  /**
   * Get current state or selected slice
   */
  getState(): T;
  getState<R>(selector: StateSelector<T, R>): R;
  getState<R>(selector?: StateSelector<T, R>): T | R {
    if (selector) {
      // Check cache first
      if (this.stateCache.has(this.state)) {
        const cache = this.stateCache.get(this.state);
        if (cache?.selector === selector) {
          return cache.value;
        }
      }
      
      // Calculate and cache result
      const value = selector(this.state);
      this.stateCache.set(this.state, { selector, value });
      return value;
    }
    return this.state;
  }

  /**
   * Update state with automatic batching
   */
  setState(updater: Partial<T> | ((state: T) => Partial<T>)): void {
    const updates = typeof updater === 'function' ? updater(this.state) : updater;
    
    // Check if update is needed
    const hasChanges = Object.keys(updates).some(
      key => this.state[key as keyof T] !== updates[key as keyof T]
    );
    
    if (!hasChanges) return;
    
    // Create new state with structural sharing
    this.state = { ...this.state, ...updates };
    
    // Clear cache
    this.stateCache = new WeakMap();
    
    // Notify listeners
    this.notifyListeners();
    
    // Persist to storage (debounced)
    if (this.persistKey) {
      this.persistToStorage();
    }
  }

  /**
   * Subscribe to state changes with optional selector
   */
  subscribe<R = T>(
    callback: (state: R) => void,
    selector?: StateSelector<T, R>,
    options?: SubscriptionOptions
  ): () => void {
    const id = Symbol();
    
    const initialValue = selector ? selector(this.state) : this.state;
    
    this.listeners.set(id, {
      selector,
      callback,
      options,
      lastValue: initialValue
    });
    
    // Call immediately if requested
    if (options?.immediate) {
      callback(initialValue);
    }
    
    // Return unsubscribe function
    return () => {
      const listener = this.listeners.get(id);
      if (listener?.timeoutId) {
        clearTimeout(listener.timeoutId);
      }
      this.listeners.delete(id);
    };
  }

  /**
   * Notify listeners with optimizations
   */
  private notifyListeners(): void {
    this.listeners.forEach((listener, id) => {
      const { selector, callback, options, lastValue } = listener;
      
      // Get current value
      const currentValue = selector ? selector(this.state) : this.state;
      
      // Check if value changed
      const equalityFn = options?.equalityFn || defaultEqualityFn;
      if (equalityFn(lastValue, currentValue)) {
        return; // No change, skip notification
      }
      
      // Update last value
      listener.lastValue = currentValue;
      
      // Handle debounce
      if (options?.debounce) {
        if (listener.timeoutId) {
          clearTimeout(listener.timeoutId);
        }
        listener.timeoutId = setTimeout(() => {
          callback(currentValue);
          listener.timeoutId = undefined;
        }, options.debounce);
        return;
      }
      
      // Handle throttle
      if (options?.throttle) {
        const now = Date.now();
        const lastCall = listener.lastCall || 0;
        
        if (now - lastCall < options.throttle) {
          return; // Skip due to throttle
        }
        
        listener.lastCall = now;
      }
      
      // Call callback
      callback(currentValue);
    });
  }

  /**
   * Load state from localStorage (optimized)
   */
  private loadFromStorage(): void {
    if (!this.persistKey) return;
    
    try {
      const stored = localStorage.getItem(this.persistKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        this.state = { ...this.state, ...parsed };
      }
    } catch (error) {
      console.error('Failed to load state from storage:', error);
    }
  }

  /**
   * Persist state to localStorage (debounced)
   */
  private persistToStorage(): void {
    if (!this.persistKey) return;
    
    if (this.persistDebounceId) {
      clearTimeout(this.persistDebounceId);
    }
    
    this.persistDebounceId = setTimeout(() => {
      try {
        localStorage.setItem(this.persistKey, JSON.stringify(this.state));
      } catch (error) {
        console.error('Failed to persist state to storage:', error);
      }
    }, 500);
  }

  /**
   * Reset state to initial value
   */
  reset(initialState: T): void {
    this.state = initialState;
    this.stateCache = new WeakMap();
    
    if (this.persistKey) {
      localStorage.removeItem(this.persistKey);
    }
    
    this.notifyListeners();
  }

  /**
   * Get state statistics
   */
  getStats(): {
    listenerCount: number;
    stateSize: number;
    persistKey?: string;
  } {
    return {
      listenerCount: this.listeners.size,
      stateSize: JSON.stringify(this.state).length,
      persistKey: this.persistKey
    };
  }
}

/**
 * React hook for optimized state management
 */
export function useOptimizedState<T extends object, R = T>(
  store: OptimizedStateStore<T>,
  selector?: StateSelector<T, R>,
  options?: SubscriptionOptions
): R {
  const [state, setState] = useState<R>(() => 
    selector ? store.getState(selector) : store.getState() as any
  );
  
  const selectorRef = useRef(selector);
  const optionsRef = useRef(options);
  
  useEffect(() => {
    selectorRef.current = selector;
    optionsRef.current = options;
  });
  
  useEffect(() => {
    const unsubscribe = store.subscribe(
      setState,
      selectorRef.current,
      optionsRef.current
    );
    
    return unsubscribe;
  }, [store]);
  
  return state;
}

/**
 * Create an optimized store with TypeScript support
 */
export function createOptimizedStore<T extends object>(
  initialState: T,
  persistKey?: string
): OptimizedStateStore<T> {
  return new OptimizedStateStore(initialState, persistKey);
}

/**
 * Batch multiple state updates
 */
export function batchUpdates<T extends object>(
  store: OptimizedStateStore<T>,
  updates: Array<Partial<T> | ((state: T) => Partial<T>)>
): void {
  const batchedUpdate = updates.reduce((acc, update) => {
    const partial = typeof update === 'function' 
      ? update(store.getState())
      : update;
    return { ...acc, ...partial };
  }, {} as Partial<T>);
  
  store.setState(batchedUpdate);
}

/**
 * Create selector with memoization
 */
export function createSelector<T, R, S>(
  selector1: StateSelector<T, R>,
  selector2: StateSelector<R, S>
): StateSelector<T, S> {
  let lastInput: R | undefined;
  let lastOutput: S | undefined;
  
  return (state: T) => {
    const input = selector1(state);
    
    if (input === lastInput && lastOutput !== undefined) {
      return lastOutput;
    }
    
    lastInput = input;
    lastOutput = selector2(input);
    return lastOutput;
  };
}

/**
 * Create multiple selectors with memoization
 */
export function createSelectors<T extends object, S extends Record<string, StateSelector<T, any>>>(
  selectors: S
): S {
  const memoized: any = {};
  
  Object.keys(selectors).forEach(key => {
    let lastState: T | undefined;
    let lastResult: any;
    
    memoized[key] = (state: T) => {
      if (state === lastState && lastResult !== undefined) {
        return lastResult;
      }
      
      lastState = state;
      lastResult = selectors[key](state);
      return lastResult;
    };
  });
  
  return memoized as S;
}