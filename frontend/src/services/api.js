import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout
});

// Add auth token to requests
apiClient.interceptors.request.use(
  (config) => {
    const apiKey = localStorage.getItem('api_key');
    if (apiKey) {
      config.headers.Authorization = `Bearer ${apiKey}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Handle errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth on 401 and redirect to login
      localStorage.removeItem('api_key');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login?reason=unauthorized';
      }
    } else if (error.response?.status === 403) {
      console.error('Access forbidden:', error.response.data);
    } else if (error.code === 'ECONNABORTED') {
      error.message = 'Request timeout - server not responding';
    } else if (!error.response) {
      error.message = 'Network error - check your connection';
    }
    return Promise.reject(error);
  }
);

// API methods
export const api = {
  // ==================== AUTH ====================
  login: (email, password) =>
    apiClient.post('/auth/login', { email, password }),

  logout: () =>
    apiClient.post('/auth/logout'),

  signup: (email, password) =>
    apiClient.post('/auth/signup', { email, password }),

  verifyEmail: (token) =>
    apiClient.post('/auth/verify-email', { token }),

  requestVerification: (email) =>
    apiClient.post('/auth/request-verification', { email }),

  getMe: () =>
    apiClient.get('/auth/me'),

  updatePassword: (currentPassword, newPassword) =>
    apiClient.patch('/auth/me/password', { current_password: currentPassword, new_password: newPassword }),

  // ==================== OAUTH ====================
  getOAuthUrl: (provider) =>
    apiClient.get(`/auth/oauth/${provider}`),

  oauthCallback: (provider, code, state) =>
    apiClient.post(`/auth/oauth/${provider}/callback`, { code, state }),

  // ==================== PERSONAS ====================
  listPersonas: (filters = {}) =>
    apiClient.get('/v1/personas', { params: filters }),

  getPersona: (personaId) =>
    apiClient.get(`/v1/personas/${personaId}`),

  compilePersona: (personaId, tier = 'standard') =>
    apiClient.post(`/v1/compile`, { persona_id: personaId, tier }),

  getPersonaVector: (personaId) =>
    apiClient.get(`/v1/personas/${personaId}/vector`),

  // ==================== PURCHASES ====================
  getPurchases: () =>
    apiClient.get('/v1/purchases'),

  purchasePersona: (personaId) =>
    apiClient.post('/v1/purchases', { persona_id: personaId }),

  refundPurchase: (purchaseId) =>
    apiClient.post(`/v1/purchases/${purchaseId}/refund`),

  // ==================== CATALOG ====================
  getCatalog: () =>
    apiClient.get('/v1/catalog'),

  searchCatalog: (query) =>
    apiClient.get('/v1/catalog/search', { params: { q: query } }),

  // ==================== ANALYTICS ====================
  getDashboard: () =>
    apiClient.get('/analytics/dashboard'),

  getTopPersonas: (limit = 10) =>
    apiClient.get('/analytics/personas/top', { params: { limit } }),

  getPersonaStats: (personaId) =>
    apiClient.get(`/analytics/personas/${personaId}`),

  getUserStats: (userId) =>
    apiClient.get(`/analytics/users/${userId}`),

  getRevenueReport: () =>
    apiClient.get('/analytics/revenue'),

  getDAU: () =>
    apiClient.get('/analytics/dau'),

  getRetention: () =>
    apiClient.get('/analytics/retention'),

  exportAnalytics: (format = 'csv') =>
    apiClient.get(`/analytics/export/${format}`, { responseType: 'blob' }),

  // ==================== CACHE ====================
  getCacheHealth: () =>
    apiClient.get('/cache/health'),

  getCacheStats: () =>
    apiClient.get('/cache/stats'),

  flushCache: () =>
    apiClient.delete('/cache/flush'),

  flushPersonaCache: (personaId) =>
    apiClient.delete(`/cache/personas/${personaId}`),

  // ==================== STRIPE ====================
  createCheckoutSession: (personaId) =>
    apiClient.post('/v1/checkout', { persona_id: personaId }),

  getCheckoutSession: (sessionId) =>
    apiClient.get(`/v1/checkout/${sessionId}`),

  // ==================== HEALTH ====================
  getHealth: () =>
    apiClient.get('/health'),
};

// Helper to handle errors with user-friendly messages
export const getErrorMessage = (error) => {
  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error.response?.status === 404) {
    return 'Resource not found';
  }
  if (error.response?.status === 422) {
    return 'Invalid input - please check your data';
  }
  if (error.message === 'Network error - check your connection') {
    return 'Network error - please check your internet connection';
  }
  return error.message || 'An unexpected error occurred';
};

export default apiClient;
