<template>
  <span
    :class="badgeClasses"
    :aria-label="ariaLabel"
    :title="title"
    :data-testid="testId"
  >
    <span v-if="iconLeft" class="badge-icon badge-icon--left" aria-hidden="true">
      <component :is="iconLeft" />
    </span>

    <span class="badge-content">
      <slot />
    </span>

    <span v-if="iconRight" class="badge-icon badge-icon--right" aria-hidden="true">
      <component :is="iconRight" />
    </span>

    <button
      v-if="dismissible"
      type="button"
      class="badge-dismiss"
      :aria-label="`Remove ${$slots.default?.[0]?.children || 'item'}`"
      @click="handleDismiss"
    >
      <svg
        class="w-3 h-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M6 18L18 6M6 6l12 12"
        />
      </svg>
    </button>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  /**
   * Badge visual variant
   * @type {'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'primary' | 'health'}
   */
  variant: {
    type: String,
    default: 'neutral',
    validator: (value) => ['success', 'warning', 'danger', 'info', 'neutral', 'primary', 'health'].includes(value)
  },

  /**
   * Badge size
   * @type {'xs' | 'sm' | 'md' | 'lg'}
   */
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['xs', 'sm', 'md', 'lg'].includes(value)
  },

  /**
   * Badge shape
   * @type {'rounded' | 'pill' | 'square'}
   */
  shape: {
    type: String,
    default: 'rounded',
    validator: (value) => ['rounded', 'pill', 'square'].includes(value)
  },

  /**
   * Health score value (for health variant)
   * Used to automatically determine color based on thresholds
   */
  healthScore: {
    type: Number,
    default: null,
    validator: (value) => value === null || (value >= 0 && value <= 100)
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
   * Show dismiss button
   */
  dismissible: {
    type: Boolean,
    default: false
  },

  /**
   * Accessibility label
   */
  ariaLabel: {
    type: String,
    default: ''
  },

  /**
   * Tooltip title
   */
  title: {
    type: String,
    default: ''
  },

  /**
   * Test ID for automated testing
   */
  testId: {
    type: String,
    default: ''
  },

  /**
   * Dotted indicator for status
   */
  dot: {
    type: Boolean,
    default: false
  },

  /**
   * Outline style instead of filled
   */
  outline: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['dismiss'])

// Compute effective variant based on health score
const effectiveVariant = computed(() => {
  if (props.variant === 'health' && props.healthScore !== null) {
    if (props.healthScore >= 90) return 'success'      // 90%+ = Excellent (green)
    if (props.healthScore >= 85) return 'info'         // 85-89% = Good (blue)
    if (props.healthScore >= 70) return 'warning'      // 70-84% = Fair (yellow)
    return 'danger'                                     // <70% = Poor (red)
  }
  return props.variant
})

const badgeClasses = computed(() => {
  const classes = [
    'badge',
    `badge--${effectiveVariant.value}`,
    `badge--${props.size}`,
    `badge--${props.shape}`,
    {
      'badge--outline': props.outline,
      'badge--dot': props.dot,
      'badge--dismissible': props.dismissible,
      'badge--with-icon': props.iconLeft || props.iconRight,
    }
  ]
  return classes
})

const handleDismiss = (event) => {
  event.stopPropagation()
  emit('dismiss')
}
</script>

<style scoped>
/* Badge Base Styles - Following v3.6.0 design tokens */
.badge {
  @apply inline-flex items-center justify-center;
  @apply font-medium text-center;
  @apply border;
  @apply transition-all duration-200;
  @apply select-none;

  /* Motion design integration */
  transition-timing-function: theme('transitionTimingFunction.standard');
}

/* Size Variants */
.badge--xs {
  @apply h-4 px-1.5 text-2xs;
  @apply gap-1;
}

.badge--sm {
  @apply h-5 px-2 text-xs;
  @apply gap-1;
}

.badge--md {
  @apply h-6 px-2.5 text-sm;
  @apply gap-1.5;
}

.badge--lg {
  @apply h-7 px-3 text-base;
  @apply gap-2;
}

/* Shape Variants */
.badge--rounded {
  @apply rounded-md;
}

.badge--pill {
  @apply rounded-full;
}

.badge--square {
  @apply rounded-none;
}

/* Color Variants - Following v3.6.0 status colors */
.badge--success {
  @apply bg-status-success-light text-status-success-dark;
  @apply border-status-success-base;
}

.badge--warning {
  @apply bg-status-warning-light text-status-warning-dark;
  @apply border-status-warning-base;
}

.badge--danger {
  @apply bg-status-danger-light text-status-danger-dark;
  @apply border-status-danger-base;
}

.badge--info {
  @apply bg-status-info-light text-status-info-dark;
  @apply border-status-info-base;
}

.badge--primary {
  @apply bg-primary-100 text-primary-800;
  @apply border-primary-200;
}

.badge--neutral {
  @apply bg-neutral-100 text-neutral-800;
  @apply border-neutral-200;
}

/* Outline Variants */
.badge--outline.badge--success {
  @apply bg-transparent text-status-success-base;
  @apply border-status-success-base;
}

.badge--outline.badge--warning {
  @apply bg-transparent text-status-warning-base;
  @apply border-status-warning-base;
}

.badge--outline.badge--danger {
  @apply bg-transparent text-status-danger-base;
  @apply border-status-danger-base;
}

.badge--outline.badge--info {
  @apply bg-transparent text-status-info-base;
  @apply border-status-info-base;
}

.badge--outline.badge--primary {
  @apply bg-transparent text-primary-600;
  @apply border-primary-300;
}

.badge--outline.badge--neutral {
  @apply bg-transparent text-neutral-600;
  @apply border-neutral-300;
}

/* Dot Indicator */
.badge--dot {
  @apply relative pl-6;
}

.badge--dot::before {
  @apply absolute left-2 top-1/2 -translate-y-1/2;
  @apply w-2 h-2 rounded-full;
  content: '';
}

.badge--dot.badge--success::before {
  @apply bg-status-success-base;
}

.badge--dot.badge--warning::before {
  @apply bg-status-warning-base;
}

.badge--dot.badge--danger::before {
  @apply bg-status-danger-base;
}

.badge--dot.badge--info::before {
  @apply bg-status-info-base;
}

.badge--dot.badge--primary::before {
  @apply bg-primary-600;
}

.badge--dot.badge--neutral::before {
  @apply bg-neutral-500;
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
  .badge--success {
    @apply bg-status-success-dark text-status-success-light;
  }

  .badge--warning {
    @apply bg-status-warning-dark text-status-warning-light;
  }

  .badge--danger {
    @apply bg-status-danger-dark text-status-danger-light;
  }

  .badge--info {
    @apply bg-status-info-dark text-status-info-light;
  }

  .badge--primary {
    @apply bg-primary-800 text-primary-200;
  }

  .badge--neutral {
    @apply bg-neutral-800 text-neutral-200;
  }
}

/* Icon Styles */
.badge-icon {
  @apply flex items-center justify-center;
}

.badge-icon--left {
  @apply -ml-0.5;
}

.badge-icon--right {
  @apply -mr-0.5;
}

/* Dismiss Button */
.badge-dismiss {
  @apply ml-1 -mr-1 p-0.5;
  @apply rounded-full;
  @apply hover:bg-black/10 focus:bg-black/10;
  @apply transition-colors duration-150;
  @apply focus:outline-none focus:ring-1 focus:ring-current;
}

.badge-dismiss:hover {
  @apply opacity-70;
}

/* Badge Content */
.badge-content {
  @apply flex items-center;
  @apply truncate;
}

/* Special Health Score Badge */
.badge--health .badge-content::after {
  content: '%';
  @apply ml-0.5 text-xs opacity-75;
}

/* Hover Effects for Interactive Badges */
.badge--dismissible:hover {
  @apply shadow-sm;
  transform: translateY(-1px);
}

/* High Contrast Mode Support */
@media (prefers-contrast: high) {
  .badge {
    @apply border-2;
  }
}

/* Accessibility: Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
  .badge {
    @apply transition-none;
  }

  .badge--dismissible:hover {
    transform: none;
  }
}

/* Print Styles */
@media print {
  .badge {
    @apply border border-neutral-300 bg-transparent text-neutral-900;
  }
}
</style>