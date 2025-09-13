import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiService, type DocumentGenerationRequest, type DocumentGenerationResponse } from '@/services/api'
import type { DocumentType } from '@/types'

export interface GeneratedDocument {
  id: string
  type: DocumentType
  content: string
  metadata: {
    generated_at: string
    quality_score?: number
    tokens_used?: number
    cost?: number
  }
  request: DocumentGenerationRequest
}

export const useDocumentStore = defineStore('documents', () => {
  // State
  const documents = ref<GeneratedDocument[]>([])
  const isGenerating = ref(false)
  const generationError = ref<string | null>(null)
  const currentGeneration = ref<GeneratedDocument | null>(null)
  const generationProgress = ref<{
    phase: string
    description: string
    startTime: number
    elapsedTime: number
  } | null>(null)

  // Computed
  const hasDocuments = computed(() => documents.value.length > 0)
  const totalCost = computed(() =>
    documents.value.reduce((sum, doc) => sum + (doc.metadata.cost || 0), 0)
  )
  const averageQualityScore = computed(() => {
    const scores = documents.value
      .map(doc => doc.metadata.quality_score)
      .filter(score => score !== undefined) as number[]

    return scores.length > 0
      ? scores.reduce((sum, score) => sum + score, 0) / scores.length
      : 0
  })

  // Actions
  function setGenerationProgress(phase: string, description: string, startTime?: number) {
    generationProgress.value = {
      phase,
      description,
      startTime: startTime || Date.now(),
      elapsedTime: 0
    }
  }

  function updateGenerationProgress() {
    if (generationProgress.value) {
      generationProgress.value.elapsedTime = Date.now() - generationProgress.value.startTime
    }
  }

  async function generateDocument(type: DocumentType, request: DocumentGenerationRequest) {
    const startTime = Date.now()
    isGenerating.value = true
    generationError.value = null
    currentGeneration.value = null

    // Set initial progress
    setGenerationProgress('initializing', 'Preparing your request...', startTime)

    // Update progress every second
    const progressInterval = setInterval(updateGenerationProgress, 1000)

    try {
      // Update progress to analysis phase
      setTimeout(() => {
        if (isGenerating.value) {
          setGenerationProgress('analyzing', 'Analyzing your project requirements...', startTime)
        }
      }, 1000)

      // Update progress to generation phase
      setTimeout(() => {
        if (isGenerating.value) {
          setGenerationProgress('generating', 'Generating document content with AI...', startTime)
        }
      }, 8000)

      // Update progress to finalization phase
      setTimeout(() => {
        if (isGenerating.value) {
          setGenerationProgress('finalizing', 'Finalizing and formatting document...', startTime)
        }
      }, 35000)
      let response: DocumentGenerationResponse

      switch (type) {
        case 'readme':
          response = await apiService.generateReadme(request)
          break
        case 'api_doc':
          response = await apiService.generateApiDoc(request)
          break
        case 'changelog':
          response = await apiService.generateChangelog(request)
          break
        default:
          throw new Error(`Unsupported document type: ${type}`)
      }

      // Handle both response structures (backend returns content directly, not nested in data)
      if (response.success && (response.content || response.data?.content)) {
        const document: GeneratedDocument = {
          id: crypto.randomUUID(),
          type,
          content: response.content || response.data.content,
          metadata: response.metadata || response.data?.metadata || {
            generated_at: response.generated_at || new Date().toISOString(),
            type: response.document_type || type
          },
          request
        }

        documents.value.unshift(document) // Add to beginning
        currentGeneration.value = document

        // Set completion progress
        setGenerationProgress('completed', 'Document generated successfully!', startTime)
        setTimeout(() => {
          generationProgress.value = null
        }, 2000)

        return document
      } else {
        const errorMessage = response.error || 'Unknown error occurred'
        const validationErrors = response.details?.map(d => d.message).join(', ')
        generationError.value = validationErrors ? `${errorMessage}: ${validationErrors}` : errorMessage
        throw new Error(generationError.value)
      }
    } catch (error) {
      let errorMessage = 'Failed to generate document'

      if (error instanceof Error) {
        if (error.name === 'TimeoutError') {
          errorMessage = 'Generation timed out. AI document generation typically takes 45-60 seconds. Please try again and ensure stable internet connection.'
        } else if (error.message.includes('Network Error')) {
          errorMessage = 'Network error. Please check your connection and try again.'
        } else if (error.message.includes('timeout')) {
          errorMessage = 'Request timed out. AI generation can take up to 2 minutes. Please try again.'
        } else {
          errorMessage = error.message
        }
      }

      generationError.value = errorMessage
      throw error
    } finally {
      clearInterval(progressInterval)
      isGenerating.value = false

      // Clear progress after a delay if there was an error
      if (generationError.value) {
        setTimeout(() => {
          generationProgress.value = null
        }, 3000)
      }
    }
  }

  function clearError() {
    generationError.value = null
    generationProgress.value = null
  }

  function deleteDocument(id: string) {
    const index = documents.value.findIndex(doc => doc.id === id)
    if (index !== -1) {
      documents.value.splice(index, 1)
    }
  }

  function clearAllDocuments() {
    documents.value = []
    currentGeneration.value = null
  }

  function getDocumentsByType(type: DocumentType) {
    return documents.value.filter(doc => doc.type === type)
  }

  return {
    // State
    documents,
    isGenerating,
    generationError,
    currentGeneration,
    generationProgress,

    // Computed
    hasDocuments,
    totalCost,
    averageQualityScore,

    // Actions
    generateDocument,
    clearError,
    deleteDocument,
    clearAllDocuments,
    getDocumentsByType
  }
}, {
  persist: {
    key: 'devdocai-documents',
    storage: localStorage,
    paths: ['documents'] // Only persist documents, not loading/error states
  }
})
