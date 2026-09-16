import { useEffect, useRef, type ChangeEvent, type KeyboardEvent } from "react";
import { ArrowUp, FileText, Globe, Mic, Paperclip, Square, X } from "lucide-react";

import { PlusMenu } from "@/components/chat/PlusMenu";
import { IconButton } from "@/components/ui/IconButton";
import { attachmentUrl } from "@/lib/api";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { cn, formatBytes } from "@/lib/utils";
import type { Attachment } from "@/types";

const MAX_TEXTAREA_HEIGHT = 208;

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  attachments: Attachment[];
  uploadingNames: string[];
  onAddFiles: (files: File[]) => void;
  onRemoveAttachment: (id: string) => void;
  webSearch: boolean;
  onToggleWebSearch: () => void;
  isStreaming: boolean;
  onStop: () => void;
  temporary: boolean;
}

export function Composer({
  value,
  onChange,
  onSubmit,
  attachments,
  uploadingNames,
  onAddFiles,
  onRemoveAttachment,
  webSearch,
  onToggleWebSearch,
  isStreaming,
  onStop,
  temporary,
}: ComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const speech = useSpeechRecognition((transcript) => {
    onChange(value ? `${value} ${transcript}` : transcript);
    textareaRef.current?.focus();
  });

  // Grow with the content up to a cap, then scroll inside the field.
  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT)}px`;
  }, [value]);

  const canSend = (value.trim().length > 0 || attachments.length > 0) && !isStreaming;

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSend) onSubmit();
    }
  };

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length > 0) onAddFiles(files);
    // Reset so selecting the same file twice still fires a change event.
    event.target.value = "";
  };

  return (
    <div className="border-t border-line bg-canvas/80 backdrop-blur">
      <div className="mx-auto w-full max-w-3xl px-4 py-3">
        {(attachments.length > 0 || uploadingNames.length > 0) && (
          <div className="mb-2 flex flex-wrap gap-2">
            {attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="group relative flex items-center gap-2 rounded-xl border border-line bg-surface py-1.5 pl-1.5 pr-8"
              >
                {attachment.is_image ? (
                  <img
                    src={attachmentUrl(attachment.id)}
                    alt={attachment.filename}
                    className="size-8 rounded-lg object-cover"
                  />
                ) : (
                  <span className="flex size-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
                    {attachment.content_type === "application/pdf" ? (
                      <FileText className="size-4" />
                    ) : (
                      <Paperclip className="size-4" />
                    )}
                  </span>
                )}
                <span className="min-w-0">
                  <span className="block max-w-[10rem] truncate text-xs font-medium text-fg">
                    {attachment.filename}
                  </span>
                  <span className="block text-[11px] text-fg-subtle">
                    {formatBytes(attachment.size_bytes)}
                  </span>
                </span>
                <button
                  type="button"
                  onClick={() => onRemoveAttachment(attachment.id)}
                  aria-label={`Remove ${attachment.filename}`}
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-0.5 text-fg-subtle transition-colors hover:bg-surface-hover hover:text-fg"
                >
                  <X className="size-3.5" />
                </button>
              </div>
            ))}

            {uploadingNames.map((name) => (
              <div
                key={name}
                className="flex items-center gap-2 rounded-xl border border-line bg-surface px-3 py-2.5"
              >
                <span className="size-3.5 animate-spin rounded-full border-2 border-accent border-t-transparent" />
                <span className="max-w-[10rem] truncate text-xs text-fg-muted">{name}</span>
              </div>
            ))}
          </div>
        )}

        <div
          className={cn(
            "flex items-end gap-1.5 rounded-2xl border bg-surface p-2 transition-colors",
            "focus-within:border-accent/50",
            temporary ? "border-accent/40" : "border-line",
          )}
        >
          <PlusMenu
            webSearch={webSearch}
            onToggleWebSearch={onToggleWebSearch}
            onPickFiles={() => fileInputRef.current?.click()}
            onPickImages={() => imageInputRef.current?.click()}
            disabled={isStreaming}
          />

          <textarea
            ref={textareaRef}
            value={value}
            rows={1}
            disabled={isStreaming}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isStreaming
                ? "Waiting for the reply..."
                : temporary
                  ? "Ask anything (not saved)"
                  : "Ask anything"
            }
            aria-label="Message"
            className="max-h-52 flex-1 resize-none bg-transparent px-1 py-2 text-sm text-fg placeholder:text-fg-subtle focus:outline-none disabled:cursor-not-allowed"
          />

          {speech.isSupported && (
            <IconButton
              label={speech.isListening ? "Stop dictation" : "Dictate message"}
              active={speech.isListening}
              disabled={isStreaming}
              onClick={speech.toggle}
            >
              <Mic className="size-[18px]" />
            </IconButton>
          )}

          {isStreaming ? (
            <IconButton
              label="Stop generating"
              onClick={onStop}
              className="bg-surface-hover text-fg"
            >
              <Square className="size-4 fill-current" />
            </IconButton>
          ) : (
            <IconButton
              label="Send message"
              onClick={onSubmit}
              disabled={!canSend}
              className={cn(
                canSend && "bg-accent text-accent-fg hover:bg-accent-hover hover:text-accent-fg",
              )}
            >
              <ArrowUp className="size-[18px]" />
            </IconButton>
          )}
        </div>

        <div className="mt-2 flex items-center justify-center gap-3 text-[11px] text-fg-subtle">
          {webSearch && (
            <span className="inline-flex items-center gap-1 text-accent">
              <Globe className="size-3" />
              Web research on
            </span>
          )}
          <span>
            {isStreaming
              ? "Answering - stop it to ask something else"
              : "Enter to send, Shift + Enter for a new line"}
          </span>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          hidden
          accept=".txt,.md,.csv,.json,.pdf,.png,.jpg,.jpeg,.gif,.webp"
          onChange={handleFiles}
        />
        <input
          ref={imageInputRef}
          type="file"
          multiple
          hidden
          accept="image/png,image/jpeg,image/gif,image/webp"
          onChange={handleFiles}
        />
      </div>
    </div>
  );
}
