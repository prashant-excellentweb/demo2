import { Code2, FileText, GraduationCap, Lightbulb, Shield } from "lucide-react";

import { Toggle } from "@/components/ui/Toggle";

const SUGGESTIONS = [
  { icon: Code2, text: "Review this function for N+1 query problems" },
  { icon: FileText, text: "Summarise the key points of a document I upload" },
  { icon: Lightbulb, text: "Explain database indexing with a worked example" },
  { icon: GraduationCap, text: "Teach me the difference between JWT and sessions" },
];

interface EmptyStateProps {
  greeting: string;
  temporary: boolean;
  onTemporaryChange: (value: boolean) => void;
  onPickSuggestion: (text: string) => void;
}

export function EmptyState({
  greeting,
  temporary,
  onTemporaryChange,
  onPickSuggestion,
}: EmptyStateProps) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center px-4 py-12 text-center">
      <h1 className="text-2xl font-semibold tracking-tight text-fg sm:text-3xl">
        {greeting}
      </h1>
      <p className="mt-2 text-sm text-fg-muted">
        Ask anything, attach files, or turn on web research from the + menu.
      </p>

      <div className="mt-8 grid w-full gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map(({ icon: Icon, text }) => (
          <button
            key={text}
            type="button"
            onClick={() => onPickSuggestion(text)}
            className="flex items-start gap-3 rounded-xl border border-line bg-surface/60 p-3 text-left text-sm text-fg-muted transition-colors hover:border-accent/40 hover:bg-surface hover:text-fg"
          >
            <Icon className="mt-0.5 size-4 shrink-0 text-accent" />
            <span>{text}</span>
          </button>
        ))}
      </div>

      <div className="mt-8 flex w-full items-center gap-3 rounded-xl border border-line bg-surface/60 p-3.5 text-left">
        <Shield className="size-5 shrink-0 text-accent" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-fg">Temporary chat</p>
          <p className="text-xs text-fg-muted">
            Nothing is saved to your history. Usage limits still apply.
          </p>
        </div>
        <Toggle
          checked={temporary}
          onChange={onTemporaryChange}
          label="Temporary chat"
        />
      </div>
    </div>
  );
}
