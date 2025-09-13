<template>
  <div class="fixed inset-0 z-50 overflow-y-auto" @keydown.esc="close">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-gray-500 bg-opacity-75" @click="close"></div>

    <!-- Search Modal -->
    <div class="flex items-start justify-center min-h-screen pt-16">
      <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full mx-4">
        <!-- Search Input -->
        <div class="border-b border-gray-200 dark:border-gray-700 p-4">
          <div class="flex items-center space-x-3">
            <MagnifyingGlassIcon class="h-5 w-5 text-gray-400" />
            <input
              ref="searchInput"
              v-model="searchQuery"
              type="text"
              class="flex-1 bg-transparent focus:outline-none text-gray-900 dark:text-white"
              placeholder="Search documents, templates, or settings..."
              @input="performSearch"
            />
          </div>
        </div>

        <!-- Search Results -->
        <div class="max-h-96 overflow-y-auto p-4">
          <div v-if="searching" class="text-center py-8">
            <div class="animate-spin h-8 w-8 border-2 border-blue-600 rounded-full border-t-transparent mx-auto"></div>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Searching...</p>
          </div>

          <div v-else-if="results.length > 0" class="space-y-4">
            <div
              v-for="result in results"
              :key="result.id"
              class="p-3 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg cursor-pointer"
              @click="openResult(result)"
            >
              <div class="flex items-start space-x-3">
                <component :is="getIcon(result.type)" class="h-5 w-5 text-gray-400 mt-0.5" />
                <div class="flex-1">
                  <h4 class="text-sm font-medium text-gray-900 dark:text-white">{{ result.title }}</h4>
                  <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ result.description }}</p>
                  <div class="flex items-center space-x-2 mt-2">
                    <span class="text-xs text-gray-400">{{ result.type }}</span>
                    <span class="text-xs text-gray-400">•</span>
                    <span class="text-xs text-gray-400">{{ result.date }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="searchQuery && !searching" class="text-center py-8">
            <p class="text-gray-500 dark:text-gray-400">No results found for "{{ searchQuery }}"</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAppStore } from '@/stores/app';
import { MagnifyingGlassIcon, DocumentTextIcon, CogIcon } from '@heroicons/vue/24/outline';

const router = useRouter();
const appStore = useAppStore();

const searchInput = ref<HTMLInputElement>();
const searchQuery = ref('');
const searching = ref(false);
const results = ref<any[]>([]);

const performSearch = () => {
  if (!searchQuery.value) {
    results.value = [];
    return;
  }

  searching.value = true;

  // Simulate search with mock results
  setTimeout(() => {
    results.value = [
      {
        id: '1',
        title: 'API Documentation',
        description: 'REST API endpoints and authentication guide',
        type: 'document',
        date: '2 hours ago',
        path: '/app/documents/1'
      },
      {
        id: '2',
        title: 'README Template',
        description: 'Standard README template for open source projects',
        type: 'template',
        date: 'Yesterday',
        path: '/app/templates/2'
      }
    ].filter(item =>
      item.title.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      item.description.toLowerCase().includes(searchQuery.value.toLowerCase())
    );
    searching.value = false;
  }, 500);
};

const getIcon = (type: string) => {
  switch (type) {
    case 'document': return DocumentTextIcon;
    case 'template': return DocumentTextIcon;
    case 'settings': return CogIcon;
    default: return DocumentTextIcon;
  }
};

const openResult = (result: any) => {
  router.push(result.path);
  close();
};

const close = () => {
  appStore.showSearch = false;
};

onMounted(() => {
  searchInput.value?.focus();
});
</script>