export type ManagementSection = 'pnl' | 'capital' | 'orders';

export interface StrategyManagementOverviewLike {
  deskKey: string;
  sortOrder: number;
}

export function normalizeManagementSection(value: unknown): ManagementSection {
  return value === 'pnl' || value === 'orders' ? value : 'capital';
}

export function resolveManagementDesk<T extends StrategyManagementOverviewLike>(
  requestedDesk: unknown,
  items: T[],
): string | null {
  const available = items.map((item) => item.deskKey);
  if (!available.length) return null;
  if (typeof requestedDesk === 'string' && available.includes(requestedDesk)) {
    return requestedDesk;
  }
  return available[0];
}
