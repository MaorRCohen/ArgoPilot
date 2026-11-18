import { Suspense } from "react";
import { PlanList } from "@/components/plan-list";
import { Problem } from "@/components/problem";
import { Recommendation } from "@/components/recommendation";
import { SoilQuestion } from "@/components/soil-question";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { getPlan } from "@/lib/planner";

/** The grower's own reading (0-10), or null when it is missing or invalid. There is no default: the planner never guesses. */
function parseSoilMoisture(raw: string | string[] | undefined): number | null {
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (value && /^\d+$/.test(value) && Number(value) <= 10) return Number(value);
  return null;
}

export default function PlotPage({ params, searchParams }: PageProps<"/plots/[id]">) {
  return (
    <Suspense fallback={<p role="status" className="text-lg text-muted-foreground">Loading plan…</p>}>
      <PlotPlan params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function PlotPlan({
  params,
  searchParams,
}: {
  params: PageProps<"/plots/[id]">["params"];
  searchParams: PageProps<"/plots/[id]">["searchParams"];
}) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const soilMoisture = parseSoilMoisture(query.soil_moisture);
  if (soilMoisture === null) return <SoilQuestion />;
  const result = await getPlan(id, soilMoisture);

  if (!result.ok) {
    return <Problem error={result.error} what="irrigation plan" retryHref={`/plots/${id}?soil_moisture=${soilMoisture}`} />;
  }

  const plan = result.data;
  const seasonEnded = plan.warnings.find((w) => w.code === "SEASON_ENDED");
  const content = (
    <>
      <Recommendation plan={plan} />

      <form method="get" className="mt-6">
        <label htmlFor="soil_moisture" className="font-bold">
          Soil moisture today
        </label>
        <p className="text-sm text-muted-foreground">Your own reading: 0 is dry or just planted, 10 is full.</p>
        <div className="mt-2 flex gap-2">
          <select
            id="soil_moisture"
            name="soil_moisture"
            defaultValue={String(soilMoisture)}
            className="h-11 min-w-0 flex-1 rounded-md border border-input bg-card px-3"
          >
            {Array.from({ length: 11 }, (_, n) => (
              <option key={n} value={n}>
                {n === 0 ? "0 (dry)" : n === 10 ? "10 (full)" : n}
              </option>
            ))}
          </select>
          <Button type="submit" size="lg" className="h-11 px-4">
            Update plan
          </Button>
        </div>
      </form>

      <PlanList plan={plan} />
    </>
  );

  if (!seasonEnded) return content;

  // The plan is already loaded: <details> only reveals it, no second request.
  return (
    <>
      <Alert className="border-2 border-warn bg-warn-tint text-foreground">
        <AlertTitle className="font-heading text-lg font-bold text-warn">This crop&apos;s usual season is over</AlertTitle>
        <AlertDescription className="text-base text-foreground">{seasonEnded.message}</AlertDescription>
      </Alert>
      <details className="mt-4">
        <summary className="flex min-h-11 cursor-pointer items-center font-bold underline underline-offset-4 outline-offset-2 focus-visible:outline-2 focus-visible:outline-ring">
          Show the plan anyway
        </summary>
        <div className="mt-4">{content}</div>
      </details>
    </>
  );
}
