import { SoilTank } from "@/components/soil-tank";
import { Tilt } from "@/components/motion/tilt";
import { Card } from "@/components/ui/card";
import type { PlanView } from "@/lib/planner";

/** The two numbers the gauge needs, or null: when one is missing the gauge is hidden, never guessed. */
function gaugeValues(plan: PlanView): { water: number; trigger: number } | null {
  const pct = plan.days[0]?.soil_water_end_pct;
  const trigger = plan.assumptions?.irrigate_when_depleted_pct;
  if (!Number.isFinite(pct) || !Number.isFinite(trigger)) return null;
  return { water: Math.min(100, Math.max(0, pct)), trigger };
}

/** Soil water at the end of today against the point where watering starts (30% of the water used). */
export function SoilGauge({ plan }: { plan: PlanView }) {
  const values = gaugeValues(plan);
  if (!values) return null;

  const { water, trigger } = values;
  const used = Math.round(100 - water);
  const pastTrigger = 100 - water >= trigger;

  return (
    <Tilt className="rounded-xl" max={3} lift={5}>
      <Card className="on-dark panel gap-0 rounded-xl p-5 shadow-float ring-0 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:gap-8 lg:flex-col lg:items-stretch lg:gap-5">
          <SoilTank
            water={water}
            trigger={trigger}
            label={`Soil water at the end of today: ${Math.round(water)}%. ${used}% of the water is used; watering starts at ${trigger}% used.`}
          />
          <div className="min-w-0">
            <h2 className="font-heading text-xl font-bold">Soil water</h2>
            <p className="mt-1 text-muted-foreground">
              {pastTrigger
                ? `${used}% used, past the ${trigger}% where watering starts.`
                : `${used}% used. Watering starts at ${trigger}%.`}
            </p>
            <ul className="mt-3 space-y-1.5 text-sm">
              <li className="flex items-center gap-2">
                <span aria-hidden className="h-1.5 w-6 rounded-full bg-leaf" />
                Enough water
              </li>
              <li className="flex items-center gap-2">
                <span aria-hidden className="h-1.5 w-6 rounded-full bg-water" />
                Time to water
              </li>
            </ul>
          </div>
        </div>
      </Card>
    </Tilt>
  );
}
