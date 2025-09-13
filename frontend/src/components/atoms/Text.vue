<template>
  <component
    :is="tag"
    :class="textClasses"
    :style="textStyles"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import type { TextProps } from '@/types/components'

// Component props
const props = defineProps({
  as: {
    type: String as PropType<'p' | 'span' | 'div' | 'small' | 'strong' | 'em' | 'code'>,
    default: 'p'
  },
  size: {
    type: String as PropType<'xs' | 'sm' | 'base' | 'lg' | 'xl'>,
    default: 'base'
  },
  weight: {
    type: String as PropType<'light' | 'normal' | 'medium' | 'semibold' | 'bold'>,
    default: 'normal'
  },
  color: {
    type: String as PropType<'default' | 'muted' | 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info'>,
    default: 'default'
  },
  align: {
    type: String as PropType<'left' | 'center' | 'right' | 'justify'>,
    default: 'left'
  },
  truncate: {
    type: [Boolean, Number],
    default: false
  },
  balance: {
    type: Boolean,
    default: false
  },
  mono: {
    type: Boolean,
    default: false
  },
  italic: {
    type: Boolean,
    default: false
  },
  underline: {
    type: Boolean,
    default: false
  },
  uppercase: {
    type: Boolean,
    default: false
  },
  capitalize: {
    type: Boolean,
    default: false
  }
})

// Computed properties
const tag = computed(() => {
  // Auto-select semantic tags based on props
  if (props.mono && props.as === 'p') return 'code'
  if (props.weight === 'bold' && props.as === 'p') return 'strong'
  if (props.italic && props.as === 'p') return 'em'
  if (props.size === 'xs' && props.as === 'p') return 'small'

  return props.as
})

// Size classes
const sizeClasses = computed(() => {
  const sizes = {
    xs: ['text-xs', 'leading-4'],
    sm: ['text-sm', 'leading-5'],
    base: ['text-base', 'leading-6'],
    lg: ['text-lg', 'leading-7'],
    xl: ['text-xl', 'leading-7']
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
  const colors = {
    default: 'text-secondary-900',
    muted: 'text-secondary-600',
    primary: 'text-primary-600',
    secondary: 'text-secondary-500',
    success: 'text-success-600',
    warning: 'text-warning-600',
    danger: 'text-danger-600',
    info: 'text-info-600'
  }
  return colors[props.color]
})

// Alignment classes
const alignClasses = computed(() => {
  const alignments = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
    justify: 'text-justify'
  }
  return alignments[props.align]
})

// Font family classes
const fontClasses = computed(() => {
  return props.mono ? 'font-mono' : 'font-sans'
})

// Style classes
const styleClasses = computed(() => {
  const classes = []

  if (props.italic) classes.push('italic')
  if (props.underline) classes.push('underline')
  if (props.uppercase) classes.push('uppercase')
  if (props.capitalize) classes.push('capitalize')

  return classes
})

// Truncation classes
const truncateClasses = computed(() => {
  if (props.truncate === true) {
    return ['truncate']
  }

  if (typeof props.truncate === 'number' && props.truncate > 1) {
    if (props.truncate === 2) return ['truncate-2']
    if (props.truncate === 3) return ['truncate-3']
    return [`line-clamp-${props.truncate}`]
  }

  return []
})

// Utility classes
const utilityClasses = computed(() => {
  const classes = []

  if (props.balance) {
    classes.push('text-balance')
  }

  return classes
})

// Final text classes
const textClasses = computed(() => [
  ...sizeClasses.value,
  weightClasses.value,
  colorClasses.value,
  alignClasses.value,
  fontClasses.value,
  ...styleClasses.value,
  ...truncateClasses.value,
  ...utilityClasses.value
])

// Additional styles
const textStyles = computed(() => {
  const styles: Record<string, string> = {}

  if (props.balance) {
    styles.textWrap = 'balance'
  }

  // Custom line clamp for numbers > 3
  if (typeof props.truncate === 'number' && props.truncate > 3) {
    styles.display = '-webkit-box'
    styles.webkitBoxOrient = 'vertical'
    styles.webkitLineClamp = props.truncate.toString()
    styles.overflow = 'hidden'
  }

  return styles
})
</script>

<style scoped>
/* Text-specific styles */
p, span, div, small, strong, em, code {
  margin: 0;
  font-family: inherit;
}

/* Code styling when using mono font */
code {
  background-color: theme('colors.secondary.100');
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875em;
}

/* Small text styling */
small {
  font-size: 0.875em;
  color: theme('colors.secondary.600');
}

/* Text balance fallback */
.text-balance {
  text-wrap: balance;
}

@supports not (text-wrap: balance) {
  .text-balance {
    hyphens: auto;
    word-break: break-word;
  }
}

/* Line clamp utilities for older browsers */
.line-clamp-4 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  overflow: hidden;
}

.line-clamp-5 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 5;
  overflow: hidden;
}

.line-clamp-6 {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 6;
  overflow: hidden;
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  code {
    background-color: theme('colors.secondary.200');
    border: 1px solid theme('colors.secondary.400');
  }
}

/* Print styles */
@media print {
  p, span, div, small, strong, em, code {
    color: black !important;
  }

  code {
    background-color: #f5f5f5 !important;
    border: 1px solid #ddd !important;
  }
}
</style>