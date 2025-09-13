<template>
  <div class="generation-review">
    <!-- Section Header -->
    <div class="mb-6">
      <Heading level="2" size="lg" weight="semibold" color="primary" class="mb-2">
        Review & Generate
      </Heading>
      <Text size="sm" color="muted">
        Review your selections and start the document generation process
      </Text>
    </div>

    <!-- Generation Summary -->
    <div class="summary-section mb-6">
      <div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <Heading level="3" size="md" weight="semibold" class="mb-4">
          Generation Summary
        </Heading>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Documents to Generate -->
          <div class="summary-item">
            <div class="flex items-center space-x-2 mb-3">
              <DocumentDuplicateIcon class="h-5 w-5 text-blue-600 dark:text-blue-400" />
              <Text size="sm" weight="semibold">Documents Selected</Text>
            </div>
            <div class="space-y-2">
              <div
                v-for="docType in formData.documentTypes"
                :key="docType"
                class="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded"
              >
                <Text size="sm">{{ getDocumentName(docType) }}</Text>
                <Text size="xs" color="muted">~{{ estimateTime(docType) }}s</Text>
              </div>
            </div>
            <div v-if="formData.documentTypes.length === 0" class="text-center py-4">
              <Text size="sm" color="muted">No documents selected</Text>
            </div>
          </div>

          <!-- Configuration Summary -->
          <div class="summary-item">
            <div class="flex items-center space-x-2 mb-3">
              <CogIcon class="h-5 w-5 text-green-600 dark:text-green-400" />
              <Text size="sm" weight="semibold">Configuration</Text>
            </div>
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <Text size="sm" color="muted">AI Enhancement</Text>
                <div class="flex items-center space-x-1">
                  <CheckIcon v-if="formData.aiEnhancement" class="h-4 w-4 text-green-600" />
                  <XMarkIcon v-else class="h-4 w-4 text-gray-400" />
                  <Text size="sm" :color="formData.aiEnhancement ? 'success' : 'muted'">
                    {{ formData.aiEnhancement ? 'Enabled' : 'Disabled' }}
                  </Text>
                </div>
              </div>
              <div class="flex items-center justify-between">
                <Text size="sm" color="muted">Tracking Matrix</Text>
                <div class="flex items-center space-x-1">
                  <CheckIcon v-if="formData.addToTracking" class="h-4 w-4 text-green-600" />
                  <XMarkIcon v-else class="h-4 w-4 text-gray-400" />
                  <Text size="sm" :color="formData.addToTracking ? 'success' : 'muted'">
                    {{ formData.addToTracking ? 'Enabled' : 'Disabled' }}
                  </Text>
                </div>
              </div>
              <div class="flex items-center justify-between">
                <Text size="sm" color="muted">AI Model</Text>
                <div class="flex items-center space-x-1">
                  <ShieldCheckIcon v-if="formData.useLocalModels" class="h-4 w-4 text-green-600" />
                  <CloudIcon v-else class="h-4 w-4 text-blue-600" />
                  <Text size="sm">
                    {{ formData.useLocalModels ? 'Local Models' : 'Cloud Models' }}
                  </Text>
                </div>
              </div>
              <div class="flex items-center justify-between">
                <Text size="sm" color="muted">Complete Suite</Text>
                <div class="flex items-center space-x-1">
                  <CheckIcon v-if="formData.generateSuite" class="h-4 w-4 text-green-600" />
                  <XMarkIcon v-else class="h-4 w-4 text-gray-400" />
                  <Text size="sm" :color="formData.generateSuite ? 'success' : 'muted'">
                    {{ formData.generateSuite ? 'Yes' : 'No' }}
                  </Text>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Generation Progress (when generating) -->
    <div v-if="isGenerating" class="progress-section mb-6">
      <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
        <div class="flex items-center space-x-3 mb-4">
          <div class="flex-shrink-0">
            <div class="loading-spinner h-6 w-6 text-blue-600"></div>
          </div>
          <div>
            <Heading level="3" size="md" weight="semibold" class="text-blue-900 dark:text-blue-100">
              Generating Documents...
            </Heading>
            <Text size="sm" class="text-blue-800 dark:text-blue-200 mt-1">
              {{ currentGenerationStep }}
            </Text>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="mb-4">
          <div class="flex items-center justify-between mb-2">
            <Text size="sm" weight="medium" class="text-blue-900 dark:text-blue-100">
              Overall Progress
            </Text>
            <Text size="sm" class="text-blue-800 dark:text-blue-200">
              {{ Math.round(generationProgress) }}%
            </Text>
          </div>
          <div class="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-3">
            <div
              class="bg-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
              :style="{ width: `${generationProgress}%` }"
              role="progressbar"
              :aria-valuenow="generationProgress"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="`Generation progress: ${Math.round(generationProgress)}%`"
            ></div>
          </div>
        </div>

        <!-- Current Document Status -->
        <div class="space-y-2">
          <div
            v-for="(doc, index) in formData.documentTypes"
            :key="doc"
            class="flex items-center space-x-3 p-2 rounded"
            :class="getDocumentStatusClass(index)"
          >
            <component
              :is="getDocumentStatusIcon(index)"
              class="h-4 w-4"
              :class="getDocumentStatusIconClass(index)"
            />
            <Text size="sm" class="flex-1">{{ getDocumentName(doc) }}</Text>
            <Text size="xs" color="muted">{{ getDocumentStatusText(index) }}</Text>
          </div>
        </div>

        <!-- Time Remaining -->
        <div v-if="estimatedTimeRemaining" class="mt-4 text-center">
          <Text size="sm" class="text-blue-800 dark:text-blue-200">
            Estimated time remaining: {{ formatTime(estimatedTimeRemaining) }}
          </Text>
        </div>
      </div>
    </div>

    <!-- Cost Estimate (for cloud models) -->
    <div v-if="!formData.useLocalModels && !isGenerating" class="cost-estimate mb-6">
      <div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
        <div class="flex items-center space-x-2 mb-2">
          <CurrencyDollarIcon class="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
          <Text size="sm" weight="semibold" class="text-yellow-800 dark:text-yellow-200">
            Estimated Cost
          </Text>
        </div>
        <div class="flex items-center justify-between">
          <Text size="sm" class="text-yellow-700 dark:text-yellow-300">
            {{ formData.documentTypes.length }} document{{ formData.documentTypes.length !== 1 ? 's' : '' }}
            × ~$0.016 average per document
          </Text>
          <Text size="lg" weight="bold" class="text-yellow-800 dark:text-yellow-200">
            ~${{ (formData.documentTypes.length * 0.016).toFixed(2) }}
          </Text>
        </div>
      </div>
    </div>

    <!-- Start Generation Button (when not generating) -->
    <div v-if="!isGenerating" class="action-section">
      <div class="text-center">
        <Button
          variant="primary"
          size="lg"
          @click="$emit('start-generation')"
          :disabled="formData.documentTypes.length === 0"
          class="px-8"
        >
          <template #iconLeft>
            <PlayIcon class="h-5 w-5" />
          </template>
          Start Generation
        </Button>
        <Text size="sm" color="muted" class="mt-3">
          You can close this wizard once generation begins
        </Text>
      </div>
    </div>

    <!-- Generation Complete -->
    <div v-if="generationProgress >= 100 && isGenerating" class="completion-section">
      <div class="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6 text-center">
        <CheckCircleIcon class="h-12 w-12 text-green-600 dark:text-green-400 mx-auto mb-4" />
        <Heading level="3" size="lg" weight="semibold" class="text-green-900 dark:text-green-100 mb-2">
          Generation Complete!
        </Heading>
        <Text size="sm" class="text-green-800 dark:text-green-200 mb-4">
          Successfully generated {{ formData.documentTypes.length }} document{{ formData.documentTypes.length !== 1 ? 's' : '' }}
        </Text>
        <div class="flex justify-center space-x-3">
          <Button variant="secondary" size="md" @click="viewDocuments">
            View Documents
          </Button>
          <Button variant="primary" size="md" @click="generateMore">
            Generate More
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  DocumentDuplicateIcon,
  CogIcon,
  CheckIcon,
  XMarkIcon,
  ShieldCheckIcon,
  CloudIcon,
  CurrencyDollarIcon,
  PlayIcon,
  CheckCircleIcon,
  ClockIcon,
  Cog6ToothIcon
} from '@heroicons/vue/24/outline'

// Components
import Heading from '@/components/atoms/Heading.vue'
import Text from '@/components/atoms/Text.vue'
import Button from '@/components/atoms/Button.vue'

// Types
interface FormData {
  documentTypes: string[]
  generateSuite: boolean
  aiEnhancement: boolean
  addToTracking: boolean
  aiModel: 'local' | 'cloud'
  useLocalModels: boolean
}

// Props
interface Props {
  formData: FormData
  isGenerating: boolean
  generationProgress: number
}

const props = defineProps<Props>()

// Emits
const emit = defineEmits<{
  'start-generation': []
}>()

// Router
const router = useRouter()

// Document names mapping
const documentNames: Record<string, string> = {
  'project-plan': 'Project Plan',
  'work-breakdown': 'Work Breakdown Structure',
  'software-requirements': 'Software Requirements Specification',
  'product-requirements': 'Product Requirements Document',
  'user-stories': 'User Stories',
  'software-design': 'Software Design Document',
  'architecture-blueprint': 'Architecture Blueprint',
  'api-specifications': 'API Specifications',
  'database-schema': 'Database Schema',
  'uml-diagrams': 'UML Diagrams',
  'mockups-wireframes': 'Mockups & Wireframes'
}

// Computed properties
const currentGenerationStep = computed(() => {
  if (props.generationProgress < 20) return 'Initializing generation process...'
  if (props.generationProgress < 40) return 'Analyzing project structure...'
  if (props.generationProgress < 60) return 'Generating document content...'
  if (props.generationProgress < 80) return 'Applying AI enhancements...'
  if (props.generationProgress < 95) return 'Finalizing documents...'
  return 'Completing generation...'
})

const estimatedTimeRemaining = computed(() => {
  if (!props.isGenerating || props.generationProgress >= 100) return null

  const totalTime = props.formData.documentTypes.length * 30 // 30 seconds per document
  const remaining = totalTime * (1 - props.generationProgress / 100)
  return Math.max(0, Math.round(remaining))
})

// Methods
const getDocumentName = (docId: string): string => {
  return documentNames[docId] || docId
}

const estimateTime = (docId: string): number => {
  const baseTime = 30
  const multiplier = props.formData.aiEnhancement ? 1.5 : 1
  return Math.round(baseTime * multiplier)
}

const getDocumentStatusClass = (index: number): string => {
  const progressPerDoc = 100 / props.formData.documentTypes.length
  const docProgress = (props.generationProgress - (index * progressPerDoc)) / progressPerDoc * 100

  if (docProgress >= 100) return 'bg-green-50 dark:bg-green-900/20'
  if (docProgress > 0) return 'bg-blue-50 dark:bg-blue-900/20'
  return 'bg-gray-50 dark:bg-gray-700'
}

const getDocumentStatusIcon = (index: number) => {
  const progressPerDoc = 100 / props.formData.documentTypes.length
  const docProgress = (props.generationProgress - (index * progressPerDoc)) / progressPerDoc * 100

  if (docProgress >= 100) return CheckIcon
  if (docProgress > 0) return Cog6ToothIcon
  return ClockIcon
}

const getDocumentStatusIconClass = (index: number): string => {
  const progressPerDoc = 100 / props.formData.documentTypes.length
  const docProgress = (props.generationProgress - (index * progressPerDoc)) / progressPerDoc * 100

  if (docProgress >= 100) return 'text-green-600 dark:text-green-400'
  if (docProgress > 0) return 'text-blue-600 dark:text-blue-400 animate-spin'
  return 'text-gray-400'
}

const getDocumentStatusText = (index: number): string => {
  const progressPerDoc = 100 / props.formData.documentTypes.length
  const docProgress = (props.generationProgress - (index * progressPerDoc)) / progressPerDoc * 100

  if (docProgress >= 100) return 'Complete'
  if (docProgress > 0) return `${Math.round(docProgress)}%`
  return 'Waiting'
}

const formatTime = (seconds: number): string => {
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${minutes}m ${remainingSeconds}s`
}

const viewDocuments = () => {
  router.push('/app/documents')
}

const generateMore = () => {
  // Reset wizard or trigger new generation
  emit('start-generation')
}
</script>

<style scoped>
.loading-spinner {
  @apply animate-spin;
}

.summary-item {
  @apply space-y-2;
}

/* Progress bar animation */
.bg-blue-600 {
  transition: width 0.5s ease-out;
}

/* Document status animations */
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .grid.md\\:grid-cols-2 {
    @apply grid-cols-1 gap-4;
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .loading-spinner,
  .animate-spin {
    @apply animate-none;
  }

  .bg-blue-600 {
    @apply transition-none;
  }
}
</style>