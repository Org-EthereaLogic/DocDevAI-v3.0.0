<template>
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
    <!-- Header with actions -->
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Generated README</h2>

      <div class="flex space-x-2">
        <button
          @click="copyToClipboard"
          class="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
        >
          {{ copied ? 'Copied!' : 'Copy' }}
        </button>

        <button
          @click="downloadMarkdown"
          class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors"
        >
          Download
        </button>

        <button
          @click="$emit('reset')"
          class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
        >
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
    setTimeout(() => {
      copied.value = false;
    }, 2000);
  } catch (error) {
    console.error('Failed to copy:', error);
    alert('Failed to copy to clipboard');
  }
};

const downloadMarkdown = () => {
  const blob = new Blob([props.content], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${props.metadata?.project_name || 'README'}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};
</script>

<style>
/* Prose styles for markdown rendering */
.prose h1 {
  @apply text-3xl font-bold mb-4 mt-6;
}

.prose h2 {
  @apply text-2xl font-bold mb-3 mt-5;
}

.prose h3 {
  @apply text-xl font-bold mb-2 mt-4;
}

.prose p {
  @apply mb-4;
}

.prose ul {
  @apply list-disc list-inside mb-4;
}

.prose ol {
  @apply list-decimal list-inside mb-4;
}

.prose li {
  @apply mb-1;
}

.prose code {
  @apply bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm;
}

.prose pre {
  @apply bg-gray-100 dark:bg-gray-900 p-4 rounded-md overflow-x-auto mb-4;
}

.prose pre code {
  @apply bg-transparent p-0;
}

.prose blockquote {
  @apply border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic mb-4;
}

.prose a {
  @apply text-blue-600 dark:text-blue-400 underline;
}

.prose a:hover {
  @apply text-blue-800 dark:text-blue-300;
}

.prose table {
  @apply w-full mb-4;
}

.prose th {
  @apply border border-gray-300 dark:border-gray-600 px-4 py-2 bg-gray-100 dark:bg-gray-800;
}

.prose td {
  @apply border border-gray-300 dark:border-gray-600 px-4 py-2;
}
</style>
