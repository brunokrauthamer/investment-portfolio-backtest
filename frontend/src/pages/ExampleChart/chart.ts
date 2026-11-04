import type { ApexOptions } from "apexcharts";

export const examplePercentageData = [
  { date: "2024-01-01", value: 0 },
  { date: "2024-02-01", value: 2.5 },
  { date: "2024-03-01", value: -1.2 },
  { date: "2024-04-01", value: 3.8 },
  { date: "2024-05-01", value: 2 },
  { date: "2024-06-01", value: 5.1 },
] as const;

export function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`;
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

export const exampleSeriesData = examplePercentageData.map(({ date, value }) => ({
  x: Date.parse(`${date}T00:00:00.000Z`),
  y: value,
}));

export const exampleSeries = [
  { name: "Example percentage", data: exampleSeriesData },
] satisfies NonNullable<ApexOptions["series"]>;

export const exampleChartOptions: ApexOptions = {
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
  stroke: { curve: "smooth", width: 3 },
  tooltip: {
    intersect: true,
    shared: false,
    x: {
      formatter: (value, opts) => {
        const point = examplePercentageData[opts?.dataPointIndex ?? -1];
        return point ? formatUtcDate(point.date) : String(value);
      },
    },
    y: { formatter: formatPercentage },
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
