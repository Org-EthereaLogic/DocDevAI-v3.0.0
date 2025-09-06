/**
 * ConfigLoader RED Phase Tests
 * These tests are written FIRST and will FAIL initially
 * Following TDD methodology: RED → GREEN → REFACTOR
 */

import { ConfigLoader } from '../../../src/cli/core/config/ConfigLoader';
import { DevDocAIConfig, MemoryMode, LogLevel } from '../../../src/cli/types/core';
import * as fs from 'fs';
import * as path from 'path';
import * as yaml from 'js-yaml';

describe('ConfigLoader - RED Phase (Failing Tests)', () => {
  let loader: ConfigLoader;
  const testConfigPath = path.join(process.cwd(), 'test.devdocai.yml');
  const defaultConfigPath = path.join(process.cwd(), '.devdocai.yml');

  beforeEach(() => {
    // This will fail - ConfigLoader doesn't exist yet
    loader = new ConfigLoader();
    
    // Clean up any existing test files
    [testConfigPath, defaultConfigPath].forEach(file => {
      if (fs.existsSync(file)) {
        fs.unlinkSync(file);
      }
    });
  });

  afterEach(() => {
    // Clean up test files
    [testConfigPath, defaultConfigPath].forEach(file => {
      if (fs.existsSync(file)) {
        fs.unlinkSync(file);
      }
    });
    
    // Stop watching if enabled
    if (loader) {
      loader.stopWatching();
    }
  });

  describe('Configuration Loading', () => {
    it('should load .devdocai.yml with proper validation', async () => {
      // Arrange: Create a valid configuration file
      const validConfig = {
        memory: {
          mode: 'standard',
          maxWorkers: 4,
          cacheSize: 1024,
          enableOptimizations: true
        },
        logging: {
          level: 'info',
          format: 'json',
          enableConsole: true
        },
        output: {
          format: 'json',
          pretty: true,
          color: true
        },
        modules: {
          enabled: ['config', 'generator', 'analyzer'],
          settings: {}
        },
        version: '3.0.0',
        environment: 'development'
      };
      
      fs.writeFileSync(defaultConfigPath, yaml.dump(validConfig));

      // Act: Load the configuration
      const config = await loader.load();

      // Assert: Configuration loaded correctly
      expect(config).toBeDefined();
      expect(config.memory.mode).toBe(MemoryMode.STANDARD);
      expect(config.logging.level).toBe(LogLevel.INFO);
      expect(config.version).toBe('3.0.0');
      expect(config.modules.enabled).toContain('config');
    });

    it('should load configuration from custom path', async () => {
      // Arrange: Create config at custom path
      const customConfig = {
        memory: { mode: 'enhanced' },
        logging: { level: 'debug', format: 'text' },
        output: { format: 'yaml' },
        modules: { enabled: [], settings: {} },
        version: '3.0.0',
        environment: 'test'
      };
      
      fs.writeFileSync(testConfigPath, yaml.dump(customConfig));

      // Act: Load from custom path
      const config = await loader.load(testConfigPath);

      // Assert: Custom config loaded
      expect(config.memory.mode).toBe(MemoryMode.ENHANCED);
      expect(config.environment).toBe('test');
    });

    it('should handle missing configuration gracefully', async () => {
      // Act: Load non-existent configuration
      const config = await loader.load('nonexistent.yml');

      // Assert: Returns default configuration
      const defaultConfig = loader.getDefault();
      expect(config).toEqual(defaultConfig);
      expect(config.memory.mode).toBe(MemoryMode.AUTO);
    });

    it('should merge environment variables with configuration', async () => {
      // Arrange: Set environment variables
      process.env.DEVDOCAI_MEMORY_MODE = 'performance';
      process.env.DEVDOCAI_LOG_LEVEL = 'debug';

      // Act: Load configuration
      const config = await loader.load();

      // Assert: Environment variables override defaults
      expect(config.memory.mode).toBe(MemoryMode.PERFORMANCE);
      expect(config.logging.level).toBe(LogLevel.DEBUG);

      // Cleanup
      delete process.env.DEVDOCAI_MEMORY_MODE;
      delete process.env.DEVDOCAI_LOG_LEVEL;
    });

    it('should meet performance target of <10ms loading time', async () => {
      // Arrange: Create configuration file
      const config = loader.getDefault();
      fs.writeFileSync(defaultConfigPath, yaml.dump(config));

      // Act: Measure loading time
      const startTime = performance.now();
      await loader.load();
      const endTime = performance.now();
      const loadTime = endTime - startTime;

      // Assert: Loading time under 10ms
      expect(loadTime).toBeLessThan(10);
    });
  });

  describe('Configuration Validation', () => {
    it('should validate configuration schema', () => {
      // Arrange: Invalid configuration
      const invalidConfig = {
        memory: {
          mode: 'invalid-mode' // Invalid memory mode
        }
      };

      // Act: Validate configuration
      const result = loader.validate(invalidConfig);

      // Assert: Validation fails with specific error
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Invalid memory mode: invalid-mode');
    });

    it('should validate memory mode values', () => {
      // Arrange: Test each valid mode
      const validModes = ['baseline', 'standard', 'enhanced', 'performance', 'auto'];
      
      validModes.forEach(mode => {
        const config = {
          memory: { mode },
          logging: { level: 'info', format: 'json' },
          output: { format: 'json' },
          modules: { enabled: [], settings: {} },
          version: '3.0.0',
          environment: 'development'
        };

        // Act & Assert: All valid modes pass
        const result = loader.validate(config);
        expect(result.valid).toBe(true);
      });
    });

    it('should validate log levels', () => {
      // Arrange: Invalid log level
      const invalidConfig = {
        memory: { mode: 'standard' },
        logging: { level: 'invalid-level', format: 'json' },
        output: { format: 'json' },
        modules: { enabled: [], settings: {} },
        version: '3.0.0',
        environment: 'development'
      };

      // Act: Validate
      const result = loader.validate(invalidConfig);

      // Assert: Validation fails
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Invalid log level: invalid-level');
    });

    it('should provide warnings for deprecated options', () => {
      // Arrange: Config with deprecated options
      const configWithDeprecated = {
        memory: { mode: 'standard', legacyOption: true }, // deprecated option
        logging: { level: 'info', format: 'json' },
        output: { format: 'json' },
        modules: { enabled: [], settings: {} },
        version: '3.0.0',
        environment: 'development'
      };

      // Act: Validate
      const result = loader.validate(configWithDeprecated);

      // Assert: Valid but with warnings
      expect(result.valid).toBe(true);
      expect(result.warnings).toContain('Deprecated option: memory.legacyOption');
    });
  });

  describe('Configuration Watching', () => {
    it('should watch configuration file for changes', (done) => {
      // Arrange: Create initial configuration
      const initialConfig = loader.getDefault();
      fs.writeFileSync(defaultConfigPath, yaml.dump(initialConfig));

      // Act: Set up watcher
      loader.watch((newConfig: DevDocAIConfig) => {
        // Assert: Callback triggered with new configuration
        expect(newConfig.memory.mode).toBe(MemoryMode.PERFORMANCE);
        done();
      });

      // Trigger change after a delay
      setTimeout(() => {
        const updatedConfig = { ...initialConfig, memory: { mode: 'performance' } };
        fs.writeFileSync(defaultConfigPath, yaml.dump(updatedConfig));
      }, 100);
    });

    it('should debounce rapid configuration changes', (done) => {
      // Arrange: Create initial configuration
      const initialConfig = loader.getDefault();
      fs.writeFileSync(defaultConfigPath, yaml.dump(initialConfig));

      let callbackCount = 0;

      // Act: Set up watcher
      loader.watch(() => {
        callbackCount++;
      });

      // Make rapid changes
      for (let i = 0; i < 5; i++) {
        setTimeout(() => {
          const config = { ...initialConfig, version: `3.0.${i}` };
          fs.writeFileSync(defaultConfigPath, yaml.dump(config));
        }, i * 10);
      }

      // Assert: Callback called only once due to debouncing
      setTimeout(() => {
        expect(callbackCount).toBe(1);
        done();
      }, 500);
    });

    it('should stop watching when requested', () => {
      // Arrange: Set up watcher
      const callback = jest.fn();
      loader.watch(callback);

      // Act: Stop watching
      loader.stopWatching();

      // Modify file after stopping
      const config = loader.getDefault();
      fs.writeFileSync(defaultConfigPath, yaml.dump(config));

      // Assert: Callback not called after stopping
      setTimeout(() => {
        expect(callback).not.toHaveBeenCalled();
      }, 200);
    });
  });

  describe('Configuration Caching', () => {
    it('should cache loaded configurations', async () => {
      // Arrange: Create configuration file
      const config = loader.getDefault();
      fs.writeFileSync(defaultConfigPath, yaml.dump(config));

      // Act: Load configuration twice
      const config1 = await loader.load();
      const config2 = await loader.load();

      // Assert: Same instance returned (cached)
      expect(config1).toBe(config2);
    });

    it('should invalidate cache when file changes', async () => {
      // Arrange: Create initial configuration
      const initialConfig = loader.getDefault();
      fs.writeFileSync(defaultConfigPath, yaml.dump(initialConfig));

      // Act: Load, modify, load again
      const config1 = await loader.load();
      
      // Modify file
      const updatedConfig = { ...initialConfig, version: '3.0.1' };
      fs.writeFileSync(defaultConfigPath, yaml.dump(updatedConfig));
      
      const config2 = await loader.load();

      // Assert: Different instances (cache invalidated)
      expect(config1).not.toBe(config2);
      expect(config2.version).toBe('3.0.1');
    });

    it('should clear cache on demand', async () => {
      // Arrange: Load configuration
      const config = loader.getDefault();
      fs.writeFileSync(defaultConfigPath, yaml.dump(config));
      const config1 = await loader.load();

      // Act: Clear cache and load again
      loader.clearCache();
      const config2 = await loader.load();

      // Assert: Different instances after cache clear
      expect(config1).not.toBe(config2);
    });
  });

  describe('Default Configuration', () => {
    it('should provide sensible defaults', () => {
      // Act: Get default configuration
      const defaultConfig = loader.getDefault();

      // Assert: Defaults are sensible
      expect(defaultConfig.memory.mode).toBe(MemoryMode.AUTO);
      expect(defaultConfig.logging.level).toBe(LogLevel.INFO);
      expect(defaultConfig.logging.format).toBe('json');
      expect(defaultConfig.output.format).toBe('json');
      expect(defaultConfig.environment).toBe('development');
      expect(defaultConfig.version).toBe('3.0.0');
    });

    it('should return immutable default configuration', () => {
      // Act: Get default configuration twice
      const default1 = loader.getDefault();
      const default2 = loader.getDefault();

      // Attempt to modify
      default1.version = '2.0.0';

      // Assert: Second instance unchanged
      expect(default2.version).toBe('3.0.0');
    });
  });

  describe('Error Handling', () => {
    it('should handle malformed YAML gracefully', async () => {
      // Arrange: Write invalid YAML
      fs.writeFileSync(defaultConfigPath, 'invalid: yaml: content:');

      // Act: Attempt to load
      const config = await loader.load();

      // Assert: Returns default configuration
      expect(config).toEqual(loader.getDefault());
    });

    it('should handle file read permissions errors', async () => {
      // Arrange: Create file with no read permissions
      fs.writeFileSync(defaultConfigPath, yaml.dump(loader.getDefault()));
      fs.chmodSync(defaultConfigPath, 0o000);

      // Act: Attempt to load
      const config = await loader.load();

      // Assert: Returns default configuration
      expect(config).toEqual(loader.getDefault());

      // Cleanup: Restore permissions
      fs.chmodSync(defaultConfigPath, 0o644);
    });

    it('should handle circular references in configuration', () => {
      // Arrange: Configuration with circular reference
      const circularConfig: any = {
        memory: { mode: 'standard' },
        logging: { level: 'info', format: 'json' },
        output: { format: 'json' },
        modules: { enabled: [], settings: {} },
        version: '3.0.0',
        environment: 'development'
      };
      circularConfig.circular = circularConfig;

      // Act: Validate circular configuration
      const result = loader.validate(circularConfig);

      // Assert: Validation handles circular reference
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Circular reference detected');
    });
  });

  describe('Integration with Environment', () => {
    it('should respect NODE_ENV for environment setting', async () => {
      // Arrange: Set NODE_ENV
      process.env.NODE_ENV = 'production';

      // Act: Load configuration
      const config = await loader.load();

      // Assert: Environment set from NODE_ENV
      expect(config.environment).toBe('production');

      // Cleanup
      delete process.env.NODE_ENV;
    });

    it('should handle home directory expansion in paths', async () => {
      // Arrange: Configuration with ~ in path
      const configWithHome = {
        memory: { mode: 'standard' },
        logging: { 
          level: 'info', 
          format: 'json',
          outputPath: '~/logs/devdocai.log'
        },
        output: { format: 'json' },
        modules: { enabled: [], settings: {} },
        version: '3.0.0',
        environment: 'development'
      };
      
      fs.writeFileSync(defaultConfigPath, yaml.dump(configWithHome));

      // Act: Load configuration
      const config = await loader.load();

      // Assert: Path expanded
      expect(config.logging.outputPath).not.toContain('~');
      expect(config.logging.outputPath).toContain(process.env.HOME || '');
    });
  });
});