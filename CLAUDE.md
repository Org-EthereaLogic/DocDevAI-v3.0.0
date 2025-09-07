# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

DevDocAI v3.0.0 is a **Python-based** AI-powered documentation generation and analysis system for solo developers. This project follows a **design-first approach** with strict adherence to design document specifications.

**CRITICAL**: This project has been **RESTARTED FROM CLEAN SLATE** (September 7, 2025). All implementation must be built from scratch following the exact specifications in the design documents located in `docs/`.

## Current Project Status

**🎯 CLEAN SLATE - READY FOR DESIGN-COMPLIANT IMPLEMENTATION**

- **Implementation Status**: **0% Complete** - Complete clean restart achieved
- **Repository Status**: ✅ **COMPLETELY CLEAN** - All previous implementation removed
- **Design Status**: **Complete** - 52 comprehensive design documents ready
- **Technology Stack**: **Python 3.8+ ONLY** (previous TypeScript attempts were incorrect)
- **Architecture**: **To be built** - Following docs/04-reference/COMPREHENSIVE_PROJECT_FINDINGS.md
- **Development Method**: **Enhanced 4-Pass TDD** - Proven methodology from design docs
- **Next Step**: **Begin M001 Configuration Manager** - Foundation module implementation

## Why the Restart?

**Architectural Drift Discovered**: Previous implementation had fundamental issues:
- ❌ M004 Document Generator used template substitution instead of AI-powered generation
- ❌ Missing M008 LLM Adapter (critical dependency for AI functionality)
- ❌ Wrong technology stack (TypeScript instead of Python as specified in design docs)
- ❌ Only 23% compliance with design document specifications
- ✅ **Solution**: Complete restart following design documents exactly

## Single Source of Truth: Design Documents

### Mandatory Reading Order
1. **[Comprehensive Project Findings](docs/04-reference/COMPREHENSIVE_PROJECT_FINDINGS.md)** - Python architecture overview
2. **[Product Requirements Document (PRD)](docs/01-specifications/requirements/DESIGN-devdocai-prd.md)** - What we're building
3. **[Software Requirements Specification (SRS)](docs/01-specifications/requirements/DESIGN-devdocai-srs.md)** - Detailed requirements
4. **[Software Design Document (SDD)](docs/01-specifications/architecture/DESIGN-devdocsai-sdd.md)** - How we're building it
5. **[Architecture Document](docs/01-specifications/architecture/DESIGN-devdocsai-architecture.md)** - System architecture
6. **[User Stories](docs/01-specifications/requirements/DESIGN-devdocsai-user-stories.md)** - User requirements

### Design Compliance Rules

**🚫 NEVER DO:**
- Implement features not specified in design documents
- Change architecture without design document update
- Skip any steps outlined in build instructions  
- Add dependencies not specified in design docs
- Create files not outlined in project structure
- Deviate from specified naming conventions
- Use TypeScript/Node.js (design specifies Python 3.8+ only)

**✅ ALWAYS DO:**
- Reference specific design document sections when implementing
- Follow the exact Python architecture from `docs/04-reference/`
- Implement test-driven development as specified
- Meet all quality gates (coverage, performance, security)
- Use only Python 3.8+ and specified frameworks
- Follow the modular architecture exactly as designed

## Implementation Roadmap

### Phase 1: Foundation (Start Here)
**Dependency Order - Critical Path:**

1. **M001: Configuration Manager** (INDEPENDENT - Start here)
   - Privacy-first defaults (local-only, no telemetry) 
   - Memory mode detection (4 modes based on available RAM)
   - Encrypted API key storage (AES-256-GCM)
   - YAML configuration with Pydantic validation

2. **M008: LLM Adapter** (Depends: M001) - **CRITICAL FOR AI**
   - Multi-provider support (OpenAI, Anthropic, Google, Local fallback)
   - Cost management and budget enforcement
   - Smart routing and response caching
   - **Essential for M004 AI-powered document generation**

3. **M002: Local Storage System** (Depends: M001)
   - SQLite with SQLCipher encryption
   - Document versioning and full-text search
   - Integration with M001 configuration

### Phase 2: Core Generation
4. **M004: Document Generator** (Depends: M001, M002, M008)
   - **AI-POWERED GENERATION** (uses M008 for LLM calls)
   - Templates guide prompts, NOT content substitution
   - 40+ document types with AI synthesis

5. **M003: MIAIR Engine** (Depends: M001, M002, M008)
   - Shannon entropy optimization
   - Mathematical quality improvement
   - AI-powered refinement

### Phase 3: Analysis & Enhancement (6 more modules)
6-13. **Remaining modules** following dependency chain

## Python Package Structure (Per Design Docs)

```
devdocai/
├── core/
│   ├── config.py          # M001: Configuration Manager
│   ├── storage.py         # M002: Local Storage (SQLite + encryption)
│   ├── generator.py       # M004: Document Generator (AI-powered)
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
├── cli.py                # Command-line interface
└── main.py               # Entry point
```

## Development Commands

### Environment Setup (To Be Created)
```bash
# Create new Python environment
python -m venv venv
source venv/bin/activate  # Linux/Mac

# Install dependencies (to be determined from design docs)
pip install -r requirements.txt

# Testing (to be implemented)
pytest --cov=devdocai --cov-report=html

# Code quality (to be configured)
black devdocai/
pylint devdocai/
mypy devdocai/
```

## Quality Gates (Per Design Docs)

- **All modules**: 85-95% test coverage requirement
- **Code complexity**: <10 cyclomatic complexity
- **Performance**: Specific benchmarks per module (M003: 248K docs/min)
- **Technology**: Python 3.8+ only (no TypeScript/Node.js)
- **Security**: AES-256-GCM encryption, privacy-first defaults

## Development Method

**Enhanced 4-Pass TDD Development Methodology:**

1. **Pass 1**: Core Implementation (TDD with 80% coverage)
2. **Pass 2**: Performance Optimization (meet benchmarks)
3. **Pass 3**: Security Hardening (95% coverage, OWASP where applicable)
4. **Pass 4**: Refactoring & Integration (40-50% code reduction target)

Git tags at each pass for rollback capability (e.g., `m001-pass1-v1`)

## Critical Implementation Notes

### M001 Configuration Manager Specifics
- Must implement in Python (previous TypeScript attempts were wrong)
- Privacy-first: telemetry disabled by default
- Use Python `cryptography` library for encryption
- Configuration loading from `.devdocai.yml` with pydantic validation

### M008 LLM Adapter Requirements (Critical)
- **ESSENTIAL for M004**: M004 cannot work without M008 LLM integration
- Multi-provider support with cost management
- Response caching and smart routing
- Local fallback when APIs unavailable or budget exhausted

### M004 Document Generator Requirements
- **AI-POWERED**: Uses M008 to call LLMs for content generation
- **NOT template substitution**: Templates guide AI prompts only
- Fails gracefully with error messages when LLMs unavailable
- This was the core architectural issue in previous implementation

## Repository Status

**Current State**: Complete clean slate achieved
- ✅ Design documentation complete (52 files)
- ❌ No implementation code (ready for fresh start)
- ❌ No configuration files (to be created from design specs)
- ❌ No test files (to be implemented with TDD approach)

**Git History**: Previous implementation work preserved in commits for reference, but completely removed from working directory.

## Development Philosophy

- **Privacy-First**: All data local, no telemetry by default
- **Offline-First**: Full functionality without internet
- **Test-Driven**: Tests before implementation (pytest)
- **Modular**: Each module independent and self-contained
- **Performance**: Meet specific benchmarks per design docs
- **AI-Powered**: Python-based ML/AI processing via MIAIR Engine and LLM Adapter
- **Design-First**: Strict adherence to documented architecture

# Important Instructions

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
ALWAYS follow the Python architecture specified in the design documents.
NEVER use TypeScript/Node.js - this project is Python-based as per design specifications.
CRITICAL: All implementation must use AI-powered generation via M008 LLM Adapter, not template substitution.