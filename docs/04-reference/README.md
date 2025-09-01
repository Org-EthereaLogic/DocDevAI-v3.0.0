# Reference Documentation

Quick reference materials for DevDocAI including API references, command guides, and technical glossaries.

## Structure

### [api/](api/)

API reference documentation including endpoints, parameters, and responses.

### [commands/](commands/)

CLI command reference with options and examples.

### [glossary/](glossary/)

Technical terms and acronyms used throughout the project.

### [dependencies/](dependencies/)

Module dependency graphs and third-party library references.

## Quick Reference

### CLI Commands

```bash
devdocai init              # Initialize documentation suite
devdocai generate [type]   # Generate documentation
devdocai enhance [file]    # AI-enhance existing docs
devdocai review [file]     # Quality review
devdocai batch [config]    # Batch operations
devdocai config [key]      # Configuration management
```

### Configuration Keys

```yaml
core:
  project_name: string
  version: semver
  output_dir: path
  
ai:
  provider: openai|anthropic|local
  model: string
  temperature: 0.0-1.0
  
storage:
  encryption: boolean
  path: path
  
quality:
  min_score: 0-100
  auto_enhance: boolean
```

### Module Reference

| Module | ID | Purpose | Dependencies |
|--------|-----|---------|--------------|
| Configuration Manager | M001 | System settings | None |
| Local Storage | M002 | Data persistence | M001 |
| MIAIR Engine | M003 | AI refinement | M001, M002, M008 |
| Document Generator | M004 | Create docs | M001, M002 |
| Tracking Matrix | M005 | Dependencies | M001, M002 |
| Suite Manager | M006 | Collections | M001, M002, M004, M005 |
| Review Engine | M007 | Quality check | M001, M002, M004 |
| LLM Adapter | M008 | AI interface | M001 |
| Enhancement Pipeline | M009 | Improvement | M001, M002, M003, M004, M007, M008 |
| SBOM Generator | M010 | Compliance | M001, M002, M005 |
| Batch Operations | M011 | Multi-doc | M001, M002, M004, M006, M007, M009 |
| Version Control | M012 | Git integration | M001, M002 |
| Template Marketplace | M013 | Templates | M001, M002, M004, M012 |

### Error Codes

| Code | Category | Description |
|------|----------|-------------|
| 1xxx | Configuration | Config errors |
| 2xxx | Storage | Storage/encryption issues |
| 3xxx | AI | AI provider errors |
| 4xxx | Generation | Document generation failures |
| 5xxx | Quality | Review/validation errors |
| 6xxx | Network | Connection issues |
| 7xxx | Permission | Access denied |
| 8xxx | Validation | Input validation |
| 9xxx | System | Internal errors |

### File Formats

#### Documentation Suite (.devdocai)

```json
{
  "version": "3.6.0",
  "metadata": {},
  "documents": [],
  "templates": [],
  "config": {}
}
```

#### Template Format (.template.md)

```yaml
---
name: Template Name
version: 1.0.0
type: readme|api|guide
variables:
  - key: description
---
# Template Content
```

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/generate | POST | Generate documentation |
| /api/enhance | POST | AI enhancement |
| /api/review | POST | Quality review |
| /api/templates | GET | List templates |
| /api/config | GET/PUT | Configuration |

### Environment Variables

```bash
DEVDOCAI_HOME           # Installation directory
DEVDOCAI_CONFIG        # Config file path
DEVDOCAI_STORAGE       # Storage location
DEVDOCAI_AI_PROVIDER   # AI provider
DEVDOCAI_AI_KEY        # API key
DEVDOCAI_LOG_LEVEL     # Logging level
```

### Glossary

**MIAIR**: Multi-Iteration AI Refinement - Entropy-based optimization
**SBOM**: Software Bill of Materials - Compliance documentation
**Quality Gate**: Minimum quality score (85%) for approval
**Suite**: Collection of related documentation
**Template**: Reusable documentation pattern
**Enhancement**: AI-powered improvement process

## Usage Tips

### Performance Optimization

- Use batch operations for multiple files
- Enable caching for repeated operations
- Configure appropriate memory mode
- Optimize template selection

### Security Best Practices

- Always enable encryption for sensitive data
- Rotate API keys regularly
- Use local models for sensitive content
- Review generated content before publishing

### Integration Patterns

- Git hooks for auto-documentation
- CI/CD pipeline integration
- IDE plugin configuration
- API webhook setup
