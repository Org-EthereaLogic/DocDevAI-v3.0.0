import js from '@eslint/js';
import pluginVue from 'eslint-plugin-vue';
import prettier from 'eslint-config-prettier';
import tseslint from '@typescript-eslint/eslint-plugin';
import tsparser from '@typescript-eslint/parser';

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  prettier,
  {
    files: ['**/*.{js,ts,vue}'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        // Node.js globals for config files
        process: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
        module: 'readonly',
        require: 'readonly',

        // Browser globals
        window: 'readonly',
        document: 'readonly',
        navigator: 'readonly',
        console: 'readonly',

        // Vue globals
        defineProps: 'readonly',
        defineEmits: 'readonly',
        defineExpose: 'readonly',
        withDefaults: 'readonly',
      },
    },
    rules: {
      // Vue-specific rules
      'vue/multi-word-component-names': 'off',
      'vue/component-definition-name-casing': ['error', 'PascalCase'],
      'vue/component-name-in-template-casing': ['error', 'PascalCase'],
      'vue/prop-name-casing': ['error', 'camelCase'],
      'vue/attribute-hyphenation': ['error', 'always'],
      'vue/v-on-event-hyphenation': ['error', 'always'],
      'vue/no-v-html': 'warn',
      'vue/require-default-prop': 'error',
      'vue/require-prop-types': 'error',
      'vue/no-unused-vars': 'error',
      'vue/no-unused-components': 'warn',
      'vue/order-in-components': 'error',
      'vue/html-indent': ['error', 2],
      'vue/max-attributes-per-line': [
        'error',
        {
          singleline: 3,
          multiline: 1,
        },
      ],

      // JavaScript rules
      'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
      'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
      'prefer-const': 'error',
      'no-var': 'error',
      'object-shorthand': 'error',
      'prefer-template': 'error',
      'prefer-arrow-callback': 'error',
      'arrow-spacing': 'error',
      'space-before-function-paren': [
        'error',
        {
          anonymous: 'always',
          named: 'never',
          asyncArrow: 'always',
        },
      ],

      // Code quality
      'eqeqeq': ['error', 'always'],
      'curly': ['error', 'all'],
      'no-duplicate-imports': 'error',
      'no-useless-concat': 'error',
      'no-useless-return': 'error',
      'no-useless-computed-key': 'error',
      'no-unneeded-ternary': 'error',

      // Best practices
      'complexity': ['warn', 15],
      'max-depth': ['warn', 4],
      'max-lines-per-function': ['warn', 100],
      'max-params': ['warn', 5],
    },
  },
  {
    files: ['**/*.ts', '**/*.tsx'],
    languageOptions: {
      parser: tsparser,
      parserOptions: {
        ecmaVersion: 'latest',
        sourceType: 'module',
        project: './tsconfig.json',
      },
    },
    plugins: {
      '@typescript-eslint': tseslint,
    },
    rules: {
      // TypeScript-specific rules
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-non-null-assertion': 'warn',
      '@typescript-eslint/prefer-optional-chain': 'error',
      '@typescript-eslint/prefer-nullish-coalescing': 'error',
      '@typescript-eslint/no-unnecessary-type-assertion': 'error',
      '@typescript-eslint/no-unused-expressions': 'error',
      '@typescript-eslint/consistent-type-imports': [
        'error',
        { prefer: 'type-imports' },
      ],
      '@typescript-eslint/consistent-type-definitions': ['error', 'interface'],
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
      '@typescript-eslint/no-inferrable-types': 'error',
      '@typescript-eslint/no-duplicate-enum-values': 'error',
      '@typescript-eslint/no-empty-interface': 'error',
      '@typescript-eslint/no-namespace': 'error',
      '@typescript-eslint/prefer-as-const': 'error',
      '@typescript-eslint/prefer-function-type': 'error',

      // Disable base ESLint rules that are covered by TypeScript
      'no-unused-vars': 'off',
      'no-undef': 'off',
      'no-redeclare': 'off',
    },
  },
  {
    files: ['**/*.stories.js', '**/*.story.js'],
    rules: {
      // Allow default exports in stories
      'import/no-default-export': 'off',
      // Allow console in stories for demo purposes
      'no-console': 'off',
    },
  },
  {
    files: ['**/*.test.js', '**/*.spec.js', 'tests/**/*.js'],
    languageOptions: {
      globals: {
        describe: 'readonly',
        it: 'readonly',
        test: 'readonly',
        expect: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        beforeAll: 'readonly',
        afterAll: 'readonly',
        vi: 'readonly',
        vitest: 'readonly',
      },
    },
    rules: {
      // Relax some rules for test files
      'no-unused-vars': 'off',
      'max-lines-per-function': 'off',
    },
  },
  {
    files: ['**/*.config.js', '**/*.config.ts', 'vite.config.js', 'tailwind.config.js'],
    languageOptions: {
      globals: {
        module: 'readonly',
        require: 'readonly',
        process: 'readonly',
        __dirname: 'readonly',
        __filename: 'readonly',
      },
    },
    rules: {
      'no-undef': 'off',
    },
  },
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      '.storybook/**',
      'storybook-static/**',
      'coverage/**',
      '*.min.js',
      'public/**',
    ],
  },
];