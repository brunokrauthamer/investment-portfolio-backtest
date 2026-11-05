import axios from "axios";

export interface IndexOption {
  id: "ibovespa" | "ifix" | "selic" | "sp500";
  name: "IBOVESPA" | "IFIX" | "Selic" | "S&P 500";
}

export type RebalancingStrategy =
  | "none"
  | "3_months"
  | "6_months"
  | "1_year"
  | "2_years"
  | "3_years";

export interface PortfolioRequest {
  initial_date: string;
  end_date: string;
  allocations: { index: IndexOption["id"]; percentage: number }[];
  rebalancing: RebalancingStrategy;
}

export interface PortfolioSeriesPoint {
  x: number;
  y: number;
  date: string;
  daily_return_pct: number;
  cumulative_return_pct: number;
}

export interface PortfolioSeries {
  name: string;
  data: PortfolioSeriesPoint[];
}

export interface PortfolioSeriesResponse {
  series: [PortfolioSeries];
}

export class InvalidPortfolioSeriesError extends Error {
  constructor() {
    super("The server response did not include a valid cumulative-return series.");
    this.name = "InvalidPortfolioSeriesError";
  }
}

function isCalendarDate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00.000Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isValidPoint(value: unknown): value is PortfolioSeriesPoint {
  if (!isRecord(value)) return false;
  const { x, y, date, daily_return_pct, cumulative_return_pct } = value;
  if (
    typeof x !== "number" || !Number.isSafeInteger(x) || Number.isNaN(new Date(x).getTime()) ||
    typeof y !== "number" || !Number.isFinite(y) ||
    typeof daily_return_pct !== "number" || !Number.isFinite(daily_return_pct) ||
    typeof cumulative_return_pct !== "number" || !Number.isFinite(cumulative_return_pct) ||
    !isCalendarDate(date) || y !== cumulative_return_pct
  ) return false;

  return new Date(x).toISOString().slice(0, 10) === date;
}

function isValidPortfolioSeriesResponse(value: unknown): value is PortfolioSeriesResponse {
  if (!isRecord(value) || !Array.isArray(value.series) || value.series.length !== 1) return false;
  const series = value.series[0];
  return (
    isRecord(series) &&
    typeof series.name === "string" && series.name.trim().length > 0 &&
    Array.isArray(series.data) && series.data.every(isValidPoint)
  );
}

const expectedIndexes: IndexOption[] = [
  { id: "ibovespa", name: "IBOVESPA" },
  { id: "ifix", name: "IFIX" },
  { id: "selic", name: "Selic" },
  { id: "sp500", name: "S&P 500" },
];

export async function fetchIndexes(): Promise<IndexOption[]> {
  const response = await axios.get<unknown>("/api/indexes");
  if (!Array.isArray(response.data) || response.data.length !== expectedIndexes.length) {
    throw new Error("The index list did not match the supported indexes.");
  }

  const valid = response.data.every((item, index) => {
    const expected = expectedIndexes[index];
    return (
      typeof item === "object" && item !== null &&
      "id" in item && "name" in item &&
      item.id === expected.id && item.name === expected.name
    );
  });
  if (!valid) throw new Error("The index list did not match the supported indexes.");
  return response.data as IndexOption[];
}

function isPortfolioPoint(value: unknown): value is PortfolioPoint {
  if (typeof value !== "object" || value === null) return false;
  if (
    Object.keys(value).length !== 5 ||
    !("x" in value) || !Number.isSafeInteger(value.x) ||
    !("y" in value) || typeof value.y !== "number" || !Number.isFinite(value.y) ||
    !("date" in value) || typeof value.date !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value.date) ||
    !("daily_return_pct" in value) || typeof value.daily_return_pct !== "number" || !Number.isFinite(value.daily_return_pct) ||
    !("cumulative_return_pct" in value) || typeof value.cumulative_return_pct !== "number" ||
    !Number.isFinite(value.cumulative_return_pct) || value.y !== value.cumulative_return_pct
  ) return false;
  return true;
}

function utcMidnightTimestamp(value: string): number | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (year < 1 || month < 1 || month > 12) return null;

  const isLeapYear = year % 400 === 0 || (year % 4 === 0 && year % 100 !== 0);
  const daysInMonth = [31, isLeapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  if (day < 1 || day > daysInMonth[month - 1]) return null;

  const adjustedYear = year - (month <= 2 ? 1 : 0);
  const era = Math.floor(adjustedYear / 400);
  const yearOfEra = adjustedYear - era * 400;
  const adjustedMonth = month + (month > 2 ? -3 : 9);
  const dayOfYear = Math.floor((153 * adjustedMonth + 2) / 5) + day - 1;
  const dayOfEra = yearOfEra * 365 + Math.floor(yearOfEra / 4) - Math.floor(yearOfEra / 100) + dayOfYear;
  const daysSinceUnixEpoch = era * 146097 + dayOfEra - 719468;
  return daysSinceUnixEpoch * 86_400_000;
}

function isPortfolioResponse(value: unknown): value is PortfolioResponse {
  if (
    typeof value !== "object" || value === null || Object.keys(value).length !== 1 ||
    !("series" in value) || !Array.isArray(value.series)
  ) {
    return false;
  }
  if (value.series.length !== 1) return false;
  const [series] = value.series;
  if (
    typeof series !== "object" || series === null ||
    Object.keys(series).length !== 2 ||
    !("name" in series) || series.name !== "Cumulative portfolio return" ||
    !("data" in series) || !Array.isArray(series.data)
  ) return false;

  let previousTimestamp = Number.NEGATIVE_INFINITY;
  for (const point of series.data) {
    if (!isPortfolioPoint(point)) return false;
    const dateTimestamp = utcMidnightTimestamp(point.date);
    if (dateTimestamp === null || point.x !== dateTimestamp || point.x <= previousTimestamp) return false;
    previousTimestamp = point.x;
  }
  return true;
}

export async function submitPortfolio(
  request: PortfolioRequest,
): Promise<PortfolioSeriesResponse> {
  const response = await axios.post<unknown>("/api/portfolio", request);
  if (!isValidPortfolioSeriesResponse(response.data)) {
    throw new InvalidPortfolioSeriesError();
  }
  return response.data;
}
