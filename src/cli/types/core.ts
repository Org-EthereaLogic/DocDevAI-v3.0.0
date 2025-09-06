/**
 * Core type definitions for DevDocAI CLI
 * Module 1: Core Infrastructure
 */

// Configuration Types
export interface DevDocAIConfig {
  memory: MemoryConfig;
  logging: LoggingConfig;
  output: OutputConfig;
  modules: ModulesConfig;
  version: string;
  environment: 'development' | 'production' | 'test';
}

export interface MemoryConfig {
  mode: MemoryMode;
  maxWorkers?: number;
  cacheSize?: number;
  enableOptimizations?: boolean;
}

export interface LoggingConfig {
  level: LogLevel;
  format: 'json' | 'text';
  outputPath?: string;
  enableConsole?: boolean;
  enableFile?: boolean;
}

export interface OutputConfig {
  format: 'json' | 'yaml' | 'text';
  pretty?: boolean;
  color?: boolean;
}

export interface ModulesConfig {
  enabled: string[];
  settings: Record<string, unknown>;
}

// Memory Mode Types
export enum MemoryMode {
  BASELINE = 'baseline',      // <2GB RAM
  STANDARD = 'standard',      // 2-4GB RAM
  ENHANCED = 'enhanced',      // 4-8GB RAM
  PERFORMANCE = 'performance', // >8GB RAM
  AUTO = 'auto'               // Auto-detect
}

export interface SystemMemoryInfo {
  total: number;
  free: number;
  available: number;
  used: number;
  percentage: number;
}

export interface MemoryModeRecommendation {
  recommended: MemoryMode;
  reason: string;
  systemMemory: SystemMemoryInfo;
  optimizations: string[];
}

// Logging Types
export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
  SILENT = 'silent'
}

export interface LogContext {
  module?: string;
  operation?: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
  error?: ErrorInfo;
  correlationId: string;
}

export interface ErrorInfo {
  code: string;
  message: string;
  stack?: string;
  cause?: Error;
}

export interface LogTransport {
  name: string;
  write(entry: LogEntry): void;
}

export interface LogEntry {
  level: LogLevel;
  message: string;
  context: LogContext;
}

// Error Types
export enum ErrorCategory {
  CONFIGURATION = '1000',      // 1001-1999
  PROCESSING = '2000',         // 2001-2999
  API = '3000',               // 3001-3999
  SECURITY = '4000',          // 4001-4999
  SYSTEM = '5000'             // 5001-5999
}

export interface FormattedError {
  code: string;
  category: ErrorCategory;
  message: string;
  suggestion: string;
  recoverable: boolean;
  timestamp: string;
  context?: Record<string, unknown>;
}

// Additional Configuration Types for GREEN phase
export interface Config {
  theme: string;
  outputFormat: string;
  aiProvider: string;
  maxTokens: number;
  temperature: number;
  paths: {
    templates: string;
    output: string;
    cache: string;
  };
  features: {
    autoSave: boolean;
    syntaxHighlighting: boolean;
    livePreview: boolean;
  };
  api: {
    openai: { key: string; model: string };
    anthropic: { key: string; model: string };
    local: { endpoint: string; model: string };
  };
  memory?: {
    mode?: MemoryMode;
    legacyOption?: boolean;
  };
  logging?: {
    level?: LogLevel;
  };
}

export interface ConfigOptions {
  defaults?: Partial<Config>;
}

export interface ValidationError {
  field: string;
  message: string;
  value: any;
}

// Validation Types
export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings?: string[];
}

// Callback Types
export type ConfigChangeCallback = (config: DevDocAIConfig) => void;

// Performance Types
export interface PerformanceMetrics {
  startupTime: number;
  configLoadTime: number;
  memoryUsage: number;
  cpuUsage: number;
}