// DevDocAI API Services - Centralized Export

// Core API Client
export { apiClient, ApiClientError, enableApiLogging } from './api';

// Module Services - All 13 Backend Modules
export { configurationService } from './modules/configuration';
export { documentService } from './modules/documents';

// Re-export types for convenience
export type {
  ApiResponse,
  ApiError,
  PaginationParams,
  PaginatedResponse,

  // M001: Configuration Manager
  ConfigurationSettings,

  // M002: Storage
  StorageStats,

  // M003: MIAIR Engine
  MIAIRAnalysis,

  // M004: Document Generator
  DocumentTemplate,
  TemplateField,
  GenerationRequest,
  GeneratedDocument,

  // M005: Tracking Matrix
  DependencyNode,
  DependencyGraph,
  DependencyEdge,

  // M006: Suite Manager
  DocumentSuite,
  SuiteDocument,

  // M007: Review Engine
  DocumentReview,
  ReviewFinding,

  // M008: LLM Adapter
  LLMProviderStatus,
  LLMRequest,
  LLMResponse,

  // M009: Enhancement Pipeline
  EnhancementJob,
  EnhancementResult,

  // M010: SBOM Generator
  SBOMReport,
  SBOMComponent,
  Vulnerability,
  License,

  // M011: Batch Operations
  BatchJob,
  BatchOperationRequest,

  // M012: Version Control
  VersionControlInfo,
  CommitInfo,

  // M013: Template Marketplace
  MarketplaceTemplate,
  TemplateInstallation,

  // Common Types
  HealthScore,
  SystemStatus,
} from '@/types/api';

// Service Factory for Dependency Injection
export class ServiceFactory {
  private static instance: ServiceFactory;
  private services: Map<string, any> = new Map();

  public static getInstance(): ServiceFactory {
    if (!ServiceFactory.instance) {
      ServiceFactory.instance = new ServiceFactory();
    }
    return ServiceFactory.instance;
  }

  public register<T>(key: string, service: T): void {
    this.services.set(key, service);
  }

  public get<T>(key: string): T {
    const service = this.services.get(key);
    if (!service) {
      throw new Error(`Service '${key}' not found`);
    }
    return service as T;
  }

  public has(key: string): boolean {
    return this.services.has(key);
  }

  public clear(): void {
    this.services.clear();
  }
}

// Default service registration
const serviceFactory = ServiceFactory.getInstance();

// Lazy registration to avoid temporal dead zone
const registerServices = () => {
  try {
    serviceFactory.register('configuration', configurationService);
    serviceFactory.register('documents', documentService);
  } catch (error) {
    console.warn('Service registration delayed due to import timing:', error);
  }
};

// Try immediate registration, fallback to lazy
try {
  registerServices();
} catch {
  // If immediate registration fails, wait for next tick
  Promise.resolve().then(registerServices);
}

export { serviceFactory };

// API Health Check Utility
export const checkApiHealth = async (): Promise<{
  healthy: boolean;
  services: Record<string, boolean>;
  response_time_ms: number;
}> => {
  const startTime = Date.now();

  try {
    // Import apiClient locally to avoid temporal dead zone
    const { apiClient } = await import('./api');
    const response = await apiClient.get('/health');
    const responseTime = Date.now() - startTime;

    return {
      healthy: response.success,
      services: response.data?.services || {},
      response_time_ms: responseTime,
    };
  } catch (error) {
    return {
      healthy: false,
      services: {},
      response_time_ms: Date.now() - startTime,
    };
  }
};

// API Configuration Utilities
export const configureApi = async (config: {
  baseURL?: string;
  timeout?: number;
  token?: string;
}): Promise<void> => {
  // Import apiClient locally to avoid temporal dead zone
  const { apiClient } = await import('./api');

  if (config.baseURL) {
    apiClient.client.defaults.baseURL = config.baseURL;
  }

  if (config.timeout) {
    apiClient.client.defaults.timeout = config.timeout;
  }

  if (config.token) {
    apiClient.setAuthToken(config.token);
  }
};

// Error Handling Utilities
export const isApiError = (error: unknown): error is ApiClientError => {
  return error instanceof ApiClientError;
};

export const getErrorMessage = (error: unknown): string => {
  if (isApiError(error)) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unknown error occurred';
};

export const shouldRetry = (error: unknown): boolean => {
  return isApiError(error) && error.isRetryable();
};