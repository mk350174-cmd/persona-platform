import React from 'react';
import { useTranslation } from 'react-i18next';

const DOMAINS = [
  { value: 'Philosophy', label: 'Philosophy', icon: '🏛️', color: 'bg-philosophy-purple' },
  { value: 'Science', label: 'Science', icon: '🔬', color: 'bg-science-cyan' },
  { value: 'Ethics', label: 'Ethics', icon: '⚖️', color: 'bg-ethics-blue' },
  { value: 'Leadership', label: 'Leadership', icon: '👑', color: 'bg-leadership-gold' },
  { value: 'Arts', label: 'Arts', icon: '🎨', color: 'bg-arts-orange' },
  { value: 'Literature', label: 'Literature', icon: '📚', color: 'bg-literature-green' },
  { value: 'Fiction', label: 'Fiction', icon: '📖', color: 'bg-fiction-pink' },
  { value: 'Mythology', label: 'Mythology', icon: '⚡', color: 'bg-mythology-lilac' },
];

const ERAS = [
  { value: 'ancient', label: 'Ancient' },
  { value: 'medieval', label: 'Medieval' },
  { value: 'renaissance', label: 'Renaissance' },
  { value: 'modern', label: 'Modern' },
  { value: 'contemporary', label: 'Contemporary' },
];

const PRICE_RANGES = [
  { value: 'free', label: 'Free' },
  { value: '0-9.99', label: '$0 - $9.99' },
  { value: '10-49.99', label: '$10 - $49.99' },
  { value: '50+', label: '$50+' },
];

export default function CatalogFilters({ filters, onFilterChange }) {
  const { t } = useTranslation();

  const handleDomainToggle = (domain) => {
    const current = filters.domains || [];
    const updated = current.includes(domain)
      ? current.filter((d) => d !== domain)
      : [...current, domain];
    onFilterChange({ ...filters, domains: updated });
  };

  const handleEraToggle = (era) => {
    const current = filters.eras || [];
    const updated = current.includes(era)
      ? current.filter((e) => e !== era)
      : [...current, era];
    onFilterChange({ ...filters, eras: updated });
  };

  const handlePriceToggle = (price) => {
    const current = filters.priceRanges || [];
    const updated = current.includes(price)
      ? current.filter((p) => p !== price)
      : [...current, price];
    onFilterChange({ ...filters, priceRanges: updated });
  };

  const handleSearch = (query) => {
    onFilterChange({ ...filters, search: query });
  };

  return (
    <aside className="w-full md:w-80 space-y-6">
      {/* Search */}
      <div className="glass-panel rounded-xl p-6">
        <label className="block text-on-surface-variant text-sm font-label-caps mb-3">
          {t('catalog.search')}
        </label>
        <input
          type="text"
          placeholder="Search personas..."
          value={filters.search || ''}
          onChange={(e) => handleSearch(e.target.value)}
          className="w-full bg-surface-container border border-border-glass rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary/50 transition-colors"
        />
      </div>

      {/* Domains */}
      <div className="glass-panel rounded-xl p-6">
        <h3 className="text-on-surface-variant text-sm font-label-caps mb-4 uppercase">
          {t('catalog.domain')}
        </h3>
        <div className="grid grid-cols-2 gap-2">
          {DOMAINS.map((domain) => (
            <button
              key={domain.value}
              onClick={() => handleDomainToggle(domain.value)}
              className={`flex flex-col items-center gap-2 px-3 py-2 rounded-lg border transition-all ${
                (filters.domains || []).includes(domain.value)
                  ? 'bg-surface-variant border-primary/50 text-on-surface'
                  : 'bg-surface-container border-border-glass text-on-surface-variant hover:border-primary/30'
              }`}
            >
              <span className="text-xl">{domain.icon}</span>
              <span className="text-xs font-mono-data">{domain.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Eras */}
      <div className="glass-panel rounded-xl p-6">
        <h3 className="text-on-surface-variant text-sm font-label-caps mb-4 uppercase">
          Era
        </h3>
        <div className="space-y-2">
          {ERAS.map((era) => (
            <label key={era.value} className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={(filters.eras || []).includes(era.value)}
                onChange={() => handleEraToggle(era.value)}
                className="w-4 h-4 rounded accent-primary"
              />
              <span className="text-on-surface text-sm">{era.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Price Ranges */}
      <div className="glass-panel rounded-xl p-6">
        <h3 className="text-on-surface-variant text-sm font-label-caps mb-4 uppercase">
          {t('catalog.price')}
        </h3>
        <div className="space-y-2">
          {PRICE_RANGES.map((range) => (
            <label key={range.value} className="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={(filters.priceRanges || []).includes(range.value)}
                onChange={() => handlePriceToggle(range.value)}
                className="w-4 h-4 rounded accent-primary"
              />
              <span className="text-on-surface text-sm">{range.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Clear filters */}
      {(filters.domains?.length || filters.eras?.length || filters.priceRanges?.length || filters.search) > 0 && (
        <button
          onClick={() => onFilterChange({ search: '', domains: [], eras: [], priceRanges: [] })}
          className="w-full py-2 px-4 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant transition-colors text-sm"
        >
          Clear all filters
        </button>
      )}
    </aside>
  );
}
