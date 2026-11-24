import { SoilTank } from "@/components/soil-tank";
import { Tilt } from "@/components/motion/tilt";
import { Card } from "@/components/ui/card";
import type { PlanView } from "@/lib/planner";

/** The water left after today's watering, or null: when it is missing the gauge is hidden, never guessed. */
function gaugeWater(plan: PlanView): number | null {
  const pct = plan.days[0]?.soil_water_end_pct;
  if (!Number.isFinite(pct)) return null;
  return Math.min(100, Math.max(0, pct));
}

/** Soil water at the end of today, after watering. It is not compared with the watering trigger. */
export function SoilGauge({ plan }: { plan: PlanView }) {
  const water = gaugeWater(plan);
  if (water === null) return null;

  const used = Math.round(100 - water);

  return (
    <Tilt className="rounded-xl" max={3} lift={5}>
      <Card className="on-dark panel gap-0 rounded-xl p-5 shadow-float ring-0 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-8 lg:flex-col lg:items-stretch lg:gap-5">
          <SoilTank
            water={water}
            label={`Soil water after today's watering: ${Math.round(water)}% left, ${used}% used.`}
          />
          <div className="min-w-0">
            <h2 className="font-heading text-xl font-bold">Soil water after today&apos;s watering</h2>
            <p className="mt-1 text-muted-foreground">
              {Math.round(water)}% left, {used}% used.
            </p>
            <ul className="mt-3 space-y-1.5 text-sm">
              <li className="flex items-center gap-2">
                <span aria-hidden className="h-1.5 w-6 rounded-full bg-leaf" />
                Water left in the soil
              </li>
            </ul>
          </div>
        </div>
      </Card>
    </Tilt>
  );
}
