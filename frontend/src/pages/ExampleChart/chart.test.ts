import { describe, expect, it } from "vitest";
import {
  formatPercentage,
  formatUtcDate,
  formatUtcMonth,
  portfolioChartOptions,
} from "./chart";

describe("portfolio return chart formatting", () => {
  it("formats percentage points for chart labels", () => {
    expect(formatPercentage(-1.2)).toBe("-1.2%");
    expect(formatPercentage(2.01)).toBe("2.01%");
  });

  it("keeps UTC date and month labels stable across time zones", () => {
    const marchTimestamp = Date.parse("2024-03-01T00:00:00.000Z");
    const initialTimeZone = process.env.TZ;
    try {
      for (const timeZone of ["America/Sao_Paulo", "America/Los_Angeles", "Asia/Tokyo"]) {
        process.env.TZ = timeZone;
        expect(formatUtcDate(marchTimestamp)).toBe("2024-03-01");
        expect(formatUtcMonth(marchTimestamp)).toBe("Mar 2024");
      }
    } finally {
      if (initialTimeZone === undefined) delete process.env.TZ;
      else process.env.TZ = initialTimeZone;
    }
  });

  it("configures a datetime axis and percentage return tooltip", () => {
    expect(portfolioChartOptions.chart?.type).toBe("line");
    expect(portfolioChartOptions.xaxis?.type).toBe("datetime");
    const yAxis = portfolioChartOptions.yaxis;
    expect(Array.isArray(yAxis)).toBe(false);
    expect((yAxis as { labels?: { formatter?: (value: number) => string } }).labels?.formatter?.(2.01)).toBe("2.01%");
    const tooltip = portfolioChartOptions.tooltip;
    expect(typeof tooltip?.custom).toBe("function");
    const tooltipY = Array.isArray(tooltip?.y) ? tooltip.y[0] : tooltip?.y;
    expect(tooltipY?.formatter?.(2.01)).toBe("2.01%");
  });
});
