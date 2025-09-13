<template>
  <div class="min-h-full bg-gray-50 dark:bg-gray-900">
    <!-- Dashboard Header -->
    <div class="bg-white dark:bg-gray-800 shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="md:flex md:items-center md:justify-between">
          <!-- Page title -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center space-x-3">
              <HomeIcon class="h-8 w-8 text-blue-600 dark:text-blue-400" />
              <div>
                <Heading level="1" size="2xl" weight="bold" color="primary">
                  Dashboard
                </Heading>
                <Text size="sm" color="muted" class="mt-1">
                  Project overview and quick actions
                </Text>
              </div>
            </div>
          </div>

          <!-- Quick actions -->
          <div class="mt-4 md:mt-0 md:ml-4 flex items-center space-x-3">
            <Button
              variant="secondary"
              size="md"
              @click="refreshDashboard"
              :loading="isRefreshing"
            >
              <template #iconLeft>
                <ArrowPathIcon class="h-4 w-4" />
              </template>
              Refresh
            </Button>

            <Button
              variant="primary"
              size="md"
              @click="generateDocument"
            >
              <template #iconLeft>
                <PlusIcon class="h-4 w-4" />
              </template>
              Generate Document
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- Dashboard content -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

      <!-- Health Score Overview -->
      <div class="mb-8">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

          <!-- Overall Health Score -->
          <div class="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div class="flex items-center justify-between mb-6">
              <div>
                <Heading level="2" size="lg" weight="semibold">
                  Project Health Score
                </Heading>
                <Text size="sm" color="muted" class="mt-1">
                  Documentation quality and completeness
                </Text>
              </div>
              <div class="flex items-center space-x-2">
                <div :class="healthScoreColor" class="text-3xl font-bold">
                  {{ healthScore }}%
                </div>
                <div :class="healthBadgeColor" class="px-3 py-1 rounded-full text-sm font-medium">
                  {{ healthStatus }}
                </div>
              </div>
            </div>

            <!-- Health Score Progress -->
            <div class="mb-4">
              <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
                <div
                  :class="healthBarColor"
                  class="h-3 rounded-full transition-all duration-1000 ease-out"
                  :style="{ width: `${healthScore}%` }"
                ></div>
              </div>
            </div>

            <!-- Health Metrics -->
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div
                v-for="metric in healthMetrics"
                :key="metric.name"
                class="text-center p-3 rounded-lg bg-gray-50 dark:bg-gray-700"
              >
                <div :class="metric.color" class="text-2xl font-bold">
                  {{ metric.value }}
                </div>
                <div class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  {{ metric.name }}
                </div>
              </div>
            </div>
          </div>

          <!-- Quick Stats -->
          <div class="space-y-6">
            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div class="flex items-center space-x-3 mb-4">
                <DocumentDuplicateIcon class="h-6 w-6 text-blue-600 dark:text-blue-400" />
                <Heading level="3" size="md" weight="semibold">
                  Documents
                </Heading>
              </div>

              <div class="space-y-3">
                <div class="flex justify-between items-center">
                  <Text size="sm" color="muted">Total</Text>
                  <Text size="sm" weight="semibold">{{ stats.totalDocuments }}</Text>
                </div>
                <div class="flex justify-between items-center">
                  <Text size="sm" color="muted">Generated Today</Text>
                  <Text size="sm" weight="semibold" color="success">+{{ stats.todayDocuments }}</Text>
                </div>
                <div class="flex justify-between items-center">
                  <Text size="sm" color="muted">Templates</Text>
                  <Text size="sm" weight="semibold">{{ stats.templates }}</Text>
                </div>
              </div>
            </div>

            <div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
              <div class="flex items-center space-x-3 mb-4">
                <ChartBarIcon class="h-6 w-6 text-green-600 dark:text-green-400" />
                <Heading level="3" size="md" weight="semibold">
                  Activity
                </Heading>
              </div>

              <div class="space-y-3">
                <div class="flex justify-between items-center">
                  <Text size="sm" color="muted">This Week</Text>
                  <Text size="sm" weight="semibold">{{ stats.weeklyActivity }}</Text>
                </div>
                <div class="flex justify-between items-center">
                  <Text size="sm" color="muted">AI Generations</Text>
                  <Text size="sm" weight="semibold" color="primary">{{ stats.aiGenerations }}</Text>
                </div>
                <div class="flex justify-between items-center">
                  <Text size="sm" color="muted">Reviews</Text>
                  <Text size="sm" weight="semibold">{{ stats.reviews }}</Text>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions Grid -->
      <div class="mb-8">
        <Heading level="2" size="lg" weight="semibold" class="mb-6">
          Quick Actions
        </Heading>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div
            v-for="action in quickActions"
            :key="action.name"
            @click="action.handler"
            class="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-md transition-shadow duration-200 cursor-pointer group"
          >
            <div class="p-6">
              <div class="flex items-center space-x-4">
                <div :class="action.iconBg" class="p-3 rounded-lg group-hover:scale-105 transition-transform duration-200">
                  <component :is="action.icon" class="h-6 w-6 text-white" />
                </div>
                <div class="flex-1">
                  <Heading level="3" size="sm" weight="semibold">
                    {{ action.name }}
                  </Heading>
                  <Text size="xs" color="muted" class="mt-1">
                    {{ action.description }}
                  </Text>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Activity & Documents -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">

        <!-- Recent Documents -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div class="p-6 border-b border-gray-200 dark:border-gray-700">
            <div class="flex items-center justify-between">
              <Heading level="2" size="lg" weight="semibold">
                Recent Documents
              </Heading>
              <Link href="/app/documents" size="sm">
                View all
              </Link>
            </div>
          </div>

          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <div
              v-for="document in recentDocuments"
              :key="document.id"
              class="p-6 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
              @click="viewDocument(document)"
            >
              <div class="flex items-start space-x-4">
                <div :class="document.iconBg" class="p-2 rounded-lg flex-shrink-0">
                  <component :is="document.icon" class="h-4 w-4 text-white" />
                </div>
                <div class="flex-1 min-w-0">
                  <Text size="sm" weight="semibold" class="truncate">
                    {{ document.title }}
                  </Text>
                  <Text size="xs" color="muted" class="mt-1">
                    {{ document.type }} • {{ formatTime(document.updatedAt) }}
                  </Text>
                  <div class="flex items-center mt-2 space-x-2">
                    <div :class="getHealthBadge(document.healthScore)" class="px-2 py-1 rounded-full text-xs font-medium">
                      {{ document.healthScore }}%
                    </div>
                    <Text size="xs" color="muted">
                      {{ document.wordCount }} words
                    </Text>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Recent Activity -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div class="p-6 border-b border-gray-200 dark:border-gray-700">
            <Heading level="2" size="lg" weight="semibold">
              Recent Activity
            </Heading>
          </div>

          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <div
              v-for="activity in recentActivity"
              :key="activity.id"
              class="p-6 hover:bg-gray-50 dark:hover:bg-gray-700"
            >
              <div class="flex items-start space-x-4">
                <div :class="activity.iconBg" class="p-2 rounded-full flex-shrink-0">
                  <component :is="activity.icon" class="h-4 w-4 text-white" />
                </div>
                <div class="flex-1 min-w-0">
                  <Text size="sm">
                    {{ activity.message }}
                  </Text>
                  <Text size="xs" color="muted" class="mt-1">
                    {{ formatTime(activity.timestamp) }}
                  </Text>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Active Operations -->
      <div v-if="activeOperations.length > 0" class="mb-8">
        <Heading level="2" size="lg" weight="semibold" class="mb-6">
          Active Operations
        </Heading>

        <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div class="divide-y divide-gray-200 dark:divide-gray-700">
            <div
              v-for="operation in activeOperations"
              :key="operation.id"
              class="p-6"
            >
              <div class="flex items-center justify-between mb-3">
                <div>
                  <Text size="sm" weight="semibold">
                    {{ operation.title }}
                  </Text>
                  <Text size="xs" color="muted" class="mt-1">
                    {{ operation.description }}
                  </Text>
                </div>
                <div class="text-right">
                  <Text size="sm" weight="semibold" color="primary">
                    {{ operation.progress }}%
                  </Text>
                  <Text size="xs" color="muted">
                    {{ operation.eta }}
                  </Text>
                </div>
              </div>

              <!-- Progress bar -->
              <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  class="bg-blue-600 dark:bg-blue-400 h-2 rounded-full transition-all duration-300"
                  :style="{ width: `${operation.progress}%` }"
                ></div>
              </div>

              <Text size="xs" color="muted" class="mt-2">
                {{ operation.status }}
              </Text>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

// Components
import Button from '@/components/atoms/Button.vue'
import Heading from '@/components/atoms/Heading.vue'
import Text from '@/components/atoms/Text.vue'
import Link from '@/components/atoms/Link.vue'

// Icons
import {
  HomeIcon,
  PlusIcon,
  ArrowPathIcon,
  DocumentDuplicateIcon,
  ChartBarIcon,
  DocumentTextIcon,
  CogIcon,
  PlayIcon,
  DocumentTextIcon,
  CheckCircleIcon,
  ClockIcon,
  UserIcon,
  CloudArrowUpIcon
} from '@heroicons/vue/24/outline'

// Router
const router = useRouter()

// Local state
const isRefreshing = ref(false)

// Mock data (in real app, these would come from stores/API)
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

const healthBadgeColor = computed(() => {
  if (healthScore.value >= 85) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
  if (healthScore.value >= 70) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
  if (healthScore.value >= 50) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
  return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
})

const healthMetrics = ref([
  { name: 'Completeness', value: '92%', color: 'text-green-600 dark:text-green-400' },
  { name: 'Accuracy', value: '88%', color: 'text-blue-600 dark:text-blue-400' },
  { name: 'Consistency', value: '85%', color: 'text-blue-600 dark:text-blue-400' },
  { name: 'Freshness', value: '81%', color: 'text-yellow-600 dark:text-yellow-400' }
])

const stats = ref({
  totalDocuments: 42,
  todayDocuments: 3,
  templates: 12,
  weeklyActivity: 18,
  aiGenerations: 24,
  reviews: 8
})

const quickActions = ref([
  {
    name: 'Generate Document',
    description: 'Create with AI assistance',
    icon: DocumentTextIcon,
    iconBg: 'bg-blue-600',
    handler: () => router.push('/app/documents/generate')
  },
  {
    name: 'Browse Templates',
    description: 'Find and use templates',
    icon: DocumentTextIcon,
    iconBg: 'bg-green-600',
    handler: () => router.push('/app/templates')
  },
  {
    name: 'Batch Operations',
    description: 'Bulk document processing',
    icon: PlayIcon,
    iconBg: 'bg-purple-600',
    handler: () => router.push('/app/batch')
  },
  {
    name: 'Settings',
    description: 'Configure preferences',
    icon: CogIcon,
    iconBg: 'bg-gray-600',
    handler: () => router.push('/app/settings')
  }
])

const recentDocuments = ref([
  {
    id: 1,
    title: 'API Documentation v2.1',
    type: 'API Reference',
    healthScore: 92,
    wordCount: 2847,
    updatedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
    icon: DocumentTextIcon,
    iconBg: 'bg-blue-500'
  },
  {
    id: 2,
    title: 'User Guide - Getting Started',
    type: 'User Manual',
    healthScore: 88,
    wordCount: 1634,
    updatedAt: new Date(Date.now() - 4 * 60 * 60 * 1000),
    icon: DocumentTextIcon,
    iconBg: 'bg-green-500'
  },
  {
    id: 3,
    title: 'Architecture Overview',
    type: 'Technical Spec',
    healthScore: 75,
    wordCount: 3521,
    updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    icon: DocumentTextIcon,
    iconBg: 'bg-purple-500'
  }
])

const recentActivity = ref([
  {
    id: 1,
    message: 'Document "API Documentation v2.1" was generated',
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    icon: CheckCircleIcon,
    iconBg: 'bg-green-500'
  },
  {
    id: 2,
    message: 'Template "React Component" was imported',
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000),
    icon: CloudArrowUpIcon,
    iconBg: 'bg-blue-500'
  },
  {
    id: 3,
    message: 'Batch operation completed for 5 documents',
    timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000),
    icon: PlayIcon,
    iconBg: 'bg-purple-500'
  }
])

const activeOperations = ref([
  {
    id: 1,
    title: 'Generating Documentation Suite',
    description: 'Processing 12 files for comprehensive docs',
    progress: 65,
    eta: '3 min remaining',
    status: 'Processing changelog.md...'
  }
])

// Methods
const refreshDashboard = async () => {
  isRefreshing.value = true
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 1500))
  isRefreshing.value = false
}

const generateDocument = () => {
  router.push('/app/documents/generate')
}

const viewDocument = (document: any) => {
  router.push(`/app/documents/${document.id}`)
}

const formatTime = (date: Date) => {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))

  if (hours < 1) {
    const minutes = Math.floor(diff / (1000 * 60))
    return minutes < 1 ? 'Just now' : `${minutes}m ago`
  }

  if (hours < 24) {
    return `${hours}h ago`
  }

  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

const getHealthBadge = (score: number) => {
  if (score >= 85) return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300'
  if (score >= 70) return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
  if (score >= 50) return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300'
  return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
}

// Lifecycle
onMounted(() => {
  // Initialize dashboard data
})
</script>