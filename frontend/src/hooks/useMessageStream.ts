import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api";
import { streamChat, type StreamEvent } from "@/lib/stream";
import type { Source } from "@/types";

interface StreamHandlers {
  onStart?: (event: Extract<StreamEvent, { type: "start" }>) => void;
  /** Receives the full reply text; not called when the stream errors. */
  onDone?: (text: string) => void;
}

/** Returned by `start` so callers do not have to read state that updates async. */
export interface StreamResult {
  text: string;
  error: string | null;
  aborted: boolean;
}

interface StreamState {
  isStreaming: boolean;
  text: string;
  sources: Source[] | null;
  error: string | null;
}

const IDLE: StreamState = { isStreaming: false, text: "", sources: null, error: null };

/**
 * Drives one streamed completion and exposes the partial text for rendering.
 *
 * The in-flight reply is deliberately component state rather than query cache:
 * it changes many times per second, and the persisted transcript is refetched
 * once the stream closes.
 */
export function useMessageStream() {
  const [state, setState] = useState<StreamState>(IDLE);
  const abortRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    // Set on every mount, not just declared once: StrictMode mounts, unmounts
    // and remounts in development, and without this the cleanup below leaves
    // the ref permanently false, so `start` discards every event it reads.
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
    };
  }, []);

  const reset = useCallback(() => setState(IDLE), []);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setState((current) => ({ ...current, isStreaming: false }));
  }, []);

  const start = useCallback(
    async (
      path: string,
      body: unknown,
      handlers: StreamHandlers = {},
    ): Promise<StreamResult> => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      setState({ isStreaming: true, text: "", sources: null, error: null });

      let accumulated = "";
      try {
        for await (const event of streamChat(path, body, controller.signal)) {
          if (!mountedRef.current) return { text: accumulated, error: null, aborted: true };

          switch (event.type) {
            case "start":
              setState((current) => ({ ...current, sources: event.sources ?? null }));
              handlers.onStart?.(event);
              break;
            case "delta":
              accumulated += event.text;
              setState((current) => ({ ...current, text: accumulated }));
              break;
            case "error":
              setState((current) => ({
                ...current,
                isStreaming: false,
                error: event.message,
              }));
              return { text: accumulated, error: event.message, aborted: false };
            case "done":
              setState((current) => ({ ...current, isStreaming: false }));
              handlers.onDone?.(accumulated);
              return { text: accumulated, error: null, aborted: false };
          }
        }
        // The stream closed without a terminal event (a proxy timeout, say);
        // keep whatever text arrived rather than discarding it.
        setState((current) => ({ ...current, isStreaming: false }));
        handlers.onDone?.(accumulated);
        return { text: accumulated, error: null, aborted: false };
      } catch (error) {
        const aborted = error instanceof DOMException && error.name === "AbortError";
        const message = aborted
          ? null
          : error instanceof ApiError
            ? error.message
            : "Could not reach the server. Check your connection and try again.";

        if (mountedRef.current) {
          setState({
            isStreaming: false,
            text: accumulated,
            sources: null,
            error: message,
          });
        }
        return { text: accumulated, error: message, aborted };
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
      }
    },
    [],
  );

  return { ...state, start, stop, reset };
}
