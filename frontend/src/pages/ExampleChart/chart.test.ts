import { afterEach, describe, expect, it } from "vitest";
import {
  createChartOptions,
  formatPercentage,
  formatUtcDate,
  formatUtcMonth,
  portfolioColor,
} from "./chart";

describe("cumulative-return chart helpers", () => {
  const initialTimeZone = process.env.TZ;

  afterEach(() => {
    if (initialTimeZone === undefined) delete process.env.TZ;
    else process.env.TZ = initialTimeZone;
  });

  it("formats returned percentages without changing chart values", () => {
    expect(formatPercentage(-1.2)).toBe("-1.2%");
    expect(formatPercentage(5.1)).toBe("5.1%");
  });

  it("keeps chart date labels and tooltips on the UTC calendar", () => {
    const timestamp = Date.parse("2024-03-01T00:00:00.000Z");
    const options = createChartOptions(["#147a62"], () => ({
      date: "2024-03-01",
      daily_return_pct: 0.25,
    }));
    const axisFormatter = options.xaxis?.labels?.formatter;
    const tooltipFormatter = options.tooltip?.x?.formatter;
    const tooltipY = Array.isArray(options.tooltip?.y) ? options.tooltip?.y[0] : options.tooltip?.y;

    for (const timeZone of ["America/Sao_Paulo", "America/Los_Angeles", "Asia/Tokyo"]) {
      process.env.TZ = timeZone;
      expect(formatUtcDate(timestamp)).toBe("2024-03-01");
      expect(formatUtcMonth(timestamp)).toBe("Mar 2024");
      expect(axisFormatter?.(String(timestamp), timestamp)).toBe("Mar 2024");
      expect((tooltipFormatter as unknown as (value: number, context: object) => string)(timestamp, {
        seriesIndex: 0,
        dataPointIndex: 0,
      })).toBe("2024-03-01");
      expect((tooltipY?.formatter as unknown as (value: number, context: object) => string)(1.5, {
        seriesIndex: 0,
        dataPointIndex: 0,
      })).toBe("1.5% (daily return: 0.25%)");
    }
  });

  it("generates distinct colors as portfolio count grows", () => {
    const colors: string[] = [];
    for (let index = 0; index < 1024; index += 1) {
      colors.push(portfolioColor(index, colors));
    }
    expect(new Set(colors).size).toBe(colors.length);
    expect(colors.every((color) => /^#[0-9a-f]{6}$/.test(color))).toBe(true);
    expect(colors[7]).not.toBe(colors[384]);
  });

  it("configures a date-based chart with dynamic line colors", () => {
    const options = createChartOptions(["#147a62", "#bb5115"], () => undefined);
    expect(options.chart?.type).toBe("line");
    expect(options.xaxis?.type).toBe("datetime");
    expect(options.colors).toEqual(["#147a62", "#bb5115"]);
    expect(options.yaxis && !Array.isArray(options.yaxis) && options.yaxis.labels?.formatter?.(-1.2)).toBe("-1.2%");
    const tooltipY = Array.isArray(options.tooltip?.y) ? options.tooltip?.y[0] : options.tooltip?.y;
    expect(tooltipY?.formatter?.(5.1)).toBe("5.1%");
  });
});
