import { memo, useRef, useState, type ReactNode } from "react";
import Markdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";
import { Check, Copy } from "lucide-react";

import { cn } from "@/lib/utils";

function CodeBlock({ children }: { children?: ReactNode }) {
  const preRef = useRef<HTMLPreElement>(null);
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    const text = preRef.current?.textContent ?? "";
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="group/code relative">
      <button
        type="button"
        onClick={copy}
        aria-label={copied ? "Copied" : "Copy code"}
        className={cn(
          "absolute right-2.5 top-2.5 z-10 inline-flex items-center gap-1 rounded-lg",
          "border border-white/15 bg-white/10 px-2 py-1 text-[11px] font-medium text-white/80",
          "opacity-0 transition group-hover/code:opacity-100 focus-visible:opacity-100",
          "hover:bg-white/20 hover:text-white",
        )}
      >
        {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
        {copied ? "Copied" : "Copy"}
      </button>
      <pre ref={preRef}>{children}</pre>
    </div>
  );
}

/**
 * Renders assistant markdown.
 *
 * `react-markdown` does not pass raw HTML through, so untrusted model output
 * cannot inject markup and no separate sanitiser is needed.
 */
export const MarkdownMessage = memo(function MarkdownMessage({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  return (
    <div className={cn("markdown", className)}>
      <Markdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeHighlight, { detect: true, ignoreMissing: true }]]}
        components={{
          pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </Markdown>
    </div>
  );
});
