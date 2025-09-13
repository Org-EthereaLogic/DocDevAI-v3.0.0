<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <!-- Logo and Brand -->
          <div class="flex items-center">
            <h1 class="text-xl font-semibold text-gray-900">DevDocAI</h1>
          </div>

          <!-- Navigation -->
          <nav class="hidden md:flex space-x-8">
            <router-link
              v-for="item in navigationItems"
              :key="item.path"
              :to="item.path"
              class="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium transition-colors"
              active-class="text-indigo-600 border-b-2 border-indigo-600"
            >
              {{ item.label }}
            </router-link>
          </nav>

          <!-- User Menu -->
          <div class="flex items-center space-x-4">
            <button
              @click="toggleNotifications"
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              <span v-if="unreadCount > 0" class="absolute -mt-5 ml-4 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                {{ unreadCount }}
              </span>
            </button>

            <button
              @click="openSettings"
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main>
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificationStore } from '@/stores/notification'

const router = useRouter()
const notificationStore = useNotificationStore()

const navigationItems = [
  { path: '/dashboard', label: 'Dashboard' },
  { path: '/generate', label: 'Generate' },
  { path: '/templates', label: 'Templates' },
  { path: '/tracking', label: 'Tracking' },
  { path: '/review', label: 'Review' }
]

const unreadCount = computed(() => notificationStore.unreadCount)

const toggleNotifications = () => {
  // TODO: Implement notification panel toggle
  console.log('Toggle notifications')
}

const openSettings = () => {
  router.push('/settings')
}
</script>
