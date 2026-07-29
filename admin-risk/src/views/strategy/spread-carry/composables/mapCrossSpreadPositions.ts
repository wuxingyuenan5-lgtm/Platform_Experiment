import type {
  CrossSpreadExecutionMode,
  CrossSpreadExitPlanResult,
  CrossSpreadLimitStrategy,
} from '@/api/platform/crossSpreadLifecycle';
import type {
  CrossSpreadObservabilityResult,
  CrossSpreadVenueObservability,
  NumericValue,
  VenuePositionSnapshot,
} from '@/api/platform/crossSpreadObservability';
import type { CrossSpreadSnapshotResult } from '@/api/platform/trading.types';
import {
  formatNullablePrice,
  formatNullableSigned,
  formatNumber,
  parseOptionalNumber,
} from './useCrossSpreadFormatting';

export interface QuantityRules {
  minOz: number;
  stepOz: number;
  mt5Multiplier: number;
}

export interface CloseOrder {
  id: string;
  direction: 'LONG_SPREAD' | 'SHORT_SPREAD';
  qtyOz: number;
  leverage: number;
  entrySpread: number;
  takeProfit: number;
  stopLoss: number;
  execution: string;
}

export interface OverviewRow {
  id: string;
  direction: string;
  qty: number;
  entrySpread: string;
  currentSpread: string;
  detail: string;
  accountStatus: string;
  accountRisk: string;
  pnl: string;
  legPnl: string;
  takeProfit: string;
  stopLoss: string;
  liquidation: string;
  margin: string;
  openTime: string;
  holdingTime: string;
  status: string;
}

interface MapOverviewRowsOptions {
  snapshot: CrossSpreadSnapshotResult | null;
  observability: CrossSpreadObservabilityResult | null;
  quantityRules: QuantityRules | null;
  longSpread: number | null;
  shortSpread: number | null;
  snapshotStatusText: string;
}

export function mapCloseOrders(exitPlans: CrossSpreadExitPlanResult[], leverage: number) {
  return exitPlans
    .filter((plan) => plan.status === 'active')
    .map<CloseOrder>((plan) => ({
      id: plan.planId,
      direction: plan.direction,
      qtyOz: Number(plan.quantityOz) || 0,
      leverage,
      entrySpread: Number(plan.entrySpread) || 0,
      takeProfit: Number(plan.takeProfitSpread) || 0,
      stopLoss: Number(plan.stopLossSpread) || 0,
      execution: `${executionSelectionLabel(plan.takeProfitExecutionMode, plan.takeProfitLimitStrategy)} / ${executionSelectionLabel(plan.stopLossExecutionMode, plan.stopLossLimitStrategy)}`,
    }));
}

export function mapOverviewRows(options: MapOverviewRowsOptions) {
  if (!options.snapshot) return [];
  const rows: OverviewRow[] = [];
  const bybitPositions = options.snapshot.bybit.positions || [];
  const mt5Positions = options.snapshot.mt5.positions || [];
  const rowCount = Math.max(bybitPositions.length, mt5Positions.length);
  for (let index = 0; index < rowCount; index += 1) {
    const bybit = bybitPositions[index];
    const mt5 = mt5Positions[index];
    const bybitLive = matchObservedPosition(options.observability?.bybit, bybit?.symbol, index);
    const mt5Live = matchObservedPosition(options.observability?.mt5, mt5?.symbol, index);
    const bybitQtyValue = Math.abs(parseOptionalNumber(bybit?.quantity) || 0);
    const mt5QtyValue =
      Math.abs(parseOptionalNumber(mt5?.quantity) || 0) *
      (options.quantityRules?.mt5Multiplier || 0);
    const qty = bybitQtyValue || mt5QtyValue;
    const direction = (parseOptionalNumber(bybit?.quantity) || 0) >= 0 ? '多头' : '空头';
    rows.push({
      id: `${bybit?.externalId || bybit?.symbol || 'bybit'}-${mt5?.externalId || mt5?.symbol || 'mt5'}-${index}`,
      direction,
      qty,
      entrySpread: '--',
      currentSpread: formatNullableSigned(
        direction === '多头' ? options.longSpread : options.shortSpread,
      ),
      detail: `BY: ${formatNullablePrice(bybit?.averagePrice)} | MT5: ${formatNullablePrice(mt5?.averagePrice)}`,
      accountStatus: `BY: ${venueReadState(options.observability?.bybit)} | MT5: ${venueReadState(options.observability?.mt5)}`,
      accountRisk: `BY: ${accountRiskText(options.observability?.bybit)} | MT5: ${accountRiskText(options.observability?.mt5)}`,
      pnl: formatNullableSigned(
        (parseOptionalNumber(bybit?.unrealizedPnl) || 0) +
          (parseOptionalNumber(mt5?.unrealizedPnl) || 0),
      ),
      legPnl: `BY: ${formatNullableSigned(parseOptionalNumber(bybit?.unrealizedPnl))} | MT5: ${formatNullableSigned(parseOptionalNumber(mt5?.unrealizedPnl))}`,
      takeProfit: '--',
      stopLoss: '--',
      liquidation: `BY: ${formatObservedLiquidation(options.observability?.bybit, bybitLive)} | MT5: ${formatObservedLiquidation(options.observability?.mt5, mt5Live)}`,
      margin: `BY: ${formatObservedMargin(bybitLive)} | MT5: ${formatObservedMargin(mt5Live)}`,
      openTime: '--',
      holdingTime: '--',
      status: options.snapshot.status === 'available' ? '正常' : options.snapshotStatusText,
    });
  }
  return rows;
}

function matchObservedPosition(
  venue: CrossSpreadVenueObservability | null | undefined,
  symbol: string | undefined,
  index: number,
) {
  if (!venue) return null;
  return venue.positions.find((position) => position.symbol === symbol) || venue.positions[index] || null;
}

function venueReadState(venue: CrossSpreadVenueObservability | null | undefined) {
  if (!venue) return '不可用';
  if (venue.status === 'complete') return `${venue.accountId} / 完整`;
  if (venue.status === 'partial') return `${venue.accountId} / 部分`;
  return `${venue.accountId} / 不可用`;
}

function accountRiskText(venue: CrossSpreadVenueObservability | null | undefined) {
  const risk = venue?.accountRisk;
  if (!risk) return '--';
  return `${money(risk.equity, risk.currency)} / ${money(risk.availableBalance, risk.currency)}`;
}

function formatObservedLiquidation(
  venue: CrossSpreadVenueObservability | null | undefined,
  position: VenuePositionSnapshot | null,
) {
  if (position?.liquidationPrice != null) return formatNumeric(position.liquidationPrice);
  if (venue?.venue === 'MT5') {
    return `Stop Out ${thresholdValue(venue.accountRisk?.stopOutLevel, venue.accountRisk?.marginThresholdMode)}`;
  }
  return '--';
}

function formatObservedMargin(position: VenuePositionSnapshot | null) {
  if (!position) return '--';
  const initial = formatNumeric(position.initialMargin);
  const maintenance = formatNumeric(position.maintenanceMargin);
  return initial === '--' && maintenance === '--' ? '--' : `${initial} / ${maintenance}`;
}

function formatNumeric(value: NumericValue | null | undefined, digits = 2) {
  const parsed = parseOptionalNumber(value);
  return parsed === null ? '--' : formatNumber(parsed, digits);
}

function money(value: NumericValue | null | undefined, currency: string) {
  const rendered = formatNumeric(value);
  return rendered === '--' ? rendered : `${rendered} ${currency}`;
}

function thresholdValue(value: NumericValue | null | undefined, mode?: string | null) {
  const parsed = parseOptionalNumber(value);
  if (parsed === null) return '--';
  return mode === '1' ? parsed.toFixed(2) : `${parsed.toFixed(2)}%`;
}

function limitStrategyLabel(strategy: CrossSpreadLimitStrategy) {
  return strategy === 'post_only_chase' ? 'PostOnly Chase' : 'FOK';
}

function executionSelectionLabel(
  mode: CrossSpreadExecutionMode,
  strategy: CrossSpreadLimitStrategy,
) {
  return mode === 'market' ? '市价' : limitStrategyLabel(strategy);
}
