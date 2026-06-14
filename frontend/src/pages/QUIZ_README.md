# HPEP-100 Quiz Component

Multi-language, interactive 50-question persona extraction quiz with real-time visualization.

## Features

- **Multi-Language Support:** Turkish, English, German, French, Japanese, Arabic
- **Progressive Form:** One question at a time with navigation
- **Score Tracking:** Real-time answer storage (0-3 scale per question)
- **Persona Visualization:** K-layer profile and CEID scores display
- **Stripe Integration:** $5 checkout flow for result access
- **Responsive Design:** Mobile-friendly interface
- **Accessibility:** Proper semantic HTML and ARIA labels

## File Structure

```
frontend/src/
├── pages/
│   └── Quiz.jsx                 # Main quiz component
├── styles/
│   └── Quiz.css                 # Quiz styling
└── QUIZ_README.md               # This file
```

## Integration

### 1. Add Route to Router

In `frontend/src/App.jsx` or routing configuration:

```jsx
import Quiz from './pages/Quiz';

// In your Routes component:
<Route path="/quiz" element={<Quiz />} />
```

### 2. Add Navigation Link

In header/navigation component:

```jsx
<Link to="/quiz" className="nav-link">
  Take the Quiz
</Link>
```

### 3. Environment Setup

Ensure API endpoint is configured:
```javascript
// Quiz.jsx uses relative paths, so ensure CORS is configured
// in api/main.py or your FastAPI CORS settings
```

## Component States

### 1. Language Selection (`lang-select`)
- User selects language (6 options)
- Displays quiz information
- Transitions to quiz stage

### 2. Quiz Taking (`quiz`)
- Displays current question with 4-point scale
- Progress bar shows completion
- Previous/Next buttons for navigation
- Submit button on final question

### 3. Results Display (`results`)
- K-layer visualization (100 dimensions)
- CEID scores with progress bars
- Checkout CTA for $5 purchase
- Option to retake quiz

## API Integration

### Endpoints Used

#### GET /api/v1/quiz/questions
Fetch questions for a specific language

```bash
curl "http://localhost:8000/api/v1/quiz/questions?lang=tr" \
  -H "Accept: application/json"
```

Response:
```json
[
  {
    "id": "S1",
    "phase": 1,
    "type": "open",
    "text": "Evrene, insan ilişkilerine... [Turkish text]"
  },
  ...
]
```

#### POST /api/v1/quiz/submit
Submit answers and extract persona

```bash
curl -X POST "http://localhost:8000/api/v1/quiz/submit" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <your_api_key>" \
  -d '{
    "answers": {
      "S1": 0.5,
      "S2": 0.7,
      ...
    }
  }'
```

Response:
```json
{
  "persona": {
    "k_layer": [0.45, 0.52, ...],
    "ceid_scores": {
      "C": 0.6,
      "E": 0.5,
      "I": 0.7,
      "D": 0.55
    },
    "tier": null,
    "created_at": "2026-06-14T23:30:00Z"
  },
  "checkout_url": "/checkout/hpep100?session_id=test"
}
```

## State Management

The component uses React hooks for state:

```javascript
const [stage, setStage] = useState('lang-select');      // UI stage
const [language, setLanguage] = useState('en');         // Selected language
const [questions, setQuestions] = useState([]);         // Fetched questions
const [answers, setAnswers] = useState({});             // User answers
const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
const [persona, setPersona] = useState(null);           // Extracted persona
const [checkoutUrl, setCheckoutUrl] = useState(null);   // Stripe URL
const [loading, setLoading] = useState(false);          // Loading state
const [error, setError] = useState(null);               // Error messages
```

## Styling

### CSS Classes
- `.quiz-container` — Main container
- `.lang-select-stage` — Language selection stage
- `.quiz-stage` — Quiz taking stage
- `.results-stage` — Results display stage
- `.question-container` — Individual question display
- `.answer-options` — Answer radio buttons
- `.klayer-grid` — K-layer visualization
- `.ceid-scores` — CEID score bars
- `.checkout-section` — Payment section

### Responsive Breakpoints
- Desktop: Full width with grid layouts
- Tablet (≤1024px): Adjusted spacing
- Mobile (≤768px): Single column, touch-friendly buttons

## Customization

### Change Quiz Colors
Edit CSS variables or theme colors in `Quiz.css`:
```css
/* Primary color (indigo) */
background: #4f46e5;

/* Gradient */
background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
```

### Modify Quiz Title
```jsx
<h1>Custom Title Here</h1>
```

### Add Custom Language
1. Update LANGUAGES array in Quiz.jsx
2. Ensure backend supports the language code
3. Add flag emoji

## Authentication

The component expects authentication token in localStorage:

```javascript
const apiKey = localStorage.getItem('api_key');
```

If not present, user is redirected to login on quiz submission.

## Error Handling

The component handles several error scenarios:

1. **Missing API Key** → Redirect to login
2. **Failed to load questions** → Display error message
3. **Failed to submit quiz** → Retry option
4. **Checkout failure** → Return to results

All errors are displayed in red boxes with recovery options.

## Performance Considerations

- Questions are fetched once per language selection
- Answers are stored locally in component state
- No intermediate auto-save (form data lost on page refresh)
- Checkout redirect is external (Stripe hosted)

## Testing

### Manual Testing Checklist

- [ ] Language selection works for all 6 languages
- [ ] Questions load correctly for each language
- [ ] Previous/Next navigation works
- [ ] Answers are saved and retrieved correctly
- [ ] Final question shows submit button
- [ ] Submit calculation is correct
- [ ] Results visualization displays K-layer and CEID
- [ ] Checkout button redirects to payment
- [ ] Mobile responsive layout works
- [ ] Error states display properly

### Unit Tests (Example)

```javascript
// Example: test language selection
test('should load questions in Turkish', async () => {
  render(<Quiz />);
  const turkishButton = screen.getByText('Türkçe');
  fireEvent.click(turkishButton);
  
  await waitFor(() => {
    expect(screen.getByText(/Question 1 of 50/)).toBeInTheDocument();
  });
});
```

## Future Enhancements

1. **Auto-save:** Save progress to backend for mid-quiz resumption
2. **Time tracking:** Measure response time per question
3. **Comparison:** Compare user results to cohort statistics
4. **Sharing:** Social sharing of persona results
5. **History:** Track all quiz attempts for user
6. **Accessibility:** WCAG 2.1 Level AA compliance
7. **Offline:** Service worker for offline quiz taking

## Known Limitations

1. **No auto-save:** Closing browser loses progress
2. **Single session:** No resume from mid-quiz state
3. **No time limits:** All questions have unlimited response time
4. **Placeholder checkout:** Currently uses test URL instead of real Stripe session
5. **No analytics:** No event tracking for user behavior

## Support

For issues or questions:
1. Check test files: `tests/test_quiz_router.py`
2. Review API: `api/routers/quiz.py`
3. Check backend: `api/quiz_service.py`
4. Contact: [support email]

---

**Created:** June 14, 2026  
**Last Updated:** June 14, 2026  
**Status:** Ready for integration
