/**
 * DevDocAI v3.6.0 Design System Components
 *
 * Centralized export for all UI components following atomic design principles
 */

// Design Tokens
export { default as designTokens } from './tokens/index.js'

// === ATOMS ===
// Basic building blocks
export { default as Button } from './atoms/Button.vue'
export { default as Badge } from './atoms/Badge.vue'
export { default as Input } from './atoms/Input.vue'

// TODO: Additional atoms to implement
// export { default as Typography } from './atoms/Typography.vue'
// export { default as Icon } from './atoms/Icon.vue'
// export { default as Avatar } from './atoms/Avatar.vue'
// export { default as Spinner } from './atoms/Spinner.vue'
// export { default as Tooltip } from './atoms/Tooltip.vue'
// export { default as Divider } from './atoms/Divider.vue'
// export { default as Checkbox } from './atoms/Checkbox.vue'
// export { default as Radio } from './atoms/Radio.vue'

// === MOLECULES ===
// Simple component combinations
export { default as FormField } from './molecules/FormField.vue'

// TODO: Additional molecules to implement
// export { default as SearchBox } from './molecules/SearchBox.vue'
// export { default as ProgressBar } from './molecules/ProgressBar.vue'
// export { default as AlertMessage } from './molecules/AlertMessage.vue'
// export { default as DropdownMenu } from './molecules/DropdownMenu.vue'
// export { default as TabGroup } from './molecules/TabGroup.vue'
// export { default as Toggle } from './molecules/Toggle.vue'
// export { default as DatePicker } from './molecules/DatePicker.vue'
// export { default as FileUpload } from './molecules/FileUpload.vue'
// export { default as HealthScore } from './molecules/HealthScore.vue'

// === ORGANISMS ===
// Complex component sections

// TODO: Organisms to implement
// export { default as Navigation } from './organisms/Navigation.vue'
// export { default as DataTable } from './organisms/DataTable.vue'
// export { default as DocumentCard } from './organisms/DocumentCard.vue'
// export { default as GenerationWizard } from './organisms/GenerationWizard.vue'
// export { default as TrackingMatrix } from './organisms/TrackingMatrix.vue'
// export { default as NotificationCenter } from './organisms/NotificationCenter.vue'
// export { default as CommandPalette } from './organisms/CommandPalette.vue'
// export { default as SettingsPanel } from './organisms/SettingsPanel.vue'
// export { default as UserVerification } from './organisms/UserVerification.vue'
// export { default as SuiteManager } from './organisms/SuiteManager.vue'

// === TEMPLATES ===
// Page layout structures

// TODO: Templates to implement
// export { default as AppLayout } from './templates/AppLayout.vue'
// export { default as AuthLayout } from './templates/AuthLayout.vue'
// export { default as OnboardingLayout } from './templates/OnboardingLayout.vue'
// export { default as DashboardLayout } from './templates/DashboardLayout.vue'
// export { default as DocumentLayout } from './templates/DocumentLayout.vue'
// export { default as SettingsLayout } from './templates/SettingsLayout.vue'

// === UTILITIES ===
// Helper functions and composables

// TODO: Utilities to implement
// export * from './utils/accessibility.js'
// export * from './utils/animation.js'
// export * from './utils/colors.js'
// export * from './utils/responsive.js'

/**
 * Component registration helper for Vue app
 *
 * @param {Object} app - Vue app instance
 */
export const registerComponents = (app) => {
  // Register available components globally
  app.component('DdButton', Button)
  app.component('DdBadge', Badge)
  app.component('DdInput', Input)
  app.component('DdFormField', FormField)

  // TODO: Register additional components as they're implemented
}

/**
 * Design system version
 */
export const version = '3.6.0'

/**
 * Available component categories for documentation
 */
export const componentCategories = {
  atoms: [
    'Button',
    'Badge',
    'Input',
    // 'Typography',
    // 'Icon',
    // 'Avatar',
    // 'Spinner',
    // 'Tooltip',
    // 'Divider',
    // 'Checkbox',
    // 'Radio',
  ],
  molecules: [
    'FormField',
    // 'SearchBox',
    // 'ProgressBar',
    // 'AlertMessage',
    // 'DropdownMenu',
    // 'TabGroup',
    // 'Toggle',
    // 'DatePicker',
    // 'FileUpload',
    // 'HealthScore',
  ],
  organisms: [
    // 'Navigation',
    // 'DataTable',
    // 'DocumentCard',
    // 'GenerationWizard',
    // 'TrackingMatrix',
    // 'NotificationCenter',
    // 'CommandPalette',
    // 'SettingsPanel',
    // 'UserVerification',
    // 'SuiteManager',
  ],
  templates: [
    // 'AppLayout',
    // 'AuthLayout',
    // 'OnboardingLayout',
    // 'DashboardLayout',
    // 'DocumentLayout',
    // 'SettingsLayout',
  ]
}

/**
 * Default export with all components
 */
export default {
  // Components
  Button,
  Badge,
  Input,
  FormField,

  // System
  designTokens,
  version,
  componentCategories,
  registerComponents,
}
