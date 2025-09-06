/**
 * @fileoverview Secure configuration loader with validation and encryption
 * @module @cli/core/config/ConfigLoader.secure
 * @version 3.0.0
 * @performance <10ms load time with security layers
 * @security Full input validation, encryption, and audit logging
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { ConfigLoaderOptimized } from './ConfigLoader.optimized';
import { 
  inputValidator, 
  auditLogger, 
  rateLimiter, 
  encryptionService,
  type ValidationResult,
  type EncryptedValue
} from '../security';

/**
 * Secure configuration with encrypted sensitive fields
 */
export interface SecureConfig extends Record<string, any> {
  encrypted?: Record<string, EncryptedValue>;
  _integrity?: string;
  _version?: number;
}

/**
 * Secure configuration loader options
 */
export interface SecureConfigLoaderOptions {
  enableEncryption?: boolean;
  enableAudit?: boolean;
  enableRateLimit?: boolean;
  sensitiveFields?: string[];
  maxConfigSize?: number;
  allowedPaths?: string[];
}

/**
 * Secure configuration loader with comprehensive security features
 * Extends optimized loader to maintain performance while adding security
 */
export class SecureConfigLoader extends ConfigLoaderOptimized {
  private readonly securityOptions: Required<SecureConfigLoaderOptions>;
  private readonly sensitiveFieldPatterns: RegExp[] = [
    /password/i,
    /secret/i,
    /token/i,
    /key/i,
    /credential/i,
    /auth/i,
    /api[-_]?key/i,
    /private/i
  ];

  constructor(options: SecureConfigLoaderOptions = {}) {
    super();
    
    this.securityOptions = {
      enableEncryption: options.enableEncryption ?? true,
      enableAudit: options.enableAudit ?? true,
      enableRateLimit: options.enableRateLimit ?? true,
      sensitiveFields: options.sensitiveFields || [],
      maxConfigSize: options.maxConfigSize || 1048576, // 1MB
      allowedPaths: options.allowedPaths || [process.cwd()]
    };

    // Initialize security monitoring
    this.initializeSecurity();
  }

  /**
   * Initializes security monitoring
   */
  private initializeSecurity(): void {
    // Set up rate limiter handlers
    rateLimiter.on('rate_limit_exceeded', (event) => {
      auditLogger.logSuspiciousActivity(
        `Rate limit exceeded for ${event.operation}`,
        'high',
        event
      );
    });

    // Set up encryption handlers
    encryptionService.on('encryption_error', (event) => {
      auditLogger.logSecurityEvent({
        type: 'encryption_operation',
        severity: 'high',
        source: 'config_loader',
        result: 'failure',
        details: event
      });
    });
  }

  /**
   * Loads configuration from file with security validation
   */
  public async loadFromFile(filePath: string): Promise<SecureConfig> {
    const startTime = Date.now();

    try {
      // Check rate limit
      if (this.securityOptions.enableRateLimit && 
          !rateLimiter.checkConfigLoadLimit(filePath)) {
        throw new Error('Rate limit exceeded for configuration loading');
      }

      // Validate file path
      const pathValidation = this.validateFilePath(filePath);
      if (!pathValidation.isValid) {
        throw new Error(`Invalid file path: ${pathValidation.errors?.join(', ')}`);
      }

      // Audit the access attempt
      if (this.securityOptions.enableAudit) {
        auditLogger.logAccessAttempt(filePath, 'allowed', {
          operation: 'config_load',
          timestamp: Date.now()
        });
      }

      // Check file size
      const stats = await fs.promises.stat(filePath);
      if (stats.size > this.securityOptions.maxConfigSize) {
        throw new Error(`Configuration file exceeds maximum size of ${this.securityOptions.maxConfigSize} bytes`);
      }

      // Read and validate content
      const content = await fs.promises.readFile(filePath, 'utf-8');
      const config = await this.parseSecureConfig(content, path.extname(filePath));

      // Cache the secure config
      this.cache.set(filePath, config);

      // Log successful load
      if (this.securityOptions.enableAudit) {
        auditLogger.logConfigurationChange({
          path: filePath,
          newValue: { loaded: true, size: stats.size },
          reason: 'Configuration loaded successfully'
        });
      }

      // Performance tracking
      const loadTime = Date.now() - startTime;
      if (loadTime > 10) {
        console.warn(`Secure config load time exceeded target: ${loadTime}ms`);
      }

      return config;
    } catch (error) {
      // Audit the failure
      if (this.securityOptions.enableAudit) {
        auditLogger.logAccessAttempt(filePath, 'denied', {
          operation: 'config_load',
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }

      throw error;
    }
  }

  /**
   * Validates file path for security
   */
  private validateFilePath(filePath: string): ValidationResult {
    // First use the input validator
    const validation = inputValidator.validateFilePath(filePath);
    if (!validation.isValid) {
      return validation;
    }

    // Additional checks for config files
    const resolvedPath = path.resolve(filePath);
    
    // Check if path is in allowed directories
    const isAllowed = this.securityOptions.allowedPaths.some(allowed => 
      resolvedPath.startsWith(path.resolve(allowed))
    );

    if (!isAllowed) {
      return {
        isValid: false,
        errors: [`Path not in allowed directories: ${this.securityOptions.allowedPaths.join(', ')}`]
      };
    }

    // Check file extension
    const ext = path.extname(filePath).toLowerCase();
    const allowedExtensions = ['.yaml', '.yml', '.json', '.js', '.ts'];
    if (!allowedExtensions.includes(ext)) {
      return {
        isValid: false,
        errors: [`Invalid configuration file extension: ${ext}`]
      };
    }

    return { isValid: true, sanitized: resolvedPath };
  }

  /**
   * Parses and secures configuration content
   */
  private async parseSecureConfig(content: string, extension: string): Promise<SecureConfig> {
    let config: any;

    // Parse based on file type
    switch (extension.toLowerCase()) {
      case '.yaml':
      case '.yml':
        const yamlValidation = inputValidator.validateYamlInput(content);
        if (!yamlValidation.isValid) {
          throw new Error(`YAML validation failed: ${yamlValidation.errors?.join(', ')}`);
        }
        config = yaml.load(yamlValidation.sanitized as string);
        break;

      case '.json':
        const jsonValidation = inputValidator.validateJsonInput(content);
        if (!jsonValidation.isValid) {
          throw new Error(`JSON validation failed: ${jsonValidation.errors?.join(', ')}`);
        }
        config = jsonValidation.sanitized;
        break;

      default:
        throw new Error(`Unsupported file extension: ${extension}`);
    }

    // Sanitize the entire config
    config = inputValidator.sanitizeUserInput(config);

    // Encrypt sensitive fields
    if (this.securityOptions.enableEncryption) {
      config = await this.encryptSensitiveFields(config);
    }

    // Add integrity check
    config._integrity = encryptionService.createMAC(JSON.stringify(config));
    config._version = Date.now();

    return config as SecureConfig;
  }

  /**
   * Encrypts sensitive fields in configuration
   */
  private async encryptSensitiveFields(config: any): Promise<any> {
    const encrypted: Record<string, EncryptedValue> = {};
    
    const processField = (obj: any, path: string = ''): any => {
      if (typeof obj !== 'object' || obj === null) {
        return obj;
      }

      const result: any = Array.isArray(obj) ? [] : {};

      for (const [key, value] of Object.entries(obj)) {
        const currentPath = path ? `${path}.${key}` : key;
        
        // Check if field should be encrypted
        if (this.shouldEncryptField(key, value)) {
          // Encrypt the value
          const encryptedValue = encryptionService.encryptSecret(
            typeof value === 'string' ? value : JSON.stringify(value),
            currentPath
          );
          encrypted[currentPath] = encryptedValue;
          
          // Replace with placeholder
          result[key] = `[ENCRYPTED:${currentPath}]`;
          
          // Audit encryption
          if (this.securityOptions.enableAudit) {
            auditLogger.logSecurityEvent({
              type: 'encryption_operation',
              severity: 'info',
              source: 'config_loader',
              resource: currentPath,
              result: 'success'
            });
          }
        } else if (typeof value === 'object' && value !== null) {
          result[key] = processField(value, currentPath);
        } else {
          result[key] = value;
        }
      }

      return result;
    };

    const securedConfig = processField(config);
    
    // Attach encrypted values metadata
    if (Object.keys(encrypted).length > 0) {
      securedConfig.encrypted = encrypted;
    }

    return securedConfig;
  }

  /**
   * Determines if a field should be encrypted
   */
  private shouldEncryptField(key: string, value: any): boolean {
    // Check explicit sensitive fields
    if (this.securityOptions.sensitiveFields.includes(key)) {
      return true;
    }

    // Check patterns
    for (const pattern of this.sensitiveFieldPatterns) {
      if (pattern.test(key)) {
        return true;
      }
    }

    // Check value patterns (e.g., looks like API key)
    if (typeof value === 'string') {
      // Looks like an API key or token
      if (/^[A-Za-z0-9+/]{20,}={0,2}$/.test(value) ||
          /^sk-[A-Za-z0-9]{48}$/.test(value) ||
          /^[A-Fa-f0-9]{32,}$/.test(value)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Decrypts sensitive fields in configuration
   */
  public async decryptConfig(config: SecureConfig): Promise<any> {
    if (!config.encrypted) {
      return config;
    }

    const decrypted = { ...config };
    delete decrypted.encrypted;

    // Decrypt each field
    for (const [path, encryptedValue] of Object.entries(config.encrypted)) {
      try {
        const decryptedValue = encryptionService.decryptSecret(encryptedValue, path);
        
        // Set the decrypted value at the correct path
        this.setNestedValue(decrypted, path, decryptedValue);
        
        // Audit decryption
        if (this.securityOptions.enableAudit) {
          auditLogger.logSecurityEvent({
            type: 'decryption_operation',
            severity: 'info',
            source: 'config_loader',
            resource: path,
            result: 'success'
          });
        }
      } catch (error) {
        // Log decryption failure
        if (this.securityOptions.enableAudit) {
          auditLogger.logSecurityEvent({
            type: 'decryption_operation',
            severity: 'high',
            source: 'config_loader',
            resource: path,
            result: 'failure',
            details: { error: error instanceof Error ? error.message : 'Unknown error' }
          });
        }
        throw error;
      }
    }

    return decrypted;
  }

  /**
   * Sets a nested value in an object
   */
  private setNestedValue(obj: any, path: string, value: any): void {
    const keys = path.split('.');
    let current = obj;

    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (!(key in current) || typeof current[key] !== 'object') {
        current[key] = {};
      }
      current = current[key];
    }

    const lastKey = keys[keys.length - 1];
    current[lastKey] = value;
  }

  /**
   * Validates configuration integrity
   */
  public validateIntegrity(config: SecureConfig): boolean {
    if (!config._integrity) {
      return false;
    }

    const configCopy = { ...config };
    const storedIntegrity = configCopy._integrity;
    delete configCopy._integrity;

    const computedIntegrity = encryptionService.createMAC(JSON.stringify(configCopy));
    
    const isValid = storedIntegrity === computedIntegrity;
    
    if (!isValid && this.securityOptions.enableAudit) {
      auditLogger.logSuspiciousActivity(
        'Configuration integrity check failed',
        'critical',
        { configVersion: config._version }
      );
    }

    return isValid;
  }

  /**
   * Saves configuration with security
   */
  public async saveConfig(config: SecureConfig, filePath: string): Promise<void> {
    // Validate path
    const pathValidation = this.validateFilePath(filePath);
    if (!pathValidation.isValid) {
      throw new Error(`Invalid file path: ${pathValidation.errors?.join(', ')}`);
    }

    // Check rate limit
    if (this.securityOptions.enableRateLimit && 
        !rateLimiter.checkConfigLoadLimit(`save:${filePath}`)) {
      throw new Error('Rate limit exceeded for configuration saving');
    }

    // Update integrity
    config._integrity = encryptionService.createMAC(JSON.stringify(config));
    config._version = Date.now();

    // Convert to appropriate format
    const ext = path.extname(filePath).toLowerCase();
    let content: string;

    switch (ext) {
      case '.yaml':
      case '.yml':
        content = yaml.dump(config);
        break;
      case '.json':
        content = JSON.stringify(config, null, 2);
        break;
      default:
        throw new Error(`Unsupported file extension: ${ext}`);
    }

    // Write file with secure permissions
    await fs.promises.writeFile(filePath, content, {
      mode: 0o600 // Read/write for owner only
    });

    // Audit the save
    if (this.securityOptions.enableAudit) {
      auditLogger.logConfigurationChange({
        path: filePath,
        newValue: { saved: true, version: config._version },
        reason: 'Configuration saved'
      });
    }
  }

  /**
   * Clears sensitive data from memory
   */
  public clearSensitiveData(): void {
    // Clear cache
    for (const [key, config] of this.cache.entries()) {
      if (config && typeof config === 'object' && 'encrypted' in config) {
        encryptionService.secureDelete(JSON.stringify(config));
      }
    }
    this.cache.clear();

    // Audit the clear operation
    if (this.securityOptions.enableAudit) {
      auditLogger.logSecurityEvent({
        type: 'encryption_operation',
        severity: 'info',
        source: 'config_loader',
        action: 'clear_sensitive_data',
        result: 'success'
      });
    }
  }
}

// Export singleton instance for consistent security policies
export const secureConfigLoader = new SecureConfigLoader();