import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Check, Pencil, Trash2, X } from "lucide-react";

import { cn } from "@/lib/utils";
import type { ChatSummary } from "@/types";

interface ChatListItemProps {
  chat: ChatSummary;
  isActive: boolean;
  onSelect: () => void;
  onRename: (title: string) => void;
  onDelete: () => void;
}

export function ChatListItem({
  chat,
  isActive,
  onSelect,
  onRename,
  onDelete,
}: ChatListItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(chat.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing]);

  const commit = () => {
    const cleaned = draft.trim();
    if (cleaned && cleaned !== chat.title) onRename(cleaned);
    setIsEditing(false);
  };

  const cancel = () => {
    setDraft(chat.title);
    setIsEditing(false);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") commit();
    if (event.key === "Escape") cancel();
  };

  if (isEditing) {
    return (
      <div className="flex items-center gap-1 rounded-lg bg-surface-hover px-2 py-1.5">
        <input
          ref={inputRef}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={onKeyDown}
          aria-label="Chat title"
          className="min-w-0 flex-1 bg-transparent text-sm text-fg focus:outline-none"
        />
        <button
          type="button"
          onClick={commit}
          aria-label="Save title"
          className="rounded p-1 text-success hover:bg-surface"
        >
          <Check className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={cancel}
          aria-label="Cancel rename"
          className="rounded p-1 text-fg-subtle hover:bg-surface"
        >
          <X className="size-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group relative flex items-center rounded-lg transition-colors",
        isActive ? "bg-surface-hover" : "hover:bg-surface-hover",
      )}
    >
      <button
        type="button"
        onClick={onSelect}
        className={cn(
          "min-w-0 flex-1 truncate px-2.5 py-2 text-left text-sm transition-colors",
          isActive ? "font-medium text-fg" : "text-fg-muted group-hover:text-fg",
        )}
      >
        {chat.title || "New Chat"}
      </button>

      {/* Revealed on hover so the list stays quiet at rest. */}
      <div
        className={cn(
          "absolute right-1 flex items-center gap-0.5 rounded-lg pl-2",
          "bg-gradient-to-l from-surface-hover via-surface-hover",
          "opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100",
        )}
      >
        <button
          type="button"
          onClick={() => setIsEditing(true)}
          aria-label={`Rename ${chat.title}`}
          className="rounded p-1 text-fg-subtle transition-colors hover:text-fg"
        >
          <Pencil className="size-3.5" />
        </button>
        <button
          type="button"
          onClick={onDelete}
          aria-label={`Delete ${chat.title}`}
          className="rounded p-1 text-fg-subtle transition-colors hover:text-danger"
        >
          <Trash2 className="size-3.5" />
        </button>
      </div>
    </div>
  );
}
