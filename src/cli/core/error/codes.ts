/**
 * DevDocAI Error Codes
 * Module 1: Core Infrastructure - Error Code Definitions
 * Based on SDD Appendix B
 */

import { ErrorCategory } from '../../types/core';

// Configuration Errors (1000-1999)
export const CONFIG_ERRORS = {
  CONFIG_NOT_FOUND: '1001',
  CONFIG_INVALID_FORMAT: '1002',
  CONFIG_VALIDATION_FAILED: '1003',
  CONFIG_PERMISSION_DENIED: '1004',
  CONFIG_PARSE_ERROR: '1005',
  CONFIG_WRITE_ERROR: '1006',
  CONFIG_WATCH_ERROR: '1007',
  CONFIG_ENV_OVERRIDE_ERROR: '1008',
  CONFIG_CIRCULAR_REFERENCE: '1009',
  CONFIG_DEPRECATED_OPTION: '1010'
} as const;

// Processing Errors (2000-2999)
export const PROCESSING_ERRORS = {
  DOCUMENT_GENERATION_FAILED: '2001',
  TEMPLATE_NOT_FOUND: '2002',
  TEMPLATE_INVALID: '2003',
  ANALYSIS_FAILED: '2004',
  ENHANCEMENT_FAILED: '2005',
  MEMORY_LIMIT_EXCEEDED: '2006',
  TIMEOUT_ERROR: '2007',
  INVALID_INPUT: '2008',
  OUTPUT_WRITE_FAILED: '2009',
  PIPELINE_ERROR: '2010'
} as const;

// API Errors (3000-3999)
export const API_ERRORS = {
  API_CONNECTION_FAILED: '3001',
  API_AUTH_FAILED: '3002',
  API_RATE_LIMIT: '3003',
  API_INVALID_RESPONSE: '3004',
  API_TIMEOUT: '3005',
  API_QUOTA_EXCEEDED: '3006',
  API_INVALID_KEY: '3007',
  API_SERVICE_UNAVAILABLE: '3008',
  API_VERSION_MISMATCH: '3009',
  API_COST_LIMIT_EXCEEDED: '3010'
} as const;

// Security Errors (4000-4999)
export const SECURITY_ERRORS = {
  SECURITY_VALIDATION_FAILED: '4001',
  SECURITY_UNAUTHORIZED: '4002',
  SECURITY_FORBIDDEN: '4003',
  SECURITY_TOKEN_EXPIRED: '4004',
  SECURITY_ENCRYPTION_FAILED: '4005',
  SECURITY_DECRYPTION_FAILED: '4006',
  SECURITY_KEY_NOT_FOUND: '4007',
  SECURITY_SIGNATURE_INVALID: '4008',
  SECURITY_PII_DETECTED: '4009',
  SECURITY_COMPLIANCE_VIOLATION: '4010'
} as const;

// System Errors (5000-5999)
export const SYSTEM_ERRORS = {
  SYSTEM_INITIALIZATION_FAILED: '5001',
  SYSTEM_MEMORY_ERROR: '5002',
  SYSTEM_DISK_FULL: '5003',
  SYSTEM_PERMISSION_DENIED: '5004',
  SYSTEM_FILE_NOT_FOUND: '5005',
  SYSTEM_NETWORK_ERROR: '5006',
  SYSTEM_DEPENDENCY_MISSING: '5007',
  SYSTEM_INCOMPATIBLE_VERSION: '5008',
  SYSTEM_RESOURCE_UNAVAILABLE: '5009',
  SYSTEM_UNKNOWN_ERROR: '5999'
} as const;

// All error codes
export const ERROR_CODES = {
  ...CONFIG_ERRORS,
  ...PROCESSING_ERRORS,
  ...API_ERRORS,
  ...SECURITY_ERRORS,
  ...SYSTEM_ERRORS
} as const;

// Error messages and suggestions
export const ERROR_MESSAGES: Record<string, { message: string; suggestion: string; recoverable: boolean }> = {
  // Configuration Errors
  [CONFIG_ERRORS.CONFIG_NOT_FOUND]: {
    message: 'Configuration file not found',
    suggestion: 'Create a .devdocai.yml file or specify a custom path using --config',
    recoverable: true
  },
  [CONFIG_ERRORS.CONFIG_INVALID_FORMAT]: {
    message: 'Configuration file has invalid format',
    suggestion: 'Check YAML syntax and ensure proper indentation',
    recoverable: false
  },
  [CONFIG_ERRORS.CONFIG_VALIDATION_FAILED]: {
    message: 'Configuration validation failed',
    suggestion: 'Review configuration schema and fix validation errors',
    recoverable: false
  },
  [CONFIG_ERRORS.CONFIG_PERMISSION_DENIED]: {
    message: 'Permission denied accessing configuration file',
    suggestion: 'Check file permissions and ensure read access',
    recoverable: false
  },
  [CONFIG_ERRORS.CONFIG_PARSE_ERROR]: {
    message: 'Failed to parse configuration file',
    suggestion: 'Verify YAML syntax and check for special characters',
    recoverable: false
  },
  [CONFIG_ERRORS.CONFIG_CIRCULAR_REFERENCE]: {
    message: 'Circular reference detected in configuration',
    suggestion: 'Remove circular references from configuration',
    recoverable: false
  },

  // Processing Errors
  [PROCESSING_ERRORS.DOCUMENT_GENERATION_FAILED]: {
    message: 'Document generation failed',
    suggestion: 'Check template and input data, ensure all required fields are provided',
    recoverable: true
  },
  [PROCESSING_ERRORS.MEMORY_LIMIT_EXCEEDED]: {
    message: 'Memory limit exceeded',
    suggestion: 'Reduce batch size or switch to a lower memory mode',
    recoverable: true
  },
  [PROCESSING_ERRORS.TIMEOUT_ERROR]: {
    message: 'Operation timed out',
    suggestion: 'Increase timeout value or process smaller batches',
    recoverable: true
  },

  // API Errors
  [API_ERRORS.API_CONNECTION_FAILED]: {
    message: 'Failed to connect to API',
    suggestion: 'Check network connection and API endpoint',
    recoverable: true
  },
  [API_ERRORS.API_RATE_LIMIT]: {
    message: 'API rate limit exceeded',
    suggestion: 'Wait before retrying or upgrade your API plan',
    recoverable: true
  },
  [API_ERRORS.API_INVALID_KEY]: {
    message: 'Invalid API key',
    suggestion: 'Verify API key in configuration',
    recoverable: false
  },

  // Security Errors
  [SECURITY_ERRORS.SECURITY_UNAUTHORIZED]: {
    message: 'Unauthorized access',
    suggestion: 'Check credentials and authentication token',
    recoverable: false
  },
  [SECURITY_ERRORS.SECURITY_PII_DETECTED]: {
    message: 'Personally identifiable information detected',
    suggestion: 'Remove or mask PII before processing',
    recoverable: true
  },

  // System Errors
  [SYSTEM_ERRORS.SYSTEM_INITIALIZATION_FAILED]: {
    message: 'System initialization failed',
    suggestion: 'Check system requirements and dependencies',
    recoverable: false
  },
  [SYSTEM_ERRORS.SYSTEM_MEMORY_ERROR]: {
    message: 'Insufficient system memory',
    suggestion: 'Free up memory or use baseline memory mode',
    recoverable: true
  },
  [SYSTEM_ERRORS.SYSTEM_UNKNOWN_ERROR]: {
    message: 'An unknown error occurred',
    suggestion: 'Check logs for more details or contact support',
    recoverable: false
  }
};

/**
 * Get error category from error code
 */
export function getErrorCategory(code: string): ErrorCategory {
  const codeNum = parseInt(code, 10);
  if (codeNum >= 1000 && codeNum < 2000) return ErrorCategory.CONFIGURATION;
  if (codeNum >= 2000 && codeNum < 3000) return ErrorCategory.PROCESSING;
  if (codeNum >= 3000 && codeNum < 4000) return ErrorCategory.API;
  if (codeNum >= 4000 && codeNum < 5000) return ErrorCategory.SECURITY;
  if (codeNum >= 5000 && codeNum < 6000) return ErrorCategory.SYSTEM;
  return ErrorCategory.SYSTEM;
}