/**
 * Webpack Configuration for M011 UI Components
 * 
 * Optimized for performance with:
 * - Code splitting
 * - Tree shaking
 * - Bundle optimization
 * - Lazy loading
 * - Production optimizations
 */

const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const webpack = require('webpack');
const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
const TerserPlugin = require('terser-webpack-plugin');
const CompressionPlugin = require('compression-webpack-plugin');

module.exports = (env, argv) => {
  const isProduction = argv.mode === 'production';
  const isDevelopment = !isProduction;
  const shouldAnalyze = process.env.ANALYZE === 'true';

  return {
    entry: {
      main: './src/index.tsx',
      // Separate vendor bundle for dependencies
      vendor: [
        'react',
        'react-dom',
        '@mui/material',
        '@mui/icons-material'
      ]
    },

    output: {
      path: path.resolve(__dirname, 'dist'),
      filename: isProduction 
        ? '[name].[contenthash:8].bundle.js'
        : '[name].bundle.js',
      chunkFilename: isProduction
        ? 'chunks/[name].[contenthash:8].chunk.js'
        : 'chunks/[name].chunk.js',
      clean: true,
      // Enable module concatenation for tree shaking
      pathinfo: false
    },

    resolve: {
      extensions: ['.ts', '.tsx', '.js', '.jsx'],
      alias: {
        '@components': path.resolve(__dirname, 'src/components'),
        '@services': path.resolve(__dirname, 'src/services'),
        '@utils': path.resolve(__dirname, 'src/utils'),
        '@types': path.resolve(__dirname, 'src/types')
      },
      // Prefer ES modules for better tree shaking
      mainFields: ['module', 'main']
    },

    module: {
      rules: [
        {
          test: /\.tsx?$/,
          use: [
            {
              loader: 'ts-loader',
              options: {
                transpileOnly: true,
                experimentalWatchApi: true,
                // Skip type checking for faster builds
                ...(isDevelopment && {
                  compilerOptions: {
                    skipLibCheck: true,
                    skipDefaultLibCheck: true
                  }
                })
              }
            }
          ],
          exclude: /node_modules/
        },
        {
          test: /\.css$/,
          use: [
            'style-loader',
            {
              loader: 'css-loader',
              options: {
                modules: {
                  auto: true,
                  localIdentName: isProduction
                    ? '[hash:base64:8]'
                    : '[path][name]__[local]'
                }
              }
            }
          ]
        },
        {
          test: /\.(png|svg|jpg|jpeg|gif)$/i,
          type: 'asset',
          parser: {
            dataUrlCondition: {
              maxSize: 8 * 1024 // 8kb
            }
          }
        }
      ]
    },

    optimization: {
      minimize: isProduction,
      minimizer: [
        new TerserPlugin({
          terserOptions: {
            parse: {
              ecma: 8
            },
            compress: {
              ecma: 5,
              warnings: false,
              comparisons: false,
              inline: 2,
              drop_console: isProduction,
              drop_debugger: isProduction,
              pure_funcs: isProduction ? ['console.log'] : []
            },
            mangle: {
              safari10: true
            },
            output: {
              ecma: 5,
              comments: false,
              ascii_only: true
            }
          },
          parallel: true
        })
      ],
      
      // Split runtime chunk for better caching
      runtimeChunk: 'single',
      
      // Module IDs for better caching
      moduleIds: 'deterministic',
      
      // Split chunks configuration
      splitChunks: {
        chunks: 'all',
        maxInitialRequests: 25,
        minSize: 20000,
        maxSize: 244000,
        cacheGroups: {
          // Vendor libraries
          vendor: {
            test: /[\\\\/]node_modules[\\\\/]/,
            name(module) {
              const packageName = module.context.match(/[\\\\/]node_modules[\\\\/](.*?)([\\\\\/]|$)/)[1];
              return `vendor.${packageName.replace('@', '')}`;
            },
            priority: 10
          },
          
          // Material-UI components
          mui: {
            test: /[\\\\/]node_modules[\\\\/]@mui[\\\\/]/,
            name: 'mui',
            priority: 20
          },
          
          // React libraries
          react: {
            test: /[\\\\/]node_modules[\\\\/](react|react-dom|react-router)[\\\\/]/,
            name: 'react',
            priority: 30
          },
          
          // Charting libraries
          charts: {
            test: /[\\\\/]node_modules[\\\\/](recharts|d3|victory)[\\\\/]/,
            name: 'charts',
            priority: 15
          },
          
          // Common components
          common: {
            test: /[\\\\/]src[\\\\/]modules[\\\\/]M011-UIComponents[\\\\/]components[\\\\/]common[\\\\/]/,
            name: 'common',
            priority: 5,
            minChunks: 2
          },
          
          // Dashboard components
          dashboard: {
            test: /[\\\\/]src[\\\\/]modules[\\\\/]M011-UIComponents[\\\\/]components[\\\\/]dashboard[\\\\/]/,
            name: 'dashboard',
            priority: 5
          }
        }
      },
      
      // Enable side effects free modules
      sideEffects: false,
      
      // Use contenthash for better caching
      realContentHash: true
    },

    plugins: [
      // Inject environment variables used in the client bundle
      new webpack.EnvironmentPlugin({
        NODE_ENV: argv.mode || 'development',
        REACT_APP_API_URL: 'http://localhost:8000',
        REACT_APP_BUILD_NUMBER: 'dev'
      }),
      new HtmlWebpackPlugin({
        template: 'public/index.html',
        // favicon: 'public/favicon.ico', // Uncomment when favicon is available
        minify: isProduction ? {
          removeComments: true,
          collapseWhitespace: true,
          removeRedundantAttributes: true,
          useShortDoctype: true,
          removeEmptyAttributes: true,
          removeStyleLinkTypeAttributes: true,
          keepClosingSlash: true,
          minifyJS: true,
          minifyCSS: true,
          minifyURLs: true
        } : false
      }),
      
      // Compression for production
      ...(isProduction ? [
        new CompressionPlugin({
          algorithm: 'gzip',
          test: /\\.(js|css|html|svg)$/,
          threshold: 8192,
          minRatio: 0.8
        }),
        new CompressionPlugin({
          algorithm: 'brotliCompress',
          test: /\\.(js|css|html|svg)$/,
          threshold: 8192,
          minRatio: 0.8,
          filename: '[path][base].br'
        })
      ] : []),
      
      // Bundle analyzer
      ...(shouldAnalyze ? [
        new BundleAnalyzerPlugin({
          analyzerMode: 'static',
          reportFilename: 'bundle-report.html',
          openAnalyzer: false,
          generateStatsFile: true,
          statsFilename: 'bundle-stats.json'
        })
      ] : [])
    ],

    devServer: {
      port: 3000,
      hot: true,
      open: true,
      historyApiFallback: true,
      compress: true,
      client: {
        overlay: {
          errors: true,
          warnings: false
        }
      },
      static: {
        directory: path.join(__dirname, 'public')
      }
    },

    // Performance hints
    performance: {
      hints: isProduction ? 'warning' : false,
      maxEntrypointSize: 512000, // 500KB
      maxAssetSize: 512000 // 500KB
    },

    // Source maps
    devtool: isProduction 
      ? 'source-map' 
      : 'eval-cheap-module-source-map',

    // Stats output
    stats: {
      assets: true,
      children: false,
      chunks: false,
      hash: false,
      modules: false,
      publicPath: false,
      timings: true,
      version: false,
      warnings: true,
      colors: true
    }
  };
};
