/**
 * DevDocAI API Client
 * 
 * TypeScript client for the FastAPI backend bridge
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Types for API requests and responses
export interface GenerateDocumentRequest {
  template: string
  context: Record<string, unknown>
  output_format?: string
}

export interface EnhanceDocumentRequest {
  content: string
  strategy?: string
  target_quality?: number
}

export interface AnalyzeDocumentRequest {
  content: string
  include_suggestions?: boolean
}

export interface DocumentResponse {
  content: string
  metadata: Record<string, unknown>
  quality_score?: number
}

export interface EnhancementResponse {
  enhanced_content: string
  improvements: string[]
  quality_improvement: number
  entropy_reduction: number
}

export interface AnalysisResponse {
  quality_score: number
  entropy_score: number
  suggestions: string[]
  issues_found: number
}

export interface ConfigurationResponse {
  privacy_mode: string
  telemetry_enabled: boolean
  api_provider: string
  memory_mode: string
  available_memory: number
}

// API Client Functions
export async function generateDocument(request: GenerateDocumentRequest): Promise<DocumentResponse> {
  const response = await fetch(`${API_BASE}/api/documents/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })
  
  if (!response.ok) {
    throw new Error(`Generation failed: ${response.statusText}`)
  }
  
  return response.json()
}

export async function enhanceDocument(request: EnhanceDocumentRequest): Promise<EnhancementResponse> {
  const response = await fetch(`${API_BASE}/api/documents/enhance`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })
  
  if (!response.ok) {
    throw new Error(`Enhancement failed: ${response.statusText}`)
  }
  
  return response.json()
}

export async function analyzeDocument(request: AnalyzeDocumentRequest): Promise<AnalysisResponse> {
  const response = await fetch(`${API_BASE}/api/documents/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  })
  
  if (!response.ok) {
    throw new Error(`Analysis failed: ${response.statusText}`)
  }
  
  return response.json()
}

export async function getConfiguration(): Promise<ConfigurationResponse> {
  const response = await fetch(`${API_BASE}/api/config`)
  
  if (!response.ok) {
    throw new Error(`Config fetch failed: ${response.statusText}`)
  }
  
  return response.json()
}

export async function listTemplates(): Promise<{ templates: unknown[] }> {
  const response = await fetch(`${API_BASE}/api/templates/list`)
  
  if (!response.ok) {
    throw new Error(`Template list failed: ${response.statusText}`)
  }
  
  return response.json()
}

export async function getMarketplaceTemplates(): Promise<{ templates: unknown[] }> {
  const response = await fetch(`${API_BASE}/api/marketplace/templates`)
  
  if (!response.ok) {
    throw new Error(`Marketplace fetch failed: ${response.statusText}`)
  }
  
  return response.json()
}

// Health check for API availability
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/`)
    return response.ok
  } catch {
    return false
  }
}