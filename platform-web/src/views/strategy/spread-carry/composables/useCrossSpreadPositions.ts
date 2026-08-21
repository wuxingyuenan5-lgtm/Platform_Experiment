import { computed, type ComputedRef, type Ref } from 'vue';
import type { CrossSpreadExitPlanResult } from '@/api/platform/crossSpreadLifecycle';
import type { CrossSpreadObservabilityResult } from '@/api/platform/crossSpreadObservability';
import type { CrossSpreadSnapshotResult } from '@/api/platform/trading.types';
import {
  mapCloseOrders,
  mapOverviewRows,
  type CloseOrder,
  type OverviewRow,
  type QuantityRules,
} from './mapCrossSpreadPositions';

interface UseCrossSpreadPositionsOptions {
  exitPlans: Ref<CrossSpreadExitPlanResult[]>;
  snapshot: Ref<CrossSpreadSnapshotResult | null>;
  observability: Ref<CrossSpreadObservabilityResult | null>;
  quantityRules: ComputedRef<QuantityRules | null>;
  longSpread: ComputedRef<number | null>;
  shortSpread: ComputedRef<number | null>;
  snapshotStatusText: ComputedRef<string>;
}

export function useCrossSpreadPositions(options: UseCrossSpreadPositionsOptions) {
  const closeOrders = computed<CloseOrder[]>(() => mapCloseOrders(options.exitPlans.value));

  const overviewRows = computed<OverviewRow[]>(() =>
    mapOverviewRows({
      snapshot: options.snapshot.value,
      observability: options.observability.value,
      quantityRules: options.quantityRules.value,
      longSpread: options.longSpread.value,
      shortSpread: options.shortSpread.value,
      snapshotStatusText: options.snapshotStatusText.value,
      exitPlans: options.exitPlans.value,
    }),
  );

  return {
    closeOrders,
    overviewRows,
  };
}

export type { CloseOrder, OverviewRow, QuantityRules };
