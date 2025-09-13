<template>
  <component
    :is="tag"
    :type="type"
    :disabled="disabled || loading"
    :aria-label="ariaLabel"
    :aria-describedby="ariaDescribedBy"
    :aria-disabled="disabled || loading"
    :class="buttonClasses"
    :tabindex="disabled ? -1 : 0"
    v-bind="linkAttrs"
    @click="handleClick"
    @keydown="handleKeydown"
    @focus="handleFocus"
    @blur="handleBlur"
  >
    <!-- Loading spinner -->
    <span
      v-if="loading"
      class="button-spinner"
      :class="spinnerClasses"
      aria-hidden="true"
    >
      <svg
        class="animate-spin"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
          class="opacity-25"
        />
        <path
          d="m22 12a10 10 0 0 1-10 10v-4a6 6 0 0 0 6-6z"
          fill="currentColor"
        />
      </svg>
    </span>

    <!-- Left icon slot -->
    <span
      v-if="$slots.iconLeft && !loading"
      class="button-icon button-icon--left"
      :class="iconClasses"
      aria-hidden="true"
    >
      <slot name="iconLeft" />
    </span>

    <!-- Button content -->
    <span
      v-if="$slots.default && !icon"
      class="button-content"
      :class="{ 'opacity-0': loading && !$slots.iconLeft && !$slots.iconRight }"
    >
      <slot />
    </span>

    <!-- Right icon slot -->
    <span
      v-if="$slots.iconRight && !loading"
      class="button-icon button-icon--right"
      :class="iconClasses"
      aria-hidden="true"
    >
      <slot name="iconRight" />
    </span>

    <!-- Icon-only content -->
    <span
      v-if="icon && $slots.default && !loading"
      class="button-icon-only"
      aria-hidden="true"
    >
      <slot />
    </span>

    <!-- Screen reader loading text -->
    <span v-if="loading" class="sr-only">
      {{ loadingText || 'Loading...' }}
    </span>
  </component>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import type { ButtonProps, ComponentSize, ComponentVariant } from '@/types/components'

// Component props
const props = defineProps({
  variant: {
    type: String as PropType<ComponentVariant>,
    default: 'primary',
    validator: (value: string) =>
      ['primary', 'secondary', 'tertiary', 'danger', 'success', 'warning', 'info'].includes(value)
  },
  size: {
    type: String as PropType<ComponentSize>,
    default: 'md',
    validator: (value: string) => ['sm', 'md', 'lg'].includes(value)
  },
  disabled: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  type: {
    type: String as PropType<'button' | 'submit' | 'reset'>,
    default: 'button'
  },
  fullWidth: {
    type: Boolean,
    default: false
  },
  icon: {
    type: Boolean,
    default: false
  },
  href: {
    type: String,
    default: undefined
  },
  to: {
    type: String,
    default: undefined
  },
  external: {
    type: Boolean,
    default: false
  },
  ariaLabel: {
    type: String,
    default: undefined
  },
  ariaDescribedBy: {
    type: String,
    default: undefined
  },
  loadingText: {
    type: String,
    default: 'Loading...'
  }
})

// Component emits
const emit = defineEmits<{
  click: [event: MouseEvent]
  focus: [event: FocusEvent]
  blur: [event: FocusEvent]
  keydown: [event: KeyboardEvent]
}>()

// Computed properties
const tag = computed(() => {
  if (props.href) return 'a'
  if (props.to) return 'router-link'
  return 'button'
})

const linkAttrs = computed(() => {
  if (props.href) {
    return {
      href: props.href,
      target: props.external ? '_blank' : undefined,
      rel: props.external ? 'noopener noreferrer' : undefined
    }
  }
  if (props.to) {
    return { to: props.to }
  }
  return {}
})

// Base button classes
const baseClasses = [
  'button',
  'inline-flex',
  'items-center',
  'justify-center',
  'rounded-md',
  'font-medium',
  'transition-all',
  'duration-200',
  'ease-in-out',
  'focus-ring',
  'relative',
  'select-none'
]

// Size classes
const sizeClasses = computed(() => {
  const sizes = {
    sm: props.icon
      ? ['h-8', 'w-8', 'p-1.5', 'text-sm']
      : ['h-8', 'px-3', 'py-1.5', 'text-sm', 'gap-1.5'],
    md: props.icon
      ? ['h-10', 'w-10', 'p-2', 'text-base']
      : ['h-10', 'px-4', 'py-2', 'text-base', 'gap-2'],
    lg: props.icon
      ? ['h-12', 'w-12', 'p-2.5', 'text-lg']
      : ['h-12', 'px-6', 'py-3', 'text-lg', 'gap-2.5']
  }
  return sizes[props.size]
})

// Variant classes
const variantClasses = computed(() => {
  const variants = {
    primary: [
      'bg-primary-600',
      'text-white',
      'border',
      'border-primary-600',
      'hover:bg-primary-700',
      'hover:border-primary-700',
      'active:bg-primary-800',
      'disabled:bg-primary-300',
      'disabled:border-primary-300',
      'disabled:cursor-not-allowed'
    ],
    secondary: [
      'bg-white',
      'text-secondary-700',
      'border',
      'border-secondary-300',
      'hover:bg-secondary-50',
      'hover:border-secondary-400',
      'active:bg-secondary-100',
      'disabled:bg-secondary-50',
      'disabled:text-secondary-400',
      'disabled:border-secondary-200',
      'disabled:cursor-not-allowed'
    ],
    tertiary: [
      'bg-transparent',
      'text-secondary-700',
      'border',
      'border-transparent',
      'hover:bg-secondary-100',
      'hover:text-secondary-900',
      'active:bg-secondary-200',
      'disabled:text-secondary-400',
      'disabled:cursor-not-allowed'
    ],
    danger: [
      'bg-danger-600',
      'text-white',
      'border',
      'border-danger-600',
      'hover:bg-danger-700',
      'hover:border-danger-700',
      'active:bg-danger-800',
      'disabled:bg-danger-300',
      'disabled:border-danger-300',
      'disabled:cursor-not-allowed'
    ],
    success: [
      'bg-success-600',
      'text-white',
      'border',
      'border-success-600',
      'hover:bg-success-700',
      'hover:border-success-700',
      'active:bg-success-800',
      'disabled:bg-success-300',
      'disabled:border-success-300',
      'disabled:cursor-not-allowed'
    ],
    warning: [
      'bg-warning-600',
      'text-white',
      'border',
      'border-warning-600',
      'hover:bg-warning-700',
      'hover:border-warning-700',
      'active:bg-warning-800',
      'disabled:bg-warning-300',
      'disabled:border-warning-300',
      'disabled:cursor-not-allowed'
    ],
    info: [
      'bg-info-600',
      'text-white',
      'border',
      'border-info-600',
      'hover:bg-info-700',
      'hover:border-info-700',
      'active:bg-info-800',
      'disabled:bg-info-300',
      'disabled:border-info-300',
      'disabled:cursor-not-allowed'
    ]
  }
  return variants[props.variant]
})

// Full width classes
const widthClasses = computed(() => {
  return props.fullWidth ? ['w-full'] : []
})

// Final button classes
const buttonClasses = computed(() => [
  ...baseClasses,
  ...sizeClasses.value,
  ...variantClasses.value,
  ...widthClasses.value
])

// Icon classes
const iconClasses = computed(() => {
  const sizes = {
    sm: ['w-4', 'h-4'],
    md: ['w-5', 'h-5'],
    lg: ['w-6', 'h-6']
  }
  return sizes[props.size]
})

// Spinner classes
const spinnerClasses = computed(() => {
  const sizes = {
    sm: ['w-4', 'h-4'],
    md: ['w-5', 'h-5'],
    lg: ['w-6', 'h-6']
  }
  return [
    ...sizes[props.size],
    props.icon ? 'absolute' : 'mr-2'
  ]
})

// Event handlers
const handleClick = (event: MouseEvent) => {
  if (!props.disabled && !props.loading) {
    emit('click', event)
  }
}

const handleKeydown = (event: KeyboardEvent) => {
  if (!props.disabled && !props.loading) {
    // Support Enter and Space for accessibility
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      const target = event.target as HTMLElement
      target.click()
    }
    emit('keydown', event)
  }
}

const handleFocus = (event: FocusEvent) => {
  if (!props.disabled && !props.loading) {
    emit('focus', event)
  }
}

const handleBlur = (event: FocusEvent) => {
  if (!props.disabled && !props.loading) {
    emit('blur', event)
  }
}
</script>

<style scoped>
/* Component-specific styles */
.button {
  /* Ensure consistent box-sizing */
  box-sizing: border-box;
}

.button:disabled {
  pointer-events: none;
}

.button-spinner {
  position: relative;
}

.button-icon--left {
  margin-right: 0.5rem;
}

.button-icon--right {
  margin-left: 0.5rem;
}

.button-content {
  transition: opacity 200ms ease-in-out;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .button {
    border-width: 2px;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .button {
    transition: none;
  }

  .button-spinner svg {
    animation: none;
  }
}
</style>