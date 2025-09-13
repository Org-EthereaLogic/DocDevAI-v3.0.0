<template>
  <div class="bg-white rounded-lg shadow p-6 transition-all duration-300 hover:shadow-lg">
    <!-- Loading State -->
    <div v-if="loading" class="animate-pulse">
      <div class="flex items-center justify-between mb-4">
        <div class="h-10 w-10 bg-gray-200 rounded"></div>
        <div class="h-4 w-16 bg-gray-200 rounded"></div>
      </div>
      <div class="h-6 bg-gray-200 rounded w-1/2 mb-2"></div>
      <div class="h-4 bg-gray-200 rounded w-3/4"></div>
    </div>

    <!-- Content -->
    <div v-else>
      <div class="flex items-center justify-between mb-4">
        <!-- Icon -->
        <div class="flex-shrink-0">
          <div class="p-2 rounded-lg" :class="iconBackgroundClass">
            <component :is="iconComponent" class="h-6 w-6" :class="iconColorClass" />
          </div>
        </div>

        <!-- Change Indicator -->
        <div v-if="change" class="flex items-center text-sm">
          <span :class="changeColorClass" class="font-medium">
            {{ change }}
          </span>
          <svg v-if="isPositiveChange" class="ml-1 h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
          <svg v-else-if="isNegativeChange" class="ml-1 h-4 w-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </div>
      </div>

      <!-- Value and Label -->
      <div class="group relative">
        <p class="text-2xl font-semibold text-gray-900">{{ value }}</p>
        <p class="text-sm text-gray-600 mt-1">{{ label }}</p>

        <!-- Tooltip -->
        <div v-if="tooltip"
             class="absolute bottom-full left-0 mb-2 hidden group-hover:block z-10 w-64 p-2 text-sm text-white bg-gray-900 rounded-lg shadow-lg"
             role="tooltip">
          {{ tooltip }}
          <div class="absolute top-full left-4 -mt-1 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// Props
const props = defineProps({
  label: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    required: true
  },
  change: {
    type: String,
    default: null
  },
  icon: {
    type: String,
    default: 'document'
  },
  loading: {
    type: Boolean,
    default: false
  },
  tooltip: {
    type: String,
    default: null
  }
})

// Computed properties for change indicators
const isPositiveChange = computed(() => {
  return props.change && (props.change.startsWith('+') || props.change.includes('increase'))
})

const isNegativeChange = computed(() => {
  return props.change && (props.change.startsWith('-') || props.change.includes('decrease'))
})

const changeColorClass = computed(() => {
  if (isPositiveChange.value) return 'text-green-600'
  if (isNegativeChange.value) return 'text-red-600'
  return 'text-gray-600'
})

// Icon styling based on type
const iconBackgroundClass = computed(() => {
  const classes = {
    document: 'bg-blue-100',
    health: 'bg-green-100',
    suite: 'bg-purple-100',
    activity: 'bg-orange-100'
  }
  return classes[props.icon] || 'bg-gray-100'
})

const iconColorClass = computed(() => {
  const classes = {
    document: 'text-blue-600',
    health: 'text-green-600',
    suite: 'text-purple-600',
    activity: 'text-orange-600'
  }
  return classes[props.icon] || 'text-gray-600'
})

// Icon components
const iconComponent = computed(() => {
  const icons = {
    document: DocumentIcon,
    health: HealthIcon,
    suite: SuiteIcon,
    activity: ActivityIcon
  }
  return icons[props.icon] || DocumentIcon
})

// Icon component definitions
const DocumentIcon = {
  template: `
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  `
}

const HealthIcon = {
  template: `
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
    </svg>
  `
}

const SuiteIcon = {
  template: `
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
    </svg>
  `
}

const ActivityIcon = {
  template: `
    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  `
}
</script>

<style scoped>
/* Smooth transitions for hover effects */
.group:hover .group-hover\:block {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
