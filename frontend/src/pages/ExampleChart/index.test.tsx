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

const portfolioResult = { series: [{
  name: "Cumulative portfolio return",
  data: [{ x: 1704153600000, y: 1, date: "2024-01-02", daily_return_pct: 1, cumulative_return_pct: 1 }],
}] };

beforeEach(() => {
  vi.mocked(axios.get).mockReset().mockResolvedValue({ data: availableIndexes });
  vi.mocked(axios.post).mockReset().mockResolvedValue({ data: portfolioResult });
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
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));

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
    expect(await screen.findByTestId("apex-chart")).toBeInTheDocument();
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
    expect(screen.queryByTestId("apex-chart")).not.toBeInTheDocument();

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
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));

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
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not calculate/i);
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));
    expect(await screen.findByTestId("apex-chart")).toBeInTheDocument();
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
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));

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
    fireEvent.click(screen.getByRole("button", { name: "Calculate portfolio return" }));

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

  it("shows a clear empty state before the first calculation", () => {
    render(<ExampleChart />);

    expect(
      screen.getByText(/submit a portfolio to calculate its historical return/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("apex-chart")).not.toBeInTheDocument();
  });
});
