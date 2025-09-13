<template>
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-gray-900">Template Marketplace</h1>
      <p class="mt-1 text-sm text-gray-600">Browse and download community-created documentation templates</p>
    </div>

    <!-- Search and Filters -->
    <div class="bg-white shadow rounded-lg mb-6">
      <div class="px-4 py-5 sm:p-6">
        <div class="flex space-x-4">
          <div class="flex-1">
            <input
              type="text"
              placeholder="Search templates..."
              class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
          </div>
          <div>
            <select class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
              <option>All Categories</option>
              <option>README</option>
              <option>API Documentation</option>
              <option>User Guides</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- Template Grid -->
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="n in 6" :key="n" class="bg-white overflow-hidden shadow rounded-lg">
        <div class="px-4 py-5 sm:p-6">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-2">
            Sample Template {{ n }}
          </h3>
          <p class="text-sm text-gray-500 mb-4">
            A comprehensive template for documentation projects
          </p>
          <div class="flex items-center justify-between">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
              README
            </span>
            <button class="text-indigo-600 hover:text-indigo-900 text-sm font-medium">
              Download
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// Template marketplace placeholder
</script>
