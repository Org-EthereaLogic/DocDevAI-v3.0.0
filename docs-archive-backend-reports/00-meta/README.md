# Meta Documentation

This directory contains documentation about the documentation system itself, including templates, conventions, and system guidelines.

## Structure

### [system/](system/)

Documentation system configuration and guidelines for maintaining the documentation structure.

### [templates/](templates/)

Reusable templates for creating new documentation:

- [Future Release Notes Template](templates/TEMPLATE-future-release-notes.md)

### [conventions/](conventions/)

Documentation standards and writing conventions used throughout the project.

## Purpose

The meta documentation serves as the foundation for maintaining consistency and quality across all project documentation. It includes:

1. **Documentation Standards**: How to write and format documentation
2. **Filing System Rules**: How to organize and categorize documents
3. **Templates**: Standard formats for common document types
4. **Maintenance Guidelines**: How to keep documentation up-to-date

## Key Guidelines

### Documentation Principles

- **Clarity First**: Write for your audience's understanding level
- **Consistency**: Follow established patterns and conventions
- **Completeness**: Include all necessary information without redundancy
- **Currency**: Keep documentation synchronized with implementation

### File Naming Conventions

- Design specifications: `DESIGN-[module]-[type].md`
- Templates: `TEMPLATE-[purpose].md`
- Guides: `[audience]-[topic].md`
- References: `[topic]-reference.md`

### Version Control

- All documentation changes should be tracked in git
- Major updates require review before merging
- Archive deprecated documentation rather than deleting

## Contributing

When adding new documentation:

1. Use appropriate templates from the templates/ directory
2. Follow conventions outlined in conventions/
3. Place documents in the correct category directory
4. Update relevant index files
5. Maintain cross-references and links

## Maintenance Schedule

Documentation reviews should occur:

- **Weekly**: Progress tracking updates
- **Sprint End**: Implementation documentation updates
- **Release**: User guide and API documentation updates
- **Quarterly**: Full documentation audit
