<template>
  <div class="card animate-fade-in">
    <div class="mb-6">
      <h2 class="heading-secondary bg-gradient-to-r from-primary-600 to-primary-700 bg-clip-text text-transparent">
        Generate AI-Powered README
      </h2>
      <p class="text-muted mt-1">Fill in your project details to create professional documentation</p>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-6">
      <!-- Project Name -->
      <div>
        <label for="projectName" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Project Name *
        </label>
        <input
          id="projectName"
          v-model="formData.projectName"
          type="text"
          required
          placeholder="e.g., DevDocAI"
          @blur="validateField('projectName')"
          @input="() => touchedFields.projectName && validateField('projectName')"
          :class="[
            'form-input',
            touchedFields.projectName && validationErrors.projectName
              ? 'border-red-500 focus:ring-red-500'
              : ''
          ]"
          data-testid="project-name-input"
        />
        <p v-if="touchedFields.projectName && validationErrors.projectName"
           class="mt-1 text-sm text-red-600 dark:text-red-400"
           data-testid="project-name-error">
          {{ validationErrors.projectName }}
        </p>
      </div>

      <!-- Description -->
      <div>
        <label for="description" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Description *
        </label>
        <textarea
          id="description"
          v-model="formData.description"
          required
          rows="3"
          placeholder="Describe your project in a few sentences..."
          @blur="validateField('description')"
          @input="() => touchedFields.description && validateField('description')"
          :class="[
            'form-input',
            touchedFields.description && validationErrors.description
              ? 'border-red-500 focus:ring-red-500'
              : ''
          ]"
          data-testid="description-input"
        ></textarea>
        <p v-if="touchedFields.description && validationErrors.description"
           class="mt-1 text-sm text-red-600 dark:text-red-400"
           data-testid="description-error">
          {{ validationErrors.description }}
        </p>
      </div>

      <!-- Tech Stack -->
      <div>
        <label for="techStack" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Tech Stack
        </label>
        <input
          id="techStack"
          v-model="techStackInput"
          type="text"
          placeholder="e.g., Python, FastAPI, Vue.js (comma-separated)"
          @keydown.enter.prevent="addTechStack"
          class="form-input"
        />
        <div v-if="formData.techStack.length > 0" class="mt-2 flex flex-wrap gap-2">
          <span
            v-for="(tech, index) in formData.techStack"
            :key="index"
            class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-primary-100 text-primary-800 dark:bg-primary-900 dark:text-primary-200 transition-all hover:scale-105"
          >
            {{ tech }}
            <button
              type="button"
              @click="removeTechStack(index)"
              class="ml-2 text-primary-600 hover:text-primary-800 dark:text-primary-400 transition-colors"
            >
              ×
            </button>
          </span>
        </div>
      </div>

      <!-- Features -->
      <div>
        <label for="features" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Key Features
        </label>
        <input
          id="features"
          v-model="featureInput"
          type="text"
          placeholder="Add a feature and press Enter"
          @keydown.enter.prevent="addFeature"
          class="form-input"
        />
        <div v-if="formData.features.length > 0" class="mt-2">
          <ul class="space-y-1">
            <li
              v-for="(feature, index) in formData.features"
              :key="index"
              class="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded"
            >
              <span class="text-sm text-gray-700 dark:text-gray-300">{{ feature }}</span>
              <button
                type="button"
                @click="removeFeature(index)"
                class="text-red-500 hover:text-red-700 transition-colors"
              >
                Remove
              </button>
            </li>
          </ul>
        </div>
      </div>

      <!-- Author -->
      <div>
        <label for="author" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Author *
        </label>
        <input
          id="author"
          v-model="formData.author"
          type="text"
          required
          placeholder="e.g., John Doe"
          @blur="validateField('author')"
          @input="() => touchedFields.author && validateField('author')"
          :class="[
            'form-input',
            touchedFields.author && validationErrors.author
              ? 'border-red-500 focus:ring-red-500'
              : ''
          ]"
          data-testid="author-input"
        />
        <p v-if="touchedFields.author && validationErrors.author"
           class="mt-1 text-sm text-red-600 dark:text-red-400"
           data-testid="author-error">
          {{ validationErrors.author }}
        </p>
      </div>

      <!-- Installation Steps (Optional) -->
      <div>
        <label for="installation" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Installation Steps (Optional)
        </label>
        <input
          id="installation"
          v-model="installationInput"
          type="text"
          placeholder="Add an installation step and press Enter"
          @keydown.enter.prevent="addInstallationStep"
          class="form-input"
        />
        <div v-if="formData.installationSteps.length > 0" class="mt-2">
          <ol class="space-y-1 list-decimal list-inside">
            <li
              v-for="(step, index) in formData.installationSteps"
              :key="index"
              class="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700 rounded"
            >
              <span class="text-sm text-gray-700 dark:text-gray-300">{{ step }}</span>
              <button
                type="button"
                @click="removeInstallationStep(index)"
                class="text-red-500 hover:text-red-700 ml-2 transition-colors"
              >
                Remove
              </button>
            </li>
          </ol>
        </div>
      </div>

      <!-- Submit Button -->
      <div class="flex justify-end space-x-3">
        <button
          v-if="isSubmitting"
          type="button"
          @click="$emit('cancel')"
          class="btn-ghost"
          data-testid="cancel-button"
        >
          Cancel
        </button>
        <button
          type="button"
          @click="resetForm"
          :disabled="isSubmitting"
          class="btn-ghost"
          data-testid="reset-button"
        >
          <span class="flex items-center gap-2">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Reset
          </span>
        </button>
        <button
          type="submit"
          :disabled="isSubmitting || !isFormValid"
          class="btn-primary group"
          data-testid="submit-button"
        >
          <span class="flex items-center gap-2">
            <svg v-if="!isSubmitting" class="w-5 h-5 group-hover:animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <svg v-else class="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ isSubmitting ? 'Generating...' : 'Generate README' }}
          </span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';
import { useNotificationStore } from '@/stores/notification';

const emit = defineEmits(['submit', 'validation-error', 'cancel']);

const notificationStore = useNotificationStore();

const isSubmitting = ref(false);
const techStackInput = ref('');
const featureInput = ref('');
const installationInput = ref('');

// Form validation state
const validationErrors = reactive({
  projectName: '',
  description: '',
  author: '',
  techStack: '',
  features: ''
});

const formData = reactive({
  projectName: '',
  description: '',
  techStack: [],
  features: [],
  author: '',
  installationSteps: []
});

// Field touched state for showing validation errors
const touchedFields = reactive({
  projectName: false,
  description: false,
  author: false
});

// Validation rules
const validateProjectName = (value) => {
  if (!value || value.trim().length === 0) {
    return 'Project name is required';
  }
  if (value.length < 2) {
    return 'Project name must be at least 2 characters';
  }
  if (value.length > 100) {
    return 'Project name must be less than 100 characters';
  }
  // Check for invalid characters
  if (!/^[a-zA-Z0-9\s\-._]+$/.test(value)) {
    return 'Project name contains invalid characters';
  }
  return '';
};

const validateDescription = (value) => {
  if (!value || value.trim().length === 0) {
    return 'Description is required';
  }
  if (value.length < 10) {
    return 'Description must be at least 10 characters';
  }
  if (value.length > 1000) {
    return 'Description must be less than 1000 characters';
  }
  return '';
};

const validateAuthor = (value) => {
  if (!value || value.trim().length === 0) {
    return 'Author name is required';
  }
  if (value.length < 2) {
    return 'Author name must be at least 2 characters';
  }
  if (value.length > 100) {
    return 'Author name must be less than 100 characters';
  }
  return '';
};

// Real-time validation
const validateField = (fieldName) => {
  touchedFields[fieldName] = true;

  switch (fieldName) {
    case 'projectName':
      validationErrors.projectName = validateProjectName(formData.projectName);
      break;
    case 'description':
      validationErrors.description = validateDescription(formData.description);
      break;
    case 'author':
      validationErrors.author = validateAuthor(formData.author);
      break;
  }
};

// Check if form is valid
const isFormValid = computed(() => {
  return formData.projectName &&
         formData.description &&
         formData.author &&
         !validationErrors.projectName &&
         !validationErrors.description &&
         !validationErrors.author;
});

const addTechStack = () => {
  const input = techStackInput.value.trim();
  if (input) {
    const techs = input.split(',').map(t => t.trim()).filter(t => t);

    // Validate tech stack items
    const invalidTechs = techs.filter(tech => tech.length > 50);
    if (invalidTechs.length > 0) {
      notificationStore.addWarning(
        'Tech Stack Warning',
        'Some technology names are too long and were not added'
      );
      techs.filter(tech => tech.length <= 50);
    }

    // Check for duplicates
    const newTechs = techs.filter(tech => !formData.techStack.includes(tech));
    if (newTechs.length < techs.length) {
      notificationStore.addInfo(
        'Duplicates Ignored',
        'Some technologies were already in the list'
      );
    }

    formData.techStack.push(...newTechs);
    techStackInput.value = '';
    validationErrors.techStack = '';
  }
};

const removeTechStack = (index) => {
  formData.techStack.splice(index, 1);
};

const addFeature = () => {
  const feature = featureInput.value.trim();

  if (!feature) {
    return;
  }

  // Validate feature
  if (feature.length > 200) {
    notificationStore.addWarning(
      'Feature Too Long',
      'Please keep features under 200 characters'
    );
    return;
  }

  // Check for duplicate
  if (formData.features.includes(feature)) {
    notificationStore.addInfo(
      'Duplicate Feature',
      'This feature is already in the list'
    );
    return;
  }

  if (formData.features.length >= 20) {
    notificationStore.addWarning(
      'Feature Limit',
      'Maximum 20 features allowed'
    );
    return;
  }

  formData.features.push(feature);
  featureInput.value = '';
  validationErrors.features = '';
};

const removeFeature = (index) => {
  formData.features.splice(index, 1);
};

const addInstallationStep = () => {
  const step = installationInput.value.trim();

  if (!step) {
    return;
  }

  // Validate installation step
  if (step.length > 300) {
    notificationStore.addWarning(
      'Installation Step Too Long',
      'Please keep installation steps under 300 characters'
    );
    return;
  }

  if (formData.installationSteps.length >= 15) {
    notificationStore.addWarning(
      'Step Limit',
      'Maximum 15 installation steps allowed'
    );
    return;
  }

  formData.installationSteps.push(step);
  installationInput.value = '';
};

const removeInstallationStep = (index) => {
  formData.installationSteps.splice(index, 1);
};

const validateAllFields = () => {
  // Touch all fields to show validation errors
  touchedFields.projectName = true;
  touchedFields.description = true;
  touchedFields.author = true;

  // Validate all fields
  validationErrors.projectName = validateProjectName(formData.projectName);
  validationErrors.description = validateDescription(formData.description);
  validationErrors.author = validateAuthor(formData.author);

  // Check for at least some content
  if (formData.techStack.length === 0 && formData.features.length === 0) {
    validationErrors.techStack = 'Please add at least some tech stack or features';
    validationErrors.features = 'Please add at least some tech stack or features';
    return false;
  }

  return isFormValid.value;
};

const handleSubmit = async () => {
  // Validate all fields
  if (!validateAllFields()) {
    // Collect all errors
    const errors = [];
    if (validationErrors.projectName) errors.push(validationErrors.projectName);
    if (validationErrors.description) errors.push(validationErrors.description);
    if (validationErrors.author) errors.push(validationErrors.author);
    if (validationErrors.techStack) errors.push(validationErrors.techStack);

    notificationStore.addError(
      'Validation Failed',
      errors.join('. ')
    );

    emit('validation-error', errors);
    return;
  }

  isSubmitting.value = true;

  try {
    // Sanitize input data
    const sanitizeString = (str) => {
      if (!str) return '';
      return str
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
        .replace(/<[^>]+>/g, '') // Remove HTML tags
        .trim();
    };

    // Convert to API format with sanitization
    const requestData = {
      project_name: sanitizeString(formData.projectName),
      description: sanitizeString(formData.description),
      tech_stack: formData.techStack.map(sanitizeString),
      features: formData.features.map(sanitizeString),
      author: sanitizeString(formData.author),
      installation_steps: formData.installationSteps.length > 0
        ? formData.installationSteps.map(sanitizeString)
        : []
    };

    emit('submit', requestData);
  } catch (error) {
    notificationStore.addError(
      'Submission Error',
      error.message || 'Failed to prepare form data'
    );
    isSubmitting.value = false;
  }
};

// Reset form
const resetForm = () => {
  formData.projectName = '';
  formData.description = '';
  formData.techStack = [];
  formData.features = [];
  formData.author = '';
  formData.installationSteps = [];

  // Reset validation
  Object.keys(validationErrors).forEach(key => {
    validationErrors[key] = '';
  });

  Object.keys(touchedFields).forEach(key => {
    touchedFields[key] = false;
  });

  techStackInput.value = '';
  featureInput.value = '';
  installationInput.value = '';

  isSubmitting.value = false;
};

// Expose for parent component
defineExpose({
  resetForm,
  isSubmitting
});
</script>
