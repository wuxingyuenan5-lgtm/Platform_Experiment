<template>
  <section class="cross-venue-workspace">
    <header class="cross-head">
      <div class="cross-head__controls">
        <label class="select-chip">
          <span>标的</span>
          <select v-model="selectedPair">
            <option :value="`${leftLegSymbol}-${rightLegSymbol}`">
              BYBIT: {{ leftLegSymbol }} vs MT5: {{ rightLegSymbol }}
            </option>
          </select>
        </label>
      </div>
    </header>

    <div class="cross-top-grid">
      <CrossVenueMarketQuotes
        :left-leg-symbol="leftLegSymbol"
        :right-leg-symbol="rightLegSymbol"
        :bybit-quote="bybitQuote"
        :mt5-quote="mt5Quote"
        :bybit-latency-ms="bybitLatencyMs"
        :mt5-latency-ms="mt5LatencyMs"
        :bybit-status="snapshot?.bybit.status"
        :mt5-status="snapshot?.mt5.status"
      />

      <CrossVenueSpreadSummary
        :long-spread="longSpread"
        :short-spread="shortSpread"
        :funding-inventory-text="fundingInventoryText"
        :usdt-usd-text="usdtUsdText"
      />

      <CrossVenueSpreadChart
        v-model:selected-range="selectedRange"
        :ranges="ranges"
        :spread-history="spreadHistory"
      />
    </div>

    <div class="cross-mid-grid">
      <CrossVenueTradingRules
        :trading-rule-rows="tradingRuleRows"
        :execution-logs="executionLogs"
        :execution-message="executionMessage"
        :execution-message-tone="executionMessageTone"
      />
      <SpreadExecutionCommand
        v-model:execution-stage="executionStage"
        v-model:execution-mode="executionMode"
        v-model:close-execution-mode="closeExecutionMode"
        v-model:qty-input="qtyInput"
        v-model:trigger-spread-input="triggerSpreadInput"
        v-model:acceptable-spread-input="acceptableSpreadInput"
        v-model:open-limit-strategy="openLimitStrategy"
        v-model:take-profit-execution="takeProfitExecution"
        v-model:take-profit-limit-strategy="takeProfitLimitStrategy"
        v-model:take-profit-spread-input="takeProfitSpreadInput"
        v-model:stop-loss-spread-input="stopLossSpreadInput"
        v-model:stop-loss-execution="stopLossExecution"
        v-model:stop-loss-limit-strategy="stopLossLimitStrategy"
        v-model:close-limit-spread-input="closeLimitSpreadInput"
        v-model:close-limit-strategy="closeLimitStrategy"
        :qty-error="qtyError"
        :bybit-qty="bybitQty"
        :mt5-lot="mt5Lot"
        :bybit-account-risk="observability?.bybit.accountRisk || null"
        :mt5-account-risk="observability?.mt5.accountRisk || null"
        :long-spread="longSpread"
        :short-spread="shortSpread"
        :submit-loading="submitLoading"
        :execution-message="executionMessage"
        :execution-message-tone="executionMessageTone"
        :limit-evidence="limitEvidence"
        :close-orders="closeOrders.filter((order) => !order.isAbnormal)"
        @commit-qty-input="commitQtyInput"
        @nudge-qty="nudgeQty"
        @commit-spread-input="commitSpreadInput"
        @prepare-open-draft="prepareOpenDraft"
        @open-confirm="openConfirm"
        @open-partial-close="openPartialClose"
      />

      <CrossVenueSpreadAnalysis />
    </div>

    <SpreadAbnormalOrders
      :orders="snapshot?.positionOverview?.abnormalOrders || []"
      :busy="submitLoading"
      @close-plan="openAbnormalClose"
      @settled="refreshAbnormalPositions"
    />
    <SpreadPositionOverview
      :overview-rows="overviewRows"
      :pnl-overview="overviewPnl"
      :empty-text="observabilityError || snapshotError || '暂无真实持仓'"
      :long-spread="longSpread"
      :update-exit-plan="updateExitPlanThresholds"
    />

    <SpreadExecutionConfirmModal
      :visible="confirmVisible"
      :submit-loading="submitLoading"
      :left-leg-symbol="leftLegSymbol"
      :right-leg-symbol="rightLegSymbol"
      :summary="confirmSummary"
      :guard-message="confirmGuardMessage"
      @close="cancelConfirmation"
      @confirm="confirmOrder"
    />
  </section>
</template>

<script setup lang="ts">
  import SpreadAbnormalOrders from './SpreadAbnormalOrders.vue';
  import CrossVenueMarketQuotes from './CrossVenueMarketQuotes.vue';
  import CrossVenueSpreadAnalysis from './CrossVenueSpreadAnalysis.vue';
  import CrossVenueSpreadChart from './CrossVenueSpreadChart.vue';
  import CrossVenueSpreadSummary from './CrossVenueSpreadSummary.vue';
  import CrossVenueTradingRules from './CrossVenueTradingRules.vue';
  import SpreadExecutionCommand from './SpreadExecutionCommand.vue';
  import SpreadExecutionConfirmModal from './SpreadExecutionConfirmModal.vue';
  import SpreadPositionOverview from './SpreadPositionOverview.vue';
  import { useCrossVenueExecutionWorkspace } from '../composables/useCrossVenueExecutionWorkspace';

  defineProps<{
    leftLegSymbol: string;
    rightLegSymbol: string;
  }>();

  const {
    acceptableSpreadInput,
    bybitQty,
    bybitLatencyMs,
    bybitQuote,
    closeExecutionMode,
    closeLimitSpreadInput,
    closeLimitStrategy,
    closeOrders,
    commitQtyInput,
    commitSpreadInput,
    cancelConfirmation,
    confirmGuardMessage,
    confirmOrder,
    confirmSummary,
    confirmVisible,
    executionLogs,
    executionMessage,
    executionMessageTone,
    executionMode,
    executionStage,
    fundingInventoryText,
    limitEvidence,
    longSpread,
    mt5Lot,
    mt5LatencyMs,
    mt5Quote,
    nudgeQty,
    observability,
    observabilityError,
    openConfirm,
    openPartialClose,
    openLimitStrategy,
    overviewRows,
    refreshAbnormalPositions,
    overviewPnl,
    prepareOpenDraft,
    qtyError,
    qtyInput,
    ranges,
    selectedPair,
    selectedRange,
    shortSpread,
    snapshot,
    snapshotError,
    spreadHistory,
    stopLossExecution,
    stopLossLimitStrategy,
    stopLossSpreadInput,
    submitLoading,
    takeProfitExecution,
    takeProfitLimitStrategy,
    takeProfitSpreadInput,
    tradingRuleRows,
    triggerSpreadInput,
    usdtUsdText,
    updateExitPlanThresholds,
  } = useCrossVenueExecutionWorkspace();
  function openAbnormalClose(planId: string) {
    closeExecutionMode.value = 'market';
    openConfirm(`CLOSE:${planId}`);
  }
</script>

<style scoped lang="less" src="./crossVenueExecutionWorkspace.less"></style>
