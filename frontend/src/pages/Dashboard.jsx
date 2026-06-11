import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useTranslation } from 'react-i18next';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const loadStats = async () => {
      try {
        const response = await api.getDashboard();
        setStats(response.data);
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="glass-panel rounded-xl p-6">
          <p className="text-on-surface-variant text-sm mb-2">{t('dashboard.activeUsers')}</p>
          <p className="text-4xl font-headline-md text-on-surface">1,234</p>
        </div>
        <div className="glass-panel rounded-xl p-6">
          <p className="text-on-surface-variant text-sm mb-2">{t('dashboard.dailyMessages')}</p>
          <p className="text-4xl font-headline-md text-on-surface">5,678</p>
        </div>
        <div className="glass-panel rounded-xl p-6">
          <p className="text-on-surface-variant text-sm mb-2">{t('dashboard.revenue')}</p>
          <p className="text-4xl font-headline-md text-on-surface">$12,345</p>
        </div>
        <div className="glass-panel rounded-xl p-6">
          <p className="text-on-surface-variant text-sm mb-2">Avg Rating</p>
          <p className="text-4xl font-headline-md text-on-surface">4.8★</p>
        </div>
      </div>

      <div className="glass-panel rounded-xl p-6">
        <h2 className="font-headline-md text-on-surface mb-4">{t('dashboard.topPersonas')}</h2>
        {/* Chart placeholder */}
        <div className="h-64 flex items-center justify-center text-on-surface-variant">
          Chart will be rendered here (Phase 2)
        </div>
      </div>
    </div>
  );
}
