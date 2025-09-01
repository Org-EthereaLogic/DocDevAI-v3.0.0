/**
 * LoadingSpinner Component Tests
 * 
 * Tests for the LoadingSpinner component including:
 * - Rendering with different props
 * - Size variants
 * - Accessibility features
 * - High contrast mode
 * - Full screen and overlay modes
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import LoadingSpinner from '../../../../../src/modules/M011-UIComponents/components/common/LoadingSpinner';
import { StateManager } from '../../../../../src/modules/M011-UIComponents/core/state-management';

// Mock the global state hook
const mockStateManager = new StateManager();
jest.mock('../../../../../src/modules/M011-UIComponents/core/state-management', () => ({
  useGlobalState: () => mockStateManager
}));

const theme = createTheme();

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('LoadingSpinner', () => {
  beforeEach(() => {
    // Reset state before each test
    mockStateManager.reset();
  });

  describe('basic rendering', () => {
    test('should render with default props', () => {
      renderWithTheme(<LoadingSpinner />);
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toBeInTheDocument();
      expect(statusElement).toHaveAttribute('aria-label', 'Loading...');
    });

    test('should render with custom message', () => {
      const message = 'Processing data...';
      renderWithTheme(<LoadingSpinner message={message} />);
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toHaveAttribute('aria-label', message);
      expect(screen.getByText(message)).toBeInTheDocument();
    });

    test('should render without message when message is empty', () => {
      renderWithTheme(<LoadingSpinner message="" />);
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toBeInTheDocument();
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
  });

  describe('size variants', () => {
    test('should render small size', () => {
      renderWithTheme(<LoadingSpinner size="small" />);
      
      const spinner = document.querySelector('.MuiCircularProgress-root');
      expect(spinner).toHaveStyle({
        width: '20px',
        height: '20px'
      });
    });

    test('should render medium size (default)', () => {
      renderWithTheme(<LoadingSpinner size="medium" />);
      
      const spinner = document.querySelector('.MuiCircularProgress-root');
      expect(spinner).toHaveStyle({
        width: '40px',
        height: '40px'
      });
    });

    test('should render large size', () => {
      renderWithTheme(<LoadingSpinner size="large" />);
      
      const spinner = document.querySelector('.MuiCircularProgress-root');
      expect(spinner).toHaveStyle({
        width: '60px',
        height: '60px'
      });
    });
  });

  describe('color variants', () => {
    test('should render with primary color (default)', () => {
      renderWithTheme(<LoadingSpinner color="primary" />);
      
      const spinner = document.querySelector('.MuiCircularProgress-root');
      expect(spinner).toHaveClass('MuiCircularProgress-colorPrimary');
    });

    test('should render with secondary color', () => {
      renderWithTheme(<LoadingSpinner color="secondary" />);
      
      const spinner = document.querySelector('.MuiCircularProgress-root');
      expect(spinner).toHaveClass('MuiCircularProgress-colorSecondary');
    });

    test('should render with inherit color', () => {
      renderWithTheme(<LoadingSpinner color="inherit" />);
      
      const spinner = document.querySelector('.MuiCircularProgress-root');
      expect(spinner).toHaveClass('MuiCircularProgress-colorInherit');
    });
  });

  describe('accessibility features', () => {
    test('should have proper ARIA attributes', () => {
      const message = 'Loading content...';
      renderWithTheme(<LoadingSpinner message={message} />);
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toHaveAttribute('aria-live', 'polite');
      expect(statusElement).toHaveAttribute('aria-label', message);
    });

    test('should handle high contrast mode', () => {
      // Enable high contrast mode
      mockStateManager.updateUIState({
        accessibility: {
          highContrast: true,
          reduceMotion: false,
          keyboardNavigation: true,
          enhancedSupport: false
        }
      });

      renderWithTheme(<LoadingSpinner />);
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toBeInTheDocument();
    });

    test('should display appropriate text size for small spinner', () => {
      renderWithTheme(
        <LoadingSpinner size="small" message="Small loading..." />
      );
      
      const textElement = screen.getByText('Small loading...');
      expect(textElement).toHaveClass('MuiTypography-caption');
    });

    test('should display appropriate text size for medium/large spinner', () => {
      renderWithTheme(
        <LoadingSpinner size="medium" message="Medium loading..." />
      );
      
      const textElement = screen.getByText('Medium loading...');
      expect(textElement).toHaveClass('MuiTypography-body2');
    });
  });

  describe('full screen mode', () => {
    test('should render in full screen mode', () => {
      renderWithTheme(<LoadingSpinner fullScreen />);
      
      const container = document.querySelector('[style*="position: fixed"]');
      expect(container).toBeInTheDocument();
      expect(container).toHaveStyle({
        position: 'fixed',
        top: '0px',
        left: '0px',
        right: '0px',
        bottom: '0px'
      });
    });

    test('should render full screen with overlay', () => {
      renderWithTheme(<LoadingSpinner fullScreen overlay />);
      
      const container = document.querySelector('[style*="position: fixed"]');
      expect(container).toHaveStyle({
        backgroundColor: 'rgba(255, 255, 255, 0.8)'
      });
    });

    test('should render full screen without overlay', () => {
      renderWithTheme(<LoadingSpinner fullScreen overlay={false} />);
      
      const container = document.querySelector('[style*="position: fixed"]');
      expect(container).toHaveStyle({
        backgroundColor: 'transparent'
      });
    });
  });

  describe('overlay mode', () => {
    test('should render with overlay but not full screen', () => {
      renderWithTheme(<LoadingSpinner overlay />);
      
      const container = document.querySelector('[style*="position: absolute"]');
      expect(container).toBeInTheDocument();
      expect(container).toHaveStyle({
        position: 'absolute',
        backgroundColor: 'rgba(255, 255, 255, 0.8)'
      });
    });

    test('should handle high contrast mode with overlay', () => {
      mockStateManager.updateUIState({
        accessibility: {
          highContrast: true,
          reduceMotion: false,
          keyboardNavigation: true,
          enhancedSupport: false
        }
      });

      renderWithTheme(<LoadingSpinner overlay />);
      
      const container = document.querySelector('[style*="position: absolute"]');
      expect(container).toBeInTheDocument();
    });
  });

  describe('custom styling', () => {
    test('should accept custom className', () => {
      const className = 'custom-loading-spinner';
      renderWithTheme(<LoadingSpinner className={className} />);
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toHaveClass(className);
    });
  });

  describe('responsive behavior', () => {
    test('should maintain aspect ratio in different container sizes', () => {
      const { container } = renderWithTheme(<LoadingSpinner />);
      
      const statusElement = container.querySelector('[role="status"]');
      expect(statusElement).toHaveStyle({
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center'
      });
    });
  });

  describe('error handling', () => {
    test('should handle null message gracefully', () => {
      renderWithTheme(<LoadingSpinner message={null as any} />);
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toBeInTheDocument();
    });

    test('should handle undefined size gracefully', () => {
      renderWithTheme(<LoadingSpinner size={undefined as any} />);
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toBeInTheDocument();
    });
  });

  describe('interaction with global state', () => {
    test('should respond to theme changes', () => {
      // Initial render
      const { rerender } = renderWithTheme(<LoadingSpinner />);
      
      // Change theme
      mockStateManager.updateUIState({ theme: 'dark' });
      
      // Re-render and verify it still works
      rerender(
        <ThemeProvider theme={theme}>
          <LoadingSpinner />
        </ThemeProvider>
      );
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toBeInTheDocument();
    });

    test('should respond to accessibility changes', () => {
      renderWithTheme(<LoadingSpinner />);
      
      // Enable high contrast
      mockStateManager.updateUIState({
        accessibility: {
          highContrast: true,
          reduceMotion: true,
          keyboardNavigation: true,
          enhancedSupport: true
        }
      });
      
      const statusElement = screen.getByRole('status');
      expect(statusElement).toBeInTheDocument();
    });
  });
});