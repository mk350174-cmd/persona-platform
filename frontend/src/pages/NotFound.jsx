import React from 'react';
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-background text-on-surface dark flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="font-display-lg text-display-lg text-on-surface mb-4">404</h1>
        <p className="font-headline-md text-on-surface-variant mb-8">Page not found</p>
        <Link
          to="/"
          className="px-6 py-3 rounded-lg bg-primary-container text-white font-body-lg hover:opacity-90 transition-opacity"
        >
          Back to Home
        </Link>
      </div>
    </div>
  );
}
