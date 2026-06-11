import { api, getErrorMessage } from './api';

/**
 * Health check service for monitoring backend connectivity
 * and service status
 */

export const health = {
  /**
   * Check if backend API is accessible
   */
  checkAPI: async () => {
    try {
      const response = await api.getHealth();
      return {
        status: 'ok',
        timestamp: new Date().toISOString(),
        data: response.data,
      };
    } catch (error) {
      return {
        status: 'error',
        timestamp: new Date().toISOString(),
        error: getErrorMessage(error),
      };
    }
  },

  /**
   * Verify API key is valid
   */
  verifyAPIKey: async () => {
    try {
      const response = await api.getMe();
      return {
        status: 'ok',
        user: response.data,
      };
    } catch (error) {
      return {
        status: 'error',
        error: getErrorMessage(error),
      };
    }
  },

  /**
   * Check cache service health
   */
  checkCache: async () => {
    try {
      const response = await api.getCacheHealth();
      return {
        status: 'ok',
        cache: response.data,
      };
    } catch (error) {
      return {
        status: 'error',
        error: getErrorMessage(error),
      };
    }
  },

  /**
   * Run full health check suite
   */
  runDiagnostics: async () => {
    const results = {
      timestamp: new Date().toISOString(),
      checks: {},
    };

    // Check API connectivity
    results.checks.api = await health.checkAPI();

    // Check authentication (only if API is healthy)
    if (localStorage.getItem('api_key')) {
      results.checks.auth = await health.verifyAPIKey();
    }

    // Check cache (only if API is healthy)
    if (results.checks.api.status === 'ok') {
      results.checks.cache = await health.checkCache();
    }

    // Overall status
    results.status = Object.values(results.checks).every((check) => check.status === 'ok')
      ? 'healthy'
      : 'degraded';

    return results;
  },

  /**
   * Monitor API connectivity with periodic checks
   */
  startMonitoring: (intervalMs = 30000, callback) => {
    const checkHealth = async () => {
      const result = await health.checkAPI();
      if (callback) {
        callback(result);
      }
    };

    // Initial check
    checkHealth();

    // Periodic checks
    const intervalId = setInterval(checkHealth, intervalMs);

    // Return stop function
    return () => clearInterval(intervalId);
  },

  /**
   * Log diagnostics to console and optionally send to backend
   */
  reportDiagnostics: async (sendToBackend = false) => {
    const diagnostics = await health.runDiagnostics();

    console.group('🏥 Persona Hub Health Check');
    console.log('Status:', diagnostics.status);
    console.table(diagnostics.checks);
    console.groupEnd();

    if (sendToBackend && diagnostics.status !== 'healthy') {
      try {
        // Send diagnostics to backend logging endpoint
        await fetch('/api/v1/diagnostics', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(diagnostics),
        });
      } catch (err) {
        console.error('Failed to send diagnostics:', err);
      }
    }

    return diagnostics;
  },
};

export default health;
