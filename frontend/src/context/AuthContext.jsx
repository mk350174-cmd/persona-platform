import React, { createContext, useState, useEffect } from 'react';
import { api } from '../services/api';

export const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check if user is logged in on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const apiKey = localStorage.getItem('api_key');
        if (apiKey) {
          const response = await api.getMe();
          setUser(response.data);
        }
      } catch (err) {
        console.error('Auth check failed:', err);
        localStorage.removeItem('api_key');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email, password) => {
    try {
      setError(null);
      const response = await api.login(email, password);
      const { api_key } = response.data;
      localStorage.setItem('api_key', api_key);
      setUser(response.data);
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || 'Login failed';
      setError(message);
      throw err;
    }
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      localStorage.removeItem('api_key');
      setUser(null);
    }
  };

  const requestVerification = async (email) => {
    try {
      setError(null);
      await api.requestVerification(email);
    } catch (err) {
      const message = err.response?.data?.detail || 'Verification request failed';
      setError(message);
      throw err;
    }
  };

  const verifyEmail = async (token) => {
    try {
      setError(null);
      await api.verifyEmail(token);
    } catch (err) {
      const message = err.response?.data?.detail || 'Verification failed';
      setError(message);
      throw err;
    }
  };

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
    requestVerification,
    verifyEmail,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
