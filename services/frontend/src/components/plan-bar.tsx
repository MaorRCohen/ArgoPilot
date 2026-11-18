"use client";

import { useRef } from "react";
import { m } from "motion/react";
import { EASE_OUT, useReveal } from "@/components/motion/use-reveal";
import { cn } from "@/lib/utils";

/** The soil-water bar of one day: it slides in from the left when the list scrolls into view (a transform, clipped by the track). */
export function PlanBar({
  pct,
  triggerPct,
  enough,
  index,
}: {
  pct: number;
  triggerPct: number;
  enough: boolean;
  index: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const hidden = useReveal(ref, "0px 0px -6% 0px") === "hidden";
  return (
    <div
      ref={ref}
      role="img"
      aria-label={`Soil water at the end of the day: ${Math.round(pct)}%`}
      className="relative h-2.5 flex-1 overflow-hidden rounded-full bg-muted ring-1 ring-border"
    >
      <m.div
        className={cn("h-full rounded-full", enough ? "bg-leaf" : "bg-water")}
        style={{ width: `${pct}%` }}
        initial={false}
        animate={
          hidden
            ? { x: "-101%", transition: { duration: 0 } }
            : { x: 0, transition: { duration: 0.9, delay: 0.1 + index * 0.07, ease: EASE_OUT } }
        }
      />
      <div className="absolute inset-y-0 w-0.5 bg-foreground" style={{ left: `${triggerPct}%` }} />
    </div>
  );
}
