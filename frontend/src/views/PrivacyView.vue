<template>
  <div class="p-8">
    <h1 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">{{ title }}</h1>
    <p class="text-gray-600 dark:text-gray-400">This page is coming soon...</p>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';

const route = useRoute();
const title = route.meta?.title || route.name || 'Page';
</script>
