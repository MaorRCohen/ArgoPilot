import { PlanBar } from "@/components/plan-bar";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { dayMonth, formatLitres, formatRun, weekday } from "@/lib/format";
import type { PlanDay, PlanView } from "@/lib/planner";
import { cn } from "@/lib/utils";

function dayName(index: number, day: PlanDay): string {
  if (index === 0) return "Today";
  if (index === 1) return "Tomorrow";
  return weekday(day.date);
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-1.5">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-semibold">{value}</dd>
    </div>
  );
}

/** One row per day: what to do, the soil water bar, and the numbers behind it. */
export function PlanList({ plan }: { plan: PlanView }) {
  const triggerPct = 100 - plan.assumptions.irrigate_when_depleted_pct;
  return (
    <section aria-labelledby="week">
      <h2 id="week" className="font-heading text-2xl font-bold">
        Next {plan.days.length} days
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Bars show soil water at the end of each day. The mark at {triggerPct}% is where watering starts.
        {plan.totals.run_minutes > 0
          ? ` In total: ${formatLitres(plan.totals.litres)}, ${formatRun(plan.totals.run_minutes)} of running.`
          : ""}
      </p>

      <Card className="mt-4 gap-0 rounded-xl p-0 ring-1 ring-border">
        <ol className="divide-y divide-border">
          {plan.days.map((day, i) => {
            const watering = day.run_minutes > 0;
            const pct = Math.min(100, Math.max(0, day.soil_water_end_pct));
            const enough = pct >= triggerPct;
            return (
              <li key={day.date} className={cn("px-4 py-4 sm:px-5", i === 0 && "bg-water-tint/45")}>
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                  <p className="whitespace-nowrap">
                    <span className="font-heading text-lg font-bold">{dayName(i, day)}</span>{" "}
                    <span className="text-muted-foreground">{dayMonth(day.date)}</span>
                  </p>
                  <p className="ml-auto text-right whitespace-nowrap">
                    {watering ? (
                      <>
                        <span className="text-xl font-bold text-water-ink">{formatRun(day.run_minutes)}</span>{" "}
                        <span className="text-muted-foreground">{formatLitres(day.litres)}</span>
                      </>
                    ) : (
                      <span className="text-muted-foreground">No water</span>
                    )}
                  </p>
                </div>

                <div className="mt-2.5 flex items-center gap-3">
                  <PlanBar pct={pct} triggerPct={triggerPct} enough={enough} index={i} />
                  <span className="w-11 text-right text-sm font-bold">{Math.round(pct)}%</span>
                </div>

                <dl className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm">
                  <Stat label="ET0" value={`${day.et0_mm} mm`} />
                  <Stat label="Kc" value={`${day.kc}`} />
                  <Stat label="Need" value={`${day.need_mm} mm`} />
                  <Stat label="Rain" value={`${day.rain_mm} mm`} />
                  <Badge variant="secondary" className="h-6 rounded-md px-2 capitalize ring-1 ring-border">
                    {day.stage}
                  </Badge>
                  {day.stale ? (
                    <Badge variant="outline" className="h-6 rounded-md border-warn bg-warn-tint px-2 text-warn-ink">
                      Old forecast
                    </Badge>
                  ) : null}
                </dl>
              </li>
            );
          })}
        </ol>
      </Card>
    </section>
  );
}
