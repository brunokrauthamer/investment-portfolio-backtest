import type { ApexOptions } from "apexcharts";

export interface TooltipPoint {
  date: string;
  daily_return_pct: number;
}

export type TooltipPointLookup = (seriesIndex: number, dataPointIndex: number) => TooltipPoint | undefined;

export function formatPercentage(value: number): string {
  return `${value}%`;
}

export function formatUtcDate(value: string | number): string {
  const timestamp =
    typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)
      ? Date.parse(`${value}T00:00:00.000Z`)
      : Number(value);

  return new Date(timestamp).toISOString().slice(0, 10);
}

export function formatUtcMonth(timestamp: number): string {
  return new Date(timestamp).toLocaleDateString("en-US", {
    month: "short",
    timeZone: "UTC",
    year: "numeric",
  });
}

function hslToHex(hue: number, saturation: number, lightness: number): string {
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
  const segment = hue / 60;
  const secondary = chroma * (1 - Math.abs((segment % 2) - 1));
  const [red, green, blue] = segment < 1
    ? [chroma, secondary, 0]
    : segment < 2
      ? [secondary, chroma, 0]
      : segment < 3
        ? [0, chroma, secondary]
        : segment < 4
          ? [0, secondary, chroma]
          : segment < 5
            ? [secondary, 0, chroma]
            : [chroma, 0, secondary];
  const offset = lightness - chroma / 2;
  return `#${[red, green, blue]
    .map((channel) => Math.round((channel + offset) * 255).toString(16).padStart(2, "0"))
    .join("")}`;
}

export function portfolioColor(index: number, previouslyAssigned: readonly string[] = []): string {
  const used = new Set(previouslyAssigned);
  let attempt = 0;
  while (true) {
    const candidateIndex = index + attempt;
    const hue = ((candidateIndex * 137.50776405) % 360 + 360) % 360;
    const saturation = 0.62 + (candidateIndex % 4) * 0.08;
    const lightness = 0.3 + (Math.floor(candidateIndex / 4) % 3) * 0.035;
    const color = hslToHex(hue, saturation, lightness);
    if (!used.has(color)) return color;
    attempt += 1;
  }
}

export function createChartOptions(
  colors: string[],
  findTooltipPoint: TooltipPointLookup,
): ApexOptions {
  return {
    chart: {
      type: "line",
      animations: { enabled: false },
      fontFamily: "inherit",
      foreColor: "#526176",
      parentHeightOffset: 0,
      toolbar: { show: false },
      zoom: { enabled: false },
    },
    colors,
    dataLabels: { enabled: false },
    grid: {
      borderColor: "#e9edf3",
      padding: { bottom: 2, left: 12, right: 14, top: 10 },
      strokeDashArray: 4,
    },
    markers: {
      colors: ["#ffffff"],
      hover: { size: 7 },
      size: 0,
      strokeColors: colors,
      strokeWidth: 3,
    },
    responsive: [{
      breakpoint: 480,
      options: {
        xaxis: {
          labels: {
            formatter: (value: string) => new Date(Number(value)).toLocaleDateString("en-US", {
              month: "short",
              timeZone: "UTC",
            }),
          },
        },
      },
    }],
    stroke: { curve: "smooth", width: 3 },
    tooltip: {
      intersect: true,
      shared: false,
      x: {
        formatter: (value, options) => {
          const point = findTooltipPoint(options?.seriesIndex ?? -1, options?.dataPointIndex ?? -1);
          return point?.date ?? formatUtcDate(value);
        },
      },
      y: {
        formatter: (value, options) => {
          const point = findTooltipPoint(options?.seriesIndex ?? -1, options?.dataPointIndex ?? -1);
          const cumulative = formatPercentage(value);
          return point
            ? `${cumulative} (daily return: ${formatPercentage(point.daily_return_pct)})`
            : cumulative;
        },
      },
    },
    xaxis: {
      type: "datetime",
      labels: {
        formatter: (value) => formatUtcMonth(Number(value)),
        hideOverlappingLabels: true,
        rotate: 0,
        showDuplicates: false,
        style: { fontSize: "11px" },
      },
      tickAmount: 5,
      tooltip: { enabled: false },
    },
    yaxis: {
      labels: {
        formatter: formatPercentage,
        style: { fontSize: "11px" },
      },
      tickAmount: 4,
    },
  };
}
