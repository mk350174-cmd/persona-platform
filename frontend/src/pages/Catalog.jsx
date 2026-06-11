import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useTranslation } from 'react-i18next';

export default function Catalog() {
  const [personas, setPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const loadPersonas = async () => {
      try {
        const response = await api.listPersonas();
        setPersonas(response.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadPersonas();
  }, []);

  if (loading) return <div className="flex items-center justify-center min-h-screen">{t('common.loading')}</div>;

  return (
    <div className="pt-20 px-margin-desktop max-w-container-max mx-auto">
      <h1 className="font-headline-md text-headline-md text-on-surface mb-8 mt-8">
        {t('catalog.title')}
      </h1>

      {error && (
        <div className="p-4 rounded-lg bg-error/20 text-error mb-8">
          {error}
        </div>
      )}

      {personas.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-on-surface-variant">{t('catalog.nothingFound')}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
          {personas.map((persona) => (
            <div key={persona.id} className="glass-panel rounded-xl p-6 hover:border-primary/50 transition-colors cursor-pointer">
              <div className="text-4xl mb-3">{persona.emoji || '🎭'}</div>
              <h3 className="font-headline-md text-on-surface mb-2">{persona.name}</h3>
              <p className="text-on-surface-variant text-sm mb-4">{persona.description}</p>
              <div className="flex gap-2">
                <span className="text-xs px-3 py-1 rounded-full bg-surface-container text-on-surface-variant">
                  {persona.domain}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
