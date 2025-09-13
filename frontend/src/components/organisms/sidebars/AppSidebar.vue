<template>
  <aside
    :class="[
      'fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 transform transition-transform duration-300 ease-in-out',
      isOpen ? 'translate-x-0' : '-translate-x-full',
      'lg:translate-x-0 lg:static lg:inset-0'
    ]"
    aria-label="Sidebar navigation"
  >
    <!-- Sidebar content -->
    <div class="flex flex-col h-full">

      <!-- Header -->
      <div class="flex items-center justify-between h-16 px-6 border-b border-gray-200 dark:border-gray-700">
        <div class="flex items-center space-x-3">
          <div class="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <DocumentTextIcon class="w-5 h-5 text-white" />
          </div>
          <span class="text-lg font-semibold text-gray-900 dark:text-white">DevDocAI</span>
        </div>

        <!-- Close button for mobile -->
        <button
          @click="closeSidebar"
          class="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Close sidebar"
        >
          <XMarkIcon class="w-5 h-5" />
        </button>
      </div>

      <!-- Health Score Overview -->
      <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div class="mb-3">
          <h3 class="text-sm font-medium text-gray-900 dark:text-white mb-2">Project Health</h3>
          <div class="flex items-center justify-between">
            <span class="text-2xl font-bold" :class="healthScoreColor">{{ healthScore }}%</span>
            <div :class="healthIndicatorClass" class="px-2 py-1 rounded-full text-xs font-medium">
              {{ healthStatus }}
            </div>
          </div>
        </div>

        <!-- Health progress bar -->
        <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            :class="healthBarColor"
            class="h-2 rounded-full transition-all duration-300"
            :style="{ width: `${healthScore}%` }"
          ></div>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-4 py-4 space-y-2 overflow-y-auto" role="navigation" aria-label="Sidebar navigation">

        <!-- Main Navigation -->
        <div class="space-y-1">
          <h4 class="px-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            Main
          </h4>

          <router-link
            v-for="item in mainNavigation"
            :key="item.name"
            :to="item.href"
            :class="[
              'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200',
              isActiveRoute(item.href)
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                : 'text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'
            ]"
            @click="handleNavClick"
          >
            <component
              :is="item.icon"
              :class="[
                'mr-3 flex-shrink-0 h-5 w-5',
                isActiveRoute(item.href)
                  ? 'text-blue-500 dark:text-blue-400'
                  : 'text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300'
              ]"
            />
            {{ item.name }}

            <!-- Badge for active operations -->
            <span
              v-if="item.badge"
              class="ml-auto inline-block py-0.5 px-2 text-xs rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300"
            >
              {{ item.badge }}
            </span>
          </router-link>
        </div>

        <!-- Tools & Operations -->
        <div class="space-y-1 pt-4">
          <h4 class="px-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            Tools
          </h4>

          <router-link
            v-for="item in toolsNavigation"
            :key="item.name"
            :to="item.href"
            :class="[
              'group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors duration-200',
              isActiveRoute(item.href)
                ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
                : 'text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800'
            ]"
            @click="handleNavClick"
          >
            <component
              :is="item.icon"
              :class="[
                'mr-3 flex-shrink-0 h-5 w-5',
                isActiveRoute(item.href)
                  ? 'text-blue-500 dark:text-blue-400'
                  : 'text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300'
              ]"
            />
            {{ item.name }}
          </router-link>
        </div>

        <!-- Recent Activity -->
        <div class="space-y-1 pt-4">
          <h4 class="px-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
            Recent Activity
          </h4>

          <div class="space-y-2">
            <div
              v-for="activity in recentActivities"
              :key="activity.id"
              class="px-3 py-2 rounded-md hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
              @click="goToActivity(activity)"
            >
              <div class="flex items-center space-x-3">
                <div :class="activity.iconBg" class="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center">
                  <component :is="activity.icon" class="w-4 h-4 text-white" />
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {{ activity.title }}
                  </p>
                  <p class="text-xs text-gray-500 dark:text-gray-400">
                    {{ formatTimeAgo(activity.timestamp) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <!-- Active Operations -->
      <div v-if="activeOperations.length > 0" class="px-4 py-4 border-t border-gray-200 dark:border-gray-700">
        <h4 class="px-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
          Active Operations
        </h4>

        <div class="space-y-3">
          <div
            v-for="operation in activeOperations"
            :key="operation.id"
            class="px-3 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-md"
          >
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-blue-900 dark:text-blue-300">
                {{ operation.title }}
              </span>
              <span class="text-xs text-blue-700 dark:text-blue-400">
                {{ operation.progress }}%
              </span>
            </div>

            <!-- Progress bar -->
            <div class="w-full bg-blue-200 dark:bg-blue-800 rounded-full h-1.5">
              <div
                class="bg-blue-600 dark:bg-blue-400 h-1.5 rounded-full transition-all duration-300"
                :style="{ width: `${operation.progress}%` }"
              ></div>
            </div>

            <p class="text-xs text-blue-700 dark:text-blue-400 mt-1">
              {{ operation.status }}
            </p>
          </div>
        </div>
      </div>

      <!-- Version Control Status -->
      <div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-2">
            <div :class="gitStatusColor" class="w-2 h-2 rounded-full"></div>
            <span class="text-sm text-gray-600 dark:text-gray-400">{{ gitStatus }}</span>
          </div>
          <button
            @click="handleGitAction"
            class="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
          >
            {{ gitActionText }}
          </button>
        </div>

        <div v-if="gitBranch" class="mt-1">
          <span class="text-xs text-gray-500 dark:text-gray-400">
            Branch: <span class="font-mono">{{ gitBranch }}</span>
          </span>
        </div>
      </div>

      <!-- Collapse/Expand Toggle -->
      <div class="hidden lg:block px-4 py-2 border-t border-gray-200 dark:border-gray-700">
        <button
          @click="toggleSidebar"
          class="w-full flex items-center justify-center px-3 py-2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 rounded-md"
        >
          <ChevronLeftIcon v-if="!isCollapsed" class="w-4 h-4 mr-2" />
          <ChevronRightIcon v-else class="w-4 h-4 mr-2" />
          {{ isCollapsed ? 'Expand' : 'Collapse' }}
        </button>
      </div>
    </div>

    <!-- Mobile overlay -->
    <Transition
      enter-active-class="transition-opacity ease-linear duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity ease-linear duration-300"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen && isMobile"
        class="fixed inset-0 bg-gray-600 bg-opacity-75 lg:hidden"
        @click="closeSidebar"
        aria-hidden="true"
      ></div>
    </Transition>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAppStore } from '@/stores/app'

// Icons
import {
  DocumentTextIcon,
  XMarkIcon,
  HomeIcon,
  DocumentDuplicateIcon,
  ChartBarIcon,
  CogIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  CodeBracketIcon,
  CloudArrowUpIcon,
  PlayIcon,
  ClockIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'

// Props
interface Props {
  isOpen?: boolean
  isCollapsed?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isOpen: false,
  isCollapsed: false
})

// Emits
const emit = defineEmits<{
  close: []
  toggle: []
}>()

// Stores
const appStore = useAppStore()
const route = useRoute()
const router = useRouter()

// Local state
const isMobile = ref(false)

// Navigation configuration
const mainNavigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Documents', href: '/documents', icon: DocumentDuplicateIcon, badge: null },
  { name: 'Templates', href: '/templates', icon: DocumentTextIcon },
  { name: 'Tracking Matrix', href: '/tracking', icon: ChartBarIcon },
]

const toolsNavigation = [
  { name: 'Batch Operations', href: '/batch', icon: PlayIcon },
  { name: 'Version Control', href: '/version', icon: CodeBracketIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
]

// Mock data (in real app, these would come from stores)
const healthScore = ref(87)
const healthStatus = computed(() => {
  if (healthScore.value >= 85) return 'Excellent'
  if (healthScore.value >= 70) return 'Good'
  if (healthScore.value >= 50) return 'Fair'
  return 'Poor'
})

const healthScoreColor = computed(() => {
  if (healthScore.value >= 85) return 'text-green-600 dark:text-green-400'
  if (healthScore.value >= 70) return 'text-blue-600 dark:text-blue-400'
  if (healthScore.value >= 50) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
})

const healthBarColor = computed(() => {
  if (healthScore.value >= 85) return 'bg-green-500'
  if (healthScore.value >= 70) return 'bg-blue-500'
  if (healthScore.value >= 50) return 'bg-yellow-500'
  return 'bg-red-500'
})

const healthIndicatorClass = computed(() => {
  if (healthScore.value >= 85) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
  if (healthScore.value >= 70) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
  if (healthScore.value >= 50) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
  return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
})

const recentActivities = ref([
  {
    id: 1,
    title: 'README.md generated',
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    icon: DocumentTextIcon,
    iconBg: 'bg-green-500',
    href: '/documents/readme'
  },
  {
    id: 2,
    title: 'API docs updated',
    timestamp: new Date(Date.now() - 15 * 60 * 1000),
    icon: ArrowPathIcon,
    iconBg: 'bg-blue-500',
    href: '/documents/api'
  },
  {
    id: 3,
    title: 'Template imported',
    timestamp: new Date(Date.now() - 30 * 60 * 1000),
    icon: CloudArrowUpIcon,
    iconBg: 'bg-purple-500',
    href: '/templates'
  }
])

const activeOperations = ref([
  {
    id: 1,
    title: 'Generating docs suite',
    progress: 65,
    status: 'Processing changelog...'
  }
])

const gitStatus = ref('Up to date')
const gitBranch = ref('main')
const gitStatusColor = computed(() => 'bg-green-400')
const gitActionText = computed(() => 'Pull')

// Methods
const isActiveRoute = (href: string) => {
  if (href === '/dashboard') {
    return route.path === '/' || route.path === '/dashboard'
  }
  return route.path.startsWith(href)
}

const closeSidebar = () => {
  emit('close')
}

const toggleSidebar = () => {
  emit('toggle')
}

const handleNavClick = () => {
  if (isMobile.value) {
    closeSidebar()
  }
}

const goToActivity = (activity: any) => {
  router.push(activity.href)
  if (isMobile.value) {
    closeSidebar()
  }
}

const handleGitAction = () => {
  // Implement git action
  console.log('Git action:', gitActionText.value)
}

const formatTimeAgo = (timestamp: Date) => {
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

const checkMobile = () => {
  isMobile.value = window.innerWidth < 1024
}

// Lifecycle
onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>