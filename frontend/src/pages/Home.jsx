import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';

export default function Home() {
  const { user } = useAuth();
  const { t } = useTranslation();

  return (
    <div className="pt-20 px-margin-desktop max-w-container-max mx-auto">
      <h1 className="font-display-lg text-display-lg text-on-surface mb-4 mt-8">
        Welcome back, {user?.email}!
      </h1>
      <p className="text-on-surface-variant text-body-lg mb-12">
        Ready to chat with your favorite personas?
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-20">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="glass-panel rounded-xl p-6 hover:border-primary/50 transition-colors cursor-pointer">
            <div className="text-5xl mb-3">🎭</div>
            <h3 className="font-headline-md text-on-surface mb-2">Recent Persona {i + 1}</h3>
            <p className="text-on-surface-variant text-sm mb-4">Last chatted 2 hours ago</p>
            <button className="text-sm text-primary hover:text-primary/80">Continue chat →</button>
          </div>
        ))}
      </div>
    </div>
  );
}
