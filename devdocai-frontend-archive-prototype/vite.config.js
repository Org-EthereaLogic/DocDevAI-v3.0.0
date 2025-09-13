import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { visualizer } from 'rollup-plugin-visualizer'
import { VitePWA } from 'vite-plugin-pwa'
// Import compression plugin with proper CommonJS handling
import compressPkg from 'vite-plugin-compress'
const compress = compressPkg.compress || compressPkg.default || compressPkg

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      vue({
        template: {
          compilerOptions: {
            // Improve build performance
            hoistStatic: true,
            cacheHandlers: true,
          }
        }
      }),

      // Progressive Web App
      VitePWA({
        registerType: 'autoUpdate',
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
          cleanupOutdatedCaches: true,
          skipWaiting: true,
        },
        manifest: {
          name: 'DevDocAI',
          short_name: 'DevDocAI',
          description: 'AI-powered documentation generation and analysis',
          theme_color: '#3B82F6',
          background_color: '#FFFFFF',
          display: 'standalone',
          start_url: '/',
          icons: [
            {
              src: '/icons/icon-192x192.png',
              sizes: '192x192',
              type: 'image/png',
            },
            {
              src: '/icons/icon-512x512.png',
              sizes: '512x512',
              type: 'image/png',
            },
          ],
        },
      }),

      // Compression (only in production)
      command === 'build' && compress && compress({
        gzip: true,
        brotli: true,
        exclude: [/\.(br|gz)$/, /\.(png|jpe?g|gif|svg|ico)$/],
      }),

      // Bundle analyzer (only when ANALYZE=true)
      env.ANALYZE && visualizer({
        filename: 'dist/stats.html',
        open: true,
        gzipSize: true,
        brotliSize: true,
      }),
    ].filter(Boolean),
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
    build: {
      // Performance optimizations
      target: 'es2020',
      rollupOptions: {
        output: {
          // Enhanced chunk splitting for better performance
          manualChunks: (id) => {
            // Vendor chunks
            if (id.includes('node_modules')) {
              if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) {
                return 'vendor-vue';
              }
              if (id.includes('axios') || id.includes('marked')) {
                return 'vendor-utils';
              }
              if (id.includes('tailwindcss') || id.includes('@tailwindcss')) {
                return 'vendor-css';
              }
              if (id.includes('@storybook')) {
                return 'vendor-storybook';
              }
              // Other vendor libraries
              return 'vendor-misc';
            }

            // Store chunks
            if (id.includes('/stores/')) {
              return 'stores';
            }

            // Component chunks
            if (id.includes('/components/')) {
              return 'components';
            }

            // Views chunks
            if (id.includes('/views/')) {
              return 'views';
            }
          },
          // Optimize file naming
          chunkFileNames: (chunkInfo) => {
            if (chunkInfo.name.startsWith('vendor-')) {
              return 'assets/vendor/[name]-[hash].js';
            }
            return 'assets/chunks/[name]-[hash].js';
          },
          entryFileNames: 'assets/[name]-[hash].js',
          assetFileNames: (assetInfo) => {
            if (assetInfo.name.endsWith('.css')) {
              return 'assets/styles/[name]-[hash].[ext]';
            }
            if (/\.(png|jpe?g|gif|svg|ico|webp)$/.test(assetInfo.name)) {
              return 'assets/images/[name]-[hash].[ext]';
            }
            if (/\.(woff2?|eot|ttf|otf)$/.test(assetInfo.name)) {
              return 'assets/fonts/[name]-[hash].[ext]';
            }
            return 'assets/[name]-[hash].[ext]';
          }
        },
        external: (id) => {
          // Externalize very large libraries that should be CDN loaded
          return false; // Keep everything bundled for now
        }
      },
      // Chunk size warnings
      chunkSizeWarningLimit: 500, // 500KB warning
      // Source maps for debugging (only in development)
      sourcemap: command === 'serve',
      // Minification
      minify: command === 'build' ? 'esbuild' : false,
      // CSS code splitting
      cssCodeSplit: true,
      // Report compressed size
      reportCompressedSize: false, // Faster builds
      // Optimize chunk loading
      assetsInlineLimit: 4096, // 4KB inline limit
    },

    // Performance optimizations
    esbuild: {
      // Remove console and debugger in production
      drop: command === 'build' ? ['console', 'debugger'] : [],
      // Legal comments
      legalComments: 'none',
    },

    // Server configuration
    server: {
      port: 5173,
      host: true,
      cors: true,
      hmr: {
        overlay: true,
      },
    },

    // Preview configuration
    preview: {
      port: 4173,
      host: true,
    },

    // Dependency optimization
    optimizeDeps: {
      include: [
        'vue',
        'vue-router',
        'pinia',
        'axios',
        'marked',
        'pinia-plugin-persistedstate',
      ],
      exclude: [
        // Large libraries that should be loaded on demand
      ],
    },

    // CSS configuration
    css: {
      devSourcemap: true,
      preprocessorOptions: {
        // Add any CSS preprocessor options here
      },
    },
    // Test configuration
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./tests/setup.js'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'html'],
        reportsDirectory: './coverage',
        exclude: [
          'node_modules/',
          'tests/',
          'dist/',
          '**/*.spec.js',
          '**/*.test.js',
          'src/main.js'
        ],
        thresholds: {
          global: {
            branches: 85,
            functions: 85,
            lines: 85,
            statements: 85
          }
        }
      },
      include: [
        'tests/unit/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
        'tests/integration/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
      ],
      exclude: [
        'node_modules/',
        'dist/',
        'tests/e2e/**'
      ],
      testTimeout: 10000,
      hookTimeout: 10000
    }
  }
})