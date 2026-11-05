import axios from "axios";
import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import ExampleChart from "./index";

vi.mock("axios", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

vi.mock("react-apexcharts", () => ({
  default: {
    default: () => <div data-testid="wrapped-chart" />,
  },
}));

it("renders the result when the wrapper import is a CommonJS exports object", async () => {
  vi.mocked(axios.get).mockResolvedValue({ data: [
    { id: "ibovespa", name: "IBOVESPA" },
    { id: "ifix", name: "IFIX" },
    { id: "selic", name: "Selic" },
    { id: "sp500", name: "S&P 500" },
  ] });
  vi.mocked(axios.post).mockResolvedValue({ data: { series: [{
    name: "Cumulative portfolio return",
    data: [{ x: 1704153600000, y: 1, date: "2024-01-02", daily_return_pct: 1, cumulative_return_pct: 1 }],
  }] } });
  render(<ExampleChart />);

  fireEvent.click(await screen.findByRole("button", { name: "Calculate portfolio return" }));

  expect(await screen.findByTestId("wrapped-chart")).toBeInTheDocument();
});
