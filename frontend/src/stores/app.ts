// Application Store - Global App State

import { defineStore } from 'pinia';
import { ref, computed, type Ref } from 'vue';

export type Theme = 'light' | 'dark' | 'auto';
export type Language = 'en' | 'es' | 'fr' | 'de' | 'ja' | 'zh' | 'pt' | 'it' | 'ru' | 'ko';

export interface AppPreferences {
  theme: Theme;
  language: Language;
  sidebarCollapsed: boolean;
  compactMode: boolean;
  animationsEnabled: boolean;
  soundEnabled: boolean;
  highContrast: boolean;
  reducedMotion: boolean;
}

export interface SystemInfo {
  userAgent: string;
  language: string;
  timezone: string;
  screenResolution: string;
  colorScheme: 'light' | 'dark' | 'no-preference';
  reduceMotion: boolean;
}

export const useAppStore = defineStore('app', () => {
  // State
  const theme = ref<Theme>('auto');
  const language = ref<Language>('en');
  const sidebarCollapsed = ref(false);
  const compactMode = ref(false);
  const animationsEnabled = ref(true);
  const soundEnabled = ref(false);
  const highContrast = ref(false);
  const reducedMotion = ref(false);

  // System state
  const isOnline = ref(navigator.onLine);
  const systemInfo = ref<SystemInfo | null>(null);
  const currentRoute = ref<string>('');
  const breadcrumbs = ref<Array<{ label: string; route?: string }>>([]);

  // Layout state
  const headerHeight = ref(64);
  const sidebarWidth = ref(256);
  const sidebarCollapsedWidth = ref(64);
  const contentPadding = ref(24);

  // Loading states
  const isInitializing = ref(true);
  const globalLoading = ref(false);
  const loadingMessage = ref('');

  // Modal states
  const showCommandPalette = ref(false);
  const showSearch = ref(false);
  const showSettings = ref(false);
  const feedbackModal = ref({
    show: false,
    type: 'info' as 'success' | 'error' | 'warning' | 'info',
    title: '',
    message: '',
  });

  // Getters
  const effectiveTheme = computed(() => {
    if (theme.value === 'auto') {
      return systemInfo.value?.colorScheme === 'dark' ? 'dark' : 'light';
    }
    return theme.value;
  });

  const isDarkMode = computed(() => effectiveTheme.value === 'dark');

  const isLightMode = computed(() => effectiveTheme.value === 'light');

  const currentSidebarWidth = computed(() => {
    return sidebarCollapsed.value ? sidebarCollapsedWidth.value : sidebarWidth.value;
  });

  const isMobile = computed(() => {
    if (!systemInfo.value) return false;
    const [width] = systemInfo.value.screenResolution.split('x').map(Number);
    return width < 768;
  });

  const isTablet = computed(() => {
    if (!systemInfo.value) return false;
    const [width] = systemInfo.value.screenResolution.split('x').map(Number);
    return width >= 768 && width < 1024;
  });

  const isDesktop = computed(() => {
    if (!systemInfo.value) return false;
    const [width] = systemInfo.value.screenResolution.split('x').map(Number);
    return width >= 1024;
  });

  const shouldReduceMotion = computed(() => {
    return reducedMotion.value || (systemInfo.value?.reduceMotion ?? false);
  });

  const preferences = computed<AppPreferences>(() => ({
    theme: theme.value,
    language: language.value,
    sidebarCollapsed: sidebarCollapsed.value,
    compactMode: compactMode.value,
    animationsEnabled: animationsEnabled.value,
    soundEnabled: soundEnabled.value,
    highContrast: highContrast.value,
    reducedMotion: reducedMotion.value,
  }));

  // Actions
  const setTheme = (newTheme: Theme) => {
    theme.value = newTheme;
    applyTheme();
  };

  const setLanguage = (newLanguage: Language) => {
    language.value = newLanguage;
    document.documentElement.lang = newLanguage;
  };

  const toggleSidebar = () => {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  };

  const setSidebarCollapsed = (collapsed: boolean) => {
    sidebarCollapsed.value = collapsed;
  };

  const setCompactMode = (compact: boolean) => {
    compactMode.value = compact;
    updateLayoutStyles();
  };

  const toggleAnimations = () => {
    animationsEnabled.value = !animationsEnabled.value;
    updateAnimationStyles();
  };

  const toggleSound = () => {
    soundEnabled.value = !soundEnabled.value;
  };

  const toggleHighContrast = () => {
    highContrast.value = !highContrast.value;
    applyContrastStyles();
  };

  const toggleReducedMotion = () => {
    reducedMotion.value = !reducedMotion.value;
    updateAnimationStyles();
  };

  const updatePreferences = (newPreferences: Partial<AppPreferences>) => {
    if (newPreferences.theme !== undefined) {
      setTheme(newPreferences.theme);
    }
    if (newPreferences.language !== undefined) {
      setLanguage(newPreferences.language);
    }
    if (newPreferences.sidebarCollapsed !== undefined) {
      setSidebarCollapsed(newPreferences.sidebarCollapsed);
    }
    if (newPreferences.compactMode !== undefined) {
      setCompactMode(newPreferences.compactMode);
    }
    if (newPreferences.animationsEnabled !== undefined) {
      animationsEnabled.value = newPreferences.animationsEnabled;
      updateAnimationStyles();
    }
    if (newPreferences.soundEnabled !== undefined) {
      soundEnabled.value = newPreferences.soundEnabled;
    }
    if (newPreferences.highContrast !== undefined) {
      highContrast.value = newPreferences.highContrast;
      applyContrastStyles();
    }
    if (newPreferences.reducedMotion !== undefined) {
      reducedMotion.value = newPreferences.reducedMotion;
      updateAnimationStyles();
    }
  };

  const setCurrentRoute = (route: string) => {
    currentRoute.value = route;
  };

  const setBreadcrumbs = (crumbs: Array<{ label: string; route?: string }>) => {
    breadcrumbs.value = crumbs;
  };

  const setGlobalLoading = (loading: boolean, message = '') => {
    globalLoading.value = loading;
    loadingMessage.value = message;
  };

  // Modal actions
  const toggleCommandPalette = () => {
    showCommandPalette.value = !showCommandPalette.value;
  };

  const toggleSearch = () => {
    showSearch.value = !showSearch.value;
  };

  const toggleSettings = () => {
    showSettings.value = !showSettings.value;
  };

  const showFeedbackModal = (type: 'success' | 'error' | 'warning' | 'info', title: string, message: string) => {
    feedbackModal.value = {
      show: true,
      type,
      title,
      message,
    };
  };

  const closeFeedbackModal = () => {
    feedbackModal.value.show = false;
  };

  // System detection
  const detectSystemInfo = (): SystemInfo => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

    return {
      userAgent: navigator.userAgent,
      language: navigator.language,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      screenResolution: `${screen.width}x${screen.height}`,
      colorScheme: mediaQuery.matches ? 'dark' : 'light',
      reduceMotion: motionQuery.matches,
    };
  };

  const setupSystemListeners = () => {
    // Online/offline detection
    window.addEventListener('online', () => {
      isOnline.value = true;
    });

    window.addEventListener('offline', () => {
      isOnline.value = false;
    });

    // Color scheme changes
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    mediaQuery.addEventListener('change', (e) => {
      if (systemInfo.value) {
        systemInfo.value.colorScheme = e.matches ? 'dark' : 'light';
      }
      if (theme.value === 'auto') {
        applyTheme();
      }
    });

    // Reduced motion changes
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    motionQuery.addEventListener('change', (e) => {
      if (systemInfo.value) {
        systemInfo.value.reduceMotion = e.matches;
      }
      updateAnimationStyles();
    });
  };

  // Style application
  const applyTheme = () => {
    const root = document.documentElement;
    root.setAttribute('data-theme', effectiveTheme.value);

    if (isDarkMode.value) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  };

  const updateLayoutStyles = () => {
    const root = document.documentElement;

    if (compactMode.value) {
      root.style.setProperty('--header-height', '48px');
      root.style.setProperty('--content-padding', '16px');
      root.style.setProperty('--sidebar-width', '240px');
    } else {
      root.style.setProperty('--header-height', '64px');
      root.style.setProperty('--content-padding', '24px');
      root.style.setProperty('--sidebar-width', '256px');
    }
  };

  const updateAnimationStyles = () => {
    const root = document.documentElement;
    const shouldDisable = !animationsEnabled.value || shouldReduceMotion.value;

    if (shouldDisable) {
      root.style.setProperty('--animation-duration', '0ms');
      root.style.setProperty('--transition-duration', '0ms');
    } else {
      root.style.removeProperty('--animation-duration');
      root.style.removeProperty('--transition-duration');
    }
  };

  const applyContrastStyles = () => {
    const root = document.documentElement;

    if (highContrast.value) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }
  };

  // Initialize store
  const initialize = async () => {
    isInitializing.value = true;

    try {
      // Detect system info
      systemInfo.value = detectSystemInfo();

      // Set up system listeners
      setupSystemListeners();

      // Apply initial styles
      applyTheme();
      updateLayoutStyles();
      updateAnimationStyles();
      applyContrastStyles();

      // Set initial language
      document.documentElement.lang = language.value;

      // Detect if user prefers reduced motion
      if (systemInfo.value.reduceMotion && !reducedMotion.value) {
        reducedMotion.value = true;
      }

    } catch (error) {
      console.error('Failed to initialize app store:', error);
    } finally {
      isInitializing.value = false;
    }
  };

  // Keyboard shortcuts
  const setupKeyboardShortcuts = () => {
    document.addEventListener('keydown', (e) => {
      // Ctrl/Cmd + \ to toggle sidebar
      if ((e.ctrlKey || e.metaKey) && e.key === '\\') {
        e.preventDefault();
        toggleSidebar();
      }

      // Ctrl/Cmd + Shift + D to toggle dark mode
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        setTheme(effectiveTheme.value === 'dark' ? 'light' : 'dark');
      }

      // Ctrl/Cmd + Shift + M to toggle compact mode
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'M') {
        e.preventDefault();
        setCompactMode(!compactMode.value);
      }
    });
  };

  return {
    // State
    theme: readonly(theme),
    language: readonly(language),
    sidebarCollapsed: readonly(sidebarCollapsed),
    compactMode: readonly(compactMode),
    animationsEnabled: readonly(animationsEnabled),
    soundEnabled: readonly(soundEnabled),
    highContrast: readonly(highContrast),
    reducedMotion: readonly(reducedMotion),
    isOnline: readonly(isOnline),
    systemInfo: readonly(systemInfo),
    currentRoute: readonly(currentRoute),
    breadcrumbs: readonly(breadcrumbs),
    headerHeight: readonly(headerHeight),
    sidebarWidth: readonly(sidebarWidth),
    sidebarCollapsedWidth: readonly(sidebarCollapsedWidth),
    contentPadding: readonly(contentPadding),
    isInitializing: readonly(isInitializing),
    globalLoading: readonly(globalLoading),
    loadingMessage: readonly(loadingMessage),
    showCommandPalette: readonly(showCommandPalette),
    showSearch: readonly(showSearch),
    showSettings: readonly(showSettings),
    feedbackModal: readonly(feedbackModal),

    // Getters
    effectiveTheme,
    isDarkMode,
    isLightMode,
    currentSidebarWidth,
    isMobile,
    isTablet,
    isDesktop,
    shouldReduceMotion,
    preferences,

    // Actions
    setTheme,
    setLanguage,
    toggleSidebar,
    setSidebarCollapsed,
    setCompactMode,
    toggleAnimations,
    toggleSound,
    toggleHighContrast,
    toggleReducedMotion,
    updatePreferences,
    setCurrentRoute,
    setBreadcrumbs,
    setGlobalLoading,
    toggleCommandPalette,
    toggleSearch,
    toggleSettings,
    showFeedbackModal,
    closeFeedbackModal,
    initialize,
    setupKeyboardShortcuts,
  };
});

// Readonly helper
function readonly<T>(ref: Ref<T>): Readonly<Ref<T>> {
  return ref as Readonly<Ref<T>>;
}

export type AppStore = ReturnType<typeof useAppStore>;