<template>
  <div class="fixed inset-0 z-50 overflow-y-auto" @keydown.esc="close">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="close"></div>

    <!-- Modal -->
    <div class="flex items-center justify-center min-h-screen p-4">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full p-6">
        <!-- Icon -->
        <div class="flex justify-center mb-4">
          <div
            :class="[
              'flex items-center justify-center h-12 w-12 rounded-full',
              type === 'success' && 'bg-green-100 dark:bg-green-900',
              type === 'error' && 'bg-red-100 dark:bg-red-900',
              type === 'warning' && 'bg-yellow-100 dark:bg-yellow-900',
              type === 'info' && 'bg-blue-100 dark:bg-blue-900'
            ]"
          >
            <component
              :is="getIcon()"
              :class="[
                'h-6 w-6',
                type === 'success' && 'text-green-600 dark:text-green-400',
                type === 'error' && 'text-red-600 dark:text-red-400',
                type === 'warning' && 'text-yellow-600 dark:text-yellow-400',
                type === 'info' && 'text-blue-600 dark:text-blue-400'
              ]"
            />
          </div>
        </div>

        <!-- Content -->
        <div class="text-center">
          <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {{ title }}
          </h3>
          <p class="text-sm text-gray-500 dark:text-gray-400">
            {{ message }}
          </p>
        </div>

        <!-- Actions -->
        <div class="mt-6 flex justify-center">
          <button
            @click="close"
            :class="[
              'px-4 py-2 text-sm font-medium text-white rounded-md',
              type === 'success' && 'bg-green-600 hover:bg-green-700',
              type === 'error' && 'bg-red-600 hover:bg-red-700',
              type === 'warning' && 'bg-yellow-600 hover:bg-yellow-700',
              type === 'info' && 'bg-blue-600 hover:bg-blue-700'
            ]"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/vue/24/outline';

interface Props {
  type?: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message?: string;
}

const props = withDefaults(defineProps<Props>(), {
  type: 'info',
  title: 'Notification',
  message: ''
});

const emit = defineEmits<{
  close: [];
}>();

const getIcon = () => {
  switch (props.type) {
    case 'success': return CheckCircleIcon;
    case 'error': return ExclamationCircleIcon;
    case 'warning': return ExclamationTriangleIcon;
    case 'info':
    default: return InformationCircleIcon;
  }
};

const close = () => {
  emit('close');
};
</script>