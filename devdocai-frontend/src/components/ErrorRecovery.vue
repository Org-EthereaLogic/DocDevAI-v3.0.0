<template>
  <div class="min-h-full flex items-center justify-center p-4">
    <div class="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <!-- Error Icon -->
      <div class="flex justify-center mb-4">
        <div :class="[
          'rounded-full p-3',
          errorTypeClass.bg
        ]">
          <svg
            class="w-12 h-12"
            :class="errorTypeClass.icon"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              v-if="errorType === 'network'"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414"
            />
            <path
              v-else-if="errorType === 'timeout'"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
            <path
              v-else-if="errorType === 'auth'"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
            <path
              v-else-if="errorType === 'rate-limit'"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
            <path
              v-else
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
      </div>

      <!-- Error Title -->
      <h2 class="text-xl font-bold text-center mb-2" :class="errorTypeClass.title">
        {{ errorTitle }}
      </h2>

      <!-- Error Message -->
      <p class="text-gray-600 dark:text-gray-400 text-center mb-6">
        {{ errorMessage }}
      </p>

      <!-- Error Details (if available) -->
      <div v-if="errorDetails" class="mb-6">
        <details class="bg-gray-50 dark:bg-gray-700 rounded p-3">
          <summary class="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300">
            Technical Details
          </summary>
          <pre class="mt-2 text-xs text-gray-600 dark:text-gray-400 overflow-x-auto">{{ errorDetails }}</pre>
        </details>
      </div>

      <!-- Suggested Actions -->
      <div v-if="suggestedActions.length > 0" class="mb-6">
        <h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
          Suggested Actions:
        </h3>
        <ul class="space-y-2">
          <li
            v-for="(action, index) in suggestedActions"
            :key="index"
            class="flex items-start"
          >
            <svg class="w-5 h-5 text-green-500 mr-2 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-sm text-gray-600 dark:text-gray-400">{{ action }}</span>
          </li>
        </ul>
      </div>

      <!-- Recovery Actions -->
      <div class="flex flex-col space-y-3">
        <button
          v-if="canRetry"
          @click="handleRetry"
          :disabled="isRetrying"
          class="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          data-testid="retry-button"
        >
          <span v-if="isRetrying" class="flex items-center justify-center">
            <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Retrying...
          </span>
          <span v-else>
            {{ retryLabel }}
          </span>
        </button>

        <button
          v-if="canGoBack"
          @click="handleGoBack"
          class="w-full px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
          data-testid="go-back-button"
        >
          Go Back
        </button>

        <button
          v-if="canGoHome"
          @click="handleGoHome"
          class="w-full px-4 py-2 border border-gray-300 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
          data-testid="go-home-button"
        >
          Go to Dashboard
        </button>

        <a
          v-if="supportLink"
          :href="supportLink"
          target="_blank"
          rel="noopener noreferrer"
          class="w-full px-4 py-2 text-center text-sm text-blue-600 dark:text-blue-400 hover:underline"
          data-testid="support-link"
        >
          Contact Support
        </a>
      </div>

      <!-- Countdown for auto-retry -->
      <div v-if="autoRetryCountdown > 0" class="mt-4 text-center">
        <p class="text-sm text-gray-600 dark:text-gray-400">
          Auto-retry in {{ autoRetryCountdown }} seconds...
        </p>
        <button
          @click="cancelAutoRetry"
          class="mt-1 text-xs text-red-600 hover:underline"
          data-testid="cancel-auto-retry"
        >
          Cancel auto-retry
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';

const props = defineProps({
  errorType: {
    type: String,
    default: 'generic',
    validator: (value) => ['network', 'timeout', 'auth', 'rate-limit', 'validation', 'generic'].includes(value)
  },
  errorTitle: {
    type: String,
    default: 'Something went wrong'
  },
  errorMessage: {
    type: String,
    default: 'An unexpected error occurred. Please try again.'
  },
  errorDetails: {
    type: String,
    default: null
  },
  canRetry: {
    type: Boolean,
    default: true
  },
  canGoBack: {
    type: Boolean,
    default: true
  },
  canGoHome: {
    type: Boolean,
    default: true
  },
  retryLabel: {
    type: String,
    default: 'Try Again'
  },
  supportLink: {
    type: String,
    default: null
  },
  autoRetry: {
    type: Boolean,
    default: false
  },
  autoRetryDelay: {
    type: Number,
    default: 5000 // 5 seconds
  }
});

const emit = defineEmits(['retry', 'go-back', 'go-home']);

const router = useRouter();
const isRetrying = ref(false);
const autoRetryCountdown = ref(0);
let autoRetryInterval = null;
let autoRetryTimeout = null;

// Compute error-specific styling
const errorTypeClass = computed(() => {
  const classes = {
    network: {
      bg: 'bg-gray-100 dark:bg-gray-700',
      icon: 'text-gray-600 dark:text-gray-400',
      title: 'text-gray-900 dark:text-white'
    },
    timeout: {
      bg: 'bg-yellow-100 dark:bg-yellow-900',
      icon: 'text-yellow-600 dark:text-yellow-400',
      title: 'text-yellow-900 dark:text-yellow-100'
    },
    auth: {
      bg: 'bg-red-100 dark:bg-red-900',
      icon: 'text-red-600 dark:text-red-400',
      title: 'text-red-900 dark:text-red-100'
    },
    'rate-limit': {
      bg: 'bg-orange-100 dark:bg-orange-900',
      icon: 'text-orange-600 dark:text-orange-400',
      title: 'text-orange-900 dark:text-orange-100'
    },
    validation: {
      bg: 'bg-purple-100 dark:bg-purple-900',
      icon: 'text-purple-600 dark:text-purple-400',
      title: 'text-purple-900 dark:text-purple-100'
    },
    generic: {
      bg: 'bg-blue-100 dark:bg-blue-900',
      icon: 'text-blue-600 dark:text-blue-400',
      title: 'text-blue-900 dark:text-blue-100'
    }
  };

  return classes[props.errorType] || classes.generic;
});

// Compute suggested actions based on error type
const suggestedActions = computed(() => {
  const actions = {
    network: [
      'Check your internet connection',
      'Verify the server is accessible',
      'Try disabling VPN or proxy if active'
    ],
    timeout: [
      'The operation is taking longer than expected',
      'Try simplifying your request',
      'Check if the server is under heavy load'
    ],
    auth: [
      'Verify your API key is correct',
      'Check if your API key has expired',
      'Ensure you have the necessary permissions'
    ],
    'rate-limit': [
      'Wait a few minutes before trying again',
      'Consider upgrading your plan for higher limits',
      'Spread out your requests over time'
    ],
    validation: [
      'Review the form for any errors',
      'Ensure all required fields are filled',
      'Check that input formats are correct'
    ],
    generic: [
      'Refresh the page and try again',
      'Clear your browser cache',
      'Contact support if the issue persists'
    ]
  };

  return actions[props.errorType] || actions.generic;
});

const handleRetry = async () => {
  isRetrying.value = true;
  cancelAutoRetry();

  try {
    await emit('retry');
  } finally {
    // Keep retrying state for at least 1 second for visual feedback
    setTimeout(() => {
      isRetrying.value = false;
    }, 1000);
  }
};

const handleGoBack = () => {
  cancelAutoRetry();
  if (window.history.length > 1) {
    router.back();
  }
  emit('go-back');
};

const handleGoHome = () => {
  cancelAutoRetry();
  router.push('/');
  emit('go-home');
};

const startAutoRetry = () => {
  if (!props.autoRetry || !props.canRetry) return;

  autoRetryCountdown.value = Math.floor(props.autoRetryDelay / 1000);

  autoRetryInterval = setInterval(() => {
    autoRetryCountdown.value--;
    if (autoRetryCountdown.value <= 0) {
      clearInterval(autoRetryInterval);
    }
  }, 1000);

  autoRetryTimeout = setTimeout(() => {
    handleRetry();
  }, props.autoRetryDelay);
};

const cancelAutoRetry = () => {
  if (autoRetryInterval) {
    clearInterval(autoRetryInterval);
    autoRetryInterval = null;
  }

  if (autoRetryTimeout) {
    clearTimeout(autoRetryTimeout);
    autoRetryTimeout = null;
  }

  autoRetryCountdown.value = 0;
};

onMounted(() => {
  startAutoRetry();
});

onUnmounted(() => {
  cancelAutoRetry();
});
</script>
