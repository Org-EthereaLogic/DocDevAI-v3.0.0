<template>
  <component
    :is="linkTag"
    :class="linkClasses"
    v-bind="linkAttrs"
    @click="handleClick"
    @focus="handleFocus"
    @blur="handleBlur"
    @keydown="handleKeydown"
  >
    <!-- Left icon slot -->
    <span
      v-if="$slots.iconLeft"
      class="link-icon link-icon--left"
      :class="iconClasses"
      aria-hidden="true"
    >
      <slot name="iconLeft" />
    </span>

    <!-- Link content -->
    <span class="link-content">
      <slot />
    </span>

    <!-- Right icon slot -->
    <span
      v-if="$slots.iconRight"
      class="link-icon link-icon--right"
      :class="iconClasses"
      aria-hidden="true"
    >
      <slot name="iconRight" />
    </span>

    <!-- External link indicator -->
    <span
      v-if="external && showExternalIcon"
      class="link-external-icon"
      :class="iconClasses"
      aria-hidden="true"
    >
      <svg
        class="w-3 h-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
        />
      </svg>
    </span>

    <!-- Screen reader text for external links -->
    <span v-if="external" class="sr-only">
      (opens in new tab)
    </span>
  </component>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import type { LinkProps } from '@/types/components'

// Component props
const props = defineProps({
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
  underline: {
    type: [Boolean, String] as PropType<boolean | 'hover' | 'always'>,
    default: 'hover'
  },
  color: {
    type: String as PropType<'default' | 'primary' | 'secondary' | 'muted'>,
    default: 'primary'
  },
  size: {
    type: String as PropType<'xs' | 'sm' | 'base' | 'lg' | 'xl'>,
    default: 'base'
  },
  weight: {
    type: String as PropType<'light' | 'normal' | 'medium' | 'semibold' | 'bold'>,
    default: 'medium'
  },
  disabled: {
    type: Boolean,
    default: false
  },
  showExternalIcon: {
    type: Boolean,
    default: true
  },
  ariaLabel: {
    type: String,
    default: undefined
  },
  target: {
    type: String as PropType<'_blank' | '_self' | '_parent' | '_top'>,
    default: undefined
  },
  rel: {
    type: String,
    default: undefined
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
const linkTag = computed(() => {
  if (props.disabled) return 'span'
  if (props.href) return 'a'
  if (props.to) return 'router-link'
  return 'button'
})

const isExternalLink = computed(() => {
  if (props.external) return true
  if (props.href) {
    try {
      const url = new URL(props.href, window.location.origin)
      return url.origin !== window.location.origin
    } catch {
      return false
    }
  }
  return false
})

const linkAttrs = computed(() => {
  if (props.disabled) {
    return {
      'aria-disabled': true,
      tabindex: -1
    }
  }

  if (props.href) {
    return {
      href: props.href,
      target: props.target || (isExternalLink.value ? '_blank' : undefined),
      rel: props.rel || (isExternalLink.value ? 'noopener noreferrer' : undefined),
      'aria-label': props.ariaLabel
    }
  }

  if (props.to) {
    return {
      to: props.to,
      'aria-label': props.ariaLabel
    }
  }

  return {
    type: 'button',
    'aria-label': props.ariaLabel
  }
})

// Size classes
const sizeClasses = computed(() => {
  const sizes = {
    xs: ['text-xs'],
    sm: ['text-sm'],
    base: ['text-base'],
    lg: ['text-lg'],
    xl: ['text-xl']
  }
  return sizes[props.size]
})

// Weight classes
const weightClasses = computed(() => {
  const weights = {
    light: 'font-light',
    normal: 'font-normal',
    medium: 'font-medium',
    semibold: 'font-semibold',
    bold: 'font-bold'
  }
  return weights[props.weight]
})

// Color classes
const colorClasses = computed(() => {
  if (props.disabled) {
    return ['text-secondary-400', 'cursor-not-allowed']
  }

  const colors = {
    default: [
      'text-secondary-700',
      'hover:text-secondary-900',
      'active:text-secondary-800'
    ],
    primary: [
      'text-primary-600',
      'hover:text-primary-700',
      'active:text-primary-800'
    ],
    secondary: [
      'text-secondary-600',
      'hover:text-secondary-700',
      'active:text-secondary-800'
    ],
    muted: [
      'text-secondary-500',
      'hover:text-secondary-600',
      'active:text-secondary-700'
    ]
  }
  return colors[props.color]
})

// Underline classes
const underlineClasses = computed(() => {
  if (props.disabled) return []

  if (props.underline === true || props.underline === 'always') {
    return ['underline']
  }

  if (props.underline === 'hover') {
    return ['hover:underline']
  }

  return ['no-underline']
})

// Base link classes
const baseLinkClasses = [
  'inline-flex',
  'items-center',
  'gap-1',
  'transition-colors',
  'duration-200',
  'ease-in-out',
  'focus:outline-none',
  'focus:ring-2',
  'focus:ring-primary-500',
  'focus:ring-offset-2',
  'rounded-sm'
]

// Final link classes
const linkClasses = computed(() => [
  ...baseLinkClasses,
  ...sizeClasses.value,
  weightClasses.value,
  ...colorClasses.value,
  ...underlineClasses.value
])

// Icon classes
const iconClasses = computed(() => {
  const sizes = {
    xs: ['w-3', 'h-3'],
    sm: ['w-3.5', 'h-3.5'],
    base: ['w-4', 'h-4'],
    lg: ['w-5', 'h-5'],
    xl: ['w-6', 'h-6']
  }
  return sizes[props.size]
})

// Event handlers
const handleClick = (event: MouseEvent) => {
  if (!props.disabled) {
    emit('click', event)
  }
}

const handleFocus = (event: FocusEvent) => {
  if (!props.disabled) {
    emit('focus', event)
  }
}

const handleBlur = (event: FocusEvent) => {
  if (!props.disabled) {
    emit('blur', event)
  }
}

const handleKeydown = (event: KeyboardEvent) => {
  if (!props.disabled) {
    // Support Enter and Space for button-like links
    if ((event.key === 'Enter' || event.key === ' ') && linkTag.value === 'button') {
      event.preventDefault()
      const target = event.target as HTMLElement
      target.click()
    }
    emit('keydown', event)
  }
}
</script>

<style scoped>
/* Link-specific styles */
a, button {
  text-decoration: none;
  border: none;
  background: none;
  padding: 0;
  font-family: inherit;
  cursor: pointer;
}

a:disabled,
button:disabled,
span[aria-disabled="true"] {
  pointer-events: none;
}

.link-icon--left {
  margin-right: 0.25rem;
}

.link-icon--right,
.link-external-icon {
  margin-left: 0.25rem;
}

.link-external-icon {
  opacity: 0.7;
}

/* Hover effects for external icon */
a:hover .link-external-icon,
button:hover .link-external-icon {
  opacity: 1;
}

/* Focus styles for better accessibility */
a:focus-visible,
button:focus-visible {
  outline: 2px solid theme('colors.primary.500');
  outline-offset: 2px;
  border-radius: 0.125rem;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  a, button {
    text-decoration: underline;
  }

  a:disabled,
  button:disabled,
  span[aria-disabled="true"] {
    text-decoration: none;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  a, button {
    transition: none;
  }
}

/* Print styles */
@media print {
  a, button {
    color: black !important;
    text-decoration: underline !important;
  }

  .link-external-icon {
    display: none;
  }

  /* Show URLs for external links in print */
  a[href^="http"]:after {
    content: " (" attr(href) ")";
    font-size: 0.8em;
    color: #666;
  }
}
</style>