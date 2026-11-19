import { ChevronDown } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

/** Change the grower's soil reading on the plan page. A plain GET form: the reading stays in the URL. */
export function SoilForm({ value }: { value: number }) {
  return (
    <Card className="gap-0 rounded-xl p-5 ring-1 ring-border sm:p-6">
      <form method="get">
        <label htmlFor="soil_moisture" className="font-heading text-xl font-bold">
          Soil moisture today
        </label>
        <p className="mt-1 text-muted-foreground">Your own reading: 0 is dry or just planted, 10 is full.</p>
        <div className="mt-4 flex gap-3">
          <div className="relative min-w-0 flex-1">
            <select
              id="soil_moisture"
              name="soil_moisture"
              defaultValue={String(value)}
              className="h-12 w-full appearance-none rounded-lg border border-input bg-card pr-10 pl-4 text-base font-medium transition-colors duration-150 ease-out hover:bg-muted"
            >
              {Array.from({ length: 11 }, (_, n) => (
                <option key={n} value={n}>
                  {n === 0 ? "0 (dry)" : n === 10 ? "10 (full)" : n}
                </option>
              ))}
            </select>
            <ChevronDown aria-hidden className="pointer-events-none absolute top-1/2 right-3 size-5 -translate-y-1/2 text-muted-foreground" />
          </div>
          <Button type="submit" size="lg" className="h-12 px-5 text-base font-semibold">
            Update plan
          </Button>
        </div>
      </form>
    </Card>
  );
}
