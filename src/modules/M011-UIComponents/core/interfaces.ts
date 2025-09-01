/**
 * M011 Core Interfaces - Fundamental type definitions for UI components
 * 
 * Defines core interfaces that align with DevDocAI's privacy-first,
 * offline-capable architecture and integration with Python backend M001-M010.
 */

/**
 * Base component interface that all UI components must implement
 */
export interface IUIComponent {
  /** Unique identifier for the component */
  id: string;
  
  /** Component type for categorization */
  type: ComponentType;
  
  /** Current state of the component */
  state: ComponentState;
  
  /** Accessibility configuration */
  accessibility: AccessibilityConfig;
  
  /** Render the component */
  render(): Promise<void>;
  
  /** Update component with new data */
  update(data: ComponentData): Promise<void>;
  
  /** Clean up resources when component is destroyed */
  destroy(): Promise<void>;
}

/**
 * Component types supported in DevDocAI UI
 */
export enum ComponentType {
  // Dashboard components
  DASHBOARD = 'dashboard',
  DOCUMENT_HEALTH = 'document_health',
  TRACKING_MATRIX = 'tracking_matrix',
  QUALITY_METRICS = 'quality_metrics',
  
  // VS Code extension components
  VSCODE_PANEL = 'vscode_panel',
  VSCODE_WEBVIEW = 'vscode_webview',
  VSCODE_TREE = 'vscode_tree',
  
  // Form and input components
  FORM = 'form',
  INPUT = 'input',
  BUTTON = 'button',
  SELECT = 'select',
  
  // Visualization components
  CHART = 'chart',
  GRAPH = 'graph',
  TREE_VIEW = 'tree_view',
  
  // Layout components
  LAYOUT = 'layout',
  PANEL = 'panel',
  MODAL = 'modal',
  SIDEBAR = 'sidebar'
}

/**
 * Component state enumeration
 */
export enum ComponentState {
  INITIALIZING = 'initializing',
  READY = 'ready',
  LOADING = 'loading',
  ERROR = 'error',
  DISABLED = 'disabled',
  DESTROYED = 'destroyed'
}

/**
 * Generic component data interface
 */
export interface ComponentData {
  [key: string]: any;
}

/**
 * Accessibility configuration for WCAG 2.1 AA compliance
 */
export interface AccessibilityConfig {
  /** ARIA label for screen readers */
  ariaLabel?: string;
  
  /** ARIA description */
  ariaDescription?: string;
  
  /** Role for accessibility tree */
  role?: string;
  
  /** Keyboard navigation support */
  keyboardNavigable: boolean;
  
  /** Screen reader support */
  screenReaderSupport: boolean;
  
  /** High contrast mode support */
  highContrastSupport: boolean;
  
  /** Focus management */
  focusManagement: FocusConfig;
  
  /** Alternative text for visual elements */
  altText?: string;
}

/**
 * Focus management configuration
 */
export interface FocusConfig {
  /** Can receive focus */
  focusable: boolean;
  
  /** Tab index */
  tabIndex?: number;
  
  /** Focus trap enabled */
  focusTrap?: boolean;
  
  /** Auto-focus on render */
  autoFocus?: boolean;
}

/**
 * Integration interface with Python backend modules
 */
export interface IPythonBackendIntegration {
  /** Execute Python module function */
  callPythonModule(
    module: PythonModule,
    function: string,
    args: any[]
  ): Promise<BackendResponse>;
  
  /** Get module status */
  getModuleStatus(module: PythonModule): Promise<ModuleStatus>;
  
  /** Subscribe to backend events */
  subscribeToEvents(
    eventType: BackendEventType,
    callback: (event: BackendEvent) => void
  ): void;
  
  /** Unsubscribe from backend events */
  unsubscribeFromEvents(eventType: BackendEventType): void;
}

/**
 * Python modules available for integration
 */
export enum PythonModule {
  M001_CONFIG = 'devdocai.core.config',
  M002_STORAGE = 'devdocai.storage',
  M003_MIAIR = 'devdocai.miair',
  M004_GENERATOR = 'devdocai.generator',
  M005_QUALITY = 'devdocai.quality',
  M006_TEMPLATES = 'devdocai.templates',
  M007_REVIEW = 'devdocai.review',
  M008_LLM = 'devdocai.llm_adapter',
  M009_ENHANCEMENT = 'devdocai.enhancement',
  M010_SECURITY = 'devdocai.security'
}

/**
 * Backend response interface
 */
export interface BackendResponse {
  success: boolean;
  data?: any;
  error?: string;
  metadata?: ResponseMetadata;
}

/**
 * Response metadata
 */
export interface ResponseMetadata {
  timestamp: number;
  module: PythonModule;
  function: string;
  executionTime: number;
  cacheHit?: boolean;
}

/**
 * Module status information
 */
export interface ModuleStatus {
  available: boolean;
  version: string;
  health: 'healthy' | 'degraded' | 'error';
  lastCheck: number;
  performance?: PerformanceMetrics;
}

/**
 * Performance metrics
 */
export interface PerformanceMetrics {
  averageResponseTime: number;
  successRate: number;
  errorRate: number;
  memoryUsage: number;
}

/**
 * Backend event types
 */
export enum BackendEventType {
  MODULE_STATUS_CHANGE = 'module_status_change',
  DOCUMENT_GENERATED = 'document_generated',
  QUALITY_ANALYSIS_COMPLETE = 'quality_analysis_complete',
  ENHANCEMENT_COMPLETE = 'enhancement_complete',
  ERROR_OCCURRED = 'error_occurred',
  PROGRESS_UPDATE = 'progress_update'
}

/**
 * Backend event interface
 */
export interface BackendEvent {
  type: BackendEventType;
  module: PythonModule;
  timestamp: number;
  data: any;
}

/**
 * UI Theme interface for consistent styling
 */
export interface UITheme {
  name: string;
  colors: ColorPalette;
  typography: TypographyConfig;
  spacing: SpacingConfig;
  breakpoints: BreakpointConfig;
  accessibility: AccessibilityTheme;
}

/**
 * Color palette definition
 */
export interface ColorPalette {
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  error: string;
  info: string;
  background: string;
  surface: string;
  text: {
    primary: string;
    secondary: string;
    disabled: string;
  };
}

/**
 * Typography configuration
 */
export interface TypographyConfig {
  fontFamily: {
    primary: string;
    monospace: string;
    dyslexicFriendly?: string;
  };
  fontSize: {
    xs: string;
    sm: string;
    base: string;
    lg: string;
    xl: string;
    '2xl': string;
    '3xl': string;
  };
  fontWeight: {
    normal: number;
    medium: number;
    semibold: number;
    bold: number;
  };
  lineHeight: {
    tight: number;
    normal: number;
    relaxed: number;
  };
}

/**
 * Spacing configuration
 */
export interface SpacingConfig {
  xs: string;
  sm: string;
  md: string;
  lg: string;
  xl: string;
  '2xl': string;
  '3xl': string;
}

/**
 * Responsive breakpoint configuration
 */
export interface BreakpointConfig {
  mobile: string;
  tablet: string;
  desktop: string;
  wide: string;
}

/**
 * Accessibility theme settings
 */
export interface AccessibilityTheme {
  focusIndicator: string;
  contrastRatio: number;
  reducedMotion: boolean;
  highContrast?: ColorPalette;
}

/**
 * Component props interface for React components
 */
export interface ComponentProps {
  className?: string;
  style?: React.CSSProperties;
  theme?: UITheme;
  accessibility?: AccessibilityConfig;
  testId?: string;
}

/**
 * State management interface
 */
export interface IStateManager {
  /** Get current state */
  getState<T>(): T;
  
  /** Update state */
  setState<T>(newState: Partial<T>): void;
  
  /** Subscribe to state changes */
  subscribe<T>(callback: (state: T) => void): () => void;
  
  /** Clear all state */
  clear(): void;
}