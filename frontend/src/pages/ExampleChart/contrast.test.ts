import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { createChartOptions } from "./chart";

function colorFromRule(stylesheet: string, selector: string, property: string): string {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const rule = stylesheet.match(new RegExp(`${escapedSelector}\\s*\\{([^}]*)\\}`));
  const color = rule?.[1]?.match(new RegExp(`\\b${property}:\\s*(#[0-9a-fA-F]{6})\\s*;`));

  if (!color?.[1]) {
    throw new Error(`Could not find ${property} in ${selector}`);
  }

  return color[1];
}

function relativeLuminance(hexColor: string): number {
  const channels = hexColor
    .slice(1)
    .match(/.{2}/g)
    ?.map((channel) => Number.parseInt(channel, 16) / 255);

  if (!channels || channels.length !== 3) {
    throw new Error(`Expected a six-digit hex color, received ${hexColor}`);
  }

  const linear = channels.map((channel) =>
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4,
  );

  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrastRatio(foreground: string | undefined, background: string): number {
  if (!foreground) {
    throw new Error("Expected ApexCharts to configure its axis text color");
  }

  const luminances = [relativeLuminance(foreground), relativeLuminance(background)].sort(
    (left, right) => right - left,
  );

  return (luminances[0] + 0.05) / (luminances[1] + 0.05);
}

const stylesheet = readFileSync(
  resolve(process.cwd(), "src/pages/ExampleChart/index.css"),
  "utf8",
);
const exampleChartOptions = createChartOptions(["#16816f"], () => undefined);
const cardBackground = colorFromRule(stylesheet, ".chart-card", "background");
const axisCaptionColor = colorFromRule(stylesheet, ".chart-axis-caption", "color");
const allocationCardBackground = colorFromRule(stylesheet, ".portfolio-card", "background");
const allocationGuidanceColor = colorFromRule(stylesheet, ".allocation-guidance", "color");
const focusOutline = stylesheet.match(
  /\.percentage-input-label input:focus-visible,[^{]+\{[^}]*outline:\s*3px solid\s*(#[0-9a-fA-F]{6})/,
);

describe("chart text contrast", () => {
  it("keeps axis labels at 4.5:1 or higher on the chart card", () => {
    expect(contrastRatio(exampleChartOptions.chart?.foreColor, cardBackground)).toBeGreaterThanOrEqual(
      4.5,
    );
  });

  it("keeps UTC/unit captions at 4.5:1 or higher on the chart card", () => {
    expect(contrastRatio(axisCaptionColor, cardBackground)).toBeGreaterThanOrEqual(4.5);
  });
});

describe("portfolio controls contrast", () => {
  it("keeps allocation instructions at 4.5:1 or higher on the form card", () => {
    expect(contrastRatio(allocationGuidanceColor, allocationCardBackground)).toBeGreaterThanOrEqual(4.5);
  });

  it("keeps visible keyboard focus at 3:1 or higher on the form card", () => {
    expect(contrastRatio(focusOutline?.[1], allocationCardBackground)).toBeGreaterThanOrEqual(3);
  });
});
