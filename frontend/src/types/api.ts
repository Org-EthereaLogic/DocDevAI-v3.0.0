// API Response Types for DevDocAI Backend Integration

// Base API Response
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
  metadata?: {
    timestamp: string;
    request_id: string;
    version: string;
  };
}

// Error Types
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, any>;
  field_errors?: Record<string, string[]>;
}

// M001: Configuration Manager Types
export interface ConfigurationSettings {
  privacy_mode: 'local_only' | 'local_manual_cloud' | 'smart_mode';
  memory_mode: 'low' | 'medium' | 'high' | 'ultra';
  ai_providers: {
    primary: string;
    fallback: string[];
    budget_limit: number;
  };
  telemetry_enabled: boolean;
  encryption_enabled: boolean;
}

// M002: Storage Types
export interface StorageStats {
  total_documents: number;
  total_size_bytes: number;
  encrypted: boolean;
  backup_status: 'current' | 'outdated' | 'none';
}

// M003: MIAIR Engine Types
export interface MIAIRAnalysis {
  entropy_score: number;
  quality_improvement: number;
  optimization_suggestions: string[];
  processing_time_ms: number;
}

// M004: Document Generator Types
export interface DocumentTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  fields: TemplateField[];
  ai_enabled: boolean;
}

export interface TemplateField {
  name: string;
  type: 'text' | 'select' | 'boolean' | 'number' | 'array';
  required: boolean;
  description?: string;
  options?: string[];
}

export interface GenerationRequest {
  template_id: string;
  input_data: Record<string, any>;
  ai_enhancement: boolean;
  output_format: 'markdown' | 'html' | 'pdf';
}

export interface GeneratedDocument {
  id: string;
  title: string;
  content: string;
  format: string;
  health_score: number;
  generated_at: string;
  ai_enhanced: boolean;
}

// M005: Tracking Matrix Types
export interface DependencyNode {
  id: string;
  name: string;
  type: 'document' | 'component' | 'api' | 'external';
  dependencies: string[];
  dependents: string[];
  last_updated: string;
}

export interface DependencyGraph {
  nodes: DependencyNode[];
  edges: DependencyEdge[];
  circular_references: string[][];
}

export interface DependencyEdge {
  from: string;
  to: string;
  relationship_type: 'depends_on' | 'references' | 'implements' | 'extends';
}

// M006: Suite Manager Types
export interface DocumentSuite {
  id: string;
  name: string;
  description: string;
  documents: SuiteDocument[];
  consistency_score: number;
  created_at: string;
  updated_at: string;
}

export interface SuiteDocument {
  id: string;
  title: string;
  health_score: number;
  last_reviewed: string;
  status: 'draft' | 'review' | 'approved' | 'published';
}

// M007: Review Engine Types
export interface DocumentReview {
  document_id: string;
  overall_score: number;
  dimension_scores: {
    clarity: number;
    completeness: number;
    consistency: number;
    accuracy: number;
  };
  findings: ReviewFinding[];
  recommendations: string[];
  reviewed_at: string;
}

export interface ReviewFinding {
  type: 'error' | 'warning' | 'suggestion' | 'info';
  category: string;
  message: string;
  location?: {
    line: number;
    column: number;
  };
  severity: 'critical' | 'high' | 'medium' | 'low';
}

// M008: LLM Adapter Types
export interface LLMProviderStatus {
  provider: string;
  available: boolean;
  response_time_ms: number;
  cost_per_1k_tokens: number;
  daily_usage: number;
  daily_limit: number;
}

export interface LLMRequest {
  prompt: string;
  provider?: string;
  max_tokens?: number;
  temperature?: number;
  model?: string;
}

export interface LLMResponse {
  content: string;
  provider_used: string;
  tokens_used: number;
  cost: number;
  processing_time_ms: number;
}

// M009: Enhancement Pipeline Types
export interface EnhancementJob {
  id: string;
  document_id: string;
  strategy: 'miair_only' | 'llm_only' | 'combined' | 'weighted_consensus';
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress_percentage: number;
  estimated_completion: string;
}

export interface EnhancementResult {
  original_score: number;
  enhanced_score: number;
  improvement_percentage: number;
  changes_made: string[];
  processing_time_ms: number;
}

// M010: SBOM Generator Types
export interface SBOMReport {
  format: 'spdx' | 'cyclonedx';
  version: string;
  components: SBOMComponent[];
  vulnerabilities: Vulnerability[];
  licenses: License[];
  generated_at: string;
  signature?: string;
}

export interface SBOMComponent {
  name: string;
  version: string;
  type: 'library' | 'framework' | 'application' | 'container';
  supplier?: string;
  download_location?: string;
  homepage?: string;
  licenses: string[];
}

export interface Vulnerability {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  description: string;
  affected_components: string[];
  cve_id?: string;
  cvss_score?: number;
}

export interface License {
  id: string;
  name: string;
  text?: string;
  url?: string;
  is_osi_approved: boolean;
  risk_level: 'high' | 'medium' | 'low';
}

// M011: Batch Operations Types
export interface BatchJob {
  id: string;
  operation_type: 'generate' | 'enhance' | 'review' | 'analyze';
  total_items: number;
  completed_items: number;
  failed_items: number;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

export interface BatchOperationRequest {
  operation_type: string;
  items: Array<Record<string, any>>;
  options?: Record<string, any>;
  priority?: 'low' | 'normal' | 'high';
}

// M012: Version Control Types
export interface VersionControlInfo {
  repository_path: string;
  current_branch: string;
  is_git_repo: boolean;
  uncommitted_changes: number;
  last_commit: {
    hash: string;
    message: string;
    author: string;
    timestamp: string;
  };
}

export interface CommitInfo {
  hash: string;
  message: string;
  author: string;
  timestamp: string;
  files_changed: string[];
  impact_score?: number;
}

// M013: Template Marketplace Types
export interface MarketplaceTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  author: string;
  version: string;
  downloads: number;
  rating: number;
  price: number;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  preview_url?: string;
  documentation_url?: string;
}

export interface TemplateInstallation {
  template_id: string;
  installed_version: string;
  installation_date: string;
  status: 'active' | 'disabled' | 'needs_update';
  local_modifications: boolean;
}

// Common Types
export interface PaginationParams {
  page: number;
  limit: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

// Health Score and Status Types
export interface HealthScore {
  value: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  status: 'excellent' | 'good' | 'needs_improvement' | 'poor' | 'critical';
  components: {
    quality: number;
    consistency: number;
    completeness: number;
  };
}

export interface SystemStatus {
  overall_health: HealthScore;
  services: {
    [key: string]: {
      status: 'healthy' | 'degraded' | 'down';
      response_time_ms: number;
      last_check: string;
    };
  };
  resource_usage: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent: number;
  };
}