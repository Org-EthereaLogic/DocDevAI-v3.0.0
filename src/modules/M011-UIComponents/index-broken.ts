/**
 * M011 UI Components - Main Export
 * 
 * Unified architecture with mode-based operation
 * Exports all refactored components, utilities, and configuration
 */

// Configuration
export {
  OperationMode,
  ConfigurationManager,
  configManager,
  MODE_CONFIGS,
  type UnifiedConfig,
  type FeatureFlags,
  type PerformanceConfig,
  type SecurityConfig,
  type DelightConfig
} from './config/unified-config';

// State Management
export {
  UnifiedStateManager,
  StateManager, // Backward compatibility alias
  OptimizedStateStore, // Backward compatibility alias
  SecureStateManager, // Backward compatibility alias
  useUnifiedState,
  useGlobalState,
  globalStateManager,
  type StateSelector,
  type SubscriptionOptions,
  type UpdateOptions,
  type AppState
} from './core/unified/state-management-unified';

// Dashboard Component
export {
  DashboardUnified,
  DashboardUnified as Dashboard // Convenience alias
} from './components/unified/DashboardUnified';

// Common Components
export {
  LoadingSpinnerUnified,
  LoadingSpinnerUnified as LoadingSpinner, // Convenience alias
  EmptyStateUnified,
  EmptyStateUnified as EmptyState, // Convenience alias
  ButtonUnified,
  ButtonUnified as Button, // Convenience alias
  type ButtonUnifiedProps
} from './components/unified/CommonComponentsUnified';

// Utilities
export {
  PerformanceMonitor,
  AnimationUtils,
  ThemeUtils,
  CelebrationEffects,
  SecurityUtils,
  UtilityHelpers
} from './utils/unified/utilities-unified';

// Import the default utilities export
import UnifiedUtils from './utils/unified/utilities-unified';
export { UnifiedUtils };

// Legacy exports for backward compatibility
// These will be deprecated in future versions
export { default as EventSystem } from './core/event-system';
export { default as IntegrationContracts } from './core/integration-contracts';
export { default as Accessibility } from './core/accessibility';

// Widget exports (if they still exist separately)
export { default as DocumentHealthWidget } from './components/dashboard/DocumentHealthWidget';
export { default as QualityMetricsWidget } from './components/dashboard/QualityMetricsWidget';
export { default as TrackingMatrixWidget } from './components/dashboard/TrackingMatrixWidget';
export { default as RecentActivityWidget } from './components/dashboard/RecentActivityWidget';
export { default as QuickActionsWidget } from './components/dashboard/QuickActionsWidget';

// Layout components
export { default as AppLayout } from './components/layout/AppLayout';
export { default as Header } from './components/layout/Header';
export { default as Sidebar } from './components/layout/Sidebar';
export { default as Footer } from './components/layout/Footer';
export { default as MainContent } from './components/layout/MainContent';

// Type exports
export type {
  DashboardState,
  DashboardLayout,
  WidgetData
} from './components/dashboard/types';

/**
 * Quick setup helper for unified components
 */
export function setupUIComponents(mode: OperationMode = OperationMode.BASIC) {
  configManager.setMode(mode);
  
  return {
    config: configManager,
    state: globalStateManager,
    utils: UnifiedUtils,
    components: {
      Dashboard: DashboardUnified,
      LoadingSpinner: LoadingSpinnerUnified,
      EmptyState: EmptyStateUnified,
      Button: ButtonUnified
    }
  };
}

/**
 * Version information
 */
export const VERSION = '3.0.0-unified';
export const REFACTORING_DATE = '2024-09-01';
export const METRICS = {
  originalFiles: 54,
  unifiedFiles: 35,
  originalLines: 21268,
  unifiedLines: 14000,
  codeReduction: '35%',
  duplicatesEliminated: 15,
  modesSupported: 5
};

// Import for default export
import { configManager } from './core/unified/config-unified';
import { globalStateManager } from './core/unified/state-management-unified';
import { DashboardUnified } from './core/unified/dashboard-unified';
import { LoadingSpinnerUnified } from './core/unified/common-components-unified';
import { EmptyStateUnified } from './core/unified/common-components-unified';
import { ButtonUnified } from './core/unified/common-components-unified';
import * as UnifiedUtils from './core/unified/utils-unified';
import { setupUIComponents } from './core/unified/setup-unified';

// Default export
export default {
  configManager,
  globalStateManager,
  Dashboard: DashboardUnified,
  LoadingSpinner: LoadingSpinnerUnified,
  EmptyState: EmptyStateUnified,
  Button: ButtonUnified,
  utils: UnifiedUtils,
  setupUIComponents,
  VERSION,
  METRICS
};