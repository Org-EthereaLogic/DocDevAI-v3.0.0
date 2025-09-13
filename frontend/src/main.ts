// DevDocAI v3.6.0 Frontend - Application Entry Point

import { createApp } from 'vue';
import { installStores, initializeStores } from '@/stores';
import { configureApi, enableApiLogging } from '@/services';
import App from './App.vue';
import router from './router';
import './style.css';

// Application initialization
async function initializeApp() {
  const app = createApp(App);

  // Install router
  app.use(router);

  // Install Pinia stores
  installStores(app);

  // Configure API client
  await configureApi({
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
    timeout: 30000,
  });

  // Enable API logging in development
  if (import.meta.env.DEV) {
    enableApiLogging(true);
  }

  // Initialize stores
  try {
    await initializeStores();
  } catch (error) {
    console.warn('Store initialization failed, continuing with defaults:', error);
  }

  // Mount application
  app.mount('#app');

  // Development utilities
  if (import.meta.env.DEV) {
    // Make app instance available globally for debugging
    (window as any).__VUE_APP__ = app;

    // Performance monitoring
    app.config.performance = true;

    // Global error handler
    app.config.errorHandler = (error, instance, info) => {
      console.error('Vue Error:', error);
      console.error('Component:', instance);
      console.error('Info:', info);

      // In a real app, you might want to send this to an error reporting service
    };

    // Global warning handler
    app.config.warnHandler = (msg, instance, trace) => {
      console.warn('Vue Warning:', msg);
      console.warn('Component:', instance);
      console.warn('Trace:', trace);
    };
  }

  return app;
}

// Initialize and start the application
initializeApp().catch(error => {
  console.error('Failed to initialize application:', error);

  // Show a basic error message if the app fails to start
  document.body.innerHTML = `
    <div style="
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      font-family: system-ui, sans-serif;
      text-align: center;
      padding: 2rem;
      background: #f9fafb;
      color: #374151;
    ">
      <div style="
        max-width: 500px;
        padding: 2rem;
        background: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      ">
        <h1 style="
          font-size: 1.5rem;
          font-weight: 600;
          margin-bottom: 1rem;
          color: #dc2626;
        ">
          DevDocAI Initialization Error
        </h1>
        <p style="margin-bottom: 1.5rem; line-height: 1.6;">
          The application failed to start. Please check your network connection and ensure the backend API is running.
        </p>
        <button
          onclick="window.location.reload()"
          style="
            padding: 0.75rem 1.5rem;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.15s;
          "
          onmouseover="this.style.backgroundColor='#2563eb'"
          onmouseout="this.style.backgroundColor='#3b82f6'"
        >
          Retry
        </button>
        <details style="margin-top: 1.5rem; text-align: left;">
          <summary style="cursor: pointer; font-weight: 500; margin-bottom: 0.5rem;">
            Technical Details
          </summary>
          <pre style="
            background: #f3f4f6;
            padding: 1rem;
            border-radius: 4px;
            font-size: 0.875rem;
            overflow-x: auto;
            color: #6b7280;
          ">${error.message || error}</pre>
        </details>
      </div>
    </div>
  `;
});

// Service Worker registration (for PWA features)
if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then(registration => {
        console.log('SW registered: ', registration);
      })
      .catch(registrationError => {
        console.log('SW registration failed: ', registrationError);
      });
  });
}

// Hot Module Replacement (HMR) for development
if (import.meta.hot) {
  import.meta.hot.accept();

  // Re-initialize stores on HMR
  import.meta.hot.accept(['@/stores/index'], async () => {
    console.log('Stores updated, re-initializing...');
    try {
      await initializeStores();
    } catch (error) {
      console.warn('Store re-initialization failed:', error);
    }
  });
}