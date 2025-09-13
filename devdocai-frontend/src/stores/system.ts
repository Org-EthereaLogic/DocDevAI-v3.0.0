import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiService } from '@/services/api'

export interface SystemStatus {
  backend_api: 'online' | 'offline' | 'error'
  ai_services: 'available' | 'limited' | 'unavailable'
  local_storage: 'ready' | 'error'
  version?: string
  uptime?: number
  last_check?: string
}

export const useSystemStore = defineStore('system', () => {
  // State
  const status = ref<SystemStatus>({
    backend_api: 'offline',
    ai_services: 'unavailable',
    local_storage: 'ready'
  })
  const isCheckingStatus = ref(false)
  const lastError = ref<string | null>(null)

  // Computed
  const isHealthy = computed(() =>
    status.value.backend_api === 'online' &&
    status.value.ai_services !== 'unavailable' &&
    status.value.local_storage === 'ready'
  )

  const healthScore = computed(() => {
    let score = 0
    if (status.value.backend_api === 'online') score += 40
    if (status.value.ai_services === 'available') score += 40
    else if (status.value.ai_services === 'limited') score += 20
    if (status.value.local_storage === 'ready') score += 20
    return score
  })

  // Actions
  async function checkSystemHealth() {
    isCheckingStatus.value = true
    lastError.value = null

    try {
      // Check backend API
      try {
        const healthResponse = await apiService.checkHealth()
        status.value.backend_api = 'online'

        // Try to get detailed system status
        try {
          const systemResponse = await apiService.getSystemStatus()
          status.value.version = systemResponse.version
          status.value.uptime = systemResponse.uptime
        } catch {
          // System status endpoint might not exist, but health check worked
        }
      } catch {
        status.value.backend_api = 'offline'
      }

      // Check AI services status - assume available if backend is online
      // We don't actually test document generation during health check
      // to avoid unnecessary API calls and costs
      if (status.value.backend_api === 'online') {
        status.value.ai_services = 'available'
      } else {
        status.value.ai_services = 'unavailable'
      }

      // Check local storage
      try {
        localStorage.setItem('devdocai-health-check', 'test')
        localStorage.removeItem('devdocai-health-check')
        status.value.local_storage = 'ready'
      } catch {
        status.value.local_storage = 'error'
      }

      status.value.last_check = new Date().toISOString()
    } catch (error) {
      lastError.value = error instanceof Error ? error.message : 'Unknown error'
      status.value.backend_api = 'error'
      status.value.ai_services = 'unavailable'
    } finally {
      isCheckingStatus.value = false
    }
  }

  function clearError() {
    lastError.value = null
  }

  // Auto-check on store initialization
  checkSystemHealth()

  return {
    // State
    status,
    isCheckingStatus,
    lastError,

    // Computed
    isHealthy,
    healthScore,

    // Actions
    checkSystemHealth,
    clearError
  }
})
