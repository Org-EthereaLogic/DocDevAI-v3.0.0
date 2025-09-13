<template>
  <div class="max-w-4xl mx-auto">
    <!-- Enhanced Header with Step Progress -->
    <div class="mb-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900 dark:text-white">DevDocAI - Generate New Document</h1>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Need help? Press F1 or click [? Help] at any time
          </p>
        </div>
        <div class="flex items-center space-x-4">
          <span class="text-sm font-medium text-gray-500 dark:text-gray-400">
            Step {{ currentStep }} of {{ totalSteps }}
          </span>
          <button
            @click="showHelp"
            class="px-3 py-2 text-sm font-medium text-indigo-600 hover:text-indigo-800 dark:text-indigo-400 dark:hover:text-indigo-200 transition-colors"
          >
            ? Help
          </button>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="mt-4">
        <div class="bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            class="bg-indigo-600 h-2 rounded-full transition-all duration-300 ease-out"
            :style="{ width: `${(currentStep / totalSteps) * 100}%` }"
          ></div>
        </div>
      </div>
    </div>

    <!-- Step 1: Document Type Selection -->
    <div v-if="currentStep === 1" class="space-y-6">
      <div>
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Select Document Type(s) - You can choose multiple!
        </h2>
        <hr class="border-gray-300 dark:border-gray-600 mb-6">
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Planning & Requirements -->
        <div>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            📋 Planning & Requirements
          </h3>
          <div class="space-y-3">
            <label v-for="doc in planningDocs" :key="doc.id" class="group block">
              <div class="flex items-center p-4 border-2 rounded-lg cursor-pointer transition-all duration-200 hover:shadow-md"
                   :class="selectedDocuments.includes(doc.id)
                     ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                     : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'">
                <input
                  type="checkbox"
                  :value="doc.id"
                  v-model="selectedDocuments"
                  class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                >
                <div class="ml-3 flex-1">
                  <span class="text-sm font-medium text-gray-900 dark:text-white">{{ doc.name }}</span>
                  <button
                    v-if="doc.tooltip"
                    @click.prevent="showTooltip(doc.tooltip)"
                    class="ml-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                  >
                    ⓘ
                  </button>
                </div>
              </div>
            </label>
          </div>
        </div>

        <!-- Design & Architecture -->
        <div>
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-4">
            📐 Design & Architecture
          </h3>
          <div class="space-y-3">
            <label v-for="doc in designDocs" :key="doc.id" class="group block">
              <div class="flex items-center p-4 border-2 rounded-lg cursor-pointer transition-all duration-200 hover:shadow-md"
                   :class="selectedDocuments.includes(doc.id)
                     ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                     : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'">
                <input
                  type="checkbox"
                  :value="doc.id"
                  v-model="selectedDocuments"
                  class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                >
                <div class="ml-3 flex-1">
                  <span class="text-sm font-medium text-gray-900 dark:text-white">{{ doc.name }}</span>
                  <button
                    v-if="doc.tooltip"
                    @click.prevent="showTooltip(doc.tooltip)"
                    class="ml-2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                  >
                    ⓘ
                  </button>
                </div>
              </div>
            </label>
          </div>
        </div>
      </div>

      <!-- Document Type Explanation -->
      <div v-if="showDocumentTypeHelp" class="p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
        <h3 class="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
          ⓘ What's the difference between SRS and PRD?
        </h3>
        <ul class="text-sm text-blue-700 dark:text-blue-300 space-y-1">
          <li>• <strong>PRD:</strong> Business requirements (what to build and why)</li>
          <li>• <strong>SRS:</strong> Technical requirements (how to build it)</li>
        </ul>
      </div>

      <!-- Current Selection Summary -->
      <div v-if="selectedDocuments.length > 0" class="p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
        <h3 class="text-sm font-medium text-green-800 dark:text-green-200 mb-2">
          Selected Documents ({{ selectedDocuments.length }})
        </h3>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="docId in selectedDocuments"
            :key="docId"
            class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
          >
            {{ getDocumentName(docId) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Step 2: Generation Options -->
    <div v-if="currentStep === 2" class="space-y-6">
      <div>
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Generation Options
        </h2>
        <hr class="border-gray-300 dark:border-gray-600 mb-6">
      </div>

      <div class="space-y-6">
        <!-- AI Enhancement -->
        <div class="p-6 border border-gray-300 dark:border-gray-600 rounded-lg">
          <label class="flex items-start space-x-3">
            <input
              type="checkbox"
              v-model="generationOptions.useAI"
              class="h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-0.5"
            >
            <div class="flex-1">
              <span class="text-base font-medium text-gray-900 dark:text-white">Use AI Enhancement</span>
              <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                ⓘ Uses MIAIR to improve quality by 60-75%
              </p>
            </div>
          </label>
        </div>

        <!-- Tracking Matrix -->
        <div class="p-6 border border-gray-300 dark:border-gray-600 rounded-lg">
          <label class="flex items-start space-x-3">
            <input
              type="checkbox"
              v-model="generationOptions.addToMatrix"
              class="h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-0.5"
            >
            <div class="flex-1">
              <span class="text-base font-medium text-gray-900 dark:text-white">Add to Tracking Matrix</span>
              <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                ⓘ Automatically tracks relationships & versions
              </p>
            </div>
          </label>
        </div>

        <!-- Complete Suite -->
        <div class="p-6 border border-gray-300 dark:border-gray-600 rounded-lg">
          <label class="flex items-start space-x-3">
            <input
              type="checkbox"
              v-model="generationOptions.generateSuite"
              class="h-5 w-5 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded mt-0.5"
            >
            <div class="flex-1">
              <span class="text-base font-medium text-gray-900 dark:text-white">Generate Complete Suite</span>
              <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                ⓘ Creates all related documents at once
              </p>
            </div>
          </label>
        </div>

        <!-- AI Model Selection -->
        <div v-if="generationOptions.useAI" class="p-6 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-800">
          <h3 class="text-base font-medium text-gray-900 dark:text-white mb-4">
            AI Model Selection (when AI Enhancement is enabled):
          </h3>

          <div class="space-y-3">
            <label class="flex items-start space-x-3">
              <input
                type="radio"
                value="local"
                v-model="generationOptions.aiModel"
                class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 mt-0.5"
              >
              <div class="flex-1">
                <span class="text-sm font-medium text-gray-900 dark:text-white">Local Models (Privacy-first, no internet needed)</span>
              </div>
            </label>

            <label class="flex items-start space-x-3">
              <input
                type="radio"
                value="cloud"
                v-model="generationOptions.aiModel"
                class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 mt-0.5"
              >
              <div class="flex-1">
                <span class="text-sm font-medium text-gray-900 dark:text-white">Cloud Models (Better quality, requires API keys)</span>
                <p class="text-xs text-gray-600 dark:text-gray-400 mt-1 ml-2">
                  └─ Claude (40%) + ChatGPT (35%) + Gemini (25%)
                </p>
              </div>
            </label>
          </div>

          <!-- Cost Estimation -->
          <div v-if="generationOptions.aiModel === 'cloud'" class="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded">
            <div class="flex items-center space-x-2">
              <svg class="h-5 w-5 text-yellow-600" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              <span class="text-sm font-medium text-yellow-800 dark:text-yellow-200">Cost Estimate</span>
            </div>
            <p class="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
              Estimated cost: ~${{ calculateCost() }} per document
            </p>
          </div>
        </div>
      </div>

      <!-- Time Estimation -->
      <div class="p-4 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
        <p class="text-sm text-gray-700 dark:text-gray-300">
          <span class="font-medium">Estimated time:</span> ~{{ getEstimatedTime() }}
        </p>
      </div>
    </div>

    <!-- Step 3: Project Details -->
    <div v-if="currentStep === 3" class="space-y-6">
      <div>
        <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          Project Details
        </h2>
        <hr class="border-gray-300 dark:border-gray-600 mb-6">
      </div>

      <!-- Use existing form component but simplified -->
      <ReadmeForm
        v-if="showProjectForm"
        @submit="handleProjectSubmit"
        :disabled="false"
        ref="projectForm"
      />
    </div>

    <!-- Navigation Buttons -->
    <div class="mt-8 flex justify-between">
      <button
        v-if="currentStep > 1"
        @click="previousStep"
        class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
      >
        ← Back
      </button>
      <div v-else></div>

      <div class="flex space-x-3">
        <button
          @click="skipWizard"
          class="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
        >
          Skip Wizard
        </button>

        <button
          v-if="currentStep < totalSteps"
          @click="nextStep"
          :disabled="!canProceed"
          class="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Next: {{ getNextStepLabel() }} →
        </button>

        <button
          v-else
          @click="startGeneration"
          :disabled="!canProceed"
          class="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          Start Generation
        </button>
      </div>
    </div>

    <!-- Tooltip Modal -->
    <div v-if="currentTooltip" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click="closeTooltip">
      <div class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md mx-4" @click.stop>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-3">Information</h3>
        <p class="text-sm text-gray-700 dark:text-gray-300 mb-4">{{ currentTooltip }}</p>
        <button
          @click="closeTooltip"
          class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          Got it
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import ReadmeForm from './ReadmeForm.vue'

const emit = defineEmits(['submit', 'cancel'])

// Wizard state
const currentStep = ref(1)
const totalSteps = ref(3)
const currentTooltip = ref(null)
const showDocumentTypeHelp = ref(true)
const showProjectForm = ref(false)

// Form data
const selectedDocuments = ref(['srs']) // Default selection from mockup
const generationOptions = ref({
  useAI: true,
  addToMatrix: true,
  generateSuite: false,
  aiModel: 'local'
})
const projectForm = ref(null)
const projectData = ref(null)

// Document types from mockup
const planningDocs = ref([
  { id: 'project-plan', name: 'Project Plan', tooltip: 'Comprehensive project planning document with timelines and milestones' },
  { id: 'wbs', name: 'Work Breakdown (WBS)', tooltip: 'Hierarchical breakdown of project tasks and deliverables' },
  { id: 'srs', name: 'Software Requirements (SRS)', tooltip: 'Technical requirements specification document' },
  { id: 'prd', name: 'Product Requirements (PRD)', tooltip: 'Business requirements and product definition document' },
  { id: 'user-stories', name: 'User Stories', tooltip: 'User-centered requirement specifications' }
])

const designDocs = ref([
  { id: 'sdd', name: 'Software Design Doc', tooltip: 'Technical design and architecture specification' },
  { id: 'architecture', name: 'Architecture Blueprint', tooltip: 'System architecture and component design' },
  { id: 'api-spec', name: 'API Specifications', tooltip: 'REST API endpoint documentation and contracts' },
  { id: 'database', name: 'Database Schema', tooltip: 'Database design and entity relationships' },
  { id: 'uml', name: 'UML Diagrams', tooltip: 'Unified Modeling Language diagrams' },
  { id: 'mockups', name: 'Mockups/Wireframes', tooltip: 'User interface design specifications' }
])

// Computed properties
const canProceed = computed(() => {
  switch (currentStep.value) {
    case 1:
      return selectedDocuments.value.length > 0
    case 2:
      return true // All options are optional
    case 3:
      return projectData.value !== null
    default:
      return false
  }
})

// Methods
const nextStep = () => {
  if (currentStep.value === 2) {
    showProjectForm.value = true
  }
  if (currentStep.value < totalSteps.value && canProceed.value) {
    currentStep.value++
  }
}

const previousStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

const skipWizard = () => {
  emit('cancel')
}

const showHelp = () => {
  // Show help or tutorial
  console.log('Show help/tutorial')
}

const showTooltip = (message) => {
  currentTooltip.value = message
}

const closeTooltip = () => {
  currentTooltip.value = null
}

const getDocumentName = (docId) => {
  const allDocs = [...planningDocs.value, ...designDocs.value]
  const doc = allDocs.find(d => d.id === docId)
  return doc ? doc.name : docId
}

const getNextStepLabel = () => {
  const labels = {
    1: 'Configure Templates',
    2: 'Project Details'
  }
  return labels[currentStep.value] || 'Next'
}

const calculateCost = () => {
  const baseCost = 0.02 // Base cost per document
  const documentCount = selectedDocuments.value.length
  const suiteCost = generationOptions.value.generateSuite ? 0.01 * documentCount : 0
  return (baseCost * documentCount + suiteCost).toFixed(3)
}

const getEstimatedTime = () => {
  const baseTime = 30 // 30 seconds base
  const documentCount = selectedDocuments.value.length
  const totalTime = baseTime * documentCount

  if (totalTime < 60) {
    return `${totalTime} seconds`
  } else {
    const minutes = Math.ceil(totalTime / 60)
    return `${minutes} minute${minutes > 1 ? 's' : ''}`
  }
}

const handleProjectSubmit = (formData) => {
  projectData.value = formData
  // Auto-proceed or stay for review
}

const startGeneration = () => {
  if (!projectData.value) {
    // Try to get data from form
    if (projectForm.value) {
      // Form should validate and emit submit
      return
    }
  }

  const wizardData = {
    selectedDocuments: selectedDocuments.value,
    generationOptions: generationOptions.value,
    projectData: projectData.value
  }

  emit('submit', wizardData)
}

// Watch for project form completion
watch(() => currentStep.value, (newStep) => {
  if (newStep === 3) {
    showProjectForm.value = true
  }
})
</script>

<style scoped>
/* Smooth step transitions */
.step-enter-active, .step-leave-active {
  transition: all 0.3s ease-out;
}

.step-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.step-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* Progress bar animation */
.bg-indigo-600 {
  transition: width 0.3s ease-out;
}

/* Hover animations */
.hover\:shadow-md:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

/* Focus states for accessibility */
input:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .dark\:bg-gray-800 {
    background-color: #1f2937;
  }
}
</style>