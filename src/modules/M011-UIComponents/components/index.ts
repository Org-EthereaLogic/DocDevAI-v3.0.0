/**
 * M011 React Components - Main component exports
 * 
 * Provides all React components for DevDocAI UI including dashboard,
 * charts, forms, and layout components with Material-UI integration.
 */

// Layout components
export * from './layout';

// Dashboard components  
export * from './dashboard';

// Common/shared components
export * from './common';

// Chart and visualization components
export * from './charts';

// Form components
export * from './forms';

// VS Code extension components
export * from './vscode';

// Component metadata
export const COMPONENT_INFO = {
  version: '1.0.0-pass1',
  totalComponents: 35,
  accessibility: 'WCAG-2.1-AA',
  framework: 'React-18-Material-UI-5'
};