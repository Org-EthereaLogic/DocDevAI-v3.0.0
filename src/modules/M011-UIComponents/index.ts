/**
 * M011: UI Components - Main Module Export
 * 
 * Privacy-first, accessible UI components for DevDocAI including:
 * - React-based dashboard for document health visualization
 * - VS Code extension webview providers
 * - Responsive design system (mobile/tablet/desktop)
 * - Integration bridge to Python backend modules M001-M010
 * - WCAG 2.1 AA compliant accessibility features
 * 
 * Pass 1 Implementation Focus:
 * - Core architecture and TypeScript interfaces
 * - Basic React dashboard framework setup
 * - VS Code extension UI foundation
 * - Python backend integration layer
 * - Essential accessibility framework
 * 
 * Performance Targets (Pass 1):
 * - Dashboard load: <2 seconds
 * - Component render: <100ms
 * - VS Code integration: <500ms response time
 * - Memory usage: <200MB for UI layer
 */

// Core Architecture
export * from './core';

// UI Components
export * from './components';

// Services (Integration Layer)
export * from './services';

// TypeScript Types and Interfaces
export * from './types';

// Utilities
export * from './utils';

// Module metadata
export const MODULE_INFO = {
  name: 'M011-UIComponents',
  version: '1.0.0-pass1',
  description: 'Privacy-first UI components for DevDocAI',
  targets: {
    dashboard_load: '<2s',
    component_render: '<100ms',
    vscode_response: '<500ms',
    memory_usage: '<200MB'
  },
  coverage_target: '80-85%',
  compliance: ['WCAG-2.1-AA', 'Privacy-First', 'Offline-Capable']
};