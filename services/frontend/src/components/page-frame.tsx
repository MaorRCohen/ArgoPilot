import type { ReactNode } from "react";
import { Band, type BandSize } from "@/components/site-band";
import type { Photo } from "@/lib/images";
import { HOME_PHOTO } from "@/lib/images";
import { cn } from "@/lib/utils";

/**
 * Every page: the cinematic hero on top, then the paper content. The first cards sit half on the hero
 * (the hero's bottom padding is larger than the overlap, so the title never touches a card).
 * With `scene` the whole page is the hero and the content sits on the photo.
 */
export function PageFrame({
  band,
  children,
  size = "compact",
  photo = HOME_PHOTO,
  scene = false,
  transitionName,
}: {
  band?: ReactNode;
  children: ReactNode;
  size?: Exclude<BandSize, "scene">;
  photo?: Photo;
  scene?: boolean;
  transitionName?: string;
}) {
  if (scene) {
    return (
      <Band size="scene" photo={photo} transitionName={transitionName}>
        {band}
        <div className={cn("w-full", band && "mt-8 sm:mt-10")}>{children}</div>
      </Band>
    );
  }
  return (
    <>
      <Band size={size} photo={photo} transitionName={transitionName}>
        {band}
      </Band>
      <main
        className={cn(
          "relative z-10 mx-auto w-full max-w-[1200px] px-4 pb-16 sm:px-6",
          size === "tall" && "pt-8 sm:pt-10",
          size === "medium" && "-mt-36 sm:-mt-48 lg:-mt-56",
          size === "stage" && "-mt-36 sm:-mt-48 lg:-mt-[30rem]",
          size === "compact" && "-mt-6 sm:-mt-8",
        )}
      >
        {children}
      </main>
    </>
  );
}
