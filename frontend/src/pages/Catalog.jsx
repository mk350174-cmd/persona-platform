import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { useTranslation } from 'react-i18next';
import CatalogFilters from '../components/CatalogFilters';
import PersonaExplorer3D from '../components/PersonaExplorer3D';
import SampleConversation from '../components/SampleConversation';

export default function Catalog() {
  const navigate = useNavigate();
  const [personas, setPersonas] = useState([]);
  const [filteredPersonas, setFilteredPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showExplorer, setShowExplorer] = useState(false);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [filters, setFilters] = useState({
    search: '',
    domains: [],
    eras: [],
    priceRanges: [],
  });
  const { t } = useTranslation();

  useEffect(() => {
    const loadPersonas = async () => {
      try {
        const response = await api.listPersonas();
        setPersonas(response.data);
        setFilteredPersonas(response.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadPersonas();
  }, []);

  // Apply filters
  useEffect(() => {
    let filtered = personas;

    // Search filter
    if (filters.search) {
      filtered = filtered.filter(
        (p) =>
          p.name.toLowerCase().includes(filters.search.toLowerCase()) ||
          p.description.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    // Domain filter
    if (filters.domains.length > 0) {
      filtered = filtered.filter((p) => filters.domains.includes(p.domain));
    }

    // Era filter
    if (filters.eras.length > 0) {
      filtered = filtered.filter((p) => filters.eras.includes(p.era?.toLowerCase()));
    }

    setFilteredPersonas(filtered);
  }, [filters, personas]);

  if (loading) return <div className="flex items-center justify-center min-h-screen">{t('common.loading')}</div>;

  return (
    <div className="pt-20 px-margin-desktop max-w-container-max mx-auto pb-20">
      <div className="mb-8 mt-8">
        <h1 className="font-headline-md text-headline-md text-on-surface mb-2">
          {t('catalog.title')}
        </h1>
        <p className="text-on-surface-variant">Explore {personas.length} AI personas</p>
      </div>

      {/* 3D Explorer Toggle */}
      <button
        onClick={() => setShowExplorer(!showExplorer)}
        className="mb-6 px-4 py-2 rounded-lg bg-primary-container text-white hover:opacity-90 transition-opacity flex items-center gap-2"
      >
        <span className="material-symbols-outlined text-sm">view_in_ar</span>
        {showExplorer ? 'Hide 3D Explorer' : 'Show 3D Explorer'}
      </button>

      {/* 3D Explorer */}
      {showExplorer && (
        <div className="mb-8">
          <PersonaExplorer3D
            personas={filteredPersonas}
            onSelect={(personaId) => {
              const persona = filteredPersonas.find((p) => p.id === personaId);
              setSelectedPersona(persona);
            }}
          />
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg bg-error/20 text-error mb-8">
          {error}
        </div>
      )}

      <div className="flex flex-col md:flex-row gap-gutter">
        {/* Sidebar Filters */}
        <CatalogFilters filters={filters} onFilterChange={setFilters} />

        {/* Main Content */}
        <div className="flex-1 space-y-8">
          {/* Sample Conversation for Selected Persona */}
          {selectedPersona && (
            <div>
              <h2 className="font-headline-md text-on-surface mb-4">
                {selectedPersona.name} - Sample Conversation
              </h2>
              <SampleConversation
                personaId={selectedPersona.id}
                onTryNow={() => {
                  // Navigate to login or chat
                }}
              />
            </div>
          )}

          {/* Personas Grid */}
          {filteredPersonas.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-on-surface-variant">{t('catalog.nothingFound')}</p>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-on-surface-variant text-sm">
                Showing {filteredPersonas.length} of {personas.length} personas
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {filteredPersonas.map((persona) => (
                  <Link
                    key={persona.id}
                    to={`/personas/${persona.id}`}
                    className="glass-panel rounded-xl p-6 hover:border-primary/50 transition-all hover:shadow-lg cursor-pointer group"
                  >
                    <div className="text-5xl mb-3 group-hover:scale-110 transition-transform">
                      {persona.emoji || '🎭'}
                    </div>
                    <h3 className="font-headline-md text-on-surface mb-2 group-hover:text-primary transition-colors">
                      {persona.name}
                    </h3>
                    <p className="text-on-surface-variant text-sm mb-4 line-clamp-2">
                      {persona.description}
                    </p>

                    <div className="flex flex-wrap gap-2 mb-4">
                      <span className="text-xs px-3 py-1 rounded-full bg-surface-container text-on-surface-variant">
                        {persona.domain}
                      </span>
                      {persona.era && (
                        <span className="text-xs px-3 py-1 rounded-full bg-surface-container text-on-surface-variant">
                          {persona.era}
                        </span>
                      )}
                    </div>

                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        setSelectedPersona(persona);
                      }}
                      className="w-full py-2 px-3 rounded-lg bg-primary-container text-white hover:opacity-90 transition-opacity text-sm"
                    >
                      {t('personas.preview')}
                    </button>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Hybrid Personas Section */}
      <div className="mt-20 pt-20 border-t border-on-surface/10">
        <div className="mb-8">
          <h2 className="font-headline-md text-headline-md text-on-surface mb-2">
            Advanced Hybrid Personas
          </h2>
          <p className="text-on-surface-variant mb-6">
            Explore our collection of 48 advanced hybrid persona combinations optimized for specialized use cases
          </p>
          <button
            onClick={() => navigate('/personas/hybrid')}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-primary-container text-white font-semibold hover:opacity-90 transition-opacity"
          >
            <span>Browse All Hybrid Personas</span>
            <span>→</span>
          </button>
        </div>

        {/* Hybrid Personas Preview Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((idx) => (
            <div
              key={idx}
              className="glass-panel rounded-xl p-6 hover:border-primary/50 transition-all hover:shadow-lg cursor-pointer group"
              onClick={() => navigate('/personas/hybrid')}
            >
              <div className="text-5xl mb-3 group-hover:scale-110 transition-transform">
                🎭
              </div>
              <h3 className="font-headline-md text-on-surface mb-2 group-hover:text-primary transition-colors">
                Hybrid Combo #{idx}
              </h3>
              <p className="text-on-surface-variant text-sm mb-4 line-clamp-2">
                Advanced blend optimized for complex interactions and specialized scenarios
              </p>

              <div className="flex flex-wrap gap-2 mb-4">
                <span className="text-xs px-3 py-1 rounded-full bg-surface-container text-on-surface-variant">
                  Hybrid
                </span>
                <span className="text-xs px-3 py-1 rounded-full bg-surface-container text-on-surface-variant">
                  Advanced
                </span>
              </div>

              <button
                onClick={(e) => {
                  e.preventDefault();
                  navigate('/personas/hybrid');
                }}
                className="w-full py-2 px-3 rounded-lg bg-primary-container text-white hover:opacity-90 transition-opacity text-sm"
              >
                Learn More
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
