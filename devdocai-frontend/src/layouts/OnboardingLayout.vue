<template>
  <div class="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
    <!-- Progress Bar -->
    <div class="fixed top-0 left-0 right-0 h-1 bg-gray-200 z-50">
      <div
        class="h-full bg-indigo-600 transition-all duration-300"
        :style="{ width: `${progress}%` }"
      />
    </div>

    <!-- Header -->
    <header class="relative bg-white/80 backdrop-blur-sm border-b border-gray-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center h-16">
          <h1 class="text-xl font-semibold text-gray-900">DevDocAI Setup</h1>

          <!-- Step Indicator -->
          <div class="flex items-center space-x-2">
            <span class="text-sm text-gray-500">Step</span>
            <span class="text-sm font-semibold text-indigo-600">{{ currentStep }}</span>
            <span class="text-sm text-gray-500">of {{ totalSteps }}</span>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1">
      <div class="max-w-3xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <router-view />
      </div>
    </main>

    <!-- Navigation Controls -->
    <footer class="bg-white border-t border-gray-200">
      <div class="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div class="flex justify-between items-center">
          <button
            v-if="currentStep > 1"
            @click="goBack"
            class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
          >
            <svg class="mr-2 -ml-1 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
            Back
          </button>
          <div v-else />

          <button
            v-if="canSkip"
            @click="skipOnboarding"
            class="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Skip for now
          </button>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useOnboardingStore } from '@/stores/onboarding'

const router = useRouter()
const onboardingStore = useOnboardingStore()

const currentStep = computed(() => onboardingStore.currentStep)
const totalSteps = computed(() => onboardingStore.totalSteps)
const progress = computed(() => (currentStep.value / totalSteps.value) * 100)
const canSkip = computed(() => onboardingStore.canSkip)

const goBack = () => {
  onboardingStore.previousStep()
}

const skipOnboarding = () => {
  onboardingStore.skipOnboarding()
  router.push('/dashboard')
}
</script>
