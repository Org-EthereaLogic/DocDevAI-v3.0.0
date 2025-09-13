import axios from 'axios'

// Create axios instance with base configuration
const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 120000, // 2 minutes to accommodate real AI generation (typically 45-60 seconds)
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for adding auth tokens, logging, etc.
api.interceptors.request.use(
  (config) => {
    // Add any authentication tokens here when implemented
    // Add request logging in development
    if (import.meta.env.DEV) {
      console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`)
    }
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    // Log successful responses in development
    if (import.meta.env.DEV) {
      console.log(`✅ API Response: ${response.status} ${response.config.url}`)
    }
    return response
  },
  (error) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Handle authentication errors
      console.error('Authentication required')
    } else if (error.response?.status === 403) {
      // Handle authorization errors
      console.error('Access forbidden')
    } else if (error.response?.status >= 500) {
      // Handle server errors
      console.error('Server error occurred')
    }

    // Enhance error messages for better UX
    if (error.code === 'ECONNABORTED') {
      const timeoutError = new Error('Request timed out. AI document generation can take up to 2 minutes. Please try again.')
      timeoutError.name = 'TimeoutError'
      console.error('API Timeout Error:', timeoutError.message)
      return Promise.reject(timeoutError)
    }

    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export default api

// Document generation request types
export interface DocumentGenerationRequest {
  project_name: string
  description: string
  author: string
  version?: string
  license?: string
  include_badges?: boolean
  include_toc?: boolean
  include_installation?: boolean
  include_usage?: boolean
  include_api?: boolean
  include_contributing?: boolean
  include_license?: boolean
  technologies?: string[]
  features?: string[]
  requirements?: string[]
}

export interface DocumentGenerationResponse {
  success: boolean
  // Backend returns content directly, not nested in data
  content?: string
  document_type?: string
  metadata?: {
    generated_at?: string
    generation_time?: number
    model_used?: string
    cached?: boolean
    project_name?: string
    type?: string
    quality_score?: number
    tokens_used?: number
    cost?: number
  }
  generated_at?: string
  // Legacy support for nested structure
  data?: {
    content: string
    metadata: {
      generated_at: string
      type: string
      quality_score?: number
      tokens_used?: number
      cost?: number
    }
  }
  error?: string | null
  details?: Array<{
    field: string
    message: string
    type: string
  }>
}

// API service functions
export const apiService = {
  // Health check
  async checkHealth() {
    const response = await api.get('/api/v1/health')
    return response.data
  },

  // System status
  async getSystemStatus() {
    const response = await api.get('/api/v1/system/status')
    return response.data
  },

  // Document generation endpoints
  async generateReadme(data: DocumentGenerationRequest): Promise<DocumentGenerationResponse> {
    const response = await api.post('/api/v1/documents/readme', data)
    return response.data
  },

  async generateApiDoc(data: DocumentGenerationRequest): Promise<DocumentGenerationResponse> {
    const response = await api.post('/api/v1/documents/api_doc', data)
    return response.data
  },

  async generateChangelog(data: DocumentGenerationRequest): Promise<DocumentGenerationResponse> {
    const response = await api.post('/api/v1/documents/changelog', data)
    return response.data
  },

  // Configuration endpoints
  async getConfig() {
    const response = await api.get('/api/v1/config')
    return response.data
  },

  async updateConfig(config: any) {
    const response = await api.put('/api/v1/config', config)
    return response.data
  },

  // Template marketplace endpoints
  async getTemplates() {
    const response = await api.get('/api/v1/templates')
    return response.data
  },

  async getTemplate(id: string) {
    const response = await api.get(`/api/v1/templates/${id}`)
    return response.data
  },

  // Tracking matrix endpoints
  async getTrackingMatrix() {
    const response = await api.get('/api/v1/tracking/matrix')
    return response.data
  },

  async analyzeImpact(document_id: string) {
    const response = await api.post('/api/v1/tracking/impact', { document_id })
    return response.data
  }
}
