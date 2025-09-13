<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-50 overflow-y-auto"
        @keydown.esc="close"
      >
        <!-- Backdrop -->
        <div
          class="fixed inset-0 bg-gray-500 bg-opacity-75 dark:bg-gray-900 dark:bg-opacity-75"
          @click="close"
        ></div>

        <!-- Modal -->
        <div class="flex items-center justify-center min-h-screen p-4">
          <div class="relative bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full p-6 shadow-xl">
            <!-- Header -->
            <div class="flex items-center justify-between mb-4">
              <h2 class="text-xl font-semibold text-gray-900 dark:text-white">
                Keyboard Shortcuts
              </h2>
              <button
                @click="close"
                class="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
              >
                <XMarkIcon class="h-6 w-6" />
              </button>
            </div>

            <!-- Content -->
            <div class="space-y-6">
              <!-- Navigation -->
              <div>
                <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-3">
                  Navigation
                </h3>
                <div class="space-y-2">
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Go to Dashboard</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">G D</kbd>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Go to Documents</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">G O</kbd>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Go to Templates</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">G T</kbd>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Go to Settings</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">G S</kbd>
                  </div>
                </div>
              </div>

              <!-- Actions -->
              <div>
                <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-3">
                  Actions
                </h3>
                <div class="space-y-2">
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Search</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">⌘ /</kbd>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Command Palette</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">⌘ K</kbd>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Toggle Sidebar</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">⌘ B</kbd>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Help</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">⌘ ?</kbd>
                  </div>
                </div>
              </div>

              <!-- Document -->
              <div>
                <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-3">
                  Document
                </h3>
                <div class="space-y-2">
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Generate Document</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">⌘ N</kbd>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Save</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">⌘ S</kbd>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600 dark:text-gray-400">Export</span>
                    <kbd class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 rounded">⌘ E</kbd>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { XMarkIcon } from '@heroicons/vue/24/outline';

interface Props {
  modelValue?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
});

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  close: [];
}>();

const close = () => {
  emit('update:modelValue', false);
  emit('close');
};
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>