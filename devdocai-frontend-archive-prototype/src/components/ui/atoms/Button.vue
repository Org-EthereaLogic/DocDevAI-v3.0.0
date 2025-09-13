<template>
  <component
    :is="tag"
    :type="tag === 'button' ? type : undefined"
    :href="tag === 'a' ? href : undefined"
    :to="tag === 'router-link' ? to : undefined"
    :disabled="disabled || loading"
    :aria-label="ariaLabel"
    :aria-describedby="ariaDescribedby"
    :class="buttonClasses"
    @click="handleClick"
    @keydown="handleKeydown"
    @focus="handleFocus"
    @blur="handleBlur"
    :data-testid="testId"
  >
    <span v-if="loading" class="button-spinner" aria-hidden="true">
      <svg
        class="animate-spin"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <circle
          class="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          stroke-width="4"
        />
        <path
          class="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
    </span>

    <span
      v-if="iconLeft && !loading"
      class="button-icon button-icon--left"
      aria-hidden="true"
    >
      <slot name="icon-left">
        <component :is="iconLeft" />
      </slot>
    </span>

    <span :class="['button-content', { 'sr-only': loading && loadingText }]">
      <slot />
    </span>

    <span v-if="loading && loadingText" class="button-loading-text">
      {{ loadingText }}
    </span>

    <span
      v-if="iconRight && !loading"
      class="button-icon button-icon--right"
      aria-hidden="true"
    >
      <slot name="icon-right">
        <component :is="iconRight" />
      </slot>
    </span>

    <span
      v-if="badge"
      class="button-badge"
      :aria-label="`${badge} notifications`"
    >
      {{ badge }}
    </span>
  </component>
</template>

<script setup>
import { computed, ref } from 'vue'

// Props with comprehensive TypeScript-style documentation
const props = defineProps({
  /**
   * Button visual variant
   * @type {'primary' | 'secondary' | 'ghost' | 'danger' | 'success' | 'warning'}
   */
  variant: {
    type: String,
    default: 'primary',
    validator: (value) => ['primary', 'secondary', 'ghost', 'danger', 'success', 'warning'].includes(value)
  },

  /**
   * Button size
   * @type {'xs' | 'sm' | 'md' | 'lg' | 'xl'}
   */
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['xs', 'sm', 'md', 'lg', 'xl'].includes(value)
  },

  /**
   * HTML element type to render
   * @type {'button' | 'a' | 'router-link'}
   */
  tag: {
    type: String,
    default: 'button',
    validator: (value) => ['button', 'a', 'router-link'].includes(value)
  },

  /**
   * Button type attribute (for button elements)
   * @type {'button' | 'submit' | 'reset'}
   */
  type: {
    type: String,
    default: 'button',
    validator: (value) => ['button', 'submit', 'reset'].includes(value)
  },

  /**
   * Disabled state
   */
  disabled: {
    type: Boolean,
    default: false
  },

  /**
   * Loading state with spinner
   */
  loading: {
    type: Boolean,
    default: false
  },

  /**
   * Text to show when loading (replaces button content)
   */
  loadingText: {
    type: String,
    default: ''
  },

  /**
   * Full width button
   */
  fullWidth: {
    type: Boolean,
    default: false
  },

  /**
   * Icon component to show on the left
   */
  iconLeft: {
    type: [String, Object],
    default: null
  },

  /**
   * Icon component to show on the right
   */
  iconRight: {
    type: [String, Object],
    default: null
  },

  /**
   * Badge number to show (for notification buttons)
   */
  badge: {
    type: [String, Number],
    default: null
  },

  /**
   * href attribute (for link buttons)
   */
  href: {
    type: String,
    default: null
  },

  /**
   * Vue Router to prop (for router-link buttons)
   */
  to: {
    type: [String, Object],
    default: null
  },

  /**
   * Accessibility label
   */
  ariaLabel: {
    type: String,
    default: ''
  },

  /**
   * ID of element that describes this button
   */
  ariaDescribedby: {
    type: String,
    default: ''
  },

  /**
   * Test ID for automated testing
   */
  testId: {
    type: String,
    default: ''
  }
})

// Emits
const emit = defineEmits(['click', 'focus', 'blur'])

// Reactive state
const isFocused = ref(false)

// Computed classes following v3.6.0 design system
const buttonClasses = computed(() => {
  const classes = [
    'button',
    `button--${props.variant}`,
    `button--${props.size}`,
    {
      'button--disabled': props.disabled,
      'button--loading': props.loading,
      'button--full-width': props.fullWidth,
      'button--focused': isFocused.value,
      'button--with-badge': props.badge,
      'button--icon-only': !$slots.default && (props.iconLeft || props.iconRight),
    }
  ]
  return classes
})

// Event handlers
const handleClick = (event) => {
  if (props.disabled || props.loading) {
    event.preventDefault()
    return
  }
  emit('click', event)
}

const handleKeydown = (event) => {
  // Handle Enter and Space keys for accessibility
  if (event.key === 'Enter' || event.key === ' ') {
    if (props.tag !== 'button') {
      event.preventDefault()
      handleClick(event)
    }
  }
}

const handleFocus = (event) => {
  isFocused.value = true
  emit('focus', event)
}

const handleBlur = (event) => {
  isFocused.value = false
  emit('blur', event)
}
</script>

<style scoped>
/* Button Base Styles - Following v3.6.0 design tokens */
.button {
  @apply relative inline-flex items-center justify-center;
  @apply font-medium text-center;
  @apply border border-transparent;
  @apply cursor-pointer select-none;
  @apply transition-all duration-200;
  @apply focus:outline-none;
  @apply disabled:cursor-not-allowed;

  /* Focus ring for accessibility */
  @apply focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2;

  /* Motion design integration */
  transition-timing-function: theme('transitionTimingFunction.standard');
}

/* Size Variants */
.button--xs {
  @apply h-6 px-2 text-xs;
  @apply rounded-md;
}

.button--sm {
  @apply h-8 px-3 text-sm;
  @apply rounded-md;
}

.button--md {
  @apply h-10 px-4 text-base;
  @apply rounded-lg;
}

.button--lg {
  @apply h-12 px-6 text-lg;
  @apply rounded-lg;
}

.button--xl {
  @apply h-14 px-8 text-xl;
  @apply rounded-xl;
}

/* Color Variants - Following v3.6.0 color system */
.button--primary {
  @apply bg-primary-600 text-white;
  @apply border-primary-600;
  @apply shadow-sm;
}

.button--primary:hover:not(:disabled) {
  @apply bg-primary-700 border-primary-700;
  @apply shadow-md;
  transform: translateY(-1px);
}

.button--primary:active:not(:disabled) {
  @apply bg-primary-800 border-primary-800;
  @apply shadow-sm;
  transform: translateY(0);
}

.button--secondary {
  @apply bg-white text-neutral-900;
  @apply border-neutral-300;
  @apply shadow-sm;
}

.button--secondary:hover:not(:disabled) {
  @apply bg-neutral-50 border-neutral-400;
  @apply shadow-md;
}

.button--secondary:active:not(:disabled) {
  @apply bg-neutral-100 border-neutral-500;
}

.button--ghost {
  @apply bg-transparent text-neutral-700;
  @apply border-transparent;
}

.button--ghost:hover:not(:disabled) {
  @apply bg-neutral-100 text-neutral-900;
}

.button--ghost:active:not(:disabled) {
  @apply bg-neutral-200;
}

.button--danger {
  @apply bg-status-danger-base text-white;
  @apply border-status-danger-base;
  @apply shadow-sm;
}

.button--danger:hover:not(:disabled) {
  @apply bg-status-danger-dark border-status-danger-dark;
  @apply shadow-md;
}

.button--success {
  @apply bg-status-success-base text-white;
  @apply border-status-success-base;
  @apply shadow-sm;
}

.button--success:hover:not(:disabled) {
  @apply bg-status-success-dark border-status-success-dark;
  @apply shadow-md;
}

.button--warning {
  @apply bg-status-warning-base text-white;
  @apply border-status-warning-base;
  @apply shadow-sm;
}

.button--warning:hover:not(:disabled) {
  @apply bg-status-warning-dark border-status-warning-dark;
  @apply shadow-md;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .button--secondary {
    @apply bg-neutral-800 text-neutral-100 border-neutral-600;
  }

  .button--secondary:hover:not(:disabled) {
    @apply bg-neutral-700 border-neutral-500;
  }

  .button--ghost {
    @apply text-neutral-300;
  }

  .button--ghost:hover:not(:disabled) {
    @apply bg-neutral-800 text-neutral-100;
  }
}

/* State Modifiers */
.button--disabled {
  @apply opacity-50 cursor-not-allowed;
  @apply shadow-none;
}

.button--loading {
  @apply cursor-wait;
}

.button--full-width {
  @apply w-full;
}

/* Icon Styles */
.button-icon {
  @apply flex items-center justify-center;
}

.button-icon--left {
  @apply mr-2;
}

.button-icon--right {
  @apply ml-2;
}

.button--icon-only .button-icon--left,
.button--icon-only .button-icon--right {
  @apply m-0;
}

/* Spinner Styles */
.button-spinner {
  @apply mr-2 flex items-center justify-center;
}

.button--icon-only .button-spinner {
  @apply m-0;
}

/* Badge Styles */
.button-badge {
  @apply absolute -top-1 -right-1;
  @apply min-w-5 h-5 px-1;
  @apply bg-status-danger-base text-white;
  @apply text-xs font-semibold;
  @apply rounded-full;
  @apply flex items-center justify-center;
}

/* Loading Text */
.button-loading-text {
  @apply flex items-center;
}

/* Focus States for High Contrast */
.button--focused {
  @apply ring-2 ring-primary-500 ring-offset-2;
}

/* Accessibility: Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
  .button {
    @apply transition-none;
  }

  .button:hover:not(:disabled) {
    transform: none;
  }
}

/* Print Styles */
@media print {
  .button {
    @apply border border-neutral-300 bg-transparent text-neutral-900;
  }
}
</style>
