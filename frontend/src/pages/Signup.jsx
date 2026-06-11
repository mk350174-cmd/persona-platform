import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function Signup() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { t } = useTranslation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setLoading(true);
    // TODO: Implement signup API call
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-background text-on-surface dark flex items-center justify-center px-4">
      <div className="glass-panel rounded-xl p-8 w-full max-w-md">
        <h1 className="font-headline-md text-headline-md text-on-surface mb-2">
          {t('auth.signup')}
        </h1>
        <p className="text-on-surface-variant text-sm mb-6">
          {t('auth.haveAccount')} <Link to="/login" className="text-primary hover:underline">{t('auth.login')}</Link>
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-error/20 text-error text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-label-caps text-on-surface-variant mb-2">
              {t('auth.email')}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-surface-container border border-border-glass rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary/50 transition-colors"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-label-caps text-on-surface-variant mb-2">
              {t('auth.password')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-surface-container border border-border-glass rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary/50 transition-colors"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-label-caps text-on-surface-variant mb-2">
              Confirm Password
            </label>
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full bg-surface-container border border-border-glass rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary/50 transition-colors"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-lg bg-primary-container text-white font-body-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {loading ? t('common.loading') : t('auth.signup')}
          </button>
        </form>
      </div>
    </div>
  );
}
