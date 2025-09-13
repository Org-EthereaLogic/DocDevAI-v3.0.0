import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref(null);
  const token = ref(null);
  const refreshToken = ref(null);
  const isLoading = ref(false);
  const error = ref(null);
  const intendedRoute = ref(null);
  const sessionExpiry = ref(null);

  // Computed
  const isAuthenticated = computed(() => !!token.value && !!user.value);

  const userInitials = computed(() => {
    if (!user.value?.name) return 'U';
    const names = user.value.name.split(' ');
    if (names.length >= 2) {
      return `${names[0][0]}${names[names.length - 1][0]}`.toUpperCase();
    }
    return names[0].substring(0, 2).toUpperCase();
  });

  const isSessionExpired = computed(() => {
    if (!sessionExpiry.value) return false;
    return new Date() > new Date(sessionExpiry.value);
  });

  // Actions (simplified for now)
  const login = async (credentials) => {
    isLoading.value = true;
    error.value = null;

    try {
      // Mock login for now
      user.value = { name: 'Test User', email: credentials.email };
      token.value = 'mock-token';

      return { success: true };
    } catch (err) {
      error.value = err.message || 'Login failed';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };

  const logout = async () => {
    user.value = null;
    token.value = null;
    refreshToken.value = null;
    sessionExpiry.value = null;
  };

  const setIntendedRoute = (route) => {
    intendedRoute.value = route;
  };

  // Reset store
  const $reset = () => {
    user.value = null;
    token.value = null;
    refreshToken.value = null;
    isLoading.value = false;
    error.value = null;
    intendedRoute.value = null;
    sessionExpiry.value = null;
  };

  return {
    // State
    user,
    token,
    isLoading,
    error,
    sessionExpiry,

    // Computed
    isAuthenticated,
    userInitials,
    isSessionExpired,

    // Actions
    login,
    logout,
    setIntendedRoute,
    $reset
  };
}, {
  persist: {
    enabled: true,
    strategies: [
      {
        key: 'auth',
        storage: localStorage,
        paths: ['user', 'token', 'refreshToken', 'sessionExpiry']
      }
    ]
  }
});
