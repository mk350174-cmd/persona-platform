import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
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

// Handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear auth on 401
      localStorage.removeItem('api_key');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// API methods
export const api = {
  // Auth
  login: (email, password) => apiClient.post('/auth/login', { email, password }),
  logout: () => apiClient.post('/auth/logout'),
  verifyEmail: (token) => apiClient.post('/auth/verify-email', { token }),
  requestVerification: (email) => apiClient.post('/auth/request-verification', { email }),
  getMe: () => apiClient.get('/auth/me'),

  // OAuth
  getOAuthUrl: (provider) => apiClient.get(`/auth/oauth/${provider}`),
  oauthCallback: (provider, code, state) =>
    apiClient.post(`/auth/oauth/${provider}/callback`, { code, state }),

  // Personas
  listPersonas: (filters = {}) => apiClient.get('/v1/personas', { params: filters }),
  getPersona: (personaId) => apiClient.get(`/v1/personas/${personaId}`),
  compilePersona: (personaId) => apiClient.post(`/v1/compile`, { persona_id: personaId }),

  // Purchases
  getPurchases: () => apiClient.get('/v1/purchases'),
  purchasePersona: (personaId) => apiClient.post('/v1/purchases', { persona_id: personaId }),

  // Catalog
  getCatalog: () => apiClient.get('/v1/catalog'),

  // Analytics
  getDashboard: () => apiClient.get('/analytics/dashboard'),
  getTopPersonas: () => apiClient.get('/analytics/personas/top'),
  getPersonaStats: (personaId) => apiClient.get(`/analytics/personas/${personaId}`),
  getUserStats: (userId) => apiClient.get(`/analytics/users/${userId}`),
  getRevenueReport: () => apiClient.get('/analytics/revenue'),
  getDAU: () => apiClient.get('/analytics/dau'),
  getRetention: () => apiClient.get('/analytics/retention'),
  exportAnalytics: (format = 'csv') => apiClient.get(`/analytics/export/${format}`),

  // Cache
  getCacheHealth: () => apiClient.get('/cache/health'),
  getCacheStats: () => apiClient.get('/cache/stats'),
  flushCache: () => apiClient.delete('/cache/flush'),
};

export default apiClient;
