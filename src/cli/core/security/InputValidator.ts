/**
 * @fileoverview Input validation and sanitization service for security hardening
 * @module @cli/core/security/InputValidator
 * @version 1.0.0
 * @security OWASP compliant input validation
 */

import * as path from 'path';
import { createHash } from 'crypto';

/**
 * Validation result interface
 */
export interface ValidationResult {
  isValid: boolean;
  sanitized?: unknown;
  errors?: string[];
  warnings?: string[];
}

/**
 * Security event for audit logging
 */
export interface SecurityEvent {
  type: 'validation_failure' | 'sanitization' | 'injection_attempt';
  source: string;
  input: string;
  timestamp: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

/**
 * Input validation and sanitization service
 * Provides comprehensive input validation to prevent injection attacks
 */
export class InputValidator {
  private static readonly MAX_INPUT_LENGTH = 10000;
  private static readonly MAX_PATH_LENGTH = 4096;
  private static readonly MAX_ENV_VAR_LENGTH = 32768;
  
  // Common injection patterns
  private static readonly INJECTION_PATTERNS = [
    /(\$\{.*?\})/g,                    // Template injection
    /({{.*?}})/g,                       // Template literals
    /(<script.*?>.*?<\/script>)/gi,    // Script injection
    /(javascript:)/gi,                  // JavaScript protocol
    /(on\w+\s*=)/gi,                   // Event handlers
    /(__proto__|constructor|prototype)/gi, // Prototype pollution
    /(require\s*\(|import\s+)/g,       // Code injection
    /(eval\s*\(|Function\s*\()/g,      // Eval injection
    /(process\.\w+)/g,                  // Process access
    /(child_process)/g,                 // Child process access
  ];

  // Path traversal patterns
  private static readonly PATH_TRAVERSAL_PATTERNS = [
    /\.\.[\/\\]/g,                      // Directory traversal
    /^[\/\\]/,                          // Absolute paths
    /^~[\/\\]/,                         // Home directory access
    /\0/g,                              // Null byte injection
    /%2e%2e/gi,                         // URL encoded traversal
    /\.\.%2f/gi,                        // Mixed encoding
  ];

  // Reserved environment variables that should never be modified
  private static readonly RESERVED_ENV_VARS = new Set([
    'PATH', 'HOME', 'USER', 'SHELL', 'PWD', 'NODE_ENV',
    'npm_', 'NODE_', 'npm_config_', 'npm_package_'
  ]);

  private securityEvents: SecurityEvent[] = [];
  private validationCache = new Map<string, ValidationResult>();

  /**
   * Validates YAML input to prevent injection attacks
   */
  public validateYamlInput(input: string): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Check input length
    if (!input || input.length === 0) {
      errors.push('Input cannot be empty');
      return { isValid: false, errors };
    }

    if (input.length > InputValidator.MAX_INPUT_LENGTH) {
      errors.push(`Input exceeds maximum length of ${InputValidator.MAX_INPUT_LENGTH}`);
      return { isValid: false, errors };
    }

    // Check for injection patterns
    for (const pattern of InputValidator.INJECTION_PATTERNS) {
      if (pattern.test(input)) {
        this.logSecurityEvent({
          type: 'injection_attempt',
          source: 'yaml_input',
          input: input.substring(0, 100),
          timestamp: Date.now(),
          severity: 'high'
        });
        errors.push(`Potential injection detected: ${pattern.source}`);
      }
    }

    // Check for suspicious YAML constructs
    if (/!!js\/function/.test(input)) {
      errors.push('JavaScript functions not allowed in YAML');
    }

    if (/!!python\//.test(input)) {
      errors.push('Python objects not allowed in YAML');
    }

    // Sanitize input
    let sanitized = input;
    
    // Remove comments that could hide malicious content
    sanitized = sanitized.replace(/#.*$/gm, '');
    
    // Remove control characters
    sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');

    // Validate YAML structure (basic check)
    const lines = sanitized.split('\n');
    let indentStack: number[] = [0];
    
    for (const line of lines) {
      if (line.trim() === '') continue;
      
      const indent = line.search(/\S/);
      if (indent === -1) continue;
      
      // Check for consistent indentation
      if (indent % 2 !== 0) {
        warnings.push('Inconsistent indentation detected');
      }
      
      // Check for deeply nested structures (potential DoS)
      if (indentStack.length > 10) {
        errors.push('YAML nesting too deep (max 10 levels)');
      }
      
      // Update indent stack
      while (indentStack.length > 0 && indent < indentStack[indentStack.length - 1]) {
        indentStack.pop();
      }
      if (indent > indentStack[indentStack.length - 1]) {
        indentStack.push(indent);
      }
    }

    return {
      isValid: errors.length === 0,
      sanitized,
      errors: errors.length > 0 ? errors : undefined,
      warnings: warnings.length > 0 ? warnings : undefined
    };
  }

  /**
   * Validates file paths to prevent directory traversal
   */
  public validateFilePath(filepath: string): ValidationResult {
    const errors: string[] = [];

    // Check path length
    if (!filepath || filepath.length === 0) {
      errors.push('File path cannot be empty');
      return { isValid: false, errors };
    }

    if (filepath.length > InputValidator.MAX_PATH_LENGTH) {
      errors.push(`Path exceeds maximum length of ${InputValidator.MAX_PATH_LENGTH}`);
      return { isValid: false, errors };
    }

    // Check for path traversal attempts
    for (const pattern of InputValidator.PATH_TRAVERSAL_PATTERNS) {
      if (pattern.test(filepath)) {
        this.logSecurityEvent({
          type: 'injection_attempt',
          source: 'file_path',
          input: filepath,
          timestamp: Date.now(),
          severity: 'critical'
        });
        errors.push(`Path traversal attempt detected: ${pattern.source}`);
      }
    }

    // Normalize and validate path
    try {
      const normalized = path.normalize(filepath);
      const resolved = path.resolve(normalized);
      
      // Ensure path stays within project boundaries
      const projectRoot = path.resolve(process.cwd());
      if (!resolved.startsWith(projectRoot)) {
        errors.push('Path must be within project directory');
      }

      // Check for sensitive directories
      const sensitivePatterns = [
        /node_modules/,
        /\.git/,
        /\.env/,
        /\.ssh/,
        /\.aws/,
        /\.config/
      ];

      for (const pattern of sensitivePatterns) {
        if (pattern.test(normalized)) {
          errors.push(`Access to sensitive directory denied: ${pattern.source}`);
        }
      }

      return {
        isValid: errors.length === 0,
        sanitized: normalized,
        errors: errors.length > 0 ? errors : undefined
      };
    } catch (error) {
      errors.push(`Invalid path: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return { isValid: false, errors };
    }
  }

  /**
   * Validates environment variables
   */
  public validateEnvironmentVar(key: string, value: string): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];

    // Validate key
    if (!key || !/^[A-Z_][A-Z0-9_]*$/i.test(key)) {
      errors.push('Invalid environment variable name');
      return { isValid: false, errors };
    }

    // Check reserved variables
    if (InputValidator.RESERVED_ENV_VARS.has(key) || 
        key.startsWith('npm_') || 
        key.startsWith('NODE_')) {
      warnings.push(`Modifying reserved variable: ${key}`);
    }

    // Validate value length
    if (value && value.length > InputValidator.MAX_ENV_VAR_LENGTH) {
      errors.push(`Value exceeds maximum length of ${InputValidator.MAX_ENV_VAR_LENGTH}`);
      return { isValid: false, errors };
    }

    // Check for injection in value
    for (const pattern of InputValidator.INJECTION_PATTERNS) {
      if (pattern.test(value)) {
        this.logSecurityEvent({
          type: 'injection_attempt',
          source: 'env_var',
          input: `${key}=${value.substring(0, 50)}`,
          timestamp: Date.now(),
          severity: 'medium'
        });
        errors.push(`Potential injection in environment variable value`);
      }
    }

    // Sanitize value
    let sanitized = value;
    
    // Remove shell metacharacters
    sanitized = sanitized.replace(/[;&|`$<>\\]/g, '');
    
    // Remove control characters
    sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');

    return {
      isValid: errors.length === 0,
      sanitized: { key, value: sanitized },
      errors: errors.length > 0 ? errors : undefined,
      warnings: warnings.length > 0 ? warnings : undefined
    };
  }

  /**
   * Generic input sanitization
   */
  public sanitizeUserInput(input: unknown): unknown {
    if (typeof input === 'string') {
      // Remove control characters
      let sanitized = input.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
      
      // Escape HTML entities
      sanitized = sanitized
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#x27;')
        .replace(/\//g, '&#x2F;');
      
      return sanitized;
    }
    
    if (Array.isArray(input)) {
      return input.map(item => this.sanitizeUserInput(item));
    }
    
    if (input && typeof input === 'object') {
      const sanitized: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(input)) {
        // Validate key to prevent prototype pollution
        if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
          this.logSecurityEvent({
            type: 'injection_attempt',
            source: 'object_key',
            input: key,
            timestamp: Date.now(),
            severity: 'critical'
          });
          continue;
        }
        sanitized[key] = this.sanitizeUserInput(value);
      }
      return sanitized;
    }
    
    return input;
  }

  /**
   * Validates JSON input
   */
  public validateJsonInput(input: string): ValidationResult {
    const errors: string[] = [];

    try {
      const parsed = JSON.parse(input);
      
      // Check for prototype pollution
      const checkPrototypePollution = (obj: any, path: string = ''): void => {
        if (obj && typeof obj === 'object') {
          for (const key of Object.keys(obj)) {
            if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
              errors.push(`Prototype pollution attempt at ${path}.${key}`);
            }
            if (typeof obj[key] === 'object') {
              checkPrototypePollution(obj[key], `${path}.${key}`);
            }
          }
        }
      };
      
      checkPrototypePollution(parsed);
      
      return {
        isValid: errors.length === 0,
        sanitized: this.sanitizeUserInput(parsed),
        errors: errors.length > 0 ? errors : undefined
      };
    } catch (error) {
      errors.push(`Invalid JSON: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return { isValid: false, errors };
    }
  }

  /**
   * Validates command-line arguments
   */
  public validateCliArgs(args: string[]): ValidationResult {
    const errors: string[] = [];
    const sanitized: string[] = [];

    for (const arg of args) {
      // Check for command injection
      if (/[;&|`$<>]/.test(arg)) {
        errors.push(`Potential command injection in argument: ${arg}`);
        continue;
      }

      // Check for path traversal in file arguments
      if (arg.includes('..') || arg.includes('~')) {
        const pathResult = this.validateFilePath(arg);
        if (!pathResult.isValid) {
          errors.push(...(pathResult.errors || []));
          continue;
        }
        sanitized.push(pathResult.sanitized as string);
      } else {
        sanitized.push(arg);
      }
    }

    return {
      isValid: errors.length === 0,
      sanitized,
      errors: errors.length > 0 ? errors : undefined
    };
  }

  /**
   * Creates a hash of input for cache keys
   */
  public createInputHash(input: string): string {
    return createHash('sha256').update(input).digest('hex');
  }

  /**
   * Logs security events for audit
   */
  private logSecurityEvent(event: SecurityEvent): void {
    this.securityEvents.push(event);
    
    // Keep only last 1000 events to prevent memory issues
    if (this.securityEvents.length > 1000) {
      this.securityEvents = this.securityEvents.slice(-1000);
    }
  }

  /**
   * Gets security events for audit
   */
  public getSecurityEvents(): SecurityEvent[] {
    return [...this.securityEvents];
  }

  /**
   * Clears security events
   */
  public clearSecurityEvents(): void {
    this.securityEvents = [];
  }
}

// Export singleton instance for consistent security policies
export const inputValidator = new InputValidator();