// DevDocAI v3.6.0 Atomic Components Export
// Foundational UI components following atomic design principles

// Import all atomic components
import Button from './Button.vue'
import Input from './Input.vue'
import Heading from './Heading.vue'
import Text from './Text.vue'
import Link from './Link.vue'

// Export individual components
export {
  Button,
  Input,
  Heading,
  Text,
  Link
}

// Export as default object for bulk imports
export default {
  Button,
  Input,
  Heading,
  Text,
  Link
}

// Type exports for TypeScript support
export type {
  ButtonProps,
  InputProps,
  HeadingProps,
  TextProps,
  LinkProps,
  ComponentSize,
  ComponentVariant,
  HeadingLevel,
  InputType
} from '@/types/components'