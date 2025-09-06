# AGENTS.md

Agent workflow specifications for DevDocAI v3.0.0 development.

## Purpose

This document defines **how to use specialized AI agents** during DevDocAI development to ensure:
- **Design document compliance** throughout all development phases
- **Quality-first delivery** with proper validation gates
- **Efficient task delegation** based on agent expertise
- **Consistent development patterns** across all 13 modules

---

## Agent Selection Matrix

### Primary Development Agents

| Agent Type | Use For | Design Compliance Check |
|-----------|---------|------------------------|
| **lead-software-engineer** | Core module implementation, complex feature development | ✅ Must reference SDD sections |
| **requirements-analyst** | Requirement clarification, PRD validation, scope definition | ✅ Must reference PRD/SRS |
| **software-architect** | System architecture decisions, module integration design | ✅ Must reference Architecture docs |
| **frontend-ux-specialist** | UI components, dashboard development, user experience | ✅ Must reference User Stories |
| **backend-reliability-engineer** | API development, data integrity, system reliability | ✅ Must reference SDD technical specs |

### Quality Assurance Agents

| Agent Type | Use For | Quality Gates |
|-----------|---------|---------------|
| **qa-test-automation** | Test strategy development, test suite implementation | ✅ 85%+ coverage requirement |
| **performance-optimizer** | Performance benchmarking, optimization validation | ✅ Must meet SDD performance targets |
| **security-engineer-devsecops** | Security hardening, vulnerability assessment | ✅ Security requirements compliance |
| **code-quality-refactorer** | Technical debt reduction, code improvement | ✅ <10 cyclomatic complexity |

---

## Agent Workflow Patterns

### Pattern 1: Module Implementation Workflow

```
1. requirements-analyst: Analyze design docs → extract module requirements
2. software-architect: Design module architecture → validate against SDD
3. lead-software-engineer: Implement core functionality → follow design patterns
4. qa-test-automation: Create test suite → achieve coverage targets
5. security-engineer-devsecops: Security review → meet compliance requirements
6. performance-optimizer: Benchmark and optimize → meet performance targets
7. code-quality-refactorer: Final cleanup → reduce complexity
```

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