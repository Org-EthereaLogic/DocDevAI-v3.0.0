<template>
  <div class="fixed inset-0 z-50 overflow-y-auto" @keydown.esc="close">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="close"></div>

    <!-- Settings Modal -->
    <div class="flex items-center justify-center min-h-screen p-4">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full">
        <!-- Header -->
        <div class="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 class="text-xl font-semibold text-gray-900 dark:text-white">Quick Settings</h2>
          <button @click="close" class="text-gray-400 hover:text-gray-500">
            <XMarkIcon class="h-6 w-6" />
          </button>
        </div>

        <!-- Settings Content -->
        <div class="p-6 space-y-6">
          <!-- Theme -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Theme
            </label>
            <select class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700">
              <option>System</option>
              <option>Light</option>
              <option>Dark</option>
            </select>
          </div>

          <!-- Notifications -->
          <div>
            <label class="flex items-center space-x-3">
              <input type="checkbox" class="rounded text-blue-600" checked />
              <span class="text-sm text-gray-700 dark:text-gray-300">Enable notifications</span>
            </label>
          </div>

          <!-- Sound Effects -->
          <div>
            <label class="flex items-center space-x-3">
              <input type="checkbox" class="rounded text-blue-600" />
              <span class="text-sm text-gray-700 dark:text-gray-300">Enable sound effects</span>
            </label>
          </div>

          <!-- Compact Mode -->
          <div>
            <label class="flex items-center space-x-3">
              <input type="checkbox" class="rounded text-blue-600" />
              <span class="text-sm text-gray-700 dark:text-gray-300">Compact mode</span>
            </label>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex justify-end space-x-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            @click="close"
            class="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
          >
            Cancel
          </button>
          <button
            @click="saveSettings"
            class="px-4 py-2 text-sm text-white bg-blue-600 hover:bg-blue-700 rounded-md"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { XMarkIcon } from '@heroicons/vue/24/outline';
import { useAppStore } from '@/stores/app';

const appStore = useAppStore();

const close = () => {
  appStore.showSettings = false;
};

const saveSettings = () => {
  // Save settings logic here
  close();
};
</script>