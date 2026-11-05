import axios from "axios";

export interface IndexOption {
  id: "ibovespa" | "ifix" | "selic" | "sp500";
  name: "IBOVESPA" | "IFIX" | "Selic" | "S&P 500";
}

export type RebalancingStrategy =
  | "none"
  | "3_months"
  | "6_months"
  | "1_year"
  | "2_years"
  | "3_years";

export interface PortfolioRequest {
  initial_date: string;
  end_date: string;
  allocations: { index: IndexOption["id"]; percentage: number }[];
  rebalancing: RebalancingStrategy;
}

export interface PortfolioAcknowledgement {
  status: "ok";
}

const expectedIndexes: IndexOption[] = [
  { id: "ibovespa", name: "IBOVESPA" },
  { id: "ifix", name: "IFIX" },
  { id: "selic", name: "Selic" },
  { id: "sp500", name: "S&P 500" },
];

export async function fetchIndexes(): Promise<IndexOption[]> {
  const response = await axios.get<unknown>("/api/indexes");
  if (!Array.isArray(response.data) || response.data.length !== expectedIndexes.length) {
    throw new Error("The index list did not match the supported indexes.");
  }

  const valid = response.data.every((item, index) => {
    const expected = expectedIndexes[index];
    return (
      typeof item === "object" && item !== null &&
      "id" in item && "name" in item &&
      item.id === expected.id && item.name === expected.name
    );
  });
  if (!valid) throw new Error("The index list did not match the supported indexes.");
  return response.data as IndexOption[];
}

export async function submitPortfolio(
  request: PortfolioRequest,
): Promise<PortfolioAcknowledgement> {
  const response = await axios.post<unknown>("/api/portfolio", request);
  if (
    typeof response.data !== "object" || response.data === null ||
    Object.keys(response.data).length !== 1 ||
    !("status" in response.data) || response.data.status !== "ok"
  ) {
    throw new Error("The server did not acknowledge the portfolio settings.");
  }
  return { status: "ok" };
}
