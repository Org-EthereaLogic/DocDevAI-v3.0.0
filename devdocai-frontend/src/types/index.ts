// DevDocAI v3.6.0 TypeScript Type Definitions

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message?: string
  errors?: string[]
}

// Document Types
export interface Document {
  id: string
  title: string
  type: DocumentType
  content: string
  metadata: DocumentMetadata
  created_at: string
  updated_at: string
}

export interface DocumentMetadata {
  author?: string
  version?: string
  tags?: string[]
  template_id?: string
  ai_generated?: boolean
  quality_score?: number
}

export type DocumentType =
  | 'readme'
  | 'api_doc'
  | 'changelog'
  | 'user_guide'
  | 'technical_spec'
  | 'custom'

// Configuration Types
export interface AppConfig {
  privacy_mode: boolean
  ai_providers: AIProviderConfig[]
  storage_settings: StorageSettings
  ui_preferences: UIPreferences
}

export interface AIProviderConfig {
  name: string
  enabled: boolean
  api_key?: string
  usage_limit?: number
  cost_per_request?: number
}

export interface StorageSettings {
  local_only: boolean
  backup_enabled: boolean
  retention_days: number
}

export interface UIPreferences {
  theme: 'light' | 'dark' | 'system'
  language: string
  accessibility_mode: boolean
  motion_reduced: boolean
}

// Template Types
export interface Template {
  id: string
  name: string
  description: string
  category: string
  version: string
  author: string
  verified: boolean
  download_count: number
  rating: number
  created_at: string
}

// Tracking Matrix Types
export interface DependencyNode {
  id: string
  name: string
  type: string
  relationships: Relationship[]
}

export interface Relationship {
  target_id: string
  type: RelationshipType
  strength: number
}

export type RelationshipType =
  | 'depends_on'
  | 'references'
  | 'implements'
  | 'extends'
  | 'includes'
  | 'calls'
  | 'uses'

// Component Props Types
export interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
}

export interface InputProps {
  label?: string
  error?: string
  required?: boolean
  placeholder?: string
}

// Store Types
export interface AppState {
  isLoading: boolean
  error: string | null
  config: AppConfig | null
  documents: Document[]
  templates: Template[]
}

// Navigation Types
export interface NavigationItem {
  name: string
  path: string
  icon?: string
  children?: NavigationItem[]
  requiresAuth?: boolean
}
