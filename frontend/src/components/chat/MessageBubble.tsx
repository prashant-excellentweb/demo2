import { useState } from "react";
import { Check, Copy, Pencil, Sparkles } from "lucide-react";

import { AttachmentChips } from "@/components/chat/AttachmentChips";
import { MarkdownMessage } from "@/components/chat/MarkdownMessage";
import { SourceList } from "@/components/chat/SourceList";
import { cn } from "@/lib/utils";
import type { Attachment, Source } from "@/types";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  attachments?: Attachment[];
  sources?: Source[] | null;
  /** Renders a blinking caret while tokens are still arriving. */
  isStreaming?: boolean;
  onEdit?: () => void;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1800);
      }}
      className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-fg-subtle transition-colors hover:bg-surface-hover hover:text-fg"
    >
      {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export function MessageBubble({
  role,
  content,
  attachments = [],
  sources,
  isStreaming = false,
  onEdit,
}: MessageBubbleProps) {
  if (role === "user") {
    return (
      <article className="animate-fade-up group flex flex-col items-end gap-2">
        {attachments.length > 0 && (
          <div className="flex justify-end">
            <AttachmentChips attachments={attachments} />
          </div>
        )}

        {content && (
          <div className="max-w-[min(42rem,85%)] rounded-2xl rounded-br-md bg-bubble-user px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words text-bubble-user-fg">
            {content}
          </div>
        )}

        {onEdit && (
          <div className="opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
            <button
              type="button"
              onClick={onEdit}
              className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs text-fg-subtle transition-colors hover:bg-surface-hover hover:text-fg"
            >
              <Pencil className="size-3.5" />
              Edit
            </button>
          </div>
        )}
      </article>
    );
  }

  return (
    <article className="animate-fade-up group flex gap-3">
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
        <Sparkles className="size-4" />
      </div>

      <div className="min-w-0 flex-1">
        <MarkdownMessage
          content={content}
          className={cn(isStreaming && "stream-caret")}
        />

        {sources && sources.length > 0 && <SourceList sources={sources} />}

        {!isStreaming && content && (
          <div className="mt-1.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
            <CopyButton text={content} />
          </div>
        )}
      </div>
    </article>
  );
}
