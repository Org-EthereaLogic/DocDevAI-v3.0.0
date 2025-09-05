---
metadata:
  id: installation_guide_standard
  name: Installation Guide Template
  description: Step-by-step installation guide template
  category: guides
  type: installation_guide
  version: 1.0.0
  author: DevDocAI
  tags: [installation, setup, guide, getting-started]
  is_custom: false
  is_active: true
variables:
  - name: project_name
    description: Name of the project
    required: true
    type: string
  - name: supported_platforms
    description: Supported platforms
    required: false
    type: string
    default: "Windows, macOS, Linux"
  - name: minimum_requirements
    description: Minimum system requirements
    required: false
    type: string
    default: "4GB RAM, 2GB disk space"
  - name: package_manager
    description: Primary package manager
    required: false
    type: string
    default: "npm"
---

# {{project_name}} Installation Guide

This guide will help you install and set up {{project_name}} on your system.

## System Requirements

### Minimum Requirements

- {{minimum_requirements}}
- Internet connection for downloading dependencies

### Supported Platforms

- {{supported_platforms}}

## Prerequisites

Before installing {{project_name}}, ensure you have the following:

<!-- IF package_manager -->
- {{package_manager}} installed and updated to the latest version
<!-- END IF -->
- Administrative/sudo privileges for system-wide installation

## Installation Methods

### Method 1: Package Manager Installation (Recommended)

<!-- IF package_manager -->
#### Using {{package_manager}}

```bash
# Install {{project_name}}
{{package_manager}} install {{project_name}}

# Verify installation
{{project_name}} --version
```
<!-- END IF -->

### Method 2: Binary Download

1. Visit the [releases page](https://github.com/{{project_name}}/releases)
2. Download the appropriate binary for your platform
3. Extract the archive to your desired location
4. Add the binary to your system PATH

### Method 3: Build from Source

```bash
# Clone the repository
git clone https://github.com/{{project_name}}/{{project_name}}.git
cd {{project_name}}

# Install dependencies
{{package_manager}} install

# Build the project
npm run build

# Install globally
npm install -g .
```

## Configuration

### Initial Setup

1. Run the setup command:

   ```bash
   {{project_name}} init
   ```

2. Follow the interactive prompts to configure:
   - Project settings
   - User preferences
   - Integration options

### Configuration File

Create a configuration file at `~/.{{project_name}}/config.yml`:

```yaml
# {{project_name}} Configuration
project:
  name: "My Project"
  version: "1.0.0"

settings:
  debug: false
  log_level: "info"
  output_format: "json"

integrations:
  enabled: []
```

## Verification

Verify your installation by running:

```bash
# Check version
{{project_name}} --version

# Run health check
{{project_name}} doctor

# Display help
{{project_name}} --help
```

Expected output:

```
{{project_name}} version X.X.X
Installation: OK
Configuration: OK
All systems operational
```

## Troubleshooting

### Common Issues

#### Issue: Command not found

**Solution:** Ensure the binary is in your PATH or run the full path to the executable.

#### Issue: Permission denied

**Solution:** Run with administrative privileges or install in user directory.

#### Issue: Dependency conflicts

**Solution:** Use a virtual environment or update conflicting packages.

### Getting Help

1. Check the [documentation](https://docs.{{project_name}}.com)
2. Search [existing issues](https://github.com/{{project_name}}/issues)
3. Ask for help in our [community forum](https://community.{{project_name}}.com)

## Next Steps

Now that {{project_name}} is installed:

1. 📚 Read the [Quick Start Guide](quickstart.md)
2. 🔧 Configure your first project
3. 🎯 Check out the [tutorials](tutorials/)
4. 🚀 Join our [community](https://community.{{project_name}}.com)

---

**Need help?** Contact our support team at support@{{project_name}}.com
