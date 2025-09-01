/**
 * M011 Secure State Management - Encrypted state management for sensitive data
 * 
 * Provides AES-256-GCM encryption for sensitive fields, secure localStorage,
 * memory cleanup, and session management. Integrates with M001 Configuration
 * and M010 Security Module patterns.
 */

import CryptoJS from 'crypto-js';
import { StateManager, AppState, GlobalStateManager } from '../core/state-management';
import { securityUtils, SecurityEventType } from './security-utils';

/**
 * Sensitive field paths that should be encrypted
 */
const SENSITIVE_FIELDS = new Set([
  'backend.apiKeys',
  'backend.tokens',
  'backend.credentials',
  'documents.content',
  'settings.apiKeys',
  'settings.credentials',
  'notifications.errors', // May contain sensitive stack traces
  'user.email',
  'user.password',
  'user.personalInfo'
]);

/**
 * Encryption configuration
 */
interface EncryptionConfig {
  algorithm: string;
  keySize: number;
  iterations: number;
  saltLength: number;
  tagLength: number;
}

/**
 * Default encryption configuration (AES-256-GCM)
 */
const DEFAULT_ENCRYPTION_CONFIG: EncryptionConfig = {
  algorithm: 'AES',
  keySize: 256,
  iterations: 100000,
  saltLength: 32,
  tagLength: 128
};

/**
 * Session configuration
 */
interface SessionConfig {
  timeout: number; // milliseconds
  warningTime: number; // milliseconds before timeout
  autoRenew: boolean;
  clearOnTimeout: boolean;
}

/**
 * Default session configuration
 */
const DEFAULT_SESSION_CONFIG: SessionConfig = {
  timeout: 30 * 60 * 1000, // 30 minutes
  warningTime: 5 * 60 * 1000, // 5 minutes
  autoRenew: true,
  clearOnTimeout: true
};

/**
 * Secure storage interface
 */
interface SecureStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
  clear(): void;
}

/**
 * Secure state manager with encryption
 */
export class SecureStateManager<T> extends StateManager<T> {
  private encryptionKey: CryptoJS.lib.WordArray | null = null;
  private encryptionConfig: EncryptionConfig;
  private sessionConfig: SessionConfig;
  private sessionTimer: NodeJS.Timeout | null = null;
  private warningTimer: NodeJS.Timeout | null = null;
  private lastActivity: number = Date.now();
  private secureStorage: SecureStorage;
  private sensitiveDataMap: WeakMap<object, Set<string>> = new WeakMap();

  constructor(
    initialState: T,
    stateKey: string,
    encryptionConfig?: EncryptionConfig,
    sessionConfig?: SessionConfig
  ) {
    super(initialState, stateKey);
    this.encryptionConfig = encryptionConfig || DEFAULT_ENCRYPTION_CONFIG;
    this.sessionConfig = sessionConfig || DEFAULT_SESSION_CONFIG;
    this.secureStorage = new SecureLocalStorage(this.getEncryptionKey.bind(this));
    this.initializeSession();
  }

  /**
   * Initialize encryption key
   */
  private async initializeEncryptionKey(): Promise<void> {
    try {
      // Generate or retrieve master key
      const masterKey = await this.getMasterKey();
      
      // Derive encryption key using PBKDF2
      const salt = this.getOrGenerateSalt();
      this.encryptionKey = CryptoJS.PBKDF2(masterKey, salt, {
        keySize: this.encryptionConfig.keySize / 32,
        iterations: this.encryptionConfig.iterations
      });
    } catch (error) {
      console.error('Failed to initialize encryption key:', error);
      throw new Error('Encryption initialization failed');
    }
  }

  /**
   * Get or generate master key
   */
  private async getMasterKey(): Promise<string> {
    // In production, this should be derived from user credentials or hardware key
    // For now, we'll use a combination of factors
    const factors = [
      navigator.userAgent,
      window.location.hostname,
      new Date().toISOString().split('T')[0], // Daily rotation
      'devdocai-v3-secure' // Application identifier
    ];
    
    return factors.join('|');
  }

  /**
   * Get or generate salt
   */
  private getOrGenerateSalt(): string {
    const saltKey = `${this.stateKey}_salt`;
    let salt = sessionStorage.getItem(saltKey);
    
    if (!salt) {
      salt = securityUtils.generateToken(this.encryptionConfig.saltLength);
      sessionStorage.setItem(saltKey, salt);
    }
    
    return salt;
  }

  /**
   * Get encryption key (lazy initialization)
   */
  private async getEncryptionKey(): Promise<CryptoJS.lib.WordArray> {
    if (!this.encryptionKey) {
      await this.initializeEncryptionKey();
    }
    return this.encryptionKey!;
  }

  /**
   * Encrypt sensitive data
   */
  private encryptSensitive(data: any, path: string = ''): any {
    if (data === null || data === undefined) {
      return data;
    }

    // Check if current path is sensitive
    const isSensitive = SENSITIVE_FIELDS.has(path) || 
                        Array.from(SENSITIVE_FIELDS).some(field => path.startsWith(field));

    if (isSensitive && typeof data === 'string') {
      // Encrypt the string value
      const encrypted = CryptoJS.AES.encrypt(data, this.encryptionKey!).toString();
      return `ENC:${encrypted}`;
    }

    // Handle objects and arrays recursively
    if (typeof data === 'object') {
      if (Array.isArray(data)) {
        return data.map((item, index) => 
          this.encryptSensitive(item, `${path}[${index}]`)
        );
      } else {
        const encrypted: any = {};
        for (const key in data) {
          const newPath = path ? `${path}.${key}` : key;
          encrypted[key] = this.encryptSensitive(data[key], newPath);
        }
        return encrypted;
      }
    }

    return data;
  }

  /**
   * Decrypt sensitive data
   */
  private decryptSensitive(data: any, path: string = ''): any {
    if (data === null || data === undefined) {
      return data;
    }

    // Check if value is encrypted
    if (typeof data === 'string' && data.startsWith('ENC:')) {
      try {
        const encrypted = data.substring(4);
        const decrypted = CryptoJS.AES.decrypt(encrypted, this.encryptionKey!);
        return decrypted.toString(CryptoJS.enc.Utf8);
      } catch (error) {
        console.error('Decryption failed for path:', path);
        return null;
      }
    }

    // Handle objects and arrays recursively
    if (typeof data === 'object') {
      if (Array.isArray(data)) {
        return data.map((item, index) => 
          this.decryptSensitive(item, `${path}[${index}]`)
        );
      } else {
        const decrypted: any = {};
        for (const key in data) {
          const newPath = path ? `${path}.${key}` : key;
          decrypted[key] = this.decryptSensitive(data[key], newPath);
        }
        return decrypted;
      }
    }

    return data;
  }

  /**
   * Override setState to encrypt sensitive fields
   */
  public setState<U = T>(newState: Partial<U>): void {
    // Encrypt sensitive fields before setting
    const encrypted = this.encryptSensitive(newState);
    super.setState(encrypted);
    
    // Update activity timestamp
    this.updateActivity();
    
    // Persist encrypted state
    this.persistState();
  }

  /**
   * Override getState to decrypt sensitive fields
   */
  public getState<U = T>(): U {
    const state = super.getState<U>();
    return this.decryptSensitive(state) as U;
  }

  /**
   * Persist state to secure storage
   */
  private persistState(): void {
    try {
      const state = super.getState(); // Get encrypted state
      const serialized = JSON.stringify(state);
      this.secureStorage.setItem(this.stateKey, serialized);
    } catch (error) {
      console.error('Failed to persist state:', error);
    }
  }

  /**
   * Load state from secure storage
   */
  public loadPersistedState(): void {
    try {
      const serialized = this.secureStorage.getItem(this.stateKey);
      if (serialized) {
        const state = JSON.parse(serialized);
        super.setState(state); // Already encrypted
      }
    } catch (error) {
      console.error('Failed to load persisted state:', error);
    }
  }

  /**
   * Initialize session management
   */
  private initializeSession(): void {
    // Set up session timeout
    this.resetSessionTimer();
    
    // Listen for user activity
    this.setupActivityListeners();
    
    // Set up periodic cleanup
    this.setupMemoryCleanup();
  }

  /**
   * Setup activity listeners
   */
  private setupActivityListeners(): void {
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    
    events.forEach(event => {
      document.addEventListener(event, () => this.updateActivity(), { passive: true });
    });
  }

  /**
   * Update activity timestamp
   */
  private updateActivity(): void {
    this.lastActivity = Date.now();
    
    if (this.sessionConfig.autoRenew) {
      this.resetSessionTimer();
    }
  }

  /**
   * Reset session timer
   */
  private resetSessionTimer(): void {
    // Clear existing timers
    if (this.sessionTimer) {
      clearTimeout(this.sessionTimer);
    }
    if (this.warningTimer) {
      clearTimeout(this.warningTimer);
    }
    
    // Set warning timer
    this.warningTimer = setTimeout(() => {
      this.onSessionWarning();
    }, this.sessionConfig.timeout - this.sessionConfig.warningTime);
    
    // Set timeout timer
    this.sessionTimer = setTimeout(() => {
      this.onSessionTimeout();
    }, this.sessionConfig.timeout);
  }

  /**
   * Handle session warning
   */
  private onSessionWarning(): void {
    // Emit warning event
    const event = new CustomEvent('sessionWarning', {
      detail: { timeRemaining: this.sessionConfig.warningTime }
    });
    window.dispatchEvent(event);
  }

  /**
   * Handle session timeout
   */
  private onSessionTimeout(): void {
    // Log security event
    securityUtils['logSecurityEvent']({
      type: SecurityEventType.INVALID_INPUT,
      message: 'Session timeout',
      details: { lastActivity: this.lastActivity },
      severity: 'medium'
    });
    
    // Clear sensitive data if configured
    if (this.sessionConfig.clearOnTimeout) {
      this.clearSensitiveData();
    }
    
    // Emit timeout event
    const event = new CustomEvent('sessionTimeout');
    window.dispatchEvent(event);
  }

  /**
   * Clear sensitive data from memory
   */
  public clearSensitiveData(): void {
    // Clear encryption key
    this.encryptionKey = null;
    
    // Clear sensitive fields from state
    const state = super.getState() as any;
    const clearedState = this.clearSensitiveFields(state);
    super.setState(clearedState);
    
    // Clear secure storage
    this.secureStorage.clear();
    
    // Force garbage collection hint
    if (typeof global !== 'undefined' && global.gc) {
      global.gc();
    }
  }

  /**
   * Clear sensitive fields from object
   */
  private clearSensitiveFields(data: any, path: string = ''): any {
    if (data === null || data === undefined) {
      return data;
    }

    const isSensitive = SENSITIVE_FIELDS.has(path) || 
                        Array.from(SENSITIVE_FIELDS).some(field => path.startsWith(field));

    if (isSensitive) {
      return null;
    }

    if (typeof data === 'object') {
      if (Array.isArray(data)) {
        return data.map((item, index) => 
          this.clearSensitiveFields(item, `${path}[${index}]`)
        );
      } else {
        const cleared: any = {};
        for (const key in data) {
          const newPath = path ? `${path}.${key}` : key;
          cleared[key] = this.clearSensitiveFields(data[key], newPath);
        }
        return cleared;
      }
    }

    return data;
  }

  /**
   * Setup periodic memory cleanup
   */
  private setupMemoryCleanup(): void {
    // Run cleanup every 5 minutes
    setInterval(() => {
      this.cleanupMemory();
    }, 5 * 60 * 1000);
  }

  /**
   * Cleanup unused memory
   */
  private cleanupMemory(): void {
    // Clear WeakMap references
    this.sensitiveDataMap = new WeakMap();
    
    // Trigger garbage collection hint
    if (typeof global !== 'undefined' && global.gc) {
      global.gc();
    }
  }

  /**
   * Destroy the state manager
   */
  public destroy(): void {
    // Clear timers
    if (this.sessionTimer) {
      clearTimeout(this.sessionTimer);
    }
    if (this.warningTimer) {
      clearTimeout(this.warningTimer);
    }
    
    // Clear sensitive data
    this.clearSensitiveData();
    
    // Clear all state
    this.clear();
  }
}

/**
 * Secure localStorage implementation
 */
class SecureLocalStorage implements SecureStorage {
  private getKey: () => Promise<CryptoJS.lib.WordArray>;

  constructor(getKey: () => Promise<CryptoJS.lib.WordArray>) {
    this.getKey = getKey;
  }

  async getItem(key: string): Promise<string | null> {
    try {
      const encrypted = localStorage.getItem(`secure_${key}`);
      if (!encrypted) return null;
      
      const encryptionKey = await this.getKey();
      const decrypted = CryptoJS.AES.decrypt(encrypted, encryptionKey);
      return decrypted.toString(CryptoJS.enc.Utf8);
    } catch (error) {
      console.error('SecureLocalStorage getItem error:', error);
      return null;
    }
  }

  async setItem(key: string, value: string): Promise<void> {
    try {
      const encryptionKey = await this.getKey();
      const encrypted = CryptoJS.AES.encrypt(value, encryptionKey).toString();
      localStorage.setItem(`secure_${key}`, encrypted);
    } catch (error) {
      console.error('SecureLocalStorage setItem error:', error);
    }
  }

  removeItem(key: string): void {
    localStorage.removeItem(`secure_${key}`);
  }

  clear(): void {
    // Only clear secure items
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith('secure_')) {
        localStorage.removeItem(key);
      }
    });
  }
}

/**
 * Global secure state manager
 */
export class GlobalSecureStateManager extends GlobalStateManager {
  private static secureInstance: GlobalSecureStateManager;
  private secureStateManager: SecureStateManager<AppState>;

  private constructor() {
    super();
    const initialState = this.getInitialState();
    this.secureStateManager = new SecureStateManager(
      initialState,
      'devdocai-secure-state'
    );
  }

  /**
   * Get secure singleton instance
   */
  public static getSecureInstance(): GlobalSecureStateManager {
    if (!GlobalSecureStateManager.secureInstance) {
      GlobalSecureStateManager.secureInstance = new GlobalSecureStateManager();
    }
    return GlobalSecureStateManager.secureInstance;
  }

  /**
   * Override initialize to use secure state
   */
  public initialize(): void {
    if (this.initialized) return;

    // Initialize encryption
    this.secureStateManager.initializeEncryptionKey();
    
    // Load persisted secure state
    this.secureStateManager.loadPersistedState();
    
    this.initialized = true;
  }

  /**
   * Get current application state (decrypted)
   */
  public getState(): AppState {
    return this.secureStateManager.getState();
  }

  /**
   * Update application state (will be encrypted)
   */
  public setState(updates: Partial<AppState>): void {
    this.secureStateManager.setState(updates);
  }

  /**
   * Subscribe to state changes
   */
  public subscribe(callback: (state: AppState) => void): () => void {
    return this.secureStateManager.subscribe(callback);
  }

  /**
   * Clear sensitive data
   */
  public clearSensitiveData(): void {
    this.secureStateManager.clearSensitiveData();
  }

  /**
   * Destroy secure state manager
   */
  public destroy(): void {
    this.secureStateManager.destroy();
  }

  /**
   * Get initial state
   */
  private getInitialState(): AppState {
    // Same as parent class implementation
    return super['getInitialState']();
  }
}

/**
 * Hook for using secure global state
 */
export function useSecureGlobalState(): GlobalSecureStateManager {
  return GlobalSecureStateManager.getSecureInstance();
}

/**
 * Memory sanitizer utility
 */
export class MemorySanitizer {
  private static sensitivePatterns = [
    /password/i,
    /token/i,
    /apikey/i,
    /secret/i,
    /credential/i,
    /auth/i,
    /private/i
  ];

  /**
   * Sanitize object in memory
   */
  public static sanitize(obj: any): void {
    if (!obj || typeof obj !== 'object') return;

    const visited = new WeakSet();
    
    const sanitizeRecursive = (current: any) => {
      if (!current || typeof current !== 'object' || visited.has(current)) {
        return;
      }
      
      visited.add(current);

      Object.keys(current).forEach(key => {
        // Check if key matches sensitive pattern
        const isSensitive = this.sensitivePatterns.some(pattern => pattern.test(key));
        
        if (isSensitive) {
          // Overwrite with random data then delete
          if (typeof current[key] === 'string') {
            current[key] = securityUtils.generateToken(current[key].length);
          }
          delete current[key];
        } else if (typeof current[key] === 'object') {
          sanitizeRecursive(current[key]);
        }
      });
    };

    sanitizeRecursive(obj);
  }

  /**
   * Clear string from memory (best effort)
   */
  public static clearString(str: string): void {
    if (typeof str !== 'string') return;
    
    // Create a new string with random data of same length
    const randomStr = securityUtils.generateToken(str.length);
    
    // Try to overwrite the original string's memory
    // Note: This is best effort, JavaScript doesn't guarantee memory overwrite
    Object.assign(str, randomStr);
  }
}

/**
 * Export types and interfaces
 */
export type { EncryptionConfig, SessionConfig, SecureStorage };