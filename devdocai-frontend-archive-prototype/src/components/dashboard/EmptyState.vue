<template>
  <div class="text-center py-16">
    <!-- Illustration -->
    <div class="mx-auto h-48 w-48 mb-8">
      <svg
        class="h-full w-full text-gray-300"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="1"
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
        <!-- Additional document icons for illustration -->
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="0.5"
          d="M6 8h4m-4 4h8m-8 4h6"
          opacity="0.5"
        />
      </svg>
    </div>

    <!-- Content -->
    <div class="max-w-md mx-auto">
      <h3 class="text-xl font-semibold text-gray-900 mb-3">
        Welcome to DevDocAI!
      </h3>
      <p class="text-gray-600 mb-8 leading-relaxed">
        You haven't created any projects yet. Start by creating your first project to
        generate AI-powered documentation and track your documentation health.
      </p>

      <!-- CTA Button -->
      <button
        @click="$emit('create-project')"
        class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all duration-300 transform hover:scale-105"
        aria-label="Create your first project"
      >
        <svg class="mr-2 -ml-1 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
        </svg>
        Create Your First Project
      </button>

      <!-- Feature Highlights -->
      <div class="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-6">
        <div class="text-center">
          <div class="mx-auto h-12 w-12 rounded-lg bg-blue-100 flex items-center justify-center mb-3">
            <svg class="h-6 w-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h4 class="text-sm font-semibold text-gray-900 mb-1">AI-Powered Generation</h4>
          <p class="text-xs text-gray-600">
            Generate comprehensive documentation using advanced AI models
          </p>
        </div>

        <div class="text-center">
          <div class="mx-auto h-12 w-12 rounded-lg bg-green-100 flex items-center justify-center mb-3">
            <svg class="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h4 class="text-sm font-semibold text-gray-900 mb-1">Health Tracking</h4>
          <p class="text-xs text-gray-600">
            Monitor documentation quality with comprehensive health scores
          </p>
        </div>

        <div class="text-center">
          <div class="mx-auto h-12 w-12 rounded-lg bg-purple-100 flex items-center justify-center mb-3">
            <svg class="h-6 w-6 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h4 class="text-sm font-semibold text-gray-900 mb-1">Suite Management</h4>
          <p class="text-xs text-gray-600">
            Organize and maintain documentation suites effortlessly
          </p>
        </div>
      </div>

      <!-- Quick Start Tips -->
      <div class="mt-12 text-left">
        <h4 class="text-sm font-semibold text-gray-900 mb-4 text-center">Quick Start Tips</h4>
        <ul class="space-y-2 text-sm text-gray-600">
          <li class="flex items-start">
            <svg class="h-4 w-4 text-indigo-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            Create a project by pointing to your code repository
          </li>
          <li class="flex items-start">
            <svg class="h-4 w-4 text-indigo-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            Configure your preferred AI model and settings
          </li>
          <li class="flex items-start">
            <svg class="h-4 w-4 text-indigo-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            Let AI generate comprehensive documentation automatically
          </li>
          <li class="flex items-start">
            <svg class="h-4 w-4 text-indigo-500 mr-2 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
            Monitor and improve documentation health over time
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
// Emits
defineEmits(['create-project'])
</script>

<style scoped>
/* Subtle animations for enhanced UX */
@keyframes float {
  0%, 100% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
}

.mx-auto.h-48.w-48 svg {
  animation: float 6s ease-in-out infinite;
}

/* Hover effect for feature highlights */
.grid > div {
  transition: transform 0.2s ease-out;
}

.grid > div:hover {
  transform: translateY(-2px);
}
</style>
