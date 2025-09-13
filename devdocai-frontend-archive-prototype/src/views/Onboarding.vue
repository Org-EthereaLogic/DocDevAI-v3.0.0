<template>
  <div>
    <!-- Step 1: Welcome -->
    <div v-if="currentStep === 1" class="text-center">
      <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-indigo-100">
        <svg class="h-6 w-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C20.168 18.477 18.582 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      </div>
      <div class="mt-3 sm:mt-5">
        <h3 class="text-lg leading-6 font-medium text-gray-900">Welcome to DevDocAI</h3>
        <div class="mt-2">
          <p class="text-sm text-gray-500">
            Let's set up your AI-powered documentation system. This will only take a few minutes.
          </p>
        </div>
      </div>
      <div class="mt-5 sm:mt-6">
        <button
          @click="nextStep"
          class="inline-flex justify-center w-full rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:text-sm"
        >
          Get Started
        </button>
      </div>
    </div>

    <!-- Step 2: Privacy Mode -->
    <div v-else-if="currentStep === 2">
      <div class="text-center">
        <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
          <svg class="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.031 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div class="mt-3 sm:mt-5">
          <h3 class="text-lg leading-6 font-medium text-gray-900">Choose Your Privacy Mode</h3>
          <div class="mt-2">
            <p class="text-sm text-gray-500">
              How would you like to process your documents?
            </p>
          </div>
        </div>
      </div>

      <div class="mt-6 space-y-4">
        <div class="relative">
          <input
            id="local-only"
            v-model="privacyMode"
            name="privacy-mode"
            type="radio"
            value="local"
            class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300"
          />
          <label for="local-only" class="ml-3 block text-sm font-medium text-gray-700">
            Local Only (Recommended)
          </label>
          <p class="ml-7 text-sm text-gray-500">
            All processing happens on your machine. Maximum privacy, no internet required.
          </p>
        </div>

        <div class="relative">
          <input
            id="cloud-enhanced"
            v-model="privacyMode"
            name="privacy-mode"
            type="radio"
            value="cloud"
            class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300"
          />
          <label for="cloud-enhanced" class="ml-3 block text-sm font-medium text-gray-700">
            Cloud Enhanced
          </label>
          <p class="ml-7 text-sm text-gray-500">
            Use cloud AI models for higher quality results. Requires API keys.
          </p>
        </div>
      </div>

      <div class="mt-6">
        <button
          @click="nextStep"
          :disabled="!privacyMode"
          class="inline-flex justify-center w-full rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:text-sm disabled:bg-gray-300"
        >
          Continue
        </button>
      </div>
    </div>

    <!-- Step 3: Complete -->
    <div v-else-if="currentStep === 3" class="text-center">
      <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
        <svg class="h-6 w-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <div class="mt-3 sm:mt-5">
        <h3 class="text-lg leading-6 font-medium text-gray-900">You're all set!</h3>
        <div class="mt-2">
          <p class="text-sm text-gray-500">
            DevDocAI is ready to help you create amazing documentation.
          </p>
        </div>
      </div>
      <div class="mt-5 sm:mt-6">
        <button
          @click="completeOnboarding"
          class="inline-flex justify-center w-full rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:text-sm"
        >
          Start Using DevDocAI
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useOnboardingStore } from '@/stores/onboarding'

const router = useRouter()
const onboardingStore = useOnboardingStore()

const privacyMode = ref('')
const currentStep = ref(1)

const nextStep = () => {
  if (currentStep.value === 2) {
    onboardingStore.updatePreference('privacyMode', privacyMode.value)
  }
  currentStep.value++
  onboardingStore.nextStep()
}

const completeOnboarding = () => {
  onboardingStore.completeOnboarding()
  router.push('/dashboard')
}
</script>
