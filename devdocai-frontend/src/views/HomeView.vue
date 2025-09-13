<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Header -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-6">
          <div class="flex items-center">
            <h1 class="text-3xl font-bold text-gray-900">DevDocAI</h1>
            <span class="ml-2 px-2 py-1 text-xs font-medium bg-primary-100 text-primary-800 rounded-full">
              v3.6.0
            </span>
          </div>
          <nav>
            <router-link
              to="/dashboard"
              class="btn-primary"
            >
              Go to Dashboard
            </router-link>
          </nav>
        </div>
      </div>
    </header>

    <!-- Hero Section -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div class="text-center">
        <h2 class="text-4xl font-extrabold text-gray-900 sm:text-6xl">
          AI-Powered
          <span class="text-primary-600">Documentation</span>
        </h2>
        <p class="mt-6 text-xl text-gray-500 max-w-3xl mx-auto">
          DevDocAI v3.6.0 brings intelligent documentation generation with enhanced UX,
          accessibility features, and comprehensive AI integration for solo developers.
        </p>

        <div class="mt-10 flex justify-center space-x-6">
          <router-link to="/dashboard" class="btn-primary text-lg px-8 py-3">
            Get Started
          </router-link>
          <button class="btn-secondary text-lg px-8 py-3">
            Learn More
          </button>
        </div>
      </div>

      <!-- Features Grid -->
      <div class="mt-20 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div class="card">
          <div class="card-body text-center">
            <div class="w-12 h-12 bg-primary-100 rounded-lg mx-auto mb-4 flex items-center justify-center">
              <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">AI Document Generation</h3>
            <p class="text-gray-600">Generate comprehensive documentation using advanced AI models with MIAIR optimization.</p>
          </div>
        </div>

        <div class="card">
          <div class="card-body text-center">
            <div class="w-12 h-12 bg-success-100 rounded-lg mx-auto mb-4 flex items-center justify-center">
              <svg class="w-6 h-6 text-success-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Smart Analytics</h3>
            <p class="text-gray-600">Track documentation quality and dependencies with interactive visualizations.</p>
          </div>
        </div>

        <div class="card">
          <div class="card-body text-center">
            <div class="w-12 h-12 bg-warning-100 rounded-lg mx-auto mb-4 flex items-center justify-center">
              <svg class="w-6 h-6 text-warning-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
              </svg>
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">Privacy First</h3>
            <p class="text-gray-600">Local-first processing with encrypted storage and privacy-conscious design.</p>
          </div>
        </div>
      </div>

      <!-- Status Section -->
      <div class="mt-16 card">
        <div class="card-header">
          <h3 class="text-lg font-semibold text-gray-900">System Status</h3>
        </div>
        <div class="card-body">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 class="text-sm font-medium text-gray-900 mb-2">Backend API</h4>
              <div class="flex items-center">
                <div class="w-3 h-3 bg-success-500 rounded-full mr-2"></div>
                <span class="text-sm text-gray-600">Connected to localhost:8000</span>
              </div>
            </div>
            <div>
              <h4 class="text-sm font-medium text-gray-900 mb-2">Frontend</h4>
              <div class="flex items-center">
                <div class="w-3 h-3 bg-success-500 rounded-full mr-2"></div>
                <span class="text-sm text-gray-600">v3.6.0 Development Environment</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
// HomeView - DevDocAI v3.6.0 Landing Page
</script>
