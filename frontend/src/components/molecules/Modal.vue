<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="transform opacity-0"
      enter-to-class="transform opacity-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="transform opacity-100"
      leave-to-class="transform opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 overflow-y-auto"
        aria-labelledby="modal-title"
        role="dialog"
        aria-modal="true"
        @keydown.esc="handleEscape"
      >
        <!-- Backdrop -->
        <div
          class="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0"
        >
          <Transition
            enter-active-class="transition-opacity duration-300 ease-out"
            enter-from-class="opacity-0"
            enter-to-class="opacity-100"
            leave-active-class="transition-opacity duration-200 ease-in"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
          >
            <div
              v-if="isOpen"
              class="fixed inset-0 bg-gray-500 bg-opacity-75 dark:bg-gray-900 dark:bg-opacity-75 transition-opacity"
              @click="handleBackdropClick"
              aria-hidden="true"
            ></div>
          </Transition>

          <!-- This element is to trick the browser into centering the modal contents. -->
          <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

          <!-- Modal panel -->
          <Transition
            enter-active-class="transition duration-300 ease-out"
            enter-from-class="transform opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            enter-to-class="transform opacity-100 translate-y-0 sm:scale-100"
            leave-active-class="transition duration-200 ease-in"
            leave-from-class="transform opacity-100 translate-y-0 sm:scale-100"
            leave-to-class="transform opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          >
            <div
              v-if="isOpen"
              ref="modalRef"
              :class="[
                'inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg px-4 pt-5 pb-4 text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:p-6',
                sizeClasses,
                customClass
              ]"
            >
              <!-- Header -->
              <div v-if="showHeader" class="flex items-center justify-between mb-4">
                <div class="flex items-center space-x-3">
                  <!-- Icon -->
                  <div v-if="icon" :class="iconContainerClasses">
                    <component :is="icon" :class="iconClasses" />
                  </div>

                  <!-- Title -->
                  <div>
                    <h3
                      id="modal-title"
                      class="text-lg font-medium text-gray-900 dark:text-white"
                    >
                      {{ title }}
                    </h3>
                    <p v-if="subtitle" class="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      {{ subtitle }}
                    </p>
                  </div>
                </div>

                <!-- Close button -->
                <button
                  v-if="showCloseButton"
                  @click="closeModal"
                  class="rounded-md text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 p-1"
                  aria-label="Close modal"
                >
                  <XMarkIcon class="h-6 w-6" />
                </button>
              </div>

              <!-- Content -->
              <div :class="contentClasses">
                <slot />
              </div>

              <!-- Footer -->
              <div v-if="showFooter" :class="footerClasses">
                <slot name="footer">
                  <!-- Default footer with action buttons -->
                  <div class="flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-3 space-y-3 space-y-reverse sm:space-y-0">
                    <Button
                      v-if="showCancelButton"
                      variant="secondary"
                      @click="handleCancel"
                      :disabled="loading"
                    >
                      {{ cancelText }}
                    </Button>

                    <Button
                      v-if="showConfirmButton"
                      :variant="confirmVariant"
                      @click="handleConfirm"
                      :loading="loading"
                      :disabled="confirmDisabled"
                    >
                      {{ confirmText }}
                    </Button>
                  </div>
                </slot>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import Button from '@/components/atoms/Button.vue'

// Types
export type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full'
export type ModalVariant = 'default' | 'info' | 'success' | 'warning' | 'danger'
export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'success' | 'warning'

// Props
interface Props {
  isOpen?: boolean
  title?: string
  subtitle?: string
  size?: ModalSize
  variant?: ModalVariant
  icon?: any
  showHeader?: boolean
  showFooter?: boolean
  showCloseButton?: boolean
  showCancelButton?: boolean
  showConfirmButton?: boolean
  cancelText?: string
  confirmText?: string
  confirmVariant?: ButtonVariant
  confirmDisabled?: boolean
  loading?: boolean
  persistent?: boolean
  customClass?: string
  contentClass?: string
  footerClass?: string
}

const props = withDefaults(defineProps<Props>(), {
  isOpen: false,
  title: '',
  subtitle: '',
  size: 'md',
  variant: 'default',
  showHeader: true,
  showFooter: true,
  showCloseButton: true,
  showCancelButton: true,
  showConfirmButton: true,
  cancelText: 'Cancel',
  confirmText: 'Confirm',
  confirmVariant: 'primary',
  confirmDisabled: false,
  loading: false,
  persistent: false,
  customClass: '',
  contentClass: '',
  footerClass: ''
})

// Emits
const emit = defineEmits<{
  close: []
  cancel: []
  confirm: []
  'update:isOpen': [value: boolean]
}>()

// Refs
const modalRef = ref<HTMLElement>()
const focusedElementBeforeModal = ref<HTMLElement>()

// Computed
const sizeClasses = computed(() => {
  const sizes = {
    sm: 'sm:max-w-sm sm:w-full',
    md: 'sm:max-w-md sm:w-full',
    lg: 'sm:max-w-lg sm:w-full',
    xl: 'sm:max-w-xl sm:w-full',
    '2xl': 'sm:max-w-2xl sm:w-full',
    full: 'sm:max-w-4xl sm:w-full'
  }
  return sizes[props.size]
})

const iconContainerClasses = computed(() => {
  const variants = {
    default: 'bg-gray-100 dark:bg-gray-700',
    info: 'bg-blue-100 dark:bg-blue-900',
    success: 'bg-green-100 dark:bg-green-900',
    warning: 'bg-yellow-100 dark:bg-yellow-900',
    danger: 'bg-red-100 dark:bg-red-900'
  }
  return `flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full ${variants[props.variant]}`
})

const iconClasses = computed(() => {
  const variants = {
    default: 'text-gray-600 dark:text-gray-300',
    info: 'text-blue-600 dark:text-blue-400',
    success: 'text-green-600 dark:text-green-400',
    warning: 'text-yellow-600 dark:text-yellow-400',
    danger: 'text-red-600 dark:text-red-400'
  }
  return `h-6 w-6 ${variants[props.variant]}`
})

const contentClasses = computed(() => {
  return `text-gray-700 dark:text-gray-300 ${props.contentClass}`
})

const footerClasses = computed(() => {
  return `mt-6 pt-4 border-t border-gray-200 dark:border-gray-600 ${props.footerClass}`
})

// Methods
const closeModal = () => {
  emit('close')
  emit('update:isOpen', false)
}

const handleCancel = () => {
  emit('cancel')
  closeModal()
}

const handleConfirm = () => {
  emit('confirm')
}

const handleBackdropClick = () => {
  if (!props.persistent) {
    closeModal()
  }
}

const handleEscape = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && !props.persistent) {
    closeModal()
  }
}

// Focus management
const trapFocus = (event: KeyboardEvent) => {
  if (!modalRef.value) return

  const focusableElements = modalRef.value.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )

  const firstElement = focusableElements[0] as HTMLElement
  const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement

  if (event.key === 'Tab') {
    if (event.shiftKey) {
      if (document.activeElement === firstElement) {
        lastElement.focus()
        event.preventDefault()
      }
    } else {
      if (document.activeElement === lastElement) {
        firstElement.focus()
        event.preventDefault()
      }
    }
  }
}

const setInitialFocus = async () => {
  await nextTick()
  if (modalRef.value) {
    const autofocusElement = modalRef.value.querySelector('[autofocus]') as HTMLElement
    const firstFocusableElement = modalRef.value.querySelector(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    ) as HTMLElement

    if (autofocusElement) {
      autofocusElement.focus()
    } else if (firstFocusableElement) {
      firstFocusableElement.focus()
    }
  }
}

const restoreFocus = () => {
  if (focusedElementBeforeModal.value) {
    focusedElementBeforeModal.value.focus()
  }
}

// Body scroll lock
const lockBodyScroll = () => {
  document.body.style.overflow = 'hidden'
}

const unlockBodyScroll = () => {
  document.body.style.overflow = ''
}

// Watchers
watch(
  () => props.isOpen,
  async (newValue) => {
    if (newValue) {
      focusedElementBeforeModal.value = document.activeElement as HTMLElement
      lockBodyScroll()
      await setInitialFocus()
      document.addEventListener('keydown', trapFocus)
    } else {
      unlockBodyScroll()
      restoreFocus()
      document.removeEventListener('keydown', trapFocus)
    }
  },
  { immediate: true }
)

// Lifecycle
onMounted(() => {
  if (props.isOpen) {
    lockBodyScroll()
    setInitialFocus()
  }
})

onUnmounted(() => {
  unlockBodyScroll()
  document.removeEventListener('keydown', trapFocus)
})
</script>