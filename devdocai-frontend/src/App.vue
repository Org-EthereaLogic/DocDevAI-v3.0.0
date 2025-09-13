<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Header -->
    <header class="bg-white dark:bg-gray-800 shadow-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center">
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
              DevDocAI
            </h1>
            <span class="ml-3 text-sm text-gray-500 dark:text-gray-400">v3.0.0</span>
          </div>

          <div class="flex items-center space-x-4">
            <span v-if="apiStatus" class="text-sm">
              <span class="inline-block w-2 h-2 rounded-full mr-2"
                    :class="apiStatus === 'healthy' ? 'bg-green-500' : 'bg-red-500'"></span>
              API {{ apiStatus === 'healthy' ? 'Connected' : 'Disconnected' }}
            </span>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Status/Error Messages -->
      <div v-if="errorMessage" class="mb-6">
        <div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <h3 class="text-sm font-medium">Error</h3>
              <p class="text-sm mt-1">{{ errorMessage }}</p>
              <button
                @click="errorMessage = null"
                class="mt-2 text-sm text-red-600 hover:text-red-500"
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Success Message -->
      <div v-if="successMessage" class="mb-6">
        <div class="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-md">
          <div class="flex">
            <div class="flex-shrink-0">
              <svg class="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </div>
            <div class="ml-3">
              <p class="text-sm font-medium">{{ successMessage }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Interface -->
      <div v-if="!isLoading && !generatedDocument">
        <!-- Introduction -->
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">
          <h2 class="text-xl font-semibold mb-3 text-gray-900 dark:text-white">
            AI-Powered Documentation Generator
          </h2>
          <p class="text-gray-600 dark:text-gray-400">
            Generate professional README documentation for your project using AI.
            Simply fill in the form below with your project details, and our AI will create
            comprehensive documentation in seconds.
          </p>
          <div class="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
            <p class="text-sm text-blue-700 dark:text-blue-300">
              <strong>Note:</strong> Generation typically takes 60-90 seconds as we use advanced AI models
              to create high-quality, contextual documentation tailored to your project.
            </p>
          </div>
        </div>

        <!-- Form -->
        <ReadmeForm @submit="handleFormSubmit" />
      </div>

      <!-- Loading State -->
      <div v-else-if="isLoading" class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-8">
        <LoadingSpinner
          :message="loadingMessage"
          :sub-message="loadingSubMessage"
          :show-timer="true"
        />
      </div>

      <!-- Generated Document -->
      <div v-else-if="generatedDocument">
        <DocumentView
          :content="generatedDocument"
          :metadata="documentMetadata"
          @reset="resetForm"
        />
      </div>
    </main>

    <!-- Footer -->
    <footer class="mt-auto bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <p class="text-center text-sm text-gray-500 dark:text-gray-400">
          DevDocAI v3.0.0 - AI-Powered Documentation for Solo Developers
        </p>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import ReadmeForm from './components/ReadmeForm.vue';
import DocumentView from './components/DocumentView.vue';
import LoadingSpinner from './components/LoadingSpinner.vue';
import { documentAPI } from './services/api';

// State
const isLoading = ref(false);
const generatedDocument = ref(null);
const documentMetadata = ref(null);
const errorMessage = ref(null);
const successMessage = ref(null);
const apiStatus = ref(null);
const loadingMessage = ref('Generating your README...');
const loadingSubMessage = ref('Our AI is crafting professional documentation for your project');

// Check API health on mount
onMounted(async () => {
  try {
    const health = await documentAPI.healthCheck();
    apiStatus.value = health.status;
  } catch (error) {
    apiStatus.value = 'error';
    console.error('API health check failed:', error);
  }
});

// Handle form submission
const handleFormSubmit = async (formData) => {
  errorMessage.value = null;
  successMessage.value = null;
  isLoading.value = true;

  // Update loading messages based on generation phase
  const updateLoadingMessage = () => {
    const messages = [
      { time: 10, message: 'Analyzing project requirements...', sub: 'Understanding your project context' },
      { time: 25, message: 'Generating documentation structure...', sub: 'Creating optimal document layout' },
      { time: 40, message: 'Writing comprehensive content...', sub: 'Adding detailed sections and examples' },
      { time: 55, message: 'Finalizing and optimizing...', sub: 'Polishing the documentation' },
      { time: 70, message: 'Almost there...', sub: 'Final quality checks' }
    ];

    let elapsed = 0;
    const interval = setInterval(() => {
      elapsed += 5;
      const message = messages.find(m => elapsed >= m.time && elapsed < m.time + 15);
      if (message) {
        loadingMessage.value = message.message;
        loadingSubMessage.value = message.sub;
      }
    }, 5000);

    return interval;
  };

  const messageInterval = updateLoadingMessage();

  try {
    console.log('Submitting form data:', formData);

    const response = await documentAPI.generateReadme(formData);

    console.log('API Response:', response);

    if (response.success && response.content) {
      generatedDocument.value = response.content;
      documentMetadata.value = response.metadata;
      successMessage.value = 'README generated successfully!';

      // Clear success message after 5 seconds
      setTimeout(() => {
        successMessage.value = null;
      }, 5000);
    } else {
      throw new Error(response.error || 'Failed to generate document');
    }
  } catch (error) {
    console.error('Generation error:', error);
    errorMessage.value = error.message || 'An error occurred while generating the document. Please try again.';
    generatedDocument.value = null;
  } finally {
    isLoading.value = false;
    clearInterval(messageInterval);
    // Reset loading messages
    loadingMessage.value = 'Generating your README...';
    loadingSubMessage.value = 'Our AI is crafting professional documentation for your project';
  }
};

// Reset form
const resetForm = () => {
  generatedDocument.value = null;
  documentMetadata.value = null;
  errorMessage.value = null;
  successMessage.value = null;
};
</script>

<style>
/* Add any global styles here */
</style>
