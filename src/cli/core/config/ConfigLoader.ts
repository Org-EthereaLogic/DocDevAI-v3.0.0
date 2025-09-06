import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { ConfigOptions, Config } from '../../types/core';

export class ConfigLoader {
  private cache: Map<string, Config> = new Map();
  private defaults: Config = {
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
    }
  };

  constructor(options?: ConfigOptions) {
    if (options?.defaults) {
      this.defaults = { ...this.defaults, ...options.defaults };
    }
  }

  async load(configPath?: string): Promise<Config> {
    const resolvedPath = this.resolvePath(configPath);
    this.currentConfigPath = resolvedPath; // Store for file watching
    
    // Check cache
    if (this.cache.has(resolvedPath)) {
      return this.cache.get(resolvedPath)!;
    }

    try {
      const configContent = await fs.promises.readFile(resolvedPath, 'utf-8');
      const rawConfig = yaml.load(configContent) as any;
      
      // Process environment variables
      const processedConfig = this.processEnvironmentVariables(rawConfig);
      
      // Validate
      this.validateAndThrow(processedConfig);
      
      // Merge with defaults
      const config = this.mergeWithDefaults(processedConfig);
      
      // Cache
      this.cache.set(resolvedPath, config);
      
      return config;
    } catch (error: any) {
      if (error.code === 'ENOENT') {
        throw new Error(`Config file not found: ${resolvedPath}`);
      }
      if (error.name === 'YAMLException') {
        throw new Error(`Invalid YAML: ${error.message}`);
      }
      throw error;
    }
  }

  loadSync(configPath?: string): Config {
    const resolvedPath = this.resolvePath(configPath);
    this.currentConfigPath = resolvedPath; // Store for file watching
    
    // Check cache
    if (this.cache.has(resolvedPath)) {
      return this.cache.get(resolvedPath)!;
    }

    try {
      const configContent = fs.readFileSync(resolvedPath, 'utf-8');
      const rawConfig = yaml.load(configContent) as any;
      
      // Process environment variables
      const processedConfig = this.processEnvironmentVariables(rawConfig);
      
      // Validate
      this.validateAndThrow(processedConfig);
      
      // Merge with defaults
      const config = this.mergeWithDefaults(processedConfig);
      
      // Cache
      this.cache.set(resolvedPath, config);
      
      return config;
    } catch (error: any) {
      if (error.code === 'ENOENT') {
        throw new Error(`Config file not found: ${resolvedPath}`);
      }
      if (error.name === 'YAMLException') {
        throw new Error(`Invalid YAML: ${error.message}`);
      }
      throw error;
    }
  }

  validate(config: any): any {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check for invalid memory mode
    if (config.memory?.mode && !['baseline', 'standard', 'enhanced', 'performance'].includes(config.memory.mode)) {
      errors.push(`Invalid memory mode: ${config.memory.mode}`);
    }

    // Check for invalid log level
    if (config.logging?.level && !['debug', 'info', 'warn', 'error', 'fatal'].includes(config.logging.level)) {
      errors.push(`Invalid log level: ${config.logging.level}`);
    }

    // Check for deprecated options
    if (config.memory?.legacyOption) {
      warnings.push('Deprecated option: memory.legacyOption');
    }

    // Required fields
    if (config.aiProvider && !['openai', 'anthropic', 'local'].includes(config.aiProvider)) {
      errors.push('Invalid AI provider');
    }

    if (config.maxTokens !== undefined) {
      if (typeof config.maxTokens !== 'number' || config.maxTokens < 1 || config.maxTokens > 128000) {
        errors.push('maxTokens must be between 1 and 128000');
      }
    }

    if (config.temperature !== undefined) {
      if (typeof config.temperature !== 'number' || config.temperature < 0 || config.temperature > 2) {
        errors.push('temperature must be between 0 and 2');
      }
    }

    // Return validation result object
    return {
      valid: errors.length === 0,
      errors,
      warnings
    };
  }

  private validateAndThrow(config: any): void {
    const result = this.validate(config);
    if (!result.valid) {
      const error = new Error(`Validation failed: ${result.errors.join(', ')}`);
      (error as any).errors = result.errors;
      throw error;
    }
  }

  merge(base: Config, overrides: Partial<Config>): Config {
    return this.deepMerge(base, overrides) as Config;
  }

  clearCache(): void {
    this.cache.clear();
  }

  getDefaults(): Config {
    return { ...this.defaults };
  }

  getDefault(): Config {
    // Alias for getDefaults to match test expectations
    return this.getDefaults();
  }

  watch(callback: (config: Config) => void): void {
    this.watchCallback = callback;
    
    // Implement file watching for REFACTOR phase
    if (this.currentConfigPath && fs.existsSync(this.currentConfigPath)) {
      fs.watchFile(this.currentConfigPath, { interval: 1000 }, async () => {
        try {
          const newConfig = await this.load(this.currentConfigPath);
          if (this.watchCallback) {
            this.watchCallback(newConfig);
          }
        } catch (error) {
          console.error('Error reloading config:', error);
        }
      });
    }
  }

  stopWatching(): void {
    if (this.currentConfigPath && fs.existsSync(this.currentConfigPath)) {
      fs.unwatchFile(this.currentConfigPath);
    }
    this.watchCallback = undefined;
  }

  private watchCallback?: (config: Config) => void;
  private currentConfigPath?: string;

  private resolvePath(configPath?: string): string {
    if (configPath) {
      return path.resolve(configPath);
    }
    
    // Check common locations
    const locations = [
      '.devdocai.yml',
      '.devdocai.yaml',
      'devdocai.yml',
      'devdocai.yaml',
      path.join(process.cwd(), '.devdocai.yml'),
      path.join(process.cwd(), '.devdocai.yaml')
    ];

    for (const loc of locations) {
      if (fs.existsSync(loc)) {
        return path.resolve(loc);
      }
    }

    return path.resolve('.devdocai.yml');
  }

  private processEnvironmentVariables(config: any): any {
    const processValue = (value: any): any => {
      if (typeof value === 'string') {
        // Replace ${VAR_NAME} with environment variable
        return value.replace(/\$\{([^}]+)\}/g, (match, varName) => {
          return process.env[varName] || match;
        });
      }
      if (Array.isArray(value)) {
        return value.map(processValue);
      }
      if (value && typeof value === 'object') {
        const result: any = {};
        for (const key in value) {
          result[key] = processValue(value[key]);
        }
        return result;
      }
      return value;
    };

    return processValue(config);
  }

  private mergeWithDefaults(config: any): Config {
    return this.deepMerge(this.defaults, config) as Config;
  }

  private deepMerge(target: any, source: any): any {
    if (!source) return target;
    
    const result = { ...target };
    
    for (const key in source) {
      if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
        result[key] = this.deepMerge(target[key] || {}, source[key]);
      } else {
        result[key] = source[key];
      }
    }
    
    return result;
  }
}