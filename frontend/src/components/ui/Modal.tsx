import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

import { IconButton } from "@/components/ui/IconButton";

interface ModalProps {
  open: boolean;
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}

export function Modal({
  open,
  title,
  description,
  onClose,
  children,
  footer,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);

    // Prevent the page behind the overlay from scrolling.
    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";

    // Move focus into the dialog so keyboard users are not left behind it.
    panelRef.current?.querySelector<HTMLElement>(
      "input, textarea, button, [tabindex]",
    )?.focus();

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = overflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="presentation"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
        className="animate-fade-up w-full max-w-md overflow-hidden rounded-2xl border border-line bg-elevated shadow-2xl"
      >
        <header className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div>
            <h2 className="text-base font-semibold text-fg">{title}</h2>
            {description && (
              <p className="mt-0.5 text-xs text-fg-muted">{description}</p>
            )}
          </div>
          <IconButton label="Close dialog" size="sm" onClick={onClose}>
            <X className="size-4" />
          </IconButton>
        </header>

        <div className="space-y-4 px-5 py-5">{children}</div>

        {footer && (
          <footer className="flex justify-end gap-2 border-t border-line bg-surface/60 px-5 py-4">
            {footer}
          </footer>
        )}
      </div>
    </div>
  );
}
