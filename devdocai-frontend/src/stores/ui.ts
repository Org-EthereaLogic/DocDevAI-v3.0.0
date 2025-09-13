import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ModalType = 'document-generation' | 'settings' | 'template-browser' | null

export const useUIStore = defineStore('ui', () => {
  // State
  const activeModal = ref<ModalType>(null)
  const sidebarOpen = ref(false)
  const theme = ref<'light' | 'dark' | 'system'>('system')
  const notifications = ref<Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    title: string
    message: string
    autoClose?: boolean
    duration?: number
  }>>([])

  // Actions
  function openModal(modal: ModalType) {
    activeModal.value = modal
  }

  function closeModal() {
    activeModal.value = null
  }

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function setTheme(newTheme: 'light' | 'dark' | 'system') {
    theme.value = newTheme
    // Apply theme logic here
  }

  function addNotification(notification: {
    type: 'success' | 'error' | 'warning' | 'info'
    title: string
    message: string
    autoClose?: boolean
    duration?: number
  }) {
    const id = crypto.randomUUID()
    const newNotification = {
      id,
      autoClose: true,
      duration: 5000,
      ...notification
    }

    notifications.value.push(newNotification)

    if (newNotification.autoClose) {
      setTimeout(() => {
        removeNotification(id)
      }, newNotification.duration)
    }

    return id
  }

  function removeNotification(id: string) {
    const index = notifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      notifications.value.splice(index, 1)
    }
  }

  function clearAllNotifications() {
    notifications.value = []
  }

  return {
    // State
    activeModal,
    sidebarOpen,
    theme,
    notifications,

    // Actions
    openModal,
    closeModal,
    toggleSidebar,
    setTheme,
    addNotification,
    removeNotification,
    clearAllNotifications
  }
}, {
  persist: {
    key: 'devdocai-ui',
    storage: localStorage,
    paths: ['theme'] // Only persist theme preference
  }
})
