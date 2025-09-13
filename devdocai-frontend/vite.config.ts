import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue({
      template: {
        compilerOptions: {
          // Improve build performance
          hoistStatic: true,
          cacheHandlers: true,
        }
      }
    })
  ],

  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },

  // Server configuration
  server: {
    port: 5173,
    host: true,
    cors: true,
    hmr: {
      overlay: true,
    },
    // Proxy API calls to backend
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },

  // Preview configuration
  preview: {
    port: 4173,
    host: true,
  },

  // Build configuration
  build: {
    target: 'es2020',
    outDir: 'dist',
    sourcemap: false, // Disable in production for now
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
          utils: ['axios']
        }
      }
    }
  },

  // CSS configuration
  css: {
    devSourcemap: true,
  },

  // Dependency optimization
  optimizeDeps: {
    include: [
      'vue',
      'vue-router',
      'pinia',
      'axios',
      'pinia-plugin-persistedstate',
    ],
  },

  // Test configuration for Vitest
  test: {
    globals: true,
    environment: 'jsdom',
  }
})
