# Complete Repository Rebuild Guide

## Step-by-Step Setup for DevDocAI v2.0.0 Fresh Start

This guide will help you rebuild the entire development environment from scratch with all integrations working correctly from the start.

---

## Part 1: GitHub Repository Setup

### 1.1 Create New Repository

```bash
# On GitHub.com:
# 1. Click "New repository"
# 2. Name: DevDocAI (or your preferred name)
# 3. Description: "AI-powered documentation system v2.0.0"
# 4. Private/Public: Your choice
# 5. DO NOT initialize with README, .gitignore, or license
# 6. Click "Create repository"
```

### 1.2 Clone and Initialize Locally

```bash
# Clone the empty repository
git clone https://github.com/YOUR-ORG/DevDocAI.git
cd DevDocAI

# Initialize with Node.js
npm init -y

# Set package.json details
npm pkg set name="devdocai"
npm pkg set version="2.0.0"
npm pkg set description="AI-powered documentation system"
npm pkg set author="Your Name"
npm pkg set license="MIT"
npm pkg set engines.node=">=18.0.0"
npm pkg set engines.npm=">=9.0.0"
```

---

## Part 2: Core Dependencies Installation

### 2.1 Install TypeScript and Core Dev Tools

```bash
# TypeScript and types
npm install --save-dev typescript @types/node ts-node tsx

# Testing framework
npm install --save-dev jest @types/jest ts-jest

# Linting and formatting
npm install --save-dev eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
npm install --save-dev prettier eslint-config-prettier eslint-plugin-prettier

# Git hooks and commit standards
npm install --save-dev husky lint-staged commitlint @commitlint/cli @commitlint/config-conventional

# Additional dev tools
npm install --save-dev rimraf cross-env dotenv
```

### 2.2 Install Production Dependencies

```bash
# Core runtime dependencies
npm install dotenv
```

---

## Part 3: Configuration Files Setup

### 3.1 TypeScript Configuration

```bash
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "commonjs",
    "lib": ["ES2022"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true,
    "allowUnusedLabels": false,
    "allowUnreachableCode": false,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "removeComments": true,
    "resolveJsonModule": true,
    "moduleResolution": "node",
    "types": ["node", "jest"]
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "coverage", "**/*.test.ts", "**/*.spec.ts"]
}
EOF
```

### 3.2 Jest Configuration

```bash
cat > jest.config.js << 'EOF'
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src', '<rootDir>/tests'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/*.test.ts',
    '!src/**/*.spec.ts',
    '!src/**/index.ts'
  ],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1'
  },
  transform: {
    '^.+\\.ts$': ['ts-jest', {
      tsconfig: {
        strict: true
      }
    }]
  },
  testTimeout: 10000,
  verbose: true
};
EOF
```

### 3.3 ESLint Configuration

```bash
cat > .eslintrc.js << 'EOF'
module.exports = {
  parser: '@typescript-eslint/parser',
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/recommended-requiring-type-checking',
    'prettier'
  ],
  plugins: ['@typescript-eslint'],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
    project: './tsconfig.json',
    tsconfigRootDir: __dirname,
  },
  env: {
    node: true,
    jest: true,
    es2022: true
  },
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'error',
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/strict-boolean-expressions': 'error',
    'no-console': 'error',
    'no-debugger': 'error'
  },
  ignorePatterns: ['dist', 'coverage', 'node_modules', '*.js']
};
EOF
```

### 3.4 Prettier Configuration

```bash
cat > .prettierrc << 'EOF'
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf"
}
EOF
```

### 3.5 Git Ignore

```bash
cat > .gitignore << 'EOF'
# Dependencies
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Build outputs
dist/
build/
*.tsbuildinfo

# Test coverage
coverage/
*.lcov
.nyc_output/

# Environment files
.env
.env.local
.env.*.local

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Temporary files
tmp/
temp/
*.log
*.tmp

# Debug files
npm-debug.log*
yarn-debug.log*
yarn-error.log*
lerna-debug.log*
EOF
```

### 3.6 Environment Template

```bash
cat > .env.example << 'EOF'
# Environment
NODE_ENV=development
LOG_LEVEL=info

# Codacy Integration
CODACY_PROJECT_TOKEN=your_token_here
CODACY_ORGANIZATION_PROVIDER=gh
CODACY_USERNAME=Your-Org
CODACY_PROJECT_NAME=DevDocAI

# Database
DB_PATH=./data/devdocai.db
DB_ENCRYPTION_KEY=your_encryption_key_here

# Security
JWT_SECRET=your_jwt_secret_here
SESSION_SECRET=your_session_secret_here

# Performance
MAX_WORKERS=4
CACHE_TTL=3600
EOF

# Copy to .env for local development
cp .env.example .env
```

---

## Part 4: NPM Scripts Setup

### 4.1 Update package.json Scripts

```bash
npm pkg set scripts.build="tsc"
npm pkg set scripts.clean="rimraf dist coverage"
npm pkg set scripts.dev="tsx watch src/index.ts"
npm pkg set scripts.start="node dist/index.js"
npm pkg set scripts.test="NODE_ENV=test jest"
npm pkg set scripts.test:watch="NODE_ENV=test jest --watch"
npm pkg set scripts.test:coverage="NODE_ENV=test jest --coverage"
npm pkg set scripts.test:ci="NODE_ENV=test jest --coverage --ci --maxWorkers=2"
npm pkg set scripts.lint="eslint src --ext .ts"
npm pkg set scripts.lint:fix="eslint src --ext .ts --fix"
npm pkg set scripts.prettier:check="prettier --check '**/*.{ts,js,json,md,yml,yaml}'"
npm pkg set scripts.prettier:write="prettier --write '**/*.{ts,js,json,md,yml,yaml}'"
npm pkg set scripts.typecheck="tsc --noEmit"
npm pkg set scripts.quality:check="npm run lint && npm run prettier:check && npm run typecheck"
npm pkg set scripts.quality:fix="npm run lint:fix && npm run prettier:write"
npm pkg set scripts.build:ci="npm run clean && npm run build"
npm pkg set scripts.prepare="husky install"
```

---

## Part 5: Git Hooks Setup

### 5.1 Initialize Husky

```bash
# Initialize husky
npm run prepare

# Create pre-commit hook
cat > .husky/pre-commit << 'EOF'
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

echo "🔍 Running pre-commit checks..."
npx lint-staged
EOF

chmod +x .husky/pre-commit

# Create commit-msg hook
cat > .husky/commit-msg << 'EOF'
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

npx commitlint --edit $1
EOF

chmod +x .husky/commit-msg
```

### 5.2 Lint-Staged Configuration

```bash
cat > .lintstagedrc.json << 'EOF'
{
  "*.ts": [
    "prettier --write",
    "eslint --fix --max-warnings 0"
  ],
  "*.{js,json}": ["prettier --write"],
  "*.md": ["prettier --write"],
  "*.{yml,yaml}": ["prettier --write"]
}
EOF
```

### 5.3 CommitLint Configuration

```bash
cat > commitlint.config.js << 'EOF'
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'build', 'ci', 'chore', 'revert']
    ],
    'subject-case': [2, 'never', ['upper-case', 'pascal-case', 'start-case']],
    'subject-max-length': [2, 'always', 100]
  }
};
EOF
```

---

## Part 6: Source Code Structure

### 6.1 Create Directory Structure

```bash
# Create source directories
mkdir -p src
mkdir -p tests
mkdir -p docs
mkdir -p scripts
mkdir -p .github/workflows
```

### 6.2 Create Initial Source Files

```bash
# Main entry point
cat > src/index.ts << 'EOF'
/**
 * DevDocAI - AI-Powered Documentation System
 * @version 2.0.0
 */

export const VERSION = '2.0.0';

export function getVersion(): string {
  return VERSION;
}

export function initialize(): void {
  // Initialize the application
  const message = `DevDocAI v${VERSION} initialized`;
  // Using console for initialization only
  // eslint-disable-next-line no-console
  console.log(message);
}

// Auto-initialize in development
if (process.env['NODE_ENV'] !== 'test') {
  initialize();
}
EOF

# Create test file
cat > tests/index.test.ts << 'EOF'
import { VERSION, getVersion, initialize } from '../src/index';

describe('DevDocAI Entry Point', () => {
  describe('Version', () => {
    it('should export correct version', () => {
      expect(VERSION).toBe('2.0.0');
    });

    it('should return version through getVersion function', () => {
      expect(getVersion()).toBe('2.0.0');
    });
  });

  describe('Initialize', () => {
    it('should initialize without errors', () => {
      expect(() => initialize()).not.toThrow();
    });

    it('should complete initialization', () => {
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();
      initialize();
      expect(consoleSpy).toHaveBeenCalledWith('DevDocAI v2.0.0 initialized');
      consoleSpy.mockRestore();
    });
  });
});
EOF
```

---

## Part 7: GitHub Actions Setup

### 7.1 CI/CD Pipeline

```bash
cat > .github/workflows/ci.yml << 'EOF'
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Test and Build
    runs-on: ubuntu-latest

    strategy:
      matrix:
        node-version: [18.x, 20.x]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linting
        run: npm run lint

      - name: Run type checking
        run: npm run typecheck

      - name: Run tests with coverage
        run: npm run test:ci

      - name: Build project
        run: npm run build

      - name: Upload coverage to Codacy
        if: matrix.node-version == '20.x'
        uses: codacy/codacy-coverage-reporter-action@v1
        with:
          project-token: ${{ secrets.CODACY_PROJECT_TOKEN }}
          coverage-reports: coverage/lcov.info
EOF
```

### 7.2 Codacy Analysis Workflow

```bash
cat > .github/workflows/codacy-analysis.yml << 'EOF'
name: Codacy Analysis

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  codacy-analysis:
    name: Codacy Security Scan
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Codacy Analysis CLI
        uses: codacy/codacy-analysis-cli-action@v4
        with:
          project-token: ${{ secrets.CODACY_PROJECT_TOKEN }}
          verbose: true
          upload: true
          max-allowed-issues: 2147483647

      - name: Upload SARIF results to GitHub
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
EOF
```

---

## Part 8: Codacy Integration

### 8.1 Create Codacy Configuration

```bash
cat > .codacy.yml << 'EOF'
---
engines:
  duplication:
    enabled: true
    config:
      languages:
        - typescript
        - javascript
  eslint:
    enabled: true
    config:
      extensions:
        - .ts
        - .tsx
        - .js
        - .jsx
  tslint:
    enabled: false
  metrics:
    enabled: true
  coverage:
    enabled: true

exclude_paths:
  - "dist/**"
  - "coverage/**"
  - "node_modules/**"
  - "**/*.test.ts"
  - "**/*.spec.ts"
  - "tests/**"
  - "docs/**"
  - "scripts/**"
EOF
```

### 8.2 Set Up GitHub Secrets

```bash
# On GitHub.com:
# 1. Go to Settings > Secrets and variables > Actions
# 2. Click "New repository secret"
# 3. Name: CODACY_PROJECT_TOKEN
# 4. Value: (Get from Codacy > Settings > Integrations > Project API)
# 5. Click "Add secret"
```

### 8.3 Configure Codacy Project

```
On Codacy.com:
1. Add your repository
2. Go to Settings > Integrations
3. Enable GitHub integration
4. Copy the Project API token
5. Go to Settings > Quality Settings
6. Set up code patterns and quality gates
```

---

## Part 9: Initial Commit and Push

### 9.1 Initialize Git and Push

```bash
# Add all files
git add .

# Create initial commit
git commit -m "feat: initial DevDocAI v2.0.0 setup with complete CI/CD"

# Add remote (if not already added)
git remote add origin https://github.com/YOUR-ORG/DevDocAI.git

# Push to main
git push -u origin main
```

### 9.2 Verify Everything Works

```bash
# Run local tests
npm test

# Check coverage
npm run test:coverage

# Run quality checks
npm run quality:check

# Build the project
npm run build
```

---

## Part 10: Post-Setup Verification

### 10.1 GitHub Actions

- Check Actions tab - all workflows should be green
- CI/CD Pipeline should run on push
- Codacy Analysis should complete

### 10.2 Codacy Dashboard

- Navigate to your Codacy project
- Check that commits show as "Analyzed"
- Verify coverage is displayed
- Review any code quality issues

### 10.3 Local Development

```bash
# Test that everything works
npm run dev         # Development server
npm test           # Tests pass
npm run build      # Build succeeds
npm run lint       # No linting errors
```

---

## Part 11: Additional Quality Tools (Optional)

### 11.1 Add More GitHub Actions

```bash
# Create security scanning
cat > .github/workflows/security.yml << 'EOF'
name: Security Audit

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 1'

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run npm audit
        run: npm audit --audit-level=moderate
EOF
```

### 11.2 Add Pre-push Hook

```bash
cat > .husky/pre-push << 'EOF'
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

echo "🚀 Running pre-push validation..."
npm run test
npm run lint
npm run typecheck
EOF

chmod +x .husky/pre-push
```

---

## Part 12: Documentation

### 12.1 Create README

```bash
cat > README.md << 'EOF'
# DevDocAI

AI-powered documentation system v2.0.0

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/YOUR_PROJECT_ID)](https://app.codacy.com/gh/YOUR-ORG/DevDocAI/dashboard)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/YOUR_PROJECT_ID)](https://app.codacy.com/gh/YOUR-ORG/DevDocAI/dashboard)

## Features
- TypeScript-based architecture
- 100% test coverage goal
- Comprehensive CI/CD pipeline
- Code quality enforcement
- Security scanning

## Getting Started

### Prerequisites
- Node.js >= 18.0.0
- npm >= 9.0.0

### Installation
\`\`\`bash
git clone https://github.com/YOUR-ORG/DevDocAI.git
cd DevDocAI
npm install
\`\`\`

### Development
\`\`\`bash
npm run dev
\`\`\`

### Testing
\`\`\`bash
npm test
npm run test:coverage
\`\`\`

### Building
\`\`\`bash
npm run build
\`\`\`

## Contributing
Please ensure all tests pass and coverage remains above 80% before submitting PRs.

## License
MIT
EOF
```

### 12.2 Create CLAUDE.md for AI Assistance

```bash
cat > CLAUDE.md << 'EOF'
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## Project Overview
DevDocAI v2.0.0 - AI-powered documentation system with zero technical debt policy.

## Development Standards
1. **No TODOs or placeholders** - Complete implementations only
2. **Test-First Development** - Write tests before implementation
3. **100% Coverage Goal** - Maintain high test coverage
4. **Type Safety** - No `any` types, strict TypeScript
5. **Clean Code** - No console.log, proper error handling

## Workflow
1. Always run tests before committing
2. Use conventional commits
3. Ensure all CI checks pass
4. Update documentation for new features

## Quality Gates
- TypeScript: Zero errors
- ESLint: Zero violations
- Tests: Must pass with >80% coverage
- Prettier: All files formatted
EOF
```

---

## Troubleshooting Tips

### If Codacy Shows "Commit not analyzed"

1. Ensure the GitHub webhook is configured in Codacy settings
2. Make sure the CODACY_PROJECT_TOKEN is set in GitHub secrets
3. The codacy-analysis workflow must run successfully
4. Check Codacy project settings for proper GitHub integration

### If Tests Fail

1. Ensure Node.js version matches requirements (>=18)
2. Clear node_modules and reinstall: `rm -rf node_modules && npm ci`
3. Check that all config files are properly formatted

### If GitHub Actions Fail

1. Verify all secrets are properly set
2. Check workflow syntax is valid
3. Ensure permissions are set correctly in repository settings

---

## Summary

This guide provides a complete, working setup that includes:

- ✅ TypeScript with strict configuration
- ✅ Jest testing with coverage
- ✅ ESLint and Prettier formatting
- ✅ Husky git hooks
- ✅ GitHub Actions CI/CD
- ✅ Codacy integration
- ✅ Conventional commits
- ✅ Complete documentation

Following these steps will give you a clean, professional repository with all integrations working from day one.
