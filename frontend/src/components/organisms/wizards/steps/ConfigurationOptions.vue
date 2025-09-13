<template>
  <div class="configuration-options">
    <!-- Section Header -->
    <div class="mb-6">
      <Heading level="2" size="lg" weight="semibold" color="primary" class="mb-2">
        Configuration Options
      </Heading>
      <Text size="sm" color="muted">
        Customize how your documents are generated and enhanced
      </Text>
    </div>

    <!-- Enhancement Options -->
    <div class="options-grid space-y-6">

      <!-- AI Enhancement -->
      <div class="option-card bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div class="flex items-start space-x-4">
          <div class="flex-shrink-0 mt-1">
            <input
              id="ai-enhancement"
              v-model="localAiEnhancement"
              type="checkbox"
              class="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 rounded"
            >
          </div>
          <div class="flex-1">
            <label
              for="ai-enhancement"
              class="flex items-center space-x-2 text-base font-medium text-gray-900 dark:text-gray-100 cursor-pointer"
            >
              <span>Use AI Enhancement</span>
              <SparklesIcon class="h-5 w-5 text-yellow-500" />
            </label>
            <div class="mt-2 flex items-center space-x-1">
              <InformationCircleIcon class="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <Text size="sm" color="muted">
                Uses MIAIR to improve quality by 60-75%
              </Text>
            </div>
          </div>
        </div>
      </div>

      <!-- Add to Tracking Matrix -->
      <div class="option-card bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div class="flex items-start space-x-4">
          <div class="flex-shrink-0 mt-1">
            <input
              id="add-tracking"
              v-model="localAddToTracking"
              type="checkbox"
              class="h-5 w-5 text-blue-600 focus:ring-blue-500 border-gray-300 dark:border-gray-600 rounded"
            >
          </div>
          <div class="flex-1">
            <label
              for="add-tracking"
              class="flex items-center space-x-2 text-base font-medium text-gray-900 dark:text-gray-100 cursor-pointer"
            >
              <span>Add to Tracking Matrix</span>
              <LinkIcon class="h-5 w-5 text-green-500" />
            </label>
            <div class="mt-2 flex items-center space-x-1">
              <InformationCircleIcon class="h-4 w-4 text-blue-600 dark:text-blue-400" />
              <Text size="sm" color="muted">
                Automatically tracks relationships & versions
              </Text>
            </div>
          </div>
        </div>
      </div>

      <!-- AI Model Selection -->
      <div class="option-card bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div class="mb-4">
          <Heading level="3" size="md" weight="semibold" class="mb-2">
            AI Model Selection
          </Heading>
          <Text size="sm" color="muted">
            Choose between local privacy-first models or cloud models for better quality
          </Text>
        </div>

        <!-- Model Type Selection -->
        <div class="space-y-4">
          <!-- Local Models -->
          <div class="model-option" :class="{ 'selected': localUseLocalModels }">
            <label class="radio-label">
              <input
                v-model="localUseLocalModels"
                :value="true"
                type="radio"
                name="model-type"
                class="sr-only"
              >
              <div class="radio-indicator">
                <div v-if="localUseLocalModels" class="radio-dot"></div>
              </div>
              <div class="flex-1">
                <div class="flex items-center space-x-2">
                  <Text size="base" weight="semibold">Local Models</Text>
                  <ShieldCheckIcon class="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
                <Text size="sm" color="muted" class="mt-1">
                  Privacy-first, no internet needed
                </Text>
                <!-- Local Models Status -->
                <div class="mt-3 space-y-2">
                  <div class="flex items-center justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">LLaMA 2 (4.2 GB)</span>
                    <span class="flex items-center text-green-600 dark:text-green-400">
                      <CheckCircleIcon class="h-4 w-4 mr-1" />
                      Installed
                    </span>
                  </div>
                  <div class="flex items-center justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Mistral 7B (3.8 GB)</span>
                    <span class="flex items-center text-green-600 dark:text-green-400">
                      <CheckCircleIcon class="h-4 w-4 mr-1" />
                      Installed
                    </span>
                  </div>
                </div>
              </div>
            </label>
          </div>

          <!-- Cloud Models -->
          <div class="model-option" :class="{ 'selected': !localUseLocalModels }">
            <label class="radio-label">
              <input
                v-model="localUseLocalModels"
                :value="false"
                type="radio"
                name="model-type"
                class="sr-only"
              >
              <div class="radio-indicator">
                <div v-if="!localUseLocalModels" class="radio-dot"></div>
              </div>
              <div class="flex-1">
                <div class="flex items-center space-x-2">
                  <Text size="base" weight="semibold">Cloud Models</Text>
                  <CloudIcon class="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
                <Text size="sm" color="muted" class="mt-1">
                  Better quality, requires API keys
                </Text>
                <!-- Cloud Models Distribution -->
                <div v-if="!localUseLocalModels" class="mt-3">
                  <Text size="xs" color="muted" class="mb-2">Model distribution:</Text>
                  <div class="space-y-1 text-xs">
                    <div class="flex items-center justify-between">
                      <span class="text-gray-600 dark:text-gray-400">Claude</span>
                      <span class="text-purple-600 dark:text-purple-400">40%</span>
                    </div>
                    <div class="flex items-center justify-between">
                      <span class="text-gray-600 dark:text-gray-400">ChatGPT</span>
                      <span class="text-green-600 dark:text-green-400">35%</span>
                    </div>
                    <div class="flex items-center justify-between">
                      <span class="text-gray-600 dark:text-gray-400">Gemini</span>
                      <span class="text-blue-600 dark:text-blue-400">25%</span>
                    </div>
                  </div>
                </div>
              </div>
            </label>
          </div>
        </div>

        <!-- Cost Information for Cloud Models -->
        <div v-if="!localUseLocalModels" class="cost-info mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <div class="flex items-center space-x-2 mb-2">
            <CurrencyDollarIcon class="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
            <Text size="sm" weight="medium" class="text-yellow-800 dark:text-yellow-200">
              Estimated Costs
            </Text>
          </div>
          <div class="space-y-1 text-sm text-yellow-700 dark:text-yellow-300">
            <div class="flex justify-between">
              <span>Claude:</span>
              <span>~$0.02 per document</span>
            </div>
            <div class="flex justify-between">
              <span>ChatGPT:</span>
              <span>~$0.01 per document</span>
            </div>
            <div class="flex justify-between">
              <span>Gemini:</span>
              <span>~$0.015 per document</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Advanced Options (Collapsible) -->
      <div class="option-card bg-gray-50 dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <button
          @click="showAdvanced = !showAdvanced"
          class="flex items-center justify-between w-full text-left"
          :aria-expanded="showAdvanced"
        >
          <Heading level="3" size="md" weight="semibold">
            Advanced Options
          </Heading>
          <ChevronDownIcon
            :class="[
              'h-5 w-5 text-gray-500 transition-transform duration-200',
              showAdvanced ? 'rotate-180' : ''
            ]"
          />
        </button>

        <Transition
          name="collapse"
          enter-active-class="transition-all duration-200 ease-out"
          enter-from-class="max-h-0 opacity-0"
          enter-to-class="max-h-96 opacity-100"
          leave-active-class="transition-all duration-200 ease-in"
          leave-from-class="max-h-96 opacity-100"
          leave-to-class="max-h-0 opacity-0"
        >
          <div v-if="showAdvanced" class="mt-4 space-y-4 overflow-hidden">
            <!-- Template Customization -->
            <div class="advanced-option">
              <label class="flex items-center space-x-3">
                <input
                  v-model="advancedOptions.customTemplates"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                >
                <div>
                  <Text size="sm" weight="medium">Use Custom Templates</Text>
                  <Text size="xs" color="muted">Apply project-specific template overrides</Text>
                </div>
              </label>
            </div>

            <!-- Version Control Integration -->
            <div class="advanced-option">
              <label class="flex items-center space-x-3">
                <input
                  v-model="advancedOptions.gitIntegration"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                >
                <div>
                  <Text size="sm" weight="medium">Git Integration</Text>
                  <Text size="xs" color="muted">Automatically commit generated documents</Text>
                </div>
              </label>
            </div>

            <!-- Quality Threshold -->
            <div class="advanced-option">
              <label class="block">
                <Text size="sm" weight="medium" class="mb-2">Quality Threshold</Text>
                <select
                  v-model="advancedOptions.qualityThreshold"
                  class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm"
                >
                  <option value="70">Standard (70%)</option>
                  <option value="85">High (85%)</option>
                  <option value="95">Premium (95%)</option>
                </select>
              </label>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, watch } from 'vue'
import {
  SparklesIcon,
  LinkIcon,
  ShieldCheckIcon,
  CloudIcon,
  CheckCircleIcon,
  CurrencyDollarIcon,
  ChevronDownIcon,
  InformationCircleIcon
} from '@heroicons/vue/24/outline'

// Components
import Heading from '@/components/atoms/Heading.vue'
import Text from '@/components/atoms/Text.vue'

// Props
interface Props {
  aiEnhancement: boolean
  addToTracking: boolean
  aiModel: 'local' | 'cloud'
  useLocalModels: boolean
}

const props = withDefaults(defineProps<Props>(), {
  aiEnhancement: true,
  addToTracking: true,
  aiModel: 'local',
  useLocalModels: true
})

// Emits
const emit = defineEmits<{
  'update:aiEnhancement': [value: boolean]
  'update:addToTracking': [value: boolean]
  'update:aiModel': [value: 'local' | 'cloud']
  'update:useLocalModels': [value: boolean]
  'update': []
}>()

// Local state
const showAdvanced = ref(false)

const advancedOptions = reactive({
  customTemplates: false,
  gitIntegration: true,
  qualityThreshold: 85
})

// Computed properties for two-way binding
const localAiEnhancement = computed({
  get: () => props.aiEnhancement,
  set: (value) => {
    emit('update:aiEnhancement', value)
    emit('update')
  }
})

const localAddToTracking = computed({
  get: () => props.addToTracking,
  set: (value) => {
    emit('update:addToTracking', value)
    emit('update')
  }
})

const localUseLocalModels = computed({
  get: () => props.useLocalModels,
  set: (value) => {
    emit('update:useLocalModels', value)
    emit('update:aiModel', value ? 'local' : 'cloud')
    emit('update')
  }
})

// Watch for changes to emit updates
watch(advancedOptions, () => {
  emit('update')
}, { deep: true })
</script>

<style scoped>
.option-card {
  @apply transition-all duration-200 hover:shadow-sm;
}

.model-option {
  @apply border border-gray-200 dark:border-gray-700 rounded-lg p-4 cursor-pointer transition-all duration-200;
}

.model-option.selected {
  @apply border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20;
}

.model-option:hover:not(.selected) {
  @apply border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-750;
}

.radio-label {
  @apply flex items-start space-x-3 cursor-pointer w-full;
}

.radio-indicator {
  @apply w-5 h-5 border-2 border-gray-300 dark:border-gray-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5;
}

.model-option.selected .radio-indicator {
  @apply border-blue-600 dark:border-blue-500;
}

.radio-dot {
  @apply w-2.5 h-2.5 bg-blue-600 dark:bg-blue-500 rounded-full;
}

.advanced-option {
  @apply py-2 border-b border-gray-200 dark:border-gray-700 last:border-b-0;
}

/* Checkbox and radio button focus styles */
input[type="checkbox"]:focus,
input[type="radio"]:focus {
  @apply ring-2 ring-blue-500 ring-offset-2 dark:ring-offset-gray-800;
}

/* Collapse transition */
.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}

.collapse-enter-to,
.collapse-leave-from {
  max-height: 24rem; /* max-h-96 */
  opacity: 1;
}

/* Responsive design */
@media (max-width: 640px) {
  .option-card {
    @apply p-4;
  }

  .model-option {
    @apply p-3;
  }

  .radio-label {
    @apply space-x-2;
  }
}

/* High contrast support */
@media (prefers-contrast: high) {
  .model-option.selected {
    @apply border-2 border-blue-600;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .option-card,
  .model-option,
  .radio-indicator {
    @apply transition-none;
  }

  .collapse-enter-active,
  .collapse-leave-active {
    @apply transition-none;
  }
}
</style>