import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import ExampleChart from "./index";

vi.mock("react-apexcharts", () => ({
  default: {
    default: () => <div data-testid="wrapped-chart" />,
  },
}));

it("renders the chart when the wrapper import is a CommonJS exports object", () => {
  render(<ExampleChart />);
  expect(screen.getByTestId("wrapped-chart")).toBeInTheDocument();
});
