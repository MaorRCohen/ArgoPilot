/**
 * Furrow / contour lines for the textured top band and the plot cards.
 * Pure geometry, no data: parallel rows pushed around by a smooth "terrain" so they read as ploughed
 * ground on a contour map. Deterministic (same output on every render), no randomness.
 */
export type FurrowOptions = {
  width: number;
  height: number;
  lines: number;
  /** Shifts the terrain so two textures never look identical. */
  seed?: number;
  /** Distance between sample points. Larger = shorter paths (the band is inline in every page). */
  step?: number;
  /** Where the "hill" sits, as a fraction of the width / height. */
  hill?: { x: number; y: number; lift: number };
};

const round = (n: number): number => Math.round(n * 10) / 10;

/** Catmull-Rom through the points, written as cubic Beziers (smooth, short path strings). */
function smooth(points: [number, number][]): string {
  const p = points;
  let d = `M${round(p[0][0])} ${round(p[0][1])}`;
  for (let i = 0; i < p.length - 1; i++) {
    const p0 = p[Math.max(0, i - 1)];
    const p1 = p[i];
    const p2 = p[i + 1];
    const p3 = p[Math.min(p.length - 1, i + 2)];
    const c1x = p1[0] + (p2[0] - p0[0]) / 6;
    const c1y = p1[1] + (p2[1] - p0[1]) / 6;
    const c2x = p2[0] - (p3[0] - p1[0]) / 6;
    const c2y = p2[1] - (p3[1] - p1[1]) / 6;
    d += `C${round(c1x)} ${round(c1y)} ${round(c2x)} ${round(c2y)} ${round(p2[0])} ${round(p2[1])}`;
  }
  return d;
}

export function furrowPaths({ width, height, lines, seed = 0, hill, step = Math.max(60, Math.round(width / 12)) }: FurrowOptions): string[] {
  const spacing = height / (lines - 1);
  const hx = (hill?.x ?? 0.75) * width;
  const hy = (hill?.y ?? 0.3) * height;
  const lift = hill?.lift ?? 0.12 * height;
  const paths: string[] = [];

  for (let i = 0; i < lines; i++) {
    const y0 = i * spacing;
    const points: [number, number][] = [];
    for (let x = -step; x <= width + step; x += step) {
      const swell =
        0.07 * height * Math.sin(x / (width * 0.2) + y0 / (height * 0.45) + seed) +
        0.035 * height * Math.sin(x / (width * 0.085) - y0 / (height * 0.3) + 1.3 + seed * 2);
      const dx = (x - hx) / (width * 0.16);
      const dy = (y0 - hy) / (height * 0.3);
      const bump = lift * Math.exp(-(dx * dx + dy * dy) / 2);
      points.push([x, y0 + swell - bump]);
    }
    paths.push(smooth(points));
  }
  return paths;
}
