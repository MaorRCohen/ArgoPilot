"use client";

import { createContext, useContext, useRef, type ReactNode } from "react";
import { m } from "motion/react";
import { EASE_OUT, useReveal } from "@/components/motion/use-reveal";

type State = "static" | "hidden" | "shown";
const RevealState = createContext<State>("static");

/**
 * Wraps one chart drawing. The server HTML shows the finished chart; once on the client, a chart that is still off
 * screen resets and plays its entrance when it scrolls into view (lines draw, bars drop). Reduced motion: stays finished.
 */
export function ChartScope({ children, className }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const state = useReveal(ref, "0px 0px -12% 0px");
  return (
    <div ref={ref} className={className}>
      <RevealState.Provider value={state}>{children}</RevealState.Provider>
    </div>
  );
}

const draw = (hidden: boolean, delay: number) =>
  hidden
    ? { pathLength: 0, opacity: 0, transition: { duration: 0 } }
    : { pathLength: 1, opacity: 1, transition: { duration: 1.2, delay, ease: EASE_OUT } };

/** A line that draws itself from left to right (stroke length is animated, nothing else). */
export function DrawLine({
  points,
  className,
  strokeWidth,
  delay = 0.3,
}: {
  points: string;
  className: string;
  strokeWidth: number;
  delay?: number;
}) {
  const hidden = useContext(RevealState) === "hidden";
  return (
    <m.polyline
      points={points}
      pathLength={1}
      fill="none"
      strokeWidth={strokeWidth}
      strokeLinejoin="round"
      strokeLinecap="round"
      className={className}
      initial={false}
      animate={draw(hidden, delay)}
    />
  );
}

/** A dashed line revealed by a solid line that draws itself inside a mask (a dash pattern cannot be drawn with stroke length). */
export function DrawDashedLine({
  id,
  points,
  className,
  strokeWidth,
  width,
  height,
  delay = 0.15,
}: {
  id: string;
  points: string;
  className: string;
  strokeWidth: number;
  width: number;
  height: number;
  delay?: number;
}) {
  const hidden = useContext(RevealState) === "hidden";
  return (
    <>
      <mask id={id} maskUnits="userSpaceOnUse" x={0} y={0} width={width} height={height}>
        <m.polyline
          points={points}
          pathLength={1}
          fill="none"
          stroke="white"
          strokeWidth={14}
          strokeLinejoin="round"
          initial={false}
          animate={draw(hidden, delay)}
        />
      </mask>
      <polyline
        points={points}
        fill="none"
        strokeWidth={strokeWidth}
        strokeDasharray="5 4"
        strokeLinecap="round"
        className={className}
        mask={`url(#${id})`}
      />
    </>
  );
}

/** A bar that drops in like a droplet and settles with a small bounce; `i` staggers the days. */
export function Drop({ children, i }: { children: ReactNode; i: number }) {
  const hidden = useContext(RevealState) === "hidden";
  return (
    <m.g
      initial={false}
      animate={
        hidden
          ? { y: -90, opacity: 0, transition: { duration: 0 } }
          : { y: 0, opacity: 1, transition: { type: "spring", stiffness: 240, damping: 13, delay: 0.45 + i * 0.09 } }
      }
    >
      {children}
    </m.g>
  );
}

/** A point that fades in just after the line reaches it. */
export function Fade({ children, i, count }: { children: ReactNode; i: number; count: number }) {
  const hidden = useContext(RevealState) === "hidden";
  return (
    <m.g
      initial={false}
      animate={
        hidden
          ? { opacity: 0, transition: { duration: 0 } }
          : { opacity: 1, transition: { duration: 0.35, delay: 0.3 + (1.2 * i) / Math.max(1, count - 1) } }
      }
    >
      {children}
    </m.g>
  );
}
