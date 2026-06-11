import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import introJs from 'intro.js';
import 'intro.js/introjs.css';

export default function OnboardingTour({ isFirstVisit = true }) {
  const [showTour, setShowTour] = useState(isFirstVisit);
  const location = useLocation();

  useEffect(() => {
    // Only show tour on first visit to home page
    if (!showTour || !isFirstVisit) return;

    // Delay to ensure DOM is ready
    const timer = setTimeout(() => {
      const intro = introJs();

      const steps = [
        {
          element: 'nav',
          intro: 'Welcome to Persona Hub! This is your navigation bar. Browse our catalog, check your dashboard, and manage your account here.',
          position: 'bottom',
        },
        {
          element: '[data-tour="search"]',
          intro: 'Search and filter through 495 unique AI personas. Find exactly what you\'re looking for.',
          position: 'bottom',
        },
        {
          element: '[data-tour="3d-explorer"]',
          intro: 'Try the 3D Explorer to visualize personas in an interactive globe. Click on any sphere to preview.',
          position: 'bottom',
        },
        {
          element: '[data-tour="filters"]',
          intro: 'Filter by domain, era, and price range to narrow down your search.',
          position: 'right',
        },
        {
          element: '[data-tour="conversation"]',
          intro: 'Preview conversations with any persona before purchasing. Get a feel for their personality.',
          position: 'top',
        },
        {
          element: '[data-tour="theme-toggle"]',
          intro: 'Toggle between light and dark modes, or switch languages here.',
          position: 'bottom',
        },
      ];

      intro.setOptions({
        steps: steps.filter((step) => document.querySelector(step.element)),
        showProgress: true,
        exitOnEsc: true,
        exitOnOverlayClick: true,
        disableInteraction: false,
        highlightClass: 'intro-highlight',
        tooltipClass: 'custom-intro-tooltip',
      });

      intro.start();
      intro.onbeforechange(() => {
        // Optional: additional logic when steps change
      });

      intro.onexit(() => {
        setShowTour(false);
        localStorage.setItem('onboarding-completed', 'true');
      });
    }, 500);

    return () => clearTimeout(timer);
  }, [showTour, isFirstVisit]);

  const restartTour = () => {
    setShowTour(true);
  };

  return null; // Tour is managed by intro.js overlay
}
