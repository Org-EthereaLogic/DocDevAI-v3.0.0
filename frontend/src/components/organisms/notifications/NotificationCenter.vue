<template>
  <div class="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none">
    <TransitionGroup
      name="notification"
      tag="div"
      class="space-y-2"
    >
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="pointer-events-auto"
      >
        <div
          :class="[
            'max-w-sm w-full bg-white dark:bg-gray-800 shadow-lg rounded-lg overflow-hidden',
            'ring-1 ring-black ring-opacity-5',
            notification.type === 'success' && 'border-l-4 border-green-400',
            notification.type === 'error' && 'border-l-4 border-red-400',
            notification.type === 'warning' && 'border-l-4 border-yellow-400',
            notification.type === 'info' && 'border-l-4 border-blue-400'
          ]"
        >
          <div class="p-4">
            <div class="flex items-start">
              <!-- Icon -->
              <div class="flex-shrink-0">
                <component
                  :is="getIcon(notification.type)"
                  :class="[
                    'h-5 w-5',
                    notification.type === 'success' && 'text-green-400',
                    notification.type === 'error' && 'text-red-400',
                    notification.type === 'warning' && 'text-yellow-400',
                    notification.type === 'info' && 'text-blue-400'
                  ]"
                />
              </div>

              <!-- Content -->
              <div class="ml-3 w-0 flex-1">
                <p v-if="notification.title" class="text-sm font-medium text-gray-900 dark:text-white">
                  {{ notification.title }}
                </p>
                <p v-if="notification.description" class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {{ notification.description }}
                </p>

                <!-- Actions -->
                <div v-if="notification.actions && notification.actions.length > 0" class="mt-3 flex space-x-2">
                  <button
                    v-for="action in notification.actions"
                    :key="action.label"
                    @click="handleAction(notification, action)"
                    :class="[
                      'text-sm font-medium rounded-md px-2 py-1',
                      action.style === 'primary' && 'text-blue-600 hover:text-blue-500',
                      action.style === 'secondary' && 'text-gray-600 hover:text-gray-500',
                      action.style === 'danger' && 'text-red-600 hover:text-red-500'
                    ]"
                  >
                    {{ action.label }}
                  </button>
                </div>
              </div>

              <!-- Close button -->
              <div class="ml-4 flex-shrink-0 flex">
                <button
                  @click="removeNotification(notification.id)"
                  class="rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
                >
                  <XMarkIcon class="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>

          <!-- Progress bar for auto-dismiss -->
          <div
            v-if="!notification.persistent"
            class="h-1 bg-gray-200 dark:bg-gray-700"
          >
            <div
              class="h-full bg-blue-600 transition-all duration-[5000ms] ease-linear"
              :style="{ width: '0%' }"
              ref="progressBar"
            ></div>
          </div>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue';
import { useNotificationsStore } from '@/stores/notifications';
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline';

const notificationsStore = useNotificationsStore();

const notifications = computed(() => notificationsStore.notifications);

const getIcon = (type: string) => {
  switch (type) {
    case 'success': return CheckCircleIcon;
    case 'error': return ExclamationCircleIcon;
    case 'warning': return ExclamationTriangleIcon;
    case 'info':
    default: return InformationCircleIcon;
  }
};

const removeNotification = (id: string) => {
  notificationsStore.removeNotification(id);
};

const handleAction = (notification: any, action: any) => {
  if (action.action) {
    action.action();
  }
  if (!action.keepOpen) {
    removeNotification(notification.id);
  }
};

// Auto-dismiss notifications after 5 seconds
let timers: { [key: string]: NodeJS.Timeout } = {};

onMounted(() => {
  // Set up auto-dismiss for existing notifications
  notifications.value.forEach(notification => {
    if (!notification.persistent) {
      timers[notification.id] = setTimeout(() => {
        removeNotification(notification.id);
      }, 5000);
    }
  });
});

onUnmounted(() => {
  // Clear all timers
  Object.values(timers).forEach(timer => clearTimeout(timer));
});
</script>

<style scoped>
/* Notification transition animations */
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.notification-leave-to {
  transform: translateX(100%);
  opacity: 0;
}

.notification-move {
  transition: transform 0.3s ease;
}
</style>