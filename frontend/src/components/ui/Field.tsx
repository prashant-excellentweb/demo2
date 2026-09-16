import { useId, type InputHTMLAttributes, type ReactNode } from "react";

import { cn } from "@/lib/utils";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: ReactNode;
}

export function Field({ label, hint, className, id, ...rest }: FieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const hintId = hint ? `${inputId}-hint` : undefined;

  return (
    <div className="space-y-1.5">
      <label htmlFor={inputId} className="block text-xs font-medium text-fg-muted">
        {label}
      </label>
      <input
        {...rest}
        id={inputId}
        aria-describedby={hintId}
        className={cn(
          "w-full rounded-xl border border-line bg-canvas px-3.5 py-2.5 text-sm text-fg",
          "placeholder:text-fg-subtle focus:border-accent focus:outline-none",
          "transition-colors",
          className,
        )}
      />
      {hint && (
        <p id={hintId} className="text-xs text-fg-subtle">
          {hint}
        </p>
      )}
    </div>
  );
}
