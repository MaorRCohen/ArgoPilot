"use client";

import { useRef, type ReactNode } from "react";
import { m } from "motion/react";
import { EASE_OUT, useReveal } from "./use-reveal";

/** Scroll-reveal for a section: fades up once when it enters the viewport. */
export function Reveal({
  children,
  className,
  delay = 0,
  y = 28,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  y?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const state = useReveal(ref);
  const hidden = state === "hidden";
  return (
    <m.div
      ref={ref}
      className={className}
      initial={false}
      animate={
        hidden
          ? { opacity: 0, y, transition: { duration: 0 } }
          : { opacity: 1, y: 0, transition: { duration: 0.6, delay, ease: EASE_OUT } }
      }
    >
      {children}
    </m.div>
  );
}
