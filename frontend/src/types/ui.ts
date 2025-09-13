// UI and Component Types for DevDocAI v3.6.0

// Component State Types
export type ComponentState = 'idle' | 'loading' | 'success' | 'error';

export interface LoadingState {
  isLoading: boolean;
  message?: string;
  progress?: number;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
  code?: string;
  details?: Record<string, any>;
  retryable?: boolean;
}

// Form and Input Types
export interface FormField {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'number' | 'select' | 'checkbox' | 'textarea' | 'file';
  value: any;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  error?: string;
  helpText?: string;
  options?: SelectOption[];
  validation?: ValidationRule[];
}

export interface SelectOption {
  label: string;
  value: string | number;
  disabled?: boolean;
  group?: string;
}

export interface ValidationRule {
  type: 'required' | 'email' | 'min' | 'max' | 'pattern' | 'custom';
  value?: any;
  message: string;
  validator?: (value: any) => boolean;
}

// Navigation Types
export interface NavigationItem {
  id: string;
  label: string;
  icon?: string;
  route?: string;
  external?: boolean;
  children?: NavigationItem[];
  badge?: {
    text: string;
    variant: 'primary' | 'success' | 'warning' | 'danger';
  };
  permission?: string;
  active?: boolean;
}

export interface Breadcrumb {
  label: string;
  route?: string;
  current?: boolean;
}

// Modal and Dialog Types
export interface ModalOptions {
  title?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | 'full';
  closable?: boolean;
  persistent?: boolean;
  backdrop?: boolean;
  keyboard?: boolean;
}

export interface ConfirmDialogOptions extends ModalOptions {
  message: string;
  confirmText?: string;
  cancelText?: string;
  variant?: 'primary' | 'success' | 'warning' | 'danger';
}

// Table and Data Grid Types
export interface TableColumn<T = any> {
  key: string;
  label: string;
  sortable?: boolean;
  searchable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  render?: (value: any, row: T) => string | any;
  headerClass?: string;
  cellClass?: string;
}

export interface TableOptions {
  selectable?: boolean;
  multiSelect?: boolean;
  pagination?: boolean;
  pageSize?: number;
  sortable?: boolean;
  searchable?: boolean;
  exportable?: boolean;
}

// Notification Types
export interface Notification {
  id: string;
  title?: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
  duration?: number;
  persistent?: boolean;
  actions?: NotificationAction[];
  timestamp: Date;
}

export interface NotificationAction {
  label: string;
  action: () => void;
  style?: 'primary' | 'secondary';
}

// Chart and Visualization Types
export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

export interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string;
  borderWidth?: number;
  fill?: boolean;
}

export interface ChartOptions {
  responsive?: boolean;
  maintainAspectRatio?: boolean;
  plugins?: Record<string, any>;
  scales?: Record<string, any>;
}

// Dashboard and Widget Types
export interface DashboardWidget {
  id: string;
  title: string;
  type: 'chart' | 'metric' | 'table' | 'custom';
  size: 'small' | 'medium' | 'large';
  position: { x: number; y: number; width: number; height: number };
  config: Record<string, any>;
  data?: any;
  refreshInterval?: number;
}

export interface MetricWidget {
  value: number | string;
  label: string;
  trend?: {
    direction: 'up' | 'down' | 'stable';
    percentage: number;
    period: string;
  };
  target?: number;
  unit?: string;
  format?: 'number' | 'percentage' | 'currency' | 'bytes';
}

// Theme and Styling Types
export interface Theme {
  name: string;
  colors: {
    primary: string;
    secondary: string;
    success: string;
    warning: string;
    danger: string;
    info: string;
    light: string;
    dark: string;
  };
  fonts: {
    primary: string;
    secondary: string;
    mono: string;
  };
  spacing: Record<string, string>;
  borderRadius: Record<string, string>;
  shadows: Record<string, string>;
}

// Accessibility Types
export interface A11yOptions {
  label?: string;
  describedBy?: string;
  labelledBy?: string;
  role?: string;
  tabIndex?: number;
  ariaExpanded?: boolean;
  ariaSelected?: boolean;
  ariaChecked?: boolean;
  ariaDisabled?: boolean;
  ariaHidden?: boolean;
}

// Animation and Transition Types
export interface AnimationConfig {
  name: string;
  duration: number;
  easing: string;
  delay?: number;
  fillMode?: 'none' | 'forwards' | 'backwards' | 'both';
}

export interface TransitionConfig {
  enter: string;
  enterActive: string;
  enterTo: string;
  leave: string;
  leaveActive: string;
  leaveTo: string;
  duration?: number | { enter: number; leave: number };
}

// File Upload Types
export interface FileUploadConfig {
  accept?: string[];
  maxSize?: number;
  maxFiles?: number;
  allowDrop?: boolean;
  showPreview?: boolean;
  autoUpload?: boolean;
}

export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  url?: string;
  progress?: number;
  status: 'pending' | 'uploading' | 'completed' | 'error';
  error?: string;
}

// Search and Filter Types
export interface SearchConfig {
  placeholder?: string;
  debounce?: number;
  minLength?: number;
  caseSensitive?: boolean;
  searchFields?: string[];
}

export interface FilterOption {
  key: string;
  label: string;
  type: 'select' | 'multiselect' | 'range' | 'date' | 'boolean';
  options?: SelectOption[];
  value?: any;
}

// Layout Types
export interface LayoutConfig {
  sidebar: {
    collapsed: boolean;
    width: number;
    collapsedWidth: number;
  };
  header: {
    height: number;
    fixed: boolean;
  };
  footer: {
    height: number;
    visible: boolean;
  };
  content: {
    padding: string;
    maxWidth?: string;
  };
}

// Tour and Onboarding Types
export interface TourStep {
  target: string;
  title: string;
  content: string;
  placement: 'top' | 'bottom' | 'left' | 'right';
  showButtons?: boolean;
  allowClicksThru?: boolean;
  highlightClass?: string;
}

export interface OnboardingFlow {
  id: string;
  name: string;
  steps: TourStep[];
  autoStart?: boolean;
  showProgress?: boolean;
  skipable?: boolean;
}

// Keyboard Shortcut Types
export interface KeyboardShortcut {
  keys: string[];
  description: string;
  action: () => void;
  global?: boolean;
  disabled?: boolean;
}

// Context Menu Types
export interface ContextMenuItem {
  label: string;
  icon?: string;
  action: () => void;
  disabled?: boolean;
  separator?: boolean;
  children?: ContextMenuItem[];
}

// Progress and Stepper Types
export interface StepperStep {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  optional?: boolean;
  icon?: string;
}

export interface ProgressConfig {
  value: number;
  max?: number;
  showLabel?: boolean;
  showPercentage?: boolean;
  animated?: boolean;
  striped?: boolean;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'success' | 'warning' | 'danger';
}

// Responsive Breakpoints
export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface ResponsiveValue<T> {
  xs?: T;
  sm?: T;
  md?: T;
  lg?: T;
  xl?: T;
  '2xl'?: T;
}

// Component Props Helper Types
export interface BaseComponentProps {
  id?: string;
  class?: string;
  style?: Record<string, any>;
  testId?: string;
  a11y?: A11yOptions;
}

export interface InteractiveComponentProps extends BaseComponentProps {
  disabled?: boolean;
  loading?: boolean;
  onClick?: (event: Event) => void;
  onFocus?: (event: FocusEvent) => void;
  onBlur?: (event: FocusEvent) => void;
}