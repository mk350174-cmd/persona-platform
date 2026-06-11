import React, { useState } from 'react';
import MarkdownRenderer from './MarkdownRenderer';

const SAMPLE_CONVERSATIONS = {
  'socrates-ancient': [
    {
      role: 'user',
      content: 'What is the meaning of life?',
    },
    {
      role: 'assistant',
      content:
        'A profound question indeed, friend. But tell me first—what do *you* think gives life meaning? Do you pursue pleasure, honor, knowledge, or virtue? The answer lies not in my words, but in your own examination of life.',
    },
  ],
  'ada-lovelace': [
    {
      role: 'user',
      content: 'How do I start learning programming?',
    },
    {
      role: 'assistant',
      content: `Begin by understanding the *principles* before the practice. Programming is a dance between logic and creativity.

**Key steps:**
1. Learn mathematical foundations
2. Master one language deeply (not superficially)
3. Practice algorithm design through problem-solving
4. Study existing elegant code

As I wrote, the Analytical Engine has no pretensions whatever to *originate* anything—it can do whatever we know how to order it to perform. But it may assist us in accomplishing much in a way new and powerful.`,
    },
  ],
  'aristotle-ancient': [
    {
      role: 'user',
      content: 'What is virtue?',
    },
    {
      role: 'assistant',
      content: `Virtue, my friend, is a habit—a state of character that produces right action and genuine flourishing (*eudaimonia*).

It lies in the mean between excess and deficiency. Courage, for instance, is the middle ground between cowardice and recklessness. To cultivate virtue, one must:

- Practice virtuous actions repeatedly
- Learn from mentors and examples
- Develop practical wisdom (*phronesis*)
- Know that virtue is its own reward`,
    },
  ],
};

export default function SampleConversation({ personaId = 'socrates-ancient', onTryNow }) {
  const [messageCount, setMessageCount] = useState(0);
  const conversation = SAMPLE_CONVERSATIONS[personaId] || SAMPLE_CONVERSATIONS['socrates-ancient'];
  const isMaxed = messageCount >= 3;

  const handleSendMessage = () => {
    if (messageCount < 2) {
      setMessageCount(messageCount + 1);
    }
  };

  return (
    <div className="glass-panel rounded-xl p-6 space-y-4 max-h-96 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline-md text-on-surface">Sample Conversation (3 messages free)</h3>
        <div className="text-sm text-on-surface-variant">{messageCount + 1} / 3</div>
      </div>

      <div className="space-y-4">
        {conversation.slice(0, messageCount + 1).map((msg, idx) => (
          <div
            key={idx}
            className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div className={`text-2xl ${msg.role === 'user' ? '' : ''}`}>
              {msg.role === 'user' ? '👤' : '🎭'}
            </div>
            <div
              className={`rounded-lg px-4 py-3 max-w-xs ${
                msg.role === 'user'
                  ? 'user-bubble'
                  : 'ai-bubble'
              }`}
            >
              <MarkdownRenderer content={msg.content} />
            </div>
          </div>
        ))}
      </div>

      {!isMaxed && (
        <button
          onClick={handleSendMessage}
          className="mt-4 w-full py-2 px-4 rounded-lg bg-primary-container text-white hover:opacity-90 transition-opacity text-sm"
        >
          Continue Conversation
        </button>
      )}

      {isMaxed && (
        <div className="mt-4 p-4 rounded-lg bg-primary-container/20 border border-primary/30 space-y-3">
          <p className="text-sm text-on-surface-variant">
            You've reached the free preview limit. Sign up to unlock full conversations!
          </p>
          <button
            onClick={onTryNow}
            className="w-full py-2 px-4 rounded-lg bg-primary-container text-white hover:opacity-90 transition-opacity text-sm font-semibold"
          >
            Try Now
          </button>
        </div>
      )}
    </div>
  );
}
