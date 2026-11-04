import { afterEach, describe, expect, it } from "vitest";
import {
  exampleChartOptions,
  examplePercentageData,
  exampleSeriesData,
  formatPercentage,
  formatUtcDate,
  formatUtcMonth,
} from "./chart";

describe("example percentage chart data", () => {
  const initialTimeZone = process.env.TZ;

  afterEach(() => {
    if (initialTimeZone === undefined) {
      delete process.env.TZ;
    } else {
      process.env.TZ = initialTimeZone;
    }
  });

  it("treats supplied values as percentages, including a negative example", () => {
    expect(formatPercentage(-1.2)).toBe("-1.2%");
    expect(formatPercentage(5.1)).toBe("5.1%");
    expect(exampleSeriesData.map(({ y }) => y)).toEqual([0, 2.5, -1.2, 3.8, 2, 5.1]);
  });

  it("keeps chart date labels and exact tooltip dates on the UTC calendar", () => {
    const marchPoint = exampleSeriesData[2];
    const axisFormatter = exampleChartOptions.xaxis?.labels?.formatter;
    const tooltipFormatter = exampleChartOptions.tooltip?.x?.formatter;

    for (const timeZone of ["America/Sao_Paulo", "America/Los_Angeles", "Asia/Tokyo"]) {
      process.env.TZ = timeZone;
      expect(formatUtcDate(marchPoint.x)).toBe("2024-03-01");
      expect(formatUtcMonth(marchPoint.x)).toBe("Mar 2024");
      expect(axisFormatter?.(String(marchPoint.x), marchPoint.x)).toBe("Mar 2024");
      expect(
        (tooltipFormatter as unknown as (
          value: string,
          context: { dataPointIndex: number },
        ) => string)("", { dataPointIndex: 2 }),
      ).toBe("2024-03-01");
    }

    expect(examplePercentageData.map(({ date }) => date)).toEqual([
      "2024-01-01",
      "2024-02-01",
      "2024-03-01",
      "2024-04-01",
      "2024-05-01",
      "2024-06-01",
    ]);
  });

  it("configures a date based horizontal axis and percentage values in the tooltip", () => {
    expect(exampleChartOptions.chart?.type).toBe("line");
    expect(exampleChartOptions.xaxis?.type).toBe("datetime");
    const yAxis = exampleChartOptions.yaxis;
    expect(Array.isArray(yAxis)).toBe(false);
    const tooltipY = Array.isArray(exampleChartOptions.tooltip?.y)
      ? exampleChartOptions.tooltip.y[0]
      : exampleChartOptions.tooltip?.y;

    expect(
      (yAxis as { labels?: { formatter?: (value: number) => string } }).labels
        ?.formatter?.(-1.2),
    ).toBe("-1.2%");
    expect(tooltipY?.formatter?.(5.1)).toBe("5.1%");
  });
});
