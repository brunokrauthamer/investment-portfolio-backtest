import ChartImport from "react-apexcharts";
import {
  exampleChartOptions,
  examplePercentageData,
  exampleSeries,
  formatPercentage,
} from "./chart";
import "./index.css";

// Vite may expose the pinned CommonJS wrapper's exports object as its default.
function resolveChartComponent(value: unknown): typeof ChartImport {
  if (typeof value === "function") return value as typeof ChartImport;
  if (value !== null && typeof value === "object" && "default" in value &&
      typeof value.default === "function") {
    return value.default as typeof ChartImport;
  }
  throw new Error("Unsupported react-apexcharts module shape: expected a component or callable default.");
}

const ReactApexChart = resolveChartComponent(ChartImport);

export function ExampleChart() {
  return (
    <main className="chart-page">
      <section aria-labelledby="page-title" className="chart-card">
        <header className="chart-header">
          <div className="chart-heading-group">
            <span className="chart-eyebrow">Visual demo</span>
            <h1 id="page-title">Percentage over time</h1>
            <p className="chart-description" id="chart-description">
              A simple line chart plotted against UTC calendar dates.
            </p>
          </div>
          <div aria-label="Date range: January through June 2024" className="date-range">
            <span className="date-range-label">Example period</span>
            <span className="date-range-value">Jan – Jun 2024</span>
          </div>
        </header>

        <figure
          aria-describedby="chart-description"
          aria-label="Illustrative percentage line chart. Open the example data table for exact dates and values."
          className="chart-figure"
          role="img"
        >
          <div className="chart-container">
            <ReactApexChart
              height={320}
              options={exampleChartOptions}
              series={exampleSeries}
              type="line"
              width="100%"
            />
          </div>
          <figcaption className="chart-axis-caption">
            <span>Dates shown in UTC</span>
            <span>Percentage</span>
          </figcaption>
        </figure>

        <footer className="chart-footer">
          <p className="data-notice">
            <span aria-hidden="true" className="notice-dot" />
            <span>
              <strong>Illustrative example data.</strong> These values are for
              display only and are not actual market performance.
            </span>
          </p>

          <details className="example-data">
            <summary>Read the example data</summary>
            <div className="example-data-table-wrap">
              <table>
                <caption className="visually-hidden">
                  Illustrative example percentage values by UTC date
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Date (UTC)</th>
                    <th scope="col">Example percentage</th>
                  </tr>
                </thead>
                <tbody>
                  {examplePercentageData.map(({ date, value }) => (
                    <tr key={date}>
                      <td>{date}</td>
                      <td>{formatPercentage(value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </footer>
      </section>

      <footer className="page-footer">
        Sample values are fictional and carry no financial interpretation.
      </footer>
    </main>
  );
}

export default ExampleChart;
