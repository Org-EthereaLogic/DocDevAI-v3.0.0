---
metadata:
  id: contributing_guidelines_standard
  name: Contributing Guidelines Template
  description: Comprehensive contributing guidelines for open source projects
  category: projects
  type: contributing
  version: 1.0.0
  author: DevDocAI
  tags: [contributing, guidelines, open-source, collaboration]
  is_custom: false
  is_active: true
variables:
  - name: project_name
    description: Name of the project
    required: true
    type: string
  - name: maintainer_name
    description: Name of the main maintainer
    required: true
    type: string
  - name: repository_url
    description: Repository URL
    required: true
    type: string
  - name: code_of_conduct_url
    description: Code of conduct URL
    required: false
    type: string
  - name: issue_template
    description: Whether issue templates are available
    required: false
    type: boolean
    default: true
---

# Contributing to {{project_name}}

Thank you for your interest in contributing to {{project_name}}! We welcome contributions from everyone.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Community](#community)

## Code of Conduct

<!-- IF code_of_conduct_url -->
This project and everyone participating in it is governed by our [Code of Conduct]({{code_of_conduct_url}}). By participating, you are expected to uphold this code.
<!-- ELSE -->
This project adheres to a Code of Conduct. By participating, you are expected to uphold high standards of respectful and inclusive behavior.
<!-- END IF -->

## Getting Started

### Prerequisites

- Git
- Node.js (version 14 or higher)
- npm or yarn

### First-time Setup

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone {{repository_url}}
   cd {{project_name}}
   ```

3. Add the upstream repository:

   ```bash
   git remote add upstream {{repository_url}}
   ```

4. Install dependencies:

   ```bash
   npm install
   ```

## How to Contribute

### Reporting Bugs

<!-- IF issue_template -->
Before creating bug reports, please check the existing issues to avoid duplicates. When creating a bug report, use our issue template and include:
<!-- ELSE -->
When reporting bugs, please include:
<!-- END IF -->

- **Clear description** of the issue
- **Steps to reproduce** the behavior
- **Expected behavior**
- **Actual behavior**
- **Environment details** (OS, Node version, etc.)
- **Screenshots** (if applicable)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:

1. Check if the enhancement has already been suggested
2. Provide a clear description of the enhancement
3. Explain why this enhancement would be useful
4. Include mockups or examples if applicable

### Contributing Code

1. **Find an issue** to work on or create one
2. **Comment** on the issue to let others know you're working on it
3. **Fork** the repository
4. **Create a branch** for your changes
5. **Make your changes** following our coding standards
6. **Test** your changes thoroughly
7. **Submit a pull request**

## Development Setup

### Local Development

1. Clone and setup the project (see [Getting Started](#getting-started))
2. Create a new branch:

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. Make your changes
4. Run the test suite:

   ```bash
   npm test
   ```

5. Run the linter:

   ```bash
   npm run lint
   ```

### Running Tests

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test path/to/test.js
```

### Building the Project

```bash
# Development build
npm run build:dev

# Production build
npm run build:prod

# Watch mode for development
npm run build:watch
```

## Pull Request Process

1. **Update documentation** if you're changing functionality
2. **Add tests** for new features or bug fixes
3. **Ensure all tests pass** and maintain coverage above 90%
4. **Update CHANGELOG.md** with your changes
5. **Rebase your branch** on the latest main branch
6. **Submit your pull request**

### Pull Request Template

When submitting a PR, please include:

```
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG updated
```

## Style Guidelines

### Code Style

- Use **2 spaces** for indentation
- Use **semicolons** at end of statements
- Use **single quotes** for strings
- Use **camelCase** for variables and functions
- Use **PascalCase** for classes and constructors

### Commit Messages

Follow the [Conventional Commits](https://conventionalcommits.org/) specification:

```
type(scope): description

Examples:
feat(auth): add OAuth2 authentication
fix(api): resolve null pointer exception
docs(readme): update installation instructions
test(unit): add tests for user service
```

### Documentation

- Update README.md for significant changes
- Add JSDoc comments for public APIs
- Include examples in documentation
- Keep documentation up-to-date

## Review Process

All submissions require review. Here's what to expect:

1. **Automated checks** will run (tests, linting, etc.)
2. **Maintainer review** within 48 hours (typically)
3. **Address feedback** and update your PR
4. **Final approval** and merge by maintainers

### Review Criteria

- Code quality and maintainability
- Test coverage and passing tests
- Documentation completeness
- Adherence to project standards
- Performance considerations

## Community

### Communication Channels

- **GitHub Issues** - Bug reports and feature requests
- **GitHub Discussions** - General questions and discussions
- **Discord** - Real-time chat with the community
- **Email** - Direct contact with maintainers

### Recognition

Contributors are recognized in:

- CONTRIBUTORS.md file
- Release notes
- GitHub contributors list
- Special mentions for significant contributions

## Questions?

Don't hesitate to ask questions! You can:

1. Open an issue with the "question" label
2. Start a discussion in GitHub Discussions
3. Reach out to maintainers directly

---

**Thank you for contributing to {{project_name}}!** 🎉

Maintained by {{maintainer_name}} and the {{project_name}} community.
