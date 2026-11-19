import Image from "next/image";
import { Suspense, ViewTransition } from "react";
import { Droplets, Layers, Ruler, Sprout } from "lucide-react";
import { PlotLink } from "@/components/motion/plot-link";
import { Reveal } from "@/components/motion/reveal";
import { Tilt } from "@/components/motion/tilt";
import { PageFrame } from "@/components/page-frame";
import { Problem } from "@/components/problem";
import { SplitTitle } from "@/components/split-title";
import { buttonVariants } from "@/components/ui/button";
import { labelFromId } from "@/lib/format";
import { photoFor } from "@/lib/images";
import { getCrops, getFarms, getPlots, type Plot } from "@/lib/registry";
import { cn } from "@/lib/utils";

export default function HomePage() {
  return (
    <PageFrame
      size="tall"
      band={
        <>
          <h1 className="font-heading text-marquee font-bold text-balance uppercase [overflow-wrap:anywhere]">
            <SplitTitle text="Farms and plots" />
          </h1>
          <p
            className="intro mt-5 max-w-[38ch] text-lg text-muted-foreground sm:text-xl"
            style={{ "--i": 4 } as React.CSSProperties}
          >
            Should I water this plot today, and for how long?
          </p>
        </>
      }
    >
      <Suspense
        fallback={
          // Tall enough that the footer stays below the fold while the farms load: no layout shift when they arrive.
          <div className="min-h-[60svh]">
            <p role="status" className="rounded-2xl bg-card p-6 text-lg text-muted-foreground shadow-lift">
              Loading farms…
            </p>
          </div>
        }
      >
        <Farms />
      </Suspense>
    </PageFrame>
  );
}

/** A plot card: a photo on top (details slide up on hover), name, crop and the way in. The photo morphs into the plot page hero. */
function PlotCard({ plot, crop }: { plot: Plot; crop: string }) {
  const photo = photoFor(plot.id);
  const chip = "glass flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-foreground";
  return (
    <Tilt className="rounded-[1.75rem]" max={5}>
      <PlotLink
        plotId={plot.id}
        className="group block overflow-hidden rounded-[1.75rem] bg-card shadow-lift ring-1 ring-border outline-offset-4"
      >
        <div className="relative aspect-[16/10] overflow-hidden bg-night">
          <ViewTransition name={`plot-photo-${plot.id}`} share="morph" default="none">
            <div className="absolute inset-0">
              <Image
                src={photo.img}
                alt=""
                fill
                sizes="(min-width: 1024px) 380px, (min-width: 640px) 46vw, 92vw"
                quality={60}
                placeholder="blur"
                className="object-cover transition-transform duration-500 ease-out group-hover:scale-110"
                style={{ objectPosition: photo.position }}
              />
            </div>
          </ViewTransition>
          <div aria-hidden className="absolute inset-0 bg-linear-to-t from-night/70 via-transparent to-transparent" />
          <dl className="on-dark absolute inset-x-0 bottom-0 flex flex-wrap gap-2 p-3.5 transition-[opacity,transform] duration-300 ease-out [@media(hover:hover)]:translate-y-3 [@media(hover:hover)]:opacity-0 group-hover:translate-y-0 group-hover:opacity-100 group-focus-visible:translate-y-0 group-focus-visible:opacity-100">
            <div className={chip}>
              <dt className="sr-only">Soil</dt>
              <Layers aria-hidden className="size-4 text-signal" />
              <dd>{labelFromId(plot.soil_id)}</dd>
            </div>
            <div className={chip}>
              <dt className="sr-only">Area</dt>
              <Ruler aria-hidden className="size-4 text-signal" />
              <dd>{plot.area_m2.toLocaleString("en-US")} m²</dd>
            </div>
          </dl>
        </div>
        <div className="p-5">
          <h3 className="font-heading text-xl leading-tight font-bold [overflow-wrap:anywhere] sm:text-2xl">
            {plot.name}
          </h3>
          <p className="mt-2 flex items-center gap-2 text-base">
            <Sprout aria-hidden className="size-4 text-leaf-ink" />
            <span className="sr-only">Crop: </span>
            <span className="font-semibold">{crop}</span>
          </p>
          <span
            className={cn(
              buttonVariants({ variant: "outline", size: "lg" }),
              "mt-5 h-12 w-full gap-2 px-4 text-base font-semibold group-hover:border-foreground group-hover:text-background group-hover:before:scale-x-100 group-focus-visible:text-background group-focus-visible:before:scale-x-100",
            )}
          >
            <Droplets aria-hidden className="size-4" />
            Today&apos;s plan
          </span>
        </div>
      </PlotLink>
    </Tilt>
  );
}

async function Farms() {
  const [farms, plots, crops] = await Promise.all([getFarms(), getPlots(), getCrops()]);
  for (const r of [farms, plots, crops]) {
    if (!r.ok) return <Problem error={r.error} what="farm list" retryHref="/" tone="paper" />;
  }
  if (!farms.ok || !plots.ok || !crops.ok) return null;

  const cropName = new Map(crops.data.map((c) => [c.id, c.name]));

  if (farms.data.length === 0) {
    return (
      <p className="rounded-2xl border-2 border-dashed border-input bg-card p-8 text-lg text-muted-foreground">
        No farms yet. Add one in the registry to see it here.
      </p>
    );
  }

  return (
    <div className="space-y-14">
      {farms.data.map((farm) => {
        const farmPlots = plots.data.filter((p) => p.farm_id === farm.id);
        return (
          <section key={farm.id} aria-labelledby={`farm-${farm.id}`}>
            <Reveal className="flex items-baseline justify-between gap-4 border-b border-input pb-3">
              <h2
                id={`farm-${farm.id}`}
                className="font-heading text-2xl font-bold [overflow-wrap:anywhere] sm:text-3xl"
              >
                {farm.name}
              </h2>
              <p className="shrink-0 text-muted-foreground">
                {/* A count of 1 to 5 does not need to count up: it is read at a glance, so it is plain text. */}
                {farmPlots.length} {farmPlots.length === 1 ? "plot" : "plots"}
              </p>
            </Reveal>
            {farmPlots.length === 0 ? (
              <p className="mt-5 rounded-2xl border-2 border-dashed border-input p-6 text-muted-foreground">
                No plots on this farm yet.
              </p>
            ) : (
              <ul className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {farmPlots.map((plot, i) => (
                  <li key={plot.id}>
                    <Reveal delay={(i % 3) * 0.07}>
                      <PlotCard plot={plot} crop={cropName.get(plot.crop_id) ?? plot.crop_id} />
                    </Reveal>
                  </li>
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
