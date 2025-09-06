/**
 * ConfigLoader specific types
 * Module 1: Core Infrastructure - Configuration Management
 */

import { DevDocAIConfig, ValidationResult, ConfigChangeCallback } from '../../types/core';

export interface IConfigLoader {
  /**
   * Load configuration from a YAML file
   * @param path - Optional path to configuration file (defaults to .devdocai.yml)
   * @returns Promise resolving to loaded configuration
   */
  load(path?: string): Promise<DevDocAIConfig>;

  /**
   * Validate configuration against schema
   * @param config - Configuration object to validate
   * @returns Validation result with errors/warnings
   */
  validate(config: unknown): ValidationResult;

  /**
   * Watch configuration file for changes
   * @param callback - Function to call when configuration changes
   */
  watch(callback: ConfigChangeCallback): void;

  /**
   * Get default configuration
   * @returns Default configuration object
   */
  getDefault(): DevDocAIConfig;

  /**
   * Clear configuration cache
   */
  clearCache(): void;

  /**
   * Stop watching configuration file
   */
  stopWatching(): void;
}

export interface ConfigOptions {
  cachingEnabled?: boolean;
  watchEnabled?: boolean;
  environmentOverrides?: boolean;
  defaultPath?: string;
}

export interface ConfigCache {
  config: DevDocAIConfig;
  path: string;
  timestamp: number;
  hash: string;
}