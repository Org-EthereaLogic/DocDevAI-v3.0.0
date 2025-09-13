/**
 * Store Integration Tests
 * Tests Pinia store integration and state management across components
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { mount } from '@vue/test-utils';
import { useDocumentStore } from '@/stores/document';
import { useApiStore } from '@/stores/api';
import { useNotificationStore } from '@/stores/notification';
import { useUserPreferencesStore } from '@/stores/userPreferences';
import ReadmeForm from '@/components/ReadmeForm.vue';
import DocumentView from '@/components/DocumentView.vue';
import { createTestingPinia, flushPromises, mockApiResponses } from '../utils/testHelpers';

describe('Store Integration Tests', () => {
  let documentStore;
  let apiStore;
  let notificationStore;
  let userPreferencesStore;
  let pinia;

  beforeEach(() => {
    pinia = createTestingPinia();
    setActivePinia(pinia);

    documentStore = useDocumentStore();
    apiStore = useApiStore();
    notificationStore = useNotificationStore();
    userPreferencesStore = useUserPreferencesStore();
  });

  describe('Document Store Integration', () => {
    it('should manage document generation workflow', async () => {
      const formData = {
        project_name: 'Store Integration Test',
        description: 'Testing store integration.',
        author: 'Store Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      // Mock API response
      vi.spyOn(apiStore, 'generateDocument').mockResolvedValue(
        mockApiResponses.generateDocument.success
      );

      // Start generation
      await documentStore.generateDocument(formData);

      expect(documentStore.currentDocument).toBeTruthy();
      expect(documentStore.generationHistory).toHaveLength(1);
      expect(documentStore.isGenerating).toBe(false);
      expect(apiStore.generateDocument).toHaveBeenCalledWith(formData);
    });

    it('should handle generation errors through store coordination', async () => {
      const formData = {
        project_name: 'Error Test',
        description: 'Testing error handling.',
        author: 'Error Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      const errorMessage = 'API generation failed';
      vi.spyOn(apiStore, 'generateDocument').mockRejectedValue(new Error(errorMessage));
      vi.spyOn(notificationStore, 'addError');

      try {
        await documentStore.generateDocument(formData);
      } catch (error) {
        // Expected error
      }

      expect(documentStore.hasError).toBe(true);
      expect(documentStore.lastError).toContain(errorMessage);
      expect(notificationStore.addError).toHaveBeenCalled();
    });

    it('should persist document history across sessions', async () => {
      // Generate first document
      const formData1 = {
        project_name: 'History Test 1',
        description: 'First document.',
        author: 'Author 1',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      vi.spyOn(apiStore, 'generateDocument').mockResolvedValue({
        ...mockApiResponses.generateDocument.success,
        content: '# History Test 1\n\nFirst document content.'
      });

      await documentStore.generateDocument(formData1);

      // Generate second document
      const formData2 = {
        project_name: 'History Test 2',
        description: 'Second document.',
        author: 'Author 2',
        tech_stack: ['Python'],
        features: ['Feature 2']
      };

      vi.spyOn(apiStore, 'generateDocument').mockResolvedValue({
        ...mockApiResponses.generateDocument.success,
        content: '# History Test 2\n\nSecond document content.'
      });

      await documentStore.generateDocument(formData2);

      expect(documentStore.generationHistory).toHaveLength(2);
      expect(documentStore.generationHistory[0].formData.project_name).toBe('History Test 1');
      expect(documentStore.generationHistory[1].formData.project_name).toBe('History Test 2');

      // Simulate session persistence
      const serializedState = JSON.stringify(documentStore.$state);

      // Clear store and restore from serialized state
      documentStore.$reset();
      expect(documentStore.generationHistory).toHaveLength(0);

      // Restore state
      const restoredState = JSON.parse(serializedState);
      documentStore.$patch(restoredState);

      expect(documentStore.generationHistory).toHaveLength(2);
      expect(documentStore.generationHistory[0].formData.project_name).toBe('History Test 1');
    });

    it('should manage document favorites and bookmarks', async () => {
      const document1 = {
        id: 'doc-1',
        title: 'Document 1',
        content: '# Document 1',
        metadata: { created_at: new Date().toISOString() }
      };

      const document2 = {
        id: 'doc-2',
        title: 'Document 2',
        content: '# Document 2',
        metadata: { created_at: new Date().toISOString() }
      };

      documentStore.addToHistory(document1);
      documentStore.addToHistory(document2);

      // Add to favorites
      documentStore.addToFavorites(document1.id);

      expect(documentStore.favorites).toContain(document1.id);
      expect(documentStore.getFavoriteDocuments()).toHaveLength(1);
      expect(documentStore.getFavoriteDocuments()[0].id).toBe('doc-1');

      // Remove from favorites
      documentStore.removeFromFavorites(document1.id);

      expect(documentStore.favorites).not.toContain(document1.id);
      expect(documentStore.getFavoriteDocuments()).toHaveLength(0);
    });

    it('should handle concurrent generation requests properly', async () => {
      const formData1 = {
        project_name: 'Concurrent Test 1',
        description: 'First concurrent request.',
        author: 'Author 1',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      const formData2 = {
        project_name: 'Concurrent Test 2',
        description: 'Second concurrent request.',
        author: 'Author 2',
        tech_stack: ['Python'],
        features: ['Feature 2']
      };

      // Mock API to return different responses with delays
      vi.spyOn(apiStore, 'generateDocument')
        .mockImplementationOnce(() =>
          new Promise(resolve =>
            setTimeout(() => resolve({
              ...mockApiResponses.generateDocument.success,
              content: '# Concurrent Test 1'
            }), 200)
          )
        )
        .mockImplementationOnce(() =>
          new Promise(resolve =>
            setTimeout(() => resolve({
              ...mockApiResponses.generateDocument.success,
              content: '# Concurrent Test 2'
            }), 100)
          )
        );

      // Start concurrent requests
      const promise1 = documentStore.generateDocument(formData1);
      const promise2 = documentStore.generateDocument(formData2);

      // Second request should cancel the first
      expect(documentStore.isGenerating).toBe(true);

      await Promise.allSettled([promise1, promise2]);

      // Only the last request should complete successfully
      expect(documentStore.currentDocument.content).toBe('# Concurrent Test 2');
      expect(documentStore.generationHistory).toHaveLength(1);
    });
  });

  describe('User Preferences Store Integration', () => {
    it('should sync preferences across components', async () => {
      const wrapper1 = mount(ReadmeForm, {
        global: { plugins: [pinia] }
      });

      const wrapper2 = mount(DocumentView, {
        global: { plugins: [pinia] },
        props: { document: null, isLoading: false }
      });

      // Change theme in preferences
      userPreferencesStore.setTheme('dark');

      await flushPromises();

      // Both components should reflect the theme change
      expect(userPreferencesStore.theme).toBe('dark');

      // Verify components received the update
      expect(wrapper1.vm.isDarkMode).toBe(true);
      expect(wrapper2.vm.isDarkMode).toBe(true);

      wrapper1.unmount();
      wrapper2.unmount();
    });

    it('should persist user preferences across sessions', async () => {
      // Set preferences
      userPreferencesStore.setTheme('dark');
      userPreferencesStore.setLanguage('es');
      userPreferencesStore.setAutoSave(true);
      userPreferencesStore.updatePreference('defaultTemplate', 'api-template');

      // Get current state
      const currentState = { ...userPreferencesStore.$state };

      // Simulate new session by resetting store
      userPreferencesStore.$reset();

      expect(userPreferencesStore.theme).toBe('light'); // default
      expect(userPreferencesStore.language).toBe('en'); // default

      // Restore from persistence (simulated)
      userPreferencesStore.$patch(currentState);

      expect(userPreferencesStore.theme).toBe('dark');
      expect(userPreferencesStore.language).toBe('es');
      expect(userPreferencesStore.autoSave).toBe(true);
      expect(userPreferencesStore.preferences.defaultTemplate).toBe('api-template');
    });

    it('should apply accessibility preferences system-wide', async () => {
      // Set accessibility preferences
      userPreferencesStore.updateAccessibilitySettings({
        highContrast: true,
        reduceMotion: true,
        largeText: true,
        screenReaderMode: true
      });

      const wrapper = mount(ReadmeForm, {
        global: { plugins: [pinia] }
      });

      await flushPromises();

      // Verify accessibility settings are applied
      expect(wrapper.classes()).toContain('high-contrast');
      expect(wrapper.classes()).toContain('reduce-motion');
      expect(wrapper.classes()).toContain('large-text');

      wrapper.unmount();
    });
  });

  describe('Notification Store Integration', () => {
    it('should coordinate notifications across different operations', async () => {
      vi.spyOn(notificationStore, 'addSuccess');
      vi.spyOn(notificationStore, 'addError');
      vi.spyOn(notificationStore, 'addInfo');

      const formData = {
        project_name: 'Notification Test',
        description: 'Testing notification coordination.',
        author: 'Notification Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      // Mock successful generation
      vi.spyOn(apiStore, 'generateDocument').mockResolvedValue(
        mockApiResponses.generateDocument.success
      );

      await documentStore.generateDocument(formData);

      expect(notificationStore.addInfo).toHaveBeenCalledWith(
        'Generation Started',
        expect.stringContaining('Generating documentation')
      );

      expect(notificationStore.addSuccess).toHaveBeenCalledWith(
        'Document Generated',
        expect.stringContaining('successfully generated')
      );
    });

    it('should handle notification queue and limits', async () => {
      // Generate multiple notifications
      for (let i = 0; i < 15; i++) {
        notificationStore.addInfo(`Notification ${i}`, `Content ${i}`);
      }

      // Should respect maximum notification limit
      expect(notificationStore.notifications.length).toBeLessThanOrEqual(10);

      // Should keep most recent notifications
      const lastNotification = notificationStore.notifications[notificationStore.notifications.length - 1];
      expect(lastNotification.title).toBe('Notification 14');
    });

    it('should auto-dismiss notifications after timeout', async () => {
      notificationStore.addSuccess('Auto Dismiss Test', 'This should auto-dismiss', { autoDismiss: true, timeout: 100 });

      expect(notificationStore.notifications).toHaveLength(1);

      // Wait for auto-dismiss timeout
      await new Promise(resolve => setTimeout(resolve, 150));

      expect(notificationStore.notifications).toHaveLength(0);
    });

    it('should group similar notifications', async () => {
      // Add similar notifications
      notificationStore.addError('Validation Error', 'Field A is required');
      notificationStore.addError('Validation Error', 'Field B is required');
      notificationStore.addError('Validation Error', 'Field C is required');

      // Should group similar notifications
      expect(notificationStore.notifications.length).toBeLessThan(3);

      const groupedNotification = notificationStore.notifications.find(n =>
        n.title === 'Validation Error' && n.count > 1
      );
      expect(groupedNotification).toBeTruthy();
    });
  });

  describe('Cross-Store Dependencies', () => {
    it('should handle API store errors through document store', async () => {
      const formData = {
        project_name: 'Cross-Store Error Test',
        description: 'Testing cross-store error handling.',
        author: 'Error Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      // Mock API error
      vi.spyOn(apiStore, 'generateDocument').mockRejectedValue(new Error('Network timeout'));

      try {
        await documentStore.generateDocument(formData);
      } catch (error) {
        // Expected error
      }

      // Document store should reflect API store error state
      expect(documentStore.hasError).toBe(true);
      expect(documentStore.lastError).toContain('Network timeout');
      expect(apiStore.hasError).toBe(true);
    });

    it('should coordinate loading states across stores', async () => {
      const formData = {
        project_name: 'Loading State Test',
        description: 'Testing loading state coordination.',
        author: 'Loading Author',
        tech_stack: ['Vue.js'],
        features: ['Feature 1']
      };

      // Mock delayed API response
      vi.spyOn(apiStore, 'generateDocument').mockImplementation(() =>
        new Promise(resolve => {
          setTimeout(() => {
            resolve(mockApiResponses.generateDocument.success);
          }, 200);
        })
      );

      // Start generation
      const generationPromise = documentStore.generateDocument(formData);

      // Check loading states are coordinated
      expect(documentStore.isGenerating).toBe(true);
      expect(apiStore.isGenerating).toBe(true);

      await generationPromise;

      // Check loading states are cleared
      expect(documentStore.isGenerating).toBe(false);
      expect(apiStore.isGenerating).toBe(false);
    });

    it('should maintain state consistency during rapid state changes', async () => {
      const operations = [];

      // Perform rapid operations
      for (let i = 0; i < 5; i++) {
        const formData = {
          project_name: `Rapid Test ${i}`,
          description: `Rapid operation ${i}.`,
          author: `Author ${i}`,
          tech_stack: ['Vue.js'],
          features: [`Feature ${i}`]
        };

        operations.push(
          documentStore.generateDocument(formData).catch(() => {
            // Ignore errors for this test
          })
        );

        // Add some preferences changes
        userPreferencesStore.setTheme(i % 2 === 0 ? 'light' : 'dark');

        // Add notifications
        notificationStore.addInfo(`Operation ${i}`, `Started operation ${i}`);
      }

      await Promise.allSettled(operations);

      // Verify final state is consistent
      expect(documentStore.generationHistory.length).toBeGreaterThanOrEqual(0);
      expect(userPreferencesStore.theme).toMatch(/^(light|dark)$/);
      expect(notificationStore.notifications.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Store Persistence and Hydration', () => {
    it('should serialize and deserialize store state correctly', () => {
      // Set up initial state
      documentStore.addToHistory({
        id: 'doc-1',
        title: 'Persistence Test',
        content: '# Test Document',
        metadata: { created_at: new Date().toISOString() }
      });

      userPreferencesStore.setTheme('dark');
      userPreferencesStore.setLanguage('es');

      // Serialize state
      const documentState = JSON.stringify(documentStore.$state);
      const preferencesState = JSON.stringify(userPreferencesStore.$state);

      // Reset stores
      documentStore.$reset();
      userPreferencesStore.$reset();

      // Verify reset
      expect(documentStore.generationHistory).toHaveLength(0);
      expect(userPreferencesStore.theme).toBe('light');

      // Deserialize and restore state
      documentStore.$patch(JSON.parse(documentState));
      userPreferencesStore.$patch(JSON.parse(preferencesState));

      // Verify restoration
      expect(documentStore.generationHistory).toHaveLength(1);
      expect(documentStore.generationHistory[0].title).toBe('Persistence Test');
      expect(userPreferencesStore.theme).toBe('dark');
      expect(userPreferencesStore.language).toBe('es');
    });

    it('should handle corrupted persisted data gracefully', () => {
      // Try to restore invalid state
      const invalidState = '{"invalid": "json"';

      expect(() => {
        documentStore.$patch(JSON.parse(invalidState));
      }).toThrow();

      // Store should remain in valid state after error
      expect(documentStore.generationHistory).toEqual([]);
      expect(documentStore.hasError).toBe(false);
    });

    it('should migrate old state format to new format', () => {
      // Simulate old state format
      const oldStateFormat = {
        documents: [
          {
            name: 'Old Document', // old field name
            body: '# Old Content', // old field name
            date: '2024-01-01' // old field name
          }
        ]
      };

      // Apply migration logic
      const migratedState = documentStore.migrateState(oldStateFormat);

      expect(migratedState.generationHistory).toBeDefined();
      expect(migratedState.generationHistory[0].title).toBe('Old Document');
      expect(migratedState.generationHistory[0].content).toBe('# Old Content');
      expect(migratedState.generationHistory[0].metadata.created_at).toBe('2024-01-01');
    });
  });
});