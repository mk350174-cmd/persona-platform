import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import CEIDRadar from '../components/CEIDRadar';

export default function CEIDMonitor() {
  const { t } = useTranslation();
  const [selectedPersona] = useState('socrates');

  const metrics = {
    consciousness: 75,
    ethics: 85,
    intelligence: 88,
    drift: 25,
    coherence: 92,
    authenticity: 78,
  };

  return (
    <div className="pt-20 px-margin-desktop max-w-container-max mx-auto pb-20">
      <h1 className="font-headline-md text-headline-md text-on-surface mb-2 mt-8">
        {t('nav.ceidMonitor')}
      </h1>
      <p className="text-on-surface-variant mb-8">
        Monitor Consciousness, Ethics, Intelligence, and Drift (CEID) metrics for your personas.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Metrics Grid */}
        <div className="lg:col-span-1 space-y-4">
          <div className="glass-panel rounded-xl p-6">
            <h3 className="font-headline-md text-on-surface mb-6">Metric Overview</h3>

            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-on-surface-variant text-sm">Consciousness</label>
                  <span className="text-on-surface font-semibold text-sm">{metrics.consciousness}%</span>
                </div>
                <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${metrics.consciousness}%` }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-on-surface-variant text-sm">Ethics</label>
                  <span className="text-on-surface font-semibold text-sm">{metrics.ethics}%</span>
                </div>
                <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                  <div
                    className="h-full bg-ethics-blue transition-all"
                    style={{ width: `${metrics.ethics}%` }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-on-surface-variant text-sm">Intelligence</label>
                  <span className="text-on-surface font-semibold text-sm">{metrics.intelligence}%</span>
                </div>
                <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                  <div
                    className="h-full bg-science-cyan transition-all"
                    style={{ width: `${metrics.intelligence}%` }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-on-surface-variant text-sm">Drift</label>
                  <span className="text-on-surface font-semibold text-sm">{metrics.drift}%</span>
                </div>
                <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                  <div
                    className="h-full bg-literature-green transition-all"
                    style={{ width: `${metrics.drift}%` }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-on-surface-variant text-sm">Coherence</label>
                  <span className="text-on-surface font-semibold text-sm">{metrics.coherence}%</span>
                </div>
                <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                  <div
                    className="h-full bg-mythology-lilac transition-all"
                    style={{ width: `${metrics.coherence}%` }}
                  ></div>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-on-surface-variant text-sm">Authenticity</label>
                  <span className="text-on-surface font-semibold text-sm">{metrics.authenticity}%</span>
                </div>
                <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                  <div
                    className="h-full bg-fiction-pink transition-all"
                    style={{ width: `${metrics.authenticity}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>

          {/* Alert Status */}
          <div className="glass-panel rounded-xl p-6 bg-surface-container-high border border-literature-green/30">
            <h4 className="font-headline-md text-literature-green mb-2">Status: Healthy</h4>
            <p className="text-on-surface-variant text-sm">
              All CEID metrics are within normal ranges. Persona is performing optimally.
            </p>
          </div>
        </div>

        {/* Radar Chart */}
        <div className="lg:col-span-2">
          <div className="glass-panel rounded-xl p-6">
            <h3 className="font-headline-md text-on-surface mb-4">CEID Profile - Radar View</h3>
            <CEIDRadar personaId={selectedPersona} metrics={metrics} />
            <p className="text-on-surface-variant text-sm mt-4">
              The radar chart displays all six CEID dimensions. Larger shapes indicate stronger
              performance in that dimension. Ideal personas maintain high scores across all areas
              while keeping drift low.
            </p>
          </div>
        </div>
      </div>

      {/* Historical Trends */}
      <div className="mt-8 glass-panel rounded-xl p-6">
        <h3 className="font-headline-md text-on-surface mb-4">Historical Trends</h3>
        <p className="text-on-surface-variant text-sm mb-6">
          Track how CEID metrics evolve over time as the persona learns and adapts.
        </p>

        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          {[
            { label: 'Week 1', consciousness: 70, ethics: 80, intelligence: 85 },
            { label: 'Week 2', consciousness: 72, ethics: 82, intelligence: 86 },
            { label: 'Week 3', consciousness: 74, ethics: 84, intelligence: 87 },
            { label: 'Week 4', consciousness: 75, ethics: 85, intelligence: 88 },
          ].map((week, idx) => (
            <div key={idx} className="bg-surface-container rounded-lg p-4 text-center">
              <p className="font-semibold text-on-surface text-sm mb-2">{week.label}</p>
              <div className="space-y-1 text-xs text-on-surface-variant">
                <p>C: {week.consciousness}%</p>
                <p>E: {week.ethics}%</p>
                <p>I: {week.intelligence}%</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
