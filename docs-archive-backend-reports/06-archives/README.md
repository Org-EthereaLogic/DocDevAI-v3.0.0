# Archives

This directory contains historical documentation, deprecated features, and lessons learned from the DevDocAI project.

## Structure

### [versions/](versions/)

Previous versions of documentation for historical reference.

### [deprecated/](deprecated/)

Documentation for deprecated features and APIs.

### [lessons-learned/](lessons-learned/)

Post-mortems, retrospectives, and learning documents.

## Purpose

The archives serve several important functions:

1. **Historical Reference**: Understand how the project evolved
2. **Decision Context**: See why certain choices were made
3. **Learning Repository**: Avoid repeating past mistakes
4. **Compliance**: Maintain audit trail for changes
5. **Migration Support**: Help users upgrade from older versions

## Archival Policy

### What Gets Archived

1. **Version Archives**
   - Documentation from each major release
   - API documentation for deprecated versions
   - Migration guides between versions
   - Release notes and changelogs

2. **Deprecated Features**
   - Feature documentation before removal
   - Deprecation notices and timelines
   - Migration paths to new features
   - Rationale for deprecation

3. **Lessons Learned**
   - Post-mortem reports from incidents
   - Sprint retrospectives with key insights
   - Architecture decision records (ADRs)
   - Performance optimization learnings
   - Security incident analyses

### When to Archive

- **Major Version Release**: Archive previous major version docs
- **Feature Deprecation**: When deprecation notice is issued
- **Incident Resolution**: After post-mortem completion
- **Sprint End**: Key learnings and decisions
- **Project Milestones**: Significant achievements or pivots

### Archive Structure

```
versions/
├── v1.0.0/
│   ├── documentation/
│   ├── api-reference/
│   └── migration-guide.md
├── v2.0.0/
│   └── ...
└── v3.0.0/
    └── ...

deprecated/
├── features/
│   ├── feature-name/
│   │   ├── documentation.md
│   │   ├── deprecation-notice.md
│   │   └── migration-guide.md
│   └── ...
└── apis/
    └── ...

lessons-learned/
├── 2024/
│   ├── Q1/
│   │   ├── incident-2024-01-15.md
│   │   └── sprint-retrospectives/
│   └── ...
└── 2025/
    └── ...
```

## Accessing Archives

### Finding Information

1. **By Version**: Check versions/ for specific release documentation
2. **By Feature**: Look in deprecated/ for removed functionality
3. **By Date**: Browse lessons-learned/ chronologically
4. **By Topic**: Use search across archive directories

### Using Archived Documentation

**Important Notes**:

- Archived documentation may not reflect current implementation
- Always refer to current documentation for active development
- Use archives for historical context and migration planning
- Contact maintainers if critical information is missing

## Notable Archives

### Key Decisions

- Initial architecture selection rationale
- Technology stack choices
- Security model evolution
- Performance optimization strategies

### Major Migrations

- Version 2.x to 3.x API changes
- Storage system redesign
- AI provider abstraction layer
- Plugin system introduction

### Incident Learnings

- Performance degradation root causes
- Security vulnerability discoveries
- Data migration challenges
- Integration failure patterns

## Contributing to Archives

### Adding to Archives

1. **Create Clear Structure**: Organize by date/version/feature
2. **Include Context**: Add README files explaining the archive
3. **Preserve Links**: Maintain references but mark as archived
4. **Add Metadata**: Include date, author, and reason for archival
5. **Update Index**: Keep this README current with notable additions

### Archive Format

```markdown
# [Archive Title]

**Archived Date**: YYYY-MM-DD
**Original Date**: YYYY-MM-DD
**Author**: [Name]
**Reason**: [Why archived]
**Status**: [Deprecated|Superseded|Historical]

## Summary
[Brief description of archived content]

## Original Content
[Preserved documentation]

## Migration Notes
[If applicable, how to migrate to current approach]

## Related Documents
[Links to related archives or current docs]
```

## Retention Policy

- **Version Documentation**: Retain for 3 major versions
- **Deprecated Features**: Retain for 2 years after removal
- **Lessons Learned**: Retain indefinitely
- **Security Incidents**: Retain for 5 years
- **Architecture Decisions**: Retain indefinitely

## Search and Discovery

### Tags

Archives should be tagged for easier discovery:

- `#architecture` - Architecture decisions
- `#security` - Security-related archives
- `#performance` - Performance optimizations
- `#api` - API changes
- `#migration` - Migration guides
- `#incident` - Incident reports
- `#retrospective` - Team learnings
