import type { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const VARIANTS: Record<Variant, string> = {
  primary: "bg-accent text-accent-fg hover:bg-accent-hover shadow-sm",
  secondary: "bg-surface text-fg border border-line hover:bg-surface-hover",
  ghost: "text-fg-muted hover:bg-surface-hover hover:text-fg",
  danger: "bg-danger/10 text-danger border border-danger/25 hover:bg-danger/20",
};

const SIZES: Record<Size, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-sm gap-2",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  isLoading?: boolean;
  children?: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  isLoading = false,
  className,
  disabled,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || isLoading}
      className={cn(
        "inline-flex items-center justify-center rounded-xl font-medium transition-colors",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
    >
      {isLoading && (
        <span className="size-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}
      {children}
    </button>
  );
}
