'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownRendererProps {
  content: string
  className?: string
}

// Helper to process text and replace [Doc X] with styled badges
const processContent = (children: React.ReactNode) => {
  if (typeof children !== 'string') return children;

  // Regex to match [Doc 1], [Doc: 1], [doc 1], [Doc 1 - WEB], etc.
  // Case insensitive, optional colon, flexible spacing
  const citationRegex = /(\[Doc\s*:?\s*\d+(?:\s*-\s*WEB)?\])/gi;

  const parts = children.split(citationRegex);

  return parts.map((part, index) => {
    // Check if this part is a citation
    const match = part.match(/\[Doc\s*:?\s*(\d+)(?:\s*-\s*WEB)?\]/i);
    if (match) {
      const docNum = match[1];
      return (
        <span
          key={index}
          className="inline-flex items-center justify-center w-5 h-5 ml-1 text-[10px] font-bold text-primary bg-primary/10 rounded-full align-top cursor-help hover:bg-primary/20 transition-colors"
          title={`Source Document ${docNum}`}
        >
          {docNum}
        </span>
      );
    }
    return part;
  });
};

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`prose prose-sm max-w-none dark:prose-invert ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Custom styling for better appearance - NotebookLM inspired
          h1: ({ children }) => (
            <h1 className="text-xl font-semibold text-foreground tracking-tight mb-4 mt-6 first:mt-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-medium text-foreground tracking-tight mb-3 mt-5 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-medium text-foreground/90 mb-2 mt-4 first:mt-0">
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p className="text-[15px] leading-7 text-foreground/90 mb-4 last:mb-0">
              {processContent(children)}
            </p>
          ),
          ul: ({ children }) => (
            <ul className="my-3 ml-4 space-y-2">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-3 ml-4 list-decimal space-y-2 marker:text-muted-foreground">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="text-[15px] leading-7 text-foreground/90 pl-1">
              {processContent(children)}
            </li>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className="italic text-foreground/80">
              {children}
            </em>
          ),
          code: ({ children }) => (
            <code className="bg-muted/50 px-1.5 py-0.5 rounded text-[13px] font-mono text-foreground/90 border border-border/50">
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre className="bg-muted/50 p-4 rounded-xl overflow-x-auto text-xs font-mono text-foreground border border-border/50 mb-4 mt-2">
              {children}
            </pre>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary/40 pl-4 italic text-muted-foreground my-4">
              {children}
            </blockquote>
          ),
          hr: () => (
            <hr className="border-border/60 my-6" />
          ),
          table: ({ children }) => (
            <div className="overflow-x-auto my-4 rounded-lg border border-border/60">
              <table className="min-w-full divide-y divide-border/60">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="px-4 py-3 bg-muted/30 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-3 text-sm text-foreground/90 border-t border-border/40 whitespace-pre-wrap">
              {processContent(children)}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
