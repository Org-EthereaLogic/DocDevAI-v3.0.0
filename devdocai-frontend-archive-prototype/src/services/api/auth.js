import apiClient from './index';

export const authAPI = {
  // Login
  login: async (credentials) => {
    // Mock login for now
    return {
      data: {
        user: { name: 'Test User', email: credentials.email },
        token: 'mock-token',
        refreshToken: 'mock-refresh-token',
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      }
    };
  },

  // Logout
  logout: async () => {
    return { data: { message: 'Logged out successfully' } };
  },

  // Refresh token
  refresh: async (refreshToken) => {
    return {
      data: {
        token: 'new-mock-token',
        refreshToken: 'new-mock-refresh-token',
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      }
    };
  },

  // Verify token
  verify: async () => {
    return { data: { valid: true } };
  },

  // Update profile
  updateProfile: async (updates) => {
    return {
      data: {
        user: { name: 'Updated User', email: 'updated@example.com', ...updates }
      }
    };
  }
};
