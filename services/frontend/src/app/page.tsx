import Link from "next/link";
import { Suspense } from "react";
import { Problem } from "@/components/problem";
import { getCrops, getFarms, getPlots } from "@/lib/registry";

export default function HomePage() {
  return (
    <>
      <h1 className="font-heading text-3xl font-bold tracking-tight">Farms and plots</h1>
      <Suspense fallback={<p className="mt-6 text-muted-foreground">Loading farms…</p>}>
        <Farms />
      </Suspense>
    </>
  );
}

async function Farms() {
  const [farms, plots, crops] = await Promise.all([getFarms(), getPlots(), getCrops()]);
  for (const r of [farms, plots, crops]) {
    if (!r.ok) return <div className="mt-6"><Problem error={r.error} what="farm list" retryHref="/" /></div>;
  }
  if (!farms.ok || !plots.ok || !crops.ok) return null;

  const cropName = new Map(crops.data.map((c) => [c.id, c.name]));

  if (farms.data.length === 0) {
    return <p className="mt-6 text-muted-foreground">No farms yet. Add one in the registry to see it here.</p>;
  }

  return (
    <div className="mt-6 space-y-8">
      {farms.data.map((farm) => {
        const farmPlots = plots.data.filter((p) => p.farm_id === farm.id);
        return (
          <section key={farm.id} aria-labelledby={`farm-${farm.id}`}>
            <h2 id={`farm-${farm.id}`} className="font-heading text-xl font-bold">
              {farm.name}
            </h2>
            {farmPlots.length === 0 ? (
              <p className="mt-2 text-muted-foreground">No plots on this farm yet.</p>
            ) : (
              <ul className="mt-2 divide-y divide-border border-y border-border">
                {farmPlots.map((plot) => (
                  <li key={plot.id}>
                    <Link
                      href={`/plots/${plot.id}`}
                      className="flex min-h-14 items-center justify-between gap-3 py-3 outline-offset-2 hover:bg-muted focus-visible:outline-2 focus-visible:outline-ring"
                    >
                      <span className="font-bold">{plot.name}</span>
                      <span className="text-right text-muted-foreground">
                        {cropName.get(plot.crop_id) ?? plot.crop_id}, {plot.area_m2.toLocaleString("en-US")} m²
                      </span>
                    </Link>
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
