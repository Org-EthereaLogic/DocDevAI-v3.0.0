<template>
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
    <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Generation Progress</h3>

    <!-- Progress Steps -->
    <div class="space-y-4">
      <div
        v-for="(step, index) in steps"
        :key="step.id"
        class="flex items-center"
      >
        <!-- Step Icon -->
        <div
          class="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300"
          :class="getStepClasses(step)"
        >
          <!-- Completed Icon -->
          <svg v-if="step.status === 'completed'" class="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>

          <!-- In Progress Spinner -->
          <div v-else-if="step.status === 'active'" class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>

          <!-- Pending Number -->
          <span v-else class="text-sm font-medium text-gray-600 dark:text-gray-400">{{ index + 1 }}</span>
        </div>

        <!-- Step Content -->
        <div class="ml-4 flex-1">
          <p
            class="text-sm font-medium transition-colors duration-300"
            :class="{
              'text-gray-900 dark:text-white': step.status === 'completed' || step.status === 'active',
              'text-gray-500 dark:text-gray-400': step.status === 'pending'
            }"
          >
            {{ step.label }}
          </p>
          <p
            v-if="step.description"
            class="text-xs mt-1 transition-colors duration-300"
            :class="{
              'text-gray-600 dark:text-gray-300': step.status === 'completed' || step.status === 'active',
              'text-gray-400 dark:text-gray-500': step.status === 'pending'
            }"
          >
            {{ step.description }}
          </p>
        </div>

        <!-- Step Duration -->
        <div v-if="step.duration" class="flex-shrink-0 ml-4">
          <span class="text-xs text-gray-500 dark:text-gray-400">{{ formatDuration(step.duration) }}</span>
        </div>
      </div>
    </div>

    <!-- Overall Progress Bar -->
    <div class="mt-6">
      <div class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
        <span>Overall Progress</span>
        <span>{{ overallProgress }}%</span>
      </div>
      <div class="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700 overflow-hidden">
        <div
          class="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full transition-all duration-500 ease-out relative"
          :style="{ width: `${overallProgress}%` }"
        >
          <!-- Animated shimmer effect -->
          <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer"></div>
        </div>
      </div>
    </div>

    <!-- Estimated Time Remaining -->
    <div v-if="estimatedTimeRemaining" class="mt-4 text-center">
      <p class="text-sm text-gray-600 dark:text-gray-400">
        Estimated time remaining: <span class="font-medium">{{ estimatedTimeRemaining }}</span>
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  currentStatus: {
    type: String,
    default: 'initializing'
  },
  progress: {
    type: Number,
    default: 0
  }
})

// Define generation steps
const steps = computed(() => {
  const allSteps = [
    {
      id: 'initializing',
      label: 'Initializing',
      description: 'Setting up AI models and environment',
      status: 'pending'
    },
    {
      id: 'analyzing',
      label: 'Analyzing Project',
      description: 'Understanding project structure and requirements',
      status: 'pending'
    },
    {
      id: 'generating',
      label: 'Generating Content',
      description: 'Creating documentation with AI assistance',
      status: 'pending'
    },
    {
      id: 'enhancing',
      label: 'Enhancing Quality',
      description: 'Applying AI-powered improvements',
      status: 'pending'
    },
    {
      id: 'formatting',
      label: 'Formatting',
      description: 'Structuring and styling the document',
      status: 'pending'
    },
    {
      id: 'finalizing',
      label: 'Finalizing',
      description: 'Final checks and preparations',
      status: 'pending'
    }
  ]

  // Update step statuses based on current status
  const currentIndex = allSteps.findIndex(s => s.id === props.currentStatus)

  return allSteps.map((step, index) => {
    if (index < currentIndex) {
      return { ...step, status: 'completed', duration: Math.floor(Math.random() * 10) + 3 }
    } else if (index === currentIndex) {
      return { ...step, status: 'active' }
    } else {
      return { ...step, status: 'pending' }
    }
  })
})

const overallProgress = computed(() => {
  return Math.min(props.progress, 100)
})

const estimatedTimeRemaining = computed(() => {
  if (props.progress >= 100) return null
  if (props.progress === 0) return '45-60 seconds'

  const remainingProgress = 100 - props.progress
  const estimatedSeconds = Math.ceil((remainingProgress / props.progress) * 10)

  if (estimatedSeconds < 60) {
    return `${estimatedSeconds} seconds`
  } else {
    const minutes = Math.floor(estimatedSeconds / 60)
    const seconds = estimatedSeconds % 60
    return `${minutes}m ${seconds}s`
  }
})

const getStepClasses = (step) => {
  if (step.status === 'completed') {
    return 'bg-green-500 dark:bg-green-600'
  } else if (step.status === 'active') {
    return 'bg-blue-500 dark:bg-blue-600 animate-pulse'
  } else {
    return 'bg-gray-200 dark:bg-gray-700'
  }
}

const formatDuration = (seconds) => {
  return `${seconds}s`
}
</script>

<style scoped>
@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(200%);
  }
}

.animate-shimmer {
  animation: shimmer 2s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
