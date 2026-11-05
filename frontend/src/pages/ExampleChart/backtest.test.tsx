import type { ApexOptions } from "apexcharts";
import axios from "axios";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ExampleChart from "./index";

vi.mock("axios", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

vi.mock("react-apexcharts", () => ({
  default: ({
    series,
  }: {
    options: ApexOptions;
    series: ApexOptions["series"];
    type: string;
  }) => <div data-testid="apex-chart" data-series={JSON.stringify(series)} />,
}));

const indexes = [
  { id: "ibovespa", name: "IBOVESPA" },
  { id: "ifix", name: "IFIX" },
  { id: "selic", name: "Selic" },
  { id: "sp500", name: "S&P 500" },
];

const resultSeries = [{
  name: "Cumulative portfolio return",
  data: [{
    x: 1704153600000,
    y: 1,
    date: "2024-01-02",
    daily_return_pct: 1,
    cumulative_return_pct: 1,
  }],
}];

beforeEach(() => {
  vi.mocked(axios.get).mockReset().mockResolvedValue({ data: indexes });
  vi.mocked(axios.post).mockReset().mockResolvedValue({ data: { series: resultSeries } });
});

afterEach(() => cleanup());

describe("portfolio backtest chart", () => {
  it("prefills the requested dates and has no fictional chart before calculation", async () => {
    render(<ExampleChart />);

    expect(await screen.findByRole("heading", { name: /configure your portfolio/i })).toBeInTheDocument();
    expect(screen.getByLabelText("Initial date")).toHaveValue("2011-01-04");
    expect(screen.getByLabelText("End date")).toHaveValue("2026-10-30");
    expect(screen.queryByTestId("apex-chart")).not.toBeInTheDocument();
    expect(screen.getByText(/submit a portfolio to calculate its historical return/i)).toBeInTheDocument();
  });

  it("passes the response series and chart points directly to ApexCharts", async () => {
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));

    await waitFor(() => expect(axios.post).toHaveBeenCalledWith("/api/portfolio", expect.any(Object)));
    const chart = await screen.findByTestId("apex-chart");
    expect(JSON.parse(chart.getAttribute("data-series") ?? "[]")).toEqual(resultSeries);
    expect(screen.getByText(/2024-01-02/)).toBeInTheDocument();
    expect(document.querySelector(".result-summary")).toHaveTextContent(/Daily return: 1%/);
    expect(document.querySelector(".result-summary")).toHaveTextContent(/Cumulative return: 1%/);
  });

  it("shows a no-data message when the range contains no CSV dates", async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({ data: { series: [{
      name: "Cumulative portfolio return",
      data: [],
    }] } });
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));

    expect(await screen.findByText(/no available data dates fall within this range/i)).toBeInTheDocument();
    expect(screen.queryByTestId("apex-chart")).not.toBeInTheDocument();
  });

  it("clears the previous result when submitted settings change", async () => {
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));
    expect(await screen.findByTestId("apex-chart")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2025-10-30" } });

    expect(screen.queryByTestId("apex-chart")).not.toBeInTheDocument();
    expect(screen.queryByText(/cumulative return: 1%/i)).not.toBeInTheDocument();
  });

  it("shows a submission error without rendering a chart or success message", async () => {
    vi.mocked(axios.post).mockRejectedValueOnce(new Error("Unavailable"));
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not calculate/i);
    expect(screen.queryByTestId("apex-chart")).not.toBeInTheDocument();
    expect(screen.queryByText(/calculated successfully/i)).not.toBeInTheDocument();
  });

  it("rejects a malformed portfolio response without treating it as empty data", async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({ data: { series: [{
      name: "Cumulative portfolio return",
      data: [{ x: "not-a-timestamp", y: "not-a-number" }],
    }] } as never });
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not calculate/i);
    expect(screen.queryByText(/no available data dates fall within this range/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId("apex-chart")).not.toBeInTheDocument();
  });
});
