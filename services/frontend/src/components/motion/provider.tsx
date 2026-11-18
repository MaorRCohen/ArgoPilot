"use client";

import type { ReactNode } from "react";
import { LazyMotion, MotionConfig } from "motion/react";

const loadFeatures = () => import("./features").then((module) => module.default);

/**
 * One provider for the whole app: the `m` components stay small (the features load after first paint), and
 * `reducedMotion="user"` makes Motion skip transform animations when the visitor asks for less motion.
 */
export function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      <LazyMotion features={loadFeatures} strict>
        {children}
      </LazyMotion>
    </MotionConfig>
  );
}
