<template>
  <component
    :is="headingTag"
    :class="headingClasses"
    :style="headingStyles"
  >
    <slot />
  </component>
</template>

<script setup lang="ts">
import { computed, type PropType } from 'vue'
import type { HeadingLevel, HeadingProps } from '@/types/components'

// Component props
const props = defineProps({
  level: {
    type: Number as PropType<HeadingLevel>,
    required: true,
    validator: (value: number) => [1, 2, 3, 4, 5, 6].includes(value)
  },
  size: {
    type: String as PropType<'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | '5xl' | '6xl'>,
    default: undefined
  },
  weight: {
    type: String as PropType<'light' | 'normal' | 'medium' | 'semibold' | 'bold'>,
    default: 'semibold'
  },
  color: {
    type: String as PropType<'default' | 'muted' | 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info'>,
    default: 'default'
  },
  align: {
    type: String as PropType<'left' | 'center' | 'right'>,
    default: 'left'
  },
  truncate: {
    type: Boolean,
    default: false
  },
  balance: {
    type: Boolean,
    default: false
  }
})

// Computed properties
const headingTag = computed(() => `h${props.level}`)

// Default size mapping based on heading level
const defaultSizeMap = {
  1: '4xl',
  2: '3xl',
  3: '2xl',
  4: 'xl',
  5: 'lg',
  6: 'base'
} as const

const actualSize = computed(() => {
  return props.size || defaultSizeMap[props.level]
})

// Size classes
const sizeClasses = computed(() => {
  const sizes = {
    xs: ['text-xs', 'leading-4'],
    sm: ['text-sm', 'leading-5'],
    base: ['text-base', 'leading-6'],
    lg: ['text-lg', 'leading-7'],
    xl: ['text-xl', 'leading-7'],
    '2xl': ['text-2xl', 'leading-8'],
    '3xl': ['text-3xl', 'leading-9'],
    '4xl': ['text-4xl', 'leading-10'],
    '5xl': ['text-5xl', 'leading-none'],
    '6xl': ['text-6xl', 'leading-none']
  }
  return sizes[actualSize.value]
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
    right: 'text-right'
  }
  return alignments[props.align]
})

// Utility classes
const utilityClasses = computed(() => {
  const classes = []

  if (props.truncate) {
    classes.push('truncate')
  }

  if (props.balance) {
    classes.push('text-balance')
  }

  return classes
})

// Final heading classes
const headingClasses = computed(() => [
  ...sizeClasses.value,
  weightClasses.value,
  colorClasses.value,
  alignClasses.value,
  ...utilityClasses.value
])

// Additional styles for text-balance if needed
const headingStyles = computed(() => {
  const styles: Record<string, string> = {}

  if (props.balance) {
    styles.textWrap = 'balance'
  }

  return styles
})
</script>

<style scoped>
/* Heading-specific styles */
h1, h2, h3, h4, h5, h6 {
  margin: 0;
  font-family: inherit;
}

/* Text balance fallback for browsers that don't support text-wrap: balance */
.text-balance {
  text-wrap: balance;
}

@supports not (text-wrap: balance) {
  .text-balance {
    /* Fallback: Use hyphens for better text breaking */
    hyphens: auto;
    word-break: break-word;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  h1, h2, h3, h4, h5, h6 {
    font-weight: 700;
  }
}

/* Print styles */
@media print {
  h1, h2, h3, h4, h5, h6 {
    color: black !important;
    page-break-after: avoid;
    orphans: 3;
    widows: 3;
  }
}
</style>