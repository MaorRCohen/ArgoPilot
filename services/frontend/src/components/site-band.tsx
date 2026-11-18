import Image from "next/image";
import Link from "next/link";
import type { ReactNode } from "react";
import { ViewTransition } from "react";
import { HeroMedia } from "@/components/motion/hero-media";
import { HOME_PHOTO, type Photo } from "@/lib/images";
import { cn } from "@/lib/utils";

/** A drop over two furrows: water and ground. */
function BrandMark() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 32 32"
      className="size-8 shrink-0"
      fill="none"
      strokeLinecap="round"
      strokeWidth="2.2"
    >
      <path
        d="M16 3.5c3.1 4 5.2 6.6 5.2 9.3a5.2 5.2 0 0 1-10.4 0c0-2.7 2.1-5.3 5.2-9.3z"
        className="fill-signal"
        stroke="none"
      />
      <path d="M3 21.5c4.3-3.6 8.7-3.6 13 0s8.7 3.6 13 0" className="stroke-straw" />
      <path d="M3 28c4.3-3.6 8.7-3.6 13 0s8.7 3.6 13 0" className="stroke-straw" opacity="0.55" />
    </svg>
  );
}

/** The soil edge: the page colour rises in a slow wave, so the hero does not end on a ruler line. */
function Edge() {
  return (
    <svg
      aria-hidden
      viewBox="0 0 1440 32"
      preserveAspectRatio="none"
      className="pointer-events-none absolute inset-x-0 bottom-0 z-[5] h-5 w-full fill-background sm:h-8"
    >
      <path d="M0 32V16C150 4 280 0 420 8s270 20 420 16 290-20 440-18c60 1 110 4 160 10V32z" />
    </svg>
  );
}

const SIZES = {
  // Full-bleed cinematic opening (home).
  tall: "min-h-[74svh] sm:min-h-[min(40rem,70svh)]",
  // Title + the first cards half on the photo (a plot page with a notice).
  medium: "min-h-[60svh] sm:min-h-[min(31rem,66svh)]",
  // Title + the answer and the gauge fully inside the photo (a plot page with a plan).
  stage: "min-h-[60svh] sm:min-h-[min(31rem,66svh)]",
  // Loading and similar short states.
  compact: "min-h-[16rem]",
  // The whole page is the hero (soil question, error): the card sits on the photo.
  scene: "min-h-[calc(100svh-4.5rem)] flex-1",
} as const;

export type BandSize = keyof typeof SIZES;

/**
 * The cinematic hero on top of every page: a full-bleed photo (parallax, slow push-in), a dark gradient so text stays
 * readable, drifting grid lines, a radar sweep, the brand, and the title block. `scene` also holds the page content.
 */
export function Band({
  children,
  size = "compact",
  photo = HOME_PHOTO,
  priority = true,
  transitionName,
}: {
  children?: ReactNode;
  size?: BandSize;
  photo?: Photo;
  priority?: boolean;
  /** Shared name for the photo morph from a plot card (see PlotCard). */
  transitionName?: string;
}) {
  const scene = size === "scene";
  const image = (
    <Image
      src={photo.img}
      alt=""
      fill
      priority={priority}
      sizes="100vw"
      placeholder="blur"
      className="object-cover"
      style={{ objectPosition: photo.position }}
    />
  );

  return (
    <section className={cn("on-dark relative isolate flex flex-col overflow-hidden bg-night", SIZES[size])}>
      <HeroMedia>
        {transitionName ? (
          <ViewTransition name={transitionName} share="morph" default="none">
            <div className="absolute inset-0">{image}</div>
          </ViewTransition>
        ) : (
          image
        )}
      </HeroMedia>
      <div aria-hidden className="hero-shade absolute inset-0 -z-20" />
      <div aria-hidden className="hero-grid-mask pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="hero-grid" />
      </div>
      <div aria-hidden className="hero-radar-wrap -z-10">
        <div className="hero-radar" />
      </div>

      <header className="mx-auto flex w-full max-w-[1200px] items-center px-4 pt-4 sm:px-6 sm:pt-6">
        <Link
          href="/"
          className="glass intro flex items-center gap-2.5 rounded-full py-2 pr-4 pl-3 outline-offset-2 transition-transform duration-150 ease-out active:scale-[0.97]"
        >
          <BrandMark />
          <span className="font-heading text-lg font-semibold tracking-wide">AgroPilot</span>
        </Link>
      </header>

      {children ? (
        <div
          className={cn(
            "mx-auto flex w-full max-w-[1200px] flex-1 flex-col px-4 sm:px-6",
            scene ? "justify-center py-8 sm:py-12" : "justify-end pt-10",
            size === "tall" && "pb-24 sm:pb-28",
            size === "medium" && "pb-44 sm:pb-56 lg:pb-64",
            size === "stage" && "pb-44 sm:pb-56 lg:pb-[33rem]",
          )}
        >
          {children}
        </div>
      ) : (
        <div className="h-16 sm:h-20" />
      )}
      {scene ? null : <Edge />}
    </section>
  );
}
