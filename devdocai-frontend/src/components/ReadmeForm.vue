<template>
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
    <h2 class="text-2xl font-bold mb-6 text-gray-900 dark:text-white">Generate README</h2>

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
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        />
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
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        ></textarea>
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
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        />
        <div v-if="formData.techStack.length > 0" class="mt-2 flex flex-wrap gap-2">
          <span
            v-for="(tech, index) in formData.techStack"
            :key="index"
            class="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
          >
            {{ tech }}
            <button
              type="button"
              @click="removeTechStack(index)"
              class="ml-2 text-blue-600 hover:text-blue-800 dark:text-blue-400"
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
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
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
                class="text-red-500 hover:text-red-700"
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
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
        />
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
          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
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
                class="text-red-500 hover:text-red-700 ml-2"
              >
                Remove
              </button>
            </li>
          </ol>
        </div>
      </div>

      <!-- Submit Button -->
      <div class="flex justify-end">
        <button
          type="submit"
          :disabled="isSubmitting"
          class="px-6 py-3 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {{ isSubmitting ? 'Generating...' : 'Generate README' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';

const emit = defineEmits(['submit']);

const isSubmitting = ref(false);
const techStackInput = ref('');
const featureInput = ref('');
const installationInput = ref('');

const formData = reactive({
  projectName: '',
  description: '',
  techStack: [],
  features: [],
  author: '',
  installationSteps: []
});

const addTechStack = () => {
  const input = techStackInput.value.trim();
  if (input) {
    const techs = input.split(',').map(t => t.trim()).filter(t => t);
    formData.techStack.push(...techs);
    techStackInput.value = '';
  }
};

const removeTechStack = (index) => {
  formData.techStack.splice(index, 1);
};

const addFeature = () => {
  if (featureInput.value.trim()) {
    formData.features.push(featureInput.value.trim());
    featureInput.value = '';
  }
};

const removeFeature = (index) => {
  formData.features.splice(index, 1);
};

const addInstallationStep = () => {
  if (installationInput.value.trim()) {
    formData.installationSteps.push(installationInput.value.trim());
    installationInput.value = '';
  }
};

const removeInstallationStep = (index) => {
  formData.installationSteps.splice(index, 1);
};

const handleSubmit = () => {
  if (!formData.projectName || !formData.description || !formData.author) {
    alert('Please fill in all required fields');
    return;
  }

  isSubmitting.value = true;

  // Convert to API format
  const requestData = {
    project_name: formData.projectName,
    description: formData.description,
    tech_stack: formData.techStack,
    features: formData.features,
    author: formData.author,
    installation_steps: formData.installationSteps.length > 0 ? formData.installationSteps : null
  };

  emit('submit', requestData);

  // Reset submitting state will be handled by parent
  setTimeout(() => {
    isSubmitting.value = false;
  }, 1000);
};
</script>
