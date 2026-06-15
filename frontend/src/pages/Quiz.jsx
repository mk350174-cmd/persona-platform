import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Quiz.css';

/**
 * HPEP-100 Quiz Page — 50-question persona extraction protocol
 *
 * Features:
 * - Multi-language support (TR, EN, DE, FR, JA, AR)
 * - Progressive form with per-question scoring (0-3 scale)
 * - Real-time K-layer & CEID persona visualization
 * - Stripe checkout integration for $5 purchase
 * - Results display with detailed score breakdown
 */

const Quiz = () => {
  const navigate = useNavigate();
  const apiKey = localStorage.getItem('api_key');

  // State management
  const [stage, setStage] = useState('lang-select'); // lang-select | quiz | results | checkout
  const [language, setLanguage] = useState('en');
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [persona, setPersona] = useState(null);
  const [checkoutUrl, setCheckoutUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const LANGUAGES = [
    { code: 'tr', name: 'Türkçe', flag: '🇹🇷' },
    { code: 'en', name: 'English', flag: '🇬🇧' },
    { code: 'de', name: 'Deutsch', flag: '🇩🇪' },
    { code: 'fr', name: 'Français', flag: '🇫🇷' },
    { code: 'ja', name: '日本語', flag: '🇯🇵' },
    { code: 'ar', name: 'العربية', flag: '🇸🇦' },
  ];

  // Fetch questions when language is selected
  useEffect(() => {
    if (stage === 'quiz' && questions.length === 0) {
      fetchQuestions();
    }
  }, [stage]);

  const fetchQuestions = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/quiz/questions?lang=${language}`);
      if (!response.ok) throw new Error('Failed to load questions');
      const data = await response.json();
      setQuestions(data);
      setCurrentQuestionIndex(0);
      setError(null);
    } catch (err) {
      setError('Failed to load quiz questions. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleLanguageSelect = (lang) => {
    setLanguage(lang);
    setQuestions([]);
    setAnswers({});
    setStage('quiz');
  };

  const handleAnswerChange = (qid, score) => {
    setAnswers(prev => ({
      ...prev,
      [qid]: parseFloat(score)
    }));
  };

  const handleNextQuestion = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    }
  };

  const handlePreviousQuestion = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!apiKey) {
      setError('You must be logged in to submit the quiz.');
      navigate('/login');
      return;
    }

    try {
      setLoading(true);
      const response = await fetch('/api/v1/quiz/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({ answers }),
      });

      if (!response.ok) throw new Error('Failed to submit quiz');

      const result = await response.json();
      setPersona(result.persona);
      setCheckoutUrl(result.checkout_url);
      setStage('results');
      setError(null);
    } catch (err) {
      setError('Failed to submit quiz. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStartCheckout = () => {
    if (checkoutUrl) {
      window.location.href = checkoutUrl;
    }
  };

  // ─── Language Selection Stage ───────────────────────────────────────────

  if (stage === 'lang-select') {
    return (
      <div className="quiz-container lang-select-stage">
        <div className="quiz-header">
          <h1>HPEP-100 Persona Quiz</h1>
          <p className="subtitle">
            50-question Human Persona Extraction Protocol
          </p>
        </div>

        <div className="language-selector">
          <h2>Select Your Language</h2>
          <div className="language-grid">
            {LANGUAGES.map(lang => (
              <button
                key={lang.code}
                className="language-button"
                onClick={() => handleLanguageSelect(lang.code)}
              >
                <span className="flag">{lang.flag}</span>
                <span className="name">{lang.name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="quiz-info">
          <h3>About This Quiz</h3>
          <ul>
            <li>✓ 50 carefully designed questions</li>
            <li>✓ Measures personality across 100 K-layer dimensions</li>
            <li>✓ Generates personalized CEID scores (Clarity, Engagement, Integration, Development)</li>
            <li>✓ Takes approximately 15-20 minutes</li>
            <li>✓ Results unlock exclusive personas</li>
          </ul>
        </div>
      </div>
    );
  }

  // ─── Quiz Stage ────────────────────────────────────────────────────────

  if (stage === 'quiz') {
    if (loading) {
      return <div className="quiz-container"><div className="loading">Loading questions...</div></div>;
    }

    if (error) {
      return (
        <div className="quiz-container error-stage">
          <div className="error-message">{error}</div>
          <button onClick={() => setStage('lang-select')}>Back to Language Selection</button>
        </div>
      );
    }

    if (questions.length === 0) {
      return <div className="quiz-container"><div className="loading">Initializing quiz...</div></div>;
    }

    const currentQuestion = questions[currentQuestionIndex];
    const currentScore = answers[currentQuestion.id] ?? null;
    const answeredCount = Object.keys(answers).length;
    const progressPercent = Math.round((currentQuestionIndex + 1) / questions.length * 100);

    return (
      <div className="quiz-container quiz-stage">
        {/* Header */}
        <div className="quiz-header-compact">
          <div className="progress-info">
            <span className="question-counter">
              Question {currentQuestionIndex + 1} of {questions.length}
            </span>
            <span className="answered-count">({answeredCount} answered)</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progressPercent}%` }}></div>
          </div>
        </div>

        {/* Question Display */}
        <div className="question-container">
          <div className="question-number">S{currentQuestion.id.substring(1)}</div>
          <h2 className="question-text">{currentQuestion.text}</h2>
          <p className="question-type">Phase {currentQuestion.phase} • Type: {currentQuestion.type}</p>
        </div>

        {/* Answer Options */}
        <div className="answer-options">
          <label className="answer-option">
            <input
              type="radio"
              name={`question-${currentQuestion.id}`}
              value="0"
              checked={currentScore === 0}
              onChange={(e) => handleAnswerChange(currentQuestion.id, e.target.value)}
            />
            <span className="option-label">Strongly Disagree (0)</span>
          </label>
          <label className="answer-option">
            <input
              type="radio"
              name={`question-${currentQuestion.id}`}
              value="1"
              checked={currentScore === 1}
              onChange={(e) => handleAnswerChange(currentQuestion.id, e.target.value)}
            />
            <span className="option-label">Disagree (1)</span>
          </label>
          <label className="answer-option">
            <input
              type="radio"
              name={`question-${currentQuestion.id}`}
              value="2"
              checked={currentScore === 2}
              onChange={(e) => handleAnswerChange(currentQuestion.id, e.target.value)}
            />
            <span className="option-label">Agree (2)</span>
          </label>
          <label className="answer-option">
            <input
              type="radio"
              name={`question-${currentQuestion.id}`}
              value="3"
              checked={currentScore === 3}
              onChange={(e) => handleAnswerChange(currentQuestion.id, e.target.value)}
            />
            <span className="option-label">Strongly Agree (3)</span>
          </label>
        </div>

        {/* Navigation */}
        <div className="navigation-controls">
          <button
            className="nav-button"
            onClick={handlePreviousQuestion}
            disabled={currentQuestionIndex === 0}
          >
            ← Previous
          </button>

          <button
            className="nav-button primary"
            onClick={handleNextQuestion}
            disabled={currentQuestionIndex === questions.length - 1}
          >
            Next →
          </button>
        </div>

        {/* Submit Button */}
        {currentQuestionIndex === questions.length - 1 && (
          <div className="submit-section">
            <button
              className="submit-button"
              onClick={handleSubmitQuiz}
              disabled={answeredCount === 0 || loading}
            >
              {loading ? 'Submitting...' : 'Submit Quiz & See Results'}
            </button>
            <p className="submit-note">
              {answeredCount > 0
                ? `You've answered ${answeredCount} of ${questions.length} questions.`
                : 'Please answer at least one question to submit.'}
            </p>
          </div>
        )}

        {error && <div className="error-message">{error}</div>}
      </div>
    );
  }

  // ─── Results Stage ─────────────────────────────────────────────────────

  if (stage === 'results' && persona) {
    return (
      <div className="quiz-container results-stage">
        <div className="results-header">
          <h1>Your Persona Results</h1>
          <p className="subtitle">Based on your HPEP-100 responses</p>
        </div>

        {/* K-Layer Visualization */}
        <div className="results-section">
          <h2>K-Layer Profile</h2>
          <div className="klayer-grid">
            {persona.k_layer.slice(0, 20).map((value, idx) => (
              <div key={idx} className="klayer-bar">
                <div className="bar-value" style={{ height: `${value * 100}%` }}></div>
                <span className="bar-label">K{idx + 1}</span>
              </div>
            ))}
            <div className="klayer-more">
              +{persona.k_layer.length - 20} more K-layers
            </div>
          </div>
        </div>

        {/* CEID Scores */}
        <div className="results-section">
          <h2>CEID Scores</h2>
          <div className="ceid-scores">
            {Object.entries(persona.ceid_scores || {}).map(([key, value]) => {
              if (typeof value !== 'number') return null;
              return (
                <div key={key} className="ceid-score">
                  <label>{key}</label>
                  <div className="score-bar">
                    <div
                      className="score-fill"
                      style={{ width: `${value * 100}%` }}
                    ></div>
                  </div>
                  <span className="score-value">{(value * 100).toFixed(1)}%</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Checkout CTA */}
        <div className="results-section checkout-section">
          <h3>Unlock Exclusive Personas</h3>
          <p>Get access to detailed persona recommendations tailored to your profile.</p>
          <button
            className="checkout-button"
            onClick={handleStartCheckout}
          >
            Complete Purchase ($5) → View Results
          </button>
          <p className="purchase-note">
            Secure payment powered by Stripe. Instant access upon completion.
          </p>
        </div>

        {/* Share Results */}
        <div className="results-footer">
          <button
            className="secondary-button"
            onClick={() => {
              setStage('lang-select');
              setQuestions([]);
              setAnswers({});
              setPersona(null);
            }}
          >
            Take Quiz Again
          </button>
        </div>
      </div>
    );
  }

  // Fallback
  return <div className="quiz-container"><div className="loading">Loading...</div></div>;
};

export default Quiz;
