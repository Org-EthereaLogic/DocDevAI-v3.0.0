# AGENTS.md

Agent workflow specifications for DevDocAI v3.0.0 development.

**✅ STATUS: M001 FOUNDATION COMPLETE - ENHANCED 4-PASS TDD METHODOLOGY PROVEN**

## Purpose

This document defines **how to use specialized AI agents** during DevDocAI development to ensure:
- **Design document compliance** throughout all development phases
- **Quality-first delivery** with proper validation gates
- **Efficient task delegation** based on agent expertise
- **Consistent development patterns** across all 13 modules

---

## Agent Selection Matrix - **READY FOR DESIGN-FIRST IMPLEMENTATION**

### Primary Development Agents - **READY FOR IMPLEMENTATION**

| Agent Type | Use For | Design Compliance Check | Status |
|-----------|---------|------------------------|---------|
| **software-architect** | System architecture, Pass 0 design validation | ✅ Must reference SDD sections | ✅ **PROVEN** - M001 architecture validated |
| **lead-software-engineer** | Python implementation, TDD development, Pass 1 | ✅ Must reference SDD sections | ✅ **PROVEN** - M001 Pass 1 (81.53% coverage) |
| **performance-optimizer** | Performance optimization, Pass 2 | ✅ Must meet SDD performance targets | ✅ **PROVEN** - M001 Pass 2 (7.13M ops/sec) |
| **security-engineer-devsecops** | Security hardening, Pass 3 | ✅ Security requirements compliance | ✅ **PROVEN** - M001 Pass 3 (27/29 tests) |
| **code-quality-refactorer** | Technical debt reduction, Pass 4 | ✅ <10 cyclomatic complexity | ✅ **PROVEN** - M001 Pass 4 (40.4% reduction) |
| **qa-testing-specialist** | Test strategy, comprehensive validation | ✅ 95%+ coverage requirement | 🔄 **READY** - Testing frameworks specified |
| **root-cause-analyzer** | Systematic issue investigation, CI/CD troubleshooting | ✅ Evidence-based analysis | 🔄 **READY** - Analysis patterns documented |

### Quality Assurance Agents

| Agent Type | Use For | Quality Gates |
|-----------|---------|---------------|
| **qa-test-automation** | Test strategy development, test suite implementation | ✅ 85%+ coverage requirement |
| **performance-optimizer** | Performance benchmarking, optimization validation | ✅ Must meet SDD performance targets |
| **security-engineer-devsecops** | Security hardening, vulnerability assessment | ✅ Security requirements compliance |
| **code-quality-refactorer** | Technical debt reduction, code improvement | ✅ <10 cyclomatic complexity |

---

## Agent Workflow Patterns - **DESIGN-FIRST APPROACH**

### Pattern 1: Enhanced 4-Pass TDD Module Implementation 

**Clean Implementation Workflow (Starting Fresh):**

```
PASS 0: software-architect → Design validation → Architecture approved
PASS 1: python-expert → Core implementation (TDD) → Foundation established  
PASS 2: performance-optimizer → Performance optimization → Targets achieved
PASS 3: security-engineer-devsecops → Security hardening → Enterprise-grade security
PASS 4: code-quality-refactorer → Code quality improvement → Technical debt reduction
```

**Implementation Order (Per Design Documents)**: 
- **M001**: Configuration Manager ✅ **COMPLETE** (INDEPENDENT) - Foundation layer - Production ready
- **M008**: LLM Adapter (Depends: M001) - **CRITICAL FOR AI** - Must be implemented before M004 - **READY**
- **M002**: Local Storage System (Depends: M001) - Foundation layer - **READY**
- **M004**: Document Generator (Depends: M001, M002, M008) - **AI-POWERED GENERATION**
- **M003**: MIAIR Engine (Depends: M001, M002, M008) - Intelligence layer

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
- **Test Coverage**: 85% minimum, 95% for critical modules (per design documents)
- **Performance**: Must meet SDD benchmarks (specific targets defined per module)
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

### Phase 1: Foundation Layer (M001, M008, M002)
- **Primary**: python-expert, software-architect
- **Support**: requirements-analyst, qa-test-automation
- **Design Focus**: Core system foundation with proper dependency order

### Phase 2: Document Management Layer (M004, M003)
- **Primary**: python-expert, backend-reliability-engineer
- **Support**: security-engineer-devsecops, performance-optimizer
- **Design Focus**: AI-powered document generation and processing

### Phase 3: Analysis & Enhancement Layer (M005, M006, M007, M009)
- **Primary**: backend-reliability-engineer, performance-optimizer
- **Support**: security-engineer-devsecops, code-quality-refactorer
- **Design Focus**: Document analysis and quality enhancement

### Phase 4: Compliance & Operations Layer (M010, M011, M012, M013)
- **Primary**: frontend-ux-specialist, lead-software-engineer
- **Support**: ux-designer-engineer, qa-test-automation
- **Design Focus**: User interfaces and operational features

### Phase 5: Integration & Polish
- **Primary**: software-architect, code-quality-refactorer
- **Support**: performance-optimizer, security-engineer-devsecops
- **Design Focus**: System integration and production readiness

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

*Last Updated: September 7, 2025 - M001 Foundation Complete - Enhanced 4-Pass TDD Methodology Proven Successful*