# DevDocAI v3.6.0 Frontend Implementation Guide

## Quick Start

### 1. Install Dependencies

```bash
# Install required packages
npm install vue-router@4 pinia pinia-plugin-persistedstate

# Optional but recommended
npm install @vueuse/core @heroicons/vue dayjs
```

### 2. Update main.js

```javascript
import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import pinia from './stores';
import './assets/styles/main.css';

const app = createApp(App);

// Install plugins
app.use(pinia);
app.use(router);

// Global error handler
app.config.errorHandler = (err, instance, info) => {
  console.error('Global error:', err, info);
  // Could send to error tracking service
};

// Mount app
app.mount('#app');
```

### 3. Update App.vue for Routing

```vue
<template>
  <component :is="layout">
    <router-view />
  </component>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useOnboardingStore } from '@/stores/onboarding';

// Import layouts
import DefaultLayout from '@/layouts/DefaultLayout.vue';
import AuthLayout from '@/layouts/AuthLayout.vue';
import OnboardingLayout from '@/layouts/OnboardingLayout.vue';

const route = useRoute();
const authStore = useAuthStore();
const onboardingStore = useOnboardingStore();

// Determine which layout to use
const layout = computed(() => {
  if (route.meta.layout === 'auth') return AuthLayout;
  if (route.meta.layout === 'onboarding') return OnboardingLayout;
  return DefaultLayout;
});

// Initialize stores on mount
onMounted(() => {
  authStore.initializeAuth();
  onboardingStore.initializeOnboarding();
});
</script>
```

## Component Examples

### 1. Dashboard View

```vue
<!-- src/views/Dashboard.vue -->
<template>
  <div class="dashboard">
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-gray-900 dark:text-white">
        Welcome to DevDocAI
      </h1>
      <p class="mt-2 text-gray-600 dark:text-gray-400">
        Your AI-powered documentation dashboard
      </p>
    </div>

    <!-- Quick Actions -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <QuickActionCard
        title="Generate Document"
        description="Create new documentation with AI"
        icon="document-plus"
        @click="navigateToGenerate"
      />
      <QuickActionCard
        title="Template Marketplace"
        description="Browse community templates"
        icon="template"
        @click="navigateToTemplates"
      />
      <QuickActionCard
        title="Review Health"
        description="Check documentation quality"
        icon="chart"
        @click="navigateToReview"
      />
    </div>

    <!-- Recent Documents -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow">
      <div class="p-6">
        <h2 class="text-xl font-semibold mb-4">Recent Documents</h2>
        <div v-if="isLoading" class="text-center py-8">
          <LoadingSpinner />
        </div>
        <div v-else-if="recentDocuments.length === 0" class="text-center py-8">
          <p class="text-gray-500">No documents yet. Start by generating one!</p>
        </div>
        <div v-else class="space-y-4">
          <DocumentCard
            v-for="doc in recentDocuments"
            :key="doc.id"
            :document="doc"
            @click="viewDocument(doc)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useDocumentStore } from '@/stores/document';
import QuickActionCard from '@/components/dashboard/QuickActionCard.vue';
import DocumentCard from '@/components/document/DocumentCard.vue';
import LoadingSpinner from '@/components/common/LoadingSpinner.vue';

const router = useRouter();
const documentStore = useDocumentStore();

const isLoading = ref(false);
const recentDocuments = ref([]);

// Navigation methods
const navigateToGenerate = () => router.push('/generate');
const navigateToTemplates = () => router.push('/templates');
const navigateToReview = () => router.push('/review');

const viewDocument = (doc) => {
  documentStore.setCurrentDocument(doc);
  router.push(`/documents/${doc.id}`);
};

// Load recent documents
onMounted(async () => {
  isLoading.value = true;
  try {
    await documentStore.fetchDocuments({ limit: 5 });
    recentDocuments.value = documentStore.recentDocuments;
  } catch (error) {
    console.error('Failed to load documents:', error);
  } finally {
    isLoading.value = false;
  }
});
</script>
```

### 2. Document Generation Wizard

```vue
<!-- src/views/DocumentWizard.vue -->
<template>
  <div class="document-wizard">
    <!-- Progress Steps -->
    <div class="mb-8">
      <StepIndicator
        :steps="steps"
        :current-step="currentStep"
      />
    </div>

    <!-- Wizard Content -->
    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <router-view
        v-slot="{ Component }"
        @next="handleNext"
        @previous="handlePrevious"
      >
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import StepIndicator from '@/components/wizard/StepIndicator.vue';

const route = useRoute();
const router = useRouter();

const steps = [
  { id: 'type', label: 'Document Type', path: '/generate' },
  { id: 'details', label: 'Project Details', path: '/generate/[type]' },
  { id: 'options', label: 'AI Options', path: '/generate/[type]/options' },
  { id: 'review', label: 'Review & Generate', path: '/generate/[type]/review' }
];

const currentStep = computed(() => {
  // Determine current step based on route
  if (route.name === 'generate-select') return 0;
  if (route.name?.includes('generate-')) return 1;
  return 0;
});

const handleNext = (data) => {
  // Store data and navigate to next step
  // Implementation depends on specific flow
};

const handlePrevious = () => {
  router.back();
};
</script>
```

### 3. Onboarding Flow

```vue
<!-- src/views/Onboarding.vue -->
<template>
  <div class="onboarding min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
    <div class="max-w-2xl w-full mx-auto p-8">
      <!-- Progress Bar -->
      <div class="mb-8">
        <div class="flex justify-between items-center mb-2">
          <span class="text-sm text-gray-600">Step {{ currentStep + 1 }} of {{ totalSteps }}</span>
          <button
            v-if="!isFirstStep"
            @click="skipOnboarding"
            class="text-sm text-gray-500 hover:text-gray-700"
          >
            Skip Tutorial
          </button>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2">
          <div
            class="bg-blue-600 h-2 rounded-full transition-all duration-300"
            :style="{ width: `${progress}%` }"
          />
        </div>
      </div>

      <!-- Content Card -->
      <div class="bg-white rounded-lg shadow-xl p-8">
        <transition name="slide" mode="out-in">
          <component
            :is="currentStepComponent"
            @next="handleNext"
            @previous="handlePrevious"
            @update-preference="updatePreference"
          />
        </transition>
      </div>

      <!-- Navigation -->
      <div class="mt-6 flex justify-between">
        <button
          v-if="!isFirstStep"
          @click="previousStep"
          class="px-4 py-2 text-gray-600 hover:text-gray-800"
        >
          ← Previous
        </button>
        <div v-else />

        <button
          v-if="!isLastStep"
          @click="nextStep"
          :disabled="!canProceed"
          class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          Next →
        </button>
        <button
          v-else
          @click="completeOnboarding"
          :disabled="!canProceed"
          class="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
        >
          Get Started
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { useOnboardingStore } from '@/stores/onboarding';

// Import step components
import WelcomeStep from '@/components/onboarding/WelcomeStep.vue';
import PrivacyStep from '@/components/onboarding/PrivacyStep.vue';
import FeaturesStep from '@/components/onboarding/FeaturesStep.vue';
import SetupStep from '@/components/onboarding/SetupStep.vue';

const router = useRouter();
const onboardingStore = useOnboardingStore();

// Destructure store properties and methods
const {
  currentStep,
  totalSteps,
  progress,
  canProceed,
  isFirstStep,
  isLastStep,
  nextStep,
  previousStep,
  updatePreference,
  completeOnboarding: complete,
  skipOnboarding: skip
} = onboardingStore;

// Map step components
const stepComponents = [
  WelcomeStep,
  PrivacyStep,
  FeaturesStep,
  SetupStep
];

const currentStepComponent = computed(() => stepComponents[currentStep.value]);

const handleNext = () => {
  if (nextStep()) {
    // Step advanced successfully
  }
};

const handlePrevious = () => {
  previousStep();
};

const completeOnboarding = () => {
  complete();
  router.push('/dashboard');
};

const skipOnboarding = () => {
  skip();
  router.push('/dashboard');
};
</script>
```

## API Integration Pattern

### 1. Create API Service Wrapper

```javascript
// src/services/api/base.js
class APIService {
  constructor(resource) {
    this.resource = resource;
  }

  async list(params = {}) {
    const response = await apiClient.get(`/${this.resource}`, { params });
    return response.data;
  }

  async get(id) {
    const response = await apiClient.get(`/${this.resource}/${id}`);
    return response.data;
  }

  async create(data) {
    const response = await apiClient.post(`/${this.resource}`, data);
    return response.data;
  }

  async update(id, data) {
    const response = await apiClient.put(`/${this.resource}/${id}`, data);
    return response.data;
  }

  async delete(id) {
    const response = await apiClient.delete(`/${this.resource}/${id}`);
    return response.data;
  }
}

export default APIService;
```

### 2. Use in Store

```javascript
// src/stores/example.js
import { defineStore } from 'pinia';
import APIService from '@/services/api/base';

const api = new APIService('documents');

export const useDocumentStore = defineStore('document', {
  state: () => ({
    items: [],
    current: null,
    loading: false,
    error: null
  }),

  actions: {
    async fetchAll() {
      this.loading = true;
      try {
        this.items = await api.list();
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    async create(data) {
      this.loading = true;
      try {
        const item = await api.create(data);
        this.items.push(item);
        return item;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    }
  }
});
```

## Testing Setup

### 1. Install Testing Dependencies

```bash
npm install -D vitest @vue/test-utils @testing-library/vue happy-dom
```

### 2. Configure Vitest

```javascript
// vite.config.js
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: './tests/setup.js'
  }
});
```

### 3. Example Component Test

```javascript
// tests/unit/components/DocumentCard.spec.js
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import DocumentCard from '@/components/document/DocumentCard.vue';

describe('DocumentCard', () => {
  it('renders document title', () => {
    const wrapper = mount(DocumentCard, {
      props: {
        document: {
          id: '1',
          title: 'Test README',
          type: 'readme',
          healthScore: 85
        }
      }
    });

    expect(wrapper.text()).toContain('Test README');
    expect(wrapper.find('.health-score').text()).toBe('85%');
  });

  it('emits click event', async () => {
    const wrapper = mount(DocumentCard, {
      props: {
        document: { id: '1', title: 'Test' }
      }
    });

    await wrapper.trigger('click');
    expect(wrapper.emitted()).toHaveProperty('click');
  });
});
```

## Next Implementation Steps

1. **Create Layout Components** (DefaultLayout, AuthLayout, OnboardingLayout)
2. **Implement Navigation Components** (AppHeader, AppSidebar, Breadcrumbs)
3. **Build Common UI Components** (Buttons, Modals, Forms)
4. **Create Page Views** following mockup specifications
5. **Connect to Backend API** with proper error handling
6. **Add Loading & Error States** for all async operations
7. **Implement Accessibility Features** (keyboard nav, ARIA labels)
8. **Add Animations** for smooth transitions
9. **Write Tests** for critical functionality
10. **Optimize Performance** (lazy loading, caching)

## Development Tips

- Use Vue DevTools for debugging stores and components
- Implement error boundaries for graceful error handling
- Add loading skeletons for better perceived performance
- Use Suspense for async component loading
- Implement proper form validation with Vuelidate or VeeValidate
- Add comprehensive keyboard shortcuts for power users
- Use Vue transitions for smooth UI animations
- Implement proper focus management for accessibility
- Add telemetry (with user consent) for usage analytics
- Use environment variables for configuration
