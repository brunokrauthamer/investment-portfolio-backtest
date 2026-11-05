import { useEffect, useState, type FormEvent } from "react";
import ChartImport from "react-apexcharts";
import {
  exampleChartOptions,
  examplePercentageData,
  exampleSeries,
  formatPercentage as formatChartPercentage,
} from "./chart";
import {
  equalAllocations,
  formatPercentage,
  FULL_ALLOCATION,
  reallocate,
  type AllocationLine,
} from "./allocation";
import {
  fetchIndexes,
  submitPortfolio,
  type IndexOption,
  type RebalancingStrategy,
} from "../../services/portfolio";
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
const strategies: { value: RebalancingStrategy; label: string }[] = [
  { value: "none", label: "None" },
  { value: "3_months", label: "3 months" },
  { value: "6_months", label: "6 months" },
  { value: "1_year", label: "1 year" },
  { value: "2_years", label: "2 years" },
  { value: "3_years", label: "3 years" },
];

function isCalendarDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00.000Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function parsePercentage(value: string): number | null {
  if (!/^\d{1,3}(?:\.\d{0,2})?$/.test(value)) return null;
  const percentage = Number(value);
  if (!Number.isFinite(percentage) || percentage < 0 || percentage > 100) return null;
  return Math.round(percentage * 100);
}

export function ExampleChart() {
  const [indexes, setIndexes] = useState<IndexOption[] | null>(null);
  const [allocations, setAllocations] = useState<AllocationLine[]>([]);
  const [loadVersion, setLoadVersion] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [initialDate, setInitialDate] = useState("2011-01-04");
  const [endDate, setEndDate] = useState("2026-10-30");
  const [rebalancing, setRebalancing] = useState<RebalancingStrategy>("none");
  const [activeDraft, setActiveDraft] = useState<{ indexId: IndexOption["id"]; value: string } | null>(null);
  const [shareError, setShareError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [acknowledgement, setAcknowledgement] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setLoadError(null);

    void fetchIndexes()
      .then((loadedIndexes) => {
        if (cancelled) return;
        setIndexes(loadedIndexes);
        setAllocations(equalAllocations(loadedIndexes));
        setActiveDraft(null);
      })
      .catch(() => {
        if (!cancelled) {
          setIndexes(null);
          setAllocations([]);
          setLoadError("Could not load indexes. Check your connection and try again.");
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => { cancelled = true; };
  }, [loadVersion]);

  const resetResponseState = () => {
    setAcknowledgement(false);
    setFormError(null);
  };

  const selectedCount = allocations.length;
  const totalHundredths = allocations.reduce((sum, line) => sum + line.hundredths, 0);
  const hasEditablePeer = (changedId: IndexOption["id"]) => allocations.some(
    ({ index, locked }) => index.id !== changedId && !locked,
  );
  const lockedHundredths = (changedId: IndexOption["id"]) => allocations.reduce(
    (sum, line) => line.index.id !== changedId && line.locked ? sum + line.hundredths : sum,
    0,
  );

  const toggleIndex = (index: IndexOption) => {
    if (!indexes) return;
    const currentSelected = new Set(allocations.map(({ index: selected }) => selected.id));
    if (currentSelected.has(index.id)) {
      if (currentSelected.size === 1) return;
      currentSelected.delete(index.id);
    } else {
      currentSelected.add(index.id);
    }
    const selected = indexes.filter(({ id }) => currentSelected.has(id));
    setAllocations(equalAllocations(selected));
    setActiveDraft(null);
    setShareError(null);
    resetResponseState();
  };

  const updateShare = (indexId: IndexOption["id"], requestedHundredths: number) => {
    const next = reallocate(allocations, indexId, requestedHundredths);
    if (next === allocations) {
      setShareError("This value does not fit with the locked shares. Unlock a share or enter a lower percentage.");
      resetResponseState();
      return;
    }
    setAllocations(next);
    setShareError(null);
    resetResponseState();
  };

  const setShareDraft = (indexId: IndexOption["id"], rawValue: string) => {
    setActiveDraft({ indexId, value: rawValue });
    const parsed = parsePercentage(rawValue);
    if (parsed === null) {
      setShareError("Enter a percentage from 0 to 100 with at most two decimal places.");
      resetResponseState();
      return;
    }
    updateShare(indexId, parsed);
  };

  const toggleLock = (indexId: IndexOption["id"], locked: boolean) => {
    setAllocations((current) => current.map((line) => line.index.id === indexId
      ? { ...line, locked }
      : line));
    resetResponseState();
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAcknowledgement(false);
    setFormError(null);
    if (activeDraft) {
      const line = allocations.find(({ index }) => index.id === activeDraft.indexId);
      const draftHundredths = parsePercentage(activeDraft.value);
      if (!line || draftHundredths === null || draftHundredths !== line.hundredths) {
        return;
      }
    }
    if (!isCalendarDate(initialDate) || !isCalendarDate(endDate)) {
      setFormError("Enter a valid initial date and end date.");
      return;
    }
    if (initialDate > endDate) {
      setFormError("Initial date must be on or before the end date.");
      return;
    }
    if (totalHundredths !== FULL_ALLOCATION || allocations.length === 0) {
      setFormError("Adjust the selected indexes so their total is exactly 100.00%.");
      return;
    }

    setIsSubmitting(true);
    try {
      await submitPortfolio({
        initial_date: initialDate,
        end_date: endDate,
        allocations: allocations.map(({ index, hundredths }) => ({
          index: index.id,
          percentage: hundredths / 100,
        })),
        rebalancing,
      });
      setAcknowledgement(true);
    } catch {
      setFormError("Could not submit the settings. Check your connection and try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="chart-page">
      <div className="portfolio-workspace">
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
                        <td>{formatChartPercentage(value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </footer>
        </section>

        <section aria-labelledby="portfolio-heading" className="portfolio-card">
          <header className="portfolio-header">
            <span className="chart-eyebrow">Portfolio setup</span>
            <h2 id="portfolio-heading">Configure your portfolio</h2>
            <p>Choose the indexes, dates and rebalancing interval to submit.</p>
          </header>

          {isLoading && (
            <p aria-live="polite" className="form-message form-message-loading">Loading available indexes…</p>
          )}
          {loadError && (
            <div className="form-load-error">
              <p role="alert" className="form-message form-message-error">{loadError}</p>
              <button type="button" className="retry-button" onClick={() => setLoadVersion((value) => value + 1)}>
                Retry loading indexes
              </button>
            </div>
          )}

          {indexes && !isLoading && (
            <form aria-labelledby="portfolio-heading" className="portfolio-form" onChange={resetResponseState} onSubmit={handleSubmit}>
              <fieldset className="allocation-fieldset" disabled={isSubmitting}>
                <legend>
                  <span>Index allocation</span>
                  <span aria-live="polite" className="allocation-total">
                    {formatPercentage(totalHundredths)}%
                  </span>
                </legend>
                <p className="allocation-guidance">
                  The total always stays at 100%. Adjust another selected share or lock shares to set a precise mix.
                  Changing which indexes are selected resets them to equal shares.
                </p>
                {indexes.map((index) => {
                  const line = allocations.find(({ index: selected }) => selected.id === index.id);
                  const selected = line !== undefined;
                  const isEditable = selected && !line.locked && selectedCount > 1 && hasEditablePeer(index.id);
                  const amount = line?.hundredths ?? 0;
                  return (
                    <div className={`allocation-row${selected ? " is-selected" : ""}`} key={index.id}>
                      <div className="allocation-row-heading">
                        <label className="index-choice">
                          <input
                            aria-label={`Include ${index.name}`}
                            checked={selected}
                            disabled={isSubmitting || (selected && selectedCount === 1)}
                            onChange={() => toggleIndex(index)}
                            type="checkbox"
                          />
                          <span>{index.name}</span>
                        </label>
                        {selected && (
                          <label className="allocation-lock">
                            <input
                              aria-label={`Lock ${index.name} allocation`}
                              checked={line.locked}
                              disabled={isSubmitting || selectedCount === 1}
                              onChange={(event) => toggleLock(index.id, event.currentTarget.checked)}
                              type="checkbox"
                            />
                            <span>Lock</span>
                          </label>
                        )}
                      </div>
                      {selected && (
                        <div className="allocation-control">
                          <label className="visually-hidden" htmlFor={`allocation-slider-${index.id}`}>
                            {index.name} allocation slider
                          </label>
                          <input
                            aria-label={`${index.name} allocation slider`}
                            className="allocation-slider"
                            disabled={!isEditable}
                            id={`allocation-slider-${index.id}`}
                            max={formatPercentage(FULL_ALLOCATION - lockedHundredths(index.id))}
                            min="0"
                            onChange={(event) => {
                              const parsed = parsePercentage(event.currentTarget.value);
                              if (parsed !== null) updateShare(index.id, parsed);
                            }}
                            step="0.01"
                            type="range"
                            value={formatPercentage(amount)}
                          />
                          <label className="percentage-input-label" htmlFor={`allocation-input-${index.id}`}>
                            <span className="visually-hidden">{index.name} allocation percentage</span>
                            <input
                              aria-describedby={shareError ? "allocation-share-error" : undefined}
                              aria-label={`${index.name} allocation percentage`}
                              aria-invalid={Boolean(shareError)}
                              disabled={!isEditable}
                              id={`allocation-input-${index.id}`}
                              inputMode="decimal"
                              max={formatPercentage(FULL_ALLOCATION - lockedHundredths(index.id))}
                              min="0"
                              onBlur={() => {
                                setActiveDraft((current) => current?.indexId === index.id ? null : current);
                                setShareError(null);
                              }}
                              onChange={(event) => setShareDraft(index.id, event.currentTarget.value)}
                              onFocus={() => setActiveDraft({ indexId: index.id, value: formatPercentage(amount) })}
                              pattern="[0-9]{1,3}(\.[0-9]{0,2})?"
                              type="text"
                              value={activeDraft?.indexId === index.id ? activeDraft.value : formatPercentage(amount)}
                            />
                            <span aria-hidden="true">%</span>
                          </label>
                        </div>
                      )}
                    </div>
                  );
                })}
                {shareError && <p className="form-message form-message-error" id="allocation-share-error" role="alert">{shareError}</p>}
              </fieldset>

              <div className="date-field-grid">
                <label className="form-label" htmlFor="initial-date">
                  Initial date
                  <input
                    aria-required="true"
                    id="initial-date"
                    disabled={isSubmitting}
                    onChange={(event) => { setInitialDate(event.currentTarget.value); resetResponseState(); }}
                    type="date"
                    value={initialDate}
                  />
                </label>
                <label className="form-label" htmlFor="end-date">
                  End date
                  <input
                    aria-required="true"
                    id="end-date"
                    disabled={isSubmitting}
                    onChange={(event) => { setEndDate(event.currentTarget.value); resetResponseState(); }}
                    type="date"
                    value={endDate}
                  />
                </label>
              </div>

              <label className="form-label strategy-field" htmlFor="rebalancing-strategy">
                Rebalancing strategy
                <select
                  disabled={isSubmitting}
                  id="rebalancing-strategy"
                  onChange={(event) => {
                    setRebalancing(event.currentTarget.value as RebalancingStrategy);
                    resetResponseState();
                  }}
                  value={rebalancing}
                >
                  {strategies.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}
                </select>
              </label>

              {formError && <p className="form-message form-message-error" role="alert">{formError}</p>}
              {acknowledgement && (
                <p aria-live="polite" className="form-message form-message-success">
                  Settings were received. Calculations are not available yet.
                </p>
              )}
              <button className="submit-button" disabled={isSubmitting} type="submit">
                {isSubmitting ? "Sending settings…" : "Submit portfolio"}
              </button>
            </form>
          )}
        </section>
      </div>

      <footer className="page-footer">
        Sample values are fictional and carry no financial interpretation.
      </footer>
    </main>
  );
}

export default ExampleChart;
