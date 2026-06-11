import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useTranslation } from 'react-i18next';

export default function Header() {
  const { user, logout, isAuthenticated } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'tr' : 'en';
    i18n.changeLanguage(newLang);
    localStorage.setItem('language', newLang);
  };

  return (
    <nav className="fixed top-0 w-full z-50 bg-surface-glass backdrop-blur-xl border-b border-border-glass">
      <div className="max-w-container-max mx-auto px-margin-desktop h-16 flex items-center justify-between">
        <Link to="/" className="font-display-lg font-bold text-primary text-[24px]">
          {t('common.appName')}
        </Link>

        <div className="hidden md:flex gap-6 items-center">
          <Link to="/catalog" className="text-on-surface-variant hover:text-on-surface transition-colors">
            {t('nav.catalog')}
          </Link>
          {isAuthenticated && (
            <>
              <Link to="/dashboard" className="text-on-surface-variant hover:text-on-surface transition-colors">
                {t('nav.dashboard')}
              </Link>
              <Link to="/ceid-monitor" className="text-on-surface-variant hover:text-on-surface transition-colors">
                {t('nav.ceidMonitor')}
              </Link>
            </>
          )}
        </div>

        <div className="flex gap-4 items-center">
          <button
            onClick={toggleTheme}
            className="p-2 rounded-full hover:bg-white/5 transition-colors"
            title={isDark ? 'Light mode' : 'Dark mode'}
          >
            <span className="material-symbols-outlined">
              {isDark ? 'light_mode' : 'dark_mode'}
            </span>
          </button>

          <button
            onClick={toggleLanguage}
            className="p-2 rounded-full hover:bg-white/5 transition-colors"
            title="Toggle language"
          >
            <span className="material-symbols-outlined">language</span>
          </button>

          {isAuthenticated ? (
            <>
              <div className="flex items-center gap-2">
                <span className="text-sm text-on-surface-variant">{user?.email}</span>
              </div>
              <button
                onClick={handleLogout}
                className="px-4 py-2 rounded-lg bg-error/20 text-error hover:bg-error/30 transition-colors"
              >
                {t('nav.logout')}
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="text-on-surface-variant hover:text-on-surface transition-colors"
              >
                {t('auth.login')}
              </Link>
              <Link
                to="/signup"
                className="px-4 py-2 rounded-lg bg-primary-container text-white hover:opacity-90 transition-opacity"
              >
                {t('auth.signup')}
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
