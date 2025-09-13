/**
 * Unit tests for ReadmeForm component
 * Tests validation, error handling, and form submission
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createTestingPinia } from '../../setup';
import ReadmeForm from '@/components/ReadmeForm.vue';
import { useNotificationStore } from '@/stores/notification';
import {
  mockFormData,
  fillForm,
  submitForm,
  triggerValidation,
  flushPromises
} from '@/utils/testHelpers';

describe('ReadmeForm', () => {
  let wrapper;
  let notificationStore;

  beforeEach(() => {
    const pinia = createTestingPinia();

    wrapper = mount(ReadmeForm, {
      global: {
        plugins: [pinia]
      }
    });

    notificationStore = useNotificationStore();
    vi.spyOn(notificationStore, 'addError');
    vi.spyOn(notificationStore, 'addWarning');
    vi.spyOn(notificationStore, 'addInfo');
  });

  afterEach(() => {
    wrapper.unmount();
  });

  describe('Form Validation', () => {
    it('should show validation error for empty project name', async () => {
      const input = wrapper.find('[data-testid="project-name-input"]');
      await input.setValue('');
      await input.trigger('blur');

      await wrapper.vm.$nextTick();

      const error = wrapper.find('[data-testid="project-name-error"]');
      expect(error.exists()).toBe(true);
      expect(error.text()).toContain('Project name is required');
    });

    it('should show validation error for short project name', async () => {
      const input = wrapper.find('[data-testid="project-name-input"]');
      await input.setValue('A');
      await input.trigger('blur');

      await wrapper.vm.$nextTick();

      const error = wrapper.find('[data-testid="project-name-error"]');
      expect(error.exists()).toBe(true);
      expect(error.text()).toContain('at least 2 characters');
    });

    it('should show validation error for invalid characters in project name', async () => {
      const input = wrapper.find('[data-testid="project-name-input"]');
      await input.setValue('Project@#$%');
      await input.trigger('blur');

      await wrapper.vm.$nextTick();

      const error = wrapper.find('[data-testid="project-name-error"]');
      expect(error.exists()).toBe(true);
      expect(error.text()).toContain('invalid characters');
    });

    it('should validate description length', async () => {
      const textarea = wrapper.find('[data-testid="description-input"]');

      // Too short
      await textarea.setValue('Short');
      await textarea.trigger('blur');
      await wrapper.vm.$nextTick();

      let error = wrapper.find('[data-testid="description-error"]');
      expect(error.exists()).toBe(true);
      expect(error.text()).toContain('at least 10 characters');

      // Valid length
      await textarea.setValue('This is a valid description for the project');
      await textarea.trigger('blur');
      await wrapper.vm.$nextTick();

      error = wrapper.find('[data-testid="description-error"]');
      expect(error.exists()).toBe(false);
    });

    it('should validate author name', async () => {
      const input = wrapper.find('[data-testid="author-input"]');

      // Empty
      await input.setValue('');
      await input.trigger('blur');
      await wrapper.vm.$nextTick();

      let error = wrapper.find('[data-testid="author-error"]');
      expect(error.exists()).toBe(true);
      expect(error.text()).toContain('Author name is required');

      // Too short
      await input.setValue('A');
      await input.trigger('blur');
      await wrapper.vm.$nextTick();

      error = wrapper.find('[data-testid="author-error"]');
      expect(error.exists()).toBe(true);
      expect(error.text()).toContain('at least 2 characters');
    });

    it('should require at least some tech stack or features', async () => {
      // Fill required fields but leave tech stack and features empty
      await fillForm(wrapper, {
        'project-name': 'Test Project',
        'description': 'This is a test description',
        'author': 'Test Author'
      });

      const submitButton = wrapper.find('[data-testid="submit-button"]');
      await submitButton.trigger('click');

      await flushPromises();

      expect(notificationStore.addError).toHaveBeenCalledWith(
        'Validation Failed',
        expect.stringContaining('tech stack or features')
      );
    });
  });

  describe('Input Sanitization', () => {
    it('should sanitize XSS attempts in project name', async () => {
      const maliciousData = mockFormData.malicious;

      await fillForm(wrapper, {
        'project-name': maliciousData.projectName,
        'description': 'Valid description for testing',
        'author': 'Valid Author'
      });

      // Add some tech stack
      const techInput = wrapper.vm;
      techInput.formData.techStack = ['Python'];

      const emitSpy = vi.spyOn(wrapper.vm, '$emit');
      await submitForm(wrapper);

      expect(emitSpy).toHaveBeenCalledWith('submit', expect.objectContaining({
        project_name: expect.not.stringContaining('<script>'),
        project_name: expect.not.stringContaining('alert')
      }));
    });

    it('should remove HTML tags from all fields', async () => {
      await fillForm(wrapper, {
        'project-name': 'Project <b>Name</b>',
        'description': 'Description with <em>emphasis</em> tags',
        'author': 'Author <span>Name</span>'
      });

      // Add tech stack
      wrapper.vm.formData.techStack = ['<div>Python</div>'];

      const emitSpy = vi.spyOn(wrapper.vm, '$emit');
      await submitForm(wrapper);

      expect(emitSpy).toHaveBeenCalledWith('submit', expect.objectContaining({
        project_name: 'Project Name',
        description: 'Description with emphasis tags',
        author: 'Author Name',
        tech_stack: ['Python']
      }));
    });
  });

  describe('Form Submission', () => {
    it('should emit submit event with valid data', async () => {
      const validData = mockFormData.valid;

      await fillForm(wrapper, {
        'project-name': validData.projectName,
        'description': validData.description,
        'author': validData.author
      });

      // Add tech stack and features
      wrapper.vm.formData.techStack = validData.techStack;
      wrapper.vm.formData.features = validData.features;

      const emitSpy = vi.spyOn(wrapper.vm, '$emit');
      await submitForm(wrapper);

      expect(emitSpy).toHaveBeenCalledWith('submit', expect.objectContaining({
        project_name: validData.projectName,
        description: validData.description,
        author: validData.author,
        tech_stack: validData.techStack,
        features: validData.features
      }));
    });

    it('should disable submit button when form is invalid', async () => {
      const submitButton = wrapper.find('[data-testid="submit-button"]');

      // Initially disabled (empty form)
      expect(submitButton.attributes('disabled')).toBeDefined();

      // Fill with invalid data
      await fillForm(wrapper, {
        'project-name': 'A', // Too short
        'description': 'Short', // Too short
        'author': '' // Empty
      });

      await wrapper.vm.$nextTick();
      expect(submitButton.attributes('disabled')).toBeDefined();
    });

    it('should disable submit button while submitting', async () => {
      const validData = mockFormData.valid;

      await fillForm(wrapper, {
        'project-name': validData.projectName,
        'description': validData.description,
        'author': validData.author
      });

      wrapper.vm.formData.techStack = validData.techStack;

      const submitButton = wrapper.find('[data-testid="submit-button"]');

      // Set submitting state
      wrapper.vm.isSubmitting = true;
      await wrapper.vm.$nextTick();

      expect(submitButton.attributes('disabled')).toBeDefined();
      expect(submitButton.text()).toContain('Generating...');
    });
  });

  describe('Tech Stack Management', () => {
    it('should add tech stack items', async () => {
      wrapper.vm.techStackInput = 'Python, JavaScript, Vue.js';
      wrapper.vm.addTechStack();

      expect(wrapper.vm.formData.techStack).toEqual(['Python', 'JavaScript', 'Vue.js']);
    });

    it('should prevent duplicate tech stack items', async () => {
      wrapper.vm.formData.techStack = ['Python'];
      wrapper.vm.techStackInput = 'Python, JavaScript';
      wrapper.vm.addTechStack();

      expect(wrapper.vm.formData.techStack).toEqual(['Python', 'JavaScript']);
      expect(notificationStore.addInfo).toHaveBeenCalledWith(
        'Duplicates Ignored',
        expect.any(String)
      );
    });

    it('should warn about tech stack items that are too long', async () => {
      const longTech = 'A'.repeat(51); // Over 50 characters
      wrapper.vm.techStackInput = longTech;
      wrapper.vm.addTechStack();

      expect(notificationStore.addWarning).toHaveBeenCalledWith(
        'Tech Stack Warning',
        expect.stringContaining('too long')
      );
    });

    it('should remove tech stack items', async () => {
      wrapper.vm.formData.techStack = ['Python', 'JavaScript', 'Vue.js'];
      wrapper.vm.removeTechStack(1);

      expect(wrapper.vm.formData.techStack).toEqual(['Python', 'Vue.js']);
    });
  });

  describe('Features Management', () => {
    it('should add features', async () => {
      wrapper.vm.featureInput = 'AI-powered generation';
      wrapper.vm.addFeature();

      expect(wrapper.vm.formData.features).toContain('AI-powered generation');
    });

    it('should prevent duplicate features', async () => {
      wrapper.vm.formData.features = ['Feature 1'];
      wrapper.vm.featureInput = 'Feature 1';
      wrapper.vm.addFeature();

      expect(wrapper.vm.formData.features).toHaveLength(1);
      expect(notificationStore.addInfo).toHaveBeenCalledWith(
        'Duplicate Feature',
        expect.any(String)
      );
    });

    it('should limit number of features to 20', async () => {
      // Add 20 features
      for (let i = 0; i < 20; i++) {
        wrapper.vm.formData.features.push(`Feature ${i + 1}`);
      }

      wrapper.vm.featureInput = 'Feature 21';
      wrapper.vm.addFeature();

      expect(wrapper.vm.formData.features).toHaveLength(20);
      expect(notificationStore.addWarning).toHaveBeenCalledWith(
        'Feature Limit',
        expect.stringContaining('Maximum 20')
      );
    });
  });

  describe('Form Reset', () => {
    it('should reset all form fields', async () => {
      // Fill form with data
      await fillForm(wrapper, mockFormData.valid);
      wrapper.vm.formData.techStack = ['Python'];
      wrapper.vm.formData.features = ['Feature 1'];

      // Reset form
      wrapper.vm.resetForm();

      expect(wrapper.vm.formData.projectName).toBe('');
      expect(wrapper.vm.formData.description).toBe('');
      expect(wrapper.vm.formData.author).toBe('');
      expect(wrapper.vm.formData.techStack).toEqual([]);
      expect(wrapper.vm.formData.features).toEqual([]);
      expect(wrapper.vm.isSubmitting).toBe(false);
    });

    it('should clear validation errors on reset', async () => {
      // Trigger validation errors
      await triggerValidation(wrapper, 'project-name');
      await triggerValidation(wrapper, 'description');
      await triggerValidation(wrapper, 'author');

      // Reset form
      wrapper.vm.resetForm();

      expect(wrapper.vm.validationErrors.projectName).toBe('');
      expect(wrapper.vm.validationErrors.description).toBe('');
      expect(wrapper.vm.validationErrors.author).toBe('');
    });
  });

  describe('Error Handling', () => {
    it('should emit validation-error event on validation failure', async () => {
      const emitSpy = vi.spyOn(wrapper.vm, '$emit');

      // Try to submit with invalid data
      await submitForm(wrapper);

      expect(emitSpy).toHaveBeenCalledWith(
        'validation-error',
        expect.any(Array)
      );
    });

    it('should handle submission errors gracefully', async () => {
      // Fill valid data
      await fillForm(wrapper, mockFormData.valid);
      wrapper.vm.formData.techStack = ['Python'];

      // Mock an error during submission
      const error = new Error('Network error');
      wrapper.vm.$emit = vi.fn().mockImplementation(() => {
        throw error;
      });

      await submitForm(wrapper);

      expect(notificationStore.addError).toHaveBeenCalled();
      expect(wrapper.vm.isSubmitting).toBe(false);
    });
  });

  describe('Cancel Functionality', () => {
    it('should show cancel button when submitting', async () => {
      wrapper.vm.isSubmitting = true;
      await wrapper.vm.$nextTick();

      const cancelButton = wrapper.find('[data-testid="cancel-button"]');
      expect(cancelButton.exists()).toBe(true);
    });

    it('should emit cancel event when cancel button is clicked', async () => {
      wrapper.vm.isSubmitting = true;
      await wrapper.vm.$nextTick();

      const emitSpy = vi.spyOn(wrapper.vm, '$emit');
      const cancelButton = wrapper.find('[data-testid="cancel-button"]');
      await cancelButton.trigger('click');

      expect(emitSpy).toHaveBeenCalledWith('cancel');
    });
  });
});
