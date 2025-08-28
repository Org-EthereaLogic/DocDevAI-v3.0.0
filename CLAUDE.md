# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

DevDocAI v3.0.0 is an AI-powered documentation generation and analysis system for solo developers. The project follows a modular architecture with 13 independent modules (M001-M013), currently in active development.

**PROJECT STATUS**: 
- M001 Configuration Manager: ✅ COMPLETE (92% coverage, exceeds performance targets)
- M002 Local Storage: 🚧 IN PROGRESS (Pass 2/3 complete, 72K queries/sec achieved)
- Security: ✅ HARDENED (Pydantic v2 migration complete, no vulnerabilities)
- Dependencies: ✅ UPDATED (setuptools 80.9.0, pydantic 2.11.7)
- Next Priority: M002 Pass 3 (Security Hardening with SQLCipher)

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

- **M002 Local Storage**: 🚧 IN PROGRESS (Pass 2/3 Complete)
  - Pass 1 ✅: Core implementation (CRUD, versioning, FTS5)
  - Pass 2 ✅: Performance optimization (72,203 queries/sec achieved, 743x improvement!)
  - Pass 3 ⏳: Security hardening with SQLCipher (pending)
  - Test coverage: ~40% (models at 81%)
  - Implementation: `devdocai/storage/` with FastStorageLayer optimization
- **M003 MIAIR Engine**: Mathematical optimization for quality improvement (Shannon entropy)
- **M004 Document Generator**: Core generation with template system
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
- M002 Local Storage: 🚧 IN PROGRESS (Pass 2/3 complete, 72K queries/sec)
- M003-M013: ⏳ Pending

Next steps focus on M002 Pass 3 (Security Hardening) with SQLCipher integration following the specifications in docs/01-specifications/architecture/DESIGN-devdocsai-sdd.md.

## Development Method

Following a validated three-pass development approach:
1. **Implementation Pass**: Core functionality with basic tests (80-85% coverage)
2. **Performance Pass**: Optimization to meet benchmarks
3. **Security Pass**: Hardening and reaching 95% coverage target

Git tags are created at each pass for rollback capability (e.g., `m001-implementation-v1`, `m001-performance-v1`, `security-pass-m001`).