<template>
  <div class="document-generation-wizard">
    <!-- Wizard Header -->
    <div class="wizard-header bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
      <div class="flex items-center justify-between">
        <div>
          <Heading level="1" size="xl" weight="semibold" color="primary">
            Generate New Document
          </Heading>
          <Text size="sm" color="muted" class="mt-1">
            Need help? Press F1 or click Help at any time
          </Text>
        </div>

        <!-- Step indicator -->
        <div class="flex items-center space-x-2 text-sm">
          <Text size="sm" color="muted">Step {{ currentStep }} of {{ totalSteps }}</Text>
          <Button
            variant="ghost"
            size="sm"
            @click="showHelp"
            aria-label="Show help"
          >
            <template #iconLeft>
              <QuestionMarkCircleIcon class="h-4 w-4" />
            </template>
            Help
          </Button>
        </div>
      </div>

      <!-- Progress bar -->
      <div class="mt-4">
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            class="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
            :style="{ width: `${progress}%` }"
            role="progressbar"
            :aria-valuenow="progress"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-label="`Step ${currentStep} of ${totalSteps}, ${progress}% complete`"
          ></div>
        </div>
      </div>
    </div>

    <!-- Wizard Content -->
    <div class="wizard-content flex-1 overflow-y-auto">
      <!-- Step 1: Document Type Selection -->
      <div v-if="currentStep === 1" class="step-content p-6">
        <DocumentTypeSelection
          v-model:selectedTypes="formData.documentTypes"
          v-model:generateSuite="formData.generateSuite"
          @update:selectedTypes="validateStep1"
        />
      </div>

      <!-- Step 2: Configuration Options -->
      <div v-if="currentStep === 2" class="step-content p-6">
        <ConfigurationOptions
          v-model:aiEnhancement="formData.aiEnhancement"
          v-model:addToTracking="formData.addToTracking"
          v-model:aiModel="formData.aiModel"
          v-model:useLocalModels="formData.useLocalModels"
          @update="validateStep2"
        />
      </div>

      <!-- Step 3: Final Review & Generation -->
      <div v-if="currentStep === 3" class="step-content p-6">
        <GenerationReview
          :form-data="formData"
          :is-generating="isGenerating"
          :generation-progress="generationProgress"
          @start-generation="startGeneration"
        />
      </div>
    </div>

    <!-- Wizard Footer -->
    <div class="wizard-footer bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-6 py-4">
      <div class="flex items-center justify-between">
        <!-- Back button -->
        <Button
          v-if="currentStep > 1"
          variant="secondary"
          size="md"
          @click="previousStep"
          :disabled="isGenerating"
        >
          <template #iconLeft>
            <ChevronLeftIcon class="h-4 w-4" />
          </template>
          Back
        </Button>
        <div v-else></div>

        <!-- Action buttons -->
        <div class="flex items-center space-x-3">
          <Button
            variant="ghost"
            size="md"
            @click="skipWizard"
            :disabled="isGenerating"
          >
            Skip Wizard
          </Button>

          <Button
            v-if="currentStep < totalSteps"
            variant="primary"
            size="md"
            @click="nextStep"
            :disabled="!canProceed || isGenerating"
          >
            Next: {{ getNextStepLabel() }}
            <template #iconRight>
              <ChevronRightIcon class="h-4 w-4" />
            </template>
          </Button>

          <Button
            v-else
            variant="primary"
            size="md"
            @click="startGeneration"
            :loading="isGenerating"
            :disabled="!canProceed"
          >
            <template #iconLeft v-if="!isGenerating">
              <PlayIcon class="h-4 w-4" />
            </template>
            {{ isGenerating ? 'Generating...' : 'Start Generation' }}
          </Button>
        </div>
      </div>

      <!-- Estimated time -->
      <div v-if="estimatedTime && currentStep === totalSteps" class="mt-3 text-center">
        <Text size="sm" color="muted">
          Estimated time: ~{{ estimatedTime }} seconds per document
        </Text>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import { useDocumentsStore } from '@/stores/documents'
import {
  QuestionMarkCircleIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  PlayIcon
} from '@heroicons/vue/24/outline'

// Components
import Heading from '@/components/atoms/Heading.vue'
import Text from '@/components/atoms/Text.vue'
import Button from '@/components/atoms/Button.vue'
import DocumentTypeSelection from './steps/DocumentTypeSelection.vue'
import ConfigurationOptions from './steps/ConfigurationOptions.vue'
import GenerationReview from './steps/GenerationReview.vue'

// Types
interface DocumentGenerationData {
  documentTypes: string[]
  generateSuite: boolean
  aiEnhancement: boolean
  addToTracking: boolean
  aiModel: 'local' | 'cloud'
  useLocalModels: boolean
}

// Props
interface Props {
  projectId?: string
  initialDocType?: string
}

const props = withDefaults(defineProps<Props>(), {
  projectId: undefined,
  initialDocType: undefined
})

// Emits
const emit = defineEmits<{
  close: []
  complete: [documents: any[]]
}>()

// Stores
const router = useRouter()
const notificationsStore = useNotificationsStore()
const documentsStore = useDocumentsStore()

// State
const currentStep = ref(1)
const totalSteps = ref(3)
const isGenerating = ref(false)
const generationProgress = ref(0)

// Form data
const formData = reactive<DocumentGenerationData>({
  documentTypes: props.initialDocType ? [props.initialDocType] : [],
  generateSuite: false,
  aiEnhancement: true,
  addToTracking: true,
  aiModel: 'local',
  useLocalModels: true
})

// Step validation
const step1Valid = ref(false)
const step2Valid = ref(true) // Configuration is optional
const step3Valid = ref(true)

// Computed
const progress = computed(() => {
  return Math.round((currentStep.value / totalSteps.value) * 100)
})

const canProceed = computed(() => {
  switch (currentStep.value) {
    case 1: return step1Valid.value
    case 2: return step2Valid.value
    case 3: return step3Valid.value
    default: return false
  }
})

const estimatedTime = computed(() => {
  if (!formData.documentTypes.length) return null

  const baseTime = 30 // seconds per document
  const aiMultiplier = formData.aiEnhancement ? 1.5 : 1
  const suiteMultiplier = formData.generateSuite ? 1.2 : 1

  const totalTime = formData.documentTypes.length * baseTime * aiMultiplier * suiteMultiplier
  return Math.round(totalTime)
})

// Methods
const validateStep1 = () => {
  step1Valid.value = formData.documentTypes.length > 0
}

const validateStep2 = () => {
  step2Valid.value = true // Configuration options are all optional
}

const nextStep = () => {
  if (!canProceed.value) return

  if (currentStep.value < totalSteps.value) {
    currentStep.value++
  }
}

const previousStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

const getNextStepLabel = () => {
  switch (currentStep.value) {
    case 1: return 'Configure Options'
    case 2: return 'Review & Generate'
    default: return 'Next'
  }
}

const showHelp = () => {
  // TODO: Implement help modal or guide
  notificationsStore.addNotification({
    type: 'info',
    title: 'Help',
    message: 'Step-by-step guidance for document generation wizard'
  })
}

const skipWizard = () => {
  router.push('/app/documents')
  emit('close')
}

const startGeneration = async () => {
  if (isGenerating.value) return

  try {
    isGenerating.value = true
    generationProgress.value = 0

    // Simulate generation progress
    const progressInterval = setInterval(() => {
      generationProgress.value += Math.random() * 15
      if (generationProgress.value >= 95) {
        clearInterval(progressInterval)
      }
    }, 1000)

    // Call the document generation API for each document type
    const generatedDocuments = []

    for (let i = 0; i < formData.documentTypes.length; i++) {
      const docType = formData.documentTypes[i]

      try {
        const result = await documentsStore.generateDocument({
          template_id: docType,
          project_id: props.projectId,
          options: {
            ai_enhancement: formData.aiEnhancement,
            add_to_tracking: formData.addToTracking,
            ai_model: formData.useLocalModels ? 'local' : 'cloud',
            generate_suite: formData.generateSuite
          }
        })

        generatedDocuments.push(result)

        // Update progress after each document
        generationProgress.value = ((i + 1) / formData.documentTypes.length) * 100
      } catch (error) {
        console.error(`Failed to generate ${docType}:`, error)
        // Continue with other documents even if one fails
      }
    }

    clearInterval(progressInterval)
    generationProgress.value = 100

    // Show success notification
    notificationsStore.addNotification({
      type: 'success',
      title: 'Documents Generated',
      message: `Successfully generated ${generatedDocuments.length} of ${formData.documentTypes.length} document(s)`
    })

    // Navigate to documents view or emit completion
    emit('complete', generatedDocuments)

    setTimeout(() => {
      router.push('/app/documents')
    }, 1500)

  } catch (error) {
    console.error('Generation failed:', error)

    notificationsStore.addNotification({
      type: 'error',
      title: 'Generation Failed',
      message: error instanceof Error ? error.message : 'Failed to generate documents'
    })
  } finally {
    isGenerating.value = false
    generationProgress.value = 0
  }
}

// Initialize validation
validateStep1()

// Watch for changes in document types to update validation
watch(() => formData.documentTypes, validateStep1, { deep: true })
</script>

<style scoped>
.document-generation-wizard {
  @apply flex flex-col h-full bg-white dark:bg-gray-900;
}

.step-content {
  @apply min-h-0 flex-1;
}

/* Accessibility focus indicators */
.wizard-header button:focus,
.wizard-footer button:focus {
  @apply ring-2 ring-blue-500 ring-offset-2 dark:ring-offset-gray-900;
}

/* Smooth transitions */
.step-content {
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(1rem);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .wizard-header {
    @apply px-4 py-3;
  }

  .wizard-content {
    @apply px-4;
  }

  .wizard-footer {
    @apply px-4 py-3;
  }

  .wizard-footer .flex {
    @apply flex-col space-y-3 space-x-0;
  }
}
</style>