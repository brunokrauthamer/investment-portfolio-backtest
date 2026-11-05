import type { ApexOptions } from "apexcharts";

export function formatPercentage(value: number): string {
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value)}%`;
}

export function formatUtcDate(value: string | number): string {
  const timestamp = typeof value === "string" ? Number(value) : value;
  return new Date(timestamp).toISOString().slice(0, 10);
}

export function formatUtcMonth(timestamp: number): string {
  return new Date(timestamp).toLocaleDateString("en-US", {
    month: "short",
    timeZone: "UTC",
    year: "numeric",
  });
}

export const portfolioChartOptions: ApexOptions = {
  chart: {
    type: "line",
    animations: { enabled: false },
    fontFamily: "inherit",
    foreColor: "#526176",
    parentHeightOffset: 0,
    toolbar: { show: false },
    zoom: { enabled: false },
  },
  colors: ["#16816f"],
  dataLabels: { enabled: false },
  grid: {
    borderColor: "#e9edf3",
    padding: { bottom: 2, left: 12, right: 14, top: 10 },
    strokeDashArray: 4,
  },
  markers: {
    colors: ["#ffffff"],
    hover: { size: 7 },
    size: 5,
    strokeColors: "#16816f",
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
    x: { formatter: (value) => formatUtcDate(value) },
    y: { formatter: formatPercentage },
    custom: ({ dataPointIndex, seriesIndex, w }) => {
      const configuredSeries = w.config.series?.[seriesIndex] as
        | { data?: unknown[] }
        | undefined;
      const point = configuredSeries?.data?.[dataPointIndex] as {
        date?: unknown;
        daily_return_pct?: unknown;
        cumulative_return_pct?: unknown;
      } | undefined;
      if (
        typeof point?.date !== "string" ||
        typeof point.daily_return_pct !== "number" ||
        typeof point.cumulative_return_pct !== "number"
      ) return "";
      return `<div class="portfolio-tooltip"><strong>${point.date}</strong><span>Daily return: ${formatPercentage(point.daily_return_pct)}</span><span>Cumulative return: ${formatPercentage(point.cumulative_return_pct)}</span></div>`;
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
    labels: { formatter: formatPercentage, style: { fontSize: "11px" } },
    tickAmount: 4,
  },
};
