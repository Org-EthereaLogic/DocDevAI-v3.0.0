/**
 * ErrorHandler RED Phase Tests
 * These tests are written FIRST and will FAIL initially
 * Following TDD methodology: RED → GREEN → REFACTOR
 */

import { ErrorHandler } from '../../../src/cli/core/error/ErrorHandler';
import { FormattedError, ErrorCategory } from '../../../src/cli/types/core';
import { DevDocAIError } from '../../../src/cli/core/error/types';
import { ERROR_CODES, CONFIG_ERRORS, SYSTEM_ERRORS } from '../../../src/cli/core/error/codes';

describe('ErrorHandler - RED Phase (Failing Tests)', () => {
  let errorHandler: ErrorHandler;

  beforeEach(() => {
    // This will fail - ErrorHandler doesn't exist yet
    errorHandler = new ErrorHandler();
  });

  describe('Error Handling', () => {
    it('should handle standard errors with proper formatting', () => {
      // Arrange: Create a standard error
      const error = new Error('Something went wrong');

      // Act: Handle the error
      const formatted = errorHandler.handle(error);

      // Assert: Error is properly formatted
      expect(formatted).toBeDefined();
      expect(formatted.message).toBe('Something went wrong');
      expect(formatted.code).toBeDefined();
      expect(formatted.category).toBeDefined();
      expect(formatted.suggestion).toBeDefined();
      expect(formatted.recoverable).toBeDefined();
      expect(formatted.timestamp).toBeDefined();
    });

    it('should handle DevDocAI errors with specific codes', () => {
      // Arrange: Create a DevDocAI error
      const error: DevDocAIError = Object.assign(new Error('Config not found'), {
        code: CONFIG_ERRORS.CONFIG_NOT_FOUND,
        category: ErrorCategory.CONFIGURATION,
        recoverable: true
      });

      // Act: Handle the error
      const formatted = errorHandler.handle(error);

      // Assert: Error contains specific code information
      expect(formatted.code).toBe(CONFIG_ERRORS.CONFIG_NOT_FOUND);
      expect(formatted.category).toBe(ErrorCategory.CONFIGURATION);
      expect(formatted.recoverable).toBe(true);
      expect(formatted.suggestion).toContain('Create a .devdocai.yml file');
    });

    it('should provide suggestions based on error codes', () => {
      // Arrange: Errors with different codes
      const configError: DevDocAIError = Object.assign(new Error('Config error'), {
        code: CONFIG_ERRORS.CONFIG_INVALID_FORMAT,
        category: ErrorCategory.CONFIGURATION,
        recoverable: false
      });

      const systemError: DevDocAIError = Object.assign(new Error('System error'), {
        code: SYSTEM_ERRORS.SYSTEM_MEMORY_ERROR,
        category: ErrorCategory.SYSTEM,
        recoverable: true
      });

      // Act: Handle errors
      const configFormatted = errorHandler.handle(configError);
      const systemFormatted = errorHandler.handle(systemError);

      // Assert: Appropriate suggestions provided
      expect(configFormatted.suggestion).toContain('Check YAML syntax');
      expect(systemFormatted.suggestion).toContain('baseline memory mode');
    });

    it('should handle errors with context information', () => {
      // Arrange: Error with context
      const error: DevDocAIError = Object.assign(new Error('Processing failed'), {
        code: '2001',
        category: ErrorCategory.PROCESSING,
        recoverable: true,
        context: {
          operation: 'generateDocument',
          module: 'generator',
          input: { template: 'api-docs', file: 'test.ts' }
        }
      });

      // Act: Handle error
      const formatted = errorHandler.handle(error);

      // Assert: Context preserved
      expect(formatted.context).toBeDefined();
      expect(formatted.context?.operation).toBe('generateDocument');
      expect(formatted.context?.module).toBe('generator');
    });

    it('should handle nested errors with cause chain', () => {
      // Arrange: Nested error
      const rootCause = new Error('Network timeout');
      const middleError = Object.assign(new Error('API call failed'), {
        cause: rootCause
      });
      const topError: DevDocAIError = Object.assign(new Error('Document generation failed'), {
        code: '2001',
        category: ErrorCategory.PROCESSING,
        recoverable: true,
        cause: middleError
      });

      // Act: Handle nested error
      const formatted = errorHandler.handle(topError);

      // Assert: Error chain preserved
      expect(formatted.message).toContain('Document generation failed');
      expect(formatted.context?.cause).toBeDefined();
    });

    it('should meet performance target of <5ms error response', () => {
      // Arrange: Create an error
      const error = new Error('Performance test error');

      // Act: Measure handling time
      const startTime = performance.now();
      errorHandler.handle(error);
      const endTime = performance.now();
      const responseTime = endTime - startTime;

      // Assert: Response time under 5ms
      expect(responseTime).toBeLessThan(5);
    });
  });

  describe('Error Throwing', () => {
    it('should throw errors with specific codes', () => {
      // Act & Assert: Throw with code
      expect(() => {
        errorHandler.throwWithCode(CONFIG_ERRORS.CONFIG_NOT_FOUND, 'Configuration file missing');
      }).toThrow();

      try {
        errorHandler.throwWithCode(CONFIG_ERRORS.CONFIG_NOT_FOUND, 'Configuration file missing');
      } catch (error: any) {
        expect(error.code).toBe(CONFIG_ERRORS.CONFIG_NOT_FOUND);
        expect(error.message).toBe('Configuration file missing');
        expect(error.category).toBe(ErrorCategory.CONFIGURATION);
      }
    });

    it('should validate error codes are in valid range', () => {
      // Act & Assert: Invalid code throws
      expect(() => {
        errorHandler.throwWithCode('9999', 'Invalid code');
      }).toThrow('Invalid error code: 9999');

      expect(() => {
        errorHandler.throwWithCode('abc', 'Non-numeric code');
      }).toThrow('Invalid error code: abc');
    });

    it('should never return from throwWithCode', () => {
      // TypeScript compile-time check for 'never' return type
      const testNever = (): never => {
        return errorHandler.throwWithCode('5001', 'Test');
      };

      // Runtime check that it actually throws
      expect(testNever).toThrow();
    });
  });

  describe('Error Recovery', () => {
    it('should identify recoverable errors', () => {
      // Arrange: Different error types
      const recoverableError: DevDocAIError = Object.assign(new Error('Rate limit'), {
        code: '3003',
        category: ErrorCategory.API,
        recoverable: true
      });

      const nonRecoverableError: DevDocAIError = Object.assign(new Error('Invalid key'), {
        code: '3007',
        category: ErrorCategory.API,
        recoverable: false
      });

      // Act & Assert: Check recovery status
      expect(errorHandler.isRecoverable(recoverableError)).toBe(true);
      expect(errorHandler.isRecoverable(nonRecoverableError)).toBe(false);
    });

    it('should determine recovery based on error code if not specified', () => {
      // Arrange: Error without explicit recoverable flag
      const error: any = new Error('Test error');
      error.code = '3003'; // Rate limit - recoverable

      // Act: Check recovery
      const isRecoverable = errorHandler.isRecoverable(error);

      // Assert: Determined from code
      expect(isRecoverable).toBe(true);
    });

    it('should default to non-recoverable for unknown errors', () => {
      // Arrange: Standard error without code
      const error = new Error('Unknown error');

      // Act: Check recovery
      const isRecoverable = errorHandler.isRecoverable(error);

      // Assert: Defaults to non-recoverable
      expect(isRecoverable).toBe(false);
    });
  });

  describe('Error Suggestions', () => {
    it('should provide suggestions for known error codes', () => {
      // Act: Get suggestions for different error codes
      const configSuggestion = errorHandler.getSuggestion(CONFIG_ERRORS.CONFIG_NOT_FOUND);
      const apiSuggestion = errorHandler.getSuggestion('3003'); // Rate limit
      const systemSuggestion = errorHandler.getSuggestion(SYSTEM_ERRORS.SYSTEM_MEMORY_ERROR);

      // Assert: Appropriate suggestions
      expect(configSuggestion).toContain('.devdocai.yml');
      expect(apiSuggestion).toContain('Wait before retrying');
      expect(systemSuggestion).toContain('memory');
    });

    it('should provide generic suggestion for unknown error codes', () => {
      // Act: Get suggestion for unknown code
      const suggestion = errorHandler.getSuggestion('9999');

      // Assert: Generic suggestion
      expect(suggestion).toContain('Check logs');
    });

    it('should provide contextual suggestions based on error category', () => {
      // Act: Get suggestions for category ranges
      const configSuggestion = errorHandler.getSuggestion('1500'); // Config range
      const processSuggestion = errorHandler.getSuggestion('2500'); // Processing range
      const apiSuggestion = errorHandler.getSuggestion('3500'); // API range

      // Assert: Category-appropriate suggestions
      expect(configSuggestion).toBeDefined();
      expect(processSuggestion).toBeDefined();
      expect(apiSuggestion).toBeDefined();
    });
  });

  describe('Custom Error Handlers', () => {
    it('should register and use custom error handlers', () => {
      // Arrange: Register custom handler
      const customHandler = jest.fn((error: Error) => ({
        code: '1999',
        category: ErrorCategory.CONFIGURATION,
        message: 'Custom handled: ' + error.message,
        suggestion: 'Custom suggestion',
        recoverable: true,
        timestamp: new Date().toISOString()
      }));

      errorHandler.registerHandler('1999', customHandler);

      // Act: Handle error with custom code
      const error: any = new Error('Test error');
      error.code = '1999';
      const formatted = errorHandler.handle(error);

      // Assert: Custom handler was used
      expect(customHandler).toHaveBeenCalled();
      expect(formatted.message).toContain('Custom handled');
      expect(formatted.suggestion).toBe('Custom suggestion');
    });

    it('should support regex patterns for custom handlers', () => {
      // Arrange: Register handler with regex pattern
      const customHandler = jest.fn((error: Error) => ({
        code: (error as any).code,
        category: ErrorCategory.API,
        message: 'API Error: ' + error.message,
        suggestion: 'Check API configuration',
        recoverable: true,
        timestamp: new Date().toISOString()
      }));

      errorHandler.registerHandler(/^3\d{3}$/, customHandler); // All 3xxx codes

      // Act: Handle error matching pattern
      const error: any = new Error('API failed');
      error.code = '3456';
      const formatted = errorHandler.handle(error);

      // Assert: Pattern-matched handler used
      expect(customHandler).toHaveBeenCalled();
      expect(formatted.message).toContain('API Error');
    });

    it('should prioritize specific handlers over pattern handlers', () => {
      // Arrange: Register both specific and pattern handlers
      const specificHandler = jest.fn(() => ({
        code: '3001',
        category: ErrorCategory.API,
        message: 'Specific handler',
        suggestion: 'Specific suggestion',
        recoverable: true,
        timestamp: new Date().toISOString()
      }));

      const patternHandler = jest.fn(() => ({
        code: '3xxx',
        category: ErrorCategory.API,
        message: 'Pattern handler',
        suggestion: 'Pattern suggestion',
        recoverable: true,
        timestamp: new Date().toISOString()
      }));

      errorHandler.registerHandler('3001', specificHandler);
      errorHandler.registerHandler(/^3\d{3}$/, patternHandler);

      // Act: Handle error with specific code
      const error: any = new Error('Test');
      error.code = '3001';
      const formatted = errorHandler.handle(error);

      // Assert: Specific handler takes precedence
      expect(specificHandler).toHaveBeenCalled();
      expect(patternHandler).not.toHaveBeenCalled();
      expect(formatted.message).toBe('Specific handler');
    });
  });

  describe('Error Formatting', () => {
    it('should format errors for logging', () => {
      // Arrange: Create error with full context
      const error: DevDocAIError = Object.assign(new Error('Test error'), {
        code: '2001',
        category: ErrorCategory.PROCESSING,
        recoverable: true,
        context: {
          operation: 'test',
          module: 'test-module'
        }
      });

      // Act: Format for logging
      const formatted = errorHandler.formatForLogging(error);

      // Assert: Properly formatted string
      expect(formatted).toContain('[2001]');
      expect(formatted).toContain('PROCESSING');
      expect(formatted).toContain('Test error');
      expect(formatted).toContain('operation: test');
    });

    it('should include stack trace in formatted output', () => {
      // Arrange: Error with stack
      const error = new Error('Stack trace test');

      // Act: Format for logging
      const formatted = errorHandler.formatForLogging(error);

      // Assert: Stack included
      expect(formatted).toContain('Stack:');
      expect(formatted).toContain('at ');
    });

    it('should handle circular references in error context', () => {
      // Arrange: Error with circular reference
      const circularObj: any = { name: 'test' };
      circularObj.self = circularObj;

      const error: DevDocAIError = Object.assign(new Error('Circular test'), {
        code: '5999',
        category: ErrorCategory.SYSTEM,
        recoverable: false,
        context: {
          circular: circularObj
        }
      });

      // Act & Assert: Formatting doesn't throw
      expect(() => {
        errorHandler.formatForLogging(error);
      }).not.toThrow();

      const formatted = errorHandler.formatForLogging(error);
      expect(formatted).toContain('[Circular]');
    });

    it('should truncate very long error messages', () => {
      // Arrange: Error with very long message
      const longMessage = 'A'.repeat(10000);
      const error = new Error(longMessage);

      // Act: Format for logging
      const formatted = errorHandler.formatForLogging(error);

      // Assert: Message truncated
      expect(formatted.length).toBeLessThan(5000);
      expect(formatted).toContain('...[truncated]');
    });
  });

  describe('Error Categories', () => {
    it('should correctly categorize errors by code range', () => {
      // Arrange: Errors from different categories
      const errors = [
        { code: '1001', expectedCategory: ErrorCategory.CONFIGURATION },
        { code: '2005', expectedCategory: ErrorCategory.PROCESSING },
        { code: '3008', expectedCategory: ErrorCategory.API },
        { code: '4002', expectedCategory: ErrorCategory.SECURITY },
        { code: '5003', expectedCategory: ErrorCategory.SYSTEM }
      ];

      errors.forEach(({ code, expectedCategory }) => {
        // Act: Create and handle error
        const error: any = new Error('Test');
        error.code = code;
        const formatted = errorHandler.handle(error);

        // Assert: Correct category
        expect(formatted.category).toBe(expectedCategory);
      });
    });

    it('should handle edge cases in code ranges', () => {
      // Test boundary values
      const boundaries = [
        { code: '1000', category: ErrorCategory.CONFIGURATION },
        { code: '1999', category: ErrorCategory.CONFIGURATION },
        { code: '2000', category: ErrorCategory.PROCESSING },
        { code: '2999', category: ErrorCategory.PROCESSING },
        { code: '3000', category: ErrorCategory.API },
        { code: '3999', category: ErrorCategory.API },
        { code: '4000', category: ErrorCategory.SECURITY },
        { code: '4999', category: ErrorCategory.SECURITY },
        { code: '5000', category: ErrorCategory.SYSTEM },
        { code: '5999', category: ErrorCategory.SYSTEM }
      ];

      boundaries.forEach(({ code, category }) => {
        const error: any = new Error('Boundary test');
        error.code = code;
        const formatted = errorHandler.handle(error);
        expect(formatted.category).toBe(category);
      });
    });
  });

  describe('Error Timestamps', () => {
    it('should include ISO formatted timestamps', () => {
      // Arrange: Create error
      const error = new Error('Timestamp test');

      // Act: Handle error
      const formatted = errorHandler.handle(error);

      // Assert: Valid ISO timestamp
      expect(formatted.timestamp).toBeDefined();
      expect(new Date(formatted.timestamp).toISOString()).toBe(formatted.timestamp);
    });

    it('should preserve original error timestamps if present', () => {
      // Arrange: Error with existing timestamp
      const originalTimestamp = '2024-01-01T00:00:00.000Z';
      const error: any = new Error('Test');
      error.timestamp = originalTimestamp;

      // Act: Handle error
      const formatted = errorHandler.handle(error);

      // Assert: Original timestamp preserved
      expect(formatted.timestamp).toBe(originalTimestamp);
    });
  });
});