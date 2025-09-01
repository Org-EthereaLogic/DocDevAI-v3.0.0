/**
 * Common UI Components - Export index
 * 
 * Centralizes exports for all common UI components:
 * - Loading states and spinners
 * - Empty state components
 * - Error boundaries and handling
 * - Toast notifications and alerts
 */

// Loading components
export { default as LoadingSpinner } from './LoadingSpinner';
export { default as SkeletonLoader } from './SkeletonLoader';

// State components
export { default as EmptyState } from './EmptyState';
export { default as ErrorBoundary } from './ErrorBoundary';

// Notification components
export { default as ToastNotificationManager } from './ToastNotification';
export type { ToastNotification, ToastType } from './ToastNotification';

// Re-export for convenience
export {
  LoadingSpinner as Spinner,
  SkeletonLoader as Skeleton,
  EmptyState as Empty,
  ErrorBoundary as ErrorWrapper,
  ToastNotificationManager as ToastManager
};