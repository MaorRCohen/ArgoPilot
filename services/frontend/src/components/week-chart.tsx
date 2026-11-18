import { ChartScope, DrawDashedLine, DrawLine, Drop, Fade } from "@/components/chart-motion";
import { Tilt } from "@/components/motion/tilt";
import { Card } from "@/components/ui/card";
import { dayMonth, weekday } from "@/lib/format";
import type { PlanDay, PlanView } from "@/lib/planner";

type Layout = {
  key: string;
  w: number;
  h: number;
  ml: number;
  mr: number;
  mt: number;
  mb: number;
  font: number;
  maxBar: number;
};

// Two drawings from the same data. Text stays the same size on screen because each SVG is shown near 1:1.
const NARROW: Layout = {
  key: "n",
  w: 336,
  h: 236,
  ml: 32,
  mr: 6,
  mt: 22,
  mb: 42,
  font: 11.5,
  maxBar: 26,
};
const WIDE: Layout = {
  key: "w",
  w: 640,
  h: 288,
  ml: 42,
  mr: 10,
  mt: 26,
  mb: 46,
  font: 13,
  maxBar: 40,
};

/** The days, or null when any number the chart needs is missing: then the chart is hidden, never filled with zeros. */
function chartDays(plan: PlanView): PlanDay[] | null {
  const days = plan.days;
  if (!days || days.length === 0) return null;
  const complete = days.every(
    (d) =>
      typeof d.date === "string" &&
      Number.isFinite(d.need_mm) &&
      Number.isFinite(d.et0_mm) &&
      Number.isFinite(d.rain_mm) &&
      Number.isFinite(d.irrigation_mm),
  );
  return complete ? days : null;
}

/** A round top value and step for the mm axis, about four gridlines. */
function niceScale(peak: number): { top: number; step: number } {
  const target = Math.max(peak, 1);
  const raw = target / 4;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / pow;
  const step = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * pow;
  return { top: Math.ceil(target / step - 1e-9) * step, step };
}

const mm = (n: number): string => String(Math.round(n * 10) / 10);

function Drawing({ days, l, label }: { days: PlanDay[]; l: Layout; label: string }) {
  const n = days.length;
  const innerW = l.w - l.ml - l.mr;
  const innerH = l.h - l.mt - l.mb;
  const peak = Math.max(...days.map((d) => Math.max(d.need_mm, d.et0_mm, d.rain_mm + d.irrigation_mm)));
  const { top, step } = niceScale(peak);
  const y = (v: number) => l.mt + innerH * (1 - v / top);
  const slot = innerW / n;
  const barW = Math.min(slot * 0.52, l.maxBar);
  const cx = (i: number) => l.ml + slot * i + slot / 2;
  const ticks: number[] = [];
  for (let t = 0; t <= top + 1e-9; t += step) ticks.push(Math.round(t * 100) / 100);
  const line = (pick: (d: PlanDay) => number) =>
    days.map((d, i) => `${cx(i).toFixed(1)},${y(pick(d)).toFixed(1)}`).join(" ");
  const rainPattern = `rain-${l.key}`;

  return (
    <svg viewBox={`0 0 ${l.w} ${l.h}`} role="img" aria-label={label} className="h-auto w-full">
      <defs>
        <pattern id={rainPattern} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="6" height="6" className="fill-water-tint" />
          <line x1="0" y1="0" x2="0" y2="6" strokeWidth="2.2" className="stroke-water" />
        </pattern>
      </defs>

      {ticks.map((t) => (
        <g key={t}>
          <line
            x1={l.ml}
            x2={l.w - l.mr}
            y1={y(t)}
            y2={y(t)}
            strokeWidth="1"
            className={t === 0 ? "stroke-input" : "stroke-border"}
          />
          <text
            x={l.ml - 7}
            y={y(t) + l.font * 0.35}
            textAnchor="end"
            fontSize={l.font}
            className="fill-muted-foreground"
          >
            {mm(t)}
          </text>
        </g>
      ))}
      <text x={l.ml - 7} y={l.mt - 10} textAnchor="end" fontSize={l.font} className="fill-muted-foreground">
        mm
      </text>

      {days.map((d, i) => {
        const x = cx(i) - barW / 2;
        const rainTop = y(d.rain_mm);
        const stackTop = y(d.rain_mm + d.irrigation_mm);
        return (
          <g key={d.date}>
            <title>{`${i === 0 ? "Today" : weekday(d.date)} ${dayMonth(d.date)}: need ${mm(d.need_mm)} mm, ET0 ${mm(d.et0_mm)} mm, rain ${mm(d.rain_mm)} mm, irrigation ${mm(d.irrigation_mm)} mm`}</title>
            {d.rain_mm > 0 || d.irrigation_mm > 0 ? (
              <Drop i={i}>
                {d.rain_mm > 0 ? (
                  <rect
                    x={x}
                    y={rainTop}
                    width={barW}
                    height={y(0) - rainTop}
                    fill={`url(#${rainPattern})`}
                    strokeWidth="1"
                    className="stroke-water"
                  />
                ) : null}
                {d.irrigation_mm > 0 ? (
                  <rect x={x} y={stackTop} width={barW} height={rainTop - stackTop} rx="2" className="fill-water" />
                ) : null}
                {d.irrigation_mm > 0 ? (
                  <text
                    x={cx(i)}
                    y={stackTop - 6}
                    textAnchor="middle"
                    fontSize={l.font}
                    fontWeight="700"
                    strokeWidth="4"
                    strokeLinejoin="round"
                    paintOrder="stroke"
                    className="fill-water-ink stroke-card"
                  >
                    {mm(d.irrigation_mm)}
                  </text>
                ) : null}
              </Drop>
            ) : null}
            <text
              x={cx(i)}
              y={l.h - l.mb + l.font + 8}
              textAnchor="middle"
              fontSize={l.font}
              fontWeight={i === 0 ? 700 : 500}
              className="fill-foreground"
            >
              {i === 0 ? "Today" : weekday(d.date)}
            </text>
            <text
              x={cx(i)}
              y={l.h - l.mb + l.font * 2 + 10}
              textAnchor="middle"
              fontSize={l.font - 1}
              className="fill-muted-foreground"
            >
              {dayMonth(d.date)}
            </text>
          </g>
        );
      })}

      <DrawDashedLine
        id={`et0-${l.key}`}
        points={line((d) => d.et0_mm)}
        strokeWidth={2}
        className="stroke-chart-et0"
        width={l.w}
        height={l.h}
      />
      <DrawLine points={line((d) => d.need_mm)} strokeWidth={2.5} className="stroke-chart-need" />
      {days.map((d, i) => (
        <Fade key={d.date} i={i} count={n}>
          <circle cx={cx(i)} cy={y(d.need_mm)} r="4" strokeWidth="2.5" className="fill-card stroke-chart-need" />
        </Fade>
      ))}
    </svg>
  );
}

function Key({ children, swatch }: { children: string; swatch: React.ReactNode }) {
  return (
    <li className="flex items-center gap-2">
      <svg aria-hidden viewBox="0 0 24 12" className="h-3 w-6 shrink-0">
        {swatch}
      </svg>
      {children}
    </li>
  );
}

/** Seven days of crop need, ET0, rain and irrigation, in mm. Inline SVG. */
export function WeekChart({ plan }: { plan: PlanView }) {
  const days = chartDays(plan);
  if (!days) return null;

  const label = `Water each day in millimetres. ${days
    .map(
      (d, i) =>
        `${i === 0 ? "Today" : weekday(d.date)}: need ${mm(d.need_mm)}, ET0 ${mm(d.et0_mm)}, rain ${mm(d.rain_mm)}, irrigation ${mm(d.irrigation_mm)}`,
    )
    .join("; ")}.`;

  return (
    <Tilt className="rounded-xl" max={2} lift={4}>
      <Card className="on-dark panel gap-0 rounded-xl p-5 shadow-float ring-0 sm:p-6">
        <h2 className="font-heading text-xl font-bold">Water each day</h2>
        <p className="mt-1 text-muted-foreground">What the crop needs, against rain and irrigation, in mm.</p>

        <ChartScope className="mt-4 hidden sm:block">
          <Drawing days={days} l={WIDE} label={label} />
        </ChartScope>
        <ChartScope className="mt-4 sm:hidden">
          <Drawing days={days} l={NARROW} label={label} />
        </ChartScope>

        <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm">
          <Key
            swatch={
              <>
                <line x1="1" x2="23" y1="6" y2="6" strokeWidth="2.5" className="stroke-chart-need" />
                <circle cx="12" cy="6" r="3.5" strokeWidth="2.5" className="fill-card stroke-chart-need" />
              </>
            }
          >
            Need
          </Key>
          <Key
            swatch={
              <line x1="1" x2="23" y1="6" y2="6" strokeWidth="2" strokeDasharray="5 4" className="stroke-chart-et0" />
            }
          >
            ET0
          </Key>
          <Key
            swatch={
              <>
                <defs>
                  <pattern
                    id="rain-key"
                    width="6"
                    height="6"
                    patternUnits="userSpaceOnUse"
                    patternTransform="rotate(45)"
                  >
                    <rect width="6" height="6" className="fill-water-tint" />
                    <line x1="0" y1="0" x2="0" y2="6" strokeWidth="2.2" className="stroke-water" />
                  </pattern>
                </defs>
                <rect
                  x="1"
                  y="1"
                  width="22"
                  height="10"
                  fill="url(#rain-key)"
                  strokeWidth="1"
                  className="stroke-water"
                />
              </>
            }
          >
            Rain
          </Key>
          <Key swatch={<rect x="1" y="1" width="22" height="10" rx="2" className="fill-water" />}>Irrigation</Key>
        </ul>
      </Card>
    </Tilt>
  );
}
