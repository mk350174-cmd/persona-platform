import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

export default function ShareLink({ personaId, personaName }) {
  const [shareUrl, setShareUrl] = useState(null);
  const [copied, setCopied] = useState(false);
  const [generating, setGenerating] = useState(false);
  const { t } = useTranslation();

  const generateShareLink = async () => {
    setGenerating(true);
    try {
      // In a real app, would call: POST /api/share with persona_id
      // For now, generate a local URL
      const token = Math.random().toString(36).substring(2, 15);
      const url = `${window.location.origin}/share/${token}`;
      setShareUrl(url);
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const shareOnSocial = (platform) => {
    const text = `Check out ${personaName} on Persona Hub - an AI persona marketplace!`;
    const encodedUrl = encodeURIComponent(shareUrl);
    const encodedText = encodeURIComponent(text);

    const urls = {
      twitter: `https://twitter.com/intent/tweet?text=${encodedText}&url=${encodedUrl}`,
      facebook: `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`,
      linkedin: `https://www.linkedin.com/sharing/share-offsite/?url=${encodedUrl}`,
    };

    if (urls[platform]) {
      window.open(urls[platform], '_blank', 'width=600,height=400');
    }
  };

  return (
    <div className="glass-panel rounded-xl p-6 space-y-4">
      <h3 className="font-headline-md text-on-surface">Share {personaName}</h3>
      <p className="text-on-surface-variant text-sm">
        Create a shareable link to this persona
      </p>

      {!shareUrl ? (
        <button
          onClick={generateShareLink}
          disabled={generating}
          className="w-full py-3 px-4 rounded-lg bg-primary-container text-white hover:opacity-90 disabled:opacity-50 transition-opacity font-semibold flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined">share</span>
          {generating ? 'Generating...' : 'Generate Share Link'}
        </button>
      ) : (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={shareUrl}
              readOnly
              className="flex-1 bg-surface-container border border-border-glass rounded-lg px-4 py-3 text-on-surface text-sm font-mono-data"
            />
            <button
              onClick={copyToClipboard}
              className={`px-4 py-3 rounded-lg transition-colors font-semibold ${
                copied
                  ? 'bg-literature-green/20 text-literature-green'
                  : 'bg-primary-container text-white hover:opacity-90'
              }`}
            >
              <span className="material-symbols-outlined">
                {copied ? 'check' : 'content_copy'}
              </span>
            </button>
          </div>

          <div className="bg-surface-container-high border border-border-glass rounded-lg p-4">
            <p className="text-on-surface-variant text-sm mb-3 font-semibold">Share on Social</p>
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={() => shareOnSocial('twitter')}
                className="px-4 py-2 rounded-lg bg-[#1DA1F2]/20 text-[#1DA1F2] hover:bg-[#1DA1F2]/30 transition-colors text-sm"
              >
                <span className="flex items-center gap-2">
                  𝕏 Twitter
                </span>
              </button>
              <button
                onClick={() => shareOnSocial('facebook')}
                className="px-4 py-2 rounded-lg bg-[#1877F2]/20 text-[#1877F2] hover:bg-[#1877F2]/30 transition-colors text-sm"
              >
                <span className="flex items-center gap-2">
                  f Facebook
                </span>
              </button>
              <button
                onClick={() => shareOnSocial('linkedin')}
                className="px-4 py-2 rounded-lg bg-[#0A66C2]/20 text-[#0A66C2] hover:bg-[#0A66C2]/30 transition-colors text-sm"
              >
                <span className="flex items-center gap-2">
                  in LinkedIn
                </span>
              </button>
            </div>
          </div>

          <button
            onClick={() => setShareUrl(null)}
            className="w-full py-2 px-4 rounded-lg bg-surface-container text-on-surface-variant hover:bg-surface-container-high transition-colors text-sm"
          >
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
