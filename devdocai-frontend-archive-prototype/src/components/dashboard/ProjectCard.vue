<template>
  <div class="bg-white rounded-lg shadow hover:shadow-lg transition-all duration-300 overflow-hidden group">
    <!-- Health Score Indicator Bar -->
    <div class="h-1 bg-gray-200">
      <div
        class="h-full transition-all duration-500"
        :class="healthScoreColorClass"
        :style="{ width: `${project.healthScore}%` }"
      ></div>
    </div>

    <!-- Card Content -->
    <div class="p-6">
      <!-- Project Header -->
      <div class="flex items-start justify-between mb-4">
        <div class="flex-1">
          <h3 class="text-lg font-semibold text-gray-900 mb-1">
            {{ project.name }}
          </h3>
          <div class="flex items-center space-x-4 text-sm text-gray-600">
            <span class="flex items-center">
              <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              {{ project.documentCount }} docs
            </span>
            <span class="flex items-center">
              <svg class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {{ formatLastUpdated }}
            </span>
          </div>
        </div>

        <!-- Status Badge -->
        <span
          class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
          :class="statusBadgeClass"
        >
          {{ statusLabel }}
        </span>
      </div>

      <!-- Health Score -->
      <div class="mb-4">
        <div class="flex items-center justify-between mb-1">
          <span class="text-sm font-medium text-gray-700">Health Score</span>
          <div class="group/tooltip relative">
            <span class="text-sm font-semibold" :class="healthScoreTextClass">
              {{ project.healthScore }}%
            </span>
            <!-- Health Score Tooltip -->
            <div class="absolute bottom-full right-0 mb-2 hidden group-hover/tooltip:block z-10 w-48 p-2 text-xs text-white bg-gray-900 rounded-lg shadow-lg">
              Documentation quality based on completeness, accuracy, and compliance
              <div class="absolute top-full right-2 -mt-1 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
            </div>
          </div>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div
            class="h-2 rounded-full transition-all duration-500"
            :class="healthScoreColorClass"
            :style="{ width: `${project.healthScore}%` }"
          ></div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
        <button
          @click="$emit('view', project)"
          class="flex-1 inline-flex items-center justify-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors duration-200"
          aria-label="View project details"
        >
          <svg class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          View
        </button>
        <button
          @click="$emit('edit', project)"
          class="flex-1 inline-flex items-center justify-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors duration-200"
          aria-label="Edit project"
        >
          <svg class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          Edit
        </button>
        <button
          @click="$emit('generate', project)"
          class="flex-1 inline-flex items-center justify-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors duration-200"
          aria-label="Generate documentation"
        >
          <svg class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Generate
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

// Props
const props = defineProps({
  project: {
    type: Object,
    required: true,
    validator: (value) => {
      return value.id && value.name && value.documentCount !== undefined &&
             value.healthScore !== undefined && value.lastUpdated
    }
  }
})

// Emits
defineEmits(['view', 'edit', 'generate'])

// Computed properties
const formatLastUpdated = computed(() => {
  const now = new Date()
  const updated = new Date(props.project.lastUpdated)
  const diffMs = now - updated
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 60) {
    return diffMins <= 1 ? 'Just now' : `${diffMins} mins ago`
  } else if (diffHours < 24) {
    return diffHours === 1 ? '1 hour ago' : `${diffHours} hours ago`
  } else if (diffDays < 30) {
    return diffDays === 1 ? '1 day ago' : `${diffDays} days ago`
  } else {
    return updated.toLocaleDateString()
  }
})

const healthScoreColorClass = computed(() => {
  const score = props.project.healthScore
  if (score >= 80) return 'bg-green-500'
  if (score >= 60) return 'bg-yellow-500'
  if (score >= 40) return 'bg-orange-500'
  return 'bg-red-500'
})

const healthScoreTextClass = computed(() => {
  const score = props.project.healthScore
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-yellow-600'
  if (score >= 40) return 'text-orange-600'
  return 'text-red-600'
})

const statusBadgeClass = computed(() => {
  const status = props.project.status || 'active'
  const classes = {
    active: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    critical: 'bg-red-100 text-red-800',
    inactive: 'bg-gray-100 text-gray-800'
  }
  return classes[status] || classes.active
})

const statusLabel = computed(() => {
  const status = props.project.status || 'active'
  const labels = {
    active: 'Active',
    warning: 'Needs Attention',
    critical: 'Critical',
    inactive: 'Inactive'
  }
  return labels[status] || 'Active'
})
</script>

<style scoped>
/* Animation for health score bar */
@keyframes fillProgress {
  from {
    width: 0;
  }
}

.bg-green-500,
.bg-yellow-500,
.bg-orange-500,
.bg-red-500 {
  animation: fillProgress 1s ease-out;
}
</style>
