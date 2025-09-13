<template>
  <div v-if="show" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" @click.self="handleBackdropClick">
    <div class="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
      <!-- Modal Header -->
      <div class="flex items-center justify-between mb-6">
        <h3 class="text-lg font-bold text-gray-900">Generate New Document</h3>
        <button @click="handleClose" class="text-gray-400 hover:text-gray-600" :disabled="documentStore.isGenerating">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- Generation Progress -->
      <div v-if="documentStore.isGenerating && documentStore.generationProgress" class="mb-6">
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <!-- Progress Header -->
          <div class="flex items-center justify-between mb-3">
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <svg class="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <h3 class="ml-2 text-sm font-medium text-blue-800">Generating Document</h3>
            </div>
            <div class="text-sm text-blue-600 font-mono">
              {{ formatElapsedTime(documentStore.generationProgress.elapsedTime) }}
            </div>
          </div>

          <!-- Progress Description -->
          <div class="mb-3">
            <p class="text-sm text-blue-700">{{ documentStore.generationProgress.description }}</p>
            <p class="text-xs text-blue-600 mt-1">AI generation typically takes 45-60 seconds</p>
          </div>

          <!-- Progress Bar -->
          <div class="w-full bg-blue-200 rounded-full h-2">
            <div
              class="bg-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
              :style="{ width: getProgressWidth() + '%' }"
            ></div>
          </div>

          <!-- Phase Indicator -->
          <div class="flex justify-between text-xs text-blue-600 mt-2">
            <span :class="getPhaseClass('initializing')">Preparing</span>
            <span :class="getPhaseClass('analyzing')">Analyzing</span>
            <span :class="getPhaseClass('generating')">Generating</span>
            <span :class="getPhaseClass('finalizing')">Finalizing</span>
          </div>
        </div>
      </div>

      <!-- Error Display -->
      <div v-if="documentStore.generationError" class="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">Generation Failed</h3>
            <div class="mt-2 text-sm text-red-700">{{ documentStore.generationError }}</div>
            <!-- Retry Button -->
            <div class="mt-3">
              <button
                @click="retryGeneration"
                class="text-sm bg-red-100 hover:bg-red-200 text-red-800 font-medium py-1 px-3 rounded transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Form -->
      <form @submit.prevent="handleSubmit" class="space-y-6">
        <!-- Document Type Selection -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">Document Type</label>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            <button
              v-for="type in documentTypes"
              :key="type.value"
              type="button"
              @click="formData.type = type.value"
              :class="[
                'p-4 border rounded-lg text-left transition-colors',
                formData.type === type.value
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-300 hover:border-gray-400'
              ]"
            >
              <div class="font-medium">{{ type.label }}</div>
              <div class="text-sm text-gray-500 mt-1">{{ type.description }}</div>
            </button>
          </div>
        </div>

        <!-- Project Information -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="project_name" class="block text-sm font-medium text-gray-700 mb-1">
              Project Name *
            </label>
            <input
              id="project_name"
              v-model="formData.project_name"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="my-awesome-project"
            />
          </div>

          <div>
            <label for="author" class="block text-sm font-medium text-gray-700 mb-1">
              Author *
            </label>
            <input
              id="author"
              v-model="formData.author"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Your Name"
            />
          </div>
        </div>

        <div>
          <label for="description" class="block text-sm font-medium text-gray-700 mb-1">
            Description *
          </label>
          <textarea
            id="description"
            v-model="formData.description"
            rows="3"
            required
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="A brief description of what your project does..."
          ></textarea>
        </div>

        <!-- Optional Fields -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="version" class="block text-sm font-medium text-gray-700 mb-1">Version</label>
            <input
              id="version"
              v-model="formData.version"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="1.0.0"
            />
          </div>

          <div>
            <label for="license" class="block text-sm font-medium text-gray-700 mb-1">License</label>
            <select
              id="license"
              v-model="formData.license"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">Select a license</option>
              <option value="MIT">MIT</option>
              <option value="Apache-2.0">Apache 2.0</option>
              <option value="GPL-3.0">GPL 3.0</option>
              <option value="BSD-3-Clause">BSD 3-Clause</option>
              <option value="ISC">ISC</option>
            </select>
          </div>
        </div>

        <!-- Technologies and Features -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="technologies" class="block text-sm font-medium text-gray-700 mb-1">
              Technologies
            </label>
            <input
              id="technologies"
              v-model="technologiesInput"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="JavaScript, React, Node.js (comma-separated)"
            />
          </div>

          <div>
            <label for="features" class="block text-sm font-medium text-gray-700 mb-1">
              Key Features
            </label>
            <input
              id="features"
              v-model="featuresInput"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Fast, Secure, User-friendly (comma-separated)"
            />
          </div>
        </div>

        <!-- Checkboxes for README options -->
        <div v-if="formData.type === 'readme'" class="space-y-3">
          <label class="block text-sm font-medium text-gray-700">Include Sections</label>
          <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
            <label v-for="option in readmeOptions" :key="option.key" class="flex items-center">
              <input
                v-model="formData[option.key]"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">{{ option.label }}</span>
            </label>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex justify-end space-x-3 pt-4 border-t">
          <button
            type="button"
            @click="handleCancel"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
            :disabled="documentStore.isGenerating"
          >
            {{ documentStore.isGenerating ? 'Please Wait...' : 'Cancel' }}
          </button>
          <button
            type="submit"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="documentStore.isGenerating || !isFormValid"
          >
            <span v-if="documentStore.isGenerating" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Generating...
            </span>
            <span v-else>Generate Document</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useDocumentStore } from '@/stores/documents'
import type { DocumentType } from '@/types'
import type { DocumentGenerationRequest } from '@/services/api'

// Props and emits
defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  close: []
  success: [document: any]
}>()

// Store
const documentStore = useDocumentStore()

// Form data
const formData = ref<DocumentGenerationRequest & { type: DocumentType }>({
  type: 'readme',
  project_name: '',
  description: '',
  author: '',
  version: '1.0.0',
  license: 'MIT',
  include_badges: true,
  include_toc: true,
  include_installation: true,
  include_usage: true,
  include_api: false,
  include_contributing: true,
  include_license: true,
  technologies: [],
  features: [],
  requirements: []
})

// Input helpers for comma-separated arrays
const technologiesInput = ref('')
const featuresInput = ref('')

// Document type options
const documentTypes = [
  {
    value: 'readme' as DocumentType,
    label: 'README',
    description: 'Project overview and documentation'
  },
  {
    value: 'api_doc' as DocumentType,
    label: 'API Documentation',
    description: 'REST API endpoint documentation'
  },
  {
    value: 'changelog' as DocumentType,
    label: 'Changelog',
    description: 'Version history and changes'
  }
]

// README options
const readmeOptions = [
  { key: 'include_badges', label: 'Badges' },
  { key: 'include_toc', label: 'Table of Contents' },
  { key: 'include_installation', label: 'Installation' },
  { key: 'include_usage', label: 'Usage Examples' },
  { key: 'include_api', label: 'API Reference' },
  { key: 'include_contributing', label: 'Contributing Guide' },
  { key: 'include_license', label: 'License Info' }
]

// Computed
const isFormValid = computed(() => {
  return formData.value.project_name.trim() !== '' &&
         formData.value.description.trim().length >= 10 &&
         formData.value.author.trim() !== ''
})

// Watch for comma-separated inputs
watch(technologiesInput, (newValue) => {
  formData.value.technologies = newValue.split(',').map(s => s.trim()).filter(s => s !== '')
})

watch(featuresInput, (newValue) => {
  formData.value.features = newValue.split(',').map(s => s.trim()).filter(s => s !== '')
})

// Clear error when form changes
watch(formData, () => {
  if (documentStore.generationError) {
    documentStore.clearError()
  }
}, { deep: true })

// Actions
async function handleSubmit() {
  if (!isFormValid.value) return

  try {
    const { type, ...requestData } = formData.value
    const document = await documentStore.generateDocument(type, requestData)
    emit('success', document)
    emit('close')

    // Reset form
    resetForm()
  } catch (error) {
    // Error is handled by the store and displayed in the UI
    console.error('Document generation failed:', error)
  }
}

function handleCancel() {
  if (documentStore.isGenerating) {
    // Show warning that generation cannot be cancelled
    return
  }
  documentStore.clearError()
  emit('close')
}

function handleClose() {
  if (documentStore.isGenerating) {
    // Prevent closing during generation
    return
  }
  documentStore.clearError()
  emit('close')
}

function handleBackdropClick() {
  if (documentStore.isGenerating) {
    // Prevent closing during generation
    return
  }
  emit('close')
}

function retryGeneration() {
  documentStore.clearError()
  handleSubmit()
}

function formatElapsedTime(milliseconds: number): string {
  const seconds = Math.floor(milliseconds / 1000)
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60

  if (minutes > 0) {
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }
  return `${seconds}s`
}

function getProgressWidth(): number {
  if (!documentStore.generationProgress) return 0

  const phase = documentStore.generationProgress.phase
  const elapsed = documentStore.generationProgress.elapsedTime / 1000 // Convert to seconds

  // Map phases to progress percentages based on typical timing
  switch (phase) {
    case 'initializing':
      return Math.min(20, (elapsed / 2) * 20) // 0-20% over 2 seconds
    case 'analyzing':
      return Math.min(35, 20 + ((elapsed - 2) / 6) * 15) // 20-35% over 6 seconds
    case 'generating':
      return Math.min(90, 35 + ((elapsed - 8) / 30) * 55) // 35-90% over 30 seconds
    case 'finalizing':
      return Math.min(95, 90 + ((elapsed - 40) / 10) * 5) // 90-95% over 10 seconds
    case 'completed':
      return 100
    default:
      return 0
  }
}

function getPhaseClass(phaseName: string): string {
  if (!documentStore.generationProgress) {
    return 'opacity-50'
  }

  const currentPhase = documentStore.generationProgress.phase
  const phases = ['initializing', 'analyzing', 'generating', 'finalizing', 'completed']
  const currentIndex = phases.indexOf(currentPhase)
  const phaseIndex = phases.indexOf(phaseName)

  if (currentIndex > phaseIndex) {
    return 'font-medium text-blue-700' // Completed phases
  } else if (currentIndex === phaseIndex) {
    return 'font-bold text-blue-800 animate-pulse' // Current phase
  } else {
    return 'opacity-50' // Future phases
  }
}

function resetForm() {
  formData.value = {
    type: 'readme',
    project_name: '',
    description: '',
    author: '',
    version: '1.0.0',
    license: 'MIT',
    include_badges: true,
    include_toc: true,
    include_installation: true,
    include_usage: true,
    include_api: false,
    include_contributing: true,
    include_license: true,
    technologies: [],
    features: [],
    requirements: []
  }
  technologiesInput.value = ''
  featuresInput.value = ''
}
</script>
