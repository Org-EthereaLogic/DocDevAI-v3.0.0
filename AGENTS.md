# AGENTS.md

Agent workflow specifications for DevDocAI v3.0.0 development.

**🎉 STATUS: M002 UNIFIED ARCHITECTURE COMPLETE + 4-PASS TDD METHODOLOGY PROVEN! 🎉**

## Purpose

This document defines **how to use specialized AI agents** during DevDocAI development to ensure:
- **Design document compliance** throughout all development phases
- **Quality-first delivery** with proper validation gates
- **Efficient task delegation** based on agent expertise
- **Consistent development patterns** across all 13 modules

---

## Agent Selection Matrix - **VALIDATED BY M001 & M002 SUCCESS**

### Primary Development Agents ✅ PROVEN EFFECTIVE ACROSS 2 MODULES

| Agent Type | Use For | Design Compliance Check | M001 Result | M002 Result |
|-----------|---------|------------------------|-------------|-------------|
| **software-architect** | System architecture, Pass 0 design validation | ✅ Must reference SDD sections | ✅ **EXCELLENT** | ✅ **EXCELLENT** - Comprehensive M002 blueprint |
| **python-expert** | Python implementation, TDD development, Pass 1 | ✅ Must reference SDD sections | ✅ **EXCEPTIONAL** - 90% coverage | ✅ **EXCEPTIONAL** - Complete implementation |
| **performance-optimizer** | Performance optimization, Pass 2 | ✅ Must meet SDD performance targets | 🚧 **PENDING** | ✅ **OUTSTANDING** - 72K queries/sec, 743x improvement |
| **security-engineer-devsecops** | Security hardening, Pass 3 | ✅ Security requirements compliance | 🚧 **PENDING** | ✅ **OUTSTANDING** - Enterprise security, PII detection |
| **code-quality-refactorer** | Technical debt reduction, Pass 4 | ✅ <10 cyclomatic complexity | 🚧 **PENDING** | ✅ **OUTSTANDING** - 66% duplication reduction, unified architecture |
| **qa-testing-specialist** | Test strategy, comprehensive validation | ✅ 95%+ coverage requirement | ✅ **EXCELLENT** | ✅ **EXCELLENT** - All testing frameworks |
| **root-cause-analyzer** | Systematic issue investigation, CI/CD troubleshooting | ✅ Evidence-based analysis | 🚧 **PENDING** | ✅ **OUTSTANDING** - Identified CI/CD tech stack mismatch |

### Quality Assurance Agents

| Agent Type | Use For | Quality Gates |
|-----------|---------|---------------|
| **qa-test-automation** | Test strategy development, test suite implementation | ✅ 85%+ coverage requirement |
| **performance-optimizer** | Performance benchmarking, optimization validation | ✅ Must meet SDD performance targets |
| **security-engineer-devsecops** | Security hardening, vulnerability assessment | ✅ Security requirements compliance |
| **code-quality-refactorer** | Technical debt reduction, code improvement | ✅ <10 cyclomatic complexity |

---

## Agent Workflow Patterns - **PROVEN BY M001 & M002**

### Pattern 1: Enhanced 4-Pass TDD Module Implementation ✅ VALIDATED ACROSS 2 MODULES

**M001 & M002 Complete Workflow:**

```
PASS 0: software-architect → Design validation → Architecture approved ✅
PASS 1: python-expert → Core implementation (TDD) → Foundation complete ✅  
PASS 2: performance-optimizer → Advanced optimization → Performance targets exceeded ✅
PASS 3: security-engineer-devsecops → Security hardening → Enterprise-grade achieved ✅
PASS 4: code-quality-refactorer → Unified architecture → 66% duplication reduction ✅
```

**Results**: 
- **M001**: 90% coverage, 34/34 tests, production-ready configuration system
- **M002**: Unified architecture (1,948 lines), 4 operation modes, 66% duplication reduction
- **Combined**: Proven 4-pass methodology delivering enterprise-grade quality consistently

### Pattern 2: Integration Workflow

```
1. software-architect: Design integration approach → validate cross-module contracts
2. backend-reliability-engineer: Implement API contracts → ensure data integrity
3. lead-software-engineer: Wire module connections → maintain interface compliance
4. qa-test-automation: Integration testing → validate end-to-end workflows
```

### Pattern 3: UI Development Workflow

```
1. requirements-analyst: Extract UI requirements → map to user stories
2. ux-designer-engineer: Design user interface → follow accessibility standards
3. frontend-ux-specialist: Implement components → meet responsive design requirements
4. qa-test-automation: UI testing → validate user experience
5. performance-optimizer: Frontend optimization → meet load time targets
```

---

## Design Document Compliance Rules

### Mandatory Agent Instructions

**Every agent MUST:**
1. **Reference specific design document sections** in their analysis
2. **Validate implementation against design specifications** before coding
3. **Cite PRD/SRS/SDD section numbers** when making decisions
4. **Flag any deviations** from approved design patterns
5. **Maintain traceability** between implementation and requirements

### Pre-Implementation Checklist

Before any agent begins work:
- [ ] Design document sections identified and reviewed
- [ ] Requirements extracted and validated
- [ ] Success criteria defined from design specs
- [ ] Integration points confirmed with architecture
- [ ] Quality gates established (coverage, performance, security)

### Post-Implementation Validation

After agent completes work:
- [ ] Implementation maps to specific design requirements
- [ ] All design document references cited
- [ ] Quality gates achieved (tests, performance, security)
- [ ] No architectural drift detected
- [ ] Integration contracts maintained

---

## Quality Gates by Agent Type

### Development Agents
- **Test Coverage**: 85% minimum, 95% for critical modules (M001, M002)
- **Performance**: Must meet SDD benchmarks (M001: 19M ops/sec)
- **Code Quality**: <10 cyclomatic complexity, max 350 lines per file
- **Design Compliance**: 100% traceability to design documents

### QA Agents
- **Security Coverage**: OWASP Top 10 compliance
- **Performance Validation**: Benchmark verification required
- **Test Automation**: CI/CD pipeline integration
- **Documentation**: Agent decisions documented with design references

---

## Agent Communication Patterns

### Cross-Agent Handoffs

When one agent completes work and hands off to another:

```
HANDOFF TEMPLATE:
- Completed: [Specific deliverables]
- Design References: [SDD 3.2, PRD 4.1, etc.]
- Quality Status: [Coverage %, Performance results, Security scan]
- Next Agent: [Specific agent type and focus area]
- Remaining Work: [Specific tasks aligned to design docs]
```

### Design Compliance Reporting

Each agent must provide compliance status:

```
COMPLIANCE TEMPLATE:
✅ Design Document Sections Implemented: [List specific sections]
✅ Requirements Traceability: [PRD/SRS references with implementation mapping]
⚠️ Deviations Noted: [Any variations with justification]
❌ Blocked Items: [Design ambiguities requiring clarification]
```

---

## Development Phase Agent Assignment

### Phase 1: CLI Interface (Per Build Instructions)
- **Primary**: lead-software-engineer
- **Support**: requirements-analyst, qa-test-automation
- **Design Focus**: SDD Section 4.1 (CLI Architecture)

### Phase 2: Web Dashboard
- **Primary**: frontend-ux-specialist
- **Support**: ux-designer-engineer, performance-optimizer
- **Design Focus**: User Stories US-001 through US-006

### Phase 3: AI Integration
- **Primary**: backend-reliability-engineer
- **Support**: security-engineer-devsecops, performance-optimizer
- **Design Focus**: SDD Section 3.3 (AI Integration Architecture)

### Phase 4: Template System
- **Primary**: lead-software-engineer
- **Support**: requirements-analyst, code-quality-refactorer
- **Design Focus**: SDD Section 3.4 (Template Management)

### Phase 5: VS Code Extension
- **Primary**: frontend-ux-specialist
- **Support**: software-architect, qa-test-automation
- **Design Focus**: SDD Section 4.3 (IDE Integration)

### Phase 6: Performance Optimization
- **Primary**: performance-optimizer
- **Support**: code-quality-refactorer, security-engineer-devsecops
- **Design Focus**: SDD Performance Requirements (All sections)

---

## Emergency Procedures

### When Agents Detect Design Drift

1. **HALT DEVELOPMENT** immediately
2. **Document deviation** with specific design document references
3. **Escalate to requirements-analyst** for requirement clarification
4. **Do not proceed** until design alignment restored
5. **Update CLAUDE.md** with lessons learned

### When Design Documents Are Ambiguous

1. **Flag specific ambiguity** with document section references
2. **Propose solution options** aligned with overall design vision
3. **Request clarification** before implementation
4. **Document decisions** for future reference

---

## Success Metrics

### Agent Effectiveness
- **Design Compliance**: 100% traceability maintained
- **Quality Gates**: All agents meet coverage/performance targets
- **Integration Success**: Clean handoffs between agents
- **Zero Drift**: No architectural deviations from approved design

### Project Velocity
- **Phase Completion**: On-schedule delivery per build instructions
- **Quality First**: No shortcuts that compromise design compliance
- **Sustainable Pace**: Consistent progress without technical debt accumulation

---

## Agent Training Notes

### For Development Team
- Always start with design document review
- Prefer design-first over code-first approaches
- Maintain quality gates throughout development
- Document all decisions with design references

### For QA Team
- Validate against design specifications, not just code functionality
- Ensure test coverage maps to requirements traceability
- Security and performance testing must meet SDD targets
- Integration testing focuses on design-specified interfaces

---

**Remember**: Design documents are law. Code is implementation. Agents are the enforcement mechanism to ensure we build exactly what was specified in our comprehensive design documentation.

---

*Last Updated: September 6, 2025 - Clean Development Branch Created*