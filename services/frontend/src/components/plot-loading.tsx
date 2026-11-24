"use client";

import { PageFrame } from "@/components/page-frame";
import { recallPlot } from "@/components/motion/last-plot";
import { HOME_PHOTO, photoFor } from "@/lib/images";

/**
 * The loading scene of a plot page. When the visitor came from a plot card it shows that plot's photo under the same
 * view-transition name, so the card's photo grows into this scene and then into the plot hero without a jump.
 */
export function PlotLoading() {
  const id = recallPlot();
  return (
    <PageFrame scene photo={id ? photoFor(id) : HOME_PHOTO} transitionName={id ? `plot-photo-${id}` : undefined}>
      <p
        role="status"
        className="on-dark panel max-w-md rounded-[1.75rem] p-8 text-lg text-muted-foreground shadow-float"
      >
        Loading plan…
      </p>
    </PageFrame>
  );
}
