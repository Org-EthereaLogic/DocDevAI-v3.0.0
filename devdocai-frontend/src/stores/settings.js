import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useSettingsStore = defineStore('settings', () => {
  // State
  const theme = ref('system'); // 'light', 'dark', 'system'
  const language = ref('en');
  const timezone = ref(Intl.DateTimeFormat().resolvedOptions().timeZone);
  const dateFormat = ref('YYYY-MM-DD');
  const timeFormat = ref('24h'); // '12h', '24h'

  // Privacy settings
  const privacyMode = ref('standard'); // 'strict', 'standard', 'minimal'
  const telemetryEnabled = ref(false);
  const crashReportingEnabled = ref(false);
  const analyticsEnabled = ref(false);

  // AI settings
  const aiProvider = ref('openai'); // 'openai', 'anthropic', 'gemini', 'local'
  const aiModel = ref('gpt-4');
  const maxTokens = ref(4000);
  const temperature = ref(0.7);
  const costBudget = ref(10.00); // Daily budget in USD
  const costAlerts = ref(true);

  // Interface settings
  const tooltipsEnabled = ref(true);
  const animationsEnabled = ref(true);
  const compactMode = ref(false);
  const sidebarCollapsed = ref(false);
  const autoSave = ref(true);
  const autoSaveInterval = ref(30); // seconds

  // Document generation settings
  const defaultDocumentType = ref('readme');
  const includeGenerationMetadata = ref(true);
  const enableVersioning = ref(true);
  const backupEnabled = ref(true);
  const maxBackups = ref(10);

  // Performance settings
  const memoryMode = ref('auto'); // 'low', 'medium', 'high', 'auto'
  const batchSize = ref(50);
  const parallelProcessing = ref(true);
  const cacheEnabled = ref(true);
  const cacheTTL = ref(3600); // seconds

  // Notification settings
  const notificationsEnabled = ref(true);
  const emailNotifications = ref(false);
  const soundEnabled = ref(false);
  const notificationTypes = ref({
    documentGenerated: true,
    batchCompleted: true,
    errors: true,
    warnings: true,
    costAlerts: true,
    systemUpdates: false
  });

  // Computed
  const isDarkMode = computed(() => {
    if (theme.value === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return theme.value === 'dark';
  });

  const isPrivacyStrict = computed(() => privacyMode.value === 'strict');
  const isCostBudgetExceeded = computed(() => {
    // This would be calculated from actual usage
    return false;
  });

  const currentLocale = computed(() => {
    const localeMap = {
      'en': 'en-US',
      'es': 'es-ES',
      'fr': 'fr-FR',
      'de': 'de-DE',
      'ja': 'ja-JP',
      'zh': 'zh-CN'
    };
    return localeMap[language.value] || 'en-US';
  });

  // Actions
  const updateTheme = (newTheme) => {
    theme.value = newTheme;
    applyTheme();
  };

  const applyTheme = () => {
    const html = document.documentElement;
    html.classList.remove('light', 'dark');

    if (theme.value === 'system') {
      // Let CSS handle system preference
      return;
    }

    html.classList.add(theme.value);
  };

  const updatePrivacyMode = (mode) => {
    privacyMode.value = mode;

    // Apply privacy settings
    if (mode === 'strict') {
      telemetryEnabled.value = false;
      crashReportingEnabled.value = false;
      analyticsEnabled.value = false;
    } else if (mode === 'minimal') {
      telemetryEnabled.value = false;
      crashReportingEnabled.value = true;
      analyticsEnabled.value = false;
    }
  };

  const updateAISettings = (settings) => {
    Object.keys(settings).forEach(key => {
      if (key === 'provider') aiProvider.value = settings[key];
      else if (key === 'model') aiModel.value = settings[key];
      else if (key === 'maxTokens') maxTokens.value = settings[key];
      else if (key === 'temperature') temperature.value = settings[key];
      else if (key === 'budget') costBudget.value = settings[key];
    });
  };

  const updateNotificationSetting = (type, enabled) => {
    if (type === 'all') {
      notificationsEnabled.value = enabled;
    } else if (notificationTypes.value.hasOwnProperty(type)) {
      notificationTypes.value[type] = enabled;
    }
  };

  const resetToDefaults = () => {
    theme.value = 'system';
    language.value = 'en';
    privacyMode.value = 'standard';
    telemetryEnabled.value = false;
    aiProvider.value = 'openai';
    aiModel.value = 'gpt-4';
    temperature.value = 0.7;
    costBudget.value = 10.00;
    tooltipsEnabled.value = true;
    animationsEnabled.value = true;
    compactMode.value = false;
    autoSave.value = true;
    autoSaveInterval.value = 30;
    notificationsEnabled.value = true;
    emailNotifications.value = false;
    soundEnabled.value = false;
  };

  const exportSettings = () => {
    return {
      theme: theme.value,
      language: language.value,
      timezone: timezone.value,
      dateFormat: dateFormat.value,
      timeFormat: timeFormat.value,
      privacyMode: privacyMode.value,
      telemetryEnabled: telemetryEnabled.value,
      crashReportingEnabled: crashReportingEnabled.value,
      analyticsEnabled: analyticsEnabled.value,
      aiProvider: aiProvider.value,
      aiModel: aiModel.value,
      maxTokens: maxTokens.value,
      temperature: temperature.value,
      costBudget: costBudget.value,
      costAlerts: costAlerts.value,
      tooltipsEnabled: tooltipsEnabled.value,
      animationsEnabled: animationsEnabled.value,
      compactMode: compactMode.value,
      autoSave: autoSave.value,
      autoSaveInterval: autoSaveInterval.value,
      defaultDocumentType: defaultDocumentType.value,
      includeGenerationMetadata: includeGenerationMetadata.value,
      enableVersioning: enableVersioning.value,
      backupEnabled: backupEnabled.value,
      maxBackups: maxBackups.value,
      memoryMode: memoryMode.value,
      batchSize: batchSize.value,
      parallelProcessing: parallelProcessing.value,
      cacheEnabled: cacheEnabled.value,
      cacheTTL: cacheTTL.value,
      notificationsEnabled: notificationsEnabled.value,
      emailNotifications: emailNotifications.value,
      soundEnabled: soundEnabled.value,
      notificationTypes: { ...notificationTypes.value }
    };
  };

  const importSettings = (settings) => {
    Object.keys(settings).forEach(key => {
      if (key === 'theme') theme.value = settings[key];
      else if (key === 'language') language.value = settings[key];
      else if (key === 'timezone') timezone.value = settings[key];
      else if (key === 'dateFormat') dateFormat.value = settings[key];
      else if (key === 'timeFormat') timeFormat.value = settings[key];
      else if (key === 'privacyMode') privacyMode.value = settings[key];
      else if (key === 'telemetryEnabled') telemetryEnabled.value = settings[key];
      else if (key === 'crashReportingEnabled') crashReportingEnabled.value = settings[key];
      else if (key === 'analyticsEnabled') analyticsEnabled.value = settings[key];
      else if (key === 'aiProvider') aiProvider.value = settings[key];
      else if (key === 'aiModel') aiModel.value = settings[key];
      else if (key === 'maxTokens') maxTokens.value = settings[key];
      else if (key === 'temperature') temperature.value = settings[key];
      else if (key === 'costBudget') costBudget.value = settings[key];
      else if (key === 'costAlerts') costAlerts.value = settings[key];
      else if (key === 'tooltipsEnabled') tooltipsEnabled.value = settings[key];
      else if (key === 'animationsEnabled') animationsEnabled.value = settings[key];
      else if (key === 'compactMode') compactMode.value = settings[key];
      else if (key === 'autoSave') autoSave.value = settings[key];
      else if (key === 'autoSaveInterval') autoSaveInterval.value = settings[key];
      else if (key === 'defaultDocumentType') defaultDocumentType.value = settings[key];
      else if (key === 'includeGenerationMetadata') includeGenerationMetadata.value = settings[key];
      else if (key === 'enableVersioning') enableVersioning.value = settings[key];
      else if (key === 'backupEnabled') backupEnabled.value = settings[key];
      else if (key === 'maxBackups') maxBackups.value = settings[key];
      else if (key === 'memoryMode') memoryMode.value = settings[key];
      else if (key === 'batchSize') batchSize.value = settings[key];
      else if (key === 'parallelProcessing') parallelProcessing.value = settings[key];
      else if (key === 'cacheEnabled') cacheEnabled.value = settings[key];
      else if (key === 'cacheTTL') cacheTTL.value = settings[key];
      else if (key === 'notificationsEnabled') notificationsEnabled.value = settings[key];
      else if (key === 'emailNotifications') emailNotifications.value = settings[key];
      else if (key === 'soundEnabled') soundEnabled.value = settings[key];
      else if (key === 'notificationTypes') {
        notificationTypes.value = { ...notificationTypes.value, ...settings[key] };
      }
    });

    // Apply theme after import
    applyTheme();
  };

  // Initialize theme on store creation
  const initializeTheme = () => {
    applyTheme();

    // Listen for system theme changes
    if (theme.value === 'system') {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', applyTheme);
    }
  };

  // Detect system capabilities
  const detectSystemCapabilities = () => {
    // Detect memory
    if ('deviceMemory' in navigator) {
      const memory = navigator.deviceMemory;
      if (memory <= 2) memoryMode.value = 'low';
      else if (memory <= 4) memoryMode.value = 'medium';
      else memoryMode.value = 'high';
    }

    // Detect connection
    if ('connection' in navigator) {
      const connection = navigator.connection;
      if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
        animationsEnabled.value = false;
        batchSize.value = 10;
      }
    }
  };

  // Reset store
  const $reset = () => {
    resetToDefaults();
  };

  return {
    // State
    theme,
    language,
    timezone,
    dateFormat,
    timeFormat,
    privacyMode,
    telemetryEnabled,
    crashReportingEnabled,
    analyticsEnabled,
    aiProvider,
    aiModel,
    maxTokens,
    temperature,
    costBudget,
    costAlerts,
    tooltipsEnabled,
    animationsEnabled,
    compactMode,
    sidebarCollapsed,
    autoSave,
    autoSaveInterval,
    defaultDocumentType,
    includeGenerationMetadata,
    enableVersioning,
    backupEnabled,
    maxBackups,
    memoryMode,
    batchSize,
    parallelProcessing,
    cacheEnabled,
    cacheTTL,
    notificationsEnabled,
    emailNotifications,
    soundEnabled,
    notificationTypes,

    // Computed
    isDarkMode,
    isPrivacyStrict,
    isCostBudgetExceeded,
    currentLocale,

    // Actions
    updateTheme,
    applyTheme,
    updatePrivacyMode,
    updateAISettings,
    updateNotificationSetting,
    resetToDefaults,
    exportSettings,
    importSettings,
    initializeTheme,
    detectSystemCapabilities,
    $reset
  };
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'settings',
        storage: localStorage,
        paths: [
          'theme',
          'language',
          'timezone',
          'dateFormat',
          'timeFormat',
          'privacyMode',
          'telemetryEnabled',
          'crashReportingEnabled',
          'analyticsEnabled',
          'aiProvider',
          'aiModel',
          'maxTokens',
          'temperature',
          'costBudget',
          'costAlerts',
          'tooltipsEnabled',
          'animationsEnabled',
          'compactMode',
          'sidebarCollapsed',
          'autoSave',
          'autoSaveInterval',
          'defaultDocumentType',
          'includeGenerationMetadata',
          'enableVersioning',
          'backupEnabled',
          'maxBackups',
          'memoryMode',
          'batchSize',
          'parallelProcessing',
          'cacheEnabled',
          'cacheTTL',
          'notificationsEnabled',
          'emailNotifications',
          'soundEnabled',
          'notificationTypes'
        ]
      }
    ]
  }
});
