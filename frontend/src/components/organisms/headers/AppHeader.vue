<template>
  <header
    class="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-40"
    role="banner"
    aria-label="Application header"
  >
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">

        <!-- Logo and Mobile Menu Toggle -->
        <div class="flex items-center">
          <!-- Mobile menu button -->
          <button
            @click="toggleMobileMenu"
            class="md:hidden -ml-2 mr-2 p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
            aria-expanded="false"
            aria-label="Toggle navigation menu"
          >
            <Bars3Icon v-if="!isMobileMenuOpen" class="h-6 w-6" />
            <XMarkIcon v-else class="h-6 w-6" />
          </button>

          <!-- Logo -->
          <div class="flex-shrink-0 flex items-center">
            <router-link
              to="/"
              class="flex items-center space-x-3 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md p-1"
            >
              <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <DocumentTextIcon class="w-5 h-5 text-white" />
              </div>
              <span class="text-xl font-semibold text-gray-900 dark:text-white">
                DevDocAI
              </span>
            </router-link>
          </div>
        </div>

        <!-- Desktop Navigation -->
        <nav class="hidden md:flex md:space-x-8" role="navigation" aria-label="Main navigation">
          <router-link
            v-for="item in navigationItems"
            :key="item.name"
            :to="item.href"
            :class="[
              'inline-flex items-center px-1 pt-1 text-sm font-medium border-b-2 transition-colors duration-200',
              isActiveRoute(item.href)
                ? 'border-blue-500 text-gray-900 dark:text-white'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-300 dark:hover:text-gray-100'
            ]"
            :aria-current="isActiveRoute(item.href) ? 'page' : undefined"
          >
            <component :is="item.icon" class="w-4 h-4 mr-2" />
            {{ item.name }}
          </router-link>
        </nav>

        <!-- Right side actions -->
        <div class="flex items-center space-x-4">

          <!-- Search (Desktop) -->
          <div class="hidden lg:block relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <MagnifyingGlassIcon class="h-4 w-4 text-gray-400" />
            </div>
            <input
              v-model="searchQuery"
              type="search"
              placeholder="Search documents..."
              class="block w-64 pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-800 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
              @keyup.enter="handleSearch"
            />
          </div>

          <!-- Notifications -->
          <div class="relative">
            <button
              @click="toggleNotifications"
              class="p-2 text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              :aria-expanded="isNotificationsOpen"
              aria-label="View notifications"
            >
              <BellIcon class="h-6 w-6" />
              <span
                v-if="unreadNotifications > 0"
                class="absolute top-0 right-0 block h-2.5 w-2.5 rounded-full bg-red-400 ring-2 ring-white dark:ring-gray-900"
                :aria-label="`${unreadNotifications} unread notifications`"
              ></span>
            </button>

            <!-- Notifications Dropdown -->
            <Transition
              enter-active-class="transition ease-out duration-200"
              enter-from-class="transform opacity-0 scale-95"
              enter-to-class="transform opacity-100 scale-100"
              leave-active-class="transition ease-in duration-75"
              leave-from-class="transform opacity-100 scale-100"
              leave-to-class="transform opacity-0 scale-95"
            >
              <div
                v-if="isNotificationsOpen"
                class="absolute right-0 mt-2 w-80 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50"
                role="menu"
              >
                <div class="p-4 border-b border-gray-100 dark:border-gray-700">
                  <h3 class="text-sm font-medium text-gray-900 dark:text-white">Notifications</h3>
                </div>
                <div class="max-h-64 overflow-y-auto">
                  <div v-if="notifications.length === 0" class="p-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                    No notifications
                  </div>
                  <div
                    v-for="notification in notifications"
                    :key="notification.id"
                    class="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-700 last:border-0"
                  >
                    <p class="text-sm text-gray-900 dark:text-white">{{ notification.message }}</p>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">{{ formatTime(notification.timestamp) }}</p>
                  </div>
                </div>
              </div>
            </Transition>
          </div>

          <!-- Theme Toggle -->
          <button
            @click="toggleTheme"
            class="p-2 text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
          >
            <SunIcon v-if="isDark" class="h-5 w-5" />
            <MoonIcon v-else class="h-5 w-5" />
          </button>

          <!-- User Menu -->
          <div class="relative">
            <button
              @click="toggleUserMenu"
              class="flex items-center space-x-3 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              :aria-expanded="isUserMenuOpen"
              aria-label="User account menu"
            >
              <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                <UserIcon class="w-5 h-5 text-white" />
              </div>
              <ChevronDownIcon class="hidden md:block w-4 h-4 text-gray-400" />
            </button>

            <!-- User Dropdown -->
            <Transition
              enter-active-class="transition ease-out duration-200"
              enter-from-class="transform opacity-0 scale-95"
              enter-to-class="transform opacity-100 scale-100"
              leave-active-class="transition ease-in duration-75"
              leave-from-class="transform opacity-100 scale-100"
              leave-to-class="transform opacity-0 scale-95"
            >
              <div
                v-if="isUserMenuOpen"
                class="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50"
                role="menu"
              >
                <div class="p-4 border-b border-gray-100 dark:border-gray-700">
                  <p class="text-sm font-medium text-gray-900 dark:text-white">User</p>
                  <p class="text-sm text-gray-500 dark:text-gray-400">Local Mode</p>
                </div>
                <div class="py-1">
                  <router-link
                    v-for="item in userMenuItems"
                    :key="item.name"
                    :to="item.href"
                    class="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    role="menuitem"
                    @click="closeAllMenus"
                  >
                    <component :is="item.icon" class="w-4 h-4 mr-3" />
                    {{ item.name }}
                  </router-link>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>

    <!-- Mobile Navigation -->
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="transform scale-95 opacity-0"
      enter-to-class="transform scale-100 opacity-100"
      leave-active-class="transition duration-75 ease-in"
      leave-from-class="transform scale-100 opacity-100"
      leave-to-class="transform scale-95 opacity-0"
    >
      <div v-if="isMobileMenuOpen" class="md:hidden border-t border-gray-200 dark:border-gray-700">
        <div class="px-2 pt-2 pb-3 space-y-1 bg-white dark:bg-gray-900">

          <!-- Mobile Search -->
          <div class="px-3 py-2">
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon class="h-4 w-4 text-gray-400" />
              </div>
              <input
                v-model="searchQuery"
                type="search"
                placeholder="Search documents..."
                class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white dark:bg-gray-800 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                @keyup.enter="handleSearch"
              />
            </div>
          </div>

          <!-- Mobile Navigation Links -->
          <router-link
            v-for="item in navigationItems"
            :key="item.name"
            :to="item.href"
            :class="[
              'flex items-center px-3 py-2 rounded-md text-base font-medium',
              isActiveRoute(item.href)
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'
            ]"
            @click="closeMobileMenu"
          >
            <component :is="item.icon" class="w-5 h-5 mr-3" />
            {{ item.name }}
          </router-link>
        </div>
      </div>
    </Transition>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/stores/app'
import { useNotificationsStore } from '@/stores/notifications'

// Icons
import {
  Bars3Icon,
  XMarkIcon,
  DocumentTextIcon,
  HomeIcon,
  DocumentDuplicateIcon,
  ChartBarIcon,
  CogIcon,
  MagnifyingGlassIcon,
  BellIcon,
  SunIcon,
  MoonIcon,
  UserIcon,
  ChevronDownIcon,
  QuestionMarkCircleIcon,
  ArrowRightOnRectangleIcon
} from '@heroicons/vue/24/outline'

// Stores
const appStore = useAppStore()
const notificationsStore = useNotificationsStore()
const { isDark } = storeToRefs(appStore)
const { notifications, unreadCount: unreadNotifications } = storeToRefs(notificationsStore)

// Router
const route = useRoute()

// Local state
const isMobileMenuOpen = ref(false)
const isNotificationsOpen = ref(false)
const isUserMenuOpen = ref(false)
const searchQuery = ref('')

// Navigation configuration
const navigationItems = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Documents', href: '/documents', icon: DocumentDuplicateIcon },
  { name: 'Templates', href: '/templates', icon: DocumentTextIcon },
  { name: 'Tracking', href: '/tracking', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
]

const userMenuItems = [
  { name: 'Settings', href: '/settings', icon: CogIcon },
  { name: 'Help', href: '/help', icon: QuestionMarkCircleIcon },
  { name: 'Sign Out', href: '/logout', icon: ArrowRightOnRectangleIcon },
]

// Computed
const isActiveRoute = (href: string) => {
  if (href === '/dashboard') {
    return route.path === '/' || route.path === '/dashboard'
  }
  return route.path.startsWith(href)
}

// Methods
const toggleMobileMenu = () => {
  isMobileMenuOpen.value = !isMobileMenuOpen.value
  if (isMobileMenuOpen.value) {
    isNotificationsOpen.value = false
    isUserMenuOpen.value = false
  }
}

const toggleNotifications = () => {
  isNotificationsOpen.value = !isNotificationsOpen.value
  if (isNotificationsOpen.value) {
    isMobileMenuOpen.value = false
    isUserMenuOpen.value = false
  }
}

const toggleUserMenu = () => {
  isUserMenuOpen.value = !isUserMenuOpen.value
  if (isUserMenuOpen.value) {
    isMobileMenuOpen.value = false
    isNotificationsOpen.value = false
  }
}

const toggleTheme = () => {
  appStore.toggleTheme()
}

const closeMobileMenu = () => {
  isMobileMenuOpen.value = false
}

const closeAllMenus = () => {
  isMobileMenuOpen.value = false
  isNotificationsOpen.value = false
  isUserMenuOpen.value = false
}

const handleSearch = () => {
  if (searchQuery.value.trim()) {
    // Implement search functionality
    console.log('Searching for:', searchQuery.value)
    closeAllMenus()
  }
}

const formatTime = (timestamp: Date) => {
  const now = new Date()
  const diff = now.getTime() - timestamp.getTime()
  const minutes = Math.floor(diff / 60000)

  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`

  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

// Click outside handler
const handleClickOutside = (event: Event) => {
  const target = event.target as Element
  if (!target.closest('.relative')) {
    closeAllMenus()
  }
}

// Lifecycle
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>