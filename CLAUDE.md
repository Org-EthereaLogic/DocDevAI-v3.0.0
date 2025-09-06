# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

DevDocAI v3.0.0 is a **Python-based** AI-powered documentation generation and analysis system for solo developers. This is a **clean slate development branch** that follows strict design document compliance.

**CRITICAL**: This project follows a **design-first approach**. All implementation must adhere exactly to the specifications in the design documents located in `docs/`.

## Current Project Status

**🎯 CLEAN SLATE PYTHON REBUILD - READY TO BEGIN**

- **Implementation Status**: 0% Complete (Clean slate - previous TypeScript build removed)
- **Design Status**: Complete and approved (Python-based architecture)
- **Technology Stack**: Python 3.8+ (as specified in design docs)
- **Architecture**: Python packages following `docs/04-reference/COMPREHENSIVE_PROJECT_FINDINGS.md`
- **Next Step**: Begin M001 Configuration Manager in Python

**What exists:**
✅ Complete design documentation (PRD v3.6.0, SRS v3.6.0, SDD v3.5.0, Architecture v3.5.0)
✅ Python-based architecture specification in `docs/04-reference/`
✅ CI/CD pipeline infrastructure (successfully identified architectural drift)
✅ Comprehensive design compliance framework
✅21 User Stories (US-001 through US-021) ready for implementation

**Previous Build Status:**
A previous TypeScript-based implementation existed but was architecturally incompatible with design specifications. The CI/CD pipeline successfully identified this drift, and we are now proceeding with the correct Python-based implementation as designed.

## Single Source of Truth: Design Documents

### Mandatory Reading Order
1. **[Product Requirements Document (PRD)](docs/01-specifications/requirements/DESIGN-devdocai-prd.md)** - What we're building
2. **[Software Requirements Specification (SRS)](docs/01-specifications/requirements/DESIGN-devdocai-srs.md)** - Detailed requirements
3. **[Software Design Document (SDD)](docs/01-specifications/architecture/DESIGN-devdocsai-sdd.md)** - How we're building it
4. **[Architecture Document](docs/01-specifications/architecture/DESIGN-devdocsai-architecture.md)** - System architecture
5. **[User Stories](docs/01-specifications/requirements/DESIGN-devdocsai-user-stories.md)** - User requirements
6. **[Comprehensive Project Findings](docs/04-reference/COMPREHENSIVE_PROJECT_FINDINGS.md)** - Python architecture specification

### Design Compliance Rules

**🚫 NEVER DO:**
- Implement features not specified in design documents
- Change architecture without design document update
- Skip any steps outlined in build instructions  
- Add dependencies not specified in design docs
- Create files not outlined in project structure
- Deviate from specified naming conventions
- Use TypeScript/Node.js (design specifies Python)

**✅ ALWAYS DO:**
- Reference specific design document sections when implementing
- Follow the exact Python architecture from `docs/04-reference/`
- Implement test-driven development as specified
- Meet all quality gates (coverage, performance, security)
- Use only Python 3.8+ and specified frameworks
- Follow the modular architecture exactly as designed

## Development Commands

### Python Development (Primary)

```bash
# Environment setup
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR: venv\Scripts\activate  # Windows

# Dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Testing
pytest                      # Run Python tests
pytest --cov=devdocai      # Coverage report (target: 95%)
pytest --cov=devdocai --cov-report=html  # HTML coverage report

# Code quality
black devdocai/            # Format Python code
pylint devdocai/           # Lint Python code
mypy devdocai/             # Type checking

# Development
python -m devdocai --help # Run CLI
python -m devdocai.cli     # Alternative CLI entry point
```

### Build & Package

```bash
# Build package
python -m build

# Install for development
pip install -e .

# Run specific modules
python -m devdocai.core.config    # M001: Configuration Manager
python -m devdocai.intelligence.miair  # M003: MIAIR Engine
```

### Git Operations

```bash
git status           # Always check status first
git diff --cached    # Review staged changes before commit
```

## Architecture Overview

### Python Package Structure (Per Design Docs)

```
devdocai/
├── core/
│   ├── config.py          # M001: Configuration Manager
│   ├── storage.py         # M002: Local Storage (SQLite + encryption)
│   ├── generator.py       # M004: Document Generator
│   ├── tracking.py        # M005: Tracking Matrix
│   ├── suite.py          # M006: Suite Manager
│   └── review.py         # M007: Review Engine
├── intelligence/
│   ├── miair.py          # M003: MIAIR Engine (entropy optimization)
│   ├── llm_adapter.py    # M008: LLM Adapter with cost management
│   └── enhance.py        # M009: Enhancement Pipeline
├── compliance/
│   ├── sbom.py           # M010: SBOM Generator
│   ├── pii.py            # PII Detection (95% accuracy target)
│   └── dsr.py            # Data Subject Rights handler
├── operations/
│   ├── batch.py          # M011: Batch Operations
│   ├── version.py        # M012: Version Control Integration
│   └── marketplace.py    # M013: Template Marketplace
├── cli.py                # Command-line interface (Click/argparse)
└── main.py               # Entry point
```

### Module System (M001-M013)

Each module is self-contained with specific responsibilities as defined in the SDD:

- **M001 Configuration Manager**: Python-based config with validation
- **M002 Local Storage**: SQLite with encryption, not TypeScript
- **M003 MIAIR Engine**: Python ML/AI processing (requires Python)
- **M004-M013**: All specified as Python modules in design docs

### Quality Gates

- **All modules**: 95% test coverage requirement (as per design docs)
- **Code complexity**: <10 cyclomatic complexity
- **Performance**: Specific benchmarks per module (M003: 248K docs/min)
- **Technology**: Python 3.8+ only (no TypeScript/Node.js)

## Critical Implementation Notes

### M001 Configuration Manager Specifics
- Must implement in Python (not TypeScript as previously attempted)
- Privacy-first: telemetry disabled by default
- Use Python cryptography library for encryption
- Configuration loading from `.devdocai.yml` with pydantic validation

### M003 MIAIR Engine Requirements
- **CRITICAL**: Requires Python for ML/AI processing
- Shannon entropy calculations in Python
- This is why the entire system must be Python-based

### Testing Strategy
- Follow TDD: Write tests first, then implementation
- Use pytest for Python testing
- Performance benchmarks required for each module
- Coverage thresholds enforced in pytest.ini

### Security Requirements
- All API keys encrypted using Python cryptography
- SQLCipher for database encryption (M002)
- Input validation on all external inputs
- No telemetry by default

## GitHub Actions Workflows

The CI/CD pipeline successfully identified the TypeScript architectural drift and is now configured for Python development:

- **ci.yml**: Main pipeline - Python testing and validation
- **python-tests.yml**: Python-specific testing pipeline  
- **security-scan.yml**: Python security analysis

## Current Development Focus

### Phase 1: M001 Configuration Manager (Python)
Following the proven Enhanced 5-Pass TDD Development Methodology adapted for Python:

1. **Pass 0**: Design Validation (verify Python architecture)
2. **Pass 1**: TDD Implementation (pytest, 95% coverage)
3. **Pass 2**: Performance Optimization (meet Python benchmarks)
4. **Pass 3**: Security Hardening (Python cryptography)
5. **Pass 4**: Refactoring (Python code quality)
6. **Pass 5**: Real-World Testing (production readiness)

## Development Philosophy

- **Privacy-First**: All data local, no telemetry by default
- **Offline-First**: Full functionality without internet
- **Test-Driven**: Tests before implementation (pytest)
- **Modular**: Each module independent and self-contained
- **Performance**: Meet specific benchmarks (M003: 248K docs/min)
- **AI-Powered**: Python-based ML/AI processing via MIAIR Engine
- **Design-First**: Strict adherence to documented architecture

## Development Method

Following the validated Enhanced 5-Pass TDD Development Methodology:

1. **Pass 0**: Design Validation (0.5 days)
2. **Pass 1**: TDD Implementation (1.5 days, RED-GREEN-REFACTOR)
3. **Pass 2**: Performance Optimization (1 day)
4. **Pass 3**: Security Hardening (1 day)
5. **Pass 4**: Mandatory Refactoring (1 day, 40-50% code reduction)
6. **Pass 5**: Real-World Testing (1 day)

Total per module: 6 days | Total project: 30 development days for all 13 modules

Git tags created at each pass for rollback capability (e.g., `m001-python-implementation-v1`)

# Important Instructions

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
ALWAYS follow the Python architecture specified in the design documents.
NEVER use TypeScript/Node.js - this project is Python-based as per design specifications.