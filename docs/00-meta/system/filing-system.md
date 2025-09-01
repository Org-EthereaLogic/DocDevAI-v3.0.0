# Documentation Filing System

This document defines the filing system structure and rules for organizing DevDocAI documentation.

## System Overview

The DevDocAI documentation uses a hierarchical filing system with numbered categories for clear organization and easy navigation.

## Directory Structure

```
docs/
├── 00-meta/              # Documentation about documentation
│   ├── system/          # Filing system and meta documentation
│   ├── templates/       # Reusable document templates
│   └── conventions/     # Writing and formatting standards
│
├── 01-specifications/    # IMMUTABLE design documents
│   ├── architecture/    # System design and technical architecture
│   ├── requirements/    # PRD, SRS, user stories, mockups
│   ├── api/            # API specifications and contracts
│   └── modules/        # Individual module specifications
│
├── 02-implementation/    # Active development documentation
│   ├── planning/       # Roadmaps, schedules, SCMP
│   ├── progress/       # Sprint tracking, status updates
│   ├── decisions/      # ADRs and technical decisions
│   └── reviews/        # Code reviews, retrospectives
│
├── 03-guides/           # How-to documentation
│   ├── user/           # End-user documentation
│   ├── developer/      # Developer guides and contribution
│   ├── api/            # API usage guides and examples
│   └── deployment/     # Installation and deployment guides
│
├── 04-reference/        # Quick reference materials
│   ├── api/            # API endpoint reference
│   ├── commands/       # CLI command reference
│   ├── glossary/       # Terms and definitions
│   └── dependencies/   # Module dependency graphs
│
├── 05-quality/          # Quality assurance documentation
│   ├── testing/        # Test plans and strategies
│   ├── security/       # Security policies and audits
│   ├── performance/    # Performance benchmarks
│   └── compliance/     # Regulatory compliance docs
│
└── 06-archives/         # Historical documentation
    ├── versions/       # Previous version documentation
    ├── deprecated/     # Deprecated feature docs
    └── lessons-learned/ # Post-mortems and retrospectives
```

## Filing Rules

### 1. Immutability Rule

Files in `01-specifications/` are **IMMUTABLE** once approved. These represent the agreed-upon design and must not be modified during implementation. Any changes require:

- Formal change request
- Impact analysis
- Stakeholder approval
- New version with clear versioning

### 2. Categorization Rules

#### 00-meta: Meta Documentation

- **Purpose**: Documentation system maintenance
- **Content**: Templates, conventions, system docs
- **Maintenance**: Update as system evolves
- **Access**: Primarily for documentation maintainers

#### 01-specifications: Design Specifications

- **Purpose**: Source of truth for system design
- **Content**: Architecture, requirements, API specs
- **Maintenance**: Frozen after approval
- **Access**: All team members reference

#### 02-implementation: Active Development

- **Purpose**: Track development progress
- **Content**: Plans, progress, decisions
- **Maintenance**: Continuously updated
- **Access**: Development team primary

#### 03-guides: User and Developer Guides

- **Purpose**: How-to instructions
- **Content**: Tutorials, guides, procedures
- **Maintenance**: Update with features
- **Access**: End users and developers

#### 04-reference: Quick References

- **Purpose**: Quick lookup materials
- **Content**: API refs, commands, glossaries
- **Maintenance**: Keep synchronized with code
- **Access**: All users

#### 05-quality: Quality Documentation

- **Purpose**: Quality assurance and standards
- **Content**: Tests, security, performance
- **Maintenance**: Continuous updates
- **Access**: QA and development teams

#### 06-archives: Historical Records

- **Purpose**: Historical reference
- **Content**: Old versions, deprecated docs
- **Maintenance**: Add only, no modifications
- **Access**: As needed for reference

### 3. File Naming Conventions

#### Standard Patterns

```
DESIGN-[module]-[type].md     # Design specifications
TEMPLATE-[purpose].md          # Reusable templates
[topic]-reference.md           # Reference documents
[audience]-[topic]-guide.md    # Guide documents
[date]-[topic].md             # Time-based documents
```

#### Rules

1. Use lowercase with hyphens (kebab-case)
2. No spaces or special characters
3. Include prefixes for document types
4. Add dates for time-sensitive docs (YYYY-MM-DD)
5. Keep names descriptive but concise

### 4. Cross-Reference Rules

#### Internal Links

- Use relative paths from current location
- Always verify links work before committing
- Update links when moving files
- Include section anchors for deep links

Example:

```markdown
[See Architecture](../01-specifications/architecture/DESIGN-devdocsai-architecture.md#overview)
```

#### External Links

- Include access date for web resources
- Archive critical external content
- Note version dependencies
- Check links quarterly

### 5. Version Control Rules

#### Document Versions

- Design specs: Use semantic versioning in metadata
- Guides: Update version with significant changes
- Archives: Preserve original version numbers
- Templates: Version independently

#### Change Tracking

```yaml
---
version: 1.2.0
date: 2024-01-15
changes:
  - Added new section on security
  - Updated API examples
  - Fixed typos in section 3
---
```

### 6. Access Control

| Directory | Read Access | Write Access | Approval Required |
|-----------|------------|--------------|-------------------|
| 00-meta | All | Doc maintainers | No |
| 01-specifications | All | None (frozen) | Yes (changes) |
| 02-implementation | All | Dev team | No |
| 03-guides | All | Contributors | Review |
| 04-reference | All | Contributors | Review |
| 05-quality | All | QA team | Review |
| 06-archives | All | Archivists | No |

### 7. Document Lifecycle

#### Creation

1. Determine correct category
2. Use appropriate template
3. Follow naming conventions
4. Add required metadata
5. Create in correct directory

#### Maintenance

1. Regular reviews per schedule
2. Update with code changes
3. Maintain cross-references
4. Archive when deprecated

#### Archival

1. Move to 06-archives
2. Add archival metadata
3. Update references
4. Preserve original content

## Search and Discovery

### Organization Benefits

- **Numbered directories**: Natural sorting order
- **Clear categories**: Easy to locate content
- **Consistent naming**: Predictable file locations
- **Hierarchical structure**: Logical grouping

### Finding Documents

1. **By Purpose**: Check category directory
2. **By Type**: Look for file prefix
3. **By Topic**: Use search within category
4. **By Date**: Check archives chronologically

### Search Tips

- Use ripgrep for fast searching: `rg "search term" docs/`
- Search specific categories: `rg "API" docs/01-specifications/`
- Find broken links: Use markdown-link-check
- List recent changes: `git log --oneline docs/`

## Maintenance Procedures

### Daily

- Update progress tracking in 02-implementation
- Check for broken links in changed files

### Weekly

- Review and merge documentation PRs
- Update sprint documentation
- Archive completed sprint docs

### Monthly

- Full link validation check
- Review and update roadmap
- Archive deprecated content

### Quarterly

- Documentation audit
- Convention review and update
- Template improvements
- Archive cleanup

## Quality Standards

### Required Elements

Every document must have:

- [ ] Clear title and purpose
- [ ] Table of contents (if >3 sections)
- [ ] Metadata header
- [ ] Proper categorization
- [ ] Working cross-references

### Quality Checks

Before committing documentation:

- [ ] Spell check passed
- [ ] Links verified
- [ ] Format conventions followed
- [ ] Placed in correct directory
- [ ] Metadata complete

## Troubleshooting

### Common Issues

#### Wrong Category

**Problem**: Document in wrong directory
**Solution**: Move to correct location, update all references

#### Broken Links

**Problem**: Links return 404
**Solution**: Update paths, use relative links, verify before commit

#### Naming Conflicts

**Problem**: Similar file names causing confusion
**Solution**: Use clear prefixes and descriptive names

#### Version Confusion

**Problem**: Unclear which version is current
**Solution**: Use clear versioning in metadata, archive old versions

## Tools and Automation

### Recommended Tools

- **VS Code**: With Markdown extensions
- **markdownlint**: Format validation
- **markdown-link-check**: Link validation
- **prettier**: Consistent formatting
- **git hooks**: Pre-commit validation

### Automation Scripts

```bash
# Validate all links
npm run docs:check-links

# Format all documentation
npm run docs:format

# Generate documentation index
npm run docs:index

# Archive old documentation
npm run docs:archive
```

## Appendix: Quick Reference

### Directory Purpose Matrix

| Directory | Primary Purpose | Update Frequency |
|-----------|----------------|------------------|
| 00-meta | System docs | As needed |
| 01-specifications | Design truth | Never (frozen) |
| 02-implementation | Dev tracking | Daily |
| 03-guides | How-to docs | Per release |
| 04-reference | Quick lookup | With code |
| 05-quality | QA docs | Continuous |
| 06-archives | History | Add only |
