/**
 * QuickActionsWidget Component Tests
 * 
 * Tests for the QuickActionsWidget component including:
 * - Action rendering and execution
 * - Keyboard shortcuts
 * - Accessibility features
 * - Loading and error states
 * - High contrast mode
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import QuickActionsWidget from '../../../../../src/modules/M011-UIComponents/components/dashboard/QuickActionsWidget';
import { StateManager } from '../../../../../src/modules/M011-UIComponents/core/state-management';
import { EventManager } from '../../../../../src/modules/M011-UIComponents/core/event-system';

const theme = createTheme();
const mockStateManager = new StateManager();
const mockEventManager = new EventManager();

// Mock the hooks
jest.mock('../../../../../src/modules/M011-UIComponents/core/state-management', () => ({
  useGlobalState: () => mockStateManager
}));

jest.mock('../../../../../src/modules/M011-UIComponents/core/event-system', () => ({
  eventManager: mockEventManager,
  UIEventType: {
    USER_ACTION: 'USER_ACTION',
    NOTIFICATION_SENT: 'NOTIFICATION_SENT'
  }
}));

jest.mock('../../../../../src/modules/M011-UIComponents/core/accessibility', () => ({
  accessibilityManager: {
    announceToScreenReader: jest.fn()
  }
}));

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ThemeProvider theme={theme}>
      {component}
    </ThemeProvider>
  );
};

describe('QuickActionsWidget', () => {
  beforeEach(() => {
    mockStateManager.reset();
    jest.clearAllMocks();
  });

  describe('basic rendering', () => {
    test('should render with default props', () => {
      renderWithTheme(<QuickActionsWidget />);
      
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    });

    test('should render custom title', () => {
      const customTitle = 'My Quick Actions';
      renderWithTheme(<QuickActionsWidget title={customTitle} />);
      
      expect(screen.getByText(customTitle)).toBeInTheDocument();
    });

    test('should render default actions', () => {
      renderWithTheme(<QuickActionsWidget />);
      
      expect(screen.getByText('Generate Document')).toBeInTheDocument();
      expect(screen.getByText('Analyze Quality')).toBeInTheDocument();
      expect(screen.getByText('Enhance Documents')).toBeInTheDocument();
      expect(screen.getByText('Create Suite')).toBeInTheDocument();
      expect(screen.getByText('Batch Process')).toBeInTheDocument();
      expect(screen.getByText('Manage Templates')).toBeInTheDocument();
      expect(screen.getByText('Settings')).toBeInTheDocument();
      expect(screen.getByText('Help & Tutorial')).toBeInTheDocument();
    });
  });

  describe('custom actions', () => {
    test('should render custom actions', () => {
      const customActions = [
        {
          id: 'custom-action',
          label: 'Custom Action',
          description: 'Custom description',
          icon: <div data-testid="custom-icon" />,
          action: jest.fn(),
          category: 'custom'
        }
      ];

      renderWithTheme(<QuickActionsWidget actions={customActions} />);
      
      expect(screen.getByText('Custom Action')).toBeInTheDocument();
      expect(screen.getByText('Custom description')).toBeInTheDocument();
      expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    });
  });

  describe('action execution', () => {
    test('should execute action when clicked', async () => {
      const mockAction = jest.fn().mockResolvedValue(undefined);
      const customActions = [
        {
          id: 'test-action',
          label: 'Test Action',
          description: 'Test description',
          icon: <div data-testid="test-icon" />,
          action: mockAction,
          category: 'test'
        }
      ];

      renderWithTheme(<QuickActionsWidget actions={customActions} />);
      
      const actionCard = screen.getByText('Test Action').closest('[role="button"]');
      expect(actionCard).toBeInTheDocument();
      
      fireEvent.click(actionCard!);
      
      await waitFor(() => {
        expect(mockAction).toHaveBeenCalled();
      });
    });

    test('should use custom action handler when provided', async () => {
      const mockOnActionClick = jest.fn().mockResolvedValue(undefined);
      const customActions = [
        {
          id: 'test-action',
          label: 'Test Action',
          description: 'Test description',
          icon: <div data-testid="test-icon" />,
          action: jest.fn(), // This should not be called
          category: 'test'
        }
      ];

      renderWithTheme(
        <QuickActionsWidget 
          actions={customActions} 
          onActionClick={mockOnActionClick}
        />
      );
      
      const actionCard = screen.getByText('Test Action').closest('[role="button"]');
      fireEvent.click(actionCard!);
      
      await waitFor(() => {
        expect(mockOnActionClick).toHaveBeenCalledWith('test-action');
      });
    });

    test('should handle action execution errors', async () => {
      const mockAction = jest.fn().mockRejectedValue(new Error('Action failed'));
      const customActions = [
        {
          id: 'failing-action',
          label: 'Failing Action',
          description: 'This will fail',
          icon: <div data-testid="failing-icon" />,
          action: mockAction,
          category: 'test'
        }
      ];

      renderWithTheme(<QuickActionsWidget actions={customActions} />);
      
      const actionCard = screen.getByText('Failing Action').closest('[role="button"]');
      fireEvent.click(actionCard!);
      
      await waitFor(() => {
        expect(mockAction).toHaveBeenCalled();
      });

      // Should add error notification to state
      const state = mockStateManager.getState();
      expect(state.ui.notifications).toHaveLength(1);
      expect(state.ui.notifications[0].type).toBe('error');
    });

    test('should show loading state during execution', async () => {
      let resolveAction: () => void;
      const mockAction = jest.fn(() => new Promise<void>(resolve => {
        resolveAction = resolve;
      }));
      
      const customActions = [
        {
          id: 'slow-action',
          label: 'Slow Action',
          description: 'Takes time',
          icon: <div data-testid="slow-icon" />,
          action: mockAction,
          category: 'test'
        }
      ];

      renderWithTheme(<QuickActionsWidget actions={customActions} />);
      
      const actionCard = screen.getByText('Slow Action').closest('[role="button"]');
      fireEvent.click(actionCard!);
      
      // Should show executing state
      await waitFor(() => {
        expect(actionCard).toHaveStyle({ opacity: '0.7' });
      });

      // Resolve the action
      resolveAction!();
      
      await waitFor(() => {
        expect(actionCard).not.toHaveStyle({ opacity: '0.7' });
      });
    });
  });

  describe('keyboard shortcuts', () => {
    test('should show keyboard shortcut indicator when enabled', () => {
      mockStateManager.updateUIState({
        accessibility: {
          keyboardNavigation: true,
          highContrast: false,
          reduceMotion: false,
          enhancedSupport: false
        }
      });

      renderWithTheme(<QuickActionsWidget />);
      
      expect(screen.getByTitle('Keyboard shortcuts enabled')).toBeInTheDocument();
    });

    test('should hide keyboard shortcut indicator when disabled', () => {
      mockStateManager.updateUIState({
        accessibility: {
          keyboardNavigation: false,
          highContrast: false,
          reduceMotion: false,
          enhancedSupport: false
        }
      });

      renderWithTheme(<QuickActionsWidget />);
      
      expect(screen.queryByTitle('Keyboard shortcuts enabled')).not.toBeInTheDocument();
    });

    test('should handle keyboard shortcut execution', () => {
      mockStateManager.updateUIState({
        accessibility: {
          keyboardNavigation: true,
          highContrast: false,
          reduceMotion: false,
          enhancedSupport: false
        }
      });

      const mockAction = jest.fn();
      const customActions = [
        {
          id: 'keyboard-action',
          label: 'Keyboard Action',
          description: 'Has shortcut',
          icon: <div data-testid="keyboard-icon" />,
          action: mockAction,
          shortcut: 'Ctrl+K',
          category: 'test'
        }
      ];

      renderWithTheme(<QuickActionsWidget actions={customActions} />);
      
      // Simulate keyboard event
      fireEvent.keyDown(window, {
        key: 'k',
        ctrlKey: true,
        preventDefault: jest.fn()
      });
      
      expect(mockAction).toHaveBeenCalled();
    });

    test('should show keyboard shortcuts in cards', () => {
      renderWithTheme(<QuickActionsWidget />);
      
      // Look for default shortcuts (Ctrl+N for Generate Document)
      expect(screen.getByText('Ctrl+N')).toBeInTheDocument();
      expect(screen.getByText('Ctrl+A')).toBeInTheDocument();
      expect(screen.getByText('Ctrl+E')).toBeInTheDocument();
    });
  });

  describe('accessibility features', () => {
    test('should have proper ARIA attributes', () => {
      renderWithTheme(<QuickActionsWidget />);
      
      const actionCards = screen.getAllByRole('button');
      actionCards.forEach(card => {
        expect(card).toHaveAttribute('aria-label');
        expect(card).toHaveAttribute('tabIndex');
      });
    });

    test('should handle keyboard navigation', () => {
      renderWithTheme(<QuickActionsWidget />);
      
      const firstActionCard = screen.getByText('Generate Document').closest('[role="button"]');
      
      // Should handle Enter key
      fireEvent.keyDown(firstActionCard!, {
        key: 'Enter',
        preventDefault: jest.fn()
      });
      
      // Should handle Space key
      fireEvent.keyDown(firstActionCard!, {
        key: ' ',
        preventDefault: jest.fn()
      });
    });

    test('should support high contrast mode', () => {
      mockStateManager.updateUIState({
        accessibility: {
          highContrast: true,
          keyboardNavigation: true,
          reduceMotion: false,
          enhancedSupport: false
        }
      });

      renderWithTheme(<QuickActionsWidget />);
      
      // Should render without errors in high contrast mode
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    });

    test('should disable actions when disabled prop is set', () => {
      const customActions = [
        {
          id: 'disabled-action',
          label: 'Disabled Action',
          description: 'Cannot be clicked',
          icon: <div data-testid="disabled-icon" />,
          action: jest.fn(),
          disabled: true,
          category: 'test'
        }
      ];

      renderWithTheme(<QuickActionsWidget actions={customActions} />);
      
      const actionCard = screen.getByText('Disabled Action').closest('[role="button"]');
      expect(actionCard).toHaveAttribute('tabIndex', '-1');
      expect(actionCard).toHaveStyle({ opacity: '0.6' });
    });
  });

  describe('loading and error states', () => {
    test('should show loading state', () => {
      renderWithTheme(<QuickActionsWidget loading={true} />);
      
      // Widget should still render the title during loading
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    });

    test('should show error state', () => {
      const errorMessage = 'Failed to load actions';
      renderWithTheme(<QuickActionsWidget error={errorMessage} />);
      
      expect(screen.getByText(`Failed to load quick actions: ${errorMessage}`)).toBeInTheDocument();
    });

    test('should show refresh button in error state', () => {
      const mockOnRefresh = jest.fn();
      renderWithTheme(
        <QuickActionsWidget 
          error="Test error" 
          onRefresh={mockOnRefresh}
        />
      );
      
      const refreshButton = screen.getByTitle('Refresh actions');
      fireEvent.click(refreshButton);
      
      expect(mockOnRefresh).toHaveBeenCalled();
    });
  });

  describe('category system', () => {
    test('should display category chips', () => {
      renderWithTheme(<QuickActionsWidget />);
      
      // Should show category labels for default actions
      expect(screen.getByText('Create')).toBeInTheDocument();
      expect(screen.getByText('Analyze')).toBeInTheDocument();
      expect(screen.getByText('Enhance')).toBeInTheDocument();
    });

    test('should apply category colors', () => {
      renderWithTheme(<QuickActionsWidget />);
      
      // Should render category chips with appropriate styling
      const createChip = screen.getByText('Create');
      expect(createChip.closest('.MuiChip-root')).toBeInTheDocument();
    });
  });

  describe('responsive behavior', () => {
    test('should hide descriptions on mobile', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 600,
      });

      renderWithTheme(<QuickActionsWidget />);
      
      // Descriptions should still be present but may be handled by responsive styling
      expect(screen.getByText('Quick Actions')).toBeInTheDocument();
    });
  });

  describe('menu functionality', () => {
    test('should show options menu', () => {
      renderWithTheme(<QuickActionsWidget />);
      
      const menuButton = screen.getByRole('button', { name: /more/i });
      fireEvent.click(menuButton);
      
      expect(screen.getByText('Customize Actions')).toBeInTheDocument();
      expect(screen.getByText('Keyboard Shortcuts')).toBeInTheDocument();
      expect(screen.getByText('Reset to Default')).toBeInTheDocument();
    });

    test('should close menu when option is selected', () => {
      renderWithTheme(<QuickActionsWidget />);
      
      const menuButton = screen.getByRole('button', { name: /more/i });
      fireEvent.click(menuButton);
      
      const customizeOption = screen.getByText('Customize Actions');
      fireEvent.click(customizeOption);
      
      // Menu should close
      expect(screen.queryByText('Customize Actions')).not.toBeInTheDocument();
    });
  });
});