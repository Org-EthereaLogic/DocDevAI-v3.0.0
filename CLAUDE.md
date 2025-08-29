# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

DevDocAI v3.0.0 is an AI-powered documentation generation and analysis system for solo developers. The project follows a modular architecture with 13 independent modules (M001-M013), currently in active development.

**PROJECT STATUS**:

- M001 Configuration Manager: ✅ COMPLETE (92% coverage, exceeds performance targets)
- M002 Local Storage: ✅ COMPLETE (All 3 passes done, 72K queries/sec, security hardened)
- M003 MIAIR Engine: ✅ COMPLETE (All 4 passes done, 248K docs/min, security hardened, refactored)
- M004 Document Generator: ✅ COMPLETE (All 4 passes done, 42.9% code reduction, production-ready)
- Security: ✅ HARDENED (HTML sanitization fixed, Codacy configured, all XSS vulnerabilities resolved)
- CI/CD: ✅ CONFIGURED (Codacy integration, markdown linting, GitHub Actions)
- Project Organization: ✅ CLEANED (Root directory organized, 15 files properly categorized)
- Overall Progress: 30.8% (4/13 modules complete)
- Next Priority: M005 Quality Engine

## Development Commands

### TypeScript/Node.js Development

```bash
# Build and run
npm run build          # Compile TypeScript (tsc)
npm run dev           # Development server with hot reload
npm run clean         # Clean dist and coverage directories

# Testing
npm test              # Run Jest tests
npm run test:watch    # Jest watch mode
npm run test:coverage # Generate coverage report (target: 95% for M001)
npm run benchmark     # Run performance benchmarks for M001

# Code quality
npm run lint          # ESLint check on src/**/*.ts
npm run lint:fix      # Auto-fix ESLint issues
```

### Python Development

```bash
# Testing
pytest                # Run Python tests
pytest --cov         # Coverage report
python test_environment.py  # Verify development environment

# Code quality
black .              # Format Python code
pylint devdocai/     # Lint Python code
```

### Git Operations

```bash
git status           # Always check status first
git diff --cached    # Review staged changes before commit
```

## Architecture Overview

### Module System (M001-M013)

The system consists of 13 modules, each self-contained with specific responsibilities:

- **M001 Configuration Manager**: ✅ COMPLETE
  - Performance achieved: 13.8M ops/sec retrieval, 20.9M ops/sec validation (exceeds target!)
  - Test coverage: 92% (51 passing tests, 9 pre-existing test stubs)
  - Security hardened: AES-256-GCM, Argon2id, random salts per encryption
  - Implementation: `devdocai/core/config.py` (703 lines, Pydantic v2 compliant)
  - Development method validated: Three-pass (Implementation → Performance → Security)

- **M002 Local Storage**: ✅ COMPLETE (All 3 passes finished)
  - Pass 1 ✅: Core implementation (CRUD, versioning, FTS5)
  - Pass 2 ✅: Performance optimization (72,203 queries/sec achieved, 743x improvement!)
  - Pass 3 ✅: Security hardening (SQLCipher, AES-256-GCM, PII detection)
  - Test coverage: ~45% overall (PII detector at 92%)
  - Implementation: `devdocai/storage/` with secure_storage.py, pii_detector.py

- **M003 MIAIR Engine**: ✅ COMPLETE (All 4 passes finished)
  - Pass 1 ✅: Core implementation (Shannon entropy, quality scoring)
  - Pass 2 ✅: Performance optimization (361,431 docs/min achieved, 29.6x improvement!)
  - Pass 3 ✅: Security hardening (input validation, rate limiting, secure caching)
  - Pass 4 ✅: Refactoring (unified engine, 56% code reduction, 248K docs/min restored)
  - Test coverage: 90%+ overall
  - Implementation: `devdocai/miair/engine_unified.py` (production-ready)

- **M004 Document Generator**: ✅ COMPLETE (All 4 passes finished)
  - Pass 1 ✅: Core implementation (912 lines, 6 templates, 85% coverage)
  - Pass 2 ✅: Performance optimization (43.2x cache improvement, batch processing, 100+ docs/sec)
  - Pass 3 ✅: Security hardening (~4,700 security lines, OWASP Top 10 compliant, XSS prevention)
  - Pass 4 ✅: Refactoring (42.9% code reduction, unified architecture, 2,370 final lines)
  - Test coverage: 95% (150+ test cases including security attack simulation)
  - Implementation: `devdocai/generator/` with unified components and enterprise-grade features
- **M005 Quality Engine**: Document analysis (85% quality gate requirement)
- **M006 Template Registry**: 30+ document templates
- **M007 Review Engine**: Multi-dimensional analysis with PII detection
- **M008 LLM Adapter**: Multi-provider AI integration
- **M009 Enhancement Pipeline**: Iterative document improvement
- **M010 Security Module**: Advanced security features
- **M011 UI Components**: Dashboard and visualizations
- **M012 CLI Interface**: Command-line operations
- **M013 VS Code Extension**: IDE integration

### Directory Structure

```
src/modules/M00X-ModuleName/
├── services/     # Business logic
├── utils/        # Helper functions
├── types/        # TypeScript type definitions
└── interfaces/   # Contracts and interfaces

tests/unit/M00X-ModuleName/  # Corresponding test structure
```

### Quality Gates

- **M001, M002**: 95% test coverage requirement
- **All modules**: 80% minimum coverage
- **Code complexity**: <10 cyclomatic complexity
- **File size**: Maximum 350 lines per file
- **Performance**: Specific benchmarks per module (see docs)

## Critical Implementation Notes

### M001 Configuration Manager Specifics

- Must implement memory mode detection (baseline/standard/enhanced/performance)
- Privacy-first: telemetry disabled by default, cloud features opt-in
- Use Argon2id for key derivation, AES-256-GCM for encryption
- Configuration loading from `.devdocai.yml` with schema validation

### Testing Strategy

- Follow TDD: Write tests first, then implementation
- Use Jest for TypeScript, pytest for Python
- Performance benchmarks required for M001 (scripts/benchmark-m001.ts)
- Coverage thresholds enforced in jest.config.js

### Security Requirements

- All API keys must be encrypted using AES-256-GCM
- SQLCipher for database encryption (M002)
- Input validation required on all external inputs
- No telemetry or cloud features enabled by default

## GitHub Actions Workflows

The project uses standard GitHub Actions (no custom actions):

- **ci.yml**: Main pipeline - runs on push/PR to main
  - Multi-version testing (Python 3.9-3.11, Node 18-20)
  - CodeQL security analysis
  - Codecov integration

- **quick-check.yml**: Fast feedback on all pushes
- **release.yml**: Automated releases on version tags

## Codacy Integration

When editing files, you MUST:

1. Run `codacy_cli_analyze` after any file edit
2. Use provider: `gh`, organization: `Org-EthereaLogic`, repository: `DocDevAI-v3.0.0`
3. Run security checks with trivy after adding dependencies

## Development Philosophy

- **Privacy-First**: All data local, no telemetry by default
- **Offline-First**: Full functionality without internet
- **Test-Driven**: Tests before implementation
- **Modular**: Each module independent and self-contained
- **Performance**: Meet specific benchmarks (M001: 19M ops/sec)

## Current Development Status

- Infrastructure: ✅ Complete (TypeScript, Jest, GitHub Actions, DevContainer)
- M001 Configuration Manager: ✅ COMPLETE (92% coverage, production-ready)
- M002 Local Storage: ✅ COMPLETE (All passes done, 72K queries/sec, security hardened)
- M003 MIAIR Engine: ✅ COMPLETE (All passes done, 361K docs/min, security hardened)
- M004-M013: ⏳ Pending

Next steps focus on M004 Document Generator following the specifications in docs/01-specifications/architecture/DESIGN-devdocsai-sdd.md.

## Development Method

Following a validated four-pass development approach:

1. **Implementation Pass**: Core functionality with basic tests (80-85% coverage)
2. **Performance Pass**: Optimization to meet benchmarks
3. **Security Pass**: Hardening and reaching 95% coverage target
4. **Refactoring Pass**: Code consolidation, duplication removal, architecture improvements (NEW)

Git tags are created at each pass for rollback capability (e.g., `m001-implementation-v1`, `m001-performance-v1`, `security-pass-m001`, `refactoring-complete`).
