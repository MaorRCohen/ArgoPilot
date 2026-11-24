"use client";

import { useSyncExternalStore, type RefObject } from "react";
import { useInView, useReducedMotion } from "motion/react";

const subscribeNothing = () => () => {};

export const EASE_OUT = [0.23, 1, 0.32, 1] as const;

/**
 * Scroll-reveal state for one element. The server HTML and the first client render are the FINAL state
 * ("static"): nothing is hidden before JavaScript runs. After mount, an element that is still off screen switches
 * to "hidden" (nobody sees it happen) and plays its entrance when it scrolls into view, once.
 * With reduced motion it stays "static" for good: content identical, no movement.
 */
export function useReveal(ref: RefObject<Element | null>, margin = "0px 0px -8% 0px"): "static" | "hidden" | "shown" {
  const reduce = useReducedMotion();
  // false on the server and while hydrating, true afterwards: the first render is always the final state.
  const mounted = useSyncExternalStore(
    subscribeNothing,
    () => true,
    () => false,
  );
  const inView = useInView(ref, { once: true, margin: margin as `${number}px` });
  if (!mounted || reduce) return "static";
  return inView ? "shown" : "hidden";
}
