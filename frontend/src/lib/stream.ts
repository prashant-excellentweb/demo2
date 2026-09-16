import { ApiError } from "@/lib/api";
import type { Source } from "@/types";

export type StreamEvent =
  | {
      type: "start";
      chat_id: string | null;
      user_message_id?: string;
      title?: string;
      sources?: Source[];
    }
  | { type: "delta"; text: string }
  | { type: "done"; message_id?: string; tokens?: number; chat_total_tokens?: number }
  | { type: "error"; message: string };

/**
 * Consume a server-sent event stream opened with POST.
 *
 * `EventSource` only issues GET requests and cannot send a JSON body, so the
 * stream is read straight off the `fetch` response instead.
 */
export async function* streamChat(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}.`;
    try {
      const parsed = (await response.json()) as { detail?: unknown };
      if (typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      // Keep the status-based fallback.
    }
    throw new ApiError(response.status, detail);
  }

  if (!response.body) {
    throw new ApiError(500, "This browser cannot read streamed responses.");
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";

  try {
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += value;

      // Events are separated by a blank line; a partial tail stays buffered
      // until the rest of it arrives.
      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const parsed = parseBlock(block);
        if (parsed) yield parsed;
        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.cancel().catch(() => undefined);
  }
}

function parseBlock(block: string): StreamEvent | null {
  const data = block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");

  if (!data) return null;

  try {
    return JSON.parse(data) as StreamEvent;
  } catch {
    return null;
  }
}
