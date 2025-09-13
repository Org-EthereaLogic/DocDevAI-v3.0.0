// Base types
export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt: string;
}

// API Response types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: number;
  success: boolean;
}

export interface PaginatedResponse<T = any> {
  data: T[];
  pagination: {
    currentPage: number;
    totalPages: number;
    perPage: number;
    total: number;
  };
}

// Document types
export interface Document extends BaseEntity {
  name: string;
  type: DocumentType;
  content: string;
  description?: string;
  healthScore: number;
  status: DocumentStatus;
  projectId?: string;
  tags?: string[];
  metadata?: Record<string, any>;
  lastReviewed?: string;
  version?: string;
}

export type DocumentType =
  | 'readme'
  | 'api-doc'
  | 'changelog'
  | 'contributing'
  | 'license'
  | 'security'
  | 'deployment'
  | 'troubleshooting';

export type DocumentStatus =
  | 'draft'
  | 'active'
  | 'archived'
  | 'needs-review';

// Project types
export interface Project extends BaseEntity {
  name: string;
  description?: string;
  type: ProjectType;
  framework?: string;
  status: ProjectStatus;
  documentCount?: number;
  tags?: string[];
  repositoryUrl?: string;
  healthScore?: number;
}

export type ProjectType =
  | 'web'
  | 'mobile'
  | 'desktop'
  | 'library'
  | 'api'
  | 'cli'
  | 'other';

export type ProjectStatus =
  | 'active'
  | 'archived'
  | 'draft';

// Template types (M013)
export interface Template extends BaseEntity {
  name: string;
  description: string;
  category: string;
  content: string;
  tags: string[];
  downloads: number;
  rating: number;
  verified: boolean;
  published: boolean;
  author: string;
  version: string;
  signature?: string;
  isLocal?: boolean;
}

export interface TemplateMarketplace {
  featured: Template[];
  community: Template[];
  verified: Template[];
  userTemplates: Template[];
  downloadHistory: TemplateDownload[];
  publishedTemplates: Template[];
}

export interface TemplateDownload {
  templateId: string;
  downloadedAt: string;
  template: Template;
}

// Cost tracking types (M008)
export interface CostTransaction {
  id: string;
  timestamp: string;
  type: 'generation' | 'enhancement' | 'review';
  provider: LLMProvider;
  model: string;
  tokensInput: number;
  tokensOutput: number;
  cost: number;
  documentId?: string;
  operation: string;
}

export type LLMProvider = 'openai' | 'anthropic' | 'gemini' | 'local';

export interface CostBudgets {
  daily: number;
  weekly: number;
  monthly: number;
}

export interface CostUsage {
  daily: number;
  weekly: number;
  monthly: number;
  total: number;
}

// Tracking matrix types (M005)
export interface TrackingRelationship {
  id: string;
  source: string;
  target: string;
  type: RelationshipType;
  strength?: number;
  bidirectional?: boolean;
  createdAt: string;
  metadata?: Record<string, any>;
}

export type RelationshipType =
  | 'DEPENDS_ON'
  | 'REFERENCES'
  | 'IMPLEMENTS'
  | 'EXTENDS'
  | 'CONFLICTS'
  | 'SUPERSEDES'
  | 'DUPLICATES';

export interface DependencyGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  status: string;
  healthScore: number;
  lastModified: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: RelationshipType;
  strength: number;
  bidirectional: boolean;
}

// Batch operations types (M011)
export interface BatchOperation {
  id: string;
  documentId: string;
  documentName: string;
  status: BatchOperationStatus;
  progress: number;
  startTime?: string;
  endTime?: string;
  duration: number;
  result?: any;
  error?: string;
  retryCount: number;
}

export type BatchOperationStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed';

export interface Batch extends BaseEntity {
  operationType: BatchOperationType;
  status: BatchStatus;
  documents: Document[];
  operations: BatchOperation[];
  options: BatchOptions;
  startedAt?: string;
  completedAt?: string;
  totalDuration: number;
  progress: number;
  results: {
    successful: number;
    failed: number;
    total: number;
  };
  error?: string;
}

export type BatchOperationType =
  | 'generate'
  | 'enhance'
  | 'review'
  | 'export'
  | 'validate';

export type BatchStatus =
  | 'pending'
  | 'running'
  | 'paused'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface BatchOptions {
  priority: 'low' | 'normal' | 'high';
  retryOnFailure: boolean;
  notifyOnComplete: boolean;
  [key: string]: any;
}

// Review types (M007)
export interface Review extends BaseEntity {
  type: ReviewType;
  status: ReviewStatus;
  documentId: string;
  score?: number;
  findings?: ReviewFinding[];
  metadata?: Record<string, any>;
  completedAt?: string;
}

export type ReviewType =
  | 'quality'
  | 'security'
  | 'performance'
  | 'accessibility'
  | 'documentation';

export type ReviewStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed';

export interface ReviewFinding {
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
  location?: string;
  suggestion?: string;
}

// Settings types
export interface AppSettings {
  theme: 'light' | 'dark' | 'system';
  language: string;
  timezone: string;
  dateFormat: string;
  timeFormat: '12h' | '24h';
  privacyMode: 'strict' | 'standard' | 'minimal';
  telemetryEnabled: boolean;
  crashReportingEnabled: boolean;
  analyticsEnabled: boolean;
  aiProvider: LLMProvider;
  aiModel: string;
  maxTokens: number;
  temperature: number;
  costBudget: number;
  costAlerts: boolean;
  tooltipsEnabled: boolean;
  animationsEnabled: boolean;
  compactMode: boolean;
  sidebarCollapsed: boolean;
  autoSave: boolean;
  autoSaveInterval: number;
  defaultDocumentType: DocumentType;
  includeGenerationMetadata: boolean;
  enableVersioning: boolean;
  backupEnabled: boolean;
  maxBackups: number;
  memoryMode: 'low' | 'medium' | 'high' | 'auto';
  batchSize: number;
  parallelProcessing: boolean;
  cacheEnabled: boolean;
  cacheTTL: number;
  notificationsEnabled: boolean;
  emailNotifications: boolean;
  soundEnabled: boolean;
  notificationTypes: Record<string, boolean>;
}

// User and authentication types
export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  preferences?: Partial<AppSettings>;
  createdAt: string;
  lastLoginAt?: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  error: string | null;
  sessionExpiry: string | null;
}

// Notification types
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  duration?: number;
  timestamp: string;
  dismissed: boolean;
  persistent?: boolean;
  icon?: string;
  actions?: NotificationAction[];
  progress?: number;
}

export interface NotificationAction {
  label: string;
  callback?: () => void;
  dismiss?: boolean;
}

// Onboarding types
export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  completed: boolean;
}

export interface OnboardingPreferences {
  privacyMode: string | null;
  theme: string;
  tooltipsEnabled: boolean;
  aiProvider: string | null;
  projectType: string | null;
}

// Form types
export interface DocumentGenerationForm {
  projectName: string;
  description: string;
  documentType: DocumentType;
  includeExamples: boolean;
  targetAudience: string;
  language: string;
  enhancementLevel: 'basic' | 'standard' | 'advanced';
  useAI: boolean;
  aiProvider: LLMProvider;
}

// Error types
export interface AppError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
  context?: string;
}

// Utility types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredKeys<T, K extends keyof T> = Required<Pick<T, K>> & Omit<T, K>;

// Store state types
export interface StoreState {
  isLoading: boolean;
  error: string | null;
  lastUpdated: string | null;
}

// Component prop types
export interface ComponentProps {
  id?: string;
  class?: string;
  style?: string | Record<string, any>;
}

// Event types
export interface CustomEvent<T = any> {
  type: string;
  detail: T;
  timestamp: string;
}