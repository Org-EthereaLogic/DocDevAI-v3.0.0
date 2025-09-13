<template>
  <div class="flex flex-col items-center justify-center p-8">
    <div class="relative">
      <!-- Spinning circle -->
      <div class="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>

      <!-- Center dot -->
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
      </div>
    </div>

    <!-- Loading message -->
    <div class="mt-4 text-center">
      <p class="text-lg font-medium text-gray-700 dark:text-gray-300">{{ message }}</p>
      <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">{{ subMessage }}</p>

      <!-- Progress indicator -->
      <div v-if="showProgress" class="mt-4">
        <div class="flex items-center justify-center space-x-1">
          <div
            v-for="i in 3"
            :key="i"
            class="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
            :style="{ animationDelay: `${i * 0.15}s` }"
          ></div>
        </div>
      </div>

      <!-- Time elapsed -->
      <div v-if="showTimer" class="mt-3">
        <p class="text-xs text-gray-400">Time elapsed: {{ formattedTime }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  message: {
    type: String,
    default: 'Generating document...'
  },
  subMessage: {
    type: String,
    default: 'This may take 60-90 seconds'
  },
  showProgress: {
    type: Boolean,
    default: true
  },
  showTimer: {
    type: Boolean,
    default: true
  }
});

const elapsedSeconds = ref(0);
let timerInterval = null;

const formattedTime = computed(() => {
  const minutes = Math.floor(elapsedSeconds.value / 60);
  const seconds = elapsedSeconds.value % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
});

onMounted(() => {
  if (props.showTimer) {
    timerInterval = setInterval(() => {
      elapsedSeconds.value++;
    }, 1000);
  }
});

onUnmounted(() => {
  if (timerInterval) {
    clearInterval(timerInterval);
  }
});
</script>

<style scoped>
@keyframes bounce {
  0%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-10px);
  }
}
</style>
