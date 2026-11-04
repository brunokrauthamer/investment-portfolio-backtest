# Daily returns in reais — specification s001

Status: proposed for approval; no implementation is approved.

## Goal and scope

Add an explicitly invoked local service in `market_data_normalizer` that reads `data/normalized/gathered_data.csv` and the prepared USD/BRL source CSV, and publishes `data/normalized/daily_returns_reais.csv`. Accept an optional data root for isolated use. Generate the project output as part of delivery. No acquisition, source modification, backtest, API or frontend behavior is included.

## Acceptance criteria

- **AC-001 — Input and output:** Read the gathered CSV's `date,ibovespa,ifix,selic,sp500` columns and the USD/BRL source's `Data,price` columns. Output exactly `date,ibovespa,ifix,selic,sp500`, ascending ISO dates from the gathered table, excluding its first row. Do not add dates appearing only in the currency source. Dates are unique. Output numeric decimal returns rather than percentages.
- **AC-002 — Brazilian index returns:** For a present IBOVESPA or IFIX observation, calculate current points divided by its most recent earlier available points minus one. A missing current observation yields zero, without resetting the last available points. This includes the user's 2011-03-07/08 gap and 2011-03-09 against 2011-03-04.
- **AC-003 — Selic:** Divide each present daily Selic percentage by 100; a missing observation yields zero.
- **AC-004 — S&P and currency:** For a present S&P observation, combine S&P and USD/BRL variations as `(1 + currency_return) * (1 + sp500_return) - 1`. Use the most recent earlier S&P observation as the index baseline, and its corresponding USD/BRL price as the currency baseline. A date's corresponding USD/BRL price is its same-day price or, if missing, the most recent earlier available price. A missing S&P observation yields zero even when the currency changes. Therefore the next S&P observation includes currency movement since the previous S&P observation, including changes during S&P gaps.
- **AC-005 — Example:** Using the user's 2011-01-03 and 2011-01-04 inputs, calculate the 2011-01-04 returns to normal numerical tolerance, including IBOVESPA approximately 0.00508087782108979, IFIX approximately -0.00854052002277483, Selic 0.00040203, and S&P in reais approximately 0.00717869311278152.
- **AC-006 — Starts, input integrity and safety:** If a current index observation lacks an earlier observation for its index, output zero for that index. If a current S&P observation or its previous S&P observation has no corresponding available currency price, output zero for S&P until a calculation is possible. Always retain present observations as future baselines, even when their return is zero. The first gathered row is omitted from the output but is available as an earlier observation. Reject missing, malformed, invalid, duplicate or unsorted gathered dates, invalid or duplicate currency dates, incompatible schemas, non-finite values, nonpositive index or currency levels, and missing input files without replacing an existing output. Source files remain read-only. Stage output in the destination directory and publish atomically.
- **AC-007 — Interface and documentation:** Provide an explicit Python entry point with optional data root, independent of the caller's working directory. Imports cause no file or network side effects. Document invocation, formulas, gap conventions and limitations in the normalizer README and architecture guidance. No new dependency is anticipated.

## User decisions

On 2026-11-04 the user decided that a missing S&P observation yields zero even if a currency observation is available; when S&P resumes, the currency baseline is the rate associated with the last S&P observation. If there is no prior index price or usable currency, output zero until calculable. These decisions were relayed by the main chat.

The current actual data contains 102 gathered dates with missing S&P but an available exchange rate; 2011-01-17 is an example. It also has one S&P observation without a same-day exchange rate, on 2026-11-04, for which an earlier rate exists. The current series all start on 2011-01-03; future inputs can differ.

## Boundaries

These are requested conventions for this derived CSV, not a general decision about portfolio accounting, dividends, taxation or calendar alignment in future backtests. Invalid input is distinguished from a genuinely blank observation. No synthetic market data is introduced.
