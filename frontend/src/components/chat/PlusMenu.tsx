import { useEffect, useRef, useState } from "react";
import { Check, Globe, ImageIcon, Paperclip, Plus } from "lucide-react";

import { IconButton } from "@/components/ui/IconButton";
import { cn } from "@/lib/utils";

interface PlusMenuProps {
  webSearch: boolean;
  onToggleWebSearch: () => void;
  onPickFiles: () => void;
  onPickImages: () => void;
  disabled?: boolean;
}

export function PlusMenu({
  webSearch,
  onToggleWebSearch,
  onPickFiles,
  onPickImages,
  disabled,
}: PlusMenuProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const onPointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };

    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const items = [
    { icon: Paperclip, label: "Add files", onClick: onPickFiles },
    { icon: ImageIcon, label: "Add photos", onClick: onPickImages },
  ];

  return (
    <div ref={containerRef} className="relative">
      <IconButton
        label="Add attachments or tools"
        disabled={disabled}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <Plus className={cn("size-5 transition-transform", open && "rotate-45")} />
      </IconButton>

      {open && (
        <div
          role="menu"
          className="animate-fade-up absolute bottom-full left-0 z-20 mb-2 w-56 overflow-hidden rounded-xl border border-line bg-elevated p-1 shadow-xl"
        >
          {items.map(({ icon: Icon, label, onClick }) => (
            <button
              key={label}
              type="button"
              role="menuitem"
              onClick={() => {
                onClick();
                setOpen(false);
              }}
              className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-hover hover:text-fg"
            >
              <Icon className="size-4" />
              {label}
            </button>
          ))}

          <div className="my-1 h-px bg-line" />

          <button
            type="button"
            role="menuitemcheckbox"
            aria-checked={webSearch}
            onClick={() => {
              onToggleWebSearch();
              setOpen(false);
            }}
            className="flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm text-fg-muted transition-colors hover:bg-surface-hover hover:text-fg"
          >
            <Globe className="size-4" />
            <span className="flex-1 text-left">Web research</span>
            {webSearch && <Check className="size-4 text-accent" />}
          </button>
        </div>
      )}
    </div>
  );
}
