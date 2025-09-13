<template>
  <div
    class="document-option"
    :class="[
      selected ? 'selected' : 'unselected',
      { 'popular': document.popular, 'recommended': document.recommended }
    ]"
    @click="$emit('toggle', document.id)"
    @keydown.enter="$emit('toggle', document.id)"
    @keydown.space.prevent="$emit('toggle', document.id)"
    tabindex="0"
    role="checkbox"
    :aria-checked="selected"
    :aria-labelledby="`doc-${document.id}-name`"
    :aria-describedby="`doc-${document.id}-description`"
  >
    <!-- Selection checkbox -->
    <div class="checkbox-container">
      <div class="checkbox" :class="{ 'checked': selected }">
        <CheckIcon v-if="selected" class="h-3 w-3 text-white" />
      </div>
    </div>

    <!-- Document info -->
    <div class="document-info flex-1">
      <div class="flex items-center space-x-2">
        <Text
          :id="`doc-${document.id}-name`"
          size="sm"
          weight="medium"
          :class="selected ? 'text-blue-900 dark:text-blue-100' : 'text-gray-900 dark:text-gray-100'"
        >
          {{ document.name }}
        </Text>

        <!-- Badges -->
        <div class="flex space-x-1">
          <span
            v-if="document.popular"
            class="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300"
          >
            Popular
          </span>
          <span
            v-if="document.recommended"
            class="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
          >
            Recommended
          </span>
        </div>
      </div>

      <Text
        :id="`doc-${document.id}-description`"
        size="xs"
        color="muted"
        class="mt-1"
      >
        {{ document.description }}
      </Text>
    </div>

    <!-- Information icon with tooltip -->
    <div class="info-icon">
      <InformationCircleIcon
        class="h-4 w-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
        :title="`Learn more about ${document.name}`"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { CheckIcon, InformationCircleIcon } from '@heroicons/vue/24/outline'
import Text from '@/components/atoms/Text.vue'

// Types
interface DocumentType {
  id: string
  name: string
  description: string
  category: 'planning' | 'design'
  popular?: boolean
  recommended?: boolean
}

// Props
interface Props {
  document: DocumentType
  selected: boolean
}

defineProps<Props>()

// Emits
defineEmits<{
  toggle: [docId: string]
}>()
</script>

<style scoped>
.document-option {
  @apply flex items-center space-x-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg cursor-pointer transition-all duration-200 hover:shadow-sm;
}

.document-option:focus {
  @apply ring-2 ring-blue-500 ring-offset-2 dark:ring-offset-gray-800 outline-none;
}

.document-option.unselected {
  @apply bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750;
}

.document-option.selected {
  @apply bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-600 shadow-sm;
}

.document-option.popular {
  @apply relative;
}

.document-option.recommended::before {
  content: '';
  @apply absolute -top-1 -right-1 w-2 h-2 bg-green-500 rounded-full;
}

.checkbox-container {
  @apply flex-shrink-0;
}

.checkbox {
  @apply w-5 h-5 border-2 border-gray-300 dark:border-gray-600 rounded transition-all duration-200 flex items-center justify-center;
}

.checkbox.checked {
  @apply bg-blue-600 border-blue-600 dark:bg-blue-500 dark:border-blue-500;
}

.document-info {
  @apply min-w-0;
}

.info-icon {
  @apply flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200;
}

.document-option:hover .info-icon {
  @apply opacity-100;
}

/* Accessibility enhancements */
@media (prefers-reduced-motion: reduce) {
  .document-option,
  .checkbox {
    @apply transition-none;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .document-option.selected {
    @apply border-2 border-blue-600;
  }
}

/* Responsive adjustments */
@media (max-width: 640px) {
  .document-option {
    @apply p-2 space-x-2;
  }

  .document-info {
    @apply pr-2;
  }
}
</style>