"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { rememberPlot } from "./last-plot";

/** A plain link to a plot that remembers which plot it was, so the loading scene can use the same photo. */
export function PlotLink({ plotId, className, children }: { plotId: string; className?: string; children: ReactNode }) {
  return (
    <Link href={`/plots/${plotId}`} className={className} onClick={() => rememberPlot(plotId)}>
      {children}
    </Link>
  );
}
