# DevDocAI v3.6.0 Design System

A comprehensive design token system extracted from DevDocAI v3.6.0 mockups and wireframes, providing a consistent visual language for all Vue 3 components.

## Overview

This design system implements the complete visual specifications from `docs/02-design/mockups/DESIGN-devdocai-mockups.md`, ensuring pixel-perfect consistency across all UI components while maintaining WCAG 2.1 AA accessibility compliance.

## Architecture

```
design-tokens.ts          # Master design token definitions
tailwind.config.ts         # Tailwind CSS configuration
src/
├── composables/
│   └── useDesignSystem.ts # Vue 3 design system composable
├── styles/
│   └── design-system.css  # Base styles and utilities
└── components/
    └── DesignSystemExample.vue # Complete usage examples
```

## Quick Start

### 1. Import Design Tokens

```typescript
// Import all tokens
import { designTokens, themes } from './design-tokens';

// Import specific categories
import { colors, typography, spacing, motion } from './design-tokens';

// TypeScript support
import type { DesignTokens, ColorPalette, ThemeMode } from './design-tokens';
```

### 2. Use Vue 3 Composable

```vue
<script setup lang="ts">
import { useDesignSystem } from '@/composables/useDesignSystem';

const {
  currentTheme,
  setTheme,
  toggleTheme,
  colors,
  getHealthColor,
  formatHealthScore,
  isMobile,
  shouldAnimate
} = useDesignSystem();
</script>

<template>
  <div :class="getHealthClass(87)">
    Health Score: {{ formatHealthScore(87) }}
  </div>
</template>
```

### 3. Use Tailwind Classes

```vue
<template>
  <!-- Semantic colors -->
  <button class="btn-primary btn-md">Primary Action</button>
  <div class="health-excellent">95% Health Score</div>

  <!-- Responsive design -->
  <div class="grid grid-cols-1 tablet:grid-cols-2 desktop:grid-cols-3">
    <!-- Content -->
  </div>

  <!-- Motion with accessibility -->
  <div class="motion-safe:animate-fade-in reduce-motion:animate-none">
    Animated content
  </div>
</template>
```

## Core Features

### 🎨 Color System

**Semantic Colors**: Success, warning, danger, info with full shade ranges
```typescript
colors.semantic.success[500] // #10b981
colors.semantic.warning[500] // #f59e0b
colors.semantic.danger[500]  // #ef4444
colors.semantic.info[500]    // #3b82f6
```

**Health Score Colors**: DevDocAI-specific quality indicators
```typescript
colors.health.excellent // 85%+ (green)
colors.health.good      // 70-84% (yellow)
colors.health.poor      // <70% (red)
```

**Theme Support**: Light, dark, and high-contrast themes
```css
.light { /* Light theme variables */ }
.dark { /* Dark theme variables */ }
.high-contrast { /* High contrast theme */ }
```

### 📝 Typography

**Font Families**:
- **Sans**: Inter (primary UI font)
- **Mono**: JetBrains Mono (code and technical content)
- **Dyslexic**: OpenDyslexic (accessibility option)

**Scale**: Complete font size scale with line heights
```css
text-xs    /* 12px */
text-sm    /* 14px */
text-base  /* 16px - body text */
text-lg    /* 18px */
text-xl    /* 20px */
text-2xl   /* 24px - headings */
text-3xl   /* 30px */
text-4xl   /* 36px */
text-5xl   /* 48px - hero text */
```

### 📏 Spacing System

**8px Base Grid**: Consistent spacing throughout the interface
```css
space-2   /* 8px - base unit */
space-4   /* 16px */
space-6   /* 24px */
space-8   /* 32px */
space-12  /* 48px */
space-16  /* 64px */
```

### 📱 Responsive Breakpoints

**Mobile-First Approach**:
```css
mobile:    375px  /* Mobile phones */
tablet:    768px  /* Tablets */
desktop:   1024px /* Laptops */
wide:      1280px /* Large screens */
ultrawide: 1536px /* Ultra-wide displays */
```

### 🎬 Motion Design

**Timing Standards** (from mockups):
```css
duration-micro:   100ms /* Hover, focus */
duration-fast:    150ms /* Button highlights */
duration-normal:  200ms /* Tab transitions */
duration-medium:  300ms /* Modal enter/exit */
duration-slow:    400ms /* Complex animations */
```

**Easing Functions**:
```css
easing-standard:   cubic-bezier(0.4, 0, 0.2, 1)      /* Standard */
easing-decelerate: cubic-bezier(0, 0, 0.2, 1)        /* Entering */
easing-accelerate: cubic-bezier(0.4, 0, 1, 1)        /* Exiting */
easing-spring:     cubic-bezier(0.68, -0.55, 0.265, 1.55) /* Playful */
```

## Component System

### Buttons

```vue
<template>
  <!-- Size variants -->
  <button class="btn-base btn-sm btn-primary">Small</button>
  <button class="btn-base btn-md btn-primary">Medium</button>
  <button class="btn-base btn-lg btn-primary">Large</button>

  <!-- Color variants -->
  <button class="btn-primary">Primary</button>
  <button class="btn-success">Success</button>
  <button class="btn-warning">Warning</button>
  <button class="btn-danger">Danger</button>
  <button class="btn-ghost">Ghost</button>
  <button class="btn-outline">Outline</button>
</template>
```

### Health Score Indicators

```vue
<template>
  <div :class="getHealthClass(score)">
    {{ formatHealthScore(score) }}
  </div>
</template>

<script setup lang="ts">
import { useDesignSystem } from '@/composables/useDesignSystem';

const { getHealthClass, formatHealthScore } = useDesignSystem();
const score = 87; // Example health score
</script>
```

### Status Indicators

```vue
<template>
  <span class="status-indicator status-online">
    {{ getStatusIcon('online') }} Online
  </span>
</template>
```

### Loading States

```vue
<template>
  <!-- Skeleton loaders -->
  <div class="loading-skeleton h-6 w-3/4"></div>

  <!-- Spinners -->
  <div class="loading-spinner"></div>

  <!-- Progress bars -->
  <div class="progress-bar">
    <div class="progress-fill health-excellent" :style="{ width: '85%' }"></div>
  </div>
</template>
```

## Accessibility Features

### WCAG 2.1 AA Compliance

**Contrast Ratios**: 4.5:1 minimum for normal text
```typescript
accessibility.contrast.minimum // '4.5:1'
accessibility.contrast.enhanced // '7:1' (AAA)
```

**Focus Indicators**: Consistent focus rings
```css
.focus-ring:focus {
  outline: 2px solid #3b82f6;
  outline-offset: 2px;
}
```

**Touch Targets**: Minimum 44px touch targets
```typescript
accessibility.touchTarget.minimum // '44px'
accessibility.touchTarget.recommended // '48px'
```

**Reduced Motion Support**:
```css
@media (prefers-reduced-motion: reduce) {
  .motion-safe:animate-fade-in {
    animation: none;
  }
}
```

### Screen Reader Support

```vue
<template>
  <!-- Screen reader only content -->
  <span class="sr-only">Screen reader only description</span>

  <!-- ARIA labels and roles -->
  <button
    aria-label="Close dialog"
    role="button"
    :aria-expanded="isOpen"
  >
    ×
  </button>
</template>
```

## Theme Management

### Automatic Theme Detection

```typescript
// Initialize theme from system preference or localStorage
const { initializeTheme } = useDesignSystem();
initializeTheme();
```

### Manual Theme Control

```vue
<template>
  <div class="flex gap-2">
    <button @click="setTheme('light')" class="btn-outline">Light</button>
    <button @click="setTheme('dark')" class="btn-outline">Dark</button>
    <button @click="setTheme('highContrast')" class="btn-outline">High Contrast</button>
    <button @click="toggleTheme()" class="btn-ghost">Toggle</button>
  </div>
</template>

<script setup lang="ts">
import { useDesignSystem } from '@/composables/useDesignSystem';

const { setTheme, toggleTheme } = useDesignSystem();
</script>
```

### CSS Custom Properties

The theme system automatically applies CSS custom properties:

```css
/* Available in all components */
var(--color-bg-primary)
var(--color-bg-secondary)
var(--color-text-primary)
var(--color-text-secondary)
var(--color-border-primary)
```

## Utility Functions

### Health Score Utilities

```typescript
const { getHealthColor, getHealthClass, formatHealthScore } = useDesignSystem();

getHealthColor(87)        // '#10b981' (green)
getHealthClass(87)        // 'health-excellent'
formatHealthScore(87.3)   // '87%'
```

### Format Utilities

```typescript
const { formatFileSize, formatDuration } = useDesignSystem();

formatFileSize(2621440)   // '2.5 MB'
formatDuration(65000)     // '1m 5s'
```

### Responsive Utilities

```typescript
const { getBreakpoint, isMobile, isTablet, isDesktop } = useDesignSystem();

getBreakpoint()  // 'desktop'
isMobile.value   // false
isTablet.value   // false
isDesktop.value  // true
```

## Animation System

### Component Animations

```vue
<template>
  <!-- Entrance animations -->
  <div class="animate-fade-in">Fading in</div>
  <div class="animate-slide-in-right">Sliding in</div>
  <div class="animate-scale-in">Scaling in</div>

  <!-- Loading animations -->
  <div class="animate-shimmer">Shimmer effect</div>
  <div class="animate-pulse-soft">Soft pulse</div>

  <!-- Accessibility-aware -->
  <div class="motion-safe:animate-bounce-gentle reduce-motion:animate-none">
    Conditional animation
  </div>
</template>
```

### JavaScript Animation Control

```typescript
const { shouldAnimate, getAnimationDuration } = useDesignSystem();

if (shouldAnimate.value) {
  // Apply animations
  element.style.transitionDuration = getAnimationDuration('medium');
}
```

## Development Workflow

### 1. Set Up Imports

```typescript
// main.ts or app.ts
import './src/styles/design-system.css';
import tailwindConfig from './tailwind.config';
```

### 2. Use in Components

```vue
<template>
  <div class="card-base card-md">
    <h2 class="text-xl font-semibold mb-4">Card Title</h2>
    <p class="text-text-secondary mb-4">Card description</p>
    <button class="btn-primary btn-md">Action</button>
  </div>
</template>

<script setup lang="ts">
import { useDesignSystem } from '@/composables/useDesignSystem';

const { currentTheme, isMobile } = useDesignSystem();
</script>
```

### 3. Custom Component Development

```vue
<template>
  <div :class="containerClasses">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useDesignSystem } from '@/composables/useDesignSystem';

interface Props {
  variant?: 'primary' | 'secondary' | 'tertiary';
  size?: 'sm' | 'md' | 'lg';
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'primary',
  size: 'md'
});

const { tokens } = useDesignSystem();

const containerClasses = computed(() => [
  'custom-component',
  `variant-${props.variant}`,
  `size-${props.size}`
]);
</script>
```

## Testing

### Accessibility Testing

```vue
<template>
  <!-- Ensure all interactive elements have proper ARIA labels -->
  <button
    aria-label="Generate document"
    :aria-pressed="isActive"
    class="touch-target btn-primary"
  >
    Generate
  </button>
</template>
```

### Responsive Testing

```typescript
// Test responsive behavior
const { getBreakpoint, isMobile } = useDesignSystem();

// In tests
expect(getBreakpoint()).toBe('mobile');
expect(isMobile.value).toBe(true);
```

### Theme Testing

```typescript
// Test theme switching
const { setTheme, currentTheme } = useDesignSystem();

setTheme('dark');
expect(currentTheme.value).toBe('dark');
expect(document.documentElement.classList.contains('dark')).toBe(true);
```

## Performance Considerations

### CSS Custom Properties
- Theme switching uses CSS custom properties for optimal performance
- No JavaScript re-renders required for theme changes

### Animation Performance
- All animations use `transform` and `opacity` (GPU-accelerated)
- Respects `prefers-reduced-motion` automatically
- Configurable animation durations and easing

### Bundle Size
- Tree-shakeable design tokens
- Modular CSS imports
- Tailwind CSS purges unused styles

## Migration Guide

### From Previous Versions

1. **Update imports**:
   ```typescript
   // Old
   import { colors } from './styles/colors';

   // New
   import { colors } from './design-tokens';
   ```

2. **Update class names**:
   ```vue
   <!-- Old -->
   <div class="bg-primary text-white">

   <!-- New -->
   <div class="bg-primary-500 text-white">
   ```

3. **Use design system composable**:
   ```vue
   <!-- Old -->
   <div :style="{ color: colors.primary }">

   <!-- New -->
   <script setup lang="ts">
   import { useDesignSystem } from '@/composables/useDesignSystem';
   const { colors } = useDesignSystem();
   </script>
   ```

## Contributing

### Adding New Tokens

1. Update `design-tokens.ts` with new values
2. Add corresponding Tailwind classes in `tailwind.config.ts`
3. Update CSS utilities in `src/styles/design-system.css`
4. Add helper functions to `useDesignSystem.ts` composable
5. Update documentation and examples

### Color Guidelines

- All colors must meet WCAG 2.1 AA contrast requirements
- Provide full shade ranges (50-900) for semantic colors
- Include dark theme variants
- Test with high contrast theme

### Animation Guidelines

- Default duration should be 200-300ms
- Always provide `prefers-reduced-motion` alternatives
- Use CSS `transform` and `opacity` for performance
- Include easing functions that match the design system

## Resources

- [DevDocAI v3.6.0 Mockups](docs/02-design/mockups/DESIGN-devdocai-mockups.md)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Vue 3 Documentation](https://vuejs.org/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [Inter Font Family](https://rsms.me/inter/)
- [JetBrains Mono](https://www.jetbrains.com/lp/mono/)

## Examples

See `src/components/DesignSystemExample.vue` for a complete demonstration of all design system components and utilities.

---

**DevDocAI v3.6.0 Design System** - Consistent, accessible, and beautiful UI components for professional documentation tools.