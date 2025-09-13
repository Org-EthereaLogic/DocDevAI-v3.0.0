<template>
  <div class="form-field" :class="formFieldClasses">
    <!-- Label -->
    <label
      v-if="label || $slots.label"
      :for="inputId"
      class="form-field__label"
      :class="labelClasses"
    >
      <span class="form-field__label-text">
        <slot name="label">{{ label }}</slot>
        <span v-if="required" class="form-field__required" aria-label="required">
          *
        </span>
        <span v-if="optional" class="form-field__optional">
          (optional)
        </span>
      </span>
      <span
        v-if="$slots.tooltip || tooltip"
        class="form-field__tooltip"
        :title="tooltip"
      >
        <slot name="tooltip">
          <svg
            class="w-4 h-4 text-neutral-400 hover:text-neutral-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </slot>
      </span>
    </label>

    <!-- Input Container -->
    <div class="form-field__input-container">
      <slot
        name="input"
        :input-id="inputId"
        :error="hasError"
        :aria-describedby="ariaDescribedby"
      >
        <!-- Default input slot fallback -->
      </slot>

      <!-- Character count (for text inputs with maxlength) -->
      <div
        v-if="showCharCount && maxLength"
        class="form-field__char-count"
        :aria-live="charCountColor === 'danger' ? 'polite' : 'off'"
      >
        <span :class="charCountClasses">
          {{ currentLength }}/{{ maxLength }}
        </span>
      </div>
    </div>

    <!-- Help Text -->
    <div
      v-if="$slots.help || helpText || hasError"
      :id="helpId"
      class="form-field__help"
      :class="helpClasses"
      role="region"
      :aria-live="hasError ? 'polite' : 'off'"
    >
      <!-- Error messages take priority -->
      <div v-if="hasError" class="form-field__error">
        <svg
          class="form-field__error-icon"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z"
          />
        </svg>
        <span>
          <slot name="error" :error="error">
            {{ errorMessage }}
          </slot>
        </span>
      </div>

      <!-- Help text when no error -->
      <div v-else class="form-field__help-text">
        <slot name="help">
          {{ helpText }}
        </slot>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, useSlots } from 'vue'

const props = defineProps({
  /**
   * Field label text
   */
  label: {
    type: String,
    default: ''
  },

  /**
   * Help text to display below input
   */
  helpText: {
    type: String,
    default: ''
  },

  /**
   * Tooltip text for label
   */
  tooltip: {
    type: String,
    default: ''
  },

  /**
   * Error state
   */
  error: {
    type: [Boolean, String, Array],
    default: false
  },

  /**
   * Required field indicator
   */
  required: {
    type: Boolean,
    default: false
  },

  /**
   * Optional field indicator
   */
  optional: {
    type: Boolean,
    default: false
  },

  /**
   * Field size
   * @type {'sm' | 'md' | 'lg'}
   */
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },

  /**
   * Input ID for accessibility
   */
  inputId: {
    type: String,
    default: () => `input-${Math.random().toString(36).substr(2, 9)}`
  },

  /**
   * Show character count for text inputs
   */
  showCharCount: {
    type: Boolean,
    default: false
  },

  /**
   * Maximum character length (for character count)
   */
  maxLength: {
    type: Number,
    default: null
  },

  /**
   * Current text length (for character count)
   */
  currentLength: {
    type: Number,
    default: 0
  },

  /**
   * Full width form field
   */
  fullWidth: {
    type: Boolean,
    default: true
  },

  /**
   * Disabled state
   */
  disabled: {
    type: Boolean,
    default: false
  }
})

const slots = useSlots()

// Computed properties
const hasError = computed(() => {
  if (typeof props.error === 'boolean') return props.error
  if (typeof props.error === 'string') return props.error.length > 0
  if (Array.isArray(props.error)) return props.error.length > 0
  return false
})

const errorMessage = computed(() => {
  if (typeof props.error === 'string') return props.error
  if (Array.isArray(props.error)) return props.error[0]
  return ''
})

const helpId = computed(() => `${props.inputId}-help`)

const ariaDescribedby = computed(() => {
  const ids = []
  if (props.helpText || slots.help || hasError.value) {
    ids.push(helpId.value)
  }
  return ids.length > 0 ? ids.join(' ') : undefined
})

// Character count logic
const charCountColor = computed(() => {
  if (!props.maxLength) return 'neutral'
  const percentage = (props.currentLength / props.maxLength) * 100
  if (percentage >= 100) return 'danger'
  if (percentage >= 80) return 'warning'
  return 'neutral'
})

// Component classes
const formFieldClasses = computed(() => {
  return {
    [`form-field--${props.size}`]: true,
    'form-field--error': hasError.value,
    'form-field--required': props.required,
    'form-field--disabled': props.disabled,
    'form-field--full-width': props.fullWidth,
  }
})

const labelClasses = computed(() => {
  return {
    'form-field__label--required': props.required,
    'form-field__label--disabled': props.disabled,
  }
})

const helpClasses = computed(() => {
  return {
    'form-field__help--error': hasError.value,
  }
})

const charCountClasses = computed(() => {
  return {
    'text-neutral-500': charCountColor.value === 'neutral',
    'text-status-warning-base': charCountColor.value === 'warning',
    'text-status-danger-base': charCountColor.value === 'danger',
  }
})
</script>

<style scoped>
/* Form Field Container */
.form-field {
  @apply flex flex-col;
}

.form-field--full-width {
  @apply w-full;
}

/* Size Variants */
.form-field--sm {
  @apply space-y-1;
}

.form-field--md {
  @apply space-y-2;
}

.form-field--lg {
  @apply space-y-3;
}

/* Label Styles */
.form-field__label {
  @apply flex items-center justify-between;
  @apply text-sm font-medium text-neutral-700;
  @apply cursor-pointer;
}

.form-field__label-text {
  @apply flex items-center gap-1;
}

.form-field__required {
  @apply text-status-danger-base;
  @apply ml-1;
}

.form-field__optional {
  @apply text-neutral-500 text-xs font-normal;
  @apply ml-1;
}

.form-field__tooltip {
  @apply ml-2 cursor-help;
  @apply transition-colors duration-150;
}

/* Label State Variants */
.form-field__label--disabled {
  @apply text-neutral-400 cursor-not-allowed;
}

.form-field--error .form-field__label {
  @apply text-status-danger-dark;
}

/* Input Container */
.form-field__input-container {
  @apply relative;
}

/* Character Count */
.form-field__char-count {
  @apply absolute bottom-2 right-3;
  @apply text-xs;
  @apply pointer-events-none;
  @apply bg-white px-1;
}

.form-field--error .form-field__char-count {
  @apply bottom-1;
}

/* Help Text Styles */
.form-field__help {
  @apply text-sm;
  @apply transition-colors duration-200;
}

.form-field__help-text {
  @apply text-neutral-600;
}

.form-field__error {
  @apply flex items-start gap-2;
  @apply text-status-danger-base;
}

.form-field__error-icon {
  @apply w-4 h-4 flex-shrink-0;
  @apply mt-0.5;
}

/* Dark Mode Support */
@media (prefers-color-scheme: dark) {
  .form-field__label {
    @apply text-neutral-300;
  }

  .form-field__label--disabled {
    @apply text-neutral-500;
  }

  .form-field__help-text {
    @apply text-neutral-400;
  }

  .form-field__char-count {
    @apply bg-neutral-800;
  }

  .form-field--error .form-field__label {
    @apply text-status-danger-light;
  }
}

/* High Contrast Mode */
@media (prefers-contrast: high) {
  .form-field__required {
    @apply font-bold;
  }

  .form-field__error {
    @apply font-semibold;
  }
}

/* Accessibility Enhancements */
.form-field__label:focus-within {
  @apply text-primary-600;
}

/* Animation for error state changes */
.form-field__help {
  @apply transition-all duration-300;
}

.form-field__error {
  animation: shake 0.3s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}

/* Print Styles */
@media print {
  .form-field__tooltip {
    @apply hidden;
  }

  .form-field__char-count {
    @apply hidden;
  }
}
</style>
