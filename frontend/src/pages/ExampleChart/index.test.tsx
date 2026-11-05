import type { ApexOptions } from "apexcharts";
import axios from "axios";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ExampleChart from "./index";

vi.mock("axios", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

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
      data-colors={JSON.stringify(options.colors)}
      data-xaxis-type={
        (Array.isArray(options.xaxis) ? options.xaxis[0] : options.xaxis)?.type
      }
      data-series={JSON.stringify(series)}
      data-type={type}
    />
  ),
}));

const availableIndexes = [
  { id: "ibovespa", name: "IBOVESPA" },
  { id: "ifix", name: "IFIX" },
  { id: "selic", name: "Selic" },
  { id: "sp500", name: "S&P 500" },
];

function responseWithPoint(y: number, date = "2020-01-01", dailyReturn = y) {
  return {
    series: [{
      name: "Cumulative portfolio return",
      data: [{
        x: Date.parse(`${date}T00:00:00.000Z`),
        y,
        date,
        daily_return_pct: dailyReturn,
        cumulative_return_pct: y,
      }],
    }],
  };
}

beforeEach(() => {
  vi.mocked(axios.get).mockReset().mockResolvedValue({ data: availableIndexes });
  vi.mocked(axios.post).mockReset().mockResolvedValue({ data: responseWithPoint(1.25) });
});

afterEach(() => cleanup());

describe("ExampleChart", () => {
  it("loads backend indexes and starts with a visible equal 100% allocation", async () => {
    render(<ExampleChart />);

    expect(await screen.findByRole("heading", { name: /configure your portfolio/i })).toBeInTheDocument();
    expect(axios.get).toHaveBeenCalledWith("/api/indexes");
    expect(Number((screen.getByLabelText("IBOVESPA allocation percentage") as HTMLInputElement).value)).toBe(25);
    expect(Number((screen.getByLabelText("IFIX allocation percentage") as HTMLInputElement).value)).toBe(25);
    expect(Number((screen.getByLabelText("Selic allocation percentage") as HTMLInputElement).value)).toBe(25);
    expect(Number((screen.getByLabelText("S&P 500 allocation percentage") as HTMLInputElement).value)).toBe(25);
    expect(screen.getByText("100.00%")).toBeInTheDocument();
  });

  it("lets users select just one index or split between two", async () => {
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.change(screen.getByLabelText("IBOVESPA allocation percentage"), { target: { value: "0" } });
    expect(Number((screen.getByLabelText("IBOVESPA allocation percentage") as HTMLInputElement).value)).toBe(0);
    expect(screen.getByText("100.00%")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("IFIX allocation percentage"), { target: { value: "12.345" } });
    expect(screen.getByRole("alert")).toHaveTextContent(/at most two decimal places/i);
    expect(screen.getByText("100.00%")).toBeInTheDocument();
    fireEvent.blur(screen.getByLabelText("IFIX allocation percentage"));

    fireEvent.click(screen.getByLabelText("Include IBOVESPA"));
    expect(Number((screen.getByLabelText("IFIX allocation percentage") as HTMLInputElement).value)).toBe(33.34);
    fireEvent.click(screen.getByLabelText("Include Selic"));
    fireEvent.click(screen.getByLabelText("Include S&P 500"));
    expect(Number((screen.getByLabelText("IFIX allocation percentage") as HTMLInputElement).value)).toBe(100);
    expect(screen.getByText("100.00%")).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText("Include S&P 500"));
    expect(Number((screen.getByLabelText("IFIX allocation percentage") as HTMLInputElement).value)).toBe(50);
    expect(Number((screen.getByLabelText("S&P 500 allocation percentage") as HTMLInputElement).value)).toBe(50);
    expect(screen.getByText("100.00%")).toBeInTheDocument();
  });

  it("supports decimal shares with locks and submits exact dates and strategy", async () => {
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    const setShare = (name: string, value: string) => {
      fireEvent.change(screen.getByLabelText(`${name} allocation percentage`), { target: { value } });
    };
    setShare("IBOVESPA", "12.34");
    fireEvent.click(screen.getByLabelText("Lock IBOVESPA allocation"));
    setShare("IFIX", "23.45");
    fireEvent.click(screen.getByLabelText("Lock IFIX allocation"));
    setShare("Selic", "34.56");
    fireEvent.click(screen.getByLabelText("Lock Selic allocation"));
    expect(Number((screen.getByLabelText("S&P 500 allocation percentage") as HTMLInputElement).value)).toBe(29.65);
    expect(screen.getByText("100.00%")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Initial date"), { target: { value: "2020-01-01" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2024-12-31" } });
    fireEvent.change(screen.getByLabelText("Rebalancing strategy"), { target: { value: "6_months" } });
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

    await waitFor(() => expect(axios.post).toHaveBeenCalledWith("/api/portfolio", {
      initial_date: "2020-01-01",
      end_date: "2024-12-31",
      allocations: [
        { index: "ibovespa", percentage: 12.34 },
        { index: "ifix", percentage: 23.45 },
        { index: "selic", percentage: 34.56 },
        { index: "sp500", percentage: 29.65 },
      ],
      rebalancing: "6_months",
    }));
    expect(await screen.findByText("Added Portfolio 1.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Portfolio 1" })).toBeInTheDocument();
    expect(screen.getByLabelText("Initial date")).toHaveValue("2011-01-04");
    expect(screen.getByLabelText("End date")).toHaveValue("2026-10-30");
    expect(screen.getByLabelText("Rebalancing strategy")).toHaveValue("none");
  });

  it("shows committed shares in all fields after another share redistributes them", async () => {
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    const ibovespa = screen.getByLabelText("IBOVESPA allocation percentage");
    const ifix = screen.getByLabelText("IFIX allocation percentage");
    fireEvent.change(ibovespa, { target: { value: "40" } });
    fireEvent.blur(ibovespa);
    fireEvent.change(ifix, { target: { value: "50" } });
    fireEvent.blur(ifix);

    expect(Number((screen.getByLabelText("IBOVESPA allocation percentage") as HTMLInputElement).value)).toBe(25);
    expect(Number((screen.getByLabelText("IFIX allocation percentage") as HTMLInputElement).value)).toBe(50);
    expect(Number((screen.getByLabelText("Selic allocation percentage") as HTMLInputElement).value)).toBe(12.5);
    expect(Number((screen.getByLabelText("S&P 500 allocation percentage") as HTMLInputElement).value)).toBe(12.5);
    expect(screen.getByText("100.00%")).toBeInTheDocument();
  });

  it("does not submit while an invalid percentage draft is active", async () => {
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.change(screen.getByLabelText("Initial date"), { target: { value: "2020-01-01" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2024-12-31" } });
    fireEvent.change(screen.getByLabelText("IFIX allocation percentage"), { target: { value: "101" } });
    fireEvent.submit(document.querySelector("form") as HTMLFormElement);

    expect(axios.post).not.toHaveBeenCalled();
    expect(screen.getByText(/at most two decimal places/i)).toHaveAttribute("role", "alert");
    expect(screen.queryByText(/added portfolio/i)).not.toBeInTheDocument();

    fireEvent.blur(screen.getByLabelText("IFIX allocation percentage"));
    expect(Number((screen.getByLabelText("IFIX allocation percentage") as HTMLInputElement).value)).toBe(25);
  });

  it("offers each supported rebalancing interval and permits an equal date range", async () => {
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    const strategy = screen.getByLabelText("Rebalancing strategy");
    expect(within(strategy).getAllByRole("option").map((option) => (option as HTMLOptionElement).value)).toEqual([
      "none", "3_months", "6_months", "1_year", "2_years", "3_years",
    ]);
    fireEvent.change(screen.getByLabelText("Initial date"), { target: { value: "2024-01-01" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2024-01-01" } });
    expect((document.querySelector("form") as HTMLFormElement).checkValidity()).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

    await waitFor(() => expect(axios.post).toHaveBeenCalledWith("/api/portfolio", {
      initial_date: "2024-01-01",
      end_date: "2024-01-01",
      allocations: availableIndexes.map(({ id }) => ({ index: id, percentage: 25 })),
      rebalancing: "none",
    }));
  });

  it("allows retry after an unsuccessful portfolio submission", async () => {
    vi.mocked(axios.post).mockRejectedValueOnce(new Error("Offline"));
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.change(screen.getByLabelText("Initial date"), { target: { value: "2020-01-01" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2024-12-31" } });
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not submit/i);
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));
    expect(await screen.findByText("Added Portfolio 1.")).toBeInTheDocument();
    expect(screen.getByLabelText("Initial date")).toHaveValue("2011-01-04");
    expect(screen.getByLabelText("End date")).toHaveValue("2026-10-30");
    expect(axios.post).toHaveBeenCalledTimes(2);
  });

  it("rejects an unexpected index response instead of filling with fallback data", async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({
      data: [{ id: "fake", name: "Invented index" }],
    } as never);
    render(<ExampleChart />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not load indexes/i);
    expect(screen.queryByText("Invented index")).not.toBeInTheDocument();
  });

  it("reports invalid and reversed date ranges without submitting", async () => {
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.change(screen.getByLabelText("Initial date"), { target: { value: "2024-12-31" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2020-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/initial date must be on or before/i);
    expect(axios.post).not.toHaveBeenCalled();
  });

  it("requires both date values before submission", async () => {
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.change(screen.getByLabelText("Initial date"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "" } });
    expect((screen.getByLabelText("Initial date") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("End date") as HTMLInputElement).value).toBe("");
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

    expect(screen.getByRole("alert")).toHaveTextContent(/enter a valid initial date and end date/i);
    expect(axios.post).not.toHaveBeenCalled();
  });

  it("shows a retry action when the available indexes cannot be loaded", async () => {
    vi.mocked(axios.get).mockRejectedValueOnce(new Error("Offline"));
    render(<ExampleChart />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not load indexes/i);
    expect(screen.queryByLabelText("IBOVESPA allocation percentage")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /retry loading indexes/i }));
    expect(await screen.findByRole("heading", { name: /configure your portfolio/i })).toBeInTheDocument();
    expect(axios.get).toHaveBeenCalledTimes(2);
  });

  it("starts without example data or a production example table", async () => {
    render(<ExampleChart />);

    expect(screen.getByRole("heading", { name: /cumulative return over time/i })).toBeInTheDocument();
    expect(screen.getByText(/submit a portfolio to add its results/i)).toBeInTheDocument();
    expect(await screen.findByText(/successful submissions will appear here/i)).toBeInTheDocument();
    expect(screen.queryByTestId("apex-chart")).not.toBeInTheDocument();
    expect(screen.queryByText(/illustrative example data/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("appends real series and configuration snapshots, resets after success, and keeps labels and colors after removal", async () => {
    const firstResponse = responseWithPoint(2.75, "2021-03-04", 1.25);
    const secondResponse = responseWithPoint(10.125, "2023-05-06", -0.5);
    vi.mocked(axios.post)
      .mockResolvedValueOnce({ data: firstResponse })
      .mockResolvedValueOnce({ data: secondResponse });
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.change(screen.getByLabelText("Initial date"), { target: { value: "2020-02-03" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2021-03-04" } });
    fireEvent.change(screen.getByLabelText("Rebalancing strategy"), { target: { value: "6_months" } });
    fireEvent.click(screen.getByLabelText("Include IFIX"));
    fireEvent.click(screen.getByLabelText("Include Selic"));
    fireEvent.click(screen.getByLabelText("Include S&P 500"));
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

    expect(await screen.findByText("Added Portfolio 1.")).toBeInTheDocument();
    const firstCard = screen.getByRole("heading", { name: "Portfolio 1" }).closest("[role='listitem']");
    expect(firstCard).not.toBeNull();
    expect(within(firstCard as HTMLElement).getByText("2020-02-03 – 2021-03-04")).toBeInTheDocument();
    expect(within(firstCard as HTMLElement).getByText("6 months")).toBeInTheDocument();
    expect(within(firstCard as HTMLElement).getByText("IBOVESPA: 100.00%")).toBeInTheDocument();
    expect(screen.getByLabelText("Initial date")).toHaveValue("2011-01-04");
    expect(screen.getByLabelText("End date")).toHaveValue("2026-10-30");
    expect(screen.getByLabelText("IFIX allocation percentage")).toHaveValue("25.00");

    fireEvent.change(screen.getByLabelText("Initial date"), { target: { value: "2022-04-05" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2023-05-06" } });
    fireEvent.change(screen.getByLabelText("Rebalancing strategy"), { target: { value: "3_years" } });
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

    expect(await screen.findByRole("heading", { name: "Portfolio 2" })).toBeInTheDocument();
    expect(screen.getByText("2022-04-05 – 2023-05-06")).toBeInTheDocument();
    expect(within(firstCard as HTMLElement).getByText("2020-02-03 – 2021-03-04")).toBeInTheDocument();
    expect(within(firstCard as HTMLElement).getByText("6 months")).toBeInTheDocument();
    expect(within(firstCard as HTMLElement).getByText("IBOVESPA: 100.00%")).toBeInTheDocument();
    const chart = screen.getByTestId("apex-chart");
    expect(chart).toHaveAttribute("data-xaxis-type", "datetime");
    const series = JSON.parse(chart.getAttribute("data-series") ?? "[]") as {
      name: string;
      data: { x: number; y: number }[];
    }[];
    const colors = JSON.parse(chart.getAttribute("data-colors") ?? "[]") as string[];
    expect(series).toEqual([
      { name: "Portfolio 1", data: [{ x: firstResponse.series[0].data[0].x, y: 2.75 }] },
      { name: "Portfolio 2", data: [{ x: secondResponse.series[0].data[0].x, y: 10.125 }] },
    ]);
    expect(colors).toHaveLength(2);
    expect(new Set(colors).size).toBe(2);

    fireEvent.click(screen.getByRole("button", { name: "Remove Portfolio 1" }));
    const remainingSeries = JSON.parse(screen.getByTestId("apex-chart").getAttribute("data-series") ?? "[]") as {
      name: string;
      data: { x: number; y: number }[];
    }[];
    const remainingColors = JSON.parse(screen.getByTestId("apex-chart").getAttribute("data-colors") ?? "[]") as string[];
    expect(remainingSeries).toEqual([
      { name: "Portfolio 2", data: [{ x: secondResponse.series[0].data[0].x, y: 10.125 }] },
    ]);
    expect(remainingColors).toEqual([colors[1]]);
    expect(screen.queryByRole("heading", { name: "Portfolio 1" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));
    expect(await screen.findByRole("heading", { name: "Portfolio 3" })).toBeInTheDocument();
    const afterNextSuccess = screen.getByTestId("apex-chart");
    const afterNextColors = JSON.parse(afterNextSuccess.getAttribute("data-colors") ?? "[]") as string[];
    const afterNextSeries = JSON.parse(afterNextSuccess.getAttribute("data-series") ?? "[]") as { name: string }[];
    expect(afterNextSeries.map(({ name }) => name)).toEqual(["Portfolio 2", "Portfolio 3"]);
    expect(afterNextColors[0]).toBe(colors[1]);
  });

  it("adds an empty result and explains that no points were returned", async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({
      data: { series: [{ name: "Cumulative portfolio return", data: [] }] },
    });
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

    expect(await screen.findByRole("heading", { name: "Portfolio 1" })).toBeInTheDocument();
    expect(screen.getByText(/no data points were returned for this portfolio/i)).toBeInTheDocument();
    expect(screen.getByText(/submitted portfolios returned no data points/i)).toBeInTheDocument();
  });

  it("rejects an acknowledgement and preserves submitted values", async () => {
    vi.mocked(axios.post).mockResolvedValueOnce({ data: { status: "ok" } });
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    fireEvent.change(screen.getByLabelText("Initial date"), { target: { value: "2021-04-03" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2022-06-05" } });
    fireEvent.change(screen.getByLabelText("Rebalancing strategy"), { target: { value: "1_year" } });
    fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/invalid cumulative-return series/i);
    expect(screen.getByLabelText("Initial date")).toHaveValue("2021-04-03");
    expect(screen.getByLabelText("End date")).toHaveValue("2022-06-05");
    expect(screen.getByLabelText("Rebalancing strategy")).toHaveValue("1_year");
    expect(screen.queryByRole("heading", { name: "Portfolio 1" })).not.toBeInTheDocument();
  });

  it("communicates loading and prevents duplicate submissions", async () => {
    let resolveRequest: ((value: { data: ReturnType<typeof responseWithPoint> }) => void) | undefined;
    vi.mocked(axios.post).mockImplementationOnce(() => new Promise((resolve) => {
      resolveRequest = resolve as (value: { data: ReturnType<typeof responseWithPoint> }) => void;
    }) as never);
    render(<ExampleChart />);

    await screen.findByRole("heading", { name: /configure your portfolio/i });
    const button = screen.getByRole("button", { name: "Add portfolio to chart" });
    fireEvent.click(button);
    expect(screen.getByRole("button", { name: "Adding portfolio…" })).toBeDisabled();
    fireEvent.submit(document.querySelector("form") as HTMLFormElement);
    expect(axios.post).toHaveBeenCalledTimes(1);

    resolveRequest?.({ data: responseWithPoint(4) });
    expect(await screen.findByRole("heading", { name: "Portfolio 1" })).toBeInTheDocument();
  });
});
