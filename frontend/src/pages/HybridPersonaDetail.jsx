import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import CEIDRadar from '../components/CEIDRadar';
import VoicePreview from '../components/VoicePreview';
import ConversationExport from '../components/ConversationExport';
import ShareLink from '../components/ShareLink';
import '../styles/HybridPersonaDetail.css';

/**
 * HybridPersonaDetail Page
 *
 * Displays detailed profile for a hybrid persona (48 total variants).
 * Route: /personas/hybrid/{id}
 *
 * Features:
 * - Bilingual display (Turkish + English)
 * - K-layer breakdown with descriptions
 * - Active/suppressed layers visualization
 * - CEID scores and characteristics
 * - Example outputs and use cases
 * - Purchase button integration
 */

export default function HybridPersonaDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [persona, setPersona] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('overview'); // overview | klayers | characteristics | pricing

  useEffect(() => {
    const loadPersona = async () => {
      try {
        setLoading(true);
        // Fetch from API: GET /api/v1/personas/hybrid/{id}/profile
        const response = await fetch(`/api/v1/personas/hybrid/${id}/profile`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(response.status === 404 ? 'Persona not found' : 'Failed to load persona');
        }

        const data = await response.json();
        setPersona(data);
        setError('');
      } catch (err) {
        setError(err.message);
        console.error('Failed to load persona:', err);
      } finally {
        setLoading(false);
      }
    };

    loadPersona();
  }, [id]);

  if (loading) {
    return (
      <div className="hybrid-persona-detail loading">
        <div className="loading-spinner">
          <p>Loading persona profile...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="hybrid-persona-detail error">
        <div className="error-container">
          <h2>Error</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/personas/hybrid')}>Back to Catalog</button>
        </div>
      </div>
    );
  }

  if (!persona) {
    return (
      <div className="hybrid-persona-detail not-found">
        <div className="not-found-container">
          <h2>Persona Not Found</h2>
          <p>The hybrid persona you're looking for doesn't exist.</p>
          <button onClick={() => navigate('/personas/hybrid')}>Browse All Personas</button>
        </div>
      </div>
    );
  }

  // Extract active K-layers (values > threshold)
  const kLayers = persona.k_layer || [];
  const activeKLayers = kLayers
    .map((value, index) => ({ index, value }))
    .filter(({ value }) => value > 0.4)
    .sort((a, b) => b.value - a.value);

  const suppressedKLayers = kLayers
    .map((value, index) => ({ index, value }))
    .filter(({ value }) => value <= 0.4)
    .sort((a, b) => a.value - b.value)
    .slice(0, 5);

  // Sample conversation for preview
  const sampleConversation = [
    {
      role: 'user',
      content: persona.characteristics_en || 'What makes you unique?'
    },
    {
      role: 'assistant',
      content: persona.example_output_en || 'This is an example response from this persona.'
    }
  ];

  return (
    <div className="hybrid-persona-detail">
      {/* Header Section */}
      <div className="detail-header">
        <div className="header-content">
          <div className="header-emoji">{persona.emoji || '🎭'}</div>
          <div className="header-info">
            <div className="header-combination">Combination #{persona.combination_number || id}</div>
            <h1 className="header-name">
              {persona.name_en || 'Hybrid Persona'}
              {persona.name_tr && <span className="header-name-tr">{persona.name_tr}</span>}
            </h1>
            <p className="header-description">
              {persona.use_case_en || persona.use_case_tr || 'Advanced hybrid persona blend'}
            </p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="quick-stats">
          <div className="stat-card">
            <span className="stat-label">K-Layers Active</span>
            <span className="stat-value">{activeKLayers.length}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Hybrid Type</span>
            <span className="stat-value">{persona.type || 'Balanced'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Complexity</span>
            <span className="stat-value">{persona.complexity || 'Advanced'}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Price</span>
            <span className="stat-value">${persona.price_usd || 29.99}</span>
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button
          className={`tab-button ${tab === 'overview' ? 'active' : ''}`}
          onClick={() => setTab('overview')}
        >
          Overview
        </button>
        <button
          className={`tab-button ${tab === 'klayers' ? 'active' : ''}`}
          onClick={() => setTab('klayers')}
        >
          K-Layers
        </button>
        <button
          className={`tab-button ${tab === 'characteristics' ? 'active' : ''}`}
          onClick={() => setTab('characteristics')}
        >
          Characteristics
        </button>
        <button
          className={`tab-button ${tab === 'pricing' ? 'active' : ''}`}
          onClick={() => setTab('pricing')}
        >
          Pricing & Purchase
        </button>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {/* Overview Tab */}
        {tab === 'overview' && (
          <div className="tab-panel overview-panel">
            <div className="content-grid">
              {/* Main Content */}
              <div className="main-content">
                {/* Use Case & Description */}
                <div className="content-section">
                  <h2>About This Persona</h2>
                  <div className="bilingual-content">
                    <div className="lang-block">
                      <h3>English</h3>
                      <p>{persona.use_case_en || 'Hybrid persona combining multiple K-layers for complex interactions.'}</p>
                    </div>
                    {persona.use_case_tr && (
                      <div className="lang-block">
                        <h3>Türkçe</h3>
                        <p>{persona.use_case_tr}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Sample Conversation */}
                <div className="content-section">
                  <h2>Sample Output</h2>
                  <div className="sample-output">
                    <p className="sample-text">
                      {persona.example_output_en || persona.example_output_tr || 'Example persona response will appear here.'}
                    </p>
                  </div>
                </div>

                {/* Voice Preview */}
                {persona.voice_id && (
                  <div className="content-section">
                    <h2>Voice Preview</h2>
                    <VoicePreview personaId={id} personaName={persona.name_en} />
                  </div>
                )}
              </div>

              {/* Sidebar: CEID & Quick Info */}
              <div className="sidebar-content">
                <div className="ceid-widget">
                  <h3>CEID Metrics</h3>
                  <CEIDRadar
                    personaId={id}
                    metrics={persona.ceid_scores || {
                      consciousness: 75,
                      ethics: 80,
                      intelligence: 85,
                      drift: 15,
                      coherence: 88,
                      authenticity: 82,
                    }}
                  />
                </div>

                <div className="info-widget">
                  <h3>Quick Info</h3>
                  <div className="info-list">
                    <div className="info-item">
                      <span className="info-label">Type</span>
                      <span className="info-value">{persona.type || 'Hybrid'}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Complexity</span>
                      <span className="info-value">{persona.complexity || 'Advanced'}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Rating</span>
                      <span className="info-value">★★★★★</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* K-Layers Tab */}
        {tab === 'klayers' && (
          <div className="tab-panel klayers-panel">
            <div className="klayers-content">
              {/* Active K-Layers */}
              <div className="klayers-section">
                <h2>Active K-Layers ({activeKLayers.length})</h2>
                <p className="section-description">
                  These K-layers are strongly activated in this persona, defining its core characteristics.
                </p>

                <div className="klayers-grid">
                  {activeKLayers.slice(0, 15).map(({ index, value }) => (
                    <div key={index} className="klayer-detail-card active">
                      <div className="klayer-header">
                        <span className="klayer-number">K{index + 1}</span>
                        <span className="klayer-value">{(value * 100).toFixed(0)}%</span>
                      </div>
                      <div className="klayer-bar">
                        <div
                          className="klayer-fill"
                          style={{ width: `${value * 100}%` }}
                        ></div>
                      </div>
                      <p className="klayer-description">
                        {persona.k_layer_descriptions?.[index] || `K-Layer ${index + 1}`}
                      </p>
                    </div>
                  ))}
                </div>

                {activeKLayers.length > 15 && (
                  <p className="more-layers">
                    +{activeKLayers.length - 15} more active K-layers
                  </p>
                )}
              </div>

              {/* Suppressed K-Layers */}
              {suppressedKLayers.length > 0 && (
                <div className="klayers-section">
                  <h2>Suppressed K-Layers</h2>
                  <p className="section-description">
                    These K-layers are intentionally suppressed or minimized in this persona.
                  </p>

                  <div className="suppressed-grid">
                    {suppressedKLayers.map(({ index, value }) => (
                      <div key={index} className="klayer-detail-card suppressed">
                        <div className="klayer-header">
                          <span className="klayer-number">K{index + 1}</span>
                          <span className="klayer-value">{(value * 100).toFixed(0)}%</span>
                        </div>
                        <div className="klayer-bar">
                          <div
                            className="klayer-fill"
                            style={{ width: `${value * 100}%` }}
                          ></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* K-Layer Distribution Chart */}
              <div className="klayers-section">
                <h2>All K-Layers Distribution</h2>
                <div className="klayer-distribution">
                  {kLayers.map((value, idx) => (
                    <div
                      key={idx}
                      className="distribution-bar"
                      style={{
                        height: `${value * 100}%`,
                        backgroundColor: value > 0.7 ? '#10b981' : value > 0.4 ? '#f59e0b' : '#e5e7eb',
                      }}
                      title={`K${idx + 1}: ${(value * 100).toFixed(0)}%`}
                    ></div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Characteristics Tab */}
        {tab === 'characteristics' && (
          <div className="tab-panel characteristics-panel">
            <div className="characteristics-content">
              <div className="characteristics-section">
                <h2>Personality Characteristics</h2>

                {/* English Characteristics */}
                <div className="characteristics-group">
                  <h3>Primary Traits (English)</h3>
                  <div className="traits-list">
                    {persona.characteristics_en ? (
                      <p>{persona.characteristics_en}</p>
                    ) : (
                      <p>Detailed characteristics will be available upon purchase.</p>
                    )}
                  </div>
                </div>

                {/* Turkish Characteristics */}
                {persona.characteristics_tr && (
                  <div className="characteristics-group">
                    <h3>Birincil Özellikler (Türkçe)</h3>
                    <div className="traits-list">
                      <p>{persona.characteristics_tr}</p>
                    </div>
                  </div>
                )}

                {/* Strengths */}
                <div className="characteristics-group">
                  <h3>Strengths</h3>
                  <div className="traits-grid">
                    {(persona.strengths || [
                      'Complex reasoning',
                      'Multi-perspective thinking',
                      'Adaptive communication',
                      'Innovative problem-solving'
                    ]).map((strength, idx) => (
                      <div key={idx} className="trait-badge">
                        ✓ {strength}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Best Used For */}
                <div className="characteristics-group">
                  <h3>Best Used For</h3>
                  <ul className="use-cases-list">
                    {(persona.use_cases || [
                      'Professional and business communications',
                      'Technical and creative collaboration',
                      'Complex problem solving',
                      'Multi-language interactions'
                    ]).map((useCase, idx) => (
                      <li key={idx}>{useCase}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Pricing & Purchase Tab */}
        {tab === 'pricing' && (
          <div className="tab-panel pricing-panel">
            <div className="pricing-content">
              <div className="pricing-hero">
                <h2>Unlock This Persona</h2>
                <div className="price-display">
                  <span className="price-currency">$</span>
                  <span className="price-amount">{persona.price_usd || 29.99}</span>
                  <span className="price-period">one-time purchase</span>
                </div>
              </div>

              <div className="pricing-features">
                <h3>What You Get</h3>
                <div className="features-list">
                  <div className="feature-item">
                    <span className="feature-icon">✓</span>
                    <span className="feature-text">Full access to this hybrid persona</span>
                  </div>
                  <div className="feature-item">
                    <span className="feature-icon">✓</span>
                    <span className="feature-text">Advanced K-layer customization</span>
                  </div>
                  <div className="feature-item">
                    <span className="feature-icon">✓</span>
                    <span className="feature-text">Voice synthesis and audio preview</span>
                  </div>
                  <div className="feature-item">
                    <span className="feature-icon">✓</span>
                    <span className="feature-text">Detailed CEID score breakdown</span>
                  </div>
                  <div className="feature-item">
                    <span className="feature-icon">✓</span>
                    <span className="feature-text">Lifetime access and future updates</span>
                  </div>
                  <div className="feature-item">
                    <span className="feature-icon">✓</span>
                    <span className="feature-text">Export and integration options</span>
                  </div>
                </div>
              </div>

              <button className="purchase-button" onClick={() => {
                alert('Stripe checkout would be initiated here');
                // TODO: Integrate with Stripe checkout
              }}>
                Purchase Access Now
              </button>

              {/* Share Section */}
              <div className="share-section">
                <h3>Share This Persona</h3>
                <ShareLink personaId={id} personaName={persona.name_en} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Export Section */}
      <div className="detail-footer">
        <div className="export-section">
          <h2>Export & Share</h2>
          <ConversationExport
            conversation={sampleConversation}
            personaName={persona.name_en}
          />
        </div>
      </div>
    </div>
  );
}
