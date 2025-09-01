/**
 * DevDocAI v3.0.0 - Configuration Service
 * 
 * Service layer for M001 Configuration Manager module
 * Handles application configuration, settings persistence, and environment management.
 */

export interface AppConfiguration {
  // General Settings
  theme: 'light' | 'dark' | 'auto';
  language: string;
  autoSave: boolean;
  
  // Performance Settings
  memoryMode: 'baseline' | 'standard' | 'enhanced' | 'performance';
  cacheSize: number; // MB
  enableBatching: boolean;
  
  // Security Settings
  encryptionEnabled: boolean;
  sessionTimeout: number; // minutes
  auditLogging: boolean;
  
  // API Settings
  openaiEnabled: boolean;
  anthropicEnabled: boolean;
  rateLimit: number; // requests per minute
  
  // Storage Settings
  localPath: string;
  backupEnabled: boolean;
  retentionDays: number;
  
  // Notification Settings
  notificationsEnabled: boolean;
  emailAlerts: boolean;
}

export interface ModuleStatus {
  M001: boolean; // Configuration Manager
  M002: boolean; // Local Storage
  M003: boolean; // MIAIR Engine
  M004: boolean; // Document Generator
  M005: boolean; // Quality Engine
  M006: boolean; // Template Registry
  M007: boolean; // Review Engine
  M008: boolean; // LLM Adapter
  M009: boolean; // Enhancement Pipeline
  M010: boolean; // Security Module
  M011: boolean; // UI Components
  M012: boolean; // CLI Interface
  M013: boolean; // VS Code Extension
}

class ConfigurationServiceImpl {
  private configuration: AppConfiguration;
  private moduleStatus: ModuleStatus;
  private initialized = false;

  constructor() {
    // Default configuration
    this.configuration = {
      theme: 'light',
      language: 'en',
      autoSave: true,
      memoryMode: 'standard',
      cacheSize: 100,
      enableBatching: true,
      encryptionEnabled: true,
      sessionTimeout: 30,
      auditLogging: true,
      openaiEnabled: false,
      anthropicEnabled: false,
      rateLimit: 60,
      localPath: './devdocai-data',
      backupEnabled: true,
      retentionDays: 365,
      notificationsEnabled: true,
      emailAlerts: false,
    };

    // Default module status (based on current development status)
    this.moduleStatus = {
      M001: true,  // Configuration Manager - Complete
      M002: true,  // Local Storage - Complete
      M003: true,  // MIAIR Engine - Complete
      M004: true,  // Document Generator - Complete
      M005: true,  // Quality Engine - Complete
      M006: true,  // Template Registry - Complete
      M007: true,  // Review Engine - Complete
      M008: true,  // LLM Adapter - Complete
      M009: true,  // Enhancement Pipeline - Complete
      M010: true,  // Security Module - Complete
      M011: true,  // UI Components - Complete
      M012: false, // CLI Interface - Pending
      M013: false, // VS Code Extension - Pending
    };
  }

  async initialize(): Promise<void> {
    try {
      console.log('Initializing Configuration Service...');
      
      // Load configuration from local storage or file
      await this.loadConfiguration();
      
      // Validate and migrate configuration if needed
      await this.validateConfiguration();
      
      // Check module availability
      await this.checkModuleStatus();
      
      this.initialized = true;
      console.log('Configuration Service initialized successfully');
    } catch (error) {
      console.error('Failed to initialize Configuration Service:', error);
      // Set initialized to true anyway to allow app to continue
      this.initialized = true;
      console.log('Configuration Service using defaults due to initialization error');
    }
  }

  async loadConfiguration(): Promise<void> {
    try {
      // In a real implementation, this would load from:
      // 1. Environment variables
      // 2. Configuration file (.devdocai.yml)
      // 3. Local storage (for UI preferences)
      // 4. Database (for persistent settings)
      
      // Safely check if localStorage is available
      if (typeof localStorage !== 'undefined' && localStorage !== null) {
        try {
          const saved = localStorage.getItem('devdocai-config');
          if (saved) {
            const parsedConfig = JSON.parse(saved);
            this.configuration = { ...this.configuration, ...parsedConfig };
          }
        } catch (storageError) {
          console.warn('localStorage access failed:', storageError);
        }
      }
      
      // Load environment-specific settings
      if (process.env.NODE_ENV === 'development') {
        this.configuration.auditLogging = false;
        this.configuration.sessionTimeout = 60; // Longer timeout in dev
      }
      
      console.log('Configuration loaded successfully');
    } catch (error) {
      console.warn('Failed to load saved configuration, using defaults:', error);
    }
  }

  async saveConfiguration(): Promise<void> {
    try {
      // Safely save to local storage for UI preferences
      if (typeof localStorage !== 'undefined' && localStorage !== null) {
        try {
          localStorage.setItem('devdocai-config', JSON.stringify(this.configuration));
        } catch (storageError) {
          console.warn('localStorage save failed:', storageError);
        }
      }
      
      // In a real implementation, this would also:
      // 1. Save to configuration file
      // 2. Update environment variables
      // 3. Persist to database
      // 4. Encrypt sensitive settings
      
      console.log('Configuration saved successfully');
    } catch (error) {
      console.error('Failed to save configuration:', error);
      // Don't throw - let the app continue
    }
  }

  async validateConfiguration(): Promise<void> {
    // Validate configuration values and apply constraints
    if (this.configuration.cacheSize < 10) {
      this.configuration.cacheSize = 10;
    }
    if (this.configuration.cacheSize > 1000) {
      this.configuration.cacheSize = 1000;
    }
    
    if (this.configuration.sessionTimeout < 5) {
      this.configuration.sessionTimeout = 5;
    }
    if (this.configuration.sessionTimeout > 480) { // 8 hours max
      this.configuration.sessionTimeout = 480;
    }
    
    if (this.configuration.rateLimit < 1) {
      this.configuration.rateLimit = 1;
    }
    if (this.configuration.rateLimit > 1000) {
      this.configuration.rateLimit = 1000;
    }
    
    console.log('Configuration validated');
  }

  async checkModuleStatus(): Promise<void> {
    try {
      // In a real implementation, this would:
      // 1. Check if module files exist
      // 2. Verify module dependencies
      // 3. Test module initialization
      // 4. Check service connectivity
      
      // For now, simulate module availability checks
      const moduleChecks = Object.keys(this.moduleStatus).map(async (moduleId) => {
        try {
          // Simulate module health check
          await new Promise(resolve => setTimeout(resolve, Math.random() * 100));
          return { moduleId, status: this.moduleStatus[moduleId as keyof ModuleStatus] };
        } catch {
          return { moduleId, status: false };
        }
      });
      
      const results = await Promise.all(moduleChecks);
      results.forEach(({ moduleId, status }) => {
        this.moduleStatus[moduleId as keyof ModuleStatus] = status;
      });
      
      console.log('Module status checked:', this.moduleStatus);
    } catch (error) {
      console.error('Failed to check module status:', error);
    }
  }

  getConfiguration(): AppConfiguration {
    if (!this.initialized) {
      console.warn('Configuration Service not initialized, returning defaults');
    }
    return { ...this.configuration };
  }

  getModuleStatus(): ModuleStatus {
    return { ...this.moduleStatus };
  }

  async updateConfiguration(updates: Partial<AppConfiguration>): Promise<void> {
    this.configuration = { ...this.configuration, ...updates };
    await this.validateConfiguration();
    await this.saveConfiguration();
    
    console.log('Configuration updated:', updates);
  }

  async resetToDefaults(): Promise<void> {
    const defaults: AppConfiguration = {
      theme: 'light',
      language: 'en',
      autoSave: true,
      memoryMode: 'standard',
      cacheSize: 100,
      enableBatching: true,
      encryptionEnabled: true,
      sessionTimeout: 30,
      auditLogging: true,
      openaiEnabled: false,
      anthropicEnabled: false,
      rateLimit: 60,
      localPath: './devdocai-data',
      backupEnabled: true,
      retentionDays: 365,
      notificationsEnabled: true,
      emailAlerts: false,
    };
    
    this.configuration = defaults;
    await this.saveConfiguration();
    
    console.log('Configuration reset to defaults');
  }

  isInitialized(): boolean {
    return this.initialized;
  }

  // Utility methods for specific configuration aspects
  getApiConfiguration() {
    return {
      openaiEnabled: this.configuration.openaiEnabled,
      anthropicEnabled: this.configuration.anthropicEnabled,
      rateLimit: this.configuration.rateLimit,
    };
  }

  getSecurityConfiguration() {
    return {
      encryptionEnabled: this.configuration.encryptionEnabled,
      sessionTimeout: this.configuration.sessionTimeout,
      auditLogging: this.configuration.auditLogging,
    };
  }

  getPerformanceConfiguration() {
    return {
      memoryMode: this.configuration.memoryMode,
      cacheSize: this.configuration.cacheSize,
      enableBatching: this.configuration.enableBatching,
    };
  }

  getStorageConfiguration() {
    return {
      localPath: this.configuration.localPath,
      backupEnabled: this.configuration.backupEnabled,
      retentionDays: this.configuration.retentionDays,
    };
  }
}

// Export singleton instance
export const ConfigurationService = new ConfigurationServiceImpl();
export default ConfigurationService;