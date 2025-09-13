<template>
  <div class="input-wrapper" :class="wrapperClasses">
    <!-- Input Element -->
    <component
      :is="multiline ? 'textarea' : 'input'"
      :id="id"
      :type="!multiline ? type : undefined"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      :required="required"
      :rows="multiline ? rows : undefined"
      :cols="multiline ? cols : undefined"
      :minlength="minlength"
      :maxlength="maxlength"
      :min="min"
      :max="max"
      :step="step"
      :autocomplete="autocomplete"
      :aria-label="ariaLabel"
      :aria-describedby="ariaDescribedby"
      :aria-invalid="error ? 'true' : 'false'"
      :class="inputClasses"
      :data-testid="testId"
      @input="handleInput"
      @change="handleChange"
      @focus="handleFocus"
      @blur="handleBlur"
      @keydown="handleKeydown"
      @keyup="handleKeyup"
      ref="inputRef"
    />

    <!-- Left Icon -->
    <span
      v-if="iconLeft"
      class="input-icon input-icon--left"
      aria-hidden="true"
    >
      <component :is="iconLeft" />
    </span>

    <!-- Right Icon / Clear Button -->
    <span
      v-if="iconRight || (clearable && modelValue)"
      class="input-icon input-icon--right"
    >
      <button
        v-if="clearable && modelValue"
        type="button"
        class="input-clear"
        :aria-label="`Clear ${ariaLabel || placeholder || 'input'}`"
        @click="handleClear"
        tabindex="-1"
      >
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
      <component v-else-if="iconRight" :is="iconRight" />
    </span>

    <!-- Loading Spinner -->
    <span
      v-if="loading"
      class="input-icon input-icon--right"
      aria-hidden="true"
    >
      <svg
        class="w-4 h-4 animate-spin"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
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
  </div>
</template>

<script setup>
import { computed, ref, nextTick } from 'vue'

const props = defineProps({
  /**
   * Input value (v-model)
   */
  modelValue: {
    type: [String, Number],
    default: ''
  },

  /**
   * Input type
   * @type {'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'search' | 'date' | 'time' | 'datetime-local'}
   */
  type: {
    type: String,
    default: 'text',
    validator: (value) => ['text', 'email', 'password', 'number', 'tel', 'url', 'search', 'date', 'time', 'datetime-local'].includes(value)
  },

  /**
   * Input size
   * @type {'sm' | 'md' | 'lg'}
   */
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
  },

  /**
   * Multiline textarea mode
   */
  multiline: {
    type: Boolean,
    default: false
  },

  /**
   * Textarea rows (multiline mode)
   */
  rows: {
    type: Number,
    default: 3
  },

  /**
   * Textarea cols (multiline mode)
   */
  cols: {
    type: Number,
    default: null
  },

  /**
   * Placeholder text
   */
  placeholder: {
    type: String,
    default: ''
  },

  /**
   * Disabled state
   */
  disabled: {
    type: Boolean,
    default: false
  },

  /**
   * Readonly state
   */
  readonly: {
    type: Boolean,
    default: false
  },

  /**
   * Required field
   */
  required: {
    type: Boolean,
    default: false
  },

  /**
   * Error state
   */
  error: {
    type: Boolean,
    default: false
  },

  /**
   * Loading state
   */
  loading: {
    type: Boolean,
    default: false
  },

  /**
   * Show clear button when value exists
   */
  clearable: {
    type: Boolean,
    default: false
  },

  /**
   * Full width input
   */
  fullWidth: {
    type: Boolean,
    default: false
  },

  /**
   * Left icon component
   */
  iconLeft: {
    type: [String, Object],
    default: null
  },

  /**
   * Right icon component
   */
  iconRight: {
    type: [String, Object],
    default: null
  },

  /**
   * Minimum length
   */
  minlength: {
    type: Number,
    default: null
  },

  /**
   * Maximum length
   */
  maxlength: {
    type: Number,
    default: null
  },

  /**
   * Minimum value (number inputs)
   */
  min: {
    type: Number,
    default: null
  },

  /**
   * Maximum value (number inputs)
   */
  max: {
    type: Number,
    default: null
  },

  /**
   * Step value (number inputs)
   */
  step: {
    type: Number,
    default: null
  },

  /**
   * Autocomplete attribute
   */
  autocomplete: {
    type: String,
    default: null
  },

  /**
   * Input ID
   */
  id: {
    type: String,
    default: ''
  },

  /**
   * Accessibility label
   */
  ariaLabel: {
    type: String,
    default: ''
  },

  /**
   * ID of element that describes this input
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

const emit = defineEmits(['update:modelValue', 'change', 'focus', 'blur', 'keydown', 'keyup', 'clear'])

// Template refs
const inputRef = ref(null)

// Reactive state
const isFocused = ref(false)

// Computed classes
const wrapperClasses = computed(() => {
  return {
    'input-wrapper--full-width': props.fullWidth,
    'input-wrapper--has-left-icon': props.iconLeft,
    'input-wrapper--has-right-icon': props.iconRight || props.clearable || props.loading,
    'input-wrapper--focused': isFocused.value,
    'input-wrapper--error': props.error,
    'input-wrapper--disabled': props.disabled,
    'input-wrapper--readonly': props.readonly,
  }
})

const inputClasses = computed(() => {
  const classes = [
    'input',
    `input--${props.size}`,
    {
      'input--error': props.error,
      'input--disabled': props.disabled,
      'input--readonly': props.readonly,
      'input--with-left-icon': props.iconLeft,
      'input--with-right-icon': props.iconRight || props.clearable || props.loading,
      'input--multiline': props.multiline,
    }
  ]
  return classes
})

// Event handlers
const handleInput = (event) => {
  emit('update:modelValue', event.target.value)
}

const handleChange = (event) => {
  emit('change', event.target.value, event)
}

const handleFocus = (event) => {
  isFocused.value = true
  emit('focus', event)
}

const handleBlur = (event) => {
  isFocused.value = false
  emit('blur', event)
}

const handleKeydown = (event) => {
  emit('keydown', event)
}

const handleKeyup = (event) => {
  emit('keyup', event)
}

const handleClear = () => {
  emit('update:modelValue', '')
  emit('clear')
  nextTick(() => {
    inputRef.value?.focus()
  })
}

// Public methods
const focus = () => {
  inputRef.value?.focus()
}

const blur = () => {
  inputRef.value?.blur()
}

const select = () => {
  inputRef.value?.select()
}

defineExpose({
  focus,
  blur,
  select,
  inputRef
})
</script>

<style scoped>
/* Input Wrapper Styles */
.input-wrapper {
  @apply relative;
}

.input-wrapper--full-width {
  @apply w-full;
}

/* Input Base Styles - Following v3.6.0 design tokens */
.input {
  @apply w-full;
  @apply border border-neutral-300;
  @apply bg-white text-neutral-900;
  @apply transition-all duration-200;
  @apply focus:outline-none;
  @apply placeholder:text-neutral-400;

  /* Focus ring for accessibility */
  @apply focus:ring-2 focus:ring-primary-500 focus:ring-offset-0 focus:border-primary-500;

  /* Motion design integration */
  transition-timing-function: theme('transitionTimingFunction.standard');
}

/* Size Variants */
.input--sm {
  @apply h-8 px-3 text-sm;
  @apply rounded-md;
}

.input--md {
  @apply h-10 px-4 text-base;
  @apply rounded-lg;
}

.input--lg {
  @apply h-12 px-5 text-lg;
  @apply rounded-lg;
}

/* Multiline Textarea */
.input--multiline {
  @apply py-3 resize-vertical;
  @apply min-h-20;
}

.input--multiline.input--sm {
  @apply py-2 min-h-16;
}

.input--multiline.input--lg {
  @apply py-4 min-h-24;
}

/* Icon Padding Adjustments */
.input--with-left-icon {
  @apply pl-10;
}

.input--with-left-icon.input--sm {
  @apply pl-8;
}

.input--with-left-icon.input--lg {
  @apply pl-12;
}

.input--with-right-icon {
  @apply pr-10;
}

.input--with-right-icon.input--sm {
  @apply pr-8;
}

.input--with-right-icon.input--lg {
  @apply pr-12;
}

/* State Variants */
.input--error {
  @apply border-status-danger-base;
  @apply focus:ring-status-danger-base focus:border-status-danger-base;
}

.input--disabled {
  @apply bg-neutral-50 text-neutral-500;
  @apply cursor-not-allowed;
  @apply border-neutral-200;
}

.input--readonly {
  @apply bg-neutral-50;
  @apply cursor-default;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .input {
    @apply bg-neutral-800 border-neutral-600 text-neutral-100;
    @apply placeholder:text-neutral-500;
  }

  .input--disabled {
    @apply bg-neutral-700 text-neutral-400 border-neutral-600;
  }

  .input--readonly {
    @apply bg-neutral-700;
  }
}

/* Icon Positioning */
.input-icon {
  @apply absolute top-1/2 -translate-y-1/2;
  @apply flex items-center justify-center;
  @apply text-neutral-400;
  @apply pointer-events-none;
}

.input-icon--left {
  @apply left-3;
}

.input-icon--right {
  @apply right-3;
}

.input--sm + .input-icon--left,
.input-wrapper--has-left-icon .input--sm ~ .input-icon--left {
  @apply left-2;
}

.input--sm + .input-icon--right,
.input-wrapper--has-right-icon .input--sm ~ .input-icon--right {
  @apply right-2;
}

.input--lg + .input-icon--left,
.input-wrapper--has-left-icon .input--lg ~ .input-icon--left {
  @apply left-4;
}

.input--lg + .input-icon--right,
.input-wrapper--has-right-icon .input--lg ~ .input-icon--right {
  @apply right-4;
}

/* Clear Button */
.input-clear {
  @apply text-neutral-400 hover:text-neutral-600;
  @apply transition-colors duration-150;
  @apply focus:outline-none focus:text-neutral-600;
  @apply pointer-events-auto;
  @apply p-0.5 rounded;
}

.input-clear:hover {
  @apply bg-neutral-100;
}

/* Wrapper State Classes */
.input-wrapper--focused .input-icon {
  @apply text-primary-500;
}

.input-wrapper--error .input-icon {
  @apply text-status-danger-base;
}

.input-wrapper--disabled .input-icon {
  @apply text-neutral-300;
}

/* High Contrast Mode Support */
@media (prefers-contrast: high) {
  .input {
    @apply border-2;
  }

  .input--error {
    @apply border-2 border-status-danger-base;
  }
}

/* Accessibility: Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
  .input {
    @apply transition-none;
  }
}

/* Print Styles */
@media print {
  .input {
    @apply border border-neutral-300 bg-transparent text-neutral-900;
  }
}
</style>
