import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useOnboardingStore = defineStore('onboarding', () => {
  // State
  const currentStep = ref(0);
  const totalSteps = ref(4);
  const isCompleted = ref(false);
  const skipped = ref(false);
  const completedSteps = ref([]);
  const userPreferences = ref({
    privacyMode: null,
    theme: 'system',
    tooltipsEnabled: true,
    aiProvider: null,
    projectType: null
  });

  // Onboarding steps configuration
  const steps = ref([
    {
      id: 'welcome',
      title: 'Welcome to DevDocAI',
      description: 'Your AI-powered documentation assistant',
      completed: false
    },
    {
      id: 'privacy',
      title: 'Choose Your Privacy Mode',
      description: 'Control how your data is processed',
      completed: false
    },
    {
      id: 'features',
      title: 'Key Features',
      description: 'Learn what DevDocAI can do for you',
      completed: false
    },
    {
      id: 'setup',
      title: 'Quick Setup',
      description: 'Configure your preferences',
      completed: false
    }
  ]);

  // Computed
  const progress = computed(() => {
    if (totalSteps.value === 0) return 0;
    return Math.round((completedSteps.value.length / totalSteps.value) * 100);
  });

  const currentStepData = computed(() => steps.value[currentStep.value]);

  const canProceed = computed(() => {
    const step = steps.value[currentStep.value];
    if (step.id === 'privacy' && !userPreferences.value.privacyMode) {
      return false;
    }
    return true;
  });

  const isFirstStep = computed(() => currentStep.value === 0);
  const isLastStep = computed(() => currentStep.value === totalSteps.value - 1);

  // Actions
  const nextStep = () => {
    if (currentStep.value < totalSteps.value - 1) {
      // Mark current step as completed
      const stepId = steps.value[currentStep.value].id;
      if (!completedSteps.value.includes(stepId)) {
        completedSteps.value.push(stepId);
        steps.value[currentStep.value].completed = true;
      }

      currentStep.value++;
      return true;
    }
    return false;
  };

  const previousStep = () => {
    if (currentStep.value > 0) {
      currentStep.value--;
      return true;
    }
    return false;
  };

  const goToStep = (stepIndex) => {
    if (stepIndex >= 0 && stepIndex < totalSteps.value) {
      currentStep.value = stepIndex;
      return true;
    }
    return false;
  };

  const completeOnboarding = () => {
    // Mark final step as completed
    const stepId = steps.value[currentStep.value].id;
    if (!completedSteps.value.includes(stepId)) {
      completedSteps.value.push(stepId);
      steps.value[currentStep.value].completed = true;
    }

    // TODO: Apply user preferences to settings store when available

    isCompleted.value = true;

    // Store completion in localStorage
    localStorage.setItem('onboarding_completed', 'true');
    localStorage.setItem('onboarding_date', new Date().toISOString());
  };

  const skipOnboarding = () => {
    skipped.value = true;
    isCompleted.value = true;
    localStorage.setItem('onboarding_completed', 'true');
    localStorage.setItem('onboarding_skipped', 'true');
  };

  const resetOnboarding = () => {
    currentStep.value = 0;
    isCompleted.value = false;
    skipped.value = false;
    completedSteps.value = [];
    steps.value.forEach(step => {
      step.completed = false;
    });
    userPreferences.value = {
      privacyMode: null,
      theme: 'system',
      tooltipsEnabled: true,
      aiProvider: null,
      projectType: null
    };

    // Clear localStorage
    localStorage.removeItem('onboarding_completed');
    localStorage.removeItem('onboarding_skipped');
    localStorage.removeItem('onboarding_date');
  };

  const updatePreference = (key, value) => {
    userPreferences.value[key] = value;
  };

  const initializeOnboarding = () => {
    // Check if onboarding was completed before
    const completed = localStorage.getItem('onboarding_completed');
    if (completed === 'true') {
      isCompleted.value = true;
      const wasSkipped = localStorage.getItem('onboarding_skipped');
      if (wasSkipped === 'true') {
        skipped.value = true;
      }
    }
  };

  // Tutorial helpers for specific features
  const showFeatureTutorial = (featureName) => {
    // This can be used to show mini-tutorials for specific features
    // after onboarding is complete
    const tutorials = {
      documentGeneration: {
        title: 'Generate Your First Document',
        steps: [
          'Select document type',
          'Fill in project details',
          'Choose AI settings',
          'Review and generate'
        ]
      },
      trackingMatrix: {
        title: 'Understanding Dependencies',
        steps: [
          'View document relationships',
          'Identify impact paths',
          'Track consistency'
        ]
      },
      healthScore: {
        title: 'Document Health Score',
        description: 'Health Score = Quality + Consistency + Completeness',
        explanation: {
          excellent: '85%+ = Professional documentation',
          good: '70-84% = Good, needs some improvements',
          needsWork: 'Below 70% = Requires attention'
        }
      }
    };

    return tutorials[featureName] || null;
  };

  // Reset store
  const $reset = () => {
    currentStep.value = 0;
    isCompleted.value = false;
    skipped.value = false;
    completedSteps.value = [];
    userPreferences.value = {
      privacyMode: null,
      theme: 'system',
      tooltipsEnabled: true,
      aiProvider: null,
      projectType: null
    };
  };

  return {
    // State
    currentStep,
    totalSteps,
    isCompleted,
    skipped,
    completedSteps,
    userPreferences,
    steps,

    // Computed
    progress,
    currentStepData,
    canProceed,
    isFirstStep,
    isLastStep,

    // Actions
    nextStep,
    previousStep,
    goToStep,
    completeOnboarding,
    skipOnboarding,
    resetOnboarding,
    updatePreference,
    initializeOnboarding,
    showFeatureTutorial,
    $reset
  };
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'onboarding',
        storage: localStorage,
        paths: ['isCompleted', 'skipped', 'userPreferences']
      }
    ]
  }
});
