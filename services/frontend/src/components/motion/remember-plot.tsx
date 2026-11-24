"use client";

import { useEffect } from "react";
import { rememberPlot } from "./last-plot";

/** Rendered on a plot page: keeps "the last plot" right even when the page was not opened from a card. */
export function RememberPlot({ id }: { id: string }) {
  useEffect(() => {
    rememberPlot(id);
  }, [id]);
  return null;
}
