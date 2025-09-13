<template>
  <div class="document-generate-view min-h-full bg-gray-50 dark:bg-gray-900">
    <!-- Header -->
    <div class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <Button
              variant="ghost"
              size="sm"
              @click="goBack"
              class="mr-2"
            >
              <template #iconLeft>
                <ArrowLeftIcon class="h-4 w-4" />
              </template>
              Back
            </Button>
            <div>
              <Heading level="1" size="xl" weight="bold" color="primary">
                Generate New Document
              </Heading>
              <Text size="sm" color="muted" class="mt-1">
                Create professional documentation with AI assistance
              </Text>
            </div>
          </div>

          <!-- Project context (if available) -->
          <div v-if="currentProject" class="text-right">
            <Text size="sm" color="muted">Project:</Text>
            <Text size="sm" weight="semibold">{{ currentProject.name }}</Text>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 min-h-[600px] flex flex-col">
        <!-- Wizard Component -->
        <DocumentGenerationWizard
          :project-id="projectId"
          :initial-doc-type="initialDocType"
          @close="handleClose"
          @complete="handleComplete"
        />
      </div>
    </div>

    <!-- Quick Start Tips (Sidebar) -->
    <div v-if="showTips" class="fixed right-4 top-1/2 transform -translate-y-1/2 w-80 z-10">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-4">
        <div class="flex items-center justify-between mb-3">
          <Heading level="3" size="sm" weight="semibold">
            Quick Tips
          </Heading>
          <Button
            variant="ghost"
            size="xs"
            @click="showTips = false"
            aria-label="Close tips"
          >
            <XMarkIcon class="h-4 w-4" />
          </Button>
        </div>

        <div class="space-y-3 text-sm">
          <div class="flex items-start space-x-2">
            <LightBulbIcon class="h-4 w-4 text-yellow-500 mt-0.5 flex-shrink-0" />
            <Text size="xs">
              Select multiple document types to generate a complete documentation suite
            </Text>
          </div>
          <div class="flex items-start space-x-2">
            <ShieldCheckIcon class="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <Text size="xs">
              Local models ensure privacy while cloud models provide higher quality
            </Text>
          </div>
          <div class="flex items-start space-x-2">
            <SparklesIcon class="h-4 w-4 text-purple-500 mt-0.5 flex-shrink-0" />
            <Text size="xs">
              AI enhancement improves document quality by 60-75% using MIAIR technology
            </Text>
          </div>
        </div>

        <div class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
          <Button
            variant="ghost"
            size="xs"
            @click="showKeyboardShortcuts"
            class="w-full justify-center"
          >
            <template #iconLeft>
              <KeyIcon class="h-3 w-3" />
            </template>
            Keyboard Shortcuts
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useNotificationsStore } from '@/stores/notifications'
import {
  ArrowLeftIcon,
  XMarkIcon,
  LightBulbIcon,
  ShieldCheckIcon,
  SparklesIcon,
  KeyIcon
} from '@heroicons/vue/24/outline'

// Components
import Heading from '@/components/atoms/Heading.vue'
import Text from '@/components/atoms/Text.vue'
import Button from '@/components/atoms/Button.vue'
import DocumentGenerationWizard from '@/components/organisms/wizards/DocumentGenerationWizard.vue'

// Stores
const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const notificationsStore = useNotificationsStore()

// State
const showTips = ref(true)

// Computed
const projectId = computed(() => route.query.projectId as string || undefined)
const initialDocType = computed(() => route.query.type as string || undefined)

const currentProject = computed(() => {
  if (!projectId.value) return null
  // TODO: Implement project store or get project data
  return { name: 'Current Project' }
})

// Methods
const goBack = () => {
  // Go back to previous page or documents list
  const referrer = route.query.from as string
  if (referrer) {
    router.push(referrer)
  } else {
    router.push('/app/documents')
  }
}

const handleClose = () => {
  goBack()
}

const handleComplete = (documents: any[]) => {
  notificationsStore.addNotification({
    type: 'success',
    title: 'Documents Generated Successfully',
    message: `Generated ${documents.length} document${documents.length !== 1 ? 's' : ''} successfully`
  })

  // Navigate to documents view with focus on new documents
  router.push({
    path: '/app/documents',
    query: {
      newDocuments: documents.map(doc => doc.id).join(','),
      projectId: projectId.value
    }
  })
}

const showKeyboardShortcuts = () => {
  // TODO: Implement keyboard shortcuts modal
  notificationsStore.addNotification({
    type: 'info',
    title: 'Keyboard Shortcuts',
    message: 'F1: Help, Tab: Navigate, Enter/Space: Select, Esc: Cancel'
  })
}

// Lifecycle
onMounted(() => {
  // Auto-hide tips after 10 seconds if user doesn't interact
  setTimeout(() => {
    if (showTips.value) {
      showTips.value = false
    }
  }, 10000)

  // Set page title
  document.title = 'Generate Document - DevDocAI'

  // Track page visit for analytics (if enabled)
  if (appStore.analyticsEnabled) {
    // TODO: Track page visit
  }
})

// Keyboard shortcuts
const handleKeydown = (event: KeyboardEvent) => {
  switch (event.key) {
    case 'Escape':
      if (event.ctrlKey || event.metaKey) {
        goBack()
      }
      break
    case 'F1':
      event.preventDefault()
      showKeyboardShortcuts()
      break
    case '?':
      if (event.shiftKey) {
        showKeyboardShortcuts()
      }
      break
  }
}

// Add global keyboard listener
onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

// Cleanup
import { onUnmounted } from 'vue'
onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.document-generate-view {
  @apply min-h-screen;
}

/* Smooth transitions for tips panel */
.fixed {
  transition: transform 0.3s ease-out, opacity 0.3s ease-out;
}

/* Focus trap for modal-like behavior */
.document-generate-view:focus-within .fixed {
  @apply opacity-100;
}

/* Responsive adjustments */
@media (max-width: 1280px) {
  .fixed.right-4 {
    @apply hidden;
  }
}

@media (max-width: 768px) {
  .max-w-6xl {
    @apply px-2;
  }

  .bg-white.rounded-lg {
    @apply rounded-none border-x-0;
  }
}

/* Print styles */
@media print {
  .fixed {
    @apply hidden;
  }

  .document-generate-view {
    @apply bg-white;
  }
}

/* Accessibility improvements */
@media (prefers-reduced-motion: reduce) {
  .fixed {
    @apply transition-none;
  }
}

/* High contrast mode */
@media (prefers-contrast: high) {
  .bg-white {
    @apply border-2 border-gray-900;
  }
}
</style>
