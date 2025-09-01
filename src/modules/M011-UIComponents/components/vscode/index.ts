/**
 * VS Code Extension Components - Export index
 * 
 * Centralizes exports for all VS Code integration components:
 * - Webview panels and providers
 * - Document generation interface
 * - Status bar integration
 * - Extension communication utilities
 */

// Core webview components
export { default as WebviewPanel } from './WebviewPanel';
export type { WebviewPanelType } from './WebviewPanel';

// Document generation
export { default as DocumentGeneratorPanel } from './DocumentGeneratorPanel';

// Status bar integration
export { default as StatusBarProvider } from './StatusBarProvider';
export type { StatusType } from './StatusBarProvider';

// Re-export for convenience
export {
  WebviewPanel as Panel,
  DocumentGeneratorPanel as Generator,
  StatusBarProvider as StatusBar
};