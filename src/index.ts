/**
 * DevDocAI v3.0.0 - Main TypeScript Entry Point
 * 
 * This is the primary entry point for the TypeScript components of DevDocAI,
 * including UI components, VS Code extensions, and web dashboard.
 * 
 * Architecture:
 * - M011: UI Components (this module)
 * - M012: CLI Interface (future)
 * - M013: VS Code Extension (future)
 * 
 * Integration:
 * - Connects to Python backend modules M001-M010 via bridge services
 * - Provides React-based dashboard and VS Code webview components
 * - Implements accessibility, responsive design, and state management
 */

// M011 UI Components - Main exports
export * from './modules/M011-UIComponents';

// Version information
export const VERSION = '3.0.0';
export const MODULE_VERSION = {
  M011_UI_COMPONENTS: '1.0.0-pass1'
};

/**
 * Development methodology marker
 * Current: M011 Pass 1 Implementation
 * - Core UI architecture setup
 * - Basic React dashboard framework
 * - VS Code extension UI foundation
 * - Integration layer with Python backend
 * - Initial test coverage (target: 80-85%)
 */
export const DEVELOPMENT_PHASE = {
  current: 'M011-Pass1-Implementation',
  target_coverage: '80-85%',
  focus: 'Core UI Architecture & Integration'
};