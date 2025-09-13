<template>
  <div v-if="show && document" class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" @click.self="$emit('close')">
    <div class="relative top-4 mx-auto p-6 border w-11/12 max-w-4xl shadow-lg rounded-md bg-white mb-8">
      <!-- Modal Header -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h3 class="text-lg font-bold text-gray-900">Generated Document</h3>
          <p class="text-sm text-gray-600 mt-1">
            {{ document.type.replace('_', ' ').charAt(0).toUpperCase() + document.type.replace('_', ' ').slice(1) }}
            for {{ document.request.project_name }}
          </p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- Document Metadata -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
        <div class="text-center">
          <div class="text-lg font-semibold text-gray-900">
            {{ document.metadata.quality_score ? Math.round(document.metadata.quality_score * 100) + '%' : 'N/A' }}
          </div>
          <div class="text-sm text-gray-500">Quality Score</div>
        </div>
        <div class="text-center">
          <div class="text-lg font-semibold text-gray-900">
            {{ document.metadata.tokens_used || 'N/A' }}
          </div>
          <div class="text-sm text-gray-500">Tokens Used</div>
        </div>
        <div class="text-center">
          <div class="text-lg font-semibold text-gray-900">
            {{ formatCost(document.metadata.cost) }}
          </div>
          <div class="text-sm text-gray-500">Generation Cost</div>
        </div>
      </div>

      <!-- Document Content -->
      <div class="mb-6">
        <div class="flex items-center justify-between mb-2">
          <h4 class="text-md font-medium text-gray-900">Generated Content</h4>
          <div class="flex space-x-2">
            <button
              @click="copyToClipboard"
              class="text-sm text-blue-600 hover:text-blue-700 flex items-center"
            >
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path>
              </svg>
              Copy
            </button>
            <button
              @click="downloadDocument"
              class="text-sm text-green-600 hover:text-green-700 flex items-center"
            >
              <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              Download
            </button>
          </div>
        </div>
        <div class="max-h-96 overflow-y-auto bg-gray-50 p-4 rounded-lg">
          <pre class="whitespace-pre-wrap text-sm text-gray-800 font-mono">{{ document.content }}</pre>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex justify-end space-x-3 pt-4 border-t">
        <button
          @click="$emit('close')"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
        >
          Close
        </button>
        <button
          @click="$emit('generate-new')"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          Generate New Document
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GeneratedDocument } from '@/stores/documents'

// Props and emits
defineProps<{
  show: boolean
  document: GeneratedDocument | null
}>()

const emit = defineEmits<{
  close: []
  'generate-new': []
}>()

// Utility functions
function formatCost(cost?: number): string {
  if (!cost) return 'Free'
  return `$${cost.toFixed(4)}`
}

async function copyToClipboard() {
  const { document: doc } = defineProps<{ document: GeneratedDocument | null }>()
  if (doc?.content) {
    try {
      await navigator.clipboard.writeText(doc.content)
      // Could emit an event to show a notification
      console.log('Content copied to clipboard')
    } catch (err) {
      console.error('Failed to copy to clipboard:', err)
    }
  }
}

function downloadDocument() {
  const { document: doc } = defineProps<{ document: GeneratedDocument | null }>()
  if (doc) {
    const filename = `${doc.request.project_name}-${doc.type}.md`
    const blob = new Blob([doc.content], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }
}
</script>
