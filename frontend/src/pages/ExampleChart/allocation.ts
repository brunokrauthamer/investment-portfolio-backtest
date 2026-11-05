import type { IndexOption } from "../../services/portfolio";

export interface AllocationLine {
  index: IndexOption;
  hundredths: number;
  locked: boolean;
}

export const FULL_ALLOCATION = 10_000;

export function equalAllocations(indexes: IndexOption[]): AllocationLine[] {
  if (indexes.length === 0) return [];
  const base = Math.floor(FULL_ALLOCATION / indexes.length);
  const remainder = FULL_ALLOCATION % indexes.length;
  return indexes.map((index, position) => ({
    index,
    hundredths: base + (position < remainder ? 1 : 0),
    locked: false,
  }));
}

export function reallocate(
  allocations: AllocationLine[],
  changedIndex: IndexOption["id"],
  requestedHundredths: number,
): AllocationLine[] {
  if (
    !Number.isInteger(requestedHundredths) ||
    requestedHundredths < 0 ||
    requestedHundredths > FULL_ALLOCATION
  ) return allocations;

  const changed = allocations.find(({ index }) => index.id === changedIndex);
  if (!changed || changed.locked) return allocations;

  const fixed = allocations.filter(({ index, locked }) => index.id !== changedIndex && locked);
  const flexible = allocations.filter(
    ({ index, locked }) => index.id !== changedIndex && !locked,
  );
  const lockedTotal = fixed.reduce((total, item) => total + item.hundredths, 0);
  const remaining = FULL_ALLOCATION - lockedTotal - requestedHundredths;
  if (remaining < 0 || (flexible.length === 0 && remaining !== 0)) return allocations;

  const redistributed = distribute(remaining, flexible);
  return allocations.map((line) => {
    if (line.index.id === changedIndex) return { ...line, hundredths: requestedHundredths };
    const next = redistributed.get(line.index.id);
    return next === undefined ? line : { ...line, hundredths: next };
  });
}

function distribute(total: number, targets: AllocationLine[]): Map<IndexOption["id"], number> {
  if (targets.length === 0) return new Map();
  const weightTotal = targets.reduce((sum, item) => sum + item.hundredths, 0);
  const weights = targets.map(({ hundredths }) => weightTotal === 0 ? 1 : hundredths);
  const denominator = weightTotal === 0 ? targets.length : weightTotal;
  const allocations = targets.map((target, index) => {
    const numerator = total * weights[index];
    return {
      id: target.index.id,
      amount: Math.floor(numerator / denominator),
      remainder: numerator % denominator,
      position: index,
    };
  });
  const extras = total - allocations.reduce((sum, item) => sum + item.amount, 0);
  const remainderOrder = [...allocations].sort(
    (left, right) => right.remainder - left.remainder || left.position - right.position,
  );
  for (const item of remainderOrder.slice(0, extras)) item.amount += 1;
  return new Map(allocations.map(({ id, amount }) => [id, amount]));
}

export function formatPercentage(hundredths: number): string {
  return (hundredths / 100).toFixed(2);
}
