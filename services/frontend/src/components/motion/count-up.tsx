"use client";

import { useEffect, useRef } from "react";
import { animate, useMotionValue, useReducedMotion } from "motion/react";
import { EASE_OUT, useReveal } from "./use-reveal";

const fractionDigits = (n: number): number => Math.min(3, (String(n).split(".")[1] ?? "").length);

/**
 * A number that counts up to its real value. The server HTML (and reduced motion) already show the final number,
 * formatted exactly like the rest of the page, so the animation never changes what is true.
 */
export function CountUp({
  value,
  group = false,
  delay = 0.25,
  duration = 1,
  as: Tag = "span",
}: {
  value: number;
  /** Thousands separators ("1,234"), as `toLocaleString("en-US")` does. */
  group?: boolean;
  delay?: number;
  duration?: number;
  as?: "span" | "tspan";
}) {
  const ref = useRef<HTMLElement | SVGTSpanElement | null>(null);
  const state = useReveal(ref);
  const reduce = useReducedMotion();
  const digits = fractionDigits(value);
  const final = group ? value.toLocaleString("en-US") : String(value);
  const played = useRef(false);
  const count = useMotionValue(0);

  useEffect(() => {
    const el = ref.current;
    if (!el || reduce) return;
    // One formatter per run: building one on every animation frame was the biggest app-level cost in the load profile.
    const format = new Intl.NumberFormat("en-US", {
      useGrouping: group,
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
    const frame = (n: number) => format.format(n);
    if (state === "hidden") {
      el.textContent = frame(0);
      played.current = false;
      return;
    }
    if (state !== "shown" || played.current) return;
    played.current = true;
    count.set(0);
    const stop = count.on("change", (n) => {
      el.textContent = frame(n);
    });
    const controls = animate(count, value, {
      duration,
      delay,
      ease: EASE_OUT,
      onComplete: () => {
        el.textContent = final;
      },
    });
    return () => {
      controls.stop();
      stop();
      played.current = false;
      el.textContent = final;
    };
  }, [state, reduce, value, group, digits, delay, duration, final, count]);

  return Tag === "tspan" ? (
    <tspan ref={ref as React.Ref<SVGTSpanElement>}>{final}</tspan>
  ) : (
    <span ref={ref as React.Ref<HTMLSpanElement>}>{final}</span>
  );
}
