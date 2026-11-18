"use client";

import { useRef, type ReactNode } from "react";
import { m, useReducedMotion, useScroll, useTransform } from "motion/react";

/**
 * The hero photo: it scrolls slower than the page (scroll-linked parallax) and slowly pushes in (Ken Burns, CSS).
 * The layer is taller than the hero so the parallax never shows an edge. `children` is the next/image, rendered on the server.
 */
export function HeroMedia({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const y = useTransform(scrollYProgress, [0, 1], ["0%", reduce ? "0%" : "12%"]);

  return (
    <div ref={ref} className="absolute inset-0 -z-30 overflow-hidden">
      <m.div style={{ y }} className="absolute inset-x-0 -top-[18%] -bottom-[18%]">
        <div className="kenburns absolute inset-0">{children}</div>
      </m.div>
    </div>
  );
}
