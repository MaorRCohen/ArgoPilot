import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageFrame } from "@/components/page-frame";
import { SplitTitle } from "@/components/split-title";
import type { Photo } from "@/lib/images";
import { cn } from "@/lib/utils";

/** A test tube filled to n/10: the scale is visible, not only the number. */
function Vial({ n }: { n: number }) {
  const inner = 41; // height of the tube's inside
  const level = (inner * n) / 10;
  const id = `vial-${n}`;
  return (
    // Inline size: Button forces every svg inside it to size-4, and an inline style wins over that rule.
    <svg
      aria-hidden
      viewBox="0 0 22 44"
      style={{ height: "clamp(2.5rem, 6vw, 3.5rem)", width: "auto" }}
      className="shrink-0"
    >
      <defs>
        <clipPath id={id}>
          <rect x="1.5" y="1.5" width="19" height={inner} rx="6" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id})`}>
        <rect x="0" y={42.5 - level} width="22" height={level} className="fill-water" />
      </g>
      <rect
        x="1.5"
        y="1.5"
        width="19"
        height={inner}
        rx="6"
        fill="none"
        strokeWidth="2"
        className="stroke-foreground"
      />
    </svg>
  );
}

/** First step of the plot page: the grower's own soil reading. One tap on a number loads the plan (GET, kept in the URL). */
export function SoilQuestion({ photo, transitionName }: { photo: Photo; transitionName?: string }) {
  return (
    <PageFrame
      scene
      photo={photo}
      transitionName={transitionName}
      band={
        <>
          <h1
            id="soil-q"
            className="max-w-[18ch] font-heading text-[clamp(1.75rem,5.6vw,3.75rem)] leading-[1.05] font-bold tracking-[0.03em] text-balance uppercase"
          >
            <SplitTitle text="How wet is the soil today?" />
          </h1>
          <p
            className="intro mt-4 max-w-[52ch] text-lg text-muted-foreground"
            style={{ "--i": 6 } as React.CSSProperties}
          >
            Squeeze a handful of soil from root depth in your hand. Dry and crumbly is low, a ball that drips is high.
          </p>
        </>
      }
    >
      <section aria-labelledby="soil-q">
        <Card
          className="on-dark panel intro gap-0 rounded-[1.75rem] p-5 shadow-float ring-0 sm:p-8"
          style={{ "--i": 7 } as React.CSSProperties}
        >
          <form method="get">
            <fieldset>
              <legend className="sr-only">Soil moisture, from 0 (dry) to 10 (soaked)</legend>
              <div className="grid grid-cols-4 gap-2.5 sm:gap-3 md:grid-cols-6 lg:grid-cols-11">
                {Array.from({ length: 11 }, (_, n) => (
                  <Button
                    key={n}
                    type="submit"
                    name="soil_moisture"
                    value={n}
                    variant="tile"
                    aria-label={n === 0 ? "0, completely dry" : n === 10 ? "10, soaked" : String(n)}
                    className={cn(
                      "h-auto min-h-28 flex-col gap-2 rounded-2xl border-2 px-1 py-3 sm:min-h-40 sm:gap-3 sm:py-4 lg:min-h-52 lg:gap-4",
                      n === 10 && "col-span-2 lg:col-span-1",
                    )}
                  >
                    <span className="text-4xl leading-none font-bold sm:text-5xl lg:text-[3.25rem]">{n}</span>
                    <Vial n={n} />
                  </Button>
                ))}
              </div>
            </fieldset>
            <dl className="mt-6 flex flex-col gap-2 text-muted-foreground sm:flex-row sm:justify-between sm:gap-8">
              <div className="flex gap-3">
                <dt className="w-6 font-bold text-foreground">0</dt>
                <dd>Completely dry / first planting</dd>
              </div>
              <div className="flex gap-3 sm:text-right">
                <dt className="w-6 font-bold text-foreground sm:order-2">10</dt>
                <dd>Soaked (after heavy rain or irrigation)</dd>
              </div>
            </dl>
          </form>
        </Card>
      </section>
    </PageFrame>
  );
}
