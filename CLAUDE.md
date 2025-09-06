# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

DevDocAI v3.0.0 is an AI-powered documentation generation and analysis system for solo developers. This is a **clean slate development branch** that follows strict design document compliance to prevent architectural drift.

**CRITICAL**: This project follows a **design-first approach**. All implementation must adhere exactly to the specifications in the design documents located in `docs/01-specifications/`.

## Current Project Status

**🎉 MODULE 1: CORE INFRASTRUCTURE - PATHFINDER COMPLETE! 🎉**

- **Implementation Status**: 7.7% Complete (Module 1 finished - all 6 passes done!)
- **Design Status**: Complete and approved
- **Development Method**: [Enhanced 5-Pass TDD Methodology](docs/02-implementation/planning/PHASE_1_CLI_ENHANCED_5PASS_PLAN.md) ✅ **VALIDATED**
- **Next Step**: Ready for Module 2-13 development using proven pathfinder patterns
- **Repository State**: Production-ready Module 1 with CI/CD infrastructure

**What exists:**
✅ Complete design documentation (PRD, SRS, SDD, Architecture)
✅ Enhanced 5-Pass implementation plan - **PROVEN SUCCESSFUL**
✅ **Module 1: Core Infrastructure - PRODUCTION READY** (6 unified components, 2,583 lines tests)
✅ **CI/CD Pathfinder Infrastructure** (7 GitHub Actions workflows, module generator)
✅ **Comprehensive Test Framework** (73 test cases, 95%+ coverage)
✅ **Unified Architecture Pattern** (60% code reduction achieved!)

**Module 1 Achievements:**
✅ **Pass 0**: Design Validation - Architecture approved
✅ **Pass 1**: TDD Implementation (RED-GREEN-REFACTOR, 264 tests)
✅ **Pass 2**: Performance Optimization (all targets exceeded)
✅ **Pass 3**: Security Hardening (enterprise-grade, <10% overhead)
✅ **Pass 4**: Refactoring (60% code reduction - exceeded 40-50% target!)
✅ **Pass 5**: Real-World Testing (PRODUCTION READY certification)

## Single Source of Truth: Design Documents

### Mandatory Reading Order
1. **[Product Requirements Document (PRD)](docs/01-specifications/requirements/DESIGN-devdocai-prd.md)** - What we're building
2. **[Software Requirements Specification (SRS)](docs/01-specifications/requirements/DESIGN-devdocai-srs.md)** - Detailed requirements
3. **[Software Design Document (SDD)](docs/01-specifications/architecture/DESIGN-devdocsai-sdd.md)** - How we're building it
4. **[Architecture Document](docs/01-specifications/architecture/DESIGN-devdocsai-architecture.md)** - System architecture
5. **[User Stories](docs/01-specifications/requirements/DESIGN-devdocsai-user-stories.md)** - User requirements
6. **[Build Instructions](docs/03-guides/deployment/DESIGN-devdocai-build-instructions.md)** - Implementation phases

### Design Compliance Rules

**🚫 NEVER DO:**
- Implement features not specified in design documents
- Change architecture without design document update
- Skip any steps outlined in build instructions  
- Add dependencies not specified in design docs
- Create files not outlined in project structure
- Deviate from specified naming conventions

**✅ ALWAYS DO:**
- Reference specific design document sections when implementing
- Follow the exact development phases outlined
- Implement test-driven development as specified
- Meet all quality gates (coverage, performance, security)
- Use only specified technologies and frameworks
- Follow the modular architecture exactly as designed

## Development Phases (Strict Sequence)

### Phase 1: CLI Interface
**Design Reference**: SDD Section 4.1  
**Implementation**: Follow build instructions exactly  
**Quality Gates**: 95% test coverage, performance benchmarks  

### Phase 2: Web Dashboard  
**Design Reference**: User Stories US-001 through US-006  
**Implementation**: React + TypeScript as specified  
**Quality Gates**: Accessibility compliance, responsive design  

### Phase 3: AI Integration
**Design Reference**: SDD Section 3.3  
**Implementation**: OpenAI/Anthropic integration as designed  
**Quality Gates**: Response time <2 seconds, cost controls  

### Phase 4: Template System
**Design Reference**: SDD Section 3.4  
**Implementation**: 35+ templates as specified  
**Quality Gates**: Template validation, generation accuracy  

### Phase 5: VS Code Extension
**Design Reference**: SDD Section 4.3  
**Implementation**: Follow extension architecture  
**Quality Gates**: IDE integration, performance  

### Phase 6: Performance Optimization
**Design Reference**: SDD Performance Requirements  
**Implementation**: Meet all benchmark targets  
**Quality Gates**: 248,000 documents/minute target  

## Architecture Compliance

### Module Structure (Mandatory)
```
src/
├── cli/           # CLI interface (Phase 1)
├── web/           # Web dashboard (Phase 2)  
├── ai/            # AI integration (Phase 3)
├── templates/     # Template system (Phase 4)
├── vscode/        # VS Code extension (Phase 5)
└── core/          # Shared utilities
```

### Quality Requirements
- **Test Coverage**: 95% minimum for core modules
- **Performance**: Meet specific benchmarks in design docs
- **Security**: Privacy-first, local-only processing
- **Code Quality**: <10 cyclomatic complexity
- **Documentation**: All public APIs documented

## Warning Signs of Architectural Drift

**🚨 STOP IMMEDIATELY if you see:**
- Implementation not matching design document specifications
- New dependencies not listed in design docs
- Architecture changes without design doc updates
- Features being added beyond specified requirements
- Quality gates being skipped or lowered
- Development phases being done out of order

## Agent Usage Guidelines

See [AGENTS.md](AGENTS.md) for specific agent workflow specifications. All agents must follow design document compliance rules.

## Error Recovery

If architectural drift is detected:
1. **HALT** all development immediately  
2. Compare current implementation to design docs
3. Document all deviations found
4. Create rollback plan to compliant state
5. Update implementation to match design exactly
6. Resume development only after compliance restored

## Success Metrics

**Target Goals - Module 1 ACHIEVED:**
- **Design Compliance**: 100% traceability to design documents ✅ **ACHIEVED** - All components follow SDD specifications
- **Phase Completion**: Module 1 pathfinder completed in specified order ✅ **ACHIEVED** - All 6 passes successful
- **Quality Gates**: All benchmarks met as specified ✅ **EXCEEDED** - 60% code reduction achieved
- **Zero Drift**: No architectural deviations from design ✅ **MAINTAINED** - Perfect design compliance

**Next Phase Target Goals:**
- **Module Development**: Complete Modules 2-13 using pathfinder patterns (Estimated: 12-16 days each)
- **CI/CD Integration**: Automated quality gates and testing (Infrastructure complete)
- **Performance Validation**: Meet all remaining performance benchmarks

## Development Commands

### Current Module 1 Commands
```bash
# Build and test Module 1
npm run build              # Compile TypeScript
npm test                   # Run all tests (95%+ coverage)
npm run test:coverage      # Generate coverage report
npm run benchmark          # Performance benchmarks

# Real-world testing
npm run test:real-world    # Comprehensive validation suite
npm run test:scenarios     # Usage scenarios
npm run test:edge         # Edge cases and stress tests
npm run test:perf         # Performance benchmarks

# Code quality
npm run lint              # ESLint check
npm run lint:fix          # Auto-fix issues
```

### Next Module Development
```bash
# Generate new module using pathfinder patterns
npx ts-node .github/scripts/generate-module.ts [MODULE] [Name] [Description] [Dependencies]

# Run 5-pass pipeline for any module
gh workflow run enhanced-5pass-pipeline.yml -f module=[MODULE] -f pass=all-passes
```

---

**Remember**: Design documents are law. Code is implementation. Any deviation from the approved design specifications will result in architectural drift and project instability.

**When in doubt, consult the design documents first.**

---

*Last Updated: September 6, 2025 - Clean Development Branch Created*