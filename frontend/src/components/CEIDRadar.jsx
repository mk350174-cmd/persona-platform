import React from 'react';
import { ResponsiveRadar } from '@nivo/radar';

export default function CEIDRadar({ personaId = 'socrates', metrics = null }) {
  const defaultMetrics = {
    Consciousness: 75,
    Ethics: 85,
    Intelligence: 88,
    Drift: 25,
    Coherence: 92,
    Authenticity: 78,
  };

  const data = [
    {
      metric: 'Consciousness',
      value: metrics?.consciousness || defaultMetrics.Consciousness,
      fullMark: 100,
    },
    {
      metric: 'Ethics',
      value: metrics?.ethics || defaultMetrics.Ethics,
      fullMark: 100,
    },
    {
      metric: 'Intelligence',
      value: metrics?.intelligence || defaultMetrics.Intelligence,
      fullMark: 100,
    },
    {
      metric: 'Drift',
      value: metrics?.drift || defaultMetrics.Drift,
      fullMark: 100,
    },
    {
      metric: 'Coherence',
      value: metrics?.coherence || defaultMetrics.Coherence,
      fullMark: 100,
    },
    {
      metric: 'Authenticity',
      value: metrics?.authenticity || defaultMetrics.Authenticity,
      fullMark: 100,
    },
  ];

  return (
    <div className="w-full h-96 rounded-xl overflow-hidden border border-border-glass">
      <ResponsiveRadar
        data={data}
        keys={['value']}
        indexBy="metric"
        margin={{ top: 50, right: 80, bottom: 50, left: 80 }}
        curve="monotoneX"
        borderWidth={2}
        borderColor="#8b5cf6"
        gridLevels={5}
        gridShape="circular"
        gridStrokeWidth={1}
        gridStroke="rgba(255, 255, 255, 0.1)"
        colors={['#8b5cf6']}
        fillOpacity={0.25}
        blendMode="multiply"
        animate={true}
        motionProps={{
          duration: 300,
        }}
        isInteractive={true}
        tooltip={({ index, value }) => (
          <div className="glass-panel rounded-lg px-3 py-2 text-sm">
            <p className="text-on-surface font-semibold">{data[index].metric}</p>
            <p className="text-primary">{value}%</p>
          </div>
        )}
        theme={{
          background: 'transparent',
          textColor: '#e3e0f1',
          fontSize: 12,
          axis: {
            domain: {
              line: {
                strokeWidth: 1,
                stroke: 'rgba(255, 255, 255, 0.1)',
              },
            },
            legend: {
              text: {
                fontSize: 12,
                fill: '#c7c4d8',
              },
            },
            ticks: {
              line: {
                stroke: 'rgba(255, 255, 255, 0.05)',
                strokeWidth: 1,
              },
              text: {
                fontSize: 10,
                fill: '#918fa1',
              },
            },
          },
          grid: {
            line: {
              stroke: 'rgba(255, 255, 255, 0.1)',
              strokeWidth: 1,
            },
          },
          legends: {
            text: {
              fontSize: 12,
              fill: '#c7c4d8',
            },
          },
          dots: {
            text: {
              fontSize: 12,
              fill: '#c7c4d8',
            },
          },
        }}
      />
    </div>
  );
}
