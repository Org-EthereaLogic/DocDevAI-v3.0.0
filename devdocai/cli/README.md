# DevDocAI CLI Module (M012)

Command-line interface for DevDocAI - AI-Powered Documentation Generation System.

## Installation

Install DevDocAI with CLI support:

```bash
# Install from source
pip install -e .

# Or install from PyPI (when published)
pip install devdocai
```

## Usage

After installation, the `devdocai` command will be available:

```bash
# Show help
devdocai --help

# Short alias
dda --help
```

## Available Commands

### 1. Document Generation

```bash
# Generate documentation for a single file
devdocai generate file api.py --template api-endpoint --output api_docs.md

# Batch generate for all Python files
devdocai generate file src/ --batch --pattern "*.py" --recursive

# Generate from API specification
devdocai generate api openapi.yaml --format openapi
```

### 2. Quality Analysis

```bash
# Analyze documentation quality
devdocai analyze document README.md --dimensions all

# Analyze with specific threshold
devdocai analyze document docs/ --threshold 0.9 --detailed

# Batch analysis with export
devdocai analyze batch docs/ --recursive --export results.csv
```

### 3. Configuration Management

```bash
# Get configuration value
devdocai config get api.key

# Set configuration value
devdocai config set quality.threshold 0.85

# List all settings
devdocai config list

# Manage profiles
devdocai config profile create production
devdocai config profile switch production
```

### 4. Template Management

```bash
# List available templates
devdocai template list --category api

# Show template content
devdocai template show api-endpoint

# Create custom template
devdocai template create my-template --from-file template.md --category custom

# Export templates
devdocai template export --output templates.json
```

### 5. Enhancement Pipeline

```bash
# Enhance documentation
devdocai enhance document README.md --strategy clarity --iterations 3

# Batch enhancement
devdocai enhance batch docs/ --recursive --parallel 4

# Configure pipeline
devdocai enhance pipeline --create my-pipeline
```

### 6. Security Operations

```bash
# Security scan
devdocai security scan src/ --recursive --type all --output report.html

# Generate SBOM
devdocai security sbom . --format spdx --output sbom.spdx --sign

# PII detection
devdocai security pii-detect data.txt --languages en es fr --mask

# Compliance check
devdocai security compliance --framework gdpr --output compliance.json
```

## Global Options

- `--version` - Show version information
- `--debug` - Enable debug output
- `--json` - Output in JSON format
- `--yaml` - Output in YAML format
- `--quiet` - Suppress non-error output
- `--config <path>` - Use specific configuration file

## Configuration

DevDocAI looks for configuration in these locations (in order):

1. `~/.devdocai/config.yml` - User configuration
2. `.devdocai.yml` - Project configuration
3. `devdocai.yml` - Alternative project configuration

Example configuration:

```yaml
version: 3.0.0
project:
  name: MyProject
  description: Project documentation

templates:
  default: general
  
quality:
  threshold: 0.8
  dimensions:
    - completeness
    - clarity
    - technical_accuracy

enhancement:
  strategies:
    - clarity
    - examples
  iterations: 2
  
security:
  pii_detection: true
  languages: [en, es]
```

## Shell Completion

Enable shell completion for better CLI experience:

```bash
# Show installation instructions
devdocai completion

# For bash
eval "$(_DEVDOCAI_COMPLETE=bash_source devdocai)"

# For zsh
eval "$(_DEVDOCAI_COMPLETE=zsh_source devdocai)"

# For fish
eval "$(_DEVDOCAI_COMPLETE=fish_source devdocai)"
```

## Project Initialization

Initialize a new DevDocAI project:

```bash
# Basic initialization
devdocai init

# With specific template
devdocai init --template api
```

This creates a `.devdocai.yml` configuration file in the current directory.

## Module Integration

The CLI integrates with all DevDocAI modules:

- **M001**: Configuration Manager - Settings and profiles
- **M002**: Local Storage - Document persistence
- **M003**: MIAIR Engine - Quality optimization
- **M004**: Document Generator - Content generation
- **M005**: Quality Engine - Analysis and scoring
- **M006**: Template Registry - Template management
- **M007**: Review Engine - Document review
- **M008**: LLM Adapter - AI provider integration
- **M009**: Enhancement Pipeline - Content improvement
- **M010**: Security Module - Security operations

## Performance Modes

Most commands support different operation modes:

- `--mode basic` - Simple operations, minimal features
- `--mode optimized` - Performance-focused, caching enabled
- `--mode secure` - Enhanced security, validation
- `--mode balanced` - Default, balanced features

## Error Handling

The CLI provides comprehensive error messages:

```bash
# Debug mode for detailed errors
devdocai --debug generate file nonexistent.py

# Quiet mode for minimal output
devdocai --quiet analyze document docs/
```

## Examples

### Complete Workflow Example

```bash
# 1. Initialize project
devdocai init --template api

# 2. Generate initial documentation
devdocai generate file src/ --batch --recursive --output docs/

# 3. Analyze quality
devdocai analyze batch docs/ --threshold 0.8 --export quality.csv

# 4. Enhance documentation
devdocai enhance batch docs/ --strategy all --iterations 2

# 5. Security scan
devdocai security scan docs/ --type pii --output security.json

# 6. Generate SBOM
devdocai security sbom . --format cyclonedx --output sbom.xml
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Generate Documentation
  run: |
    devdocai generate file src/ --batch --output docs/
    devdocai analyze batch docs/ --threshold 0.85
    
- name: Security Check
  run: |
    devdocai security scan . --recursive --severity high
    devdocai security sbom . --output sbom.spdx
```

## Testing

Run CLI tests:

```bash
# Run all CLI tests
pytest devdocai/cli/tests/

# Run specific test file
pytest devdocai/cli/tests/test_cli.py -v

# Test with coverage
pytest devdocai/cli/tests/ --cov=devdocai.cli --cov-report=html
```

## Development

The CLI module follows the established DevDocAI patterns:

1. **4-Pass Development**: Implementation → Performance → Security → Refactoring
2. **Test Coverage**: Target 80%+ coverage
3. **Module Integration**: Seamless integration with M001-M010
4. **Privacy-First**: No telemetry, offline-capable
5. **User-Friendly**: Comprehensive help, intuitive commands

## License

MIT License - See LICENSE file for details

## Support

- GitHub Issues: https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/issues
- Documentation: https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/wiki
