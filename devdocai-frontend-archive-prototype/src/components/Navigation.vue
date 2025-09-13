<template>
  <nav class="bg-white shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-16">
        <div class="flex">
          <div class="flex-shrink-0 flex items-center">
            <h1 class="text-xl font-semibold text-gray-900">DevDocAI</h1>
          </div>
          <div class="hidden sm:ml-6 sm:flex sm:space-x-8">
            <router-link
              v-for="item in navigation"
              :key="item.name"
              :to="item.href"
              class="text-gray-900 inline-flex items-center px-1 pt-1 border-b-2 border-transparent text-sm font-medium hover:text-gray-700 hover:border-gray-300"
              active-class="border-indigo-500 text-gray-900"
            >
              {{ item.name }}
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
const navigation = [
  { name: 'Dashboard', href: '/dashboard' },
  { name: 'Generate', href: '/generate' },
  { name: 'Templates', href: '/templates' },
  { name: 'Tracking', href: '/tracking' },
  { name: 'Review', href: '/review' },
  { name: 'Settings', href: '/settings' }
]
</script>
