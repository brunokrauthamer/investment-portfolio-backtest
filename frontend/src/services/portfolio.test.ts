import axios from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { submitPortfolio, type PortfolioRequest, type PortfolioResponse } from "./portfolio";

vi.mock("axios", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

const request: PortfolioRequest = {
  initial_date: "2024-01-01",
  end_date: "2024-01-03",
  allocations: [{ index: "ibovespa", percentage: 100 }],
  rebalancing: "none",
};

const point = (date: string, x: number) => ({
  date,
  x,
  y: 1,
  daily_return_pct: 1,
  cumulative_return_pct: 1,
});

beforeEach(() => vi.mocked(axios.post).mockReset());
afterEach(() => vi.clearAllMocks());

describe("portfolio response validation", () => {
  it("rejects impossible dates, mismatched UTC timestamps, and non-chronological points", async () => {
    const invalidResponses: PortfolioResponse[] = [
      { series: [{ name: "Cumulative portfolio return", data: [point("2024-99-99", 0)] }] },
      { series: [{ name: "Cumulative portfolio return", data: [point("2024-01-02", 0)] }] },
      { series: [{
        name: "Cumulative portfolio return",
        data: [
          point("2024-01-02", Date.UTC(2024, 0, 2)),
          point("2024-01-01", Date.UTC(2024, 0, 1)),
        ],
      }] },
    ];

    for (const data of invalidResponses) {
      vi.mocked(axios.post).mockResolvedValueOnce({ data });
      await expect(submitPortfolio(request)).rejects.toThrow(/invalid portfolio result/i);
    }
  });

  it("returns the validated series unchanged", async () => {
    const data: PortfolioResponse = { series: [{
      name: "Cumulative portfolio return",
      data: [point("2024-01-02", Date.UTC(2024, 0, 2))],
    }] };
    vi.mocked(axios.post).mockResolvedValueOnce({ data });

    const response = await submitPortfolio(request);

    expect(response.series).toBe(data.series);
  });
});
