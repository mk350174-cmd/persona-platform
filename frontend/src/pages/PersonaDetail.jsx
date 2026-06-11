import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../services/api';
import { useTranslation } from 'react-i18next';
import SampleConversation from '../components/SampleConversation';
import VoicePreview from '../components/VoicePreview';
import ConversationExport from '../components/ConversationExport';
import ShareLink from '../components/ShareLink';
import CEIDRadar from '../components/CEIDRadar';

export default function PersonaDetail() {
  const { id } = useParams();
  const [persona, setPersona] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { t } = useTranslation();

  useEffect(() => {
    const loadPersona = async () => {
      try {
        // For demo, create sample persona from ID
        const samplePersonas = {
          'socrates': {
            id: 'socrates',
            name: 'Socrates',
            emoji: '🏛️',
            domain: 'Philosophy',
            era: 'Ancient Greece',
            description: 'Ancient Greek philosopher known for the Socratic method of inquiry and his pursuit of truth through dialogue.',
          },
          'ada-lovelace': {
            id: 'ada-lovelace',
            name: 'Ada Lovelace',
            emoji: '💻',
            domain: 'Science',
            era: 'Victorian Era',
            description: 'English mathematician and visionary, considered the first computer programmer.',
          },
        };

        const foundPersona = samplePersonas[id] || {
          id: id,
          name: 'Unknown Persona',
          emoji: '🎭',
          domain: 'Philosophy',
          era: 'Modern',
          description: 'A fascinating historical figure with unique perspectives.',
        };

        setPersona(foundPersona);
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

  const sampleConversation = [
    { role: 'user', content: 'What is virtue?' },
    {
      role: 'assistant',
      content: 'Virtue is a state of character that produces right action and genuine flourishing.',
    },
  ];

  return (
    <div className="pt-20 px-margin-desktop max-w-container-max mx-auto pb-20">
      {/* Header Section */}
      <div className="glass-panel rounded-xl p-8 mb-8">
        <div className="flex gap-8">
          <div className="text-8xl">{persona.emoji}</div>
          <div className="flex-1">
            <h1 className="font-display-lg text-display-lg text-on-surface mb-4">{persona.name}</h1>
            <p className="text-on-surface-variant text-body-lg mb-6">{persona.description}</p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
              <div>
                <span className="text-on-surface-variant text-sm">{t('personas.domain')}</span>
                <p className="text-on-surface font-headline-md">{persona.domain}</p>
              </div>
              <div>
                <span className="text-on-surface-variant text-sm">{t('personas.era')}</span>
                <p className="text-on-surface font-headline-md">{persona.era}</p>
              </div>
              <div>
                <span className="text-on-surface-variant text-sm">{t('personas.ceid')}</span>
                <p className="text-on-surface font-headline-md">85%</p>
              </div>
              <div>
                <span className="text-on-surface-variant text-sm">{t('catalog.rating')}</span>
                <p className="text-on-surface font-headline-md">4.9★</p>
              </div>
            </div>

            <button className="px-6 py-3 rounded-lg bg-primary-container text-white font-body-lg hover:opacity-90 transition-opacity flex items-center gap-2">
              <span className="material-symbols-outlined">play_arrow</span>
              {t('personas.chat')}
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* Left Column: Sample Conversation & Voice Preview */}
        <div className="lg:col-span-2 space-y-8">
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface mb-4">
              {t('personas.preview')} - {persona.name}
            </h2>
            <SampleConversation personaId={id} onTryNow={() => {}} />
          </div>

          <VoicePreview personaId={id} personaName={persona.name} />
        </div>

        {/* Right Column: CEID Radar */}
        <div className="lg:col-span-1">
          <h3 className="font-headline-md text-on-surface mb-4">CEID Profile</h3>
          <CEIDRadar
            personaId={id}
            metrics={{
              consciousness: 78,
              ethics: 85,
              intelligence: 88,
              drift: 22,
              coherence: 92,
              authenticity: 80,
            }}
          />
        </div>
      </div>

      {/* Export and Share Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <ConversationExport conversation={sampleConversation} personaName={persona.name} />
        <ShareLink personaId={id} personaName={persona.name} />
      </div>
    </div>
  );
}
