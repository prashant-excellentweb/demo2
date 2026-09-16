import type { ReactNode } from "react";
import { Sparkles } from "lucide-react";

interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
  footer: ReactNode;
}

export function AuthLayout({ title, subtitle, children, footer }: AuthLayoutProps) {
  return (
    <div className="flex min-h-full items-center justify-center bg-canvas px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <span className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-accent text-accent-fg shadow-lg">
            <Sparkles className="size-6" />
          </span>
          <h1 className="text-xl font-semibold tracking-tight text-fg">{title}</h1>
          <p className="mt-1 text-sm text-fg-muted">{subtitle}</p>
        </div>

        <div className="rounded-2xl border border-line bg-surface p-6 shadow-sm">
          {children}
        </div>

        <p className="mt-6 text-center text-sm text-fg-muted">{footer}</p>
      </div>
    </div>
  );
}
