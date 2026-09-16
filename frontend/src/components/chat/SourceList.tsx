import { Globe } from "lucide-react";

import { hostnameOf } from "@/lib/utils";
import type { Source } from "@/types";

export function SourceList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null;

  return (
    <div className="mt-3 space-y-1.5">
      <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-fg-subtle">
        <Globe className="size-3" />
        Sources
      </p>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((source, index) => (
          <a
            key={`${source.url}-${index}`}
            href={source.url}
            target="_blank"
            rel="noreferrer noopener"
            title={source.snippet}
            className="inline-flex max-w-[16rem] items-center gap-1.5 rounded-lg border border-line bg-surface px-2 py-1 text-xs text-fg-muted transition-colors hover:border-accent/40 hover:text-fg"
          >
            <span className="text-fg-subtle">{index + 1}.</span>
            <span className="truncate">{source.title || hostnameOf(source.url)}</span>
          </a>
        ))}
      </div>
    </div>
  );
}
