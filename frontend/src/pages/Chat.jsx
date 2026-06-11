import React, { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../hooks/useWebSocket';
import MarkdownRenderer from '../components/MarkdownRenderer';

export default function Chat() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [inputText, setInputText] = useState('');
  const [personaName, setPersonaName] = useState('Persona');
  const messagesEndRef = useRef(null);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  const { messages, isConnected, isLoading, error, visualParams, sendMessage } =
    useWebSocket(id, user?.api_key);

  // Load persona info
  useEffect(() => {
    const personas = {
      socrates: { name: 'Socrates', emoji: '🏛️' },
      'ada-lovelace': { name: 'Ada Lovelace', emoji: '💻' },
      aristotle: { name: 'Aristotle', emoji: '🏺' },
    };
    const persona = personas[id] || { name: 'Unknown', emoji: '🎭' };
    setPersonaName(persona.name);
  }, [id]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = (e) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading || !isConnected) return;

    sendMessage(inputText);
    setInputText('');
  };

  return (
    <div className="pt-16 h-screen bg-background text-on-surface dark flex flex-col">
      {/* Header */}
      <div className="bg-surface-glass backdrop-blur-xl border-b border-border-glass px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/home')}
            className="material-symbols-outlined text-on-surface-variant hover:text-on-surface transition-colors"
          >
            arrow_back
          </button>
          <div>
            <h1 className="font-headline-md text-on-surface">Chat with {personaName}</h1>
            <p className={`text-sm ${isConnected ? 'text-literature-green' : 'text-error'}`}>
              {isConnected ? '● Connected' : '● Disconnected'}
            </p>
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto space-y-4 px-6 py-6 max-w-4xl mx-auto w-full">
        {messages.length === 0 && (
          <div className="h-full flex items-center justify-center text-center">
            <div>
              <div className="text-6xl mb-4">{personaName === 'Socrates' ? '🏛️' : '🎭'}</div>
              <h2 className="font-headline-md text-on-surface mb-2">Start a conversation</h2>
              <p className="text-on-surface-variant">Ask {personaName} anything you'd like to discuss</p>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div className="text-2xl shrink-0">
              {msg.role === 'user' ? '👤' : '🎭'}
            </div>
            <div
              className={`rounded-lg px-4 py-3 max-w-xl ${
                msg.role === 'user'
                  ? 'user-bubble'
                  : 'ai-bubble'
              }`}
            >
              <MarkdownRenderer content={msg.content} />

              {msg.audio_b64 && (
                <div className="mt-3 pt-3 border-t border-border-glass">
                  <audio
                    controls
                    className="w-full h-8"
                    src={`data:${msg.mime_type};base64,${msg.audio_b64}`}
                  />
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="text-2xl">🎭</div>
            <div className="ai-bubble rounded-lg px-4 py-3 flex items-center gap-2">
              <span className="streaming-cursor"></span>
              <span className="text-on-surface-variant">Thinking...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-error/20 border border-error rounded-lg px-4 py-3 text-error">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-surface-glass backdrop-blur-xl border-t border-border-glass px-6 py-4 max-w-4xl mx-auto w-full">
        <form onSubmit={handleSendMessage} className="flex gap-3">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type your message..."
            disabled={!isConnected || isLoading}
            className="flex-1 bg-surface-container border border-border-glass rounded-lg px-4 py-3 text-on-surface placeholder-on-surface-variant focus:outline-none focus:border-primary/50 disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            disabled={!isConnected || isLoading || !inputText.trim()}
            className="px-6 py-3 rounded-lg bg-primary-container text-white hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center gap-2"
          >
            <span className="material-symbols-outlined">send</span>
          </button>
        </form>
      </div>
    </div>
  );
}
