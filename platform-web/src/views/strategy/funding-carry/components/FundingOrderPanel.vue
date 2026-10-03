<template>
  <section class="funding-exec-shell" data-testid="funding-order-panel">
    <header class="funding-exec-topbar">
      <div class="selector-chip"
        ><span>标的</span><strong>{{ strategyLabel }}</strong></div
      >
      <button type="button" class="refresh-btn" @click="$emit('refresh')">刷新行情</button>
    </header>

    <div class="funding-upper-grid">
      <section class="panel quote-panel">
        <div class="panel-title panel-title--between">
          <h3>资金费率行情</h3>
          <a
            class="flat-action quote-analysis-link"
            href="https://www.coinglass.com/zh/FundingRate"
            target="_blank"
            rel="noopener noreferrer"
            >行情分析</a
          >
        </div>
        <article class="exchange-card">
          <div class="exchange-card__head">
            <div class="exchange-brand"
              ><span class="exchange-logo">B</span><strong>Bybit</strong></div
            >
            <span class="status-pill" :class="{ offline: context?.dataQualityState !== 'complete' }"
              ><i></i
              >{{ context?.dataQualityState === 'complete' ? '行情已同步' : '行情待更新' }}</span
            >
          </div>
          <div class="exchange-stats">
            <div
              ><span>现货中间价</span><strong>{{ context?.spotQuote?.mid ?? '--' }}</strong></div
            >
            <div
              ><span>永续中间价</span
              ><strong>{{ context?.perpetualQuote?.mid ?? '--' }}</strong></div
            >
            <div
              ><span>资金费率</span
              ><strong :class="fundingTone">{{ fundingRateLabel }}</strong></div
            >
            <div
              ><span>下次结算</span><strong>{{ formatTime(context?.nextFundingTime) }}</strong></div
            >
            <div
              ><span>期现基差</span><strong>{{ context?.basis ?? '--' }}</strong></div
            >
            <div class="spread-kpi"
              ><span>开仓可成交价差</span><strong>{{ executableSpreadOpen }}</strong
              ><small>{{ executableSpreadOpenPercent }}%</small></div
            >
            <div class="spread-kpi"
              ><span>平仓可成交价差</span><strong>{{ executableSpreadClose }}</strong
              ><small>{{ executableSpreadClosePercent }}%</small></div
            >
            <div
              ><span>数据时间</span><strong>{{ formatTime(context?.asOf) }}</strong></div
            >
          </div>
        </article>
      </section>

      <FundingBasisPanel />
    </div>

    <div class="funding-lower-grid">
      <section class="panel status-panel">
        <div class="panel-title"
          ><h3>交易规则 · {{ context?.perpetualSymbol ?? '--' }}</h3></div
        >
        <div class="rule-list">
          <div class="rule-list__row"
            ><span>永续执行</span><strong>{{ executionPolicyLabel }}</strong></div
          >
          <div class="rule-list__row"><span>现货对冲</span><strong>按成交量市价执行</strong></div>
          <div class="rule-list__row"
            ><span>现货最小数量</span
            ><strong>{{ context?.minimumQuantity?.spot ?? '--' }}</strong></div
          >
          <div class="rule-list__row"
            ><span>永续最小数量</span
            ><strong>{{ context?.minimumQuantity?.perpetual ?? '--' }}</strong></div
          >
          <div class="rule-list__row"
            ><span>现货数量步长</span
            ><strong>{{ context?.quantityStep?.spot ?? '--' }}</strong></div
          >
          <div class="rule-list__row"
            ><span>永续数量步长</span
            ><strong>{{ context?.quantityStep?.perpetual ?? '--' }}</strong></div
          >
          <div class="rule-list__row"
            ><span>交易权限</span><strong>{{ readinessLabel }}</strong></div
          >
        </div>
        <div class="status-feedback" role="status" aria-live="polite">
          <strong>执行反馈</strong>
          <p v-if="error" class="error-text">{{ failureMessage(error) }}</p>
          <p v-else-if="pendingDraft"> {{ stateLabel(workspaceState) }}，{{ pendingFeedback }} </p>
          <p v-else>{{ stateLabel(workspaceState) }}</p>
          <p v-if="failureReason" class="error-text">{{ failureMessage(failureReason) }}</p>
        </div>
      </section>

      <section class="panel order-panel">
        <div class="panel-title"><h3>套利执行指令</h3></div>
        <section class="embedded-funding">
          <div class="panel-title"><h3>开仓资金</h3></div>
          <div class="opportunity-meta">
            <div><span>套利方向</span><strong>现货买入 + 永续卖出</strong></div>
            <div
              ><span>可用开仓资金</span><strong>{{ fundingAvailable }}</strong></div
            >
            <div
              ><span>建议数量</span><strong>{{ context?.suggestedQuantity ?? '--' }}</strong></div
            >
          </div>
        </section>
        <div class="stage-tabs">
          <button type="button" :class="{ active: stage === 'open' }" @click="stage = 'open'"
            >开仓</button
          >
          <button type="button" :class="{ active: stage === 'close' }" @click="stage = 'close'"
            >平仓</button
          >
        </div>

        <div class="execution-controls">
          <span class="execution-controls__label">永续执行方式</span>
          <div class="execution-methods" role="group" aria-label="永续执行方式">
            <button
              v-for="method in executionMethods"
              :key="method.value"
              type="button"
              :class="{ active: executionPolicy === method.value }"
              :aria-pressed="executionPolicy === method.value"
              :disabled="submitting || !!pendingDraft"
              @click="$emit('update:execution-policy', method.value)"
              >{{ method.label }}</button
            >
          </div>
          <label v-if="executionPolicy === 'fok'" class="field limit-price-field">
            <span>永续限价</span>
            <div class="input-with-unit">
              <input
                :value="perpetualLimitPriceInput"
                type="text"
                inputmode="decimal"
                aria-label="永续限价"
                :disabled="submitting || !!pendingDraft"
                placeholder="输入限价"
                @input="
                  $emit(
                    'update:perpetual-limit-price-input',
                    ($event.target as HTMLInputElement).value,
                  )
                "
              />
              <em>USDT</em>
            </div>
            <small
              >价格步长 {{ context?.tickSize?.perpetual ?? '--' }}；{{
                stage === 'open' ? '卖出最低价' : '买入最高价'
              }}。</small
            >
          </label>
        </div>

        <template v-if="stage === 'open'">
          <div class="funding-order-grid">
            <section class="funding-order-column">
              <label class="field">
                <span>标的</span>
                <input
                  v-model="symbolSearch"
                  type="search"
                  placeholder="搜索标的：BTC、ETH、XAUT"
                  aria-label="搜索交易标的"
                  autocomplete="off"
                  spellcheck="false"
                />
                <select
                  :value="context?.perpetualSymbol"
                  @change="handleSymbolChange(($event.target as HTMLSelectElement).value)"
                >
                  <option
                    v-for="item in filteredSymbolOptions"
                    :key="item.perpetualSymbol"
                    :value="item.perpetualSymbol"
                  >
                    {{ item.baseAsset }} · {{ item.perpetualSymbol }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span>名义本金</span>
                <div class="input-with-unit">
                  <input
                    :value="notionalInput"
                    type="text"
                    @input="
                      $emit('update:notional-input', ($event.target as HTMLInputElement).value)
                    "
                  />
                  <em>USDT</em>
                </div>
              </label>
              <label class="field">
                <span>永续目标数量（币）</span>
                <input
                  :value="quantityInput"
                  type="text"
                  inputmode="decimal"
                  @input="$emit('update:quantity-input', ($event.target as HTMLInputElement).value)"
                />
              </label>
            </section>

            <section class="funding-order-column">
              <div class="funding-leg-grid">
                <div class="funding-leg-card"
                  ><span>现货头寸（扣费前）</span
                  ><strong>买入 {{ context?.openSizing?.spotQuantity ?? '--' }}</strong
                  ><small>{{ context?.spotSymbol ?? '--' }}</small></div
                >
                <div class="funding-leg-card"
                  ><span>永续头寸</span
                  ><strong>卖出 {{ context?.openSizing?.perpetualQuantity ?? '--' }}</strong
                  ><small>{{ context?.perpetualSymbol ?? '--' }}</small></div
                >
              </div>
              <div class="funding-metric-grid">
                <div class="mini-kpi"
                  ><span>反算永续名义金额</span><strong>{{ estimatedNotional }} USDT</strong></div
                >
              </div>
              <p v-if="context?.openSizing?.reason" class="error-text">{{
                context.openSizing.reason
              }}</p>
            </section>
          </div>
          <button
            class="submit-btn submit-btn--green"
            type="button"
            :disabled="!canSubmit || submitting"
            @click="$emit('submit-open')"
          >
            {{ submitting ? '提交中' : `${executionPolicyLabel}开仓` }}
          </button>
        </template>

        <template v-else>
          <div class="funding-close-shell">
            <p v-if="selectedCloseGroup?.spotFeeAdjusted" class="status-feedback"
              >现货净到账：{{
                selectedCloseGroup.netSpotAcquired ?? '等待成交费用同步'
              }}；手续费扣币：{{
                selectedCloseGroup.spotFeeResidualQuantity ?? '--'
              }}。平仓按净到账比例执行。</p
            >
            <div class="funding-close-table-wrap">
              <table class="funding-close-table">
                <thead
                  ><tr
                    ><th>组合</th><th>已对冲</th><th>已平仓</th><th>剩余可平</th><th>状态</th
                    ><th>操作</th></tr
                  ></thead
                >
                <tbody>
                  <tr
                    v-for="item in activeGroups"
                    :key="item.instructionId"
                    :class="{ selected: selectedCloseInstructionId === item.instructionId }"
                  >
                    <td>{{ item.perpetualSymbol }} / {{ item.spotSymbol }}</td>
                    <td>{{ item.hedgedQuantity }}</td>
                    <td>{{
                      item.authoritativeClosedQuantity ?? item.alreadyClosedQuantity ?? '0'
                    }}</td>
                    <td>{{ item.remainingClosableQuantity ?? '0' }}</td>
                    <td>{{ stateLabel(item.status) }}</td>
                    <td
                      ><button
                        type="button"
                        class="flat-action"
                        :disabled="!hasClosableQuantity(item)"
                        @click="$emit('select-close-instruction', item.instructionId)"
                        >选择</button
                      ></td
                    >
                  </tr>
                  <tr v-if="!activeGroups.length"
                    ><td colspan="6" class="empty-cell">暂无活动组合</td></tr
                  >
                </tbody>
              </table>
            </div>
            <label class="field">
              <span>平仓数量</span>
              <input
                :value="closeQuantityInput"
                aria-label="平仓数量"
                :disabled="!selectedCloseInstructionId"
                type="text"
                inputmode="decimal"
                @input="
                  $emit('update:close-quantity-input', ($event.target as HTMLInputElement).value)
                "
              />
              <small>最多可平 {{ selectedCloseGroup?.remainingClosableQuantity ?? '0' }}</small>
            </label>
            <div class="close-fractions" role="group" aria-label="平仓比例">
              <button
                v-for="fraction in [25, 50, 75, 100]"
                :key="fraction"
                type="button"
                :disabled="!selectedCloseInstructionId || submitting || !!pendingDraft"
                @click="$emit('select-close-fraction', fraction)"
              >
                {{ fraction === 100 ? '全部平仓' : `${fraction}%` }}
              </button>
            </div>
            <p class="execution-hint"
              >比例按剩余可平数量计算，并按永续数量步长向下取整；可直接输入部分平仓数量。</p
            >
            <button
              class="submit-btn submit-btn--red"
              type="button"
              :disabled="!canClose || submitting || !selectedCloseInstructionId"
              @click="$emit('submit-close')"
            >
              {{ submitting ? '提交中' : `${executionPolicyLabel}平仓` }}
            </button>
          </div>
        </template>
      </section>

      <section class="panel history-panel">
        <div class="panel-title"><h3>执行记录</h3></div>
        <table class="analysis-table">
          <thead
            ><tr
              ><th>组合</th><th>已对冲</th><th>已平 / 剩余</th><th>资金费</th><th>手续费</th
              ><th>状态</th></tr
            ></thead
          >
          <tbody>
            <tr v-for="item in executionGroups" :key="item.instructionId">
              <td>{{ item.perpetualSymbol }} / {{ item.spotSymbol }}</td>
              <td>{{ item.hedgedQuantity }}</td>
              <td
                >{{ item.authoritativeClosedQuantity ?? '0' }} /
                {{ item.remainingClosableQuantity ?? '0' }}</td
              >
              <td>{{ item.fundingFees ?? '--' }}</td>
              <td>{{ item.fees ?? '--' }}</td>
              <td>{{ stateLabel(item.status) }}</td>
            </tr>
            <tr v-if="!executionGroups.length"
              ><td colspan="6" class="empty-cell">暂无执行记录</td></tr
            >
          </tbody>
        </table>
      </section>
    </div>

    <section
      v-if="abnormalGroups.length || pendingRecovery || abnormalMessage"
      class="panel positions-panel funding-abnormal"
    >
      <div class="panel-title"
        ><h3>资费异常订单</h3><span>{{ abnormalGroups.length }} 项待处理</span></div
      >
      <article v-for="item in abnormalGroups" :key="item.instructionId">
        <strong>{{ item.perpetualSymbol }} · {{ item.instructionId }}</strong>
        <p>{{ item.abnormalReason }}</p>
        <p
          >永续剩余空仓 {{ item.remainingPerpetualQuantity }}；现货剩余持币
          {{ item.remainingSpotHolding ?? '待核对' }}；净敞口
          {{ item.netDeltaQuantity ?? '待核对' }}；结果未知预约
          {{ item.resultUnknownReservedQuantity }}</p
        >
        <button
          v-if="item.abnormalAction === 'close_group'"
          type="button"
          :disabled="submitting"
          @click="selectAbnormalClose(item.instructionId)"
          >处理该组合平仓</button
        >
        <button
          v-else-if="item.abnormalAction === 'flatten_open'"
          type="button"
          :disabled="abnormalSubmitting || submitting || !canTrade"
          @click="pendingAbnormal = item.batchId"
          >平掉异常开仓剩余仓位</button
        >
        <button
          v-else-if="item.abnormalAction === 'finish_close'"
          type="button"
          :disabled="abnormalSubmitting || submitting || !canTrade || !!pendingRecovery"
          @click="
            pendingRecovery = {
              instructionId: item.recoveryCloseInstructionId,
              key: item.recoveryIdempotencyKey,
              quantity: item.recoverySpotQuantity,
            }
          "
          >{{
            Number(item.recoverySpotQuantity) > 0 ? '补平原指令剩余现货' : '核对原补平结果'
          }}</button
        >
        <p v-else>执行结果尚未确定，请先核对原指令及两腿成交。</p>
        <div v-if="pendingAbnormal === item.batchId">
          <p>确认市价平掉此资费异常开仓的已确认剩余仓位？现货按扣费后剩余数量执行。</p>
          <button type="button" :disabled="abnormalSubmitting" @click="pendingAbnormal = null"
            >取消</button
          >
          <button
            type="button"
            :disabled="abnormalSubmitting"
            @click="confirmAbnormalClose(item.batchId)"
            >确认平仓</button
          >
        </div>
      </article>
      <div v-if="pendingRecovery" role="group" aria-label="确认补平现货">
        <p v-if="Number(pendingRecovery.quantity) > 0"
          >原平仓永续腿已完成。确认在同一账户市价卖出剩余 {{ pendingRecovery.quantity }} 现货？</p
        >
        <p v-else>核对原补平请求及成交，不重复下单。</p>
        <button type="button" :disabled="abnormalSubmitting" @click="pendingRecovery = null"
          >取消</button
        >
        <button
          type="button"
          :disabled="abnormalSubmitting || !canTrade"
          @click="confirmCloseRecovery"
          >确认补平现货</button
        >
      </div>
      <p v-if="abnormalMessage" role="status">{{ abnormalMessage }}</p>
    </section>

    <section class="panel positions-panel">
      <div class="panel-title"><h3>当前持仓总览</h3></div>
      <div class="positions-metrics">
        <div
          ><span>活动组合</span><strong>{{ activeGroups.length }}</strong></div
        >
        <div
          ><span>待平预约</span><strong>{{ pendingCloseTotal }}</strong></div
        >
        <div
          ><span>结果未知预约</span><strong>{{ unknownReservedTotal }}</strong></div
        >
        <div
          ><span>Funding 已预约</span
          ><strong>{{ context?.activeReservation?.fundingReserved ?? '--' }}</strong></div
        >
        <div
          ><span>Cross 已预约</span
          ><strong>{{ context?.activeReservation?.crossReserved ?? '--' }}</strong></div
        >
        <div
          ><span>可用资金</span><strong>{{ fundingAvailable }}</strong></div
        >
      </div>
      <div class="positions-table-wrap">
        <table class="positions-table">
          <thead
            ><tr
              ><th>组合</th><th>现货腿</th><th>永续腿</th><th>累计现货成交</th><th>累计永续成交</th
              ><th>剩余可平</th><th>净敞口</th><th>状态</th><th>更新时间</th
              ><th>价差止盈止损</th></tr
            ></thead
          >
          <tbody>
            <tr v-for="item in activeGroups" :key="item.instructionId">
              <td>{{ item.instructionId }}</td
              ><td>{{ item.spotSymbol }}</td
              ><td>{{ item.perpetualSymbol }}</td>
              <td>{{ item.cumulativeSpotFill ?? item.hedgedQuantity }}</td
              ><td>{{ item.cumulativePerpetualFill ?? item.hedgedQuantity }}</td>
              <td>{{ item.remainingClosableQuantity ?? item.residualQuantity }}</td
              ><td>{{ item.residualQuantity ?? '--' }}</td
              ><td>{{ stateLabel(item.status) }}</td
              ><td>{{ formatTime(item.asOf) }}</td>
              <td
                ><FundingExitSettings
                  :open-instruction-id="item.openInstructionId || item.instructionId"
                  :plan="item.exitPlan"
                  :can-trade="canTrade && !item.isAbnormal"
                  @saved="$emit('refresh')"
              /></td>
            </tr>
            <tr v-if="!activeGroups.length"
              ><td colspan="10" class="empty-cell">暂无真实 Funding 持仓</td></tr
            >
          </tbody>
        </table>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import Decimal from 'decimal.js';
  import { useUserStore } from '@/store/modules/user';
  import FundingBasisPanel from './FundingBasisPanel.vue';
  import FundingExitSettings from './FundingExitSettings.vue';
  import { closeFundingAbnormalOpen, recoverFundingClose } from '@/api/platform/fundingWorkspace';
  import type { FundingExecutionPolicy } from '../composables/fundingExecutionRecovery';

  const props = defineProps<{
    context: Record<string, any> | null;
    positionGroups: Array<Record<string, any>>;
    pendingDraft: Record<string, any> | null;
    workspaceState: string;
    failureReason?: unknown;
    submitting: boolean;
    error: string | null;
    quantityInput: string;
    closeQuantityInput: string;
    executionPolicy: FundingExecutionPolicy;
    perpetualLimitPriceInput: string;
    canClose: boolean;
    notionalInput: string;
    selectedCloseInstructionId: string;
    selectedCloseGroup: Record<string, any> | null;
    canSubmit: boolean;
  }>();

  const emit = defineEmits<{
    (event: 'update:notional-input', value: string): void;
    (event: 'update:quantity-input', value: string): void;
    (event: 'update:close-quantity-input', value: string): void;
    (event: 'update:execution-policy', value: FundingExecutionPolicy): void;
    (event: 'update:perpetual-limit-price-input', value: string): void;
    (event: 'select-close-fraction', percent: number): void;
    (event: 'submit-open'): void;
    (event: 'submit-close'): void;
    (event: 'refresh'): void;
    (event: 'select-symbol', perpetualSymbol: string, spotSymbol: string): void;
    (event: 'select-close-instruction', instructionId: string): void;
  }>();

  const stage = ref<'open' | 'close'>('open');
  const symbolSearch = ref('');
  const executionMethods: Array<{ value: FundingExecutionPolicy; label: string }> = [
    { value: 'market', label: '市价' },
    { value: 'fok', label: '限价 FOK' },
    { value: 'post_only_chase', label: '挂单追价' },
  ];
  const executionPolicyLabel = computed(
    () => executionMethods.find((method) => method.value === props.executionPolicy)?.label ?? '--',
  );
  const pendingFeedback = computed(() =>
    ['manual_intervention', 'result_unknown'].includes(props.workspaceState)
      ? '保留原指令，等待核对'
      : '正在恢复同一指令',
  );
  const estimatedNotional = computed(() => {
    try {
      const amount = new Decimal(String(props.context?.openSizing?.estimatedNotional ?? ''));
      return amount.isFinite() ? amount.toFixed(2) : '--';
    } catch {
      return '--';
    }
  });
  const filteredSymbolOptions = computed(() => {
    const needle = symbolSearch.value.trim().toUpperCase();
    const options = (props.context?.symbolOptions ?? []) as Array<Record<string, any>>;
    if (!needle) return options;
    const matches = options.filter(
      (item) =>
        String(item.baseAsset ?? '')
          .toUpperCase()
          .includes(needle) ||
        String(item.perpetualSymbol ?? '')
          .toUpperCase()
          .includes(needle) ||
        String(item.spotSymbol ?? '')
          .toUpperCase()
          .includes(needle),
    );
    const current = options.find(
      (item) => String(item.perpetualSymbol ?? '') === String(props.context?.perpetualSymbol ?? ''),
    );
    return current && !matches.includes(current) ? [current, ...matches] : matches;
  });
  const activeGroups = computed(() =>
    props.positionGroups.filter((item) => item.lifecycleState !== 'history' && !item.isAbnormal),
  );
  const abnormalGroups = computed(() =>
    props.positionGroups.filter((item) => item.lifecycleState !== 'history' && item.isAbnormal),
  );
  const user = useUserStore();
  const canTrade = computed(() => user.authentication?.user.role === 'ceo');
  const pendingAbnormal = ref<string | null>(null);
  const abnormalSubmitting = ref(false);
  const abnormalMessage = ref('');
  const pendingRecovery = ref<{ instructionId: string; key: string; quantity: string } | null>(
    null,
  );
  watch(
    () => user.authentication?.user.userId,
    () => {
      pendingRecovery.value = null;
      pendingAbnormal.value = null;
      abnormalMessage.value = '';
    },
  );
  async function confirmCloseRecovery() {
    const pending = pendingRecovery.value;
    if (!pending || abnormalSubmitting.value || !canTrade.value) return;
    abnormalSubmitting.value = true;
    try {
      const result = await recoverFundingClose(pending.instructionId, pending.key);
      abnormalMessage.value =
        result.instruction.status === 'completed'
          ? '原平仓已完成，永续腿未重复下单。'
          : '原平仓仍待核对，请查看原指令与成交。';
      if (result.instruction.status === 'completed') pendingRecovery.value = null;
    } catch {
      abnormalMessage.value = '补平结果尚未确认；再次确认沿用原请求，仅核对已有成交。';
    } finally {
      abnormalSubmitting.value = false;
      emit('refresh');
    }
  }
  function selectAbnormalClose(instructionId: string) {
    stage.value = 'close';
    emit('select-close-instruction', instructionId);
  }
  async function confirmAbnormalClose(batchId: string) {
    if (abnormalSubmitting.value || !canTrade.value) return;
    abnormalSubmitting.value = true;
    try {
      const result = await closeFundingAbnormalOpen(batchId, user.authentication!.user.userId);
      abnormalMessage.value =
        result.status === 'completed'
          ? '资费异常仓位已平仓'
          : `平仓尚未完成：${result.failureReason || result.status}`;
    } catch {
      abnormalMessage.value = '平仓回执尚未确认，请核对原处理记录；再次点击沿用同一请求。';
    } finally {
      abnormalSubmitting.value = false;
      pendingAbnormal.value = null;
      emit('refresh');
    }
  }
  const executionGroups = computed(() =>
    [...props.positionGroups].sort((a, b) =>
      String(b.asOf ?? '').localeCompare(String(a.asOf ?? '')),
    ),
  );
  const strategyLabel = computed(() => props.context?.perpetualSymbol ?? '--');
  const fundingAvailable = computed(() => {
    const raw = props.context?.activeReservation?.fundingAvailable;
    if (raw == null) return '--';
    try {
      const amount = new Decimal(String(raw));
      return amount.isFinite()
        ? `${amount.toFixed(2)} ${props.context?.activeReservation?.currency ?? 'USDT'}`
        : '--';
    } catch {
      return '--';
    }
  });
  const fundingRateValue = computed(() => {
    if (props.context?.fundingRate == null) return null;
    const value = Number(props.context.fundingRate);
    return Number.isFinite(value) ? value * 100 : null;
  });
  const fundingRateLabel = computed(() =>
    fundingRateValue.value === null ? '--' : `${fundingRateValue.value.toFixed(4)}%`,
  );
  function formatFourDecimals(value: unknown) {
    if (value == null || value === '') return '--';
    try {
      const amount = new Decimal(String(value));
      return amount.isFinite() ? amount.toFixed(4) : '--';
    } catch {
      return '--';
    }
  }
  const executableSpreadOpen = computed(() =>
    formatFourDecimals(props.context?.executableSpread?.open),
  );
  const executableSpreadOpenPercent = computed(() =>
    formatFourDecimals(props.context?.executableSpread?.openPercent),
  );
  const executableSpreadClose = computed(() =>
    formatFourDecimals(props.context?.executableSpread?.close),
  );
  const executableSpreadClosePercent = computed(() =>
    formatFourDecimals(props.context?.executableSpread?.closePercent),
  );
  const fundingTone = computed(() =>
    fundingRateValue.value !== null && fundingRateValue.value < 0 ? 'red' : 'green',
  );
  const readinessLabel = computed(() => {
    const state = props.context?.controlledLiveReadiness;
    if (!state) return '正在读取交易状态';
    if (state.ready === true) return '可执行';
    if (state.liveTradingEnabled === false || state.runtimeLiveWriteEnabled === false)
      return '资费实盘写入未启用（与 MT5 休市无关），开仓和平仓均暂停';
    if (state.killSwitchClear === false) return '风控已暂停交易';
    return '交易连接或市场状态未就绪';
  });

  function sum(items: Array<Record<string, any>>, key: string) {
    return items
      .reduce((total, item) => {
        try {
          return total.plus(String(item[key] ?? '0'));
        } catch {
          return total;
        }
      }, new Decimal(0))
      .toFixed();
  }
  const pendingCloseTotal = computed(() => sum(activeGroups.value, 'pendingCloseQuantity'));
  const unknownReservedTotal = computed(() =>
    sum(activeGroups.value, 'resultUnknownReservedQuantity'),
  );

  function handleSymbolChange(perpetualSymbol: string) {
    const option = props.context?.symbolOptions?.find(
      (item: Record<string, any>) => item.perpetualSymbol === perpetualSymbol,
    );
    if (option) emit('select-symbol', option.perpetualSymbol, option.spotSymbol);
  }
  function formatTime(value: unknown) {
    if (!value) return '--';
    const date = new Date(String(value));
    return Number.isNaN(date.getTime())
      ? String(value)
      : date.toLocaleString('zh-CN', { hour12: false });
  }
  function stateLabel(state: unknown) {
    const labels: Record<string, string> = {
      loading: '等待指令',
      submitting: '提交中',
      accepted: '已受理',
      executing: '执行中',
      partially_hedged: '部分对冲',
      reconciling: '对账中',
      completed: '已完成',
      failed: '已失败',
      rejected: '已拒绝',
      result_unknown: '结果待确认',
      manual_intervention: '需要人工处理',
      hedged: '已对冲',
    };
    return labels[String(state ?? '')] ?? String(state || '尚未开始');
  }
  function failureMessage(value: unknown): string {
    const message = String(value ?? '');
    if (message.includes('Reference price is unavailable for reservation')) {
      return '未取得可用报价，本次未下单。刷新行情后可重新提交。';
    }
    if (message.includes('Account is not mapped to a live adapter'))
      return '交易账户连接未就绪，本次未下单。';
    return message;
  }
  function hasClosableQuantity(group: Record<string, any>): boolean {
    try {
      return new Decimal(group.remainingClosableQuantity ?? '0').gt(0);
    } catch {
      return false;
    }
  }
</script>

<style scoped lang="less">
  .funding-exec-shell {
    display: grid;
    gap: 12px;
    color: var(--strategy-text-1);
  }

  .funding-exec-topbar,
  .panel-title--between,
  .exchange-card__head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .selector-chip {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    min-height: 42px;
    padding: 0 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: #fff;
  }

  .selector-chip span {
    color: var(--strategy-text-3);
  }

  .refresh-btn,
  .flat-action {
    height: 38px;
    padding: 0 14px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 10px;
    background: #fff;
    color: var(--strategy-text-2);
    font-weight: 700;
    cursor: pointer;
  }

  .funding-upper-grid {
    display: grid;
    grid-template-columns: 1.45fr 1fr;
    gap: 12px;
  }

  .embedded-funding {
    min-width: 0;
    padding: 16px 18px 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 18px;
    background: #fff;
    box-shadow: var(--strategy-shadow-soft);
  }

  .quote-analysis-link {
    display: inline-flex;
    align-items: center;
    text-decoration: none;
  }

  .funding-lower-grid {
    display: grid;
    grid-template-columns: 0.6fr 1.5fr 0.9fr;
    gap: 12px;
    align-items: stretch;
  }

  .panel {
    min-width: 0;
    padding: 16px 18px 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 18px;
    background: #fff;
    box-shadow: var(--strategy-shadow-card);
  }

  .execution-hint {
    margin: 12px 0 0;
    color: var(--strategy-text-3);
    font-size: 12px;
    line-height: 1.6;
  }

  .panel-title {
    margin-bottom: 12px;
  }

  .panel-title h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 16px;
    font-weight: 800;
  }

  .exchange-card {
    padding: 16px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 14px;
  }

  .exchange-brand {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .exchange-logo {
    display: grid;
    place-items: center;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: #f3f4f6;
    font-weight: 800;
  }

  .status-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    color: var(--strategy-success);
    font-size: 12px;
    font-weight: 700;
  }

  .status-pill i {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: currentcolor;
  }

  .status-pill.offline {
    color: var(--strategy-danger);
  }

  .exchange-stats,
  .opportunity-meta,
  .rule-list {
    display: grid;
    gap: 10px;
    margin-top: 14px;
  }

  .exchange-stats div,
  .opportunity-meta div,
  .rule-list__row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }

  .exchange-stats span,
  .opportunity-meta span,
  .rule-list__row span {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .opportunity-value {
    margin: 18px 0;
    font-size: 36px;
    font-weight: 800;
  }

  .green {
    color: var(--strategy-success) !important;
  }

  .red {
    color: var(--strategy-danger) !important;
  }

  .data-badge {
    color: var(--strategy-text-faint);
    font-size: 12px;
  }

  .trend-chart {
    height: 250px;
  }

  .rule-list__row {
    align-items: center;
    min-height: 42px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 10px;
  }

  .status-feedback {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid var(--strategy-border-soft);
  }

  .status-feedback p {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .error-text {
    color: var(--strategy-danger) !important;
  }

  .stage-tabs {
    display: flex;
    gap: 8px;
    margin-bottom: 14px;
  }

  .stage-tabs button {
    min-width: 72px;
    height: 40px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 10px;
    background: #fff;
    color: var(--strategy-text-2);
    font-weight: 700;
    cursor: pointer;
  }

  .stage-tabs button.active {
    background: var(--strategy-accent-soft);
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
    color: var(--strategy-accent-strong);
  }

  .funding-order-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .funding-order-column {
    display: grid;
    gap: 12px;
    align-content: start;
  }

  .field {
    display: grid;
    gap: 6px;
  }

  .field span {
    color: var(--strategy-text-2);
    font-size: 13px;
    font-weight: 700;
  }

  .field select,
  .field input {
    width: 100%;
    height: 46px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 12px;
    background: #fff;
  }

  .input-with-unit {
    display: grid;
    grid-template-columns: 1fr 72px;
    overflow: hidden;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 12px;
  }

  .input-with-unit input {
    border: 0;
    border-radius: 0;
  }

  .input-with-unit em {
    display: grid;
    place-items: center;
    color: var(--strategy-text-3);
    font-style: normal;
    font-weight: 700;
  }

  .funding-leg-grid,
  .funding-metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .funding-leg-card,
  .mini-kpi {
    display: grid;
    gap: 6px;
    min-height: 88px;
    padding: 12px 14px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 14px;
  }

  .funding-leg-card span,
  .mini-kpi span,
  .funding-leg-card small {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .funding-leg-card strong,
  .mini-kpi strong {
    font-size: 18px;
  }

  .submit-btn {
    width: 100%;
    height: 50px;
    margin-top: 14px;
    border: 0;
    border-radius: 12px;
    color: #fff;
    font-weight: 800;
    cursor: pointer;
  }

  .submit-btn--green {
    background: linear-gradient(90deg, #119c41, #0fa24c);
  }

  .submit-btn--red {
    background: linear-gradient(90deg, #df3342, #f14f5c);
  }

  .submit-btn:disabled {
    opacity: 0.45;
    cursor: not-allowed;
  }

  .funding-close-shell {
    display: grid;
    gap: 14px;
  }

  .funding-close-table-wrap,
  .funding-abnormal {
    border-color: #e9bcb6;
    background: #fffaf8;
  }

  .funding-abnormal article {
    padding: 14px 0;
    overflow-wrap: anywhere;
  }

  .funding-abnormal button {
    margin-right: 12px;
  }

  .positions-table-wrap {
    overflow: auto;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 14px;
  }

  .funding-close-table,
  .analysis-table,
  .positions-table {
    width: 100%;
    border-collapse: collapse;
  }

  .funding-close-table th,
  .funding-close-table td,
  .analysis-table th,
  .analysis-table td,
  .positions-table th,
  .positions-table td {
    padding: 12px 10px;
    border-bottom: 1px solid var(--strategy-border-soft);
    font-size: 12px;
    text-align: left;
    white-space: nowrap;
  }

  th {
    background: var(--strategy-table-head-bg);
    color: var(--strategy-text-3);
  }

  tr.selected {
    background: var(--strategy-surface-selected);
  }

  .positions-metrics {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 12px;
  }

  .positions-metrics div {
    display: grid;
    gap: 4px;
    padding: 10px 12px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 12px;
  }

  .positions-metrics span {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .positions-table {
    min-width: 1180px;
  }

  .empty-cell {
    color: var(--strategy-text-faint);
    text-align: center !important;
  }

  @media (max-width: 1400px) {
    .funding-lower-grid {
      grid-template-columns: minmax(180px, 0.6fr) minmax(0, 1.5fr);
    }

    .history-panel {
      grid-column: 1 / -1;
    }
  }

  @media (max-width: 960px) {
    .funding-upper-grid,
    .funding-lower-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 800px) {
    .funding-order-grid,
    .funding-leg-grid,
    .funding-metric-grid,
    .positions-metrics {
      grid-template-columns: 1fr;
    }

    .funding-exec-topbar {
      flex-direction: column;
      align-items: stretch;
    }
  }

  .execution-controls {
    display: grid;
    margin-bottom: 16px;
    padding: 14px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: 12px;
    background: var(--strategy-bg-soft, #f8faff);
    gap: 10px;
  }

  .execution-controls__label {
    color: var(--strategy-text-2);
    font-size: 12px;
    font-weight: 700;
  }

  .execution-methods,
  .close-fractions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .execution-methods button,
  .close-fractions button {
    min-height: 36px;
    padding: 6px 14px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 8px;
    background: #fff;
    color: var(--strategy-text-2);
    cursor: pointer;
  }

  .execution-methods button.active {
    border-color: var(--strategy-accent-ring);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    font-weight: 700;
  }

  .execution-methods button:focus-visible,
  .close-fractions button:focus-visible {
    outline: 2px solid var(--strategy-accent-strong);
    outline-offset: 2px;
  }

  .execution-methods button:disabled,
  .close-fractions button:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }

  .limit-price-field {
    max-width: 400px;
  }
</style>
