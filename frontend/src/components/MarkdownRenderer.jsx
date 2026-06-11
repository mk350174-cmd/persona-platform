import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';

const markdownComponents = {
  code({ node, inline, className, children, ...props }) {
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : 'javascript';

    if (inline) {
      return (
        <code className="bg-surface-container px-2 py-1 rounded text-primary text-sm" {...props}>
          {children}
        </code>
      );
    }

    return (
      <SyntaxHighlighter
        style={atomDark}
        language={language}
        PreTag="div"
        className="rounded-lg my-4"
        {...props}
      >
        {String(children).replace(/\n$/, '')}
      </SyntaxHighlighter>
    );
  },
  h1: ({ node, ...props }) => <h1 className="text-2xl font-bold text-on-surface my-4" {...props} />,
  h2: ({ node, ...props }) => <h2 className="text-xl font-bold text-on-surface my-3" {...props} />,
  h3: ({ node, ...props }) => <h3 className="text-lg font-bold text-on-surface my-2" {...props} />,
  p: ({ node, ...props }) => <p className="text-on-surface my-2 leading-relaxed" {...props} />,
  ul: ({ node, ...props }) => <ul className="list-disc list-inside my-2 text-on-surface" {...props} />,
  ol: ({ node, ...props }) => <ol className="list-decimal list-inside my-2 text-on-surface" {...props} />,
  li: ({ node, ...props }) => <li className="ml-4 my-1" {...props} />,
  blockquote: ({ node, ...props }) => (
    <blockquote className="border-l-4 border-primary pl-4 my-2 text-on-surface-variant italic" {...props} />
  ),
  a: ({ node, ...props }) => (
    <a className="text-primary hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
  ),
  table: ({ node, ...props }) => (
    <table className="border-collapse border border-border-glass my-4 w-full" {...props} />
  ),
  th: ({ node, ...props }) => (
    <th className="border border-border-glass bg-surface-container-high px-4 py-2 text-on-surface" {...props} />
  ),
  td: ({ node, ...props }) => (
    <td className="border border-border-glass px-4 py-2 text-on-surface" {...props} />
  ),
};

export default function MarkdownRenderer({ content }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={markdownComponents}
      className="prose prose-invert max-w-none"
    >
      {content}
    </ReactMarkdown>
  );
}
