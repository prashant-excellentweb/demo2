import { AlertCircle } from "lucide-react";

import { MessageBubble } from "@/components/chat/MessageBubble";
import { ThinkingIndicator } from "@/components/chat/ThinkingIndicator";
import type { Attachment, Source } from "@/types";

export interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  attachments: Attachment[];
  sources: Source[] | null;
  /** Only persisted user messages can be rewound and resent. */
  editable: boolean;
}

interface MessageTimelineProps {
  messages: DisplayMessage[];
  streamingText: string;
  streamingSources: Source[] | null;
  isStreaming: boolean;
  statusLabel: string | null;
  error: string | null;
  onEdit: (message: DisplayMessage) => void;
}

export function MessageTimeline({
  messages,
  streamingText,
  streamingSources,
  isStreaming,
  statusLabel,
  error,
  onEdit,
}: MessageTimelineProps) {
  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-6">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          role={message.role}
          content={message.content}
          attachments={message.attachments}
          sources={message.sources}
          onEdit={message.editable ? () => onEdit(message) : undefined}
        />
      ))}

      {/* Before the first token lands there is nothing to render but progress. */}
      {isStreaming && !streamingText && <ThinkingIndicator label={statusLabel ?? undefined} />}

      {streamingText && (
        <MessageBubble
          role="assistant"
          content={streamingText}
          sources={streamingSources}
          isStreaming={isStreaming}
        />
      )}

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl border border-danger/30 bg-danger/10 p-3.5 text-sm text-danger"
        >
          <AlertCircle className="mt-0.5 size-4 shrink-0" />
          <p>{error}</p>
        </div>
      )}
    </div>
  );
}
