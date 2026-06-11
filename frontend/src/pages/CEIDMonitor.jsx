import React from 'react';
import { useTranslation } from 'react-i18next';

export default function CEIDMonitor() {
  const { t } = useTranslation();

  return (
    <div className="pt-20 px-margin-desktop max-w-container-max mx-auto pb-20">
      <h1 className="font-headline-md text-headline-md text-on-surface mb-8 mt-8">
        {t('nav.ceidMonitor')}
      </h1>

      <div className="glass-panel rounded-xl p-8">
        <h2 className="font-headline-md text-on-surface mb-4">Persona CEID Metrics</h2>
        <p className="text-on-surface-variant mb-8">
          Monitor Consciousness, Ethics, Intelligence, and Drift (CEID) metrics for your personas.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="space-y-4">
            <div>
              <label className="text-on-surface-variant text-sm mb-2 block">Consciousness</label>
              <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                <div className="h-full w-3/4 bg-primary"></div>
              </div>
              <span className="text-sm text-on-surface mt-1">75%</span>
            </div>
            <div>
              <label className="text-on-surface-variant text-sm mb-2 block">Ethics</label>
              <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                <div className="h-full w-4/5 bg-ethics-blue"></div>
              </div>
              <span className="text-sm text-on-surface mt-1">80%</span>
            </div>
            <div>
              <label className="text-on-surface-variant text-sm mb-2 block">Intelligence</label>
              <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                <div className="h-full w-5/6 bg-science-cyan"></div>
              </div>
              <span className="text-sm text-on-surface mt-1">83%</span>
            </div>
            <div>
              <label className="text-on-surface-variant text-sm mb-2 block">Drift</label>
              <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                <div className="h-full w-1/4 bg-literature-green"></div>
              </div>
              <span className="text-sm text-on-surface mt-1">25%</span>
            </div>
          </div>

          <div className="glass-panel rounded-xl p-4 bg-surface-container-high border border-border-glass">
            <h3 className="font-headline-md text-on-surface mb-3">Radar Chart</h3>
            <div className="h-64 flex items-center justify-center text-on-surface-variant">
              Radar visualization will be added in Phase 3
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
