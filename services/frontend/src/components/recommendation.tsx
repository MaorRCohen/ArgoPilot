import { Check, Clock, Droplets, TriangleAlert } from "lucide-react";
import { CountUp } from "@/components/motion/count-up";
import { Tilt } from "@/components/motion/tilt";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { dayMonth, formatAge, runParts, weekday } from "@/lib/format";
import { furrowPaths } from "@/lib/furrows";
import type { PlanView } from "@/lib/planner";
import { cn } from "@/lib/utils";

const OLD_FORECAST_HOURS = 6;

// Computed once: decoration for the answer card.
const CARD_LINES = furrowPaths({
  width: 400,
  height: 300,
  lines: 14,
  seed: 1.7,
  hill: { x: 0.72, y: 0.35, lift: 44 },
});

/** Today's answer, first and big: the key number (minutes of running) is the largest thing on the page. */
export function Recommendation({ plan }: { plan: PlanView }) {
  const today = plan.days[0];
  const { irrigate, run_minutes } = plan.today;
  const age = formatAge(plan.forecast_age_min);
  const veryOld = today.stale && plan.forecast_age_min > OLD_FORECAST_HOURS * 60;
  // SEASON_ENDED is shown by the page (before the plan); STALE_FORECAST is the block below.
  const other = plan.warnings.filter((w) => w.code !== "STALE_FORECAST" && w.code !== "SEASON_ENDED");
  const parts = runParts(run_minutes);
  const pct = Number.isFinite(today.soil_water_end_pct) ? Math.round(today.soil_water_end_pct) : null;

  return (
    <section aria-labelledby="today">
      <div className="intro" style={{ "--i": 4 } as React.CSSProperties}>
        <Tilt className="rounded-[1.75rem]" max={2.5} lift={6}>
          <Card className="on-dark panel relative gap-0 rounded-[1.75rem] p-0 shadow-float ring-0">
            {/* The same furrows as the band, in the colour of the answer (water blue / leaf green), fading out to the left. */}
            <svg
              aria-hidden
              viewBox="0 0 400 300"
              preserveAspectRatio="xMaxYMid slice"
              className={cn(
                "pointer-events-none absolute inset-y-0 right-0 h-full w-3/5 [mask-image:linear-gradient(to_left,black_15%,transparent_95%)]",
                irrigate ? "text-water" : "text-leaf",
              )}
            >
              <g fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.3">
                {CARD_LINES.map((d, i) => (
                  <path key={i} d={d} />
                ))}
              </g>
            </svg>

            <div className="relative p-6 sm:p-9">
              <div className="flex items-start justify-between gap-4">
                <p className="pt-1 text-muted-foreground">
                  Today, {weekday(plan.today.date)} {dayMonth(plan.today.date)}
                </p>
                <div
                  aria-hidden
                  className={cn(
                    "grid size-12 shrink-0 place-items-center rounded-full sm:size-14",
                    irrigate ? "bg-water-tint text-water-ink" : "bg-leaf-tint text-leaf-ink",
                  )}
                >
                  {irrigate ? (
                    <Droplets className="size-6 sm:size-7" />
                  ) : (
                    <Check className="size-6 sm:size-7" strokeWidth={2.6} />
                  )}
                </div>
              </div>

              {irrigate ? (
                <h1 id="today" className="mt-3 flex flex-col">
                  <span className="font-heading text-3xl leading-none font-bold sm:text-4xl">Water for</span>{" "}
                  <span
                    className={cn(
                      "mt-2 flex flex-wrap items-baseline gap-x-[0.18em] font-bold text-foreground",
                      parts.length === 1 ? "text-hero" : "text-hero-2",
                    )}
                  >
                    {parts.map((p, i) => (
                      <span key={p.unit} className="whitespace-nowrap">
                        {i > 0 ? " " : null}
                        <CountUp value={Number(p.value)} />
                        <span className="ml-[0.1em] text-[0.28em] font-semibold tracking-normal"> {p.unit}</span>
                      </span>
                    ))}
                  </span>
                </h1>
              ) : (
                <h1 id="today" className="mt-3 max-w-[11ch] font-heading text-display font-extrabold text-balance">
                  No irrigation today
                </h1>
              )}

              <p className="mt-5 text-xl leading-snug sm:text-2xl">
                {irrigate ? (
                  <>
                    <span className="font-bold">
                      <CountUp value={today.litres} group delay={0.4} /> L
                    </span>{" "}
                    through the drip lines
                  </>
                ) : (
                  "The soil still holds enough water."
                )}
              </p>
            </div>

            <div className="relative flex flex-wrap items-center gap-x-2 border-t border-border bg-muted px-6 py-3.5 text-sm sm:px-9">
              {pct !== null ? (
                <p>
                  Soil water at the end of today:{" "}
                  <span className="font-bold">
                    <CountUp value={pct} delay={0.45} />%
                  </span>
                  {today.stale ? <span className="font-bold text-warn-ink"> (old forecast)</span> : null}
                </p>
              ) : today.stale ? (
                <p className="font-bold text-warn-ink">Old forecast</p>
              ) : null}
              {today.stale ? null : (
                <p className="flex items-center gap-1.5 text-muted-foreground sm:ml-auto">
                  <Clock className="size-4" aria-hidden />
                  Forecast fetched {age}.
                </p>
              )}
            </div>
          </Card>
        </Tilt>
      </div>

      <div className="mt-4 space-y-3">
        {other.map((w, i) => (
          <Alert
            key={`${w.code}-${i}`}
            className="gap-y-1 rounded-xl border-warn/60 bg-warn-tint px-4 py-3.5 text-warn-ink"
          >
            <TriangleAlert className="size-5" aria-hidden />
            {w.code === "IRRIGATION_CAPPED" ? (
              <AlertTitle className="font-heading text-lg font-bold text-warn-ink">
                A full refill takes more than a day
              </AlertTitle>
            ) : null}
            <AlertDescription className="text-base text-foreground">{w.message}</AlertDescription>
          </Alert>
        ))}

        {today.stale ? (
          <Alert
            className={cn(
              "gap-y-1 rounded-xl px-4 py-3.5 text-warn-ink",
              veryOld ? "border-2 border-warn bg-warn-tint" : "border-warn/60 bg-warn-tint",
            )}
          >
            <TriangleAlert className="size-5" aria-hidden />
            <AlertTitle className="font-heading text-lg font-bold text-warn-ink">
              {veryOld ? `The forecast is more than ${OLD_FORECAST_HOURS} hours old` : "The forecast is out of date"}
            </AlertTitle>
            <AlertDescription className="text-base text-foreground">
              The weather provider did not answer, so this plan uses the last forecast we had, fetched {age}.
              {veryOld
                ? " Treat these numbers with care and check the field yourself."
                : " Reload in a few minutes for a fresh one."}
            </AlertDescription>
          </Alert>
        ) : null}
      </div>
    </section>
  );
}
