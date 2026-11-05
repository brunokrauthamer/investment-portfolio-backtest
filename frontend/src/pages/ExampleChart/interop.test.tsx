import { fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import ExampleChart from "./index";

vi.mock("react-apexcharts", () => ({
  default: {
    default: () => <div data-testid="wrapped-chart" />,
  },
}));

vi.mock("axios", () => ({
  default: {
    get: vi.fn().mockResolvedValue({
      data: [
        { id: "ibovespa", name: "IBOVESPA" },
        { id: "ifix", name: "IFIX" },
        { id: "selic", name: "Selic" },
        { id: "sp500", name: "S&P 500" },
      ],
    }),
    post: vi.fn().mockResolvedValue({
      data: {
        series: [{
          name: "Cumulative portfolio return",
          data: [{
            x: Date.parse("2020-01-01T00:00:00.000Z"),
            y: 1.25,
            date: "2020-01-01",
            daily_return_pct: 1.25,
            cumulative_return_pct: 1.25,
          }],
        }],
      },
    }),
  },
}));

it("renders the chart after submitting a valid result when the wrapper import is a CommonJS exports object", async () => {
  render(<ExampleChart />);

  await screen.findByRole("heading", { name: /configure your portfolio/i });
  fireEvent.click(screen.getByRole("button", { name: "Add portfolio to chart" }));

  expect(await screen.findByTestId("wrapped-chart")).toBeInTheDocument();
});
