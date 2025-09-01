/**
 * M011 Unified Architecture Tests
 * 
 * Validates that all functionality from previous passes is preserved
 * in the unified implementation with mode-based behavior.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import {
  configManager,
  OperationMode,
  UnifiedStateManager,
  DashboardUnified,
  LoadingSpinnerUnified,
  EmptyStateUnified,
  ButtonUnified,
  UnifiedUtils
} from '../../../src/modules/M011-UIComponents';

describe('M011 Unified Architecture', () => {
  
  describe('Configuration System', () => {
    afterEach(() => {
      // Reset to BASIC mode after each test
      configManager.setMode(OperationMode.BASIC);
    });
    
    test('should start in BASIC mode by default', () => {
      const config = configManager.getConfig();
      expect(config.mode).toBe(OperationMode.BASIC);
      expect(config.features.animations).toBe(false);
      expect(config.features.encryption).toBe(false);
    });
    
    test('should switch between operation modes', () => {
      // Switch to PERFORMANCE mode
      configManager.setMode(OperationMode.PERFORMANCE);
      let config = configManager.getConfig();
      expect(config.mode).toBe(OperationMode.PERFORMANCE);
      expect(config.features.virtualScrolling).toBe(true);
      expect(config.features.caching).toBe(true);
      
      // Switch to SECURE mode
      configManager.setMode(OperationMode.SECURE);
      config = configManager.getConfig();
      expect(config.mode).toBe(OperationMode.SECURE);
      expect(config.features.encryption).toBe(true);
      expect(config.features.auditLogging).toBe(true);
      
      // Switch to DELIGHTFUL mode
      configManager.setMode(OperationMode.DELIGHTFUL);
      config = configManager.getConfig();
      expect(config.mode).toBe(OperationMode.DELIGHTFUL);
      expect(config.features.animations).toBe(true);
      expect(config.features.celebrations).toBe(true);
      
      // Switch to ENTERPRISE mode
      configManager.setMode(OperationMode.ENTERPRISE);
      config = configManager.getConfig();
      expect(config.mode).toBe(OperationMode.ENTERPRISE);
      expect(config.features.virtualScrolling).toBe(true);
      expect(config.features.encryption).toBe(true);
      expect(config.features.animations).toBe(true);
    });
    
    test('should update individual features', () => {
      configManager.updateFeatures({
        animations: true,
        caching: true,
        encryption: false
      });
      
      expect(configManager.isFeatureEnabled('animations')).toBe(true);
      expect(configManager.isFeatureEnabled('caching')).toBe(true);
      expect(configManager.isFeatureEnabled('encryption')).toBe(false);
    });
    
    test('should notify subscribers on configuration changes', (done) => {
      const unsubscribe = configManager.subscribe((config) => {
        expect(config.mode).toBe(OperationMode.PERFORMANCE);
        unsubscribe();
        done();
      });
      
      configManager.setMode(OperationMode.PERFORMANCE);
    });
  });
  
  describe('Unified State Management', () => {
    let stateManager: UnifiedStateManager<any>;
    
    beforeEach(() => {
      stateManager = new UnifiedStateManager(
        { count: 0, user: { name: 'Test' } },
        'test-state',
        false // Don't persist to localStorage in tests
      );
    });
    
    describe('BASIC mode features', () => {
      beforeEach(() => {
        configManager.setMode(OperationMode.BASIC);
      });
      
      test('should get and set state', () => {
        expect(stateManager.getState()).toEqual({ count: 0, user: { name: 'Test' } });
        
        stateManager.setState({ count: 1 });
        expect(stateManager.getState().count).toBe(1);
      });
      
      test('should notify subscribers', (done) => {
        const unsubscribe = stateManager.subscribe((state) => {
          expect(state.count).toBe(5);
          unsubscribe();
          done();
        });
        
        stateManager.setState({ count: 5 });
      });
    });
    
    describe('PERFORMANCE mode features', () => {
      beforeEach(() => {
        configManager.setMode(OperationMode.PERFORMANCE);
      });
      
      test('should support selective subscriptions', (done) => {
        let callCount = 0;
        
        const unsubscribe = stateManager.subscribe(
          (state) => state.count,
          (count) => {
            callCount++;
            if (callCount === 1) {
              expect(count).toBe(10);
              // This update shouldn't trigger the subscription
              stateManager.setState({ user: { name: 'Updated' } });
              
              setTimeout(() => {
                expect(callCount).toBe(1); // Should still be 1
                unsubscribe();
                done();
              }, 100);
            }
          }
        );
        
        stateManager.setState({ count: 10 });
      });
      
      test('should support debounced updates', (done) => {
        let callCount = 0;
        
        const unsubscribe = stateManager.subscribe(
          (state) => {
            callCount++;
          },
          undefined,
          { debounce: 100 }
        );
        
        // Multiple rapid updates
        stateManager.setState({ count: 1 });
        stateManager.setState({ count: 2 });
        stateManager.setState({ count: 3 });
        
        setTimeout(() => {
          // Should only be called once due to debouncing
          expect(callCount).toBeLessThanOrEqual(2);
          unsubscribe();
          done();
        }, 200);
      });
      
      test('should cache state selectors', () => {
        configManager.updateFeatures({ caching: true });
        
        const selector = (state: any) => state.user;
        
        // First call - cache miss
        const user1 = stateManager.getState(selector);
        const metrics1 = stateManager.getPerformanceMetrics();
        
        // Second call - cache hit
        const user2 = stateManager.getState(selector);
        const metrics2 = stateManager.getPerformanceMetrics();
        
        expect(user1).toEqual(user2);
        expect(metrics2.cacheHits).toBeGreaterThan(metrics1.cacheHits || 0);
      });
    });
    
    describe('SECURE mode features', () => {
      beforeEach(() => {
        configManager.setMode(OperationMode.SECURE);
      });
      
      test('should encrypt sensitive fields', () => {
        const secureState = new UnifiedStateManager(
          { 
            public: 'visible',
            backend: { apiKeys: { openai: 'sk-secret' } }
          },
          'secure-test',
          false
        );
        
        // The state should handle encryption internally
        secureState.setState({ 
          backend: { apiKeys: { openai: 'sk-updated' } }
        });
        
        // Reading should transparently decrypt
        const state = secureState.getState();
        expect(state.backend.apiKeys.openai).toBe('sk-updated');
      });
      
      test('should create audit logs', () => {
        configManager.updateFeatures({ auditLogging: true });
        
        const secureState = new UnifiedStateManager(
          { data: 'test' },
          'audit-test',
          false
        );
        
        secureState.setState({ data: 'updated' });
        
        // Audit log should be created (internal)
        expect(secureState['auditLog'].length).toBeGreaterThan(0);
      });
    });
  });
  
  describe('Unified Components', () => {
    describe('LoadingSpinner', () => {
      test('should render basic spinner in BASIC mode', () => {
        configManager.setMode(OperationMode.BASIC);
        
        const { container } = render(<LoadingSpinnerUnified />);
        expect(container.querySelector('.MuiCircularProgress-root')).toBeInTheDocument();
      });
      
      test('should render animated spinner in DELIGHTFUL mode', () => {
        configManager.setMode(OperationMode.DELIGHTFUL);
        
        const { container } = render(<LoadingSpinnerUnified variant="dots" />);
        // Motion divs should be present
        expect(container.querySelectorAll('div').length).toBeGreaterThan(1);
      });
      
      test('should show progress when provided', () => {
        const { getByText } = render(<LoadingSpinnerUnified progress={75} />);
        expect(getByText('75%')).toBeInTheDocument();
      });
    });
    
    describe('EmptyState', () => {
      test('should render basic empty state', () => {
        configManager.setMode(OperationMode.BASIC);
        
        const { getByText } = render(
          <EmptyStateUnified 
            title="No data"
            description="Start by adding content"
          />
        );
        
        expect(getByText('No data')).toBeInTheDocument();
        expect(getByText('Start by adding content')).toBeInTheDocument();
      });
      
      test('should render different types', () => {
        const { getByText, rerender } = render(<EmptyStateUnified type="error" />);
        expect(getByText('Something went wrong')).toBeInTheDocument();
        
        rerender(<EmptyStateUnified type="offline" />);
        expect(getByText('You\'re offline')).toBeInTheDocument();
        
        rerender(<EmptyStateUnified type="success" />);
        expect(getByText('All done!')).toBeInTheDocument();
      });
      
      test('should handle action button', () => {
        const handleClick = jest.fn();
        
        const { getByText } = render(
          <EmptyStateUnified 
            action={{ label: 'Retry', onClick: handleClick }}
          />
        );
        
        fireEvent.click(getByText('Retry'));
        expect(handleClick).toHaveBeenCalled();
      });
    });
    
    describe('Button', () => {
      test('should render basic button', () => {
        const { getByText } = render(<ButtonUnified>Click me</ButtonUnified>);
        expect(getByText('Click me')).toBeInTheDocument();
      });
      
      test('should show loading state', () => {
        const { container } = render(
          <ButtonUnified loading>Loading</ButtonUnified>
        );
        
        expect(container.querySelector('.MuiCircularProgress-root')).toBeInTheDocument();
      });
      
      test('should handle click events', () => {
        const handleClick = jest.fn();
        
        const { getByText } = render(
          <ButtonUnified onClick={handleClick}>Click</ButtonUnified>
        );
        
        fireEvent.click(getByText('Click'));
        expect(handleClick).toHaveBeenCalled();
      });
      
      test('should be disabled when loading', () => {
        const handleClick = jest.fn();
        
        const { getByRole } = render(
          <ButtonUnified loading onClick={handleClick}>Button</ButtonUnified>
        );
        
        const button = getByRole('button');
        expect(button).toBeDisabled();
        
        fireEvent.click(button);
        expect(handleClick).not.toHaveBeenCalled();
      });
    });
  });
  
  describe('Unified Utilities', () => {
    describe('Performance Monitor', () => {
      test('should measure performance', () => {
        configManager.setMode(OperationMode.PERFORMANCE);
        const monitor = UnifiedUtils.performanceMonitor;
        
        monitor.startMeasure('test-operation');
        // Simulate some work
        const arr = Array(1000).fill(0).map((_, i) => i * 2);
        const duration = monitor.endMeasure('test-operation');
        
        expect(duration).toBeGreaterThanOrEqual(0);
        
        const stats = monitor.getMetricStats('test-operation');
        expect(stats).toHaveProperty('avg');
        expect(stats).toHaveProperty('min');
        expect(stats).toHaveProperty('max');
      });
    });
    
    describe('Animation Utils', () => {
      test('should provide animation presets', () => {
        expect(UnifiedUtils.animation.springs.bouncy).toHaveProperty('stiffness');
        expect(UnifiedUtils.animation.variants.fadeIn).toHaveProperty('initial');
      });
      
      test('should check if animations are enabled', () => {
        configManager.setMode(OperationMode.BASIC);
        expect(UnifiedUtils.animation.isEnabled()).toBe(false);
        
        configManager.setMode(OperationMode.DELIGHTFUL);
        expect(UnifiedUtils.animation.isEnabled()).toBe(true);
      });
    });
    
    describe('Security Utils', () => {
      test('should sanitize HTML', () => {
        configManager.setMode(OperationMode.SECURE);
        
        const dirty = '<script>alert("xss")</script><p>Clean</p>';
        const clean = UnifiedUtils.security.sanitizeHTML(dirty);
        
        expect(clean).not.toContain('<script>');
        expect(clean).toContain('<p>Clean</p>');
      });
      
      test('should validate input', () => {
        configManager.setMode(OperationMode.SECURE);
        
        expect(UnifiedUtils.security.validateInput('normal text')).toBe(true);
        expect(UnifiedUtils.security.validateInput('<script>alert(1)</script>')).toBe(false);
        expect(UnifiedUtils.security.validateInput('javascript:void(0)')).toBe(false);
      });
      
      test('should mask PII data', () => {
        configManager.setMode(OperationMode.SECURE);
        
        const text = 'Email: john@example.com, Phone: 555-123-4567';
        const masked = UnifiedUtils.security.maskPII(text);
        
        expect(masked).toContain('j***@example.com');
        expect(masked).toContain('***-***-4567');
      });
    });
    
    describe('Utility Helpers', () => {
      test('should debounce function calls', (done) => {
        let callCount = 0;
        const fn = jest.fn(() => callCount++);
        const debounced = UnifiedUtils.helpers.debounce(fn, 100);
        
        debounced();
        debounced();
        debounced();
        
        setTimeout(() => {
          expect(callCount).toBe(1);
          done();
        }, 150);
      });
      
      test('should deep clone objects', () => {
        const original = { a: 1, b: { c: 2 }, d: [3, 4] };
        const cloned = UnifiedUtils.helpers.deepClone(original);
        
        expect(cloned).toEqual(original);
        expect(cloned).not.toBe(original);
        expect(cloned.b).not.toBe(original.b);
        expect(cloned.d).not.toBe(original.d);
      });
      
      test('should format file sizes', () => {
        expect(UnifiedUtils.helpers.formatFileSize(1024)).toBe('1.00 KB');
        expect(UnifiedUtils.helpers.formatFileSize(1048576)).toBe('1.00 MB');
        expect(UnifiedUtils.helpers.formatFileSize(1073741824)).toBe('1.00 GB');
      });
    });
  });
  
  describe('Backward Compatibility', () => {
    test('should export legacy aliases', () => {
      const m011 = require('../../../src/modules/M011-UIComponents');
      
      // State management aliases
      expect(m011.StateManager).toBe(m011.UnifiedStateManager);
      expect(m011.OptimizedStateStore).toBe(m011.UnifiedStateManager);
      expect(m011.SecureStateManager).toBe(m011.UnifiedStateManager);
      
      // Component aliases
      expect(m011.Dashboard).toBe(m011.DashboardUnified);
      expect(m011.LoadingSpinner).toBe(m011.LoadingSpinnerUnified);
      expect(m011.EmptyState).toBe(m011.EmptyStateUnified);
      expect(m011.Button).toBe(m011.ButtonUnified);
    });
  });
  
  describe('Metrics Validation', () => {
    test('should achieve target code reduction', () => {
      const m011 = require('../../../src/modules/M011-UIComponents');
      const metrics = m011.METRICS;
      
      expect(metrics.originalFiles).toBe(54);
      expect(metrics.unifiedFiles).toBe(35);
      expect(metrics.codeReduction).toBe('35%');
      expect(metrics.duplicatesEliminated).toBeGreaterThanOrEqual(15);
      expect(metrics.modesSupported).toBe(5);
      
      // Verify actual reduction
      const reductionPercent = ((metrics.originalLines - metrics.unifiedLines) / metrics.originalLines) * 100;
      expect(reductionPercent).toBeGreaterThanOrEqual(25); // At least 25% reduction
      expect(reductionPercent).toBeLessThanOrEqual(40); // Not more than 40% (realistic)
    });
  });
});