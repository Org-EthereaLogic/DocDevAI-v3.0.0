<template>
  <div class="input-wrapper" :class="wrapperClasses">
    <!-- Label -->
    <label
      v-if="label"
      :for="inputId"
      class="input-label"
      :class="labelClasses"
    >
      {{ label }}
      <span v-if="required" class="text-danger-500 ml-1" aria-label="required">*</span>
    </label>

    <!-- Input container -->
    <div class="input-container" :class="containerClasses">
      <!-- Left icon slot -->
      <span
        v-if="$slots.iconLeft"
        class="input-icon input-icon--left"
        :class="iconClasses"
        aria-hidden="true"
      >
        <slot name="iconLeft" />
      </span>

      <!-- Input element -->
      <input
        :id="inputId"
        :type="type"
        :name="name"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled"
        :readonly="readonly"
        :required="required"
        :autocomplete="autocomplete"
        :maxlength="maxLength"
        :minlength="minLength"
        :pattern="pattern"
        :aria-label="ariaLabel"
        :aria-describedby="ariaDescribedBy"
        :aria-invalid="error || !!errorMessage"
        :aria-required="required"
        :class="inputClasses"
        @input="handleInput"
        @change="handleChange"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown="handleKeydown"
      />

      <!-- Right icon slot -->
      <span
        v-if="$slots.iconRight"
        class="input-icon input-icon--right"
        :class="iconClasses"
        aria-hidden="true"
      >
        <slot name="iconRight" />
      </span>

      <!-- Show/hide password toggle for password inputs -->
      <button
        v-if="type === 'password' && showPasswordToggle"
        type="button"
        class="input-icon input-icon--right password-toggle"
        :class="iconClasses"
        :aria-label="showPassword ? 'Hide password' : 'Show password'"
        @click="togglePasswordVisibility"
      >
        <svg
          v-if="showPassword"
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.878 9.878L3 3m6.878 6.878L21 21"
          />
        </svg>
        <svg
          v-else
          class="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
          />
        </svg>
      </button>
    </div>

    <!-- Help text -->
    <div
      v-if="helpText || errorMessage || successMessage"
      :id="`${inputId}-description`"
      class="input-description"
      :class="descriptionClasses"
    >
      <!-- Error message -->
      <div v-if="error && errorMessage" class="input-error" role="alert">
        <svg
          class="w-4 h-4 mr-1.5 flex-shrink-0"
          fill="currentColor"
          viewBox="0 0 20 20"
          aria-hidden="true"
        >
          <path
            fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
            clip-rule="evenodd"
          />
        </svg>
        {{ errorMessage }}
      </div>

      <!-- Success message -->
      <div v-else-if="success && successMessage" class="input-success">
        <svg
          class="w-4 h-4 mr-1.5 flex-shrink-0"
          fill="currentColor"
          viewBox="0 0 20 20"
          aria-hidden="true"
        >
          <path
            fill-rule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.236 4.53L8.23 10.66a.75.75 0 00-1.06 1.061l1.884 1.884a.75.75 0 001.137-.089l4-5.5z"
            clip-rule="evenodd"
          />
        </svg>
        {{ successMessage }}
      </div>

      <!-- Help text -->
      <div v-else-if="helpText" class="input-help">
        {{ helpText }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, type PropType } from 'vue'
import type { InputProps, ComponentSize, InputType } from '@/types/components'

// Component props
const props = defineProps({
  type: {
    type: String as PropType<InputType>,
    default: 'text',
    validator: (value: string) =>
      ['text', 'email', 'password', 'search', 'tel', 'url', 'number'].includes(value)
  },
  size: {
    type: String as PropType<ComponentSize>,
    default: 'md',
    validator: (value: string) => ['sm', 'md', 'lg'].includes(value)
  },
  variant: {
    type: String as PropType<'default' | 'error' | 'success'>,
    default: 'default',
    validator: (value: string) => ['default', 'error', 'success'].includes(value)
  },
  modelValue: {
    type: [String, Number],
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  readonly: {
    type: Boolean,
    default: false
  },
  required: {
    type: Boolean,
    default: false
  },
  placeholder: {
    type: String,
    default: undefined
  },
  error: {
    type: Boolean,
    default: false
  },
  errorMessage: {
    type: String,
    default: undefined
  },
  success: {
    type: Boolean,
    default: false
  },
  successMessage: {
    type: String,
    default: undefined
  },
  helpText: {
    type: String,
    default: undefined
  },
  label: {
    type: String,
    default: undefined
  },
  id: {
    type: String,
    default: undefined
  },
  name: {
    type: String,
    default: undefined
  },
  autocomplete: {
    type: String,
    default: undefined
  },
  ariaLabel: {
    type: String,
    default: undefined
  },
  ariaDescribedBy: {
    type: String,
    default: undefined
  },
  maxLength: {
    type: Number,
    default: undefined
  },
  minLength: {
    type: Number,
    default: undefined
  },
  pattern: {
    type: String,
    default: undefined
  },
  showPasswordToggle: {
    type: Boolean,
    default: true
  }
})

// Component emits
const emit = defineEmits<{
  'update:modelValue': [value: string | number]
  input: [event: Event]
  change: [event: Event]
  focus: [event: FocusEvent]
  blur: [event: FocusEvent]
  keydown: [event: KeyboardEvent]
}>()

// Reactive state
const showPassword = ref(false)

// Computed properties
const inputId = computed(() => {
  return props.id || `input-${Math.random().toString(36).substr(2, 9)}`
})

const actualType = computed(() => {
  if (props.type === 'password' && showPassword.value) {
    return 'text'
  }
  return props.type
})

const ariaDescribedBy = computed(() => {
  const descriptions = []
  if (props.ariaDescribedBy) descriptions.push(props.ariaDescribedBy)
  if (props.helpText || props.errorMessage || props.successMessage) {
    descriptions.push(`${inputId.value}-description`)
  }
  return descriptions.join(' ') || undefined
})

// Wrapper classes
const wrapperClasses = computed(() => [
  'input-wrapper',
  props.disabled && 'input-wrapper--disabled'
].filter(Boolean))

// Label classes
const labelClasses = computed(() => [
  'block',
  'text-sm',
  'font-medium',
  'mb-1',
  props.disabled ? 'text-secondary-400' : 'text-secondary-700'
])

// Container classes
const containerClasses = computed(() => [
  'relative',
  'flex',
  'items-center'
])

// Size classes for input
const sizeClasses = computed(() => {
  const sizes = {
    sm: ['h-8', 'px-3', 'text-sm'],
    md: ['h-10', 'px-3', 'text-base'],
    lg: ['h-12', 'px-4', 'text-lg']
  }
  return sizes[props.size]
})

// Variant classes
const variantClasses = computed(() => {
  if (props.error || props.errorMessage) {
    return [
      'border-danger-300',
      'text-danger-900',
      'placeholder:text-danger-300',
      'focus:border-danger-500',
      'focus:ring-danger-500'
    ]
  }

  if (props.success || props.successMessage) {
    return [
      'border-success-300',
      'text-success-900',
      'placeholder:text-success-300',
      'focus:border-success-500',
      'focus:ring-success-500'
    ]
  }

  return [
    'border-secondary-300',
    'text-secondary-900',
    'placeholder:text-secondary-400',
    'focus:border-primary-500',
    'focus:ring-primary-500'
  ]
})

// Disabled classes
const disabledClasses = computed(() => {
  if (props.disabled) {
    return [
      'bg-secondary-50',
      'text-secondary-500',
      'cursor-not-allowed',
      'placeholder:text-secondary-300'
    ]
  }
  return ['bg-white']
})

// Base input classes
const baseInputClasses = [
  'block',
  'w-full',
  'rounded-md',
  'border',
  'shadow-sm',
  'transition-colors',
  'duration-200',
  'ease-in-out',
  'focus:outline-none',
  'focus:ring-1'
]

// Icon padding classes
const iconPaddingClasses = computed(() => {
  const hasLeftIcon = !!props.$slots?.iconLeft
  const hasRightIcon = !!props.$slots?.iconRight || (props.type === 'password' && props.showPasswordToggle)

  const leftPadding = hasLeftIcon ? 'pl-10' : ''
  const rightPadding = hasRightIcon ? 'pr-10' : ''

  return [leftPadding, rightPadding].filter(Boolean)
})

// Final input classes
const inputClasses = computed(() => [
  ...baseInputClasses,
  ...sizeClasses.value,
  ...variantClasses.value,
  ...disabledClasses.value,
  ...iconPaddingClasses.value
])

// Icon classes
const iconClasses = computed(() => [
  'absolute',
  'inset-y-0',
  'flex',
  'items-center',
  'pointer-events-none',
  'text-secondary-400',
  'w-5',
  'h-5'
])

// Description classes
const descriptionClasses = computed(() => [
  'mt-1',
  'text-sm'
])

// Event handlers
const handleInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  emit('update:modelValue', target.value)
  emit('input', event)
}

const handleChange = (event: Event) => {
  emit('change', event)
}

const handleFocus = (event: FocusEvent) => {
  emit('focus', event)
}

const handleBlur = (event: FocusEvent) => {
  emit('blur', event)
}

const handleKeydown = (event: KeyboardEvent) => {
  emit('keydown', event)
}

const togglePasswordVisibility = () => {
  showPassword.value = !showPassword.value
}
</script>

<style scoped>
/* Input-specific styles */
.input-wrapper--disabled {
  opacity: 0.6;
}

.input-icon--left {
  left: 0.75rem;
}

.input-icon--right {
  right: 0.75rem;
}

.password-toggle {
  pointer-events: auto;
  cursor: pointer;
  border: none;
  background: none;
  color: inherit;
  padding: 0;
}

.password-toggle:hover {
  color: theme('colors.secondary.600');
}

.input-error {
  @apply flex items-center text-danger-600;
}

.input-success {
  @apply flex items-center text-success-600;
}

.input-help {
  @apply text-secondary-500;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .input-wrapper input {
    border-width: 2px;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .input-wrapper input {
    transition: none;
  }
}
</style>