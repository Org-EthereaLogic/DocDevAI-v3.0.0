# DevDocAI v3.5.0 Build Instructions

---

## Implementation Status Matrix

| Component | Status | Progress | Target Date | Notes |
|-----------|--------|----------|-------------|--------|
| **Phase 1: Foundation** | Planned | 0% | Q1 2026 | Core architecture design complete |
| Document Generator (M004) | Planned | 0% | Month 1-2 | 40+ template specifications ready |
| Tracking Matrix (M005) | Planned | 0% | Month 1-2 | Real-time dependency mapping design |
| Review Engine (M007) | Planned | 0% | Month 2 | 10+ review types specified |
| VS Code Extension | Planned | 0% | Month 2 | Extension manifest designed |
| CLI Interface | Planned | 0% | Month 1 | Command specifications complete |
| **Phase 2: Intelligence** | Planned | 0% | Q2 2026 | AI integration architecture defined |
| MIAIR Engine (M003) | Planned | 0% | Month 3-4 | Entropy optimization algorithms ready |
| LLM Adapter (M008) | Planned | 0% | Month 3-4 | Multi-provider interface designed |
| Enhancement Pipeline (M009) | Planned | 0% | Month 4 | Quality improvement workflow specified |
| **Phase 3: Advanced** | Planned | 0% | Q3 2026 | Compliance features designed |
| SBOM Generator (M010) | Planned | 0% | Month 5-6 | SPDX 2.3/CycloneDX 1.4 specs |
| PII Detector (M011) | Planned | 0% | Month 5-6 | 95% accuracy target defined |
| DSR Handler (M012) | Planned | 0% | Month 6 | GDPR/CCPA workflows designed |
| Plugin System (M013) | Planned | 0% | Month 6 | Secure sandboxing architecture |

**Current Phase**: Design Specification Complete
**Implementation Start**: Pending
**Estimated Completion**: 8-12 months from implementation start

---

## Document Information

**Version:** 3.5.0
**Date:** August 23, 2025
**Status:** FINAL - Suite Aligned v3.5.0
**Document Type:** Build and Implementation Guide
**Implementation Status:** Design Phase - Ready for Development
**License:** Apache-2.0 (Core), MIT (Plugin SDK)

### Living Document Approach

This document follows a living document strategy where sections are progressively updated as implementation proceeds:

- **🟢 Implemented**: Feature is built and tested
- **🟡 In Progress**: Currently under development
- **🔴 Planned**: Design complete, awaiting implementation
- **🔵 Future Enhancement**: Planned for versions beyond 3.5.0

Current Status: **🔴 All features in Planned state**

---

## Prerequisites

### System Requirements

| Component | Minimum | Recommended | Purpose |
|-----------|---------|-------------|---------|
| **Node.js** | v18.0.0 | v20.0.0 | Runtime environment |
| **npm/yarn** | v9.0.0 | Latest stable | Package management |
| **Python** | v3.8.0 | v3.11.0 | AI models & PII detection |
| **Git** | v2.30.0 | Latest stable | Version control |
| **VS Code** | v1.85.0 | Latest stable | Extension host |
| **RAM** | 1GB | 4GB+ | See Memory Modes below |
| **Storage** | 2GB | 10GB+ | Models & cache |

### Memory Mode Requirements

Aligned with Architecture Blueprint Section 9.1:

| Mode | RAM | Features | Local Models | Performance |
|------|-----|----------|--------------|-------------|
| **Baseline** | <2GB | Core only, no AI | None | Basic operations |
| **Standard** | 2-4GB | Core + Cloud AI | None | Cloud-enhanced |
| **Enhanced** | 4-8GB | Core + Local AI | MiAIR-v3.5.gguf | Offline AI |
| **Performance** | >8GB | Full features | All models | Maximum speed |

### Automated Prerequisite Checker

```bash
# Run the prerequisite verification script (once implemented)
npm run doctor

# The script will check:
# ✓ Node.js version (≥18.0.0)
# ✓ npm version (≥9.0.0)
# ✓ Python version (≥3.8.0)
# ✓ Git version (≥2.30.0)
# ✓ VS Code installation
# ✓ Available RAM and recommended memory mode
# ✓ Available disk space (≥2GB)
# ✓ Write permissions in installation directory
# ✓ Network connectivity (for cloud features)
# ✓ GPU availability (optional, for enhanced performance)
```

Future implementation will include automatic fixes for common issues:

- Missing Node.js → Provide platform-specific installation command
- Outdated npm → Run `npm install -g npm@latest`
- Insufficient permissions → Guide through permission setup
- Low disk space → Suggest cleanup or alternative location

---

## Installation Process

### Phase 1: Environment Setup

#### 1. Clone Repository

```bash
# Clone the repository (when available)
git clone https://github.com/devdocai/devdocai-v3.5.git
cd devdocai-v3.5

# Verify repository structure
tree -L 2
# Expected structure:
# ├── src/
# │   ├── core/           # M001-M002: Core components
# │   ├── generator/      # M004: Document generator
# │   ├── analyzer/       # M007: Review engine
# │   ├── matrix/         # M005: Tracking matrix
# │   ├── ai/            # M003, M008-M009: AI components
# │   └── compliance/     # M010-M012: Compliance features
# ├── extensions/
# │   └── vscode/        # VS Code extension
# ├── cli/              # Command-line interface
# ├── plugins/          # M013: Plugin system
# ├── templates/        # 40+ document templates
# ├── models/          # Local AI models
# ├── tests/           # Test suites
# └── docs/            # Documentation
```

#### 2. Install Dependencies

```bash
# Install Node.js dependencies
npm install

# Install Python dependencies for AI features
pip install -r requirements.txt

# Development dependencies (local to project)
npm install --save-dev \
  typescript@5.3.3 \
  @types/node@20.11.0 \
  @vscode/vsce@2.22.0 \
  yo@5.0.0 \
  generator-code@1.7.8

# Verify installations
npm run verify:dependencies
```

### Phase 2: Configuration

#### 1. Memory Mode Configuration

Create `.devdocai.yml` in project root:

```yaml
# DevDocAI v3.5.0 Configuration
version: "3.5.0"
metadata:
  project_name: "MyProject"
  organization: "MyOrg"
  quality_gate: 85  # Exactly 85% as per SRS requirements

# Memory mode (auto-detected or manually set)
memory:
  mode: "standard"  # baseline | standard | enhanced | performance
  cache_size: 1024  # MB
  model_loading: "lazy"  # lazy | eager

# Feature toggles based on memory mode
features:
  local_ai: false  # Enabled in enhanced/performance modes
  cloud_ai: true   # Available in all modes except baseline
  batch_processing: true
  real_time_analysis: true

# Performance tuning
performance:
  max_workers: 4
  chunk_size: 1000
  debounce_ms: 500
```

#### 2. API Keys and Cost Management

Create `.env` file (never commit this):

```bash
# Cloud AI Providers (optional)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_AI_API_KEY=...

# Cost Management (REQ-044, US-009)
DAILY_COST_LIMIT=10.00
MONTHLY_COST_LIMIT=200.00
COST_ALERT_THRESHOLD=0.80

# API Routing Preferences
PREFERRED_PROVIDER=openai
FALLBACK_PROVIDER=anthropic
ROUTING_STRATEGY=cost_optimized  # cost_optimized | quality_first | balanced

# Compliance Features
ENABLE_SBOM_SIGNING=true
ENABLE_PII_DETECTION=true
ENABLE_AUDIT_LOGGING=true
```

#### 3. Local Model Setup

Detailed setup for local AI models in Enhanced/Performance modes:

```bash
# Create models directory
mkdir -p models/miair
mkdir -p models/embeddings
mkdir -p models/pii

# Download MiAIR model (Enhanced mode)
# Note: These are placeholder URLs for future model distribution
curl -L https://models.devdocai.org/miair/v3.5/miair-v3.5.gguf \
  -o models/miair/miair-v3.5.gguf

# Download embedding model for semantic search
curl -L https://models.devdocai.org/embeddings/v1.0/embeddings-v1.0.gguf \
  -o models/embeddings/embeddings-v1.0.gguf

# Download PII detection model
curl -L https://models.devdocai.org/pii/v2.0/pii-detector-v2.0.gguf \
  -o models/pii/pii-detector-v2.0.gguf

# Verify model integrity
npm run models:verify

# Expected output:
# ✓ MiAIR v3.5 model: Valid (SHA256: abc123...)
# ✓ Embeddings v1.0 model: Valid (SHA256: def456...)
# ✓ PII Detector v2.0 model: Valid (SHA256: ghi789...)
# ✓ Total model size: 3.7GB
# ✓ Available disk space: 25.3GB
```

Model configuration in `.devdocai.yml`:

```yaml
models:
  miair:
    path: "./models/miair/miair-v3.5.gguf"
    quantization: "Q4_K_M"  # Optimized for 4-8GB RAM
    context_length: 4096
    batch_size: 512
    threads: 4

  embeddings:
    path: "./models/embeddings/embeddings-v1.0.gguf"
    dimensions: 768
    max_tokens: 512

  pii_detector:
    path: "./models/pii/pii-detector-v2.0.gguf"
    confidence_threshold: 0.95  # 95% accuracy target (US-020)
    categories:
      - names
      - emails
      - phones
      - addresses
      - ssn
      - credit_cards
      - medical_records
```

### Phase 3: Security Setup

#### Generate Security Keys

```bash
# Generate Ed25519 signing keys for plugins
npm run security:keygen

# Generate encryption keys for sensitive data
npm run security:generate-encryption-keys

# Create certificate for SBOM signing
npm run security:create-sbom-cert

# Output:
# ✓ Plugin signing keys generated: keys/plugin-sign.key, keys/plugin-sign.pub
# ✓ Encryption keys generated: keys/encryption.key
# ✓ SBOM certificate created: keys/sbom-cert.pem
# ✓ Keys secured with appropriate permissions (600)
```

---

## Build Process

### Development Build

```bash
# Complete development build
npm run build:dev

# Individual component builds
npm run build:core        # Core system (M001-M002)
npm run build:generator    # Document generator (M004)
npm run build:analyzer     # Analysis engine (M007)
npm run build:matrix       # Tracking matrix (M005)
npm run build:ai          # AI components (M003, M008-M009)
npm run build:compliance   # Compliance features (M010-M012)
npm run build:vscode      # VS Code extension
npm run build:cli         # CLI tool

# Watch mode for development
npm run dev
```

### Production Build

```bash
# Optimized production build
npm run build:prod

# With specific optimizations
npm run build:prod -- --minify --tree-shake --optimize-images

# Platform-specific builds
npm run build:win     # Windows
npm run build:mac     # macOS
npm run build:linux   # Linux

# Docker build
docker build -t devdocai:3.5.0 .
```

### Testing

Comprehensive testing aligned with Test Plan requirements:

```bash
# Run all tests (80% coverage minimum, 90% for critical paths)
npm test

# Unit tests for each module
npm run test:unit

# Integration tests
npm run test:integration

# End-to-end tests
npm run test:e2e

# Compliance tests (US-019, US-020, US-021)
npm run test:compliance

# Performance tests (sub-second response times)
npm run test:performance

# Security tests (100% coverage for security functions)
npm run test:security

# Accessibility tests (WCAG 2.1 Level AA)
npm run test:a11y

# Coverage report
npm run test:coverage
```

---

## Verification Process

### Component Verification

```bash
# Verify all components are properly built
npm run verify:all

# Individual verifications
npm run verify:core        # ✓ Core system operational
npm run verify:generator    # ✓ 40+ templates available
npm run verify:analyzer     # ✓ 10+ review types functional
npm run verify:matrix       # ✓ Real-time tracking active
npm run verify:ai          # ✓ MIAIR engine ready
npm run verify:compliance   # ✓ SBOM, PII, DSR operational
npm run verify:quality-gate # ✓ 85% threshold configured
```

### VS Code Extension Verification

```bash
# Package the extension
cd extensions/vscode
npm run package

# Install in VS Code
code --install-extension devdocai-3.5.0.vsix

# Verify commands are available
code --list-extensions | grep devdocai
# Expected: devdocai.devdocai-vscode@3.5.0
```

### CLI Verification

```bash
# Link CLI globally
npm link

# Verify installation
devdocai --version
# Expected: DevDocAI v3.5.0

# Test core commands
devdocai generate --list-templates  # Should show 40+ templates
devdocai analyze --help            # Should show 10+ review types
devdocai sbom generate --help      # Should show SPDX/CycloneDX options
devdocai scan-pii --help          # Should show PII categories
devdocai dsr --help               # Should show export/delete/rectify
```

---

## Build Artifacts

### Expected Output Structure

```
dist/
├── core/
│   ├── devdocai-core.js         # Core library
│   ├── devdocai-core.d.ts       # TypeScript definitions
│   └── devdocai-core.js.map     # Source maps
├── vscode/
│   └── devdocai-3.5.0.vsix      # VS Code extension package
├── cli/
│   ├── devdocai-cli              # Executable (Unix)
│   ├── devdocai-cli.exe          # Executable (Windows)
│   └── devdocai-cli.pkg          # macOS package
├── plugins/
│   ├── plugin-sdk-3.5.0.tgz      # Plugin SDK package
│   └── examples/                 # Example plugins
├── templates/
│   └── templates-3.5.0.zip       # All 40+ templates
├── models/
│   ├── miair-v3.5.gguf          # MiAIR model
│   ├── embeddings-v1.0.gguf     # Embeddings model
│   └── pii-detector-v2.0.gguf   # PII detection model
└── compliance/
    ├── sbom.spdx.json            # SPDX format SBOM
    ├── sbom.cyclonedx.json       # CycloneDX format SBOM
    └── signatures/               # Digital signatures
```

### Artifact Verification

```bash
# Verify all artifacts
npm run verify:artifacts

# Checks performed:
# ✓ All files present
# ✓ File sizes within expected ranges
# ✓ Digital signatures valid
# ✓ SBOM complete and signed
# ✓ Version numbers consistent
# ✓ License files included
```

---

## Troubleshooting

### Common Issues and Solutions

#### Memory Mode Detection Issues

```bash
# Problem: Incorrect memory mode detected
# Solution: Manually set in .devdocai.yml
memory:
  mode: "enhanced"  # Force specific mode

# Verify with:
devdocai config get memory.mode
```

#### Model Loading Failures

```bash
# Problem: Local models fail to load
# Solution 1: Verify model files
npm run models:verify

# Solution 2: Check memory availability
devdocai doctor --check-memory

# Solution 3: Use quantized models for lower RAM
# Edit .devdocai.yml:
models:
  miair:
    quantization: "Q4_0"  # Smaller but less accurate
```

#### Build Failures

```bash
# Problem: Build fails with dependency errors
# Solution: Clean and rebuild
npm run clean
rm -rf node_modules package-lock.json
npm install
npm run build:dev

# Problem: TypeScript errors
# Solution: Check TypeScript version
npx tsc --version  # Should be 5.3.3
```

#### API Rate Limits

```bash
# Problem: Hit API rate limits
# Solution: Configure fallback providers in .env
FALLBACK_PROVIDER=anthropic
ROUTING_STRATEGY=balanced

# Monitor usage:
devdocai cost report --period=today
```

#### Plugin Signature Verification

```bash
# Problem: Plugin signature verification fails
# Solution: Regenerate keys
npm run security:keygen

# Verify plugin:
devdocai plugin verify <plugin-name>
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/build.yml
name: DevDocAI Build Pipeline
on: [push, pull_request]

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        node: [18, 20]

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node }}
          cache: 'npm'

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          npm ci
          pip install -r requirements.txt

      - name: Run Prerequisite Check
        run: npm run doctor

      - name: Build
        run: npm run build:prod

      - name: Test
        run: npm test

      - name: Generate SBOM
        run: npm run sbom:generate

      - name: Package Artifacts
        run: npm run package:all

      - name: Upload Artifacts
        uses: actions/upload-artifact@v3
        with:
          name: devdocai-${{ matrix.os }}-node${{ matrix.node }}
          path: dist/
```

---

## Release Process

### Version Management

```bash
# Update version across all components
npm run version:update 3.5.0

# Generate changelog
npm run changelog:generate

# Tag release
git tag -s v3.5.0 -m "Release v3.5.0"
git push origin v3.5.0
```

### Release Checklist

- [ ] All tests passing (100% critical paths)
- [ ] Documentation updated
- [ ] SBOM generated and signed
- [ ] Security audit completed
- [ ] Performance benchmarks met
- [ ] Accessibility validation passed
- [ ] Release notes prepared
- [ ] Artifacts signed
- [ ] Docker images built
- [ ] npm packages published

---

## Support and Resources

### Documentation

- **User Manual**: `docs/user-manual.md`
- **API Documentation**: `docs/api-reference.md`
- **Plugin Development Guide**: `docs/plugin-guide.md`
- **Architecture Blueprint**: `docs/architecture.md`

### Community

- **GitHub Issues**: <https://github.com/devdocai/devdocai-v3.5/issues>
- **Discussions**: <https://github.com/devdocai/devdocai-v3.5/discussions>
- **Discord**: <https://discord.gg/devdocai>
- **Email**: <support@devdocai.org>

### Contributing

See `CONTRIBUTING.md` for guidelines on:

- Code style and standards
- Testing requirements
- Pull request process
- Code of conduct

---

## Appendices

### Appendix A: Module Implementation Status

| Module ID | Component | Status | Test Coverage | Notes |
|-----------|-----------|--------|---------------|--------|
| M001 | Core Infrastructure | 🔴 Planned | 0% | Foundation layer |
| M002 | Local Storage | 🔴 Planned | 0% | File system operations |
| M003 | MIAIR Engine | 🔴 Planned | 0% | Entropy optimization |
| M004 | Document Generator | 🔴 Planned | 0% | 40+ templates |
| M005 | Tracking Matrix | 🔴 Planned | 0% | Real-time updates |
| M006 | Suite Manager | 🔴 Planned | 0% | Cross-references |
| M007 | Review Engine | 🔴 Planned | 0% | 10+ review types |
| M008 | LLM Adapter | 🔴 Planned | 0% | Multi-provider |
| M009 | Enhancement Pipeline | 🔴 Planned | 0% | Quality improvement |
| M010 | SBOM Generator | 🔴 Planned | 0% | SPDX/CycloneDX |
| M011 | PII Detector | 🔴 Planned | 0% | 95% accuracy |
| M012 | DSR Handler | 🔴 Planned | 0% | GDPR/CCPA |
| M013 | Plugin System | 🔴 Planned | 0% | Secure sandbox |

### Appendix B: Performance Benchmarks

| Operation | Target | Current | Status |
|-----------|--------|---------|--------|
| VS Code Response | <500ms | N/A | 🔴 Not Measured |
| Document Analysis (10 pages) | <10s | N/A | 🔴 Not Measured |
| SBOM Generation | <30s | N/A | 🔴 Not Measured |
| PII Scan (100 pages) | <60s | N/A | 🔴 Not Measured |
| Matrix Update | <1s | N/A | 🔴 Not Measured |
| Enhancement (MIAIR) | <45s | N/A | 🔴 Not Measured |

### Appendix C: Compliance Checklist

- [ ] GDPR Article 15-22 compliance (DSR implementation)
- [ ] CCPA compliance (data deletion, portability)
- [ ] SPDX 2.3 specification compliance
- [ ] CycloneDX 1.4 specification compliance
- [ ] WCAG 2.1 Level AA accessibility
- [ ] OWASP security standards
- [ ] IEEE 830-1998 documentation standards

---

**Document Status**: FINAL - v3.5.0 Suite Aligned
**Alignment**: Complete consistency with Architecture v3.6.0, SRS v3.6.0, PRD v3.6.0, and User Stories v3.5.0
**Last Updated**: August 23, 2025
**Next Review**: Upon implementation start

This document serves as the authoritative build and implementation guide for DevDocAI v3.5.0, providing a clear roadmap from the current design phase through to full implementation.
