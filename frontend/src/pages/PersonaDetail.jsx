import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useTranslation } from 'react-i18next';

export default function PersonaDetail() {
  const { id } = useParams();
  const [persona, setPersona] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const loadPersona = async () => {
      try {
        const response = await api.getPersona(id);
        setPersona(response.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadPersona();
  }, [id]);

  if (loading) return <div className="flex items-center justify-center min-h-screen">{t('common.loading')}</div>;
  if (error) return <div className="flex items-center justify-center min-h-screen text-error">{error}</div>;
  if (!persona) return <div className="flex items-center justify-center min-h-screen">{t('errors.notFound')}</div>;

  return (
    <div className="pt-20 px-margin-desktop max-w-container-max mx-auto pb-20">
      <div className="glass-panel rounded-xl p-8">
        <div className="flex gap-8">
          <div className="text-8xl">{persona.emoji || '🎭'}</div>
          <div className="flex-1">
            <h1 className="font-display-lg text-display-lg text-on-surface mb-4">{persona.name}</h1>
            <p className="text-on-surface-variant mb-6">{persona.description}</p>

            <div className="grid grid-cols-2 gap-4 mb-8">
              <div>
                <span className="text-on-surface-variant text-sm">{t('personas.domain')}</span>
                <p className="text-on-surface font-headline-md">{persona.domain}</p>
              </div>
              <div>
                <span className="text-on-surface-variant text-sm">{t('personas.era')}</span>
                <p className="text-on-surface font-headline-md">{persona.era}</p>
              </div>
            </div>

            <button className="px-6 py-3 rounded-lg bg-primary-container text-white font-body-lg hover:opacity-90 transition-opacity">
              {t('personas.chat')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
