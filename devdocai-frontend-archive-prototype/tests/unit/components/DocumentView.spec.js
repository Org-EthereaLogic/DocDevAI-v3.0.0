/**
 * Unit tests for DocumentView component
 * Tests document display, accessibility, and user interactions
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createTestingPinia } from '../../setup';
import DocumentView from '@/components/DocumentView.vue';
import { useNotificationStore } from '@/stores/notification';
import { mockFormData, createA11yMocks, flushPromises } from '../../utils/testHelpers';

describe('DocumentView', () => {
  let wrapper;
  let notificationStore;
  let a11yMocks;

  const mockDocument = {
    content: '# Test Project\n\nThis is a test document with **bold** text and `code`.',
    metadata: {
      generation_time: 2.5,
      model_used: 'gpt-4',
      cost: 0.05,
      created_at: '2024-09-12T10:00:00Z'
    },
    title: 'Test Project Documentation'
  };

  beforeEach(() => {
    const pinia = createTestingPinia();
    a11yMocks = createA11yMocks();

    wrapper = mount(DocumentView, {
      global: {
        plugins: [pinia]
      },
      props: {
        document: mockDocument,
        isLoading: false
      }
    });

    notificationStore = useNotificationStore();
    vi.spyOn(notificationStore, 'addSuccess');
    vi.spyOn(notificationStore, 'addError');
  });

  afterEach(() => {
    wrapper.unmount();
    a11yMocks.clearAnnouncements();
  });

  describe('Document Display', () => {
    it('should render document content correctly', () => {
      const content = wrapper.find('[data-testid="document-content"]');
      expect(content.exists()).toBe(true);
      expect(content.html()).toContain('Test Project');
    });

    it('should render metadata when available', () => {
      const metadata = wrapper.find('[data-testid="document-metadata"]');
      expect(metadata.exists()).toBe(true);
      expect(metadata.text()).toContain('gpt-4');
      expect(metadata.text()).toContain('2.5');
    });

    it('should show loading state', async () => {
      await wrapper.setProps({ isLoading: true });

      const loadingIndicator = wrapper.find('[data-testid="loading-indicator"]');
      expect(loadingIndicator.exists()).toBe(true);
      expect(loadingIndicator.text()).toContain('Generating');
    });

    it('should show empty state when no document', async () => {
      await wrapper.setProps({ document: null });

      const emptyState = wrapper.find('[data-testid="empty-state"]');
      expect(emptyState.exists()).toBe(true);
      expect(emptyState.text()).toContain('No document generated yet');
    });
  });

  describe('Accessibility Features', () => {
    it('should have proper ARIA labels', () => {
      const main = wrapper.find('[role="main"]');
      expect(main.exists()).toBe(true);
      expect(main.attributes('aria-label')).toBe('Generated document content');

      const content = wrapper.find('[data-testid="document-content"]');
      expect(content.attributes('aria-live')).toBe('polite');
    });

    it('should announce document updates to screen readers', async () => {
      const newDocument = { ...mockDocument, content: '# Updated Project\n\nUpdated content.' };
      await wrapper.setProps({ document: newDocument });

      await flushPromises();

      const announcements = a11yMocks.getAnnouncements();
      expect(announcements).toContain('polite');
    });

    it('should have keyboard navigation for interactive elements', () => {
      const copyButton = wrapper.find('[data-testid="copy-button"]');
      expect(copyButton.attributes('tabindex')).toBe('0');
      expect(copyButton.attributes('role')).toBe('button');

      const downloadButton = wrapper.find('[data-testid="download-button"]');
      expect(downloadButton.attributes('tabindex')).toBe('0');
      expect(downloadButton.attributes('role')).toBe('button');
    });

    it('should have proper heading structure', () => {
      const headings = wrapper.findAll('h1, h2, h3, h4, h5, h6');
      expect(headings.length).toBeGreaterThan(0);

      // Check that h1 comes before other headings
      const h1 = wrapper.find('h1');
      if (h1.exists()) {
        expect(h1.text()).toContain('Test Project');
      }
    });

    it('should provide alternative text for images', () => {
      // If document contains images, they should have alt text
      const images = wrapper.findAll('img');
      images.forEach(img => {
        expect(img.attributes('alt')).toBeDefined();
      });
    });
  });

  describe('Copy Functionality', () => {
    beforeEach(() => {
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockResolvedValue()
        }
      });
    });

    it('should copy document content to clipboard', async () => {
      const copyButton = wrapper.find('[data-testid="copy-button"]');
      await copyButton.trigger('click');

      await flushPromises();

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockDocument.content);
      expect(notificationStore.addSuccess).toHaveBeenCalledWith(
        'Copied to Clipboard',
        'Document content has been copied to your clipboard.'
      );
    });

    it('should handle copy errors gracefully', async () => {
      navigator.clipboard.writeText.mockRejectedValue(new Error('Clipboard access denied'));

      const copyButton = wrapper.find('[data-testid="copy-button"]');
      await copyButton.trigger('click');

      await flushPromises();

      expect(notificationStore.addError).toHaveBeenCalledWith(
        'Copy Failed',
        'Unable to copy to clipboard. Please try selecting and copying manually.'
      );
    });

    it('should show visual feedback during copy operation', async () => {
      const copyButton = wrapper.find('[data-testid="copy-button"]');

      // Click and check for immediate feedback
      await copyButton.trigger('click');

      // Button should show copied state temporarily
      expect(copyButton.text()).toContain('Copied');

      // Wait for state to reset
      await new Promise(resolve => setTimeout(resolve, 2100));
      await wrapper.vm.$nextTick();

      expect(copyButton.text()).toContain('Copy');
    });
  });

  describe('Download Functionality', () => {
    beforeEach(() => {
      // Mock URL.createObjectURL and URL.revokeObjectURL
      global.URL.createObjectURL = vi.fn(() => 'blob:mock-url');
      global.URL.revokeObjectURL = vi.fn();

      // Mock document.createElement for download
      const mockLink = {
        click: vi.fn(),
        setAttribute: vi.fn(),
        style: {}
      };
      vi.spyOn(document, 'createElement').mockReturnValue(mockLink);
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => {});
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => {});
    });

    it('should download document as markdown file', async () => {
      const downloadButton = wrapper.find('[data-testid="download-button"]');
      await downloadButton.trigger('click');

      expect(document.createElement).toHaveBeenCalledWith('a');
      expect(global.URL.createObjectURL).toHaveBeenCalled();
    });

    it('should use proper filename for download', async () => {
      const downloadButton = wrapper.find('[data-testid="download-button"]');
      await downloadButton.trigger('click');

      const mockLink = document.createElement.mock.results[0].value;
      expect(mockLink.setAttribute).toHaveBeenCalledWith(
        'download',
        expect.stringMatching(/test-project.*\.md/)
      );
    });

    it('should handle download errors gracefully', async () => {
      global.URL.createObjectURL.mockImplementation(() => {
        throw new Error('Blob creation failed');
      });

      const downloadButton = wrapper.find('[data-testid="download-button"]');
      await downloadButton.trigger('click');

      expect(notificationStore.addError).toHaveBeenCalledWith(
        'Download Failed',
        expect.stringContaining('Unable to download')
      );
    });
  });

  describe('Preview Toggle', () => {
    it('should toggle between preview and source view', async () => {
      const toggleButton = wrapper.find('[data-testid="preview-toggle"]');

      // Initially in preview mode
      expect(wrapper.vm.showSource).toBe(false);

      await toggleButton.trigger('click');
      expect(wrapper.vm.showSource).toBe(true);

      const sourceView = wrapper.find('[data-testid="source-view"]');
      expect(sourceView.exists()).toBe(true);
      expect(sourceView.text()).toContain(mockDocument.content);
    });

    it('should announce view changes to screen readers', async () => {
      const toggleButton = wrapper.find('[data-testid="preview-toggle"]');

      await toggleButton.trigger('click');
      await flushPromises();

      const announcements = a11yMocks.getAnnouncements();
      expect(announcements.length).toBeGreaterThan(0);
    });

    it('should maintain proper focus management', async () => {
      const toggleButton = wrapper.find('[data-testid="preview-toggle"]');

      await toggleButton.trigger('focus');
      await toggleButton.trigger('click');

      // Toggle button should maintain focus
      expect(document.activeElement).toBe(toggleButton.element);
    });
  });

  describe('Responsive Design', () => {
    it('should adapt to mobile viewport', async () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      });

      window.dispatchEvent(new Event('resize'));
      await wrapper.vm.$nextTick();

      const container = wrapper.find('[data-testid="document-container"]');
      expect(container.classes()).toContain('mobile-layout');
    });

    it('should stack action buttons vertically on small screens', async () => {
      // Simulate small screen
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 320
      });

      window.dispatchEvent(new Event('resize'));
      await wrapper.vm.$nextTick();

      const actions = wrapper.find('[data-testid="document-actions"]');
      expect(actions.classes()).toContain('flex-col');
    });
  });

  describe('Error Handling', () => {
    it('should handle malformed document content', async () => {
      const malformedDocument = {
        ...mockDocument,
        content: null
      };

      await wrapper.setProps({ document: malformedDocument });

      const errorState = wrapper.find('[data-testid="error-state"]');
      expect(errorState.exists()).toBe(true);
      expect(errorState.text()).toContain('Unable to display document');
    });

    it('should handle missing metadata gracefully', async () => {
      const documentWithoutMeta = {
        content: mockDocument.content,
        title: mockDocument.title
        // No metadata
      };

      await wrapper.setProps({ document: documentWithoutMeta });

      const metadata = wrapper.find('[data-testid="document-metadata"]');
      expect(metadata.exists()).toBe(false);
    });
  });

  describe('Performance', () => {
    it('should not re-render unnecessarily', async () => {
      const renderSpy = vi.spyOn(wrapper.vm, '$forceUpdate');

      // Props that shouldn't trigger re-render
      await wrapper.setProps({
        document: mockDocument, // Same document
        isLoading: false // Same loading state
      });

      expect(renderSpy).not.toHaveBeenCalled();
    });

    it('should handle large documents efficiently', async () => {
      const largeContent = 'Large content line\n'.repeat(10000);
      const largeDocument = {
        ...mockDocument,
        content: largeContent
      };

      const startTime = performance.now();
      await wrapper.setProps({ document: largeDocument });
      const endTime = performance.now();

      // Should render large documents within reasonable time
      expect(endTime - startTime).toBeLessThan(1000);
    });
  });
});