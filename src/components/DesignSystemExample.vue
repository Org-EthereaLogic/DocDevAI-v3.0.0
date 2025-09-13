<template>
  <div class="design-system-example container-responsive py-8">
    <!-- Theme Controls -->
    <div class="card-base card-md mb-8">
      <h2 class="text-2xl font-semibold mb-4 text-text-primary">
        DevDocAI v3.6.0 Design System Demo
      </h2>

      <div class="flex flex-wrap gap-4 mb-6">
        <button
          @click="setTheme('light')"
          :class="[
            'btn-base btn-md',
            currentTheme === 'light' ? 'btn-primary' : 'btn-outline'
          ]"
        >
          ☀️ Light
        </button>

        <button
          @click="setTheme('dark')"
          :class="[
            'btn-base btn-md',
            currentTheme === 'dark' ? 'btn-primary' : 'btn-outline'
          ]"
        >
          🌙 Dark
        </button>

        <button
          @click="setTheme('highContrast')"
          :class="[
            'btn-base btn-md',
            currentTheme === 'highContrast' ? 'btn-primary' : 'btn-outline'
          ]"
        >
          ♿ High Contrast
        </button>

        <button
          @click="toggleTheme"
          class="btn-base btn-md btn-ghost"
        >
          🔄 Toggle
        </button>
      </div>

      <div class="text-sm text-text-secondary">
        Current theme: <code class="px-2 py-1 bg-bg-secondary rounded">{{ currentTheme }}</code> |
        System theme: <code class="px-2 py-1 bg-bg-secondary rounded">{{ systemTheme }}</code> |
        Reduced motion: <code class="px-2 py-1 bg-bg-secondary rounded">{{ reducedMotion }}</code>
      </div>
    </div>

    <!-- Color Palette -->
    <div class="card-base card-md mb-8">
      <h3 class="text-xl font-semibold mb-4">Color Palette</h3>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div class="text-center">
          <div class="w-16 h-16 bg-green-500 rounded-lg mx-auto mb-2"></div>
          <span class="text-sm">Success</span>
        </div>
        <div class="text-center">
          <div class="w-16 h-16 bg-yellow-500 rounded-lg mx-auto mb-2"></div>
          <span class="text-sm">Warning</span>
        </div>
        <div class="text-center">
          <div class="w-16 h-16 bg-red-500 rounded-lg mx-auto mb-2"></div>
          <span class="text-sm">Danger</span>
        </div>
        <div class="text-center">
          <div class="w-16 h-16 bg-blue-500 rounded-lg mx-auto mb-2"></div>
          <span class="text-sm">Info</span>
        </div>
      </div>

      <!-- Health Score Examples -->
      <div class="space-y-3">
        <h4 class="font-medium">Health Score Indicators</h4>
        <div class="flex flex-wrap gap-3">
          <div :class="getHealthClass(95)">
            {{ formatHealthScore(95) }} Excellent
          </div>
          <div :class="getHealthClass(78)">
            {{ formatHealthScore(78) }} Good
          </div>
          <div :class="getHealthClass(65)">
            {{ formatHealthScore(65) }} Needs Work
          </div>
        </div>
      </div>
    </div>

    <!-- Typography -->
    <div class="card-base card-md mb-8">
      <h3 class="text-xl font-semibold mb-4">Typography</h3>

      <div class="space-y-4">
        <div>
          <h1 class="text-5xl font-bold">Heading 1</h1>
          <code class="text-xs text-text-tertiary">text-5xl font-bold</code>
        </div>
        <div>
          <h2 class="text-3xl font-semibold">Heading 2</h2>
          <code class="text-xs text-text-tertiary">text-3xl font-semibold</code>
        </div>
        <div>
          <h3 class="text-xl font-medium">Heading 3</h3>
          <code class="text-xs text-text-tertiary">text-xl font-medium</code>
        </div>
        <div>
          <p class="text-base">
            This is body text using the Inter font family. It maintains excellent readability
            across all screen sizes and follows WCAG 2.1 AA accessibility guidelines.
          </p>
          <code class="text-xs text-text-tertiary">text-base</code>
        </div>
        <div>
          <p class="text-sm text-text-secondary">
            Secondary text used for descriptions and less important information.
          </p>
          <code class="text-xs text-text-tertiary">text-sm text-text-secondary</code>
        </div>
        <div class="font-mono text-sm bg-bg-secondary p-3 rounded">
          <code>Monospace font for code examples using JetBrains Mono</code>
        </div>
      </div>
    </div>

    <!-- Buttons -->
    <div class="card-base card-md mb-8">
      <h3 class="text-xl font-semibold mb-4">Buttons</h3>

      <div class="space-y-6">
        <!-- Button Variants -->
        <div>
          <h4 class="font-medium mb-3">Variants</h4>
          <div class="flex flex-wrap gap-3">
            <button class="btn-base btn-md btn-primary">Primary</button>
            <button class="btn-base btn-md btn-success">Success</button>
            <button class="btn-base btn-md btn-warning">Warning</button>
            <button class="btn-base btn-md btn-danger">Danger</button>
            <button class="btn-base btn-md btn-info">Info</button>
            <button class="btn-base btn-md btn-ghost">Ghost</button>
            <button class="btn-base btn-md btn-outline">Outline</button>
          </div>
        </div>

        <!-- Button Sizes -->
        <div>
          <h4 class="font-medium mb-3">Sizes</h4>
          <div class="flex flex-wrap items-center gap-3">
            <button class="btn-base btn-sm btn-primary">Small</button>
            <button class="btn-base btn-md btn-primary">Medium</button>
            <button class="btn-base btn-lg btn-primary">Large</button>
            <button class="btn-base btn-xl btn-primary">Extra Large</button>
          </div>
        </div>

        <!-- Button States -->
        <div>
          <h4 class="font-medium mb-3">States</h4>
          <div class="flex flex-wrap gap-3">
            <button class="btn-base btn-md btn-primary">Normal</button>
            <button class="btn-base btn-md btn-primary" disabled>Disabled</button>
            <button class="btn-base btn-md btn-primary loading">
              <div class="loading-spinner mr-2"></div>
              Loading
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Form Elements -->
    <div class="card-base card-md mb-8">
      <h3 class="text-xl font-semibold mb-4">Form Elements</h3>

      <div class="space-y-4 max-w-md">
        <div>
          <label for="example-input" class="block text-sm font-medium mb-2">
            Text Input
          </label>
          <input
            id="example-input"
            type="text"
            placeholder="Enter some text..."
            class="input-base input-md"
          />
        </div>

        <div>
          <label for="example-select" class="block text-sm font-medium mb-2">
            Select
          </label>
          <select id="example-select" class="input-base input-md">
            <option>Choose an option</option>
            <option>Option 1</option>
            <option>Option 2</option>
            <option>Option 3</option>
          </select>
        </div>

        <div>
          <label for="example-textarea" class="block text-sm font-medium mb-2">
            Textarea
          </label>
          <textarea
            id="example-textarea"
            rows="3"
            placeholder="Enter a description..."
            class="input-base"
          ></textarea>
        </div>

        <div class="flex items-center space-x-2">
          <input
            id="example-checkbox"
            type="checkbox"
            class="touch-target"
          />
          <label for="example-checkbox" class="text-sm">
            I agree to the terms and conditions
          </label>
        </div>
      </div>
    </div>

    <!-- Status Indicators -->
    <div class="card-base card-md mb-8">
      <h3 class="text-xl font-semibold mb-4">Status Indicators</h3>

      <div class="space-y-4">
        <div>
          <h4 class="font-medium mb-3">Status Badges</h4>
          <div class="flex flex-wrap gap-3">
            <span class="status-indicator status-online">
              {{ getStatusIcon('online') }} Online
            </span>
            <span class="status-indicator status-offline">
              {{ getStatusIcon('offline') }} Offline
            </span>
            <span class="status-indicator status-pending">
              {{ getStatusIcon('pending') }} Pending
            </span>
            <span class="status-indicator status-error">
              {{ getStatusIcon('error') }} Error
            </span>
            <span class="status-indicator status-processing">
              {{ getStatusIcon('processing') }} Processing
            </span>
          </div>
        </div>

        <div>
          <h4 class="font-medium mb-3">Progress Bars</h4>
          <div class="space-y-3">
            <div>
              <div class="flex justify-between text-sm mb-1">
                <span>Excellent Health (95%)</span>
                <span>95%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill health-excellent" style="width: 95%"></div>
              </div>
            </div>

            <div>
              <div class="flex justify-between text-sm mb-1">
                <span>Good Health (78%)</span>
                <span>78%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill health-good" style="width: 78%"></div>
              </div>
            </div>

            <div>
              <div class="flex justify-between text-sm mb-1">
                <span>Poor Health (45%)</span>
                <span>45%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill health-poor" style="width: 45%"></div>
              </div>
            </div>

            <div>
              <div class="text-sm mb-1">Loading...</div>
              <div class="progress-bar progress-indeterminate">
                <div class="progress-fill" style="width: 100%"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading States -->
    <div class="card-base card-md mb-8">
      <h3 class="text-xl font-semibold mb-4">Loading States</h3>

      <div class="space-y-6">
        <div>
          <h4 class="font-medium mb-3">Skeleton Loaders</h4>
          <div class="space-y-3">
            <div class="loading-skeleton h-6 w-3/4"></div>
            <div class="loading-skeleton h-4 w-1/2"></div>
            <div class="loading-skeleton h-4 w-2/3"></div>
            <div class="loading-skeleton h-20 w-full"></div>
          </div>
        </div>

        <div>
          <h4 class="font-medium mb-3">Spinners & Indicators</h4>
          <div class="flex items-center gap-6">
            <div class="flex items-center gap-2">
              <div class="loading-spinner"></div>
              <span class="text-sm">Spinner</span>
            </div>

            <div class="flex items-center gap-2">
              <div class="loading-dots">
                <div></div>
                <div></div>
                <div></div>
              </div>
              <span class="text-sm">Dots</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Animations -->
    <div class="card-base card-md mb-8">
      <h3 class="text-xl font-semibold mb-4">Animations</h3>

      <div class="space-y-4">
        <div class="flex flex-wrap gap-3">
          <button
            @click="triggerAnimation('fade-in')"
            class="btn-base btn-sm btn-outline"
          >
            Fade In
          </button>
          <button
            @click="triggerAnimation('slide-in-right')"
            class="btn-base btn-sm btn-outline"
          >
            Slide In
          </button>
          <button
            @click="triggerAnimation('scale-in')"
            class="btn-base btn-sm btn-outline"
          >
            Scale In
          </button>
          <button
            @click="triggerAnimation('bounce-gentle')"
            class="btn-base btn-sm btn-outline"
          >
            Bounce
          </button>
        </div>

        <div
          ref="animationTarget"
          class="w-32 h-32 bg-primary-100 rounded-lg flex items-center justify-center text-primary-700 font-medium"
        >
          Animation Target
        </div>
      </div>
    </div>

    <!-- Responsive Information -->
    <div class="card-base card-md">
      <h3 class="text-xl font-semibold mb-4">Responsive Information</h3>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        <div>
          <strong>Current Breakpoint:</strong> {{ getBreakpoint() }}
        </div>
        <div>
          <strong>Is Mobile:</strong> {{ isMobile }}
        </div>
        <div>
          <strong>Is Tablet:</strong> {{ isTablet }}
        </div>
        <div>
          <strong>Is Desktop:</strong> {{ isDesktop }}
        </div>
      </div>

      <div class="mt-4 pt-4 border-t border-border-primary">
        <h4 class="font-medium mb-2">Format Utilities</h4>
        <div class="space-y-1 text-sm">
          <div>File size: {{ formatFileSize(1024 * 1024 * 2.5) }}</div>
          <div>Duration: {{ formatDuration(65000) }}</div>
          <div>Health score: {{ formatHealthScore(87.3) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useDesignSystem } from '../composables/useDesignSystem';

// Use the design system composable
const {
  currentTheme,
  systemTheme,
  reducedMotion,
  setTheme,
  toggleTheme,
  getBreakpoint,
  isMobile,
  isTablet,
  isDesktop,
  getHealthClass,
  formatHealthScore,
  formatFileSize,
  formatDuration,
  getStatusIcon
} = useDesignSystem();

// Animation demo
const animationTarget = ref<HTMLElement>();

const triggerAnimation = (animationType: string) => {
  if (!animationTarget.value) return;

  // Remove existing animation classes
  animationTarget.value.classList.remove(
    'animate-fade-in',
    'animate-slide-in-right',
    'animate-scale-in',
    'animate-bounce-gentle'
  );

  // Add the requested animation
  setTimeout(() => {
    animationTarget.value?.classList.add(`animate-${animationType}`);
  }, 10);

  // Remove animation class after it completes
  setTimeout(() => {
    animationTarget.value?.classList.remove(`animate-${animationType}`);
  }, 800);
};
</script>

<style scoped>
/* Additional component-specific styles if needed */
.design-system-example {
  min-height: 100vh;
  background-color: var(--color-bg-secondary);
}

/* Demo-specific loading animation */
.loading {
  position: relative;
  pointer-events: none;
}

.loading::after {
  content: '';
  position: absolute;
  inset: 0;
  background-color: rgba(255, 255, 255, 0.7);
  border-radius: inherit;
}
</style>