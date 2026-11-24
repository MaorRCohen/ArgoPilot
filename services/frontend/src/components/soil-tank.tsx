"use client";

import { useRef } from "react";
import { m } from "motion/react";
import { CountUp } from "@/components/motion/count-up";
import { useReveal } from "@/components/motion/use-reveal";

// Geometry of the tank (SVG units). The wavelength equals the tank width: globals.css moves the waves by exactly one
// wavelength (-236px) per loop, so the loop is seamless.
const W = 340;
const H = 190;
const TX = 84; // tank left
const TY = 14; // tank top
const TW = 236; // tank width = one wavelength
const TH = 140; // tank height
const RX = 26;
const BOTTOM = TY + TH;
const AMP = 5;

/** One sine wave, three wavelengths wide, as a path; `phase` shifts it so two layers never line up. */
function wave(phase: number, closed: boolean): string {
  const pts: string[] = [];
  for (let x = 0; x <= TW * 3; x += 8) {
    const y = AMP * Math.sin((2 * Math.PI * x) / TW + phase);
    pts.push(`${x} ${y.toFixed(2)}`);
  }
  const top = `M${pts.join("L")}`;
  return closed ? `${top}L${TW * 3} ${TH + 30}L0 ${TH + 30}Z` : top;
}
const WAVE_A = { fill: wave(0, true), crest: wave(0, false) };
const WAVE_B = { fill: wave(2.2, true), crest: wave(2.2, false) };

/**
 * Soil water as a tank of liquid: the level is the percentage, the surface moves in two slow waves, and the level
 * rises on a spring when the card scrolls into view. The liquid is always leaf green: it shows the water left, and it is
 * not compared with the watering trigger.
 */
export function SoilTank({ water, label }: { water: number; label: string }) {
  const ref = useRef<SVGSVGElement>(null);
  const state = useReveal(ref, "0px 0px -5% 0px");
  const hidden = state === "hidden";

  const levelY = BOTTOM - (TH * water) / 100;

  return (
    <svg
      ref={ref}
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={label}
      className="mx-auto h-auto w-full max-w-[340px] shrink-0"
    >
      <defs>
        <clipPath id="tank-clip">
          <rect x={TX} y={TY} width={TW} height={TH} rx={RX} />
        </clipPath>
      </defs>

      <rect x={TX} y={TY} width={TW} height={TH} rx={RX} className="fill-muted" />

      {/* the liquid: the group sits at its final level; the spring only moves it up from below the floor */}
      <g clipPath="url(#tank-clip)">
        <g transform={`translate(${TX} ${levelY})`}>
          <m.g
            initial={false}
            animate={
              hidden
                ? { y: TH + 24, transition: { duration: 0 } }
                : { y: 0, transition: { type: "spring", duration: 1.2, bounce: 0.2, delay: 0.4 } }
            }
          >
            <g className="wave-slow fill-leaf" opacity="0.16">
              <path d={WAVE_B.fill} />
            </g>
            <g className="wave">
              <path d={WAVE_A.fill} className="fill-leaf" opacity="0.24" />
              <path d={WAVE_A.crest} fill="none" strokeWidth="2.5" strokeLinecap="round" className="stroke-leaf" />
            </g>
          </m.g>
        </g>
      </g>

      <rect x={TX} y={TY} width={TW} height={TH} rx={RX} fill="none" strokeWidth="2" className="stroke-input" />

      {/* a dark window behind the number: the moving surface of the liquid can never run through the digits */}
      <rect
        x={TX + TW / 2 - 78}
        y={TY + TH - 84}
        width={156}
        height={76}
        rx={14}
        className="fill-card"
        opacity="0.78"
      />
      <text
        x={TX + TW / 2}
        y={TY + TH - 36}
        textAnchor="middle"
        fontSize="58"
        fontWeight="700"
        letterSpacing="-2"
        className="fill-foreground"
      >
        <CountUp as="tspan" value={Math.round(water)} duration={1.1} delay={0.4} />%
      </text>
      <text x={TX + TW / 2} y={TY + TH - 12} textAnchor="middle" fontSize="15" className="fill-foreground">
        soil water left
      </text>
      <text x={TX - 12} y={BOTTOM} textAnchor="end" fontSize="12.5" className="fill-muted-foreground">
        0%
      </text>
      <text x={TX - 12} y={TY + 9} textAnchor="end" fontSize="12.5" className="fill-muted-foreground">
        100%
      </text>
      <title>{`${Math.round(water)}% soil water left after today's watering`}</title>
    </svg>
  );
}
