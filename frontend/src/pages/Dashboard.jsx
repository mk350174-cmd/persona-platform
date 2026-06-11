import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useTranslation } from 'react-i18next';
import AnalyticsCharts from '../components/AnalyticsCharts';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const loadStats = async () => {
      try {
        // In real app, would call: const response = await api.getDashboard();
        // For now, set sample data
        setStats({
          activeUsers: 1234,
          dailyMessages: 5678,
          revenue: 12345,
          avgRating: 4.8,
        });
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  if (loading) return <div className="flex items-center justify-center min-h-screen">{t('common.loading')}</div>;

  return (
    <div className="pt-20 px-margin-desktop max-w-container-max mx-auto pb-20">
      <h1 className="font-headline-md text-headline-md text-on-surface mb-8 mt-8">
        {t('dashboard.title')}
      </h1>

      {error && (
        <div className="p-4 rounded-lg bg-error/20 text-error mb-8">
          {error}
        </div>
      )}

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="glass-panel rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-on-surface-variant text-sm mb-2">{t('dashboard.activeUsers')}</p>
              <p className="text-4xl font-headline-md text-on-surface">
                {stats?.activeUsers?.toLocaleString()}
              </p>
            </div>
            <span className="text-4xl">👥</span>
          </div>
        </div>
        <div className="glass-panel rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-on-surface-variant text-sm mb-2">{t('dashboard.dailyMessages')}</p>
              <p className="text-4xl font-headline-md text-on-surface">
                {stats?.dailyMessages?.toLocaleString()}
              </p>
            </div>
            <span className="text-4xl">💬</span>
          </div>
        </div>
        <div className="glass-panel rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-on-surface-variant text-sm mb-2">{t('dashboard.revenue')}</p>
              <p className="text-4xl font-headline-md text-on-surface">
                ${stats?.revenue?.toLocaleString()}
              </p>
            </div>
            <span className="text-4xl">💰</span>
          </div>
        </div>
        <div className="glass-panel rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-on-surface-variant text-sm mb-2">Avg Rating</p>
              <p className="text-4xl font-headline-md text-on-surface">
                {stats?.avgRating}★
              </p>
            </div>
            <span className="text-4xl">⭐</span>
          </div>
        </div>
      </div>

      {/* Analytics Charts */}
      <AnalyticsCharts />
    </div>
  );
}
