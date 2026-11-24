/** "38 min", "2 h", "17 h 20 min". */
export function formatRun(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

/** The same text as formatRun, split into number and unit so the number can be set big: 38 min, or 2 h and 20 min. */
export function runParts(minutes: number): { value: string; unit: string }[] {
  if (minutes < 60) return [{ value: String(minutes), unit: "min" }];
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0
    ? [{ value: String(h), unit: "h" }]
    : [
        { value: String(h), unit: "h" },
        { value: String(m), unit: "min" },
      ];
}

/** "clay-loam" -> "Clay loam". The registry's names are these ids in sentence case, so no extra request is needed. */
export function labelFromId(id: string): string {
  const text = id.replace(/[-_]+/g, " ").trim();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export const formatLitres = (litres: number): string => `${litres.toLocaleString("en-US")} L`;

// Dates are plain calendar days (the plot's local day): format them in UTC so they never shift.
const utc = (iso: string) => new Date(`${iso}T00:00:00Z`);

export const weekday = (iso: string): string =>
  utc(iso).toLocaleDateString("en-GB", { weekday: "short", timeZone: "UTC" });

export const dayMonth = (iso: string): string =>
  utc(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });

/** "3 h ago", "25 min ago". */
export function formatAge(minutes: number): string {
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  return hours < 48 ? `${hours} h ago` : `${Math.floor(hours / 24)} days ago`;
}
