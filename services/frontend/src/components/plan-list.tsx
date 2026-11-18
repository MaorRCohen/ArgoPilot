import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { dayMonth, formatLitres, formatRun, weekday } from "@/lib/format";
import type { PlanDay, PlanView } from "@/lib/planner";

function dayName(index: number, day: PlanDay): string {
  if (index === 0) return "Today";
  if (index === 1) return "Tomorrow";
  return weekday(day.date);
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-1.5">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-bold">{value}</dd>
    </div>
  );
}

/** One row per day: what to do, the soil water bar, and the numbers behind it. */
export function PlanList({ plan }: { plan: PlanView }) {
  const triggerPct = 100 - plan.assumptions.irrigate_when_depleted_pct;
  return (
    <section aria-labelledby="week" className="mt-10">
      <h2 id="week" className="font-heading text-2xl font-bold tracking-tight">
        Next {plan.days.length} days
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Bars show soil water at the end of each day. The mark at {triggerPct}% is where watering starts.
        {plan.totals.run_minutes > 0
          ? ` In total: ${formatLitres(plan.totals.litres)}, ${formatRun(plan.totals.run_minutes)} of running.`
          : ""}
      </p>

      <ol className="mt-3 space-y-2">
        {plan.days.map((day, i) => {
          const watering = day.run_minutes > 0;
          const pct = Math.min(100, Math.max(0, day.soil_water_end_pct));
          return (
            <li key={day.date}>
              <Card className="gap-0 rounded-lg px-3 py-3 ring-1 ring-border">
              <div className="flex items-baseline justify-between gap-3">
                <p>
                  <span className="font-heading text-lg font-bold">{dayName(i, day)}</span>{" "}
                  <span className="text-muted-foreground">{dayMonth(day.date)}</span>
                </p>
                <p className="text-right">
                  {watering ? (
                    <>
                      <span className="font-heading text-lg font-bold text-water">{formatRun(day.run_minutes)}</span>{" "}
                      <span className="text-muted-foreground">{formatLitres(day.litres)}</span>
                    </>
                  ) : (
                    <span className="text-muted-foreground">No water</span>
                  )}
                </p>
              </div>

              <div className="mt-2 flex items-center gap-3">
                <div
                  role="img"
                  aria-label={`Soil water at the end of the day: ${Math.round(pct)}%`}
                  className="relative h-3 flex-1 overflow-hidden rounded-sm bg-muted"
                >
                  <div className="bar-fill h-full bg-water" style={{ width: `${pct}%`, animationDelay: `${i * 60}ms` }} />
                  <div className="absolute inset-y-0 w-0.5 bg-foreground" style={{ left: `${triggerPct}%` }} />
                </div>
                <span className="w-10 text-right text-sm font-bold">{Math.round(pct)}%</span>
              </div>

              <dl className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
                <Stat label="ET0" value={`${day.et0_mm} mm`} />
                <Stat label="Kc" value={`${day.kc}`} />
                <Stat label="Need" value={`${day.need_mm} mm`} />
                <Stat label="Rain" value={`${day.rain_mm} mm`} />
                <Badge variant="secondary" className="capitalize">
                  {day.stage}
                </Badge>
                {day.stale ? (
                  <Badge variant="outline" className="border-warn text-warn">
                    Old forecast
                  </Badge>
                ) : null}
              </dl>
              </Card>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
