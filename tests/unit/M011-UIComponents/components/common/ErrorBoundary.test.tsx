/**
 * ErrorBoundary Component Tests
 * 
 * Tests for the ErrorBoundary component including:
 * - Error catching and display
 * - Retry functionality
 * - Error reporting
 * - Fallback UI rendering
 * - Recovery mechanisms
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ErrorBoundary from '../../../../../src/modules/M011-UIComponents/components/common/ErrorBoundary';

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

// Component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean; errorMessage?: string }> = ({ 
  shouldThrow = true, 
  errorMessage = 'Test error' 
}) => {
  if (shouldThrow) {
    throw new Error(errorMessage);
  }
  return <div>No error</div>;
};

// Component that works normally
const WorkingComponent: React.FC = () => {
  return <div>Working component</div>;
};

describe('ErrorBoundary', () => {
  // Suppress error console logs during tests
  beforeEach(() => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('normal operation', () => {
    test('should render children when no error occurs', () => {
      renderWithTheme(
        <ErrorBoundary>
          <WorkingComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Working component')).toBeInTheDocument();
    });

    test('should not show error UI when children render successfully', () => {
      renderWithTheme(
        <ErrorBoundary>
          <WorkingComponent />
        </ErrorBoundary>
      );

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      expect(screen.queryByText('Component Error')).not.toBeInTheDocument();
    });
  });

  describe('error catching', () => {
    test('should catch and display error', () => {
      renderWithTheme(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Component Error')).toBeInTheDocument();
      expect(screen.getByText('Test error')).toBeInTheDocument();
    });

    test('should display custom error message', () => {
      const customMessage = 'Custom error occurred';
      renderWithTheme(
        <ErrorBoundary>
          <ThrowError errorMessage={customMessage} />
        </ErrorBoundary>
      );

      expect(screen.getByText(customMessage)).toBeInTheDocument();
    });

    test('should handle error with no message', () => {
      renderWithTheme(
        <ErrorBoundary>
          <ThrowError errorMessage="" />
        </ErrorBoundary>
      );

      expect(screen.getByText('An unexpected error occurred while rendering this component.')).toBeInTheDocument();
    });
  });

  describe('error boundary levels', () => {
    test('should show page-level error UI', () => {
      renderWithTheme(
        <ErrorBoundary level="page">
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText('Oops! Something went wrong')).toBeInTheDocument();
      expect(screen.getByText('The page encountered an error and cannot be displayed properly.')).toBeInTheDocument();
    });

    test('should show component-level error UI (default)', () => {
      renderWithTheme(
        <ErrorBoundary level="component">
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText('Component Error')).toBeInTheDocument();
      expect(screen.getByText('This component failed to render due to an error.')).toBeInTheDocument();
    });

    test('should show widget-level error UI', () => {
      renderWithTheme(
        <ErrorBoundary level="widget">
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText('Component Error')).toBeInTheDocument();
    });
  });

  describe('retry functionality', () => {
    test('should show retry button', () => {
      renderWithTheme(
        <ErrorBoundary maxRetries={3}>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText('Try Again')).toBeInTheDocument();
    });

    test('should retry when retry button is clicked', () => {
      let shouldThrow = true;
      const TestComponent = () => {
        if (shouldThrow) {
          shouldThrow = false; // Only throw once
          throw new Error('First time error');
        }
        return <div>Retry successful</div>;
      };

      renderWithTheme(
        <ErrorBoundary maxRetries={3}>
          <TestComponent />
        </ErrorBoundary>
      );

      // Should show error first
      expect(screen.getByText('Component Error')).toBeInTheDocument();

      // Click retry
      fireEvent.click(screen.getByText('Try Again'));

      // Should show successful component
      expect(screen.getByText('Retry successful')).toBeInTheDocument();
    });

    test('should track retry count', () => {
      renderWithTheme(
        <ErrorBoundary maxRetries={2}>
          <ThrowError />
        </ErrorBoundary>
      );

      // Initial error - should show "Retry attempts: 0/2"
      expect(screen.getByText(/Retry attempts: 0\/2/)).toBeInTheDocument();

      // Click retry once
      fireEvent.click(screen.getByText('Try Again'));

      // Should show "Retry attempts: 1/2"
      expect(screen.getByText(/Retry attempts: 1\/2/)).toBeInTheDocument();
    });

    test('should hide retry button after max retries', () => {
      renderWithTheme(
        <ErrorBoundary maxRetries={1}>
          <ThrowError />
        </ErrorBoundary>
      );

      // Click retry once
      fireEvent.click(screen.getByText('Try Again'));

      // Should still show retry button with count 1/1
      expect(screen.getByText('Try Again')).toBeInTheDocument();

      // Click retry again (should be last attempt)
      fireEvent.click(screen.getByText('Try Again'));

      // Should not show retry button anymore
      expect(screen.queryByText('Try Again')).not.toBeInTheDocument();
    });
  });

  describe('error reporting', () => {
    test('should show report issue button', () => {
      renderWithTheme(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText('Report Issue')).toBeInTheDocument();
    });

    test('should handle report issue click', () => {
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: jest.fn().mockResolvedValue('')
        }
      });

      // Mock alert
      const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});

      renderWithTheme(
        <ErrorBoundary>
          <ThrowError errorMessage="Reportable error" />
        </ErrorBoundary>
      );

      fireEvent.click(screen.getByText('Report Issue'));

      expect(navigator.clipboard.writeText).toHaveBeenCalled();

      alertSpy.mockRestore();
    });

    test('should handle clipboard failure gracefully', () => {
      // Mock clipboard API to fail
      Object.assign(navigator, {
        clipboard: {
          writeText: jest.fn().mockRejectedValue(new Error('Clipboard error'))
        }
      });

      renderWithTheme(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      // Should not throw when clicking report
      expect(() => {
        fireEvent.click(screen.getByText('Report Issue'));
      }).not.toThrow();
    });
  });

  describe('custom fallback UI', () => {
    test('should render custom fallback', () => {
      const customFallback = <div>Custom error UI</div>;

      renderWithTheme(
        <ErrorBoundary fallback={customFallback}>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText('Custom error UI')).toBeInTheDocument();
      expect(screen.queryByText('Component Error')).not.toBeInTheDocument();
    });
  });

  describe('error details', () => {
    test('should show error details in development', () => {
      // Mock development environment
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      renderWithTheme(
        <ErrorBoundary showDetails={true}>
          <ThrowError errorMessage="Detailed error" />
        </ErrorBoundary>
      );

      expect(screen.getByText('Show Error Details')).toBeInTheDocument();

      // Expand details
      fireEvent.click(screen.getByText('Show Error Details'));

      expect(screen.getByText('Error Message:')).toBeInTheDocument();
      expect(screen.getByText('Detailed error')).toBeInTheDocument();

      // Restore environment
      process.env.NODE_ENV = originalEnv;
    });

    test('should hide error details in production', () => {
      renderWithTheme(
        <ErrorBoundary showDetails={false}>
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.queryByText('Show Error Details')).not.toBeInTheDocument();
    });
  });

  describe('reset functionality', () => {
    test('should reset when resetKeys change', () => {
      let shouldThrow = true;
      const TestComponent = () => {
        if (shouldThrow) {
          throw new Error('Resetable error');
        }
        return <div>Reset successful</div>;
      };

      const { rerender } = renderWithTheme(
        <ErrorBoundary resetKeys={['key1']}>
          <TestComponent />
        </ErrorBoundary>
      );

      // Should show error
      expect(screen.getByText('Component Error')).toBeInTheDocument();

      // Stop throwing and change reset key
      shouldThrow = false;
      rerender(
        <ThemeProvider theme={theme}>
          <ErrorBoundary resetKeys={['key2']}>
            <TestComponent />
          </ErrorBoundary>
        </ThemeProvider>
      );

      // Should show successful component
      expect(screen.getByText('Reset successful')).toBeInTheDocument();
    });
  });

  describe('lifecycle methods', () => {
    test('should call onError callback', () => {
      const onErrorSpy = jest.fn();

      renderWithTheme(
        <ErrorBoundary onError={onErrorSpy}>
          <ThrowError errorMessage="Callback test error" />
        </ErrorBoundary>
      );

      expect(onErrorSpy).toHaveBeenCalledWith(
        expect.any(Error),
        expect.objectContaining({
          componentStack: expect.any(String)
        })
      );
    });
  });

  describe('page-level specific features', () => {
    test('should show "Go Home" button for page-level errors', () => {
      // Mock window.location
      delete (window as any).location;
      window.location = { href: '' } as any;

      renderWithTheme(
        <ErrorBoundary level="page">
          <ThrowError />
        </ErrorBoundary>
      );

      expect(screen.getByText('Go Home')).toBeInTheDocument();
    });

    test('should navigate home when "Go Home" is clicked', () => {
      // Mock window.location
      delete (window as any).location;
      window.location = { href: '' } as any;

      renderWithTheme(
        <ErrorBoundary level="page">
          <ThrowError />
        </ErrorBoundary>
      );

      fireEvent.click(screen.getByText('Go Home'));

      expect(window.location.href).toBe('/');
    });
  });

  describe('accessibility', () => {
    test('should have proper ARIA attributes', () => {
      renderWithTheme(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const alertElement = screen.getByRole('alert');
      expect(alertElement).toHaveAttribute('aria-live', 'assertive');
    });

    test('should be keyboard accessible', () => {
      renderWithTheme(
        <ErrorBoundary>
          <ThrowError />
        </ErrorBoundary>
      );

      const retryButton = screen.getByText('Try Again');
      expect(retryButton).toBeInTheDocument();
      
      // Should be focusable
      retryButton.focus();
      expect(retryButton).toHaveFocus();
    });
  });
});