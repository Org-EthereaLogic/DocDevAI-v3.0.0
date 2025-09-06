/**
 * Logger RED Phase Tests
 * These tests are written FIRST and will FAIL initially
 * Following TDD methodology: RED → GREEN → REFACTOR
 */

import { Logger } from '../../../src/cli/core/logging/Logger';
import { LogLevel, LogContext, LogTransport, LogEntry } from '../../../src/cli/types/core';
import { ConsoleTransport, FileTransport } from '../../../src/cli/core/logging/types';
import * as fs from 'fs';
import * as path from 'path';

describe('Logger - RED Phase (Failing Tests)', () => {
  let logger: Logger;
  let consoleLogSpy: jest.SpyInstance;
  let consoleErrorSpy: jest.SpyInstance;
  let consoleWarnSpy: jest.SpyInstance;

  beforeEach(() => {
    // This will fail - Logger doesn't exist yet
    logger = new Logger();
    
    // Spy on console methods
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
  });

  afterEach(() => {
    // Restore console methods
    consoleLogSpy.mockRestore();
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    
    // Clean up any log files
    const testLogFile = path.join(process.cwd(), 'test.log');
    if (fs.existsSync(testLogFile)) {
      fs.unlinkSync(testLogFile);
    }
  });

  describe('Basic Logging', () => {
    it('should log debug messages', () => {
      // Act: Log debug message
      logger.debug('Debug message');

      // Assert: Message logged at debug level
      expect(consoleLogSpy).toHaveBeenCalled();
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall).toContain('debug');
      expect(logCall).toContain('Debug message');
    });

    it('should log info messages', () => {
      // Act: Log info message
      logger.info('Info message');

      // Assert: Message logged at info level
      expect(consoleLogSpy).toHaveBeenCalled();
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall).toContain('info');
      expect(logCall).toContain('Info message');
    });

    it('should log warning messages', () => {
      // Act: Log warning message
      logger.warn('Warning message');

      // Assert: Message logged at warn level
      expect(consoleWarnSpy).toHaveBeenCalled();
      const logCall = consoleWarnSpy.mock.calls[0][0];
      expect(logCall).toContain('warn');
      expect(logCall).toContain('Warning message');
    });

    it('should log error messages', () => {
      // Act: Log error message
      const error = new Error('Test error');
      logger.error('Error occurred', error);

      // Assert: Message and error logged
      expect(consoleErrorSpy).toHaveBeenCalled();
      const logCall = consoleErrorSpy.mock.calls[0][0];
      expect(logCall).toContain('error');
      expect(logCall).toContain('Error occurred');
      expect(logCall).toContain('Test error');
    });

    it('should include timestamp in log entries', () => {
      // Act: Log message
      logger.info('Timestamp test');

      // Assert: Timestamp included
      const logCall = consoleLogSpy.mock.calls[0][0];
      // Check for ISO date format
      expect(logCall).toMatch(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
    });
  });

  describe('Log Levels', () => {
    it('should respect log level settings', () => {
      // Arrange: Set log level to warn
      logger.setLevel(LogLevel.WARN);

      // Act: Log at different levels
      logger.debug('Debug - should not appear');
      logger.info('Info - should not appear');
      logger.warn('Warning - should appear');
      logger.error('Error - should appear');

      // Assert: Only warn and error logged
      expect(consoleLogSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).toHaveBeenCalledTimes(1);
      expect(consoleErrorSpy).toHaveBeenCalledTimes(1);
    });

    it('should get current log level', () => {
      // Arrange: Set log level
      logger.setLevel(LogLevel.DEBUG);

      // Act: Get log level
      const level = logger.getLevel();

      // Assert: Correct level returned
      expect(level).toBe(LogLevel.DEBUG);
    });

    it('should handle silent log level', () => {
      // Arrange: Set to silent
      logger.setLevel(LogLevel.SILENT);

      // Act: Try to log at all levels
      logger.debug('Debug');
      logger.info('Info');
      logger.warn('Warning');
      logger.error('Error');

      // Assert: Nothing logged
      expect(consoleLogSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).not.toHaveBeenCalled();
      expect(consoleErrorSpy).not.toHaveBeenCalled();
    });

    it('should validate log level hierarchy', () => {
      // Test level hierarchy: DEBUG < INFO < WARN < ERROR < SILENT
      const levels = [
        { level: LogLevel.DEBUG, shouldLog: [true, true, true, true] },
        { level: LogLevel.INFO, shouldLog: [false, true, true, true] },
        { level: LogLevel.WARN, shouldLog: [false, false, true, true] },
        { level: LogLevel.ERROR, shouldLog: [false, false, false, true] },
        { level: LogLevel.SILENT, shouldLog: [false, false, false, false] }
      ];

      levels.forEach(({ level, shouldLog }) => {
        // Reset spies
        consoleLogSpy.mockClear();
        consoleWarnSpy.mockClear();
        consoleErrorSpy.mockClear();

        // Set level and log
        logger.setLevel(level);
        logger.debug('Debug');
        logger.info('Info');
        logger.warn('Warn');
        logger.error('Error');

        // Check expectations
        const debugCalls = consoleLogSpy.mock.calls.filter(c => c[0].includes('debug')).length;
        const infoCalls = consoleLogSpy.mock.calls.filter(c => c[0].includes('info')).length;
        const warnCalls = consoleWarnSpy.mock.calls.length;
        const errorCalls = consoleErrorSpy.mock.calls.length;

        expect(debugCalls > 0).toBe(shouldLog[0]);
        expect(infoCalls > 0).toBe(shouldLog[1]);
        expect(warnCalls > 0).toBe(shouldLog[2]);
        expect(errorCalls > 0).toBe(shouldLog[3]);
      });
    });
  });

  describe('Log Context', () => {
    it('should include context in log entries', () => {
      // Act: Log with context
      logger.info('Operation completed', {
        module: 'config',
        operation: 'load',
        metadata: { file: 'config.yml' }
      });

      // Assert: Context included
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall).toContain('module');
      expect(logCall).toContain('config');
      expect(logCall).toContain('operation');
      expect(logCall).toContain('load');
    });

    it('should include correlation ID in context', () => {
      // Arrange: Set correlation ID
      const correlationId = 'abc-123-def';
      logger.setCorrelationId(correlationId);

      // Act: Log message
      logger.info('Request processed');

      // Assert: Correlation ID included
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall).toContain(correlationId);
    });

    it('should preserve correlation ID across log calls', () => {
      // Arrange: Set correlation ID
      const correlationId = 'xyz-789';
      logger.setCorrelationId(correlationId);

      // Act: Log multiple messages
      logger.info('First message');
      logger.info('Second message');
      logger.warn('Third message');

      // Assert: All have same correlation ID
      [consoleLogSpy, consoleWarnSpy].forEach(spy => {
        spy.mock.calls.forEach(call => {
          if (call[0]) {
            expect(call[0]).toContain(correlationId);
          }
        });
      });
    });

    it('should handle error context properly', () => {
      // Arrange: Create error with cause
      const rootCause = new Error('Root cause');
      const error = Object.assign(new Error('Main error'), {
        cause: rootCause,
        code: 'ERR_TEST'
      });

      // Act: Log error with context
      logger.error('Operation failed', error, {
        module: 'test',
        operation: 'process'
      });

      // Assert: Error details and context included
      const logCall = consoleErrorSpy.mock.calls[0][0];
      expect(logCall).toContain('Main error');
      expect(logCall).toContain('ERR_TEST');
      expect(logCall).toContain('module');
      expect(logCall).toContain('test');
    });
  });

  describe('Log Transports', () => {
    it('should support console transport', () => {
      // Arrange: Create console transport
      const consoleTransport: ConsoleTransport = {
        name: 'console',
        enableColors: true,
        format: 'text',
        write: jest.fn()
      };

      // Act: Add transport and log
      logger.addTransport(consoleTransport);
      logger.info('Console transport test');

      // Assert: Transport called
      expect(consoleTransport.write).toHaveBeenCalled();
    });

    it('should support file transport', async () => {
      // Arrange: Create file transport
      const logFile = path.join(process.cwd(), 'test.log');
      const fileTransport: FileTransport = {
        name: 'file',
        filepath: logFile,
        write: jest.fn((entry: LogEntry) => {
          // Simulate file writing
          fs.appendFileSync(logFile, JSON.stringify(entry) + '\n');
        })
      };

      // Act: Add transport and log
      logger.addTransport(fileTransport);
      logger.info('File transport test');
      await logger.flush();

      // Assert: File created and written
      expect(fileTransport.write).toHaveBeenCalled();
      expect(fs.existsSync(logFile)).toBe(true);
      const content = fs.readFileSync(logFile, 'utf8');
      expect(content).toContain('File transport test');
    });

    it('should support multiple transports', () => {
      // Arrange: Create multiple transports
      const transport1 = { name: 'transport1', write: jest.fn() };
      const transport2 = { name: 'transport2', write: jest.fn() };

      // Act: Add transports and log
      logger.addTransport(transport1);
      logger.addTransport(transport2);
      logger.info('Multiple transports');

      // Assert: Both transports called
      expect(transport1.write).toHaveBeenCalled();
      expect(transport2.write).toHaveBeenCalled();
    });

    it('should remove transports by name', () => {
      // Arrange: Add transport
      const transport = { name: 'removable', write: jest.fn() };
      logger.addTransport(transport);

      // Act: Remove transport and log
      logger.removeTransport('removable');
      logger.info('After removal');

      // Assert: Transport not called
      expect(transport.write).not.toHaveBeenCalled();
    });
  });

  describe('Child Loggers', () => {
    it('should create child loggers with additional context', () => {
      // Act: Create child logger
      const childLogger = logger.child({
        module: 'child-module',
        service: 'test-service'
      });

      // Log with child
      childLogger.info('Child message');

      // Assert: Parent context included
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall).toContain('child-module');
      expect(logCall).toContain('test-service');
    });

    it('should inherit parent log level', () => {
      // Arrange: Set parent level
      logger.setLevel(LogLevel.WARN);

      // Act: Create child and try to log
      const childLogger = logger.child({ module: 'child' });
      childLogger.debug('Debug from child');
      childLogger.info('Info from child');
      childLogger.warn('Warn from child');

      // Assert: Only warn logged (inherited level)
      expect(consoleLogSpy).not.toHaveBeenCalled();
      expect(consoleWarnSpy).toHaveBeenCalledTimes(1);
    });

    it('should merge child and parent context', () => {
      // Arrange: Set parent correlation ID
      logger.setCorrelationId('parent-correlation');

      // Act: Create child with additional context
      const childLogger = logger.child({
        module: 'child',
        operation: 'test'
      });

      childLogger.info('Merged context test');

      // Assert: Both parent and child context present
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall).toContain('parent-correlation');
      expect(logCall).toContain('child');
      expect(logCall).toContain('test');
    });

    it('should allow nested child loggers', () => {
      // Act: Create nested children
      const child1 = logger.child({ level1: 'value1' });
      const child2 = child1.child({ level2: 'value2' });
      const child3 = child2.child({ level3: 'value3' });

      child3.info('Nested child message');

      // Assert: All context levels present
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall).toContain('value1');
      expect(logCall).toContain('value2');
      expect(logCall).toContain('value3');
    });
  });

  describe('Log Formatting', () => {
    it('should format logs as JSON when configured', () => {
      // Arrange: Create logger with JSON format
      logger = new Logger({ format: 'json' });

      // Act: Log message
      logger.info('JSON format test', { data: 'value' });

      // Assert: Output is valid JSON
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(() => JSON.parse(logCall)).not.toThrow();
      const parsed = JSON.parse(logCall);
      expect(parsed.message).toBe('JSON format test');
      expect(parsed.level).toBe('info');
    });

    it('should format logs as text when configured', () => {
      // Arrange: Create logger with text format
      logger = new Logger({ format: 'text' });

      // Act: Log message
      logger.info('Text format test');

      // Assert: Output is human-readable text
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall).toContain('[INFO]');
      expect(logCall).toContain('Text format test');
      expect(() => JSON.parse(logCall)).toThrow(); // Not JSON
    });

    it('should support colored output for console', () => {
      // Arrange: Create logger with colors enabled
      logger = new Logger({ enableColors: true });

      // Act: Log at different levels
      logger.debug('Debug');
      logger.info('Info');
      logger.warn('Warn');
      logger.error('Error');

      // Assert: ANSI color codes present
      const calls = [...consoleLogSpy.mock.calls, ...consoleWarnSpy.mock.calls, ...consoleErrorSpy.mock.calls];
      calls.forEach(call => {
        if (call[0]) {
          // Check for ANSI escape codes
          expect(call[0]).toMatch(/\x1b\[\d+m/);
        }
      });
    });

    it('should truncate very long messages', () => {
      // Arrange: Create very long message
      const longMessage = 'A'.repeat(10000);

      // Act: Log long message
      logger.info(longMessage);

      // Assert: Message truncated
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall.length).toBeLessThan(5000);
      expect(logCall).toContain('...[truncated]');
    });
  });

  describe('Log Buffering', () => {
    it('should buffer logs when configured', async () => {
      // Arrange: Create logger with buffering
      logger = new Logger({ maxBufferSize: 10 });
      const transport = { name: 'test', write: jest.fn() };
      logger.addTransport(transport);

      // Act: Log multiple messages quickly
      for (let i = 0; i < 5; i++) {
        logger.info(`Message ${i}`);
      }

      // Assert: Not all written immediately
      expect(transport.write.mock.calls.length).toBeLessThanOrEqual(5);

      // Flush buffer
      await logger.flush();
      expect(transport.write.mock.calls.length).toBe(5);
    });

    it('should flush buffer when full', () => {
      // Arrange: Small buffer size
      logger = new Logger({ maxBufferSize: 3 });
      const transport = { name: 'test', write: jest.fn() };
      logger.addTransport(transport);

      // Act: Log more than buffer size
      for (let i = 0; i < 5; i++) {
        logger.info(`Message ${i}`);
      }

      // Assert: Buffer flushed automatically
      expect(transport.write.mock.calls.length).toBeGreaterThanOrEqual(3);
    });

    it('should flush on process exit', async () => {
      // Arrange: Logger with buffering
      logger = new Logger({ maxBufferSize: 100 });
      const transport = { name: 'test', write: jest.fn() };
      logger.addTransport(transport);

      // Act: Log and trigger flush
      logger.info('Exit test');
      await logger.flush();

      // Assert: All messages flushed
      expect(transport.write).toHaveBeenCalled();
    });
  });

  describe('Performance', () => {
    it('should handle high-volume logging efficiently', () => {
      // Arrange: Disable console for performance test
      logger.setLevel(LogLevel.SILENT);

      // Act: Log many messages
      const startTime = performance.now();
      for (let i = 0; i < 1000; i++) {
        logger.info(`Message ${i}`, { index: i });
      }
      const endTime = performance.now();
      const duration = endTime - startTime;

      // Assert: Fast enough (< 100ms for 1000 messages)
      expect(duration).toBeLessThan(100);
    });

    it('should not block on synchronous logging', () => {
      // Act: Time a single log operation
      const startTime = performance.now();
      logger.info('Performance test');
      const endTime = performance.now();
      const duration = endTime - startTime;

      // Assert: Very fast (< 1ms)
      expect(duration).toBeLessThan(1);
    });
  });

  describe('Error Handling', () => {
    it('should handle transport write failures gracefully', () => {
      // Arrange: Transport that throws
      const failingTransport = {
        name: 'failing',
        write: jest.fn(() => {
          throw new Error('Transport failed');
        })
      };

      logger.addTransport(failingTransport);

      // Act & Assert: Logging doesn't throw
      expect(() => {
        logger.info('Test message');
      }).not.toThrow();
    });

    it('should handle circular references in context', () => {
      // Arrange: Circular reference
      const circular: any = { name: 'test' };
      circular.self = circular;

      // Act & Assert: Logging doesn't throw
      expect(() => {
        logger.info('Circular test', { data: circular });
      }).not.toThrow();

      // Check output contains circular indicator
      const logCall = consoleLogSpy.mock.calls[0][0];
      expect(logCall).toContain('[Circular]');
    });

    it('should handle undefined and null values', () => {
      // Act & Assert: Various edge cases
      expect(() => {
        logger.info(undefined as any);
        logger.info(null as any);
        logger.info('', undefined);
        logger.info('', null, null);
      }).not.toThrow();
    });
  });
});