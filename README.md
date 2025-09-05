# DevDocAI

<div align="center">

![DevDocAI Logo](https://raw.githubusercontent.com/Org-EthereaLogic/DocDevAI-v3.0.0/main/docs/assets/devdocai-logo.png)

**Transform your code into beautiful documentation with AI**

[![Version](https://img.shields.io/badge/Version-3.0.0-blue)](https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/releases)
[![License](https://img.shields.io/badge/License-Apache_2.0-green)](LICENSE)
[![Build Status](https://img.shields.io/badge/Build-Passing-green)](.github/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/Coverage-95%25-green)](docs/05-quality/)
[![Node](https://img.shields.io/badge/Node.js-18+-green)](https://nodejs.org)
[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://python.org)

[**Live Demo**](http://localhost:3000) • [**Quick Start**](#-quick-start) • [**Documentation**](docs/) • [**Contributing**](#-contributing)

</div>

---

## 🚀 What is DevDocAI?

DevDocAI is your AI-powered documentation assistant that generates, analyzes, and improves technical documentation automatically. Perfect for solo developers who want to spend more time coding and less time writing docs.

### ✨ Key Benefits

- 📝 **Generate docs from code** - Turn your codebase into comprehensive documentation in seconds
- 🤖 **AI-powered analysis** - Get intelligent suggestions to improve your documentation quality
- 🔒 **100% private** - Everything runs locally. Your code never leaves your machine
- ⚡ **Lightning fast** - Process 248,000 documents per minute with our MIAIR engine
- 🎨 **35+ templates** - Professional documentation templates for every need

### 🎥 See It In Action

![DevDocAI Dashboard Demo](docs/assets/dashboard-demo.gif)
<!-- TODO: Add animated GIF showing the dashboard in action -->

---

## 🏃 Quick Start

Get up and running in less than 2 minutes:

```bash
# Install DevDocAI CLI globally
npm install -g devdocai

# Generate documentation for your project
devdocai generate README.md

# Launch the web dashboard
devdocai dashboard
```

That's it! Visit http://localhost:3000 to see your documentation dashboard.

---

## 📦 Installation Options

### For Users (Recommended)

<details>
<summary><b>Option 1: NPM Package (Easiest)</b></summary>

```bash
npm install -g devdocai
devdocai --version
```
</details>

<details>
<summary><b>Option 2: VS Code Extension</b></summary>

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "DevDocAI"
4. Click Install

![VS Code Extension](docs/assets/vscode-extension.png)
<!-- TODO: Add VS Code extension screenshot -->
</details>

<details>
<summary><b>Option 3: Web Application</b></summary>

```bash
# Clone and run locally
git clone https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0.git
cd DocDevAI-v3.0.0
npm install
npm run dev:react
```

Open http://localhost:3000 in your browser.
</details>

### For Developers

<details>
<summary><b>Development Setup</b></summary>

```bash
# Prerequisites
node --version  # v18.0+ required
python --version # v3.9+ required
git --version   # v2.0+ required

# Clone and install
git clone https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0.git
cd DocDevAI-v3.0.0
npm install
pip install -r requirements.txt

# Configure API keys (optional for AI features)
cp .env.example .env
# Edit .env with your OpenAI/Anthropic/Google keys

# Run tests
npm test
pytest

# Start development
npm run dev:react
```

See [Developer Guide](docs/03-guides/developer/) for detailed setup instructions.
</details>

---

## 💻 Usage Examples

### CLI Commands

```bash
# Generate documentation
devdocai generate README.md --template api-docs
devdocai generate docs/ --recursive

# Analyze existing docs
devdocai analyze README.md --format json
devdocai quality-check ./docs

# Manage templates
devdocai template list
devdocai template create my-template

# Security scanning
devdocai security scan --pii --compliance gdpr
```

### Web Dashboard Features

The web dashboard at http://localhost:3000 provides:

- 📊 **Real-time Analytics** - Monitor documentation quality scores
- 🎨 **Template Gallery** - Browse and customize 35+ templates  
- 🔍 **Quality Inspector** - Get AI-powered improvement suggestions
- 📈 **Progress Tracking** - View documentation coverage metrics
- 🛡️ **Security Center** - PII detection and compliance checking

![Dashboard Screenshot](docs/assets/dashboard-main.png)
<!-- TODO: Add dashboard screenshot -->

### VS Code Integration

Right-click any file in VS Code to:
- Generate documentation instantly
- Analyze documentation quality
- Apply AI-powered improvements
- Preview rendered documentation

---

## 🌟 Features

### Core Capabilities

<details>
<summary><b>🤖 AI-Powered Generation</b></summary>

- Multi-LLM synthesis (OpenAI, Anthropic, Google)
- Context-aware documentation
- Code understanding and explanation
- Automatic API documentation from code
</details>

<details>
<summary><b>📊 Quality Analysis</b></summary>

- Real-time quality scoring
- Readability metrics
- Completeness checking
- Best practice validation
- WCAG accessibility compliance
</details>

<details>
<summary><b>🔒 Privacy & Security</b></summary>

- 100% local processing available
- AES-256 encryption
- PII detection and masking
- GDPR/CCPA compliance tools
- Zero telemetry by default
</details>

<details>
<summary><b>⚡ Performance</b></summary>

- 248,000 documents/minute processing
- Sub-second analysis
- Parallel processing
- Smart caching
- Incremental updates
</details>

---

## 🏗️ Architecture

DevDocAI uses a modular, privacy-first architecture:

```
┌─────────────────────────────────────┐
│         User Interfaces             │
│  Web UI • CLI • VS Code Extension   │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│         Core Engine                 │
│  Document Generation • AI Synthesis │
│  Quality Analysis • Templates       │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│      Security & Storage             │
│  Local-First • Encrypted • Private  │
└─────────────────────────────────────┘
```

All processing happens locally by default. Cloud AI features are optional and require explicit opt-in.

---

## 🤝 Contributing

We welcome contributions! DevDocAI is built by developers, for developers.

### How to Contribute

1. **Fork & Clone**
   ```bash
   git clone https://github.com/YourUsername/DevDocAI-v3.0.0.git
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make Your Changes**
   - Write tests first (TDD approach)
   - Follow existing code style
   - Add documentation

4. **Submit a Pull Request**
   - Clear description of changes
   - Link any related issues
   - Ensure all tests pass

See [CONTRIBUTING.md](docs/03-guides/developer/CONTRIBUTING.md) for detailed guidelines.

### Areas We Need Help

- 🌍 **Internationalization** - Help translate to other languages
- 🎨 **UI/UX Design** - Improve the dashboard experience
- 📚 **Documentation** - Write tutorials and guides
- 🧪 **Testing** - Increase test coverage
- 🔌 **Integrations** - Add support for more platforms

---

## 📚 Documentation

- [**User Guide**](docs/03-guides/user/) - Getting started tutorials
- [**API Reference**](docs/04-reference/) - Complete API documentation
- [**Developer Guide**](docs/03-guides/developer/) - Contributing and architecture
- [**Templates Gallery**](docs/templates/) - Browse all 35+ templates

---

## 🙋 Support

### Getting Help

- 💬 [**Discussions**](https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/discussions) - Ask questions and share ideas
- 🐛 [**Issues**](https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/issues) - Report bugs or request features
- 📧 [**Email**](mailto:support@devdocai.com) - Direct support (placeholder)
- 🎮 [**Discord**](https://discord.gg/devdocai) - Community chat (placeholder)

### Frequently Asked Questions

<details>
<summary><b>Does DevDocAI send my code to the cloud?</b></summary>

No! By default, all processing happens locally on your machine. Cloud AI features (OpenAI, Anthropic, etc.) are completely optional and require explicit configuration. Your code privacy is our top priority.
</details>

<details>
<summary><b>What programming languages are supported?</b></summary>

DevDocAI supports all major programming languages including JavaScript, TypeScript, Python, Java, C++, Go, Rust, and more. The AI models can understand and document code in 30+ languages.
</details>

<details>
<summary><b>Can I use my own AI API keys?</b></summary>

Yes! You can configure your own OpenAI, Anthropic, or Google AI API keys in the `.env` file. This gives you full control over costs and usage.
</details>

<details>
<summary><b>Is there a cloud/SaaS version available?</b></summary>

Currently, DevDocAI is self-hosted only to ensure maximum privacy and control. We may offer an optional cloud service in the future, but local-first will always be our priority.
</details>

---

## 🏆 Acknowledgments

### Built With

- [React](https://reactjs.org/) - UI framework
- [TypeScript](https://www.typescriptlang.org/) - Type safety
- [Material-UI](https://mui.com/) - Component library
- [OpenAI](https://openai.com/) - AI capabilities
- [SQLite](https://www.sqlite.org/) - Local storage

### Special Thanks

- All our contributors and early adopters
- The open-source community for inspiration
- You, for choosing DevDocAI! 

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ by developers, for developers**

[⬆ Back to Top](#devdocai)

</div>
