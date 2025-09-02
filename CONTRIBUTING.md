# Contributing to DevDocAI

Thank you for your interest in contributing to DevDocAI! This document provides guidelines and instructions for contributing to the project.

## 🚀 Quick Start

1. **Fork the repository** and clone your fork
2. **Install dependencies**:
   ```bash
   npm install           # Node.js dependencies
   pip install -e .      # Python package in development mode
   ```
3. **Run tests** to ensure everything works:
   ```bash
   npm test             # TypeScript/React tests
   pytest               # Python tests
   ```

## 📁 Project Structure

```
DevDocAI/
├── src/                    # TypeScript/React source code
│   ├── modules/           # M011 UI Components
│   ├── components/        # React components
│   └── services/          # Service layer
├── devdocai/              # Python source code
│   ├── core/             # M001-M002 Core modules
│   ├── generator/        # M004 Document Generator
│   ├── quality/          # M005 Quality Engine
│   └── security/         # M010 Security Module
├── tests/                 # Test files
├── docs/                  # Documentation
│   ├── 02-implementation/ # Development docs
│   └── PROJECT_COMPLETE_2025-09-02.md
└── archive/               # Historical development artifacts
```

## 🔧 Development Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+
- Git
- VS Code (recommended)

### Environment Setup

1. Copy `.env.example` to `.env` and configure
2. Install development tools:
   ```bash
   npm install -g typescript eslint
   pip install black pytest pylint
   ```

### Running the Application

```bash
# Web application
npm run dev:react        # Starts at http://localhost:3000

# CLI tool
npm run dev             # Development mode with hot reload

# VS Code Extension
# Open in VS Code and press F5 to debug
```

## 📝 Code Style

### TypeScript/JavaScript
- Use ESLint: `npm run lint`
- Auto-fix: `npm run lint:fix`
- Follow existing patterns in the codebase

### Python
- Use Black formatter: `black .`
- Use pylint: `pylint devdocai/`
- Follow PEP 8 guidelines

### Commits
- Use conventional commits format
- Examples:
  - `feat: add new template type`
  - `fix: resolve memory leak in M003`
  - `docs: update API documentation`
  - `refactor: simplify security module`

## 🧪 Testing

### Running Tests

```bash
# All tests
npm test                # TypeScript tests
pytest                  # Python tests

# With coverage
npm run test:coverage   # TypeScript coverage
pytest --cov           # Python coverage
```

### Writing Tests

- Place tests in `tests/` directory
- Follow naming convention: `test_*.py` or `*.test.ts`
- Aim for 80%+ coverage on new code
- Include both unit and integration tests

## 🏗️ Module Development

DevDocAI uses a modular architecture with 13 modules (M001-M013). When contributing:

### Four-Pass Development Method

1. **Implementation Pass**: Core functionality (80-85% coverage)
2. **Performance Pass**: Optimization to meet benchmarks
3. **Security Pass**: Hardening and security review
4. **Refactoring Pass**: Code cleanup and architecture improvements

### Module Guidelines

- Each module should be independent
- Follow the existing module structure
- Document public APIs
- Include comprehensive tests
- Meet performance benchmarks (see module specs)

## 🔒 Security

- Never commit secrets or API keys
- Use environment variables for configuration
- Follow OWASP guidelines
- Run security scans: `npm audit`
- Report security issues privately to maintainers

## 📖 Documentation

- Update relevant documentation when making changes
- Include JSDoc/docstrings for public APIs
- Update README if adding new features
- Add examples for complex functionality

## 🤝 Pull Request Process

1. **Create a feature branch**: `git checkout -b feature/your-feature`
2. **Make your changes** following the guidelines above
3. **Run tests and linting** to ensure quality
4. **Update documentation** as needed
5. **Commit with descriptive message**
6. **Push to your fork** and create a Pull Request
7. **Describe your changes** in the PR description
8. **Link any related issues**

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No secrets or keys committed
- [ ] Performance benchmarks met (if applicable)
- [ ] Security considerations addressed

## 📊 Performance Benchmarks

Key performance targets to maintain:

- M001 Config: 19M ops/sec retrieval
- M002 Storage: 70K+ queries/sec
- M003 MIAIR: 200K+ docs/min
- M005 Quality: <10ms for analysis
- M011 UI: <3s initial load

## 🐛 Reporting Issues

Please use GitHub Issues to report bugs:

1. Search existing issues first
2. Include reproduction steps
3. Provide system information
4. Include error messages/logs
5. Add relevant labels

## 💡 Feature Requests

We welcome feature suggestions! Please:

1. Check if already requested
2. Explain the use case
3. Provide examples if possible
4. Be open to discussion

## 📜 License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.

## 🙏 Recognition

Contributors will be recognized in:
- GitHub contributors page
- Release notes
- Project documentation

## 📮 Contact

- GitHub Issues: Bug reports and feature requests
- Discussions: General questions and ideas
- Security: Report vulnerabilities privately

Thank you for helping make DevDocAI better! 🎉