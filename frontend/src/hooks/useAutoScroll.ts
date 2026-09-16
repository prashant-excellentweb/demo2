import { useCallback, useEffect, useRef } from "react";

const PINNED_THRESHOLD_PX = 120;

/**
 * Keeps a scroll container pinned to the newest content.
 *
 * Only follows along while the user is already near the bottom, so scrolling up
 * to reread an earlier answer is not yanked back down by incoming tokens.
 */
export function useAutoScroll<T>(dependency: T) {
  const containerRef = useRef<HTMLDivElement>(null);
  const pinnedRef = useRef(true);

  const handleScroll = useCallback(() => {
    const element = containerRef.current;
    if (!element) return;
    const distanceFromBottom =
      element.scrollHeight - element.scrollTop - element.clientHeight;
    pinnedRef.current = distanceFromBottom < PINNED_THRESHOLD_PX;
  }, []);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "smooth") => {
    const element = containerRef.current;
    if (!element) return;
    element.scrollTo({ top: element.scrollHeight, behavior });
    pinnedRef.current = true;
  }, []);

  useEffect(() => {
    if (pinnedRef.current) {
      containerRef.current?.scrollTo({
        top: containerRef.current.scrollHeight,
        behavior: "auto",
      });
    }
  }, [dependency]);

  return { containerRef, handleScroll, scrollToBottom };
}
