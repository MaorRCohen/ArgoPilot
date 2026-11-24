"use client";

import { useEffect, useRef, type ReactNode } from "react";

/** How far the photo layer sits lower when the hero has fully scrolled away, in % of the layer's own height. */
const PARALLAX = 12;
const MOTION_OK = "(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)";

/**
 * The hero photo: it scrolls slower than the page (parallax) and slowly pushes in (Ken Burns, CSS). The layer is taller
 * than the hero so the parallax never shows an edge. `children` is the next/image, rendered on the server.
 * The parallax is a plain passive scroll listener (no animation library) and only runs with a real mouse and when motion
 * is allowed: on phones and with reduced motion the photo stays put and scrolling costs nothing.
 */
export function HeroMedia({ children }: { children: ReactNode }) {
  const frame = useRef<HTMLDivElement>(null);
  const layer = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const hero = frame.current;
    const el = layer.current;
    if (!hero || !el) return;
    const query = window.matchMedia(MOTION_OK);
    let raf = 0;
    let last = -1;

    const update = () => {
      raf = 0;
      const box = hero.getBoundingClientRect();
      const progress = Math.min(1, Math.max(0, -box.top / box.height));
      if (progress === last) return;
      last = progress;
      el.style.transform = `translate3d(0, ${(progress * PARALLAX).toFixed(2)}%, 0)`;
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(update);
    };
    const start = () => {
      el.style.willChange = "transform";
      window.addEventListener("scroll", onScroll, { passive: true });
      update();
    };
    const stop = () => {
      window.removeEventListener("scroll", onScroll);
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
      last = -1;
      el.style.transform = "";
      el.style.willChange = "";
    };
    const sync = () => {
      stop();
      if (query.matches) start();
    };

    sync();
    query.addEventListener("change", sync);
    return () => {
      query.removeEventListener("change", sync);
      stop();
    };
  }, []);

  return (
    <div ref={frame} className="absolute inset-0 -z-30 overflow-hidden">
      <div ref={layer} className="absolute inset-x-0 -top-[18%] -bottom-[18%]">
        <div className="kenburns absolute inset-0">{children}</div>
      </div>
    </div>
  );
}
