import { Suspense } from "react";
import { ChevronDown, Sprout, TriangleAlert } from "lucide-react";
import { PageFrame } from "@/components/page-frame";
import { PlanList } from "@/components/plan-list";
import { PlotLoading } from "@/components/plot-loading";
import { Problem } from "@/components/problem";
import { Recommendation } from "@/components/recommendation";
import { SoilForm } from "@/components/soil-form";
import { SoilGauge } from "@/components/soil-gauge";
import { SoilQuestion } from "@/components/soil-question";
import { WeekChart } from "@/components/week-chart";
import { RememberPlot } from "@/components/motion/remember-plot";
import { Reveal } from "@/components/motion/reveal";
import { SplitTitle } from "@/components/split-title";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { labelFromId } from "@/lib/format";
import { photoFor } from "@/lib/images";
import { getPlan } from "@/lib/planner";
import { cn } from "@/lib/utils";

/** The grower's own reading (0-10), or null when it is missing or invalid. There is no default: the planner never guesses. */
function parseSoilMoisture(raw: string | string[] | undefined): number | null {
  const value = Array.isArray(raw) ? raw[0] : raw;
  if (value && /^\d+$/.test(value) && Number(value) <= 10) return Number(value);
  return null;
}

export default function PlotPage({ params, searchParams }: PageProps<"/plots/[id]">) {
  return (
    <Suspense fallback={<PlotLoading />}>
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
  const photo = photoFor(id);
  const transitionName = `plot-photo-${id}`;
  if (soilMoisture === null) {
    return (
      <>
        <RememberPlot id={id} />
        <SoilQuestion photo={photo} transitionName={transitionName} />
      </>
    );
  }
  const result = await getPlan(id, soilMoisture);

  if (!result.ok) {
    return (
      <>
        <RememberPlot id={id} />
        <PageFrame scene photo={photo} transitionName={transitionName}>
          <Problem
            error={result.error}
            what="irrigation plan"
            retryHref={`/plots/${id}?soil_moisture=${soilMoisture}`}
          />
        </PageFrame>
      </>
    );
  }

  const plan = result.data;
  const seasonEnded = plan.warnings.find((w) => w.code === "SEASON_ENDED");

  const band = (
    <>
      <p className="font-heading text-[clamp(1.875rem,6vw,4.25rem)] leading-[1.04] font-bold tracking-[0.04em] text-balance uppercase [overflow-wrap:anywhere]">
        <SplitTitle text={plan.plot_name} />
      </p>
      <p
        className="intro mt-4 flex items-center gap-2 text-lg text-foreground"
        style={{ "--i": 5 } as React.CSSProperties}
      >
        <Sprout aria-hidden className="size-5 text-signal" />
        {labelFromId(plan.crop)}
      </p>
    </>
  );

  // Wide screens: the answer and the gauge float on the photo, the chart below the answer, the controls and the day list on the right.
  // The DOM order is the reading order on a phone: answer, gauge, chart, soil form, day list.
  const content = (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:items-start lg:gap-x-8">
      <div className="lg:col-start-1 lg:row-start-1">
        <Recommendation plan={plan} />
      </div>
      <div className="intro lg:col-start-2 lg:row-start-1" style={{ "--i": 6 } as React.CSSProperties}>
        <SoilGauge plan={plan} />
      </div>
      <Reveal className="lg:col-start-1 lg:row-span-2 lg:row-start-2">
        <WeekChart plan={plan} />
      </Reveal>
      <Reveal className="lg:col-start-2 lg:row-start-2">
        <SoilForm value={soilMoisture} />
      </Reveal>
      <Reveal className="lg:col-start-2 lg:row-start-3">
        <PlanList plan={plan} />
      </Reveal>
    </div>
  );

  if (!seasonEnded) {
    return (
      <>
        <RememberPlot id={id} />
        <PageFrame size="stage" photo={photo} transitionName={transitionName} band={band}>
          {content}
        </PageFrame>
      </>
    );
  }

  // The plan is already loaded: <details> only reveals it, no second request.
  return (
    <>
      <RememberPlot id={id} />
      <PageFrame size="medium" photo={photo} transitionName={transitionName} band={band}>
        <Alert className="gap-y-1.5 rounded-2xl border-2 border-warn bg-warn-tint px-4 py-4 text-warn-ink shadow-hero sm:px-8 sm:py-7">
          <TriangleAlert className="size-7" aria-hidden />
          <AlertTitle className="font-heading text-xl font-bold text-warn-ink sm:text-3xl">
            This crop&apos;s usual season is over
          </AlertTitle>
          <AlertDescription className="text-base text-foreground sm:text-lg">{seasonEnded.message}</AlertDescription>
        </Alert>
        <details className="group mt-4 sm:mt-5">
          <summary
            className={cn(
              buttonVariants({ variant: "outline", size: "lg" }),
              "h-12 cursor-pointer border-input bg-card px-5 text-base font-semibold",
            )}
          >
            Show the plan anyway
            <ChevronDown
              aria-hidden
              className="size-4 transition-transform duration-200 ease-out group-open:rotate-180"
            />
          </summary>
          <div className="mt-5 sm:mt-6">{content}</div>
        </details>
      </PageFrame>
    </>
  );
}
