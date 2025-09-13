<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Navigation -->
    <nav class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <router-link to="/" class="text-xl font-bold text-gray-900">
              DevDocAI
            </router-link>
          </div>
          <div class="flex items-center space-x-4">
            <span class="text-sm text-gray-600">Dashboard</span>
          </div>
        </div>
      </div>
    </nav>

    <!-- Dashboard Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p class="mt-2 text-gray-600">
          Welcome to DevDocAI v3.6.0 - your AI-powered documentation companion
        </p>
      </div>

      <!-- Quick Actions -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="card">
          <div class="card-body">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Generate Docs</h3>
            <p class="text-sm text-gray-600 mb-4">Create new documentation with AI assistance</p>
            <button @click="openDocumentModal" class="btn-primary w-full" :disabled="documentStore.isGenerating">
              <span v-if="documentStore.isGenerating" class="flex items-center justify-center">
                <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Generating...
              </span>
              <span v-else>New Document</span>
            </button>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Tracking Matrix</h3>
            <p class="text-sm text-gray-600 mb-4">View dependency relationships</p>
            <button @click="showComingSoon('Tracking Matrix')" class="btn-secondary w-full">
              View Matrix
            </button>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Templates</h3>
            <p class="text-sm text-gray-600 mb-4">Browse marketplace templates</p>
            <button @click="showComingSoon('Template Marketplace')" class="btn-secondary w-full">
              Browse
            </button>
          </div>
        </div>

        <div class="card">
          <div class="card-body">
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Settings</h3>
            <p class="text-sm text-gray-600 mb-4">Configure your preferences</p>
            <button @click="showComingSoon('Settings')" class="btn-secondary w-full">
              Configure
            </button>
          </div>
        </div>
      </div>

      <!-- Status Cards -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="card">
          <div class="card-header">
            <div class="flex items-center justify-between">
              <h3 class="text-lg font-semibold text-gray-900">System Health</h3>
              <button
                @click="refreshSystemHealth"
                :disabled="systemStore.isCheckingStatus"
                class="text-sm text-blue-600 hover:text-blue-700 disabled:opacity-50"
              >
                <svg v-if="systemStore.isCheckingStatus" class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                </svg>
              </button>
            </div>
          </div>
          <div class="card-body">
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-gray-900">Backend API</span>
                <div class="flex items-center">
                  <div :class="[
                    'w-3 h-3 rounded-full mr-2',
                    systemHealthStatus.backend === 'online' ? 'bg-green-500' :
                    systemHealthStatus.backend === 'error' ? 'bg-red-500' : 'bg-gray-400'
                  ]"></div>
                  <span :class="[
                    'text-sm capitalize',
                    systemHealthStatus.backend === 'online' ? 'text-green-600' :
                    systemHealthStatus.backend === 'error' ? 'text-red-600' : 'text-gray-500'
                  ]">{{ systemHealthStatus.backend }}</span>
                </div>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-gray-900">AI Services</span>
                <div class="flex items-center">
                  <div :class="[
                    'w-3 h-3 rounded-full mr-2',
                    systemHealthStatus.ai === 'available' ? 'bg-green-500' :
                    systemHealthStatus.ai === 'limited' ? 'bg-yellow-500' : 'bg-red-500'
                  ]"></div>
                  <span :class="[
                    'text-sm capitalize',
                    systemHealthStatus.ai === 'available' ? 'text-green-600' :
                    systemHealthStatus.ai === 'limited' ? 'text-yellow-600' : 'text-red-600'
                  ]">{{ systemHealthStatus.ai }}</span>
                </div>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium text-gray-900">Local Storage</span>
                <div class="flex items-center">
                  <div :class="[
                    'w-3 h-3 rounded-full mr-2',
                    systemHealthStatus.storage === 'ready' ? 'bg-green-500' : 'bg-red-500'
                  ]"></div>
                  <span :class="[
                    'text-sm capitalize',
                    systemHealthStatus.storage === 'ready' ? 'text-green-600' : 'text-red-600'
                  ]">{{ systemHealthStatus.storage }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h3 class="text-lg font-semibold text-gray-900">Recent Activity</h3>
          </div>
          <div class="card-body">
            <div v-if="!documentStore.hasDocuments" class="text-center py-8 text-gray-500">
              <svg class="w-12 h-12 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              <p class="text-sm">No recent documents</p>
              <p class="text-xs mt-1">Generate your first document to get started</p>
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="document in recentDocuments"
                :key="document.id"
                class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <div class="flex items-center space-x-3">
                  <div :class="[
                    'w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium text-white',
                    document.type === 'readme' ? 'bg-blue-500' :
                    document.type === 'api_doc' ? 'bg-green-500' :
                    document.type === 'changelog' ? 'bg-purple-500' : 'bg-gray-500'
                  ]">
                    {{ document.type.charAt(0).toUpperCase() }}
                  </div>
                  <div>
                    <p class="text-sm font-medium text-gray-900">
                      {{ document.request.project_name }}
                    </p>
                    <p class="text-xs text-gray-500 capitalize">
                      {{ document.type.replace('_', ' ') }}
                    </p>
                  </div>
                </div>
                <div class="text-right">
                  <div v-if="document.metadata.quality_score" class="text-xs text-gray-500">
                    Quality: {{ Math.round(document.metadata.quality_score * 100) }}%
                  </div>
                  <div class="text-xs text-gray-400">
                    {{ new Date(document.metadata.generated_at).toLocaleDateString() }}
                  </div>
                </div>
              </div>
              <div v-if="documentStore.documents.length > 5" class="text-center pt-2">
                <button class="text-sm text-blue-600 hover:text-blue-700">
                  View all documents
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Document Generation Modal -->
    <DocumentGenerationModal
      :show="uiStore.activeModal === 'document-generation'"
      @close="uiStore.closeModal"
      @success="onDocumentGenerated"
    />

    <!-- Document Result Modal -->
    <DocumentResultModal
      :show="showResultModal"
      :document="currentResult"
      @close="closeResultModal"
      @generate-new="generateNewDocument"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useDocumentStore, useSystemStore, useUIStore } from '@/stores'
import DocumentGenerationModal from '@/components/DocumentGenerationModal.vue'
import DocumentResultModal from '@/components/DocumentResultModal.vue'
import type { GeneratedDocument } from '@/stores/documents'

// Stores
const documentStore = useDocumentStore()
const systemStore = useSystemStore()
const uiStore = useUIStore()

// Local state
const showResultModal = ref(false)
const currentResult = ref<GeneratedDocument | null>(null)

// Computed
const recentDocuments = computed(() =>
  documentStore.documents.slice(0, 5)
)

const systemHealthStatus = computed(() => ({
  backend: systemStore.status.backend_api,
  ai: systemStore.status.ai_services,
  storage: systemStore.status.local_storage
}))

// Actions
function openDocumentModal() {
  uiStore.openModal('document-generation')
}

function onDocumentGenerated(document: GeneratedDocument) {
  currentResult.value = document
  showResultModal.value = true

  uiStore.addNotification({
    type: 'success',
    title: 'Document Generated',
    message: `Successfully generated ${document.type} for ${document.request.project_name}`
  })
}

function refreshSystemHealth() {
  systemStore.checkSystemHealth()
}

function closeResultModal() {
  showResultModal.value = false
  currentResult.value = null
}

function generateNewDocument() {
  closeResultModal()
  openDocumentModal()
}

function showComingSoon(feature: string) {
  uiStore.addNotification({
    type: 'info',
    title: 'Coming Soon',
    message: `${feature} functionality will be available in a future release.`,
    duration: 3000
  })
}

// Initialize
onMounted(() => {
  if (!systemStore.status.last_check) {
    systemStore.checkSystemHealth()
  }
})
</script>
