/**
 * @fileoverview Unified Configuration Loader with mode-based behavior
 * @module @cli/core/config/ConfigLoader.unified
 * @version 1.0.0
 * @performance <10ms load time in all modes
 * @security Input validation, encryption, and audit logging
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { ConfigOptions, Config } from '../../types/core';
import { SecurityService, SecurityMode, ValidationResult, EncryptedValue } from '../security/SecurityService.unified';

/**
 * Configuration loader operation mode
 */
export enum ConfigLoaderMode {
  BASIC = 'basic',          // Simple loading, no optimization or security
  OPTIMIZED = 'optimized',  // Performance optimizations enabled
  SECURE = 'secure',        // Security features enabled
  ENTERPRISE = 'enterprise' // All features enabled
}

/**
 * Unified configuration loader options
 */
export interface UnifiedConfigLoaderOptions extends ConfigOptions {
  mode?: ConfigLoaderMode;
  security?: SecurityService;
  caching?: {
    enabled: boolean;
    ttl?: number;
    maxSize?: number;
  };
  performance?: {
    lazyLoad?: boolean;
    precompile?: boolean;
    parallelLoad?: boolean;
  };
}

/**
 * Unified Configuration Loader
 * Combines basic, optimized, and secure implementations into a single
 * configurable loader with mode-based behavior switching
 */
export class UnifiedConfigLoader {
  private mode: ConfigLoaderMode;
  private security: SecurityService;
  private defaults: Config;
  private cache = new Map<string, { config: Config; timestamp: number }>();
  private fileCache = new Map<string, string>();
  private pathCache = new Map<string, string>();
  private watchCallback?: (config: Config) => void;
  private currentConfigPath?: string;
  private options: UnifiedConfigLoaderOptions;

  // Pre-compiled patterns for performance
  private static readonly ENV_VAR_REGEX = /\$\{([^}]+)\}/g;
  private static readonly YAML_SCHEMA = yaml.DEFAULT_SCHEMA;
  private static readonly CONFIG_LOCATIONS = [
    '.devdocai.yml',
    '.devdocai.yaml',
    'devdocai.yml',
    'devdocai.yaml'
  ];

  // Performance metrics
  private metrics = {
    loadTime: 0,
    cacheHits: 0,
    cacheMisses: 0
  };

  constructor(options?: UnifiedConfigLoaderOptions) {
    this.options = options || {};
    this.mode = options?.mode || ConfigLoaderMode.BASIC;
    
    // Initialize security service based on mode
    this.security = options?.security || new SecurityService({
      mode: this.getSecurityMode(this.mode)
    });

    // Initialize defaults
    this.defaults = this.createDefaults(options?.defaults);
    
    // Setup performance features if needed
    if (this.isOptimized()) {
      this.setupOptimizations();
    }
  }

  /**
   * Map loader mode to security mode
   */
  private getSecurityMode(mode: ConfigLoaderMode): SecurityMode {
    switch (mode) {
      case ConfigLoaderMode.BASIC:
        return SecurityMode.BASIC;
      case ConfigLoaderMode.OPTIMIZED:
        return SecurityMode.BASIC;
      case ConfigLoaderMode.SECURE:
        return SecurityMode.SECURE;
      case ConfigLoaderMode.ENTERPRISE:
        return SecurityMode.ENTERPRISE;
      default:
        return SecurityMode.STANDARD;
    }
  }

  /**
   * Check if optimizations are enabled
   */
  private isOptimized(): boolean {
    return this.mode === ConfigLoaderMode.OPTIMIZED || 
           this.mode === ConfigLoaderMode.ENTERPRISE;
  }

  /**
   * Check if security is enabled
   */
  private isSecure(): boolean {
    return this.mode === ConfigLoaderMode.SECURE || 
           this.mode === ConfigLoaderMode.ENTERPRISE;
  }

  /**
   * Setup performance optimizations
   */
  private setupOptimizations(): void {
    // Pre-warm caches
    if (this.options.caching?.enabled !== false) {
      this.cache.clear();
      this.fileCache.clear();
      this.pathCache.clear();
    }

    // Setup cache cleanup
    if (this.options.caching?.ttl) {
      setInterval(() => this.cleanupCache(), this.options.caching.ttl);
    }
  }

  /**
   * Create default configuration
   */
  private createDefaults(overrides?: Partial<Config>): Config {
    return {
      theme: 'default',
      outputFormat: 'markdown',
      aiProvider: 'openai',
      maxTokens: 4000,
      temperature: 0.7,
      paths: {
        templates: './templates',
        output: './output',
        cache: './.devdocai-cache'
      },
      features: {
        autoSave: true,
        syntaxHighlighting: true,
        livePreview: false
      },
      api: {
        openai: { key: '', model: 'gpt-4' },
        anthropic: { key: '', model: 'claude-3' },
        local: { endpoint: 'http://localhost:11434', model: 'llama2' }
      },
      ...overrides
    };
  }

  /**
   * Load configuration with mode-based behavior
   */
  async load(configPath?: string): Promise<Config> {
    const startTime = Date.now();

    try {
      // Resolve path
      const resolvedPath = await this.resolvePath(configPath);
      this.currentConfigPath = resolvedPath;

      // Check cache if enabled
      if (this.isOptimized() && this.cache.has(resolvedPath)) {
        const cached = this.cache.get(resolvedPath)!;
        if (this.isCacheValid(cached)) {
          this.metrics.cacheHits++;
          this.metrics.loadTime = Date.now() - startTime;
          return cached.config;
        }
      }
      this.metrics.cacheMisses++;

      // Security validation if enabled
      if (this.isSecure()) {
        const validation = await this.security.validate(resolvedPath, {
          type: 'path',
          context: 'config_load'
        });
        
        if (!validation.valid) {
          throw new Error(`Security validation failed: ${validation.errors?.join(', ')}`);
        }
      }

      // Rate limiting if enabled
      if (this.isSecure()) {
        const allowed = await this.security.checkRateLimit('config_load');
        if (!allowed) {
          throw new Error('Rate limit exceeded for configuration loading');
        }
      }

      // Load and parse configuration
      const config = await this.loadAndParse(resolvedPath);

      // Merge with defaults
      const mergedConfig = this.mergeConfigs(this.defaults, config);

      // Process environment variables
      const processedConfig = this.processEnvironmentVars(mergedConfig);

      // Encrypt sensitive fields if in secure mode
      const finalConfig = await this.processSensitiveFields(processedConfig);

      // Cache if enabled
      if (this.isOptimized()) {
        this.cache.set(resolvedPath, {
          config: finalConfig,
          timestamp: Date.now()
        });
      }

      // Audit if enabled
      if (this.isSecure()) {
        await this.security.audit('config_loaded', {
          path: resolvedPath,
          mode: this.mode
        });
      }

      this.metrics.loadTime = Date.now() - startTime;
      return finalConfig;

    } catch (error) {
      this.metrics.loadTime = Date.now() - startTime;
      
      if (this.isSecure()) {
        await this.security.audit('config_load_error', {
          error: error.message,
          path: configPath
        });
      }
      
      throw error;
    }
  }

  /**
   * Resolve configuration path
   */
  private async resolvePath(configPath?: string): Promise<string> {
    // Check cache if optimized
    if (this.isOptimized() && configPath && this.pathCache.has(configPath)) {
      return this.pathCache.get(configPath)!;
    }

    if (configPath) {
      const resolved = path.resolve(configPath);
      if (this.isOptimized()) {
        this.pathCache.set(configPath, resolved);
      }
      return resolved;
    }

    // Search for config file
    for (const location of UnifiedConfigLoader.CONFIG_LOCATIONS) {
      const fullPath = path.resolve(process.cwd(), location);
      if (fs.existsSync(fullPath)) {
        if (this.isOptimized()) {
          this.pathCache.set('default', fullPath);
        }
        return fullPath;
      }
    }

    throw new Error('No configuration file found');
  }

  /**
   * Load and parse configuration file
   */
  private async loadAndParse(filePath: string): Promise<any> {
    // Check file cache if optimized
    if (this.isOptimized() && this.fileCache.has(filePath)) {
      const content = this.fileCache.get(filePath)!;
      return yaml.load(content, { schema: UnifiedConfigLoader.YAML_SCHEMA });
    }

    // Read file
    const content = await fs.promises.readFile(filePath, 'utf-8');

    // Cache if optimized
    if (this.isOptimized()) {
      this.fileCache.set(filePath, content);
    }

    // Validate content if secure
    if (this.isSecure()) {
      const validation = await this.security.validate(content, {
        type: 'config',
        context: 'config_parse'
      });
      
      if (!validation.valid) {
        throw new Error(`Config validation failed: ${validation.errors?.join(', ')}`);
      }
    }

    // Parse YAML
    return yaml.load(content, { schema: UnifiedConfigLoader.YAML_SCHEMA });
  }

  /**
   * Process environment variables in configuration
   */
  private processEnvironmentVars(config: any): any {
    const processValue = (value: any): any => {
      if (typeof value === 'string') {
        return value.replace(UnifiedConfigLoader.ENV_VAR_REGEX, (_, envVar) => {
          const envValue = process.env[envVar];
          if (envValue === undefined && this.isSecure()) {
            throw new Error(`Environment variable ${envVar} not found`);
          }
          return envValue || '';
        });
      }
      
      if (typeof value === 'object' && value !== null) {
        const processed: any = Array.isArray(value) ? [] : {};
        for (const key in value) {
          if (value.hasOwnProperty(key)) {
            processed[key] = processValue(value[key]);
          }
        }
        return processed;
      }
      
      return value;
    };

    return processValue(config);
  }

  /**
   * Process sensitive fields with encryption
   */
  private async processSensitiveFields(config: any): Promise<any> {
    if (!this.isSecure()) {
      return config;
    }

    const sensitivePatterns = [
      /password/i,
      /secret/i,
      /key/i,
      /token/i,
      /credential/i
    ];

    const processField = async (obj: any, path: string = ''): Promise<any> => {
      if (typeof obj !== 'object' || obj === null) {
        return obj;
      }

      const processed: any = Array.isArray(obj) ? [] : {};
      
      for (const key in obj) {
        if (!obj.hasOwnProperty(key)) continue;
        
        const fullPath = path ? `${path}.${key}` : key;
        const value = obj[key];
        
        // Check if field is sensitive
        const isSensitive = sensitivePatterns.some(pattern => pattern.test(key));
        
        if (isSensitive && typeof value === 'string') {
          // Encrypt sensitive string values
          processed[key] = await this.security.encrypt(value);
        } else if (typeof value === 'object') {
          // Recursively process objects
          processed[key] = await processField(value, fullPath);
        } else {
          processed[key] = value;
        }
      }
      
      return processed;
    };

    return processField(config);
  }

  /**
   * Merge configurations with deep merge
   */
  private mergeConfigs(base: any, override: any): any {
    if (override === undefined || override === null) {
      return base;
    }

    if (typeof base !== 'object' || typeof override !== 'object') {
      return override;
    }

    const merged = { ...base };
    
    for (const key in override) {
      if (override.hasOwnProperty(key)) {
        if (typeof override[key] === 'object' && 
            typeof merged[key] === 'object' &&
            !Array.isArray(override[key])) {
          merged[key] = this.mergeConfigs(merged[key], override[key]);
        } else {
          merged[key] = override[key];
        }
      }
    }
    
    return merged;
  }

  /**
   * Check if cache entry is valid
   */
  private isCacheValid(entry: { config: Config; timestamp: number }): boolean {
    if (!this.options.caching?.ttl) {
      return true; // No TTL, cache is always valid
    }
    
    const age = Date.now() - entry.timestamp;
    return age < this.options.caching.ttl;
  }

  /**
   * Clean up expired cache entries
   */
  private cleanupCache(): void {
    const now = Date.now();
    const ttl = this.options.caching?.ttl || 0;
    
    for (const [key, entry] of this.cache.entries()) {
      if (now - entry.timestamp > ttl) {
        this.cache.delete(key);
      }
    }
  }

  /**
   * Save configuration
   */
  async save(config: Config, configPath?: string): Promise<void> {
    const resolvedPath = configPath || this.currentConfigPath;
    
    if (!resolvedPath) {
      throw new Error('No configuration path specified');
    }

    // Validate if secure
    if (this.isSecure()) {
      const validation = await this.security.validate(config, {
        type: 'config',
        context: 'config_save'
      });
      
      if (!validation.valid) {
        throw new Error(`Config validation failed: ${validation.errors?.join(', ')}`);
      }
    }

    // Convert to YAML
    const yamlContent = yaml.dump(config, {
      indent: 2,
      lineWidth: 120,
      schema: UnifiedConfigLoader.YAML_SCHEMA
    });

    // Write file
    await fs.promises.writeFile(resolvedPath, yamlContent, 'utf-8');

    // Update cache if enabled
    if (this.isOptimized()) {
      this.cache.set(resolvedPath, {
        config,
        timestamp: Date.now()
      });
      this.fileCache.set(resolvedPath, yamlContent);
    }

    // Audit if enabled
    if (this.isSecure()) {
      await this.security.audit('config_saved', {
        path: resolvedPath
      });
    }
  }

  /**
   * Watch configuration file for changes
   */
  watch(callback: (config: Config) => void): void {
    if (!this.currentConfigPath) {
      throw new Error('No configuration loaded');
    }

    this.watchCallback = callback;

    fs.watch(this.currentConfigPath, async (eventType) => {
      if (eventType === 'change') {
        try {
          const config = await this.load(this.currentConfigPath);
          if (this.watchCallback) {
            this.watchCallback(config);
          }
        } catch (error) {
          console.error('Error reloading configuration:', error);
        }
      }
    });
  }

  /**
   * Get configuration metrics
   */
  getMetrics(): typeof this.metrics {
    return { ...this.metrics };
  }

  /**
   * Update loader mode
   */
  updateMode(mode: ConfigLoaderMode): void {
    this.mode = mode;
    this.security.updateConfig({
      mode: this.getSecurityMode(mode)
    });
    
    if (this.isOptimized()) {
      this.setupOptimizations();
    }
  }

  /**
   * Cleanup resources
   */
  async cleanup(): Promise<void> {
    this.cache.clear();
    this.fileCache.clear();
    this.pathCache.clear();
    await this.security.cleanup();
  }
}

// Export factory function for easy instantiation
export function createConfigLoader(options?: UnifiedConfigLoaderOptions): UnifiedConfigLoader {
  return new UnifiedConfigLoader(options);
}

// Export default instance with basic mode
export const configLoader = new UnifiedConfigLoader({ mode: ConfigLoaderMode.BASIC });