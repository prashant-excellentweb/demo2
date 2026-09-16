import { Sparkles } from "lucide-react";

export function ThinkingIndicator({ label }: { label?: string }) {
  return (
    <article className="animate-fade-up flex gap-3">
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
        <Sparkles className="size-4" />
      </div>
      <div className="flex h-8 items-center gap-2">
        <span className="flex gap-1">
          {[0, 1, 2].map((dot) => (
            <span
              key={dot}
              className="size-2 animate-bounce rounded-full bg-fg-subtle"
              style={{ animationDelay: `${dot * 140}ms`, animationDuration: "900ms" }}
            />
          ))}
        </span>
        {label && <span className="text-xs text-fg-muted">{label}</span>}
      </div>
    </article>
  );
}
