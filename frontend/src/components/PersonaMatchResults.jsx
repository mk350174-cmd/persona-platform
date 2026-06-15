import React from 'react';
import '../styles/PersonaMatchResults.css';

/**
 * PersonaMatchResults Component
 *
 * Displays quiz results and persona matching recommendations.
 * Props:
 *   - personaMatch: {top_match, top_5_matches}
 *   - kLayer: Array of K-layer values (100 dimensions)
 *   - onExplore: Callback to navigate to persona details
 */

const PersonaMatchResults = ({ personaMatch, kLayer, onExplore }) => {
  if (!personaMatch || !kLayer) {
    return <div className="match-results-container"><p>Loading results...</p></div>;
  }

  const topMatch = personaMatch.top_match || {};
  const top5 = personaMatch.top_5_matches || [];

  // Extract active K-layers (values > 0.5)
  const activeKLayers = kLayer
    .map((value, index) => ({ index, value }))
    .filter(({ value }) => value > 0.5)
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  // K-layer categories for context
  const kLayerCategories = {
    'Analytical': [0, 1, 2, 3, 4],
    'Creative': [5, 6, 7, 8, 9],
    'Emotional': [10, 11, 12, 13, 14],
    'Social': [15, 16, 17, 18, 19],
    'Strategic': [20, 21, 22, 23, 24],
    'Adaptive': [25, 26, 27, 28, 29],
  };

  const getCategoryForKLayer = (index) => {
    for (const [category, indices] of Object.entries(kLayerCategories)) {
      if (indices.includes(index)) return category;
    }
    return 'Other';
  };

  return (
    <div className="match-results-container">
      {/* Top Match Card */}
      <div className="top-match-card">
        <div className="match-emoji">{topMatch.emoji || '🎭'}</div>
        <div className="match-info">
          <h2 className="match-name">{topMatch.name_en || topMatch.name_tr || 'Unknown'}</h2>
          <p className="match-score-label">Match Score</p>
          <div className="score-badge">{(topMatch.match_score * 100).toFixed(1)}%</div>
          <p className="match-description">
            {topMatch.use_case_en || topMatch.use_case_tr || 'Hybrid persona blend'}
          </p>
          <button
            className="explore-button"
            onClick={() => onExplore(topMatch.id)}
          >
            Explore Full Profile →
          </button>
        </div>
      </div>

      {/* Top 5 Rankings */}
      <div className="top-5-section">
        <h3 className="section-title">Top 5 Matches</h3>
        <div className="rankings-list">
          {top5.map((match, index) => (
            <div key={match.id} className="ranking-item">
              <div className="rank-number">#{index + 1}</div>
              <div className="rank-emoji">{match.emoji || '🎭'}</div>
              <div className="rank-content">
                <h4 className="rank-name">{match.name_en || match.name_tr}</h4>
                <p className="rank-type">Type: {match.type || 'Hybrid'}</p>
              </div>
              <div className="rank-score">
                <div className="score-percentage">{(match.match_score * 100).toFixed(0)}%</div>
                <div className="score-bar">
                  <div
                    className="score-fill"
                    style={{ width: `${match.match_score * 100}%` }}
                  ></div>
                </div>
              </div>
              <button
                className="rank-button"
                onClick={() => onExplore(match.id)}
              >
                View
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* K-Layer Breakdown */}
      <div className="klayer-breakdown-section">
        <h3 className="section-title">Your K-Layer Profile</h3>
        <div className="klayer-legend">
          <p className="klayer-subtitle">Top 10 Active Layers</p>
        </div>

        <div className="active-layers-grid">
          {activeKLayers.map(({ index, value }) => (
            <div key={index} className="layer-card">
              <div className="layer-header">
                <span className="layer-label">K{index + 1}</span>
                <span className="layer-category-badge">
                  {getCategoryForKLayer(index)}
                </span>
              </div>
              <div className="layer-visualization">
                <div className="layer-bar-container">
                  <div
                    className="layer-bar-fill"
                    style={{ height: `${value * 100}%` }}
                  ></div>
                </div>
              </div>
              <div className="layer-value">{(value * 100).toFixed(0)}%</div>
            </div>
          ))}
        </div>

        {/* All K-Layers Mini View */}
        <div className="all-klayers-mini">
          <p className="mini-title">All 100 K-Layers</p>
          <div className="klayer-mini-grid">
            {kLayer.map((value, idx) => (
              <div
                key={idx}
                className="klayer-mini-bar"
                style={{
                  backgroundColor: value > 0.7 ? '#10b981' : value > 0.4 ? '#f59e0b' : '#e5e7eb',
                  opacity: Math.max(0.3, value)
                }}
                title={`K${idx + 1}: ${(value * 100).toFixed(0)}%`}
              ></div>
            ))}
          </div>
        </div>
      </div>

      {/* Recommendations Section */}
      <div className="recommendations-section">
        <h3 className="section-title">Personalized Recommendations</h3>
        <div className="recommendations-grid">
          <div className="recommendation-card">
            <div className="rec-icon">💡</div>
            <h4>Best For</h4>
            <p>{topMatch.use_case_en || 'Professional communication and engagement'}</p>
          </div>
          <div className="recommendation-card">
            <div className="rec-icon">🎯</div>
            <h4>Primary Strength</h4>
            <p>
              {activeKLayers[0]
                ? `${getCategoryForKLayer(activeKLayers[0].index)} Domain Excellence`
                : 'Balanced Multi-dimensional Ability'
              }
            </p>
          </div>
          <div className="recommendation-card">
            <div className="rec-icon">🚀</div>
            <h4>Next Steps</h4>
            <p>Explore hybrid combinations and unlock exclusive personas</p>
          </div>
        </div>
      </div>

      {/* Call to Action */}
      <div className="cta-section">
        <h3>Ready to Experience Your Persona?</h3>
        <p>Purchase access to unlock detailed persona recommendations tailored to your profile</p>
        <button
          className="cta-button"
          onClick={() => onExplore(topMatch.id)}
        >
          View Top Match & Unlock Personas
        </button>
      </div>
    </div>
  );
};

export default PersonaMatchResults;
