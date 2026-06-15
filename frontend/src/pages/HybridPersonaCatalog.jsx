import React, { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import '../styles/HybridPersonaCatalog.css';

/**
 * HybridPersonaCatalog Page
 *
 * Browse and search all 48 hybrid personas.
 * Route: /personas/hybrid
 *
 * Features:
 * - Paginated list (skip/limit)
 * - Full-text search (name/use-case)
 * - Filter by persona type (if applicable)
 * - Sort by combination number
 * - Responsive grid layout
 */

export default function HybridPersonaCatalog() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // State management
  const [personas, setPersonas] = useState([]);
  const [filteredPersonas, setFilteredPersonas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Pagination and filtering
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(12);
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [selectedType, setSelectedType] = useState(searchParams.get('type') || 'all');
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'combination');

  // Load personas from API
  useEffect(() => {
    const loadPersonas = async () => {
      try {
        setLoading(true);
        const response = await fetch('/api/v1/personas/hybrid?limit=100');
        if (!response.ok) {
          throw new Error('Failed to load personas');
        }
        const data = await response.json();
        const personaList = Array.isArray(data) ? data : data.personas || [];
        setPersonas(personaList);
        setError('');
      } catch (err) {
        setError('Failed to load hybrid personas. Please try again later.');
        console.error('Error loading personas:', err);
      } finally {
        setLoading(false);
      }
    };

    loadPersonas();
  }, []);

  // Apply filters and search
  useEffect(() => {
    let filtered = personas;

    // Search filter (name and use case)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (p) =>
          (p.name_en && p.name_en.toLowerCase().includes(query)) ||
          (p.name_tr && p.name_tr.toLowerCase().includes(query)) ||
          (p.use_case_en && p.use_case_en.toLowerCase().includes(query)) ||
          (p.use_case_tr && p.use_case_tr.toLowerCase().includes(query))
      );
    }

    // Type filter
    if (selectedType !== 'all') {
      filtered = filtered.filter((p) => p.type === selectedType);
    }

    // Sorting
    if (sortBy === 'combination') {
      filtered.sort((a, b) => (a.combination_number || 0) - (b.combination_number || 0));
    } else if (sortBy === 'name') {
      filtered.sort((a, b) => (a.name_en || '').localeCompare(b.name_en || ''));
    } else if (sortBy === 'rating') {
      filtered.sort((a, b) => (b.rating || 0) - (a.rating || 0));
    }

    setFilteredPersonas(filtered);
    setCurrentPage(1);

    // Update URL params
    const params = new URLSearchParams();
    if (searchQuery) params.set('search', searchQuery);
    if (selectedType !== 'all') params.set('type', selectedType);
    if (sortBy !== 'combination') params.set('sort', sortBy);
    setSearchParams(params);
  }, [personas, searchQuery, selectedType, sortBy, setSearchParams]);

  // Pagination
  const totalPages = Math.ceil(filteredPersonas.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const displayedPersonas = filteredPersonas.slice(startIndex, endIndex);

  // Get unique types for filter
  const personaTypes = ['all', ...new Set(personas.map((p) => p.type).filter(Boolean))];

  // Handlers
  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
  };

  const handleTypeChange = (e) => {
    setSelectedType(e.target.value);
  };

  const handleSortChange = (e) => {
    setSortBy(e.target.value);
  };

  const handlePersonaClick = (personaId) => {
    navigate(`/personas/hybrid/${personaId}`);
  };

  const goToPage = (page) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // Render
  return (
    <div className="hybrid-catalog-container">
      {/* Header */}
      <div className="catalog-header">
        <h1 className="catalog-title">48 Hybrid Personas</h1>
        <p className="catalog-subtitle">
          Explore our collection of advanced hybrid persona combinations
        </p>
      </div>

      {/* Search and Filters */}
      <div className="catalog-controls">
        {/* Search Bar */}
        <div className="search-bar-wrapper">
          <input
            type="text"
            className="search-bar"
            placeholder="Search by name or use case..."
            value={searchQuery}
            onChange={handleSearchChange}
          />
          <span className="search-icon">🔍</span>
        </div>

        {/* Filter Controls */}
        <div className="filter-controls">
          {/* Type Filter */}
          <div className="filter-group">
            <label htmlFor="type-filter">Type:</label>
            <select
              id="type-filter"
              className="filter-select"
              value={selectedType}
              onChange={handleTypeChange}
            >
              {personaTypes.map((type) => (
                <option key={type} value={type}>
                  {type === 'all' ? 'All Types' : type}
                </option>
              ))}
            </select>
          </div>

          {/* Sort Filter */}
          <div className="filter-group">
            <label htmlFor="sort-filter">Sort by:</label>
            <select
              id="sort-filter"
              className="filter-select"
              value={sortBy}
              onChange={handleSortChange}
            >
              <option value="combination">Combination #</option>
              <option value="name">Name (A-Z)</option>
              <option value="rating">Top Rated</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && <div className="error-banner">{error}</div>}

      {/* Results Info */}
      {!loading && (
        <div className="results-info">
          Showing {displayedPersonas.length > 0 ? startIndex + 1 : 0} -{' '}
          {Math.min(endIndex, filteredPersonas.length)} of {filteredPersonas.length} personas
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading hybrid personas...</p>
        </div>
      )}

      {/* No Results State */}
      {!loading && filteredPersonas.length === 0 && (
        <div className="no-results">
          <p>No personas found matching your criteria.</p>
          <button
            className="reset-button"
            onClick={() => {
              setSearchQuery('');
              setSelectedType('all');
              setSortBy('combination');
            }}
          >
            Reset Filters
          </button>
        </div>
      )}

      {/* Personas Grid */}
      {!loading && displayedPersonas.length > 0 && (
        <div className="personas-grid">
          {displayedPersonas.map((persona) => (
            <div
              key={persona.id}
              className="persona-card"
              onClick={() => handlePersonaClick(persona.id)}
            >
              {/* Card Header */}
              <div className="card-header">
                <div className="combination-badge">
                  #{persona.combination_number || 'N/A'}
                </div>
                {persona.rating && (
                  <div className="rating-badge">
                    ★ {persona.rating.toFixed(1)}
                  </div>
                )}
              </div>

              {/* Card Emoji/Icon */}
              <div className="card-emoji">{persona.emoji || '🎭'}</div>

              {/* Card Content */}
              <div className="card-content">
                <h3 className="card-title">
                  {persona.name_en || 'Hybrid Persona'}
                </h3>
                {persona.name_tr && (
                  <p className="card-subtitle">{persona.name_tr}</p>
                )}

                <p className="card-description">
                  {persona.use_case_en || persona.use_case_tr || 'Advanced hybrid persona'}
                </p>

                {/* Tags */}
                <div className="card-tags">
                  {persona.type && (
                    <span className="tag tag-type">{persona.type}</span>
                  )}
                  {persona.complexity && (
                    <span className="tag tag-complexity">
                      {persona.complexity}
                    </span>
                  )}
                </div>
              </div>

              {/* Card Footer */}
              <div className="card-footer">
                <span className="card-price">
                  ${persona.price_usd || 29.99}
                </span>
                <button className="card-button">
                  View Profile →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && !loading && (
        <div className="pagination">
          <button
            className="pagination-button"
            onClick={() => goToPage(currentPage - 1)}
            disabled={currentPage === 1}
          >
            ← Previous
          </button>

          <div className="pagination-info">
            Page {currentPage} of {totalPages}
          </div>

          <div className="pagination-buttons">
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              let pageNum;
              if (totalPages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage > totalPages - 3) {
                pageNum = totalPages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }
              return (
                <button
                  key={pageNum}
                  className={`pagination-number ${
                    pageNum === currentPage ? 'active' : ''
                  }`}
                  onClick={() => goToPage(pageNum)}
                >
                  {pageNum}
                </button>
              );
            })}
          </div>

          <button
            className="pagination-button"
            onClick={() => goToPage(currentPage + 1)}
            disabled={currentPage === totalPages}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
