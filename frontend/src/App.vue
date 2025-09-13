<template>
  <div id="app" class="app-layout">
    <!-- Skip to content link for accessibility -->
    <a href="#main-content" class="skip-link">
      Skip to main content
    </a>

    <!-- Loading overlay for initial app load -->
    <Transition name="fade">
      <div
        v-if="appStore.isInitializing"
        class="fixed inset-0 z-50 flex items-center justify-center bg-white dark:bg-gray-900"
      >
        <div class="text-center">
          <div class="loading-spinner h-8 w-8 mx-auto mb-4"></div>
          <p class="text-gray-600 dark:text-gray-400">
            Initializing DevDocAI...
          </p>
        </div>
      </div>
    </Transition>

    <!-- Main Application Layout -->
    <div v-if="!appStore.isInitializing" class="flex h-screen">
      <!-- Sidebar -->
      <AppSidebar
        v-if="showSidebar"
        :collapsed="appStore.sidebarCollapsed"
        @toggle="appStore.toggleSidebar"
      />

      <!-- Main Content Area -->
      <div class="flex-1 flex flex-col min-w-0">
        <!-- Header -->
        <AppHeader
          :sidebar-collapsed="appStore.sidebarCollapsed"
          @toggle-sidebar="appStore.toggleSidebar"
        />

        <!-- Page Content -->
        <main
          id="main-content"
          class="flex-1 overflow-auto bg-gray-50 dark:bg-gray-900"
          :class="[
            appStore.compactMode ? 'p-4' : 'p-6',
            { 'transition-all duration-300': appStore.animationsEnabled }
          ]"
        >
          <!-- Router View with page transitions -->
          <RouterView v-slot="{ Component, route }">
            <Transition
              :name="getPageTransition(route)"
              mode="out-in"
              appear
            >
              <Suspense>
                <component :is="Component" :key="route.path" />

                <template #fallback>
                  <div class="flex items-center justify-center min-h-64">
                    <div class="loading-spinner h-6 w-6 mr-3"></div>
                    <span class="text-gray-600 dark:text-gray-400">
                      Loading page...
                    </span>
                  </div>
                </template>
              </Suspense>
            </Transition>
          </RouterView>
        </main>
      </div>
    </div>

    <!-- Global Modals -->
    <GlobalModals />

    <!-- Notification Center -->
    <NotificationCenter />

    <!-- Global Loading Overlay -->
    <Transition name="fade">
      <div
        v-if="appStore.globalLoading"
        class="fixed inset-0 z-40 flex items-center justify-center bg-black bg-opacity-50"
        role="dialog"
        aria-labelledby="loading-title"
        aria-describedby="loading-description"
      >
        <div class="bg-white dark:bg-gray-800 rounded-lg p-6 shadow-xl max-w-sm w-full mx-4">
          <div class="flex items-center">
            <div class="loading-spinner h-5 w-5 mr-3"></div>
            <div>
              <h3 id="loading-title" class="font-medium text-gray-900 dark:text-gray-100">
                Processing...
              </h3>
              <p
                v-if="appStore.loadingMessage"
                id="loading-description"
                class="text-sm text-gray-600 dark:text-gray-400 mt-1"
              >
                {{ appStore.loadingMessage }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Keyboard shortcuts help (hidden by default) -->
    <KeyboardShortcutsHelp v-if="showKeyboardHelp" @close="showKeyboardHelp = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useAppStore } from '@/stores/app';
import { useNotificationsStore } from '@/stores/notifications';
import AppHeader from '@/components/organisms/headers/AppHeader.vue';
import AppSidebar from '@/components/organisms/sidebars/AppSidebar.vue';
import NotificationCenter from '@/components/organisms/notifications/NotificationCenter.vue';
import GlobalModals from '@/components/organisms/modals/GlobalModals.vue';
import KeyboardShortcutsHelp from '@/components/molecules/help/KeyboardShortcutsHelp.vue';

const route = useRoute();
const appStore = useAppStore();
const notificationsStore = useNotificationsStore();

// Local state
const showKeyboardHelp = ref(false);

// Computed
const showSidebar = computed(() => {
  // Hide sidebar on certain routes (e.g., login, onboarding)
  const hiddenRoutes = ['/login', '/onboarding', '/error'];
  return !hiddenRoutes.includes(route.path);
});

// Page transition logic
const getPageTransition = (route: any) => {
  if (!appStore.animationsEnabled || appStore.shouldReduceMotion) {
    return 'none';
  }

  // Different transitions for different route types
  if (route.meta?.transition) {
    return route.meta.transition;
  }

  return 'fade';
};

// Keyboard shortcuts
const handleKeyboardShortcuts = (event: KeyboardEvent) => {
  // Global shortcuts that work regardless of focus
  if (event.ctrlKey || event.metaKey) {
    switch (event.key) {
      case '/':
        event.preventDefault();
        // Focus search input if available
        const searchInput = document.querySelector('[data-search-input]') as HTMLInputElement;
        if (searchInput) {
          searchInput.focus();
        }
        break;

      case '?':
        event.preventDefault();
        showKeyboardHelp.value = !showKeyboardHelp.value;
        break;

      case 'k':
        event.preventDefault();
        // Open command palette (to be implemented)
        console.log('Command palette shortcut triggered');
        break;
    }
  }

  // Escape key handling
  if (event.key === 'Escape') {
    if (showKeyboardHelp.value) {
      showKeyboardHelp.value = false;
    }
  }
};

// Theme changes
watch(
  () => appStore.effectiveTheme,
  (newTheme) => {
    // Update document class and meta theme-color
    document.documentElement.setAttribute('data-theme', newTheme);

    const metaThemeColor = document.querySelector('meta[name="theme-color"]');
    if (metaThemeColor) {
      metaThemeColor.setAttribute(
        'content',
        newTheme === 'dark' ? '#1f2937' : '#ffffff'
      );
    }
  },
  { immediate: true }
);

// Error handling
const handleGlobalError = (event: ErrorEvent) => {
  console.error('Global error:', event.error);

  notificationsStore.error(
    'An unexpected error occurred. Please refresh the page if the problem persists.',
    {
      title: 'Application Error',
      persistent: true,
      actions: [
        {
          label: 'Refresh Page',
          action: () => window.location.reload(),
          style: 'primary',
        },
        {
          label: 'Report Issue',
          action: () => {
            // Open issue reporting (to be implemented)
            console.log('Report issue action triggered');
          },
          style: 'secondary',
        },
      ],
    }
  );
};

const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
  console.error('Unhandled promise rejection:', event.reason);

  notificationsStore.warning(
    'A background operation failed. Some features may not work correctly.',
    {
      title: 'Background Error',
      description: 'The application will continue to function, but you may need to retry some actions.',
    }
  );
};

// Lifecycle
onMounted(async () => {
  // Initialize the app store first
  await appStore.initialize();

  // Set up keyboard shortcuts
  appStore.setupKeyboardShortcuts();
  document.addEventListener('keydown', handleKeyboardShortcuts);

  // Set up global error handling
  window.addEventListener('error', handleGlobalError);
  window.addEventListener('unhandledrejection', handleUnhandledRejection);

  // Initialize app-level functionality
  if (appStore.soundEnabled) {
    // Preload notification sounds or setup audio context
  }

  // Set initial route
  appStore.setCurrentRoute(route.path);
});

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyboardShortcuts);
  window.removeEventListener('error', handleGlobalError);
  window.removeEventListener('unhandledrejection', handleUnhandledRejection);
});

// Watch route changes
watch(
  () => route.path,
  (newPath) => {
    appStore.setCurrentRoute(newPath);

    // Update breadcrumbs based on route meta
    if (route.meta?.breadcrumbs) {
      appStore.setBreadcrumbs(route.meta.breadcrumbs);
    }

    // Announce page changes for screen readers
    const pageTitle = route.meta?.title || 'Page loaded';
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = `Navigated to ${pageTitle}`;
    document.body.appendChild(announcement);

    setTimeout(() => {
      document.body.removeChild(announcement);
    }, 1000);
  }
);
</script>

<style scoped>
/* Page transition styles */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-duration) var(--ease-out);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all var(--transition-duration) var(--ease-out);
}

.slide-enter-from {
  transform: translateX(100%);
  opacity: 0;
}

.slide-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}

.scale-enter-active,
.scale-leave-active {
  transition: all var(--transition-duration) var(--ease-out);
}

.scale-enter-from,
.scale-leave-to {
  transform: scale(0.95);
  opacity: 0;
}

/* No transition for reduced motion */
.none-enter-active,
.none-leave-active {
  transition: none;
}
</style>