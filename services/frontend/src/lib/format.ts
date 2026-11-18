/** "38 min", "2 h", "17 h 20 min". */
export function formatRun(minutes: number): string {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
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
