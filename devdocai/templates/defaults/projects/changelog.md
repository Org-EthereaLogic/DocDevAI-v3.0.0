---
metadata:
  id: changelog_standard
  name: Changelog Template
  description: Standard changelog template following Keep a Changelog format
  category: projects
  type: changelog
  version: 1.0.0
  author: DevDocAI
  tags: [changelog, releases, versioning, history]
  is_custom: false
  is_active: true
variables:
  - name: project_name
    description: Name of the project
    required: true
    type: string
  - name: repository_url
    description: Repository URL
    required: false
    type: string
  - name: latest_version
    description: Latest version number
    required: false
    type: string
    default: "1.0.0"
---

# Changelog

All notable changes to {{project_name}} will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature descriptions go here

### Changed
- Changes to existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Features removed in this release

### Fixed
- Bug fixes

### Security
- Vulnerability fixes

## [{{latest_version}}] - {{current_date}}

### Added
- Initial release of {{project_name}}
- Core functionality implemented
- Basic documentation
- Unit tests with 90%+ coverage

### Changed
- N/A (initial release)

### Fixed
- N/A (initial release)

## Template for Future Releases

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Features removed in this version

### Fixed
- Bug fixes

### Security
- Vulnerability fixes
```

## Release Types

- **Major version (X.0.0)** - Incompatible API changes
- **Minor version (0.X.0)** - Backward-compatible functionality additions
- **Patch version (0.0.X)** - Backward-compatible bug fixes

## Links

<!-- IF repository_url -->
[Unreleased]: {{repository_url}}/compare/v{{latest_version}}...HEAD
[{{latest_version}}]: {{repository_url}}/releases/tag/v{{latest_version}}
<!-- END IF -->