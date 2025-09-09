#!/usr/bin/env ts-node

/**
 * Module Generator Script
 * Generates boilerplate for new modules based on Module 1's unified architecture
 */

import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';
import { execSync } from 'child_process';

interface ModuleConfig {
  id: string;
  name: string;
  description: string;
  dependencies?: string[];
  primaryMetric?: string;
  baselineValue?: number;
  targetValue?: number;
  metricUnit?: string;
}

class ModuleGenerator {
  private templatePath = path.join(__dirname, '../templates/module-template.yml');
  private projectRoot = path.join(__dirname, '../..');

  constructor(private config: ModuleConfig) {}

  async generate(): Promise<void> {
    console.log(`🚀 Generating module ${this.config.id}: ${this.config.name}`);

    // Load template
    const template = this.loadTemplate();

    // Replace placeholders
    const processedTemplate = this.processTemplate(template);

    // Create directory structure
    await this.createDirectoryStructure();

    // Generate files
    await this.generateFiles(processedTemplate);

    // Create workflow
    await this.createWorkflow();

    // Update package.json scripts
    await this.updatePackageJson();

    // Initialize git branch
    await this.initializeGitBranch();

    console.log(`✅ Module ${this.config.id} generated successfully!`);
    console.log(`📝 Next steps:`);
    console.log(`   1. Review the generated structure in src/modules/${this.config.id}/`);
    console.log(`   2. Start with Pass 0: npm run module:design ${this.config.id}`);
    console.log(`   3. Follow the 5-pass methodology in MODULE_${this.config.id}_PLAN.md`);
  }

  private loadTemplate(): string {
    return fs.readFileSync(this.templatePath, 'utf-8');
  }

  private processTemplate(template: string): any {
    const processed = template
      .replace(/{{MODULE_ID}}/g, this.config.id)
      .replace(/{{MODULE_NAME}}/g, this.config.name)
      .replace(/{{MODULE_DESCRIPTION}}/g, this.config.description)
      .replace(/{{CREATED_DATE}}/g, new Date().toISOString())
      .replace(/{{ADDITIONAL_DEPENDENCIES}}/g,
        this.config.dependencies?.map(d => `    - ${d}`).join('\n') || '')
      .replace(/{{PRIMARY_METRIC}}/g, this.config.primaryMetric || 'operations_per_second')
      .replace(/{{BASELINE_VALUE}}/g, String(this.config.baselineValue || 1000))
      .replace(/{{TARGET_VALUE}}/g, String(this.config.targetValue || 10000))
      .replace(/{{METRIC_UNIT}}/g, this.config.metricUnit || 'ops/sec');

    return yaml.load(processed);
  }

  private async createDirectoryStructure(): Promise<void> {
    const dirs = [
      `src/modules/${this.config.id}/unified`,
      `src/modules/${this.config.id}/types`,
      `src/modules/${this.config.id}/utils`,
      `tests/unit/${this.config.id}`,
      `tests/integration/${this.config.id}`,
      `tests/security/${this.config.id}`,
      `tests/e2e/${this.config.id}`,
      `benchmarks/${this.config.id}`,
      `docs/api`,
      `docs/guides`,
      `examples/${this.config.id}`,
    ];

    for (const dir of dirs) {
      const fullPath = path.join(this.projectRoot, dir);
      fs.mkdirSync(fullPath, { recursive: true });
      console.log(`📁 Created: ${dir}`);
    }
  }

  private async generateFiles(moduleConfig: any): Promise<void> {
    // Generate unified implementation
    await this.generateUnifiedImplementation(moduleConfig);

    // Generate configuration
    await this.generateConfiguration(moduleConfig);

    // Generate types
    await this.generateTypes(moduleConfig);

    // Generate tests
    await this.generateTests(moduleConfig);

    // Generate benchmarks
    await this.generateBenchmarks(moduleConfig);

    // Generate documentation
    await this.generateDocumentation(moduleConfig);

    // Generate module plan
    await this.generateModulePlan(moduleConfig);
  }

  private async generateUnifiedImplementation(config: any): Promise<void> {
    const className = `${this.config.name}Unified`;
    const content = `/**
 * ${this.config.name} - Unified Implementation
 * Based on Module 1's proven unified architecture pattern
 */

import { I${this.config.name}, I${this.config.name}Config, OperationMode } from '../types';
import { ConfigurationManager } from '../../M001/unified/configuration_manager_unified';
import { BaseUnified } from '../../../core/base_unified';

export class ${className} extends BaseUnified implements I${this.config.name} {
  private config: I${this.config.name}Config;
  private mode: OperationMode;
  private configManager: ConfigurationManager;

  constructor(config?: Partial<I${this.config.name}Config>) {
    super();
    this.configManager = ConfigurationManager.getInstance();
    this.config = this.mergeConfig(config);
    this.mode = this.config.mode || OperationMode.BASIC;
    this.initialize();
  }

  private mergeConfig(config?: Partial<I${this.config.name}Config>): I${this.config.name}Config {
    const defaults = this.getDefaultConfig();
    const stored = this.configManager.get('${this.config.id}', {});
    return { ...defaults, ...stored, ...config };
  }

  private getDefaultConfig(): I${this.config.name}Config {
    return {
      mode: OperationMode.BASIC,
      enableCaching: false,
      enableSecurity: false,
      enableMonitoring: false,
      // Add module-specific defaults
    };
  }

  private initialize(): void {
    // Mode-specific initialization
    switch (this.mode) {
      case OperationMode.PERFORMANCE:
        this.initializePerformanceMode();
        break;
      case OperationMode.SECURE:
        this.initializeSecureMode();
        break;
      case OperationMode.ENTERPRISE:
        this.initializeEnterpriseMode();
        break;
      default:
        this.initializeBasicMode();
    }
  }

  private initializeBasicMode(): void {
    // Basic mode initialization
  }

  private initializePerformanceMode(): void {
    this.config.enableCaching = true;
    // Performance optimizations
  }

  private initializeSecureMode(): void {
    this.config.enableSecurity = true;
    // Security hardening
  }

  private initializeEnterpriseMode(): void {
    this.config.enableCaching = true;
    this.config.enableSecurity = true;
    this.config.enableMonitoring = true;
    // Full feature set
  }

  // Module-specific methods to be implemented

  public async process(input: any): Promise<any> {
    // Implement core functionality
    throw new Error('Not implemented');
  }

  public getMetrics(): Record<string, any> {
    return {
      mode: this.mode,
      operations: 0,
      errors: 0,
      latency: 0,
    };
  }
}

// Factory function for easy instantiation
export function create${this.config.name}(
  mode: OperationMode = OperationMode.BASIC,
  config?: Partial<I${this.config.name}Config>
): ${className} {
  return new ${className}({ ...config, mode });
}
`;

    const filePath = path.join(
      this.projectRoot,
      `src/modules/${this.config.id}/unified/${this.config.name.toLowerCase()}_unified.ts`
    );
    fs.writeFileSync(filePath, content);
    console.log(`📝 Generated: ${filePath}`);
  }

  private async generateConfiguration(config: any): Promise<void> {
    const content = `/**
 * ${this.config.name} Configuration
 */

export enum OperationMode {
  BASIC = 'basic',
  PERFORMANCE = 'performance',
  SECURE = 'secure',
  ENTERPRISE = 'enterprise',
}

export interface ${this.config.name}Config {
  mode: OperationMode;
  enableCaching: boolean;
  enableSecurity: boolean;
  enableMonitoring: boolean;

  // Performance settings
  maxConcurrency?: number;
  timeout?: number;
  retryAttempts?: number;

  // Security settings
  encryptionEnabled?: boolean;
  auditLogging?: boolean;
  rateLimiting?: boolean;

  // Module-specific settings
  // Add as needed
}

export const DEFAULT_CONFIG: ${this.config.name}Config = {
  mode: OperationMode.BASIC,
  enableCaching: false,
  enableSecurity: false,
  enableMonitoring: false,
  maxConcurrency: 10,
  timeout: 30000,
  retryAttempts: 3,
};
`;

    const filePath = path.join(
      this.projectRoot,
      `src/modules/${this.config.id}/unified/config_unified.ts`
    );
    fs.writeFileSync(filePath, content);
    console.log(`📝 Generated: ${filePath}`);
  }

  private async generateTypes(config: any): Promise<void> {
    const content = `/**
 * ${this.config.name} Type Definitions
 */

import { OperationMode } from '../unified/config_unified';

export interface I${this.config.name} {
  process(input: any): Promise<any>;
  getMetrics(): Record<string, any>;
}

export interface I${this.config.name}Config {
  mode: OperationMode;
  enableCaching: boolean;
  enableSecurity: boolean;
  enableMonitoring: boolean;
  [key: string]: any;
}

export interface I${this.config.name}Options {
  // Add module-specific options
}

export interface I${this.config.name}Result {
  success: boolean;
  data?: any;
  error?: Error;
  metadata?: Record<string, any>;
}
`;

    const filePath = path.join(
      this.projectRoot,
      `src/modules/${this.config.id}/types/index.ts`
    );
    fs.writeFileSync(filePath, content);
    console.log(`📝 Generated: ${filePath}`);
  }

  private async generateTests(config: any): Promise<void> {
    const content = `/**
 * ${this.config.name} Unit Tests
 */

import { ${this.config.name}Unified, create${this.config.name} } from '../../src/modules/${this.config.id}/unified/${this.config.name.toLowerCase()}_unified';
import { OperationMode } from '../../src/modules/${this.config.id}/unified/config_unified';

describe('${this.config.name}', () => {
  let instance: ${this.config.name}Unified;

  beforeEach(() => {
    instance = create${this.config.name}();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Mode', () => {
    it('should initialize in basic mode by default', () => {
      const metrics = instance.getMetrics();
      expect(metrics.mode).toBe(OperationMode.BASIC);
    });

    it('should process input correctly', async () => {
      // Implement test
    });
  });

  describe('Performance Mode', () => {
    beforeEach(() => {
      instance = create${this.config.name}(OperationMode.PERFORMANCE);
    });

    it('should enable caching in performance mode', () => {
      const metrics = instance.getMetrics();
      expect(metrics.mode).toBe(OperationMode.PERFORMANCE);
    });
  });

  describe('Secure Mode', () => {
    beforeEach(() => {
      instance = create${this.config.name}(OperationMode.SECURE);
    });

    it('should enable security features in secure mode', () => {
      const metrics = instance.getMetrics();
      expect(metrics.mode).toBe(OperationMode.SECURE);
    });
  });

  describe('Enterprise Mode', () => {
    beforeEach(() => {
      instance = create${this.config.name}(OperationMode.ENTERPRISE);
    });

    it('should enable all features in enterprise mode', () => {
      const metrics = instance.getMetrics();
      expect(metrics.mode).toBe(OperationMode.ENTERPRISE);
    });
  });
});
`;

    const filePath = path.join(
      this.projectRoot,
      `tests/unit/${this.config.id}/${this.config.name.toLowerCase()}.test.ts`
    );
    fs.writeFileSync(filePath, content);
    console.log(`📝 Generated: ${filePath}`);
  }

  private async generateBenchmarks(config: any): Promise<void> {
    const content = `/**
 * ${this.config.name} Benchmarks
 */

import { ${this.config.name}Unified, create${this.config.name} } from '../../src/modules/${this.config.id}/unified/${this.config.name.toLowerCase()}_unified';
import { OperationMode } from '../../src/modules/${this.config.id}/unified/config_unified';
import { performance } from 'perf_hooks';

interface BenchmarkResult {
  mode: OperationMode;
  operations: number;
  duration: number;
  opsPerSecond: number;
  avgLatency: number;
}

class ${this.config.name}Benchmark {
  private results: BenchmarkResult[] = [];

  async run(): Promise<void> {
    console.log('🏃 Running ${this.config.name} Benchmarks...');

    await this.benchmarkMode(OperationMode.BASIC);
    await this.benchmarkMode(OperationMode.PERFORMANCE);
    await this.benchmarkMode(OperationMode.SECURE);
    await this.benchmarkMode(OperationMode.ENTERPRISE);

    this.printResults();
  }

  private async benchmarkMode(mode: OperationMode): Promise<void> {
    const instance = create${this.config.name}(mode);
    const operations = 10000;

    const start = performance.now();

    for (let i = 0; i < operations; i++) {
      // await instance.process(testData);
    }

    const duration = performance.now() - start;
    const opsPerSecond = (operations / duration) * 1000;
    const avgLatency = duration / operations;

    this.results.push({
      mode,
      operations,
      duration,
      opsPerSecond,
      avgLatency,
    });
  }

  private printResults(): void {
    console.log('\\n📊 Benchmark Results:');
    console.log('═'.repeat(80));

    const headers = ['Mode', 'Operations', 'Duration (ms)', 'Ops/Sec', 'Avg Latency (ms)'];
    console.log(headers.map(h => h.padEnd(15)).join(' | '));
    console.log('-'.repeat(80));

    for (const result of this.results) {
      const row = [
        result.mode,
        result.operations.toString(),
        result.duration.toFixed(2),
        result.opsPerSecond.toFixed(0),
        result.avgLatency.toFixed(4),
      ];
      console.log(row.map(r => r.padEnd(15)).join(' | '));
    }

    console.log('═'.repeat(80));

    // Check against targets
    const performanceResult = this.results.find(r => r.mode === OperationMode.PERFORMANCE);
    const target = ${this.config.targetValue || 10000};

    if (performanceResult && performanceResult.opsPerSecond >= target) {
      console.log(\`✅ Performance target met: \${performanceResult.opsPerSecond.toFixed(0)} ops/sec >= \${target} ops/sec\`);
    } else {
      console.log(\`❌ Performance target not met: \${performanceResult?.opsPerSecond.toFixed(0) || 0} ops/sec < \${target} ops/sec\`);
    }
  }
}

// Run benchmarks
const benchmark = new ${this.config.name}Benchmark();
benchmark.run().catch(console.error);
`;

    const filePath = path.join(
      this.projectRoot,
      `benchmarks/${this.config.id}/${this.config.name.toLowerCase()}.bench.ts`
    );
    fs.writeFileSync(filePath, content);
    console.log(`📝 Generated: ${filePath}`);
  }

  private async generateDocumentation(config: any): Promise<void> {
    const apiDoc = `# ${this.config.name} API Documentation

## Overview
${this.config.description}

## Installation
\`\`\`typescript
import { create${this.config.name} } from './modules/${this.config.id}/unified/${this.config.name.toLowerCase()}_unified';
\`\`\`

## Usage

### Basic Mode
\`\`\`typescript
const ${this.config.name.toLowerCase()} = create${this.config.name}();
const result = await ${this.config.name.toLowerCase()}.process(data);
\`\`\`

### Performance Mode
\`\`\`typescript
const ${this.config.name.toLowerCase()} = create${this.config.name}(OperationMode.PERFORMANCE);
const result = await ${this.config.name.toLowerCase()}.process(data);
\`\`\`

### Secure Mode
\`\`\`typescript
const ${this.config.name.toLowerCase()} = create${this.config.name}(OperationMode.SECURE);
const result = await ${this.config.name.toLowerCase()}.process(data);
\`\`\`

### Enterprise Mode
\`\`\`typescript
const ${this.config.name.toLowerCase()} = create${this.config.name}(OperationMode.ENTERPRISE);
const result = await ${this.config.name.toLowerCase()}.process(data);
\`\`\`

## API Reference

### Methods

#### process(input: any): Promise<any>
Processes the input data according to the configured mode.

#### getMetrics(): Record<string, any>
Returns current metrics and statistics.

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| mode | OperationMode | BASIC | Operation mode |
| enableCaching | boolean | false | Enable caching |
| enableSecurity | boolean | false | Enable security features |
| enableMonitoring | boolean | false | Enable monitoring |

## Performance Benchmarks

| Mode | Target | Achieved | Status |
|------|--------|----------|--------|
| BASIC | ${this.config.baselineValue} ${this.config.metricUnit} | TBD | ⏳ |
| PERFORMANCE | ${this.config.targetValue} ${this.config.metricUnit} | TBD | ⏳ |
| SECURE | ${this.config.targetValue * 0.9} ${this.config.metricUnit} | TBD | ⏳ |
| ENTERPRISE | ${this.config.targetValue * 0.85} ${this.config.metricUnit} | TBD | ⏳ |
`;

    const apiPath = path.join(this.projectRoot, `docs/api/${this.config.id}.md`);
    fs.writeFileSync(apiPath, apiDoc);
    console.log(`📝 Generated: ${apiPath}`);
  }

  private async generateModulePlan(config: any): Promise<void> {
    const plan = `# MODULE ${this.config.id}: ${this.config.name} Development Plan

## Overview
${this.config.description}

## 5-Pass Development Methodology

### Pass 0: Design & Architecture (Current)
**Status:** 🟡 In Progress
**Timeline:** 2-3 days

#### Tasks:
- [ ] Define module interfaces
- [ ] Create API specification
- [ ] Design data models
- [ ] Plan integration points with ${this.config.dependencies?.join(', ') || 'M001'}
- [ ] Document performance targets
- [ ] Define security requirements

#### Deliverables:
- MODULE_${this.config.id}_DESIGN.md
- API specification
- Data model schemas
- Integration plan

#### Quality Gates:
- Complexity score < 10
- Design review approved
- All interfaces defined

### Pass 1: Core Implementation
**Status:** ⏳ Pending
**Timeline:** 3-4 days

#### Tasks:
- [ ] Implement core ${this.config.name.toLowerCase()} functionality
- [ ] Create comprehensive unit tests (80% coverage target)
- [ ] Implement error handling
- [ ] Integrate with Configuration Manager (M001)
- [ ] Create API endpoints

#### Deliverables:
- Core implementation in \`src/modules/${this.config.id}/\`
- Unit tests with 80%+ coverage
- Integration tests
- Pass 1 completion report

#### Quality Gates:
- Test coverage ≥ 80%
- All tests passing
- Linting and type checking pass
- Basic functionality working

### Pass 2: Performance Optimization
**Status:** ⏳ Pending
**Timeline:** 2-3 days

#### Tasks:
- [ ] Profile current performance
- [ ] Implement caching strategies
- [ ] Optimize algorithms
- [ ] Add parallel processing where applicable
- [ ] Reduce memory footprint

#### Deliverables:
- Optimized implementation
- Performance benchmarks
- Pass 2 completion report

#### Quality Gates:
- Performance improvement ≥ 10%
- Target: ${this.config.targetValue} ${this.config.metricUnit}
- Memory usage optimized
- No performance regressions

### Pass 3: Security Hardening
**Status:** ⏳ Pending
**Timeline:** 2-3 days

#### Tasks:
- [ ] Implement input validation
- [ ] Add output encoding
- [ ] Implement authentication/authorization
- [ ] Add encryption where needed
- [ ] Create security tests (95% coverage target)
- [ ] Run vulnerability scanning

#### Deliverables:
- Security-hardened implementation
- Security test suite
- Vulnerability scan report
- Pass 3 completion report

#### Quality Gates:
- Security test coverage ≥ 95%
- Zero critical/high vulnerabilities
- Security overhead < 10%
- All OWASP Top 10 addressed

### Pass 4: Refactoring & Unification
**Status:** ⏳ Pending
**Timeline:** 2 days

#### Tasks:
- [ ] Eliminate code duplication
- [ ] Unify multiple implementations
- [ ] Apply design patterns (Strategy, Factory, etc.)
- [ ] Reduce cyclomatic complexity
- [ ] Create unified architecture

#### Deliverables:
- Unified implementation
- Refactoring report
- Pass 4 completion report

#### Quality Gates:
- Code reduction ≥ 30%
- Code duplication < 5%
- Cyclomatic complexity < 8
- All tests still passing

### Pass 5: Production Readiness
**Status:** ⏳ Pending
**Timeline:** 1-2 days

#### Tasks:
- [ ] Production testing
- [ ] Real-world validation
- [ ] Complete documentation
- [ ] Prepare deployment artifacts
- [ ] Set up monitoring

#### Deliverables:
- Production-ready module
- Complete documentation
- Deployment guide
- Pass 5 completion report

#### Quality Gates:
- All production tests passing
- Documentation complete
- Monitoring configured
- Ready for deployment

## Success Metrics

### Performance
- **Baseline:** ${this.config.baselineValue} ${this.config.metricUnit}
- **Target:** ${this.config.targetValue} ${this.config.metricUnit}
- **Current:** TBD

### Quality
- **Test Coverage:** 95% (target)
- **Code Reduction:** 60% (target based on Module 1)
- **Security Grade:** A+ (target)

### Timeline
- **Total Estimated:** 12-16 days
- **Start Date:** ${new Date().toISOString().split('T')[0]}
- **Target Completion:** TBD

## Dependencies
- M001: Configuration Manager ✅
${this.config.dependencies?.map(d => `- ${d}: TBD`).join('\n') || ''}

## Risks & Mitigations
1. **Performance targets too aggressive**
   - Mitigation: Iterative optimization, consider trade-offs
2. **Integration complexity**
   - Mitigation: Early integration testing, clear interfaces
3. **Security overhead**
   - Mitigation: Selective security features by mode

## Notes
- Follow Module 1's unified architecture pattern
- Maintain backward compatibility
- Document all design decisions
- Regular check-ins at each pass completion
`;

    const planPath = path.join(this.projectRoot, `MODULE_${this.config.id}_PLAN.md`);
    fs.writeFileSync(planPath, plan);
    console.log(`📝 Generated: ${planPath}`);
  }

  private async createWorkflow(): Promise<void> {
    const workflow = `name: ${this.config.id} - ${this.config.name} Pipeline

on:
  push:
    paths:
      - 'src/modules/${this.config.id}/**'
      - 'tests/**/${this.config.id}/**'
      - 'benchmarks/${this.config.id}/**'
  pull_request:
    paths:
      - 'src/modules/${this.config.id}/**'
      - 'tests/**/${this.config.id}/**'
  workflow_dispatch:

jobs:
  test:
    uses: ./.github/workflows/enhanced-5pass-pipeline.yml
    with:
      module: ${this.config.id}
      pass: all-passes
    secrets: inherit
`;

    const workflowPath = path.join(
      this.projectRoot,
      `.github/workflows/module-${this.config.id.toLowerCase()}.yml`
    );
    fs.writeFileSync(workflowPath, workflow);
    console.log(`📝 Generated: ${workflowPath}`);
  }

  private async updatePackageJson(): Promise<void> {
    const packageJsonPath = path.join(this.projectRoot, 'package.json');
    const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));

    // Add module-specific scripts
    const scripts = {
      [`module:${this.config.id.toLowerCase()}:test`]: `jest tests/unit/${this.config.id}`,
      [`module:${this.config.id.toLowerCase()}:bench`]: `ts-node benchmarks/${this.config.id}/*.bench.ts`,
      [`module:${this.config.id.toLowerCase()}:build`]: `tsc -p src/modules/${this.config.id}/tsconfig.json`,
      [`module:${this.config.id.toLowerCase()}:design`]: `npm run validate:design -- --module=${this.config.id}`,
    };

    packageJson.scripts = { ...packageJson.scripts, ...scripts };
    fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2));
    console.log(`📝 Updated: package.json with ${this.config.id} scripts`);
  }

  private async initializeGitBranch(): Promise<void> {
    try {
      execSync(`git checkout -b module/${this.config.id.toLowerCase()}`, {
        cwd: this.projectRoot,
      });
      console.log(`🌿 Created git branch: module/${this.config.id.toLowerCase()}`);
    } catch (error) {
      console.log(`⚠️  Could not create git branch (may already exist)`);
    }
  }
}

// CLI Interface
async function main() {
  const args = process.argv.slice(2);

  if (args.length < 3) {
    console.error('Usage: generate-module.ts <MODULE_ID> <MODULE_NAME> <DESCRIPTION> [DEPENDENCIES]');
    console.error('Example: generate-module.ts M002 LocalStorage "Local storage system" M001');
    process.exit(1);
  }

  const config: ModuleConfig = {
    id: args[0],
    name: args[1],
    description: args[2],
    dependencies: args.slice(3),
  };

  // Module-specific metrics
  const moduleMetrics: Record<string, Partial<ModuleConfig>> = {
    M002: {
      primaryMetric: 'queries_per_second',
      baselineValue: 1000,
      targetValue: 72000,
      metricUnit: 'queries/sec',
    },
    M003: {
      primaryMetric: 'documents_per_minute',
      baselineValue: 10000,
      targetValue: 248000,
      metricUnit: 'docs/min',
    },
    // Add more module-specific metrics
  };

  const generator = new ModuleGenerator({
    ...config,
    ...moduleMetrics[config.id],
  });

  await generator.generate();
}

// Run if called directly
if (require.main === module) {
  main().catch(console.error);
}

export { ModuleGenerator, ModuleConfig };
