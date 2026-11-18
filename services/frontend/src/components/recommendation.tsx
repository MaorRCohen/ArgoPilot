import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card } from "@/components/ui/card";
import { dayMonth, formatAge, formatLitres, formatRun, weekday } from "@/lib/format";
import type { PlanView } from "@/lib/planner";

const OLD_FORECAST_HOURS = 6;

/** Today's answer, first and big. The blue fill is the soil water level at the end of today. */
export function Recommendation({ plan }: { plan: PlanView }) {
  const today = plan.days[0];
  const { irrigate, run_minutes } = plan.today;
  const age = formatAge(plan.forecast_age_min);
  const veryOld = today.stale && plan.forecast_age_min > OLD_FORECAST_HOURS * 60;
  // SEASON_ENDED is shown by the page (before the plan); STALE_FORECAST is the block below.
  const other = plan.warnings.filter((w) => w.code !== "STALE_FORECAST" && w.code !== "SEASON_ENDED");

  return (
    <section aria-labelledby="today">
      <Card className="relative min-h-52 gap-0 rounded-lg py-0 ring-1 ring-border">
        <div
          aria-hidden
          className="level-rise absolute inset-x-0 bottom-0 bg-water-tint"
          style={{ height: `${Math.min(100, today.soil_water_end_pct)}%` }}
        />
        <div className="relative flex min-h-52 flex-col justify-between gap-6 p-4">
          <p className="text-muted-foreground">
            Today, {weekday(plan.today.date)} {dayMonth(plan.today.date)}
          </p>
          <div>
            <h1 id="today" className="font-heading text-5xl leading-[1.02] font-extrabold tracking-tight text-balance">
              {irrigate ? `Water for ${formatRun(run_minutes)}` : "No irrigation today"}
            </h1>
            <p className="mt-2 text-lg">
              {irrigate
                ? `${formatLitres(today.litres)} through the drip lines`
                : "The soil still holds enough water."}
            </p>
          </div>
          <p className="text-sm">
            <span className="font-bold">{plan.plot_name}</span>, soil water at the end of today:{" "}
            <span className="font-bold">{Math.round(today.soil_water_end_pct)}%</span>
            {today.stale ? <span className="font-bold text-warn"> (old forecast)</span> : null}
          </p>
        </div>
      </Card>

      {other.map((w, i) => (
        <Alert key={`${w.code}-${i}`} className="mt-3 border-warn/50 bg-warn-tint text-foreground">
          {w.code === "IRRIGATION_CAPPED" ? (
            <AlertTitle className="font-heading text-base font-bold text-warn">A full refill takes more than a day</AlertTitle>
          ) : null}
          <AlertDescription className="text-sm text-foreground">{w.message}</AlertDescription>
        </Alert>
      ))}

      {today.stale ? (
        <Alert
          className={`mt-3 text-foreground ${veryOld ? "border-2 border-warn bg-warn-tint" : "border-warn/50 bg-warn-tint"}`}
        >
          <AlertTitle className="font-heading text-base font-bold text-warn">
            {veryOld ? `The forecast is more than ${OLD_FORECAST_HOURS} hours old` : "The forecast is out of date"}
          </AlertTitle>
          <AlertDescription className="text-sm text-foreground">
            The weather provider did not answer, so this plan uses the last forecast we had, fetched {age}.
            {veryOld ? " Treat these numbers with care and check the field yourself." : " Reload in a few minutes for a fresh one."}
          </AlertDescription>
        </Alert>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">Forecast fetched {age}.</p>
      )}

    </section>
  );
}
