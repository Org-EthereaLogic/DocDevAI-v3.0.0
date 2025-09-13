<template>
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 animate-pulse">
    <!-- Header Skeleton -->
    <div class="flex justify-between items-center mb-6">
      <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/4"></div>
      <div class="flex space-x-2">
        <div class="h-10 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
        <div class="h-10 bg-gray-200 dark:bg-gray-700 rounded w-24"></div>
        <div class="h-10 bg-gray-200 dark:bg-gray-700 rounded w-32"></div>
      </div>
    </div>

    <!-- Metadata Skeleton -->
    <div class="mb-4 p-3 bg-gray-100 dark:bg-gray-700 rounded-md">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div class="h-4 bg-gray-200 dark:bg-gray-600 rounded"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-600 rounded"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-600 rounded"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-600 rounded"></div>
      </div>
    </div>

    <!-- Tab Navigation Skeleton -->
    <div class="mb-4 border-b border-gray-200 dark:border-gray-700">
      <div class="flex space-x-8">
        <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
        <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
      </div>
    </div>

    <!-- Content Skeleton -->
    <div class="space-y-4">
      <!-- Title -->
      <div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>

      <!-- Paragraph Lines -->
      <div class="space-y-2">
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
      </div>

      <!-- Section Header -->
      <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mt-6"></div>

      <!-- List Items -->
      <div class="space-y-2 ml-4">
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-4/5"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6"></div>
      </div>

      <!-- Code Block -->
      <div class="bg-gray-100 dark:bg-gray-900 p-4 rounded-md mt-6">
        <div class="space-y-2">
          <div class="h-3 bg-gray-300 dark:bg-gray-700 rounded w-1/3"></div>
          <div class="h-3 bg-gray-300 dark:bg-gray-700 rounded w-2/3"></div>
          <div class="h-3 bg-gray-300 dark:bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>

      <!-- More Content -->
      <div class="space-y-2 mt-6">
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-4/5"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
// This is a skeleton loader component for document display
// It shows animated placeholders while content is loading
</script>

<style scoped>
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}
</style>
