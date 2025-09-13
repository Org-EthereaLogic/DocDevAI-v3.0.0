<template>
  <div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
    <!-- Navigation -->
    <nav class="container mx-auto px-6 py-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <div class="h-8 w-8 bg-blue-600 rounded-lg"></div>
          <span class="text-xl font-bold text-gray-900 dark:text-white">DevDocAI</span>
        </div>
        <div class="flex items-center space-x-6">
          <router-link to="/app/dashboard" class="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
            Dashboard
          </router-link>
          <router-link to="/app/documents" class="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
            Documents
          </router-link>
          <router-link to="/app/dashboard" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            Get Started
          </router-link>
        </div>
      </div>
    </nav>

    <!-- Hero Section -->
    <div class="container mx-auto px-6 py-24">
      <div class="text-center max-w-4xl mx-auto">
        <h1 class="text-5xl font-bold text-gray-900 dark:text-white mb-6">
          AI-Powered Documentation
          <span class="text-blue-600">Made Simple</span>
        </h1>
        <p class="text-xl text-gray-600 dark:text-gray-300 mb-8">
          Generate professional documentation with the power of AI. Save time, maintain consistency, and focus on what matters most - building great software.
        </p>
        <div class="flex items-center justify-center space-x-4">
          <router-link to="/app/dashboard" class="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-lg font-medium">
            Start Generating
          </router-link>
          <router-link to="/app/help" class="px-6 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 text-lg font-medium">
            Learn More
          </router-link>
        </div>
      </div>
    </div>

    <!-- Features -->
    <div class="container mx-auto px-6 py-24">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="bg-white dark:bg-gray-800 rounded-xl p-8 shadow-lg">
          <div class="h-12 w-12 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center mb-4">
            <SparklesIcon class="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">AI-Powered</h3>
          <p class="text-gray-600 dark:text-gray-300">
            Leverage GPT-4, Claude, and Gemini to generate high-quality documentation automatically.
          </p>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-xl p-8 shadow-lg">
          <div class="h-12 w-12 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center mb-4">
            <ShieldCheckIcon class="h-6 w-6 text-green-600 dark:text-green-400" />
          </div>
          <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">Privacy-First</h3>
          <p class="text-gray-600 dark:text-gray-300">
            Your data stays local. No telemetry, no tracking. Full control over your documentation.
          </p>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-xl p-8 shadow-lg">
          <div class="h-12 w-12 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center mb-4">
            <BoltIcon class="h-6 w-6 text-purple-600 dark:text-purple-400" />
          </div>
          <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">Blazing Fast</h3>
          <p class="text-gray-600 dark:text-gray-300">
            Generate complete documentation suites in seconds with optimized performance.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { SparklesIcon, ShieldCheckIcon, BoltIcon } from '@heroicons/vue/24/outline';
</script>