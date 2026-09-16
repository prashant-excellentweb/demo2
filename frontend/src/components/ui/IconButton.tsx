import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Required: an icon alone gives assistive tech nothing to announce. */
  label: string;
  size?: "sm" | "md";
  active?: boolean;
  children: ReactNode;
}

export function IconButton({
  label,
  size = "md",
  active = false,
  className,
  children,
  ...rest
}: IconButtonProps) {
  return (
    <button
      {...rest}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-lg transition-colors",
        "text-fg-muted hover:bg-surface-hover hover:text-fg",
        "disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent",
        size === "sm" ? "size-7" : "size-9",
        active && "bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent",
        className,
      )}
    >
      {children}
    </button>
  );
}
