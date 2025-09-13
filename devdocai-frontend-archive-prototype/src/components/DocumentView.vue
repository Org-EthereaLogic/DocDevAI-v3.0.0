<template>
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
    <!-- Header with actions -->
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Generated README</h2>

      <div class="flex space-x-2">
        <button
          @click="copyToClipboard"
          class="inline-flex items-center px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-all duration-200"
          :class="{ 'bg-green-600 hover:bg-green-700': copied }"
        >
          <svg v-if="!copied" class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <svg v-else class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
          {{ copied ? 'Copied!' : 'Copy to Clipboard' }}
        </button>

        <button
          @click="downloadMarkdown"
          class="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download .md
        </button>

        <button
          @click="$emit('reset')"
          class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
        >
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Generate Another
        </button>
      </div>
    </div>

    <!-- Metadata -->
    <div v-if="metadata" class="mb-4 p-3 bg-gray-100 dark:bg-gray-700 rounded-md">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <span class="font-medium text-gray-600 dark:text-gray-400">Generation Time:</span>
          <span class="ml-2 text-gray-900 dark:text-white">{{ formatTime(metadata.generation_time) }}</span>
        </div>
        <div v-if="metadata.model_used">
          <span class="font-medium text-gray-600 dark:text-gray-400">Model:</span>
          <span class="ml-2 text-gray-900 dark:text-white">{{ metadata.model_used }}</span>
        </div>
        <div v-if="metadata.cached !== undefined">
          <span class="font-medium text-gray-600 dark:text-gray-400">From Cache:</span>
          <span class="ml-2 text-gray-900 dark:text-white">{{ metadata.cached ? 'Yes' : 'No' }}</span>
        </div>
        <div v-if="metadata.cost">
          <span class="font-medium text-gray-600 dark:text-gray-400">Cost:</span>
          <span class="ml-2 text-gray-900 dark:text-white">${{ metadata.cost.toFixed(3) }}</span>
        </div>
      </div>
    </div>

    <!-- Tab Toggle -->
    <div class="mb-4 border-b border-gray-200 dark:border-gray-700">
      <nav class="-mb-px flex space-x-8">
        <button
          @click="activeTab = 'preview'"
          :class="[
            'py-2 px-1 border-b-2 font-medium text-sm transition-colors',
            activeTab === 'preview'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
          ]"
        >
          Preview
        </button>
        <button
          @click="activeTab = 'markdown'"
          :class="[
            'py-2 px-1 border-b-2 font-medium text-sm transition-colors',
            activeTab === 'markdown'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
          ]"
        >
          Markdown
        </button>
      </nav>
    </div>

    <!-- Content -->
    <div class="markdown-content">
      <!-- Preview Tab -->
      <div v-if="activeTab === 'preview'" class="prose prose-lg dark:prose-invert max-w-none" v-html="renderedHtml"></div>

      <!-- Markdown Tab -->
      <div v-if="activeTab === 'markdown'">
        <pre class="bg-gray-100 dark:bg-gray-900 p-4 rounded-md overflow-x-auto">
          <code class="text-sm text-gray-800 dark:text-gray-200">{{ content }}</code>
        </pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { marked } from 'marked';

const props = defineProps({
  content: {
    type: String,
    required: true
  },
  metadata: {
    type: Object,
    default: () => ({})
  }
});

const emit = defineEmits(['reset']);

const activeTab = ref('preview');
const copied = ref(false);

// Configure marked options
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: true,
  mangle: false,
  sanitize: false
});

const renderedHtml = computed(() => {
  try {
    return marked(props.content);
  } catch (error) {
    console.error('Error rendering markdown:', error);
    return '<p>Error rendering markdown content</p>';
  }
});

const formatTime = (seconds) => {
  if (!seconds) return 'N/A';
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = (seconds % 60).toFixed(0);
  return `${minutes}m ${remainingSeconds}s`;
};

const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.content);
    copied.value = true;

    // Show success feedback
    const successMessage = document.createElement('div');
    successMessage.className = 'fixed top-4 right-4 z-50 px-4 py-2 bg-green-600 text-white rounded-lg shadow-lg transform transition-all duration-300 translate-x-0';
    successMessage.textContent = 'Document copied to clipboard!';
    document.body.appendChild(successMessage);

    // Animate in
    setTimeout(() => {
      successMessage.style.opacity = '0';
      successMessage.style.transform = 'translateX(100%)';
    }, 2000);

    // Remove from DOM
    setTimeout(() => {
      document.body.removeChild(successMessage);
      copied.value = false;
    }, 2500);

  } catch (error) {
    console.error('Failed to copy:', error);

    // Show error feedback
    const errorMessage = document.createElement('div');
    errorMessage.className = 'fixed top-4 right-4 z-50 px-4 py-2 bg-red-600 text-white rounded-lg shadow-lg';
    errorMessage.textContent = 'Failed to copy to clipboard';
    document.body.appendChild(errorMessage);

    setTimeout(() => {
      document.body.removeChild(errorMessage);
    }, 3000);
  }
};

const downloadMarkdown = () => {
  try {
    const blob = new Blob([props.content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().split('T')[0];
    const projectName = props.metadata?.project_name || 'README';
    const sanitizedName = projectName.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    a.download = `${sanitizedName}_${timestamp}.md`;

    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // Show download success feedback
    const successMessage = document.createElement('div');
    successMessage.className = 'fixed top-4 right-4 z-50 px-4 py-2 bg-blue-600 text-white rounded-lg shadow-lg transform transition-all duration-300';
    successMessage.textContent = `Downloaded: ${a.download}`;
    document.body.appendChild(successMessage);

    setTimeout(() => {
      successMessage.style.opacity = '0';
      successMessage.style.transform = 'translateX(100%)';
    }, 2000);

    setTimeout(() => {
      document.body.removeChild(successMessage);
    }, 2500);

  } catch (error) {
    console.error('Failed to download:', error);

    // Show error feedback
    const errorMessage = document.createElement('div');
    errorMessage.className = 'fixed top-4 right-4 z-50 px-4 py-2 bg-red-600 text-white rounded-lg shadow-lg';
    errorMessage.textContent = 'Failed to download document';
    document.body.appendChild(errorMessage);

    setTimeout(() => {
      document.body.removeChild(errorMessage);
    }, 3000);
  }
};
</script>

<style>
/* Prose styles for markdown rendering */
.prose h1 {
  font-size: 1.875rem;
  font-weight: 700;
  margin-bottom: 1rem;
  margin-top: 1.5rem;
}

.prose h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  margin-top: 1.25rem;
}

.prose h3 {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  margin-top: 1rem;
}

.prose p {
  margin-bottom: 1rem;
}

.prose ul {
  list-style-type: disc;
  list-style-position: inside;
  margin-bottom: 1rem;
}

.prose ol {
  list-style-type: decimal;
  list-style-position: inside;
  margin-bottom: 1rem;
}

.prose li {
  margin-bottom: 0.25rem;
}

.prose code {
  background-color: rgb(243 244 246);
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875rem;
}

.dark .prose code {
  background-color: rgb(31 41 55);
}

.prose pre {
  background-color: rgb(243 244 246);
  padding: 1rem;
  border-radius: 0.375rem;
  overflow-x: auto;
  margin-bottom: 1rem;
}

.dark .prose pre {
  background-color: rgb(17 24 39);
}

.prose pre code {
  background-color: transparent;
  padding: 0;
}

.prose blockquote {
  border-left: 4px solid rgb(209 213 219);
  padding-left: 1rem;
  font-style: italic;
  margin-bottom: 1rem;
}

.dark .prose blockquote {
  border-left-color: rgb(75 85 99);
}

.prose a {
  color: rgb(37 99 235);
  text-decoration: underline;
}

.dark .prose a {
  color: rgb(96 165 250);
}

.prose a:hover {
  color: rgb(29 78 216);
}

.dark .prose a:hover {
  color: rgb(147 197 253);
}

.prose table {
  width: 100%;
  margin-bottom: 1rem;
}

.prose th {
  border: 1px solid rgb(209 213 219);
  padding: 0.5rem 1rem;
  background-color: rgb(243 244 246);
}

.dark .prose th {
  border-color: rgb(75 85 99);
  background-color: rgb(31 41 55);
}

.prose td {
  border: 1px solid rgb(209 213 219);
  padding: 0.5rem 1rem;
}

.dark .prose td {
  border-color: rgb(75 85 99);
}
</style>
