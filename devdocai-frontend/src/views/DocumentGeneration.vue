<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Generate Documentation</h1>
      <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">Create AI-powered documentation for your project</p>
    </div>

    <!-- Main Content Area -->
    <div class="space-y-6">
      <!-- Generation Form (shown when not generating and no result) -->
      <div v-if="!isGenerating && !generatedDocument" class="bg-white dark:bg-gray-800 shadow rounded-lg">
        <div class="px-4 py-5 sm:p-6">
          <ReadmeForm
            @submit="handleGenerate"
            :disabled="isGenerating"
          />
        </div>
      </div>

      <!-- Loading State (shown during generation) -->
      <div v-if="isGenerating" class="space-y-6">
        <!-- Main Loading Card -->
        <div class="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div class="px-4 py-5 sm:p-6">
            <LoadingSpinner
              :message="getStatusMessage()"
              :sub-message="getSubStatusMessage()"
              :show-progress="true"
              :show-timer="true"
            />

            <!-- Status Updates -->
            <div v-if="statusMessages.length > 0" class="mt-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
              <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Status Updates</h3>
              <div class="space-y-1 max-h-32 overflow-y-auto">
                <div
                  v-for="(message, index) in statusMessages"
                  :key="index"
                  class="text-xs text-gray-600 dark:text-gray-400 flex items-start"
                >
                  <span class="text-blue-500 mr-2">→</span>
                  <span>{{ message }}</span>
                </div>
              </div>
            </div>

            <!-- Cancel Button -->
            <div class="mt-6 flex justify-center">
              <button
                @click="cancelGeneration"
                class="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
              >
                Cancel Generation
              </button>
            </div>
          </div>
        </div>

        <!-- Progress Tracker (optional enhanced view) -->
        <GenerationProgress
          :current-status="generationStatus"
          :progress="generationProgress"
        />

        <!-- Document Skeleton Preview -->
        <DocumentSkeleton />
      </div>

      <!-- Result Display (shown when document is generated) -->
      <div v-if="!isGenerating && generatedDocument">
        <DocumentView
          :content="generatedDocument.content"
          :metadata="generatedDocument.metadata"
          @reset="resetGeneration"
        />
      </div>

      <!-- Error State -->
      <div v-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800 dark:text-red-200">Generation Failed</h3>
            <div class="mt-2 text-sm text-red-700 dark:text-red-300">
              <p>{{ error }}</p>
            </div>
            <div class="mt-4">
              <button
                @click="resetGeneration"
                class="text-sm font-medium text-red-600 hover:text-red-500 dark:text-red-400 dark:hover:text-red-300"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { useDocumentStore } from '@/stores/document'
import { useNotificationStore } from '@/stores/notification'
import ReadmeForm from '@/components/ReadmeForm.vue'
import DocumentView from '@/components/DocumentView.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import GenerationProgress from '@/components/GenerationProgress.vue'
import DocumentSkeleton from '@/components/DocumentSkeleton.vue'

// Stores
const documentStore = useDocumentStore()
const notificationStore = useNotificationStore()

// State
const isGenerating = ref(false)
const generatedDocument = ref(null)
const error = ref(null)
const generationProgress = ref(0)
const generationStatus = ref(null)
const statusMessages = ref([])
let statusInterval = null

// Computed
const getStatusMessage = () => {
  const messages = {
    'initializing': 'Initializing AI models...',
    'analyzing': 'Analyzing project structure...',
    'generating': 'Generating documentation content...',
    'enhancing': 'Enhancing with AI insights...',
    'formatting': 'Formatting and structuring...',
    'finalizing': 'Finalizing document...',
    'complete': 'Generation complete!'
  }
  return messages[generationStatus.value] || 'Processing your request...'
}

const getSubStatusMessage = () => {
  const messages = {
    'initializing': 'Setting up the generation pipeline',
    'analyzing': 'Understanding your project requirements',
    'generating': 'This may take 30-60 seconds',
    'enhancing': 'Adding AI-powered improvements',
    'formatting': 'Applying best practices',
    'finalizing': 'Almost done...',
    'complete': 'Your document is ready!'
  }
  return messages[generationStatus.value] || 'Please wait while we work our magic'
}

// Watch for store changes
watch(() => documentStore.generationProgress, (newValue) => {
  generationProgress.value = newValue
})

watch(() => documentStore.generationStatus, (newValue) => {
  if (newValue && newValue !== generationStatus.value) {
    generationStatus.value = newValue
    addStatusMessage(`Status: ${getStatusMessage()}`)
  }
})

// Methods
const handleGenerate = async (formData) => {
  isGenerating.value = true
  error.value = null
  generatedDocument.value = null
  statusMessages.value = []
  generationProgress.value = 0
  generationStatus.value = 'initializing'

  // Add initial status message
  addStatusMessage('Starting document generation...')

  // Simulate progress updates during generation
  startProgressSimulation()

  try {
    const response = await documentStore.generateDocument('readme', formData)

    // Store the generated document
    generatedDocument.value = {
      content: response.document.content,
      metadata: {
        generation_time: response.document.generation_time || 47,
        model_used: response.document.model_used || 'GPT-4',
        cached: response.document.cached || false,
        cost: response.document.cost || 0.047,
        project_name: formData.project_name
      }
    }

    // Success notification
    notificationStore.addSuccess(
      'Document Generated Successfully',
      'Your README has been created and is ready for use!'
    )

    addStatusMessage('Generation completed successfully!')

  } catch (err) {
    error.value = err.message || 'An unexpected error occurred during generation'
    notificationStore.addError(
      'Generation Failed',
      error.value
    )
    addStatusMessage(`Error: ${error.value}`)
  } finally {
    isGenerating.value = false
    stopProgressSimulation()
    generationProgress.value = 100
    setTimeout(() => {
      generationProgress.value = 0
      generationStatus.value = null
    }, 1000)
  }
}

const cancelGeneration = () => {
  // TODO: Implement actual cancellation logic when backend supports it
  isGenerating.value = false
  stopProgressSimulation()
  generationProgress.value = 0
  generationStatus.value = null
  statusMessages.value = []
  notificationStore.addInfo('Generation Cancelled', 'Document generation has been cancelled')
}

const resetGeneration = () => {
  generatedDocument.value = null
  error.value = null
  generationProgress.value = 0
  generationStatus.value = null
  statusMessages.value = []
}

const addStatusMessage = (message) => {
  const timestamp = new Date().toLocaleTimeString()
  statusMessages.value.push(`[${timestamp}] ${message}`)

  // Keep only last 10 messages
  if (statusMessages.value.length > 10) {
    statusMessages.value = statusMessages.value.slice(-10)
  }
}

const startProgressSimulation = () => {
  let progress = 0
  const statusStages = [
    { at: 10, status: 'analyzing' },
    { at: 30, status: 'generating' },
    { at: 60, status: 'enhancing' },
    { at: 80, status: 'formatting' },
    { at: 90, status: 'finalizing' }
  ]

  statusInterval = setInterval(() => {
    if (progress < 90 && isGenerating.value) {
      progress += Math.random() * 3
      progress = Math.min(progress, 90)
      generationProgress.value = Math.floor(progress)

      // Update status based on progress
      const stage = statusStages.find(s => progress >= s.at && generationStatus.value !== s.status)
      if (stage) {
        generationStatus.value = stage.status
      }
    }
  }, 1000)
}

const stopProgressSimulation = () => {
  if (statusInterval) {
    clearInterval(statusInterval)
    statusInterval = null
  }
}

// Cleanup
onUnmounted(() => {
  stopProgressSimulation()
})
</script>
