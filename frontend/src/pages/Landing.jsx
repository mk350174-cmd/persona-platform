import React from 'react';
import { Link } from 'react-router-dom';
import Header from '../components/Header';

export default function Landing() {
  return (
    <div className="min-h-screen bg-background text-on-surface dark flex flex-col">
      <Header />

      <main className="flex-1 flex flex-col items-center justify-center mt-16">
        {/* Background effects */}
        <div className="fixed inset-0 z-0 pointer-events-none">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-primary-container rounded-full mix-blend-screen filter blur-[120px] opacity-20"></div>
          <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] bg-philosophy-purple rounded-full mix-blend-screen filter blur-[100px] opacity-15"></div>
        </div>

        <div className="relative z-10 text-center px-4 max-w-2xl">
          <h1 className="font-display-lg text-display-lg text-on-surface mb-6 glow-text">
            Meet Your Ideal AI Persona
          </h1>

          <p className="font-body-lg text-body-lg text-on-surface-variant mb-8">
            Explore 495 meticulously crafted AI personas spanning philosophy, science, arts, ethics, and more.
            Compile custom models with advanced neural techniques and integrate them into your applications.
          </p>

          <div className="flex gap-4 justify-center">
            <Link
              to="/catalog"
              className="px-6 py-3 rounded-lg bg-primary-container text-white font-body-lg hover:opacity-90 transition-opacity"
            >
              Explore Catalog
            </Link>
            <Link
              to="/signup"
              className="px-6 py-3 rounded-lg bg-surface-container text-on-surface border border-primary/30 font-body-lg hover:bg-surface-container-high transition-colors"
            >
              Get Started
            </Link>
          </div>

          {/* Feature highlights */}
          <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="glass-panel rounded-xl p-6">
              <div className="text-3xl mb-3">🎭</div>
              <h3 className="font-headline-md text-on-surface mb-2">495 Personas</h3>
              <p className="text-on-surface-variant text-sm">
                Carefully curated characters across multiple domains and eras.
              </p>
            </div>

            <div className="glass-panel rounded-xl p-6">
              <div className="text-3xl mb-3">⚡</div>
              <h3 className="font-headline-md text-on-surface mb-2">Real-time Chat</h3>
              <p className="text-on-surface-variant text-sm">
                Stream conversations with intelligent personas via WebSocket.
              </p>
            </div>

            <div className="glass-panel rounded-xl p-6">
              <div className="text-3xl mb-3">🔧</div>
              <h3 className="font-headline-md text-on-surface mb-2">Compile Models</h3>
              <p className="text-on-surface-variant text-sm">
                Create custom AI models with advanced techniques and fine-tuning.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
