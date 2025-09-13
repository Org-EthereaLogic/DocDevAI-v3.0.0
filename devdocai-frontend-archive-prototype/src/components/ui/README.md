# DevDocAI v3.6.0 Design System Components

This directory contains the foundational design system components following atomic design principles and WCAG 2.1 AA accessibility standards.

## Architecture Overview

```
ui/
├── atoms/           # Basic building blocks
├── molecules/       # Simple component groups
├── organisms/       # Complex component sections
├── templates/       # Page layout structures
├── tokens/          # Design token definitions
└── utils/           # Component utilities
```

## Component Hierarchy (Atomic Design)

### 🔹 Atoms - Basic Building Blocks
- **Button** - All button variants with accessibility features
- **Input** - Text inputs, textareas with validation states
- **Badge** - Status indicators, tags, health scores
- **Icon** - SVG icon system with accessibility labels
- **Typography** - Headings, text, labels with semantic hierarchy
- **Avatar** - User profile pictures and initials
- **Spinner** - Loading states and progress indicators
- **Tooltip** - Contextual help and information display
- **Divider** - Visual separation elements
- **Checkbox/Radio** - Form selection components

### 🔸 Molecules - Simple Component Groups
- **FormField** - Input + label + validation + help text
- **SearchBox** - Input + search icon + clear button
- **ProgressBar** - Progress indicator + percentage + label
- **AlertMessage** - Icon + message + action buttons
- **DropdownMenu** - Trigger + menu items + keyboard navigation
- **TabGroup** - Tab buttons + content panels
- **Toggle** - Switch component with labels
- **DatePicker** - Input + calendar popup
- **FileUpload** - Drag & drop area + file list
- **HealthScore** - Score display + color coding + tooltip

### 🔶 Organisms - Complex Component Sections
- **Navigation** - Main app navigation with breadcrumbs
- **DataTable** - Table + sorting + pagination + filters
- **DocumentCard** - Document preview + metadata + actions
- **GenerationWizard** - Multi-step form with progress
- **TrackingMatrix** - Interactive dependency visualization
- **NotificationCenter** - Toast notifications + management
- **CommandPalette** - Search + keyboard shortcuts
- **SettingsPanel** - Configuration form + categories
- **UserVerification** - Human verification dashboard
- **SuiteManager** - Document suite management interface

### 🔷 Templates - Page Layout Structures
- **AppLayout** - Main application shell
- **AuthLayout** - Login/registration pages
- **OnboardingLayout** - First-run tutorial screens
- **DashboardLayout** - Main dashboard structure
- **DocumentLayout** - Document viewing/editing
- **SettingsLayout** - Settings and configuration

## Design Principles

### ✅ Accessibility First (WCAG 2.1 AA)
- Keyboard navigation support
- Screen reader compatibility (ARIA labels)
- High contrast mode support
- Focus management and visible indicators
- Skip links and landmark navigation
- Color contrast ratios ≥4.5:1

### 🎨 Visual Consistency
- Consistent spacing (8px grid system)
- Standardized color palette and status colors
- Typography scale with semantic meaning
- Shadow system for elevation and depth
- Border radius consistency

### ⚡ Performance Optimized
- Lazy loading for complex components
- Minimal bundle impact
- Tree-shakeable exports
- Efficient re-renders with Vue 3 composition

### 🔧 Developer Experience
- TypeScript support for all components
- Comprehensive prop documentation
- Storybook integration for development
- Consistent API patterns across components
- Easy customization through design tokens

## Component API Standards

### Props Structure
```typescript
interface ComponentProps {
  // State Props
  disabled?: boolean
  loading?: boolean
  error?: boolean | string

  // Appearance Props
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg' | 'xl'

  // Accessibility Props
  'aria-label'?: string
  'aria-describedby'?: string
  id?: string

  // Event Handlers (consistent naming)
  onClick?: (event: Event) => void
  onChange?: (value: any) => void
  onFocus?: (event: FocusEvent) => void
  onBlur?: (event: FocusEvent) => void
}
```

### Consistent Event Handling
- `onClick` for click events
- `onChange` for value changes
- `onSubmit` for form submissions
- `onFocus`/`onBlur` for focus management
- `onKeyDown` for keyboard interactions

### Accessibility Requirements
- All interactive elements must have `aria-label` or accessible text
- Focus indicators must be visible and have 4.5:1 contrast ratio
- Keyboard navigation must work without mouse
- Error states must be announced to screen readers
- Loading states must be communicated accessibly

## Motion Design Integration

Components follow v3.6.0 motion design specifications:

### Timing Standards
- Micro-interactions: 100-200ms
- State transitions: 200-400ms
- Page transitions: 300-500ms
- Complex animations: 400-800ms

### Easing Functions
- `ease-standard`: Default for most transitions
- `ease-decelerate`: For entering elements
- `ease-accelerate`: For exiting elements
- `ease-spring`: For playful interactions

### Accessibility Support
- Respects `prefers-reduced-motion` user preference
- Provides alternative static states when motion is disabled
- Uses semantic animations that enhance understanding

## Usage Examples

### Basic Button Usage
```vue
<template>
  <Button
    variant="primary"
    size="md"
    :loading="isSubmitting"
    @click="handleSubmit"
    aria-label="Generate document"
  >
    Generate Document
  </Button>
</template>
```

### Form Field with Validation
```vue
<template>
  <FormField
    label="Project Name"
    :error="validationError"
    required
  >
    <Input
      v-model="projectName"
      placeholder="Enter project name"
      :error="!!validationError"
      @blur="validateField"
    />
  </FormField>
</template>
```

### Health Score Display
```vue
<template>
  <HealthScore
    :score="87"
    :threshold="85"
    show-tooltip
    aria-label="Document health score is 87 out of 100"
  />
</template>
```

## Responsive Design

Components are designed mobile-first with breakpoint considerations:

- **xs (375px)**: Mobile portrait
- **sm (640px)**: Mobile landscape / small tablet
- **md (768px)**: Tablet portrait
- **lg (1024px)**: Tablet landscape / small desktop
- **xl (1280px)**: Desktop
- **2xl (1536px)**: Large desktop

## Implementation Status

- [x] Design tokens and Tailwind configuration
- [ ] Atomic components (Buttons, Inputs, Typography)
- [ ] Molecule components (FormFields, ProgressBars)
- [ ] Organism components (Navigation, DataTable)
- [ ] Template components (Layouts)
- [ ] Storybook integration
- [ ] Accessibility testing
- [ ] Performance optimization
- [ ] Documentation completion

## Next Steps

1. Implement atomic components starting with Button and Input
2. Create molecule components building on atoms
3. Develop organism components for complex features
4. Set up Storybook for component development
5. Add comprehensive accessibility testing
6. Performance optimization and bundle analysis
7. Integration with existing prototype components