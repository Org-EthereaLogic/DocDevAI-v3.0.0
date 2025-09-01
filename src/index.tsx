/**
 * DevDocAI v3.0.0 - Application Entry Point
 * 
 * Main entry point for the full DocDevAI application
 * Privacy-first, offline-capable documentation generation system
 */

import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
// import App from './AppSimple'; // Temporarily using simple app for debugging

// Performance monitoring in development
if (process.env.NODE_ENV === 'development') {
  const reportWebVitals = (metric: any) => {
    console.log('Web Vitals:', metric);
  };
  
  // Log performance metrics
  if ('performance' in window && 'measure' in window.performance) {
    window.addEventListener('load', () => {
      const perfData = window.performance.getEntriesByType('navigation')[0] as any;
      console.log('Page Load Metrics:', {
        domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
        loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
        domInteractive: perfData.domInteractive,
        firstPaint: perfData.firstPaint
      });
    });
  }
}

// Mount the application
const container = document.getElementById('root');
if (!container) {
  throw new Error('Failed to find root element');
}

const root = createRoot(container);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// Register service worker for offline support (production only)
if ('serviceWorker' in navigator && process.env.NODE_ENV === 'production') {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then(registration => {
        console.log('ServiceWorker registered:', registration);
      })
      .catch(error => {
        console.error('ServiceWorker registration failed:', error);
      });
  });
}

// Hide loading screen
window.addEventListener('DOMContentLoaded', () => {
  const loader = document.getElementById('app-loader');
  if (loader) {
    setTimeout(() => {
      loader.style.opacity = '0';
      setTimeout(() => loader.remove(), 300);
    }, 100);
  }
});