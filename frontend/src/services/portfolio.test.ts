import axios from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";
import { submitPortfolio, type PortfolioSeriesResponse } from "./portfolio";

vi.mock("axios", () => ({ default: { post: vi.fn() } }));

const request = {
  initial_date: "2020-01-01",
  end_date: "2020-01-02",
  allocations: [{ index: "ibovespa" as const, percentage: 100 }],
  rebalancing: "none" as const,
};

const validResponse: PortfolioSeriesResponse = {
  series: [{
    name: "Cumulative portfolio return",
    data: [
      { x: 1577836800000, y: 1.25, date: "2020-01-01", daily_return_pct: 1.25, cumulative_return_pct: 1.25 },
      { x: 1577923200000, y: 1.5, date: "2020-01-02", daily_return_pct: 0.25, cumulative_return_pct: 1.5 },
    ],
  }],
};

afterEach(() => vi.resetAllMocks());

describe("submitPortfolio response contract", () => {
  it("returns the API series with plotted values and supplemental points unchanged", async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({ data: validResponse });

    await expect(submitPortfolio(request)).resolves.toEqual(validResponse);
    expect(axios.post).toHaveBeenCalledWith("/api/portfolio", request);
  });

  it("accepts a valid empty data array", async () => {
    const empty = { series: [{ name: "Cumulative portfolio return", data: [] }] };
    vi.mocked(axios.post).mockResolvedValueOnce({ data: empty });

    await expect(submitPortfolio(request)).resolves.toEqual(empty);
  });

  it.each([
    ["an acknowledgement", { status: "ok" }],
    ["no series", { series: [] }],
    ["multiple series", { series: [validResponse.series[0], validResponse.series[0]] }],
    ["a missing data array", { series: [{ name: "Returns" }] }],
    ["a non-finite return", { series: [{ name: "Returns", data: [{ ...validResponse.series[0].data[0], y: Infinity }] }] }],
    ["a date inconsistent with its UTC timestamp", { series: [{ name: "Returns", data: [{ ...validResponse.series[0].data[0], date: "2020-01-02" }] }] }],
    ["a plotted value inconsistent with cumulative_return_pct", { series: [{ name: "Returns", data: [{ ...validResponse.series[0].data[0], y: 2 }] }] }],
  ])("rejects %s", async (_description, data) => {
    vi.mocked(axios.post).mockResolvedValueOnce({ data });

    await expect(submitPortfolio(request)).rejects.toThrow(/valid cumulative-return series/i);
  });
});
