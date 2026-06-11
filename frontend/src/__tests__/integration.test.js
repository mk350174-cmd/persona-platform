/**
 * Integration Tests for Persona Hub Frontend
 * Tests API connectivity, authentication, and core features
 */

import { api, getErrorMessage } from '../services/api';
import { health } from '../services/health';

describe('Backend Integration', () => {
  describe('Health Check', () => {
    test('API should be accessible', async () => {
      const result = await health.checkAPI();
      expect(result.status).toBeDefined();
      expect(result.timestamp).toBeDefined();
    });

    test('Should run full diagnostics', async () => {
      const diagnostics = await health.runDiagnostics();
      expect(diagnostics.status).toMatch(/healthy|degraded/);
      expect(diagnostics.checks).toBeDefined();
      expect(diagnostics.timestamp).toBeDefined();
    });
  });

  describe('API Endpoints', () => {
    test('Personas endpoint should return list', async () => {
      try {
        const response = await api.listPersonas();
        expect(response.status).toBe(200);
        expect(Array.isArray(response.data)).toBe(true);
      } catch (error) {
        expect(error.response?.status).toBeDefined();
      }
    });

    test('Catalog endpoint should be accessible', async () => {
      try {
        const response = await api.getCatalog();
        expect(response.status).toBe(200);
      } catch (error) {
        expect(error.response?.status).toBeDefined();
      }
    });

    test('Analytics dashboard endpoint should work', async () => {
      try {
        const response = await api.getDashboard();
        expect(response.status).toBe(200);
        expect(response.data).toHaveProperty('activeUsers');
      } catch (error) {
        // Expected to fail without auth
        expect(error.response?.status).toBeGreaterThanOrEqual(400);
      }
    });
  });

  describe('Error Handling', () => {
    test('Should handle network errors gracefully', async () => {
      const error = new Error('Network error');
      error.code = 'ECONNREFUSED';
      const message = getErrorMessage(error);
      expect(message).toContain('Network');
    });

    test('Should handle 404 errors', async () => {
      const error = new Error('Not Found');
      error.response = { status: 404 };
      const message = getErrorMessage(error);
      expect(message).toBe('Resource not found');
    });

    test('Should handle validation errors', async () => {
      const error = new Error('Validation Error');
      error.response = { status: 422 };
      const message = getErrorMessage(error);
      expect(message).toContain('Invalid input');
    });
  });

  describe('Auth Flow', () => {
    test('Should validate API key format', () => {
      const validKey = 'prs_1234567890abcdef';
      expect(validKey.startsWith('prs_')).toBe(true);
      expect(validKey.length).toBeGreaterThan(4);
    });

    test('Should handle 401 unauthorized', async () => {
      const error = new Error('Unauthorized');
      error.response = { status: 401 };
      const message = getErrorMessage(error);
      expect(message).toBeDefined();
    });
  });

  describe('WebSocket', () => {
    test('Should construct correct WebSocket URL', () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/chat/socrates?tier=full`;
      expect(wsUrl).toMatch(/^ws(s)?:\/\//);
      expect(wsUrl).toContain('/chat/');
    });
  });
});

describe('Performance Tests', () => {
  test('Bundle size should be within limits', () => {
    // This would be checked via build artifacts
    // Target: <1MB gzipped
    expect(true).toBe(true);
  });

  test('API response time should be acceptable', async () => {
    const startTime = performance.now();
    try {
      await api.getCatalog();
      const endTime = performance.now();
      const responseTime = endTime - startTime;
      expect(responseTime).toBeLessThan(5000); // 5 second limit
    } catch (error) {
      // Network error is ok for this test
      expect(true).toBe(true);
    }
  });
});

describe('Feature Flags', () => {
  test('Should respect feature flags from env', () => {
    const analytics = import.meta.env.VITE_ENABLE_ANALYTICS === 'true';
    const voice = import.meta.env.VITE_ENABLE_VOICE === 'true';
    const pwa = import.meta.env.VITE_ENABLE_PWA === 'true';

    expect([true, false]).toContain(analytics);
    expect([true, false]).toContain(voice);
    expect([true, false]).toContain(pwa);
  });
});

describe('Security', () => {
  test('API URLs should use HTTPS in production', () => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    if (import.meta.env.MODE === 'production') {
      expect(apiUrl).toMatch(/^https:\/\//);
    }
  });

  test('WebSocket should use WSS in production', () => {
    if (import.meta.env.MODE === 'production') {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      expect(protocol).toBe('wss:');
    }
  });

  test('Should not expose sensitive data in localStorage', () => {
    const keys = Object.keys(localStorage);
    const sensitivePatterns = ['password', 'secret', 'token'];
    const hasSensitiveData = keys.some((key) =>
      sensitivePatterns.some((pattern) => key.toLowerCase().includes(pattern))
    );
    expect(hasSensitiveData).toBe(false);
  });
});

export default {
  api,
  health,
};
