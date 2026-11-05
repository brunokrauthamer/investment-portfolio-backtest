# Investment Portfolio Backtesting

Comparing investment strategies across markets takes more than looking up a few index values: the data comes from different sources, follows different calendars, and may be quoted in different currencies. This dashboard brings those histories together so individual investors, students, and other curious users can explore how hypothetical portfolio allocations would have performed over time.

Choose a date range, allocate weights across IBOVESPA, IFIX, Selic, and the S&P 500, and compare the cumulative returns of multiple portfolios on one chart. You can also choose whether to rebalance periodically. Results are historical simulations, not forecasts of future performance.

## Run the app

Install Docker with the Compose plugin and start the Docker engine. From the project root, run:

```sh
docker compose up --build
```

Open [http://localhost:8080](http://localhost:8080). The app uses the included `data/normalized/daily_returns_reais.csv`, which must be present on the host; Docker mounts it read-only for the API. Press `Ctrl+C` to stop the app.

## Key choices

- **A local, modular application:** React and TypeScript provide the interface, with ApexCharts for visualization. A Python/FastAPI backend handles validation and portfolio calculations, and pandas reads and prepares the data. Docker Compose runs the frontend and backend together.
- **Comparable returns in reais:** The source series are transformed into daily returns. S&P 500 returns incorporate USD/BRL exchange-rate changes; the other available series are already based on Brazilian data. The chart shows compounded percentage returns rather than a monetary balance.
- **Explicit portfolio rules:** Allocations must add up to 100%. Asset weights drift with their returns. Rebalancing can be disabled or scheduled every 3 or 6 months, or every 1, 2, or 3 years; the reset takes effect after the first available observation on or after each scheduled date.
- **Separate acquisition from application startup:** Source data and derived returns are stored as CSV files. Starting the app reads the existing returns file and does not contact market-data providers. Acquisition records and source files are kept separately from the derived data.

## Data provenance

| Data | Source and collection method |
| --- | --- |
| **IBOVESPA** | Annual daily-evolution CSV files are downloaded from the endpoint used by [B3's IBOVESPA page](https://sistemaswebb3-listados.b3.com.br/indexStatisticsPage/daily-evolution/IBOV?language=pt-br). The returned data is decoded and saved as B3's original files. |
| **IFIX** | Annual daily-evolution CSV files are obtained in the same way from the endpoint used by [B3's IFIX page](https://sistemaswebb3-listados.b3.com.br/indexStatisticsPage/daily-evolution/IFIX?language=pt-br). |
| **Selic** | A Selenium browser scraper reads the paginated daily effective-rate observations for [Banco Central do Brasil's SGS series 11](https://dadosabertos.bcb.gov.br/dataset/11-taxa-de-juros---selic) and saves them to CSV. |
| **S&P 500** | An HTML scraper reads the date and adjusted-close columns from [Yahoo Finance's `^GSPC` history page](https://finance.yahoo.com/quote/%5EGSPC/history/). The adjusted close should not be assumed to represent a total-return series. See the manifest discrepancy below. |
| **USD/BRL** | The initial exchange-rate history came from a user-supplied CSV attributed to [Investing.com](https://br.investing.com/currencies/usd-brl-historical-data). Its date and price columns were retained for currency conversion; the original retrieval time and usage terms have not been verified. |

Source files, available retrieval details, and checksums are kept under `data/`. B3 downloads and the scraped series use different collection methods; none is fetched when the dashboard starts.

## Known limitations

- Data is not refreshed automatically. USD/BRL has no updater; IFIX, IBOVESPA, and Selic are downloaded in full again when refreshed, then compared with the saved data. The derived returns file must also be regenerated after source updates.
- The S&P 500 source CSV includes an observation for 2026-11-04, but its manifest records coverage only through 2026-11-03 and a different checksum. The manifest does not establish the provenance of the extra observation.
- Source calendars and coverage differ. A missing observation produces a zero return for that series on the affected date, and the latest available USD/BRL price is carried forward when necessary. In particular, S&P 500 currency movement on a date without an index observation is reflected when the next index observation is available. Gaps or stale data can therefore affect results.
- The simulation uses index and rate series as portfolio proxies. It does not model transaction costs, taxes, inflation, or separate dividend cash flows; the available source series determine what is reflected in their values.
- Portfolio comparisons exist only in the current browser session. There are no saved portfolios or user accounts, and IMA-B, maximum drawdown, date shortcuts, and allocation-drift rebalancing are not yet available.
- The backtest is still under development; independent end-to-end QA remains pending.

## What to improve next

1. Add a USD/BRL data getter to update the existing exchange-rate history.
2. Make IFIX, IBOVESPA, and Selic updates incremental, fetching only the data needed to extend the existing history.
3. Replace CSV storage with a relational database.
4. Expand dashboard metrics, including maximum drawdown over the selected period.
5. Add IMA-B as another index available for portfolio allocation.
6. Add date shortcuts such as year to date, one year, and five years.
7. Run data acquisition automatically with a background worker once a day.
8. Let users save and reload portfolios, and add authentication.
9. Support rebalancing when an asset's weight deviates from its target by a chosen threshold.

