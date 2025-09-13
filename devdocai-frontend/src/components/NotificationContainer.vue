<template>
  <div class="fixed top-4 right-4 z-50 space-y-2">
    <transition-group name="notification" tag="div">
      <div
        v-for="notification in uiStore.notifications"
        :key="notification.id"
        :class="[
          'max-w-sm bg-white border rounded-lg shadow-lg p-4',
          notificationClasses[notification.type]
        ]"
      >
        <div class="flex items-start">
          <div class="flex-shrink-0">
            <component :is="notificationIcons[notification.type]" class="h-5 w-5" />
          </div>
          <div class="ml-3 w-0 flex-1">
            <p :class="['text-sm font-medium', textClasses[notification.type]]">
              {{ notification.title }}
            </p>
            <p :class="['mt-1 text-sm', textClasses[notification.type]]">
              {{ notification.message }}
            </p>
          </div>
          <div class="ml-4 flex-shrink-0 flex">
            <button
              @click="uiStore.removeNotification(notification.id)"
              :class="['rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2', focusClasses[notification.type]]"
            >
              <span class="sr-only">Close</span>
              <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { h } from 'vue'
import { useUIStore } from '@/stores/ui'

const uiStore = useUIStore()

// Icon components
const CheckCircleIcon = () => h('svg', {
  class: 'text-green-400',
  fill: 'currentColor',
  viewBox: '0 0 20 20'
}, [
  h('path', {
    fillRule: 'evenodd',
    d: 'M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z',
    clipRule: 'evenodd'
  })
])

const XCircleIcon = () => h('svg', {
  class: 'text-red-400',
  fill: 'currentColor',
  viewBox: '0 0 20 20'
}, [
  h('path', {
    fillRule: 'evenodd',
    d: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z',
    clipRule: 'evenodd'
  })
])

const ExclamationTriangleIcon = () => h('svg', {
  class: 'text-yellow-400',
  fill: 'currentColor',
  viewBox: '0 0 20 20'
}, [
  h('path', {
    fillRule: 'evenodd',
    d: 'M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z',
    clipRule: 'evenodd'
  })
])

const InformationCircleIcon = () => h('svg', {
  class: 'text-blue-400',
  fill: 'currentColor',
  viewBox: '0 0 20 20'
}, [
  h('path', {
    fillRule: 'evenodd',
    d: 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z',
    clipRule: 'evenodd'
  })
])

// Style mappings
const notificationIcons = {
  success: CheckCircleIcon,
  error: XCircleIcon,
  warning: ExclamationTriangleIcon,
  info: InformationCircleIcon
}

const notificationClasses = {
  success: 'border-green-200 bg-green-50',
  error: 'border-red-200 bg-red-50',
  warning: 'border-yellow-200 bg-yellow-50',
  info: 'border-blue-200 bg-blue-50'
}

const textClasses = {
  success: 'text-green-800',
  error: 'text-red-800',
  warning: 'text-yellow-800',
  info: 'text-blue-800'
}

const focusClasses = {
  success: 'focus:ring-green-500',
  error: 'focus:ring-red-500',
  warning: 'focus:ring-yellow-500',
  info: 'focus:ring-blue-500'
}
</script>

<style scoped>
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.notification-move {
  transition: transform 0.3s ease;
}
</style>
