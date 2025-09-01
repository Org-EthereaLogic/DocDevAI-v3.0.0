# DevDocAI VS Code Extension

AI-powered documentation generation and analysis directly in VS Code.

## Features

### 📝 Documentation Generation
- Generate comprehensive documentation from code comments and structure
- Support for Python, TypeScript, JavaScript, and more
- Multiple documentation templates (API, Class, Function, Module, etc.)
- Context-aware generation with code analysis

### 📊 Quality Analysis
- Real-time documentation quality scoring
- Detailed metrics: Completeness, Clarity, Accuracy, Maintainability
- Inline suggestions and improvements
- Visual quality indicators in status bar

### 🔒 Security Integration
- Built-in security scanning
- PII detection in documentation
- SBOM generation
- Vulnerability reporting

### 🚀 MIAIR Optimization
- Shannon entropy-based optimization
- Intelligent documentation structuring
- Performance insights
- Quality recommendations

### 🎨 Rich UI Experience
- Interactive dashboard
- Document tree view
- Quality metrics visualization
- Template management

## Installation

1. Install from VS Code Marketplace:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Search for "DevDocAI"
   - Click Install

2. Manual Installation:
   ```bash
   cd src/modules/M013-VSCodeExtension
   npm install
   npm run compile
   code --install-extension devdocai-3.0.0.vsix
   ```

## Requirements

- VS Code 1.70.0 or higher
- Python 3.9+ (for backend CLI)
- Node.js 16+ (for extension)
- DevDocAI CLI installed (M012)

## Configuration

Configure DevDocAI through VS Code settings:

```json
{
  "devdocai.operationMode": "BASIC",
  "devdocai.autoDocumentation": false,
  "devdocai.defaultTemplate": "module",
  "devdocai.qualityThreshold": 70,
  "devdocai.enableMIAIR": true,
  "devdocai.enableSecurity": true
}
```

### Operation Modes

- **BASIC**: Core functionality only
- **PERFORMANCE**: Optimized with caching and lazy loading
- **SECURE**: Full security features enabled
- **ENTERPRISE**: All features with maximum security and performance

## Usage

### Generate Documentation

1. **Command Palette**: 
   - Press `Ctrl+Shift+P`
   - Type "DevDocAI: Generate Documentation"
   - Select template and options

2. **Context Menu**:
   - Right-click on a file in Explorer
   - Select "Generate Documentation"

3. **Keyboard Shortcut**:
   - Press `Ctrl+Alt+D` (Windows/Linux)
   - Press `Cmd+Alt+D` (Mac)

### Analyze Quality

1. Open a markdown documentation file
2. Press `Ctrl+Alt+Q` to analyze quality
3. View detailed report with suggestions

### Open Dashboard

1. Press `Ctrl+Alt+Shift+D` to open dashboard
2. Or click the DevDocAI status bar item
3. View metrics, recent activity, and quick actions

## Commands

| Command | Description | Shortcut |
|---------|-------------|----------|
| `devdocai.generateDocumentation` | Generate documentation for current file | `Ctrl+Alt+D` |
| `devdocai.analyzeQuality` | Analyze documentation quality | `Ctrl+Alt+Q` |
| `devdocai.openDashboard` | Open DevDocAI dashboard | `Ctrl+Alt+Shift+D` |
| `devdocai.selectTemplate` | Select documentation template | - |
| `devdocai.configureSettings` | Configure extension settings | - |
| `devdocai.runSecurityScan` | Run security scan on code | - |
| `devdocai.showMIAIRInsights` | Show MIAIR optimization insights | - |
| `devdocai.refreshDocumentation` | Refresh existing documentation | - |
| `devdocai.exportDocumentation` | Export documentation to various formats | - |
| `devdocai.toggleAutoDoc` | Toggle automatic documentation | - |

## Views

### Document Tree
Shows all documents in workspace with quality indicators:
- ✅ Documented (green)
- ⚠️ Needs Update (yellow)
- ❌ Undocumented (red)

### Quality Metrics
Displays real-time quality scores for active document:
- Overall score
- Individual metrics
- Improvement suggestions

### Templates
Browse and select from available documentation templates:
- 35+ built-in templates
- Custom template support
- Language-specific templates

## Status Bar

The DevDocAI status bar item shows:
- Current document quality score
- Documentation coverage percentage
- Quick access to dashboard
- Real-time status updates

## Development

### Building from Source

```bash
# Clone repository
git clone https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0.git
cd DocDevAI-v3.0.0/src/modules/M013-VSCodeExtension

# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Run tests
npm test

# Package extension
npm run package
```

### Testing

Run the test suite:
```bash
npm test
```

Coverage report:
```bash
npm run test:coverage
```

### Debugging

1. Open the extension folder in VS Code
2. Press F5 to launch Extension Development Host
3. Set breakpoints in source code
4. Test commands in the development instance

## Architecture

The extension follows a modular architecture:

```
M013-VSCodeExtension/
├── src/
│   ├── extension.ts         # Main entry point
│   ├── commands/            # Command implementations
│   ├── providers/           # Tree/hover/lens providers
│   ├── services/           # CLI, config, status services
│   ├── webviews/          # Dashboard and panels
│   └── utils/             # Helper utilities
├── resources/             # Static assets
└── tests/                # Test suite
```

### Integration with DevDocAI Modules

- **M001**: Configuration management
- **M002**: Local storage for documentation
- **M003**: MIAIR optimization engine
- **M004**: Document generation
- **M005**: Quality analysis
- **M006**: Template registry
- **M007**: Review engine
- **M008**: LLM adapter (optional)
- **M009**: Enhancement pipeline
- **M010**: Security module
- **M011**: UI components for webviews
- **M012**: CLI interface for backend communication

## Performance

- Lazy loading of heavy components
- Caching of analysis results
- Debounced status updates
- Efficient file watching
- Minimal memory footprint

## Security

- No telemetry by default (privacy-first)
- Encrypted API key storage
- Secure communication with CLI
- Input validation
- XSS prevention in webviews

## Troubleshooting

### Extension not activating
- Check VS Code version (requires 1.70+)
- Verify Python installation
- Check extension logs: View → Output → DevDocAI

### CLI connection issues
- Verify Python path in settings
- Check CLI installation: `python -m devdocai.cli --version`
- Review logs for error messages

### Performance issues
- Switch to PERFORMANCE mode in settings
- Disable auto-documentation for large projects
- Increase quality threshold to reduce analysis frequency

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure 80% code coverage
5. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

- GitHub Issues: [Report bugs](https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/issues)
- Documentation: [Wiki](https://github.com/Org-EthereaLogic/DocDevAI-v3.0.0/wiki)
- Community: Join our discussions

## Changelog

### Version 3.0.0
- Initial release with full DevDocAI integration
- Support for 9+ programming languages
- 35+ documentation templates
- Real-time quality analysis
- Security scanning integration
- MIAIR optimization
- Interactive dashboard
- Auto-documentation mode

---

Built with ❤️ for developers who value great documentation.