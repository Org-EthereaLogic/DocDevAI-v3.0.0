// Component types for DevDocAI v3.6.0 Design System

export type ComponentSize = 'sm' | 'md' | 'lg';
export type ComponentVariant = 'primary' | 'secondary' | 'tertiary' | 'danger' | 'success' | 'warning' | 'info';

// Button component types
export interface ButtonProps {
  variant?: ComponentVariant;
  size?: ComponentSize;
  disabled?: boolean;
  loading?: boolean;
  type?: 'button' | 'submit' | 'reset';
  fullWidth?: boolean;
  icon?: boolean;
  iconPosition?: 'left' | 'right';
  ariaLabel?: string;
  ariaDescribedBy?: string;
}

// Input component types
export type InputType = 'text' | 'email' | 'password' | 'search' | 'tel' | 'url' | 'number';

export interface InputProps {
  type?: InputType;
  size?: ComponentSize;
  variant?: 'default' | 'error' | 'success';
  disabled?: boolean;
  readonly?: boolean;
  required?: boolean;
  placeholder?: string;
  value?: string | number;
  error?: boolean;
  errorMessage?: string;
  helpText?: string;
  label?: string;
  id?: string;
  name?: string;
  autocomplete?: string;
  ariaLabel?: string;
  ariaDescribedBy?: string;
  maxLength?: number;
  minLength?: number;
  pattern?: string;
}

// Typography component types
export type HeadingLevel = 1 | 2 | 3 | 4 | 5 | 6;

export interface HeadingProps {
  level: HeadingLevel;
  size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | '5xl' | '6xl';
  weight?: 'light' | 'normal' | 'medium' | 'semibold' | 'bold';
  color?: 'default' | 'muted' | 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info';
  align?: 'left' | 'center' | 'right';
  truncate?: boolean;
  balance?: boolean;
}

export interface TextProps {
  size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl';
  weight?: 'light' | 'normal' | 'medium' | 'semibold' | 'bold';
  color?: 'default' | 'muted' | 'primary' | 'secondary' | 'success' | 'warning' | 'danger' | 'info';
  align?: 'left' | 'center' | 'right' | 'justify';
  truncate?: boolean | number;
  balance?: boolean;
  mono?: boolean;
}

export interface LinkProps {
  href?: string;
  to?: string;
  external?: boolean;
  underline?: boolean | 'hover' | 'always';
  color?: 'default' | 'primary' | 'secondary' | 'muted';
  size?: 'xs' | 'sm' | 'base' | 'lg' | 'xl';
  weight?: 'light' | 'normal' | 'medium' | 'semibold' | 'bold';
  ariaLabel?: string;
  target?: '_blank' | '_self' | '_parent' | '_top';
  rel?: string;
}

// Common component state types
export interface LoadingState {
  loading?: boolean;
  loadingText?: string;
}

export interface DisabledState {
  disabled?: boolean;
  disabledReason?: string;
}

export interface ErrorState {
  error?: boolean;
  errorMessage?: string;
}

export interface ValidationState extends ErrorState {
  valid?: boolean;
  validationMessage?: string;
}

// Accessibility types
export interface AccessibilityProps {
  ariaLabel?: string;
  ariaLabelledBy?: string;
  ariaDescribedBy?: string;
  ariaExpanded?: boolean;
  ariaHidden?: boolean;
  role?: string;
  tabIndex?: number;
}

// Event types
export interface ComponentEvents {
  click?: (event: MouseEvent) => void;
  focus?: (event: FocusEvent) => void;
  blur?: (event: FocusEvent) => void;
  keydown?: (event: KeyboardEvent) => void;
  keyup?: (event: KeyboardEvent) => void;
}

export interface InputEvents extends ComponentEvents {
  input?: (event: Event) => void;
  change?: (event: Event) => void;
  'update:modelValue'?: (value: string | number) => void;
}

// Animation and motion types
export type AnimationDuration = 'fast' | 'normal' | 'slow';
export type AnimationEasing = 'ease' | 'ease-in' | 'ease-out' | 'ease-in-out';

export interface AnimationProps {
  animate?: boolean;
  duration?: AnimationDuration;
  easing?: AnimationEasing;
  delay?: number;
}

// Responsive types
export interface ResponsiveProps {
  responsive?: boolean;
  breakpoints?: {
    sm?: Partial<ButtonProps | InputProps | HeadingProps | TextProps>;
    md?: Partial<ButtonProps | InputProps | HeadingProps | TextProps>;
    lg?: Partial<ButtonProps | InputProps | HeadingProps | TextProps>;
    xl?: Partial<ButtonProps | InputProps | HeadingProps | TextProps>;
  };
}

// Theme types
export interface ThemeProps {
  theme?: 'light' | 'dark' | 'auto';
  highContrast?: boolean;
}