"use client";

import { useRef, useSyncExternalStore, type ReactNode } from "react";
import { m, useMotionValue, useReducedMotion, useSpring, useTransform } from "motion/react";

const FINE = "(hover: hover) and (pointer: fine)";
function subscribeFine(onChange: () => void) {
  const query = window.matchMedia(FINE);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

/**
 * A card that leans toward the cursor on a spring, lifts and glows on hover, and shrinks a little when pressed.
 * Tilt, lift and glow only run with a real mouse ((hover: hover) and (pointer: fine)) and never with reduced motion;
 * the press feedback works for touch too. Everything is transform or opacity.
 */
export function Tilt({
  children,
  className,
  max = 5,
  lift = 8,
}: {
  children: ReactNode;
  /** Set the corner radius here (for example "rounded-[1.75rem]"): the glow and the glare copy it. */
  className?: string;
  /** Largest tilt in degrees. */
  max?: number;
  /** Hover lift in px. */
  lift?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const fine = useSyncExternalStore(
    subscribeFine,
    () => window.matchMedia(FINE).matches,
    () => false,
  );
  const enabled = fine && !reduce;

  const px = useMotionValue(0.5);
  const py = useMotionValue(0.5);
  const spring = { stiffness: 220, damping: 20, mass: 0.7 };
  const rotateY = useSpring(useTransform(px, [0, 1], [-max, max]), spring);
  const rotateX = useSpring(useTransform(py, [0, 1], [max, -max]), spring);
  const glow = useSpring(0, { stiffness: 200, damping: 26 });
  const glareX = useSpring(useTransform(px, [0, 1], ["-22%", "22%"]), spring);
  const glareY = useSpring(useTransform(py, [0, 1], ["-22%", "22%"]), spring);
  const glareOpacity = useTransform(glow, (v) => v * 0.55);

  function onPointerMove(event: React.PointerEvent) {
    if (!enabled || event.pointerType !== "mouse" || !ref.current) return;
    const box = ref.current.getBoundingClientRect();
    px.set((event.clientX - box.left) / box.width);
    py.set((event.clientY - box.top) / box.height);
    glow.set(1);
  }
  function onPointerLeave() {
    px.set(0.5);
    py.set(0.5);
    glow.set(0);
  }

  return (
    <m.div
      ref={ref}
      className={`relative ${className ?? ""}`}
      style={{ rotateX, rotateY, transformPerspective: 1100 }}
      whileHover={enabled ? { y: -lift } : undefined}
      whileTap={{ scale: 0.985 }}
      transition={{ type: "spring", stiffness: 380, damping: 26 }}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
    >
      {children}
      <m.span
        aria-hidden
        className="pointer-events-none absolute inset-0 rounded-[inherit] shadow-glow"
        style={{ opacity: glow }}
      />
      <span aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden rounded-[inherit]">
        <m.span
          className="absolute -inset-1/2 bg-[radial-gradient(closest-side,rgb(255_255_255/0.5),transparent)]"
          style={{ x: glareX, y: glareY, opacity: glareOpacity }}
        />
      </span>
    </m.div>
  );
}
