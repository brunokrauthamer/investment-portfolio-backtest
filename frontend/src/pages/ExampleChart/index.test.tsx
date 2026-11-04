import type { ApexOptions } from "apexcharts";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ExampleChart from "./index";

vi.mock("react-apexcharts", () => ({
  default: ({
    options,
    series,
    type,
  }: {
    options: ApexOptions;
    series: ApexOptions["series"];
    type: string;
  }) => (
    <div
      data-testid="apex-chart"
      data-xaxis-type={
        (Array.isArray(options.xaxis) ? options.xaxis[0] : options.xaxis)?.type
      }
      data-series={JSON.stringify(series)}
      data-type={type}
    />
  ),
}));

describe("ExampleChart", () => {
  it("renders the labeled line chart and its accessible example values", () => {
    render(<ExampleChart />);

    expect(
      screen.getByRole("heading", { name: /percentage over time/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/illustrative example data/i),
    ).toBeInTheDocument();

    const chart = screen.getByTestId("apex-chart");
    expect(chart).toHaveAttribute("data-type", "line");
    const series = JSON.parse(chart.getAttribute("data-series") ?? "[]") as {
      name: string;
      data: { x: number; y: number }[];
    }[];

    expect(chart).toHaveAttribute("data-xaxis-type", "datetime");
    expect(series[0].data).toHaveLength(6);
    expect(new Date(series[0].data[0].x).toISOString().slice(0, 10)).toBe(
      "2024-01-01",
    );
    expect(series[0].data[2].y).toBe(-1.2);
    expect(series[0].data[5].y).toBe(5.1);

    const summary = screen.getByText(/read the example data/i);
    const details = summary.closest("details");
    expect(details).not.toBeNull();
    fireEvent.click(summary);
    const table = within(details as HTMLDetailsElement).getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(7);
    expect(within(table).getByText("2024-03-01")).toBeInTheDocument();
    expect(within(table).getByText("-1.2%")).toBeInTheDocument();
  });
});
