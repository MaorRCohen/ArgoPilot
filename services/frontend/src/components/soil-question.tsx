import { Button } from "@/components/ui/button";

/** First step of the plot page: the grower's own soil reading. One tap on a number loads the plan (GET, kept in the URL). */
export function SoilQuestion() {
  return (
    <section aria-labelledby="soil-q">
      <h1 id="soil-q" className="font-heading text-4xl leading-tight font-extrabold tracking-tight text-balance">
        How wet is the soil today?
      </h1>
      <p className="mt-3">
        Squeeze a handful of soil from root depth in your hand. Dry and crumbly is low, a ball that drips is high.
      </p>
      <form method="get" className="mt-5">
        <div className="grid grid-cols-6 gap-2">
          {Array.from({ length: 11 }, (_, n) => (
            <Button
              key={n}
              type="submit"
              name="soil_moisture"
              value={n}
              variant="outline"
              className="h-12 text-lg font-bold"
            >
              {n}
            </Button>
          ))}
        </div>
        <dl className="mt-3 space-y-1 text-sm text-muted-foreground">
          <div className="flex gap-2">
            <dt className="w-6 font-bold text-foreground">0</dt>
            <dd>Completely dry / first planting</dd>
          </div>
          <div className="flex gap-2">
            <dt className="w-6 font-bold text-foreground">10</dt>
            <dd>Soaked (after heavy rain or irrigation)</dd>
          </div>
        </dl>
      </form>
    </section>
  );
}
