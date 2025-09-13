<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Sidebar -->
    <AppSidebar
      :is-open="isSidebarOpen"
      :is-collapsed="isSidebarCollapsed"
      @close="closeSidebar"
      @toggle="toggleSidebarCollapse"
    />

    <!-- Main content area -->
    <div
      :class="[
        'transition-all duration-300 ease-in-out',
        isSidebarCollapsed && !isMobile
          ? 'lg:ml-16'
          : 'lg:ml-64',
        'flex flex-col min-h-screen'
      ]"
    >
      <!-- Header -->
      <AppHeader @toggle-sidebar="toggleSidebar" />

      <!-- Main content -->
      <main class="flex-1 relative overflow-hidden">
        <!-- Page content -->
        <div class="h-full">
          <Transition
            name="page"
            mode="out-in"
            enter-active-class="transition duration-300 ease-out"
            enter-from-class="transform opacity-0 translate-x-4"
            enter-to-class="transform opacity-100 translate-x-0"
            leave-active-class="transition duration-200 ease-in"
            leave-from-class="transform opacity-100 translate-x-0"
            leave-to-class="transform opacity-0 -translate-x-4"
          >
            <router-view v-slot="{ Component, route }">
              <div class="h-full">
                <component
                  :is="Component"
                  :key="route.path"
                  class="h-full"
                />
              </div>
            </router-view>
          </Transition>
        </div>

        <!-- Loading overlay -->
        <Transition
          enter-active-class="transition duration-300 ease-out"
          enter-from-class="opacity-0"
          enter-to-class="opacity-100"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="opacity-100"
          leave-to-class="opacity-0"
        >
          <div
            v-if="isLoading"
            class="absolute inset-0 bg-white dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-75 flex items-center justify-center z-40"
          >
            <div class="flex flex-col items-center space-y-4">
              <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p class="text-sm text-gray-600 dark:text-gray-400">{{ loadingText }}</p>
            </div>
          </div>
        </Transition>
      </main>

      <!-- Footer (optional) -->
      <footer
        v-if="showFooter"
        class="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 px-4 py-3"
      >
        <div class="max-w-7xl mx-auto flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
          <div class="flex items-center space-x-4">
            <span>DevDocAI v3.6.0</span>
            <span>•</span>
            <span>{{ documentsCount }} documents</span>
            <span>•</span>
            <span class="flex items-center space-x-1">
              <div :class="connectionStatusColor" class="w-2 h-2 rounded-full"></div>
              <span>{{ connectionStatus }}</span>
            </span>
          </div>

          <div class="flex items-center space-x-4">
            <button
              @click="showKeyboardShortcuts"
              class="hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              title="Keyboard shortcuts"
            >
              ⌘ Shortcuts
            </button>
            <router-link
              to="/app/help"
              class="hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
            >
              Help
            </router-link>
          </div>
        </div>
      </footer>
    </div>

    <!-- Keyboard shortcuts modal -->
    <Modal
      v-model:is-open="isShortcutsModalOpen"
      title="Keyboard Shortcuts"
      size="lg"
      :show-footer="false"
    >
      <div class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 class="font-medium text-gray-900 dark:text-white mb-2">Navigation</h4>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span>Dashboard</span>
                <kbd class="kbd">G → D</kbd>
              </div>
              <div class="flex justify-between">
                <span>Documents</span>
                <kbd class="kbd">G → O</kbd>
              </div>
              <div class="flex justify-between">
                <span>Templates</span>
                <kbd class="kbd">G → T</kbd>
              </div>
              <div class="flex justify-between">
                <span>Settings</span>
                <kbd class="kbd">G → S</kbd>
              </div>
            </div>
          </div>

          <div>
            <h4 class="font-medium text-gray-900 dark:text-white mb-2">Actions</h4>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between">
                <span>Generate Document</span>
                <kbd class="kbd">⌘ + N</kbd>
              </div>
              <div class="flex justify-between">
                <span>Search</span>
                <kbd class="kbd">⌘ + K</kbd>
              </div>
              <div class="flex justify-between">
                <span>Toggle Sidebar</span>
                <kbd class="kbd">⌘ + B</kbd>
              </div>
              <div class="flex justify-between">
                <span>Toggle Theme</span>
                <kbd class="kbd">⌘ + Shift + L</kbd>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Modal>

    <!-- Global notifications -->
    <div class="fixed bottom-4 right-4 z-50 space-y-2">
      <Transition
        v-for="notification in notifications"
        :key="notification.id"
        enter-active-class="transition duration-300 ease-out transform"
        enter-from-class="translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-2"
        enter-to-class="translate-y-0 opacity-100 sm:translate-x-0"
        leave-active-class="transition duration-100 ease-in"
        leave-from-class="opacity-100"
        leave-to-class="opacity-0"
      >
        <div
          :class="[
            'max-w-sm w-full bg-white dark:bg-gray-800 shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden',
            notification.type === 'success' && 'border-l-4 border-green-400',
            notification.type === 'error' && 'border-l-4 border-red-400',
            notification.type === 'warning' && 'border-l-4 border-yellow-400',
            notification.type === 'info' && 'border-l-4 border-blue-400'
          ]"
        >
          <div class="p-4">
            <div class="flex items-start">
              <div class="flex-shrink-0">
                <component
                  :is="getNotificationIcon(notification.type)"
                  :class="[
                    'h-5 w-5',
                    notification.type === 'success' && 'text-green-400',
                    notification.type === 'error' && 'text-red-400',
                    notification.type === 'warning' && 'text-yellow-400',
                    notification.type === 'info' && 'text-blue-400'
                  ]"
                />
              </div>
              <div class="ml-3 w-0 flex-1">
                <p class="text-sm font-medium text-gray-900 dark:text-white">
                  {{ notification.title }}
                </p>
                <p v-if="notification.message" class="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  {{ notification.message }}
                </p>
              </div>
              <div class="ml-4 flex-shrink-0 flex">
                <button
                  @click="dismissNotification(notification.id)"
                  class="rounded-md inline-flex text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <XMarkIcon class="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/stores/app'
import { useNotificationsStore } from '@/stores/notifications'

// Components
import AppHeader from '@/components/organisms/headers/AppHeader.vue'
import AppSidebar from '@/components/organisms/sidebars/AppSidebar.vue'
import Modal from '@/components/molecules/Modal.vue'

// Icons
import {
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon
} from '@heroicons/vue/24/outline'

// Stores
const appStore = useAppStore()
const notificationsStore = useNotificationsStore()
const { isSidebarOpen, isSidebarCollapsed, isLoading, loadingText } = storeToRefs(appStore)
const { notifications } = storeToRefs(notificationsStore)

// Local state
const isMobile = ref(false)
const isShortcutsModalOpen = ref(false)
const showFooter = ref(true)

// Mock data (in real app, this would come from stores)
const documentsCount = ref(42)
const connectionStatus = ref('Connected')
const connectionStatusColor = computed(() => 'bg-green-400')

// Methods
const toggleSidebar = () => {
  appStore.toggleSidebar()
}

const closeSidebar = () => {
  appStore.closeSidebar()
}

const toggleSidebarCollapse = () => {
  appStore.toggleSidebarCollapse()
}

const showKeyboardShortcuts = () => {
  isShortcutsModalOpen.value = true
}

const dismissNotification = (id: string) => {
  notificationsStore.removeNotification(id)
}

const getNotificationIcon = (type: string) => {
  const icons = {
    success: CheckCircleIcon,
    error: ExclamationCircleIcon,
    warning: ExclamationTriangleIcon,
    info: InformationCircleIcon
  }
  return icons[type] || InformationCircleIcon
}

// Keyboard shortcuts
const handleKeyboardShortcuts = (event: KeyboardEvent) => {
  // Global shortcuts
  if ((event.metaKey || event.ctrlKey)) {
    switch (event.key) {
      case 'n':
        event.preventDefault()
        // Navigate to document generation
        // router.push('/app/documents/generate')
        break
      case 'k':
        event.preventDefault()
        // Open search modal
        break
      case 'b':
        event.preventDefault()
        toggleSidebar()
        break
      case 'L':
        if (event.shiftKey) {
          event.preventDefault()
          appStore.toggleTheme()
        }
        break
    }
  }

  // Navigation shortcuts (G + key)
  if (event.key === 'g') {
    // Set flag for next key
    window.addEventListener('keydown', handleNavigationShortcuts, { once: true })
  }
}

const handleNavigationShortcuts = (event: KeyboardEvent) => {
  switch (event.key) {
    case 'd':
      // router.push('/app/dashboard')
      break
    case 'o':
      // router.push('/app/documents')
      break
    case 't':
      // router.push('/app/templates')
      break
    case 's':
      // router.push('/app/settings')
      break
  }
}

const checkMobile = () => {
  isMobile.value = window.innerWidth < 1024
  if (isMobile.value && isSidebarOpen.value) {
    closeSidebar()
  }
}

// Lifecycle
onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  document.addEventListener('keydown', handleKeyboardShortcuts)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  document.removeEventListener('keydown', handleKeyboardShortcuts)
})
</script>

<style scoped>
.kbd {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.5rem;
  background-color: #f3f4f6;
  color: #374151;
  font-size: 0.75rem;
  line-height: 1rem;
  font-family: monospace;
  border-radius: 0.25rem;
  border: 1px solid #d1d5db;
}

.dark .kbd {
  background-color: #374151;
  color: #d1d5db;
  border-color: #4b5563;
}

/* Page transition styles */
.page-enter-active,
.page-leave-active {
  transition: all 0.3s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.page-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>