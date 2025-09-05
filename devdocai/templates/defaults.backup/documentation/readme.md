---
metadata:
  id: readme_standard
  name: Standard README Template
  description: A comprehensive README template for software projects
  category: documentation
  type: readme
  version: 1.0.0
  author: DevDocAI
  tags: [readme, documentation, project, overview]
  is_custom: false
  is_active: true
variables:
  - name: project_name
    description: Name of the project
    required: true
    type: string
  - name: project_description
    description: Brief description of the project
    required: true
    type: string
  - name: author_name
    description: Author or organization name
    required: true
    type: string
  - name: installation_steps
    description: Installation instructions
    required: false
    type: string
    default: "Clone the repository and follow the setup instructions"
  - name: usage_example
    description: Basic usage example
    required: false
    type: string
    default: "See examples directory for usage samples"
  - name: license_type
    description: License type
    required: false
    type: string
    default: "MIT"
  - name: repository_url
    description: Repository URL
    required: false
    type: string
  - name: documentation_url
    description: Documentation URL
    required: false
    type: string
  - name: contributing_guidelines
    description: Contributing guidelines
    required: false
    type: boolean
    default: true
---

# {{project_name}}

{{project_description}}

<!-- IF repository_url -->
[![GitHub Repository](https://img.shields.io/github/stars/{{repository_url}}?style=social)]({{repository_url}})
<!-- END IF -->

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Features](#features)
<!-- IF documentation_url -->
- [Documentation](#documentation)
<!-- END IF -->
<!-- IF contributing_guidelines -->
- [Contributing](#contributing)
<!-- END IF -->
- [License](#license)

## Installation

{{installation_steps}}

```bash
# Example installation
git clone {{repository_url}}
cd {{project_name}}
npm install  # or your package manager
```

## Usage

{{usage_example}}

```javascript
// Basic usage example
const {{project_name}} = require('{{project_name}}');

// Your code here
```

## Features

- ✨ **Feature 1**: Description of feature 1
- 🚀 **Feature 2**: Description of feature 2
- 🔧 **Feature 3**: Description of feature 3
- 📚 **Feature 4**: Description of feature 4

<!-- IF documentation_url -->
## Documentation

For detailed documentation, visit: [{{documentation_url}}]({{documentation_url}})
<!-- END IF -->

<!-- IF contributing_guidelines -->
## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
<!-- END IF -->

## License

This project is licensed under the {{license_type}} License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: support@{{author_name}}.com
- 🐛 Issues: [GitHub Issues]({{repository_url}}/issues)
<!-- IF documentation_url -->
- 📖 Documentation: [{{documentation_url}}]({{documentation_url}})
<!-- END IF -->

---

Made with ❤️ by {{author_name}}
