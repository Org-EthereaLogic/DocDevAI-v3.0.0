/**
 * Custom hook for state that persists to localStorage
 * Automatically saves and restores state across browser sessions
 */

import { useState, useEffect, useCallback } from 'react';

export function usePersistedState<T>(
  key: string,
  initialValue: T,
  options: {
    serialize?: (value: T) => string;
    deserialize?: (value: string) => T;
    onError?: (error: Error, key: string) => void;
  } = {}
): [T, (value: T | ((prev: T) => T)) => void, () => void] {
  const {
    serialize = JSON.stringify,
    deserialize = JSON.parse,
    onError = (error) => console.warn('usePersistedState error:', error)
  } = options;

  // Initialize state from localStorage or use initial value
  const [state, setState] = useState<T>(() => {
    try {
      if (typeof window === 'undefined') return initialValue;
      
      const item = window.localStorage.getItem(key);
      if (item === null) return initialValue;
      
      return deserialize(item);
    } catch (error) {
      onError(error as Error, key);
      return initialValue;
    }
  });

  // Update localStorage when state changes
  useEffect(() => {
    try {
      if (typeof window === 'undefined') return;
      
      window.localStorage.setItem(key, serialize(state));
    } catch (error) {
      onError(error as Error, key);
    }
  }, [key, state, serialize, onError]);

  // Clear persisted data
  const clearPersistedData = useCallback(() => {
    try {
      if (typeof window === 'undefined') return;
      
      window.localStorage.removeItem(key);
      setState(initialValue);
    } catch (error) {
      onError(error as Error, key);
    }
  }, [key, initialValue, onError]);

  return [state, setState, clearPersistedData];
}

/**
 * Hook for persisting form state specifically
 * Includes debouncing to prevent excessive localStorage writes
 */
export function usePersistedFormState<T extends Record<string, any>>(
  formKey: string,
  initialFormState: T,
  debounceMs: number = 500
): [T, (updates: Partial<T> | ((prev: T) => T)) => void, () => void] {
  const [formState, setFormState, clearFormState] = usePersistedState(
    `devdocai_form_${formKey}`,
    initialFormState
  );

  const [debouncedState, setDebouncedState] = useState(formState);
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null);

  // Debounced update function
  const updateFormState = useCallback((updates: Partial<T> | ((prev: T) => T)) => {
    const newState = typeof updates === 'function' ? updates(debouncedState) : { ...debouncedState, ...updates };
    setDebouncedState(newState);

    // Clear existing timeout
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    // Set new timeout to persist after debounce period
    const newTimeoutId = setTimeout(() => {
      setFormState(newState);
    }, debounceMs);

    setTimeoutId(newTimeoutId);
  }, [debouncedState, timeoutId, debounceMs, setFormState]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [timeoutId]);

  return [debouncedState, updateFormState, clearFormState];
}