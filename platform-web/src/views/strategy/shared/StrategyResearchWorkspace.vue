<template>
  <section class="research-workspace">
    <header class="research-toolbar research-card">
      <label
        >交易所<select v-model="venue"
          ><option>Bybit</option
          ><option disabled>Binance · 未接入</option
          ><option disabled>OKX · 未接入</option></select
        ></label
      >
      <strong>{{ pairId === 'cross-gold' ? 'XAUTUSDT − XAUUSD' : 'BTCUSDT 永续 − 现货' }}</strong>
      <label
        >方向<select v-model="direction"
          ><option value="buy_spread">买价差</option
          ><option value="sell_spread">卖价差</option></select
        ></label
      >
      <label
        >数量（{{ pairId === 'cross-gold' ? '盎司' : 'BTC' }}）<input
          v-model="quantity"
          inputmode="decimal"
      /></label>
      <label
        >开始<input v-model="start" type="datetime-local" @change="followRecent = false"
      /></label>
      <label
        >结束<input v-model="end" type="datetime-local" @change="followRecent = false"
      /></label>
      <label
        >样本<select v-model="view"
          ><option value="valid">研究有效</option
          ><option value="all">全部观测</option></select
        ></label
      >
      <button type="button" :disabled="historyLoading" @click="loadHistory">查询已采集历史</button>
      <button type="button" @click="recentWindow">最近 5 分钟</button>
      <label><input v-model="followRecent" type="checkbox" />跟随最新窗口</label>
      <button type="button" @click="showStatus = !showStatus">采集状态</button>
    </header>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="latest?.data?.quality?.length" role="status">
      当前样本限制：{{ latest.data.quality.map(qualityLabel).join('、') }}
    </p>
    <aside v-if="showStatus" class="research-card status-grid" aria-label="采集状态">
      <span>采集：{{ status?.data?.consumer?.status || '未启用' }}</span>
      <span>归档至：{{ status?.publishedThrough || '暂无' }}</span>
      <span>保存容量：{{ status?.data?.bytes ?? '未知' }} 字节</span>
      <span>磁盘剩余：{{ status?.data?.diskFreeBytes ?? '未知' }} 字节</span>
      <span>按当前窗口估算每日：{{ status?.data?.projectedBytesPerDay ?? '覆盖不足' }} 字节</span>
      <span>分片：{{ status?.data?.parts ?? '未知' }}</span>
      <span
        >图表索引：{{ status?.data?.projection?.processedParts ?? 0 }} /
        {{ status?.data?.projection?.publishedParts ?? 0 }} 分片</span
      >
      <span>落盘：{{ captureState?.lastDurableAt || '暂无' }}</span>
      <span
        >源缺口：{{
          captureState?.error || status?.data?.consumer?.error || '未报告；不代表完整'
        }}</span
      >
      <span>备份：{{ status?.data?.backup || '未验证' }}</span>
      <span>历史闭市日历：{{ status?.data?.calendarCoverage || '未验证' }}</span>
      <span v-for="(source, name) in captureState?.sources || {}" :key="name">
        {{ name }}：{{ sourceLabel(source.status) }}
        {{ source.reason ? ` · ${source.reason}` : '' }}
        {{ source.clock === 'unverified' ? ' · 源时钟未验证' : '' }}
      </span>
      <p>关闭页面后由服务持续采集。查询与刷新只读取已发布数据，不回补历史。</p>
    </aside>
    <FundingMarketBoard
      v-if="pairId === 'funding-btc'"
      :data="boardData"
      exchange="Bybit"
      selected-range="current"
      selected-symbol="BTC"
      selected-resolution="原生记录"
      :range-options="[{ value: 'current', label: '当前指示资费' }]"
      v-model:symbols="fundingSymbols"
      v-model:search="fundingSearch"
      v-model:sort="fundingSort"
    />
    <ResearchHistoryPanel
      :pair-id="pairId"
      :symbols="fundingSymbolOptions"
      v-model:symbol="selectedFundingSymbol"
      v-model:resolution="fundingResolution"
    />
    <FundingChartPanel
      v-if="pairId === 'funding-btc'"
      :data="fundingChart"
      context-locked
      exact-window
      exchange="Bybit"
      symbol="BTC"
      range="current"
      resolution="原生记录"
      :start-date="start.slice(0, 10)"
      :end-date="end.slice(0, 10)"
    />
    <FundingDetailPanel
      v-if="pairId === 'funding-btc'"
      :rows="history?.data?.rows || []"
      :borrow-rows="borrowObservations"
      :symbol="selectedFundingSymbol"
      :symbol-options="fundingSymbolOptions"
      :range-days="basisRangeDays"
      :resolution="basisResolution"
      @update:symbol="selectedFundingSymbol = $event"
      @update:range-days="onBasisRangeChange"
      @update:resolution="onBasisResolutionChange"
    />
    <CrossVenueResearchAnalysis v-else :history="history" :latest="latest" />
    <p v-if="historyLoading" role="status">正在读取所选窗口的已采集历史…</p>
    <p v-if="historyError" role="alert">{{ historyError }}</p>
    <div class="research-main">
      <article class="research-card">
        <h3>单次收益情景</h3>
        <label>入场价差<input v-model="entry" inputmode="decimal" /></label>
        <label>退出价差<input v-model="target" inputmode="decimal" /></label>
        <label>持有秒数<input v-model="holding" inputmode="numeric" /></label>
        <label>开平仓总手续费<input v-model="fees" placeholder="未知" inputmode="decimal" /></label>
        <label
          >额外执行成本<input v-model="executionCost" placeholder="未知" inputmode="decimal"
        /></label>
        <label><input v-model="zeroFundingScenario" type="checkbox" />明确假设本次资金费为 0</label>
        <label v-if="pairId === 'cross-gold'"
          ><input v-model="zeroSwapScenario" type="checkbox" />明确假设本次 Swap 为 0</label
        >
        <label v-if="pairId === 'cross-gold'"
          ><input v-model="fxScenario" type="checkbox" />USD/USDT 按 1:1 情景估值</label
        >
        <details
          ><summary>资金费与借贷情景</summary>
          <label>假设结算费率（小数）<input v-model="fundingRate" placeholder="未知" /></label>
          <label>假设结算标记价格<input v-model="markPrice" placeholder="未知" /></label>
          <label>结算时间<input v-model="settlementTime" type="datetime-local" /></label>
          <label>借款金额<input v-model="borrowAmount" placeholder="留空为自有资金" /></label>
          <label>每小时借款利率（小数）<input v-model="hourlyRate" placeholder="未知" /></label>
          <label
            >负债类型<select v-model="liability"
              ><option value="spot">现货负债</option
              ><option value="derivatives">衍生品负债</option></select
            ></label
          >
          <p>借贷采用明确的恒定利率情景；未付利息继续计息。Swap 资料不足时保持未知。</p>
        </details>
        <button type="button" @click="calculate">计算</button>
        <dl v-if="calculation?.data">
          <dt>净损益</dt><dd>{{ calculation.data.netPnl ?? '成本覆盖不足' }}</dd>
          <dt>保本退出价差</dt><dd>{{ calculation.data.breakEvenExitSpread ?? '未知' }}</dd>
          <dt>价差价格损益</dt><dd>{{ calculation.data.pricePnl }}</dd> <dt>资金费</dt
          ><dd>{{ calculation.data.fundingCash ?? '未知' }}</dd> <dt>借贷 / Swap</dt
          ><dd
            >{{ calculation.data.borrowCash ?? '未知' }} /
            {{ calculation.data.swapCash ?? '未知' }}</dd
          >
        </dl>
        <p v-if="calculation">结果是费用假设下的情景，不是已成交业绩。</p>
      </article>
    </div>
    <article class="research-card">
      <h3>条件实验 · 独立事件与逐次回放</h3>
      <div class="research-toolbar">
        <label>价格风险阈值<input v-model="risk" placeholder="可留空" /></label>
        <label>样本外开始<input v-model="validation" type="datetime-local" /></label>
        <label>MT5 每盎司滑点假设<input v-model="slippage" placeholder="未知" /></label>
        <label
          >入场矩阵（逗号分隔）<input v-model="entryGrid" placeholder="默认当前入场线"
        /></label>
        <label>退出矩阵（逗号分隔）<input v-model="exitGrid" placeholder="默认当前退出线" /></label>
        <label
          >数量情景（逗号分隔）<input v-model="quantityGrid" placeholder="默认当前数量"
        /></label>
        <button type="button" :disabled="running" @click="run">运行实验</button>
        <button type="button" @click="save">保存研究参数</button>
        <button v-if="running" type="button" @click="cancelRun">取消实验</button>
        <a
          v-if="savedId"
          :href="`#/strategy/platform?desk=${
            pairId === 'cross-gold' ? 'crossSpread' : 'funding'
          }&section=execution&researchDraft=${savedId}`"
          >交接执行草案</a
        >
      </div>
      <p>{{ runMessage }}</p>
      <p>默认不重叠；退出后须离开再进入条件区。未知路径与未完成样本单列，零延迟仅是理想情景。</p>
      <div v-if="experiment?.data?.result">
        <div class="status-grid">
          <span>独立事件：{{ experiment.data.result.summary.independentEvents }}</span>
          <span>净收益样本：{{ experiment.data.result.summary.netSampleCount }}</span>
          <span>中位净收益：{{ experiment.data.result.summary.netP50 ?? '不足' }}</span>
          <span>未知比例：{{ experiment.data.result.summary.unknownRatio ?? '不足' }}</span>
        </div>
        <div class="research-tabs">
          <button
            v-for="item in tabs"
            :key="item.key"
            type="button"
            @click="
              tab = item.key;
              matrixIndex = null;
            "
            >{{ item.label }}</button
          >
        </div>
        <table v-if="tab === 'events'">
          <thead
            ><tr
              ><th>入场</th><th>结果</th><th>净收益</th><th>MAE / MFE</th><th>回放</th></tr
            ></thead
          >
          <tbody
            ><tr v-for="event in displayedEvents" :key="event.id">
              <td>{{ event.entryAt || '未入场' }}</td
              ><td>{{ event.exitReason }}</td
              ><td>{{ event.netPnl ?? '未知' }}</td>
              <td>{{ event.priceMAE ?? '未知' }} / {{ event.priceMFE ?? '未知' }}</td>
              <td><button type="button" @click="openReplay(event.id)">查看</button></td>
            </tr></tbody
          >
        </table>
        <table v-else-if="tab === 'matrix'">
          <thead
            ><tr
              ><th>入场</th><th>退出</th><th>独立事件</th><th>中位净收益</th><th>事件列表</th></tr
            ></thead
          >
          <tbody
            ><tr v-for="(cell, i) in experiment.data.result.matrix" :key="i"
              ><td>{{ cell.entry }}</td
              ><td>{{ cell.target }}</td
              ><td>{{ cell.summary.independentEvents }}</td
              ><td>{{ cell.summary.netP50 ?? '未知' }}</td
              ><td
                ><button
                  type="button"
                  @click="
                    matrixIndex = i;
                    tab = 'events';
                  "
                  >查看</button
                ></td
              ></tr
            ></tbody
          >
        </table>
        <table v-else-if="tab === 'holdingCurve'">
          <thead
            ><tr
              ><th>持有秒数</th><th>同批入场</th><th>有效 / 未知</th><th>P10 / P50 / P90</th></tr
            ></thead
          >
          <tbody
            ><tr v-for="(point, i) in experiment.data.result.holdingCurve" :key="i"
              ><td>{{ point.seconds }}</td
              ><td>{{ point.entryCohortCount }}</td
              ><td>{{ point.sampleCount }} / {{ point.unknownCount }}</td
              ><td
                >{{ point.p10 ?? '未知' }} / {{ point.p50 ?? '未知' }} /
                {{ point.p90 ?? '未知' }}</td
              ></tr
            ></tbody
          >
        </table>
        <table v-else-if="tab === 'latencyScenarios' || tab === 'quantityScenarios'">
          <thead
            ><tr
              ><th>情景（毫秒 / 数量）</th><th>事件数</th><th>中位净收益</th><th>未知比例</th></tr
            ></thead
          >
          <tbody
            ><tr v-for="(point, i) in experiment.data.result[tab]" :key="i"
              ><td>{{ point.latencyMs ?? point.quantity }}</td
              ><td>{{ point.summary.independentEvents }}</td
              ><td>{{ point.summary.netP50 ?? '未知' }}</td
              ><td>{{ point.summary.unknownRatio ?? '未知' }}</td></tr
            ></tbody
          >
        </table>
        <dl v-else-if="tab === 'sampleOutOfTraining'"
          ><dt>样本外独立事件</dt
          ><dd>{{ experiment.data.result.sampleOutOfTraining.independentEvents }}</dd
          ><dt>中位净收益</dt
          ><dd>{{ experiment.data.result.sampleOutOfTraining.netP50 ?? '不足' }}</dd
          ><dt>未知比例</dt
          ><dd>{{ experiment.data.result.sampleOutOfTraining.unknownRatio ?? '不足' }}</dd></dl
        >
        <pre v-else>{{ JSON.stringify(experiment.data.result[tab], null, 2) }}</pre>
        <details v-if="replay"
          ><summary>事件路径与费用现金流</summary
          ><pre>{{ JSON.stringify(replay.data, null, 2) }}</pre>
        </details>
      </div>
      <details v-if="history"
        ><summary>覆盖、排除与分位数</summary
        ><pre>{{ JSON.stringify(history.data?.distribution, null, 2) }}</pre>
      </details>
    </article>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
  import CrossVenueResearchAnalysis from '../spread-carry/components/CrossVenueResearchAnalysis.vue';
  import {
    researchDraft,
    researchCancel,
    researchFunding,
    researchLatest,
    researchReplay,
    researchResult,
    researchRun,
    researchScenario,
    researchSeries,
    researchStatus,
    type ResearchResponse,
    type ResearchScenario,
    type ResearchExperiment,
  } from '@/api/platform/strategyResearch';
  import ResearchHistoryPanel from './ResearchHistoryPanel.vue';
  import FundingMarketBoard from '../funding-carry/components/FundingMarketBoard.vue';
  import FundingChartPanel from '../funding-carry/components/FundingChartPanel.vue';
  import FundingDetailPanel from '../funding-carry/components/FundingDetailPanel.vue';
  import type { FundingMarketBoardData, FundingChartPanelData } from '../funding-carry/types';

  const props = defineProps<{ pairId: 'cross-gold' | 'funding-btc' }>();
  const venue = ref('Bybit');
  const direction = ref<'buy_spread' | 'sell_spread'>('sell_spread');
  const quantity = ref('1');
  function localTime(t: number) {
    const d = new Date(t);
    return new Date(t - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  }
  const end = ref(localTime(Date.now()));
  const start = ref(localTime(Date.now() - 86400000));
  const validation = ref(localTime(Date.now() - 150000));
  const view = ref<'all' | 'valid'>('valid');
  const entry = ref('');
  const target = ref('');
  const holding = ref('900');
  const fees = ref('');
  const executionCost = ref('');
  const risk = ref('');
  const slippage = ref('');
  const fxScenario = ref(false);
  const zeroFundingScenario = ref(false);
  const zeroSwapScenario = ref(false);
  const fundingRate = ref('');
  const markPrice = ref('');
  const settlementTime = ref(end.value);
  const borrowAmount = ref('');
  const hourlyRate = ref('');
  const liability = ref<'spot' | 'derivatives'>('spot');
  const entryGrid = ref('');
  const exitGrid = ref('');
  const quantityGrid = ref('');
  const error = ref('');
  const showStatus = ref(false);
  const latest = ref<ResearchResponse>();
  const status = ref<ResearchResponse>();
  const captureState = computed(
    () => status.value?.data?.consumer?.runtime || status.value?.data?.runtime,
  );
  function qualityLabel(value: string) {
    return (
      (
        {
          clock_unverified: '时钟未验证',
          stale_quote: '报价过期',
          capture_gap: '采集缺口',
          source_gap: '来源中断',
          backfill_only: '回补样本',
          numeric_invalid: '数值异常',
          book_unsynced: '盘口尚未同步',
        } as Record<string, string>
      )[value] || value
    );
  }
  function sourceLabel(value?: string | null) {
    return (
      (
        {
          received: '已接收',
          receiving: '接收中',
          empty_range: '本次区间无 Tick',
          gap: '有缺口',
          interval_measured: '时间区间已测量',
          subscriptions_started: '订阅已建立',
          backfilling: '历史回补中',
          up_to_date: '历史已追平，持续增量',
          range_scanned: '历史区间扫描完成',
        } as Record<string, string>
      )[value || ''] ||
      value ||
      '未知'
    );
  }
  const history = ref<ResearchResponse>();
  const calculation = ref<ResearchResponse>();
  const funding = ref<ResearchResponse>();
  const experiment = ref<ResearchResponse>();
  const replay = ref<ResearchResponse>();
  const running = ref(false);
  const runMessage = ref('');
  const tab = ref('events');
  const savedId = ref('');
  const matrixIndex = ref<number | null>(null);
  const displayedEvents = computed(() =>
    matrixIndex.value === null
      ? experiment.value?.data?.result?.events || []
      : experiment.value?.data?.result?.matrix[matrixIndex.value]?.events || [],
  );
  const tabs = [
    { key: 'events', label: '独立事件' },
    { key: 'matrix', label: '入场退出矩阵' },
    { key: 'holdingCurve', label: '持有时间' },
    { key: 'latencyScenarios', label: '延迟情景' },
    { key: 'quantityScenarios', label: '数量情景' },
    { key: 'sampleOutOfTraining', label: '样本外' },
    { key: 'jointFundingSpread', label: '资费价差联合' },
    { key: 'settlementEvents', label: '结算事件' },
    { key: 'exitRuleComparison', label: '配对退出规则' },
    { key: 'opportunityDurations', label: '机会持续时间' },
  ];
  const historyLoading = ref(false);
  const historyError = ref('');
  const followRecent = ref(true);
  let lastHistoryRead = 0;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let stopped = false;
  let lastFundingRead = 0;
  const fundingSymbols = ref('BTC,ETH,SOL,XAUT,CRCL,MSTR');
  const fundingSymbolOptions = computed(() =>
    fundingSymbols.value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
  );
  const selectedFundingSymbol = ref('BTC');
  const fundingResolution = ref<'1h' | '8h' | '1d'>('1h');
  const basisRangeDays = ref<1 | 7 | 30>(1);
  const basisResolution = ref<'15m' | '1h' | '8h' | '1d'>('15m');
  const fundingSearch = ref('');
  const fundingSort = ref<'default' | 'name' | 'rate_desc' | 'rate_asc'>('default');
  const boardData = computed<FundingMarketBoardData>(
    () =>
      (funding.value?.data?.board as unknown as FundingMarketBoardData) || {
        updatedAt: '',
        symbolOptions: [],
        resolutionOptions: [],
        summaryCards: [],
        highest: [],
        lowest: [],
        usdtExchanges: ['Bybit'],
        inverseExchanges: [],
        rows: [],
      },
  );
  const fundingChart = computed<FundingChartPanelData>(
    () =>
      (funding.value?.data?.fundingChart as unknown as FundingChartPanelData) || {
        title: 'Bybit 指示资金费率',
        legendFunding: '指示资金费率',
        legendPrice: '',
        points: [],
      },
  );
  const borrowObservations = computed(
    () =>
      (history.value?.data?.borrowObservations ||
        funding.value?.data?.borrowObservations ||
        []) as Array<{ at: string; rate: string }>,
  );
  let fundingRequest = 0;
  async function loadFunding() {
    const request = ++fundingRequest;
    const result = await researchFunding({
      symbols: fundingSymbols.value,
      search: fundingSearch.value,
      sort: fundingSort.value,
      from: new Date(start.value).toISOString(),
      to: new Date(end.value).toISOString(),
    });
    if (request === fundingRequest && !stopped) funding.value = result;
  }
  watch([fundingSymbols, fundingSearch, fundingSort], () => {
    void loadFunding().catch(() => {
      error.value = '资费列表读取失败，请重试';
    });
  });
  async function recentWindow() {
    followRecent.value = true;
    end.value = localTime(Date.now());
    start.value = localTime(Date.now() - 300000);
    await loadHistory();
  }
  async function poll() {
    if (stopped) return;
    try {
      if (!document.hidden) {
        const reads: Promise<void>[] = [
          researchLatest(props.pairId).then((value) => {
            latest.value = value;
          }),
          researchStatus().then((value) => {
            status.value = value;
          }),
        ];
        if (props.pairId === 'funding-btc' && Date.now() - lastFundingRead >= 30000) {
          reads.push(
            loadFunding().then(() => {
              lastFundingRead = Date.now();
            }),
          );
        }
        const results = await Promise.allSettled(reads);
        error.value = results.some((r) => r.status === 'rejected')
          ? '部分数据读取失败；保留最近成功结果，请重试或缩短历史窗口。'
          : '';
        if (followRecent.value && !historyLoading.value && Date.now() - lastHistoryRead >= 30000) {
          end.value = localTime(Date.now());
          start.value = localTime(Date.now() - basisRangeDays.value * 86400000);
          await loadHistory();
        }
        if (running.value && experiment.value?.data?.run_id) {
          experiment.value = await researchResult(experiment.value.data.run_id);
          running.value = ['queued', 'running'].includes(experiment.value.status);
          runMessage.value = running.value
            ? '实验处理中'
            : experiment.value.status === 'completed'
            ? '实验完成'
            : '实验失败或已取消：' +
              String(experiment.value.data?.error || experiment.value.status);
        }
      }
    } catch {
      error.value = '研究数据暂不可用，请检查服务与访问权限。';
    } finally {
      if (!stopped) timer = setTimeout(poll, 5000);
    }
  }
  async function loadHistory() {
    if (historyLoading.value) return;
    historyLoading.value = true;
    lastHistoryRead = Date.now();
    historyError.value = '';
    const requested = [
      start.value,
      end.value,
      view.value,
      props.pairId,
      selectedFundingSymbol.value,
      basisResolution.value,
    ];
    try {
      const result = await researchSeries(
        props.pairId,
        new Date(start.value).toISOString(),
        new Date(end.value).toISOString(),
        view.value,
        basisResolution.value,
        selectedFundingSymbol.value,
      );
      if (
        requested.join('|') ===
        [
          start.value,
          end.value,
          view.value,
          props.pairId,
          selectedFundingSymbol.value,
          basisResolution.value,
        ].join('|')
      )
        history.value = result;
    } catch {
      historyError.value = '历史读取超时或窗口超过容量限制；可选择“最近 5 分钟”重试。';
    } finally {
      historyLoading.value = false;
    }
  }
  function onBasisRangeChange(days: 1 | 7 | 30) {
    basisRangeDays.value = days;
    followRecent.value = false;
    end.value = localTime(Date.now());
    start.value = localTime(Date.now() - days * 86400000);
    void loadHistory();
  }
  function onBasisResolutionChange(value: '15m' | '1h' | '8h' | '1d') {
    basisResolution.value = value;
    void loadHistory();
  }
  function scenarioBody(): ResearchScenario {
    const openedAt = new Date(start.value).toISOString();
    return {
      pairId: props.pairId,
      direction: direction.value,
      quantity: quantity.value,
      entrySpread: entry.value,
      exitSpread: target.value,
      openedAt,
      closedAt: new Date(Date.parse(openedAt) + Number(holding.value) * 1000).toISOString(),
      currency: 'USDT',
      fxAssumption: fxScenario.value ? 'explicit_1_to_1' : 'same_currency',
      tradingFees: fees.value || null,
      additionalExecutionCost: executionCost.value || null,
      costProfileId: 'user-scenario.v1',
      funding: fundingRate.value
        ? [
            {
              at: new Date(settlementTime.value).toISOString(),
              observedAt: openedAt,
              rate: fundingRate.value,
              mark: markPrice.value || null,
              kind: 'scenario',
              markQuality: 'prior_estimate',
              currency: 'USDT',
            },
          ]
        : [],
      fundingCoverage: zeroFundingScenario.value || fundingRate.value ? 'scenario' : 'unknown',
      swap: [],
      swapCoverage:
        props.pairId === 'funding-btc'
          ? 'not_applicable'
          : zeroSwapScenario.value
          ? 'scenario'
          : 'unknown',
      borrow: borrowAmount.value
        ? {
            product: 'uta_flexible',
            principal: borrowAmount.value,
            hourlyRate: hourlyRate.value || null,
            liabilityType: liability.value,
            currency: 'USDT',
            vipLevel: 'scenario',
            observedAt: openedAt,
            effectiveFrom: openedAt,
            billingRuleVersion: 'bybit-uta-2026-09-03',
          }
        : {
            product: 'self_funded',
            principal: '0',
            liabilityType: 'spot',
            currency: 'USDT',
            vipLevel: 'scenario',
            billingRuleVersion: 'bybit-uta-2026-09-03',
          },
    };
  }
  async function cancelRun() {
    if (experiment.value?.data?.run_id)
      experiment.value = await researchCancel(experiment.value.data.run_id);
    running.value = false;
    runMessage.value = '实验已取消';
  }
  async function calculate() {
    followRecent.value = false;
    try {
      calculation.value = await researchScenario(scenarioBody());
      error.value = '';
    } catch {
      calculation.value = undefined;
      error.value = '请检查数量、价差、时间及明确的费用/汇率情景。';
    }
  }
  async function run() {
    followRecent.value = false;
    try {
      const body: ResearchExperiment = {
        pairId: props.pairId,
        direction: direction.value,
        quantity: quantity.value,
        entryThreshold: entry.value,
        exitTarget: target.value,
        riskPnl: risk.value || null,
        clockBasis: 'observed',
        qualityProfileId: 'research-quality.v2',
        holdingSeconds: [300, 900, 3600, 14400],
        latencyMs: [0, 100, 250, 500, 1000],
        maxQuoteAgeMs: 2000,
        entryThresholds: entryGrid.value
          .split(',')
          .map((x) => x.trim())
          .filter(Boolean),
        exitTargets: exitGrid.value
          .split(',')
          .map((x) => x.trim())
          .filter(Boolean),
        quantities: quantityGrid.value
          .split(',')
          .map((x) => x.trim())
          .filter(Boolean),
        maxHoldingSeconds: Number(holding.value),
        from: new Date(start.value).toISOString(),
        to: new Date(end.value).toISOString(),
        cutoff: new Date(end.value).toISOString(),
        validationFrom: new Date(validation.value).toISOString(),
        costProfile: scenarioBody(),
        mt5SlippagePerUnit: slippage.value || null,
      };
      experiment.value = await researchRun(body);
      running.value = true;
      runMessage.value = '实验已排队，输入窗口已固定。';
    } catch {
      error.value = '实验参数无效或无权限；请检查样本外时间和费用情景。';
    }
  }
  async function openReplay(id: string) {
    try {
      replay.value = await researchReplay(experiment.value?.data?.run_id || '', id);
    } catch {
      error.value = '回放暂不可用。';
    }
  }
  async function save() {
    followRecent.value = false;
    try {
      const draft = await researchDraft({
        pairId: props.pairId,
        direction: direction.value,
        quantity: quantity.value,
        entryThreshold: entry.value,
        exitTarget: target.value,
        methodVersion: 'experiment.v1',
        costProfileId: 'user-scenario.v1',
      });
      savedId.value = draft.data?.id || '';
      runMessage.value = '研究参数已保存：' + draft.data?.id + '。执行前需重新取价和检查风险。';
    } catch {
      error.value = '研究参数保存失败。';
    }
  }
  watch(
    () => [props.pairId, start.value, end.value, view.value],
    () => {
      history.value = undefined;
      calculation.value = undefined;
    },
  );
  watch(selectedFundingSymbol, () => {
    if (props.pairId === 'funding-btc') void loadHistory();
  });
  watch(fundingSymbols, (value) => {
    const options = value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    if (options.length && !options.includes(selectedFundingSymbol.value)) {
      selectedFundingSymbol.value = options[0];
    }
  });
  onMounted(() => {
    void poll();
  });
  onUnmounted(() => {
    stopped = true;
    if (timer) clearTimeout(timer);
  });
</script>

<style lang="less">
  #app:has(.research-workspace) {
    min-width: 0;
  }
</style>

<style scoped lang="less">
  .research-workspace {
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
    max-width: 100%;
    color: var(--strategy-text-1);
    gap: 18px;
  }

  .research-toolbar,
  .status-grid,
  .research-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    align-items: end;
  }

  .research-main {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
  }

  .research-card {
    min-width: 0;
    padding: 20px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
  }

  label {
    display: flex;
    gap: 6px;
    flex-direction: column;
    margin-bottom: 8px;
    font-size: 12px;
  }

  input,
  select,
  button,
  textarea {
    padding: 8px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface);
    color: inherit;
  }

  input[type='checkbox'] {
    align-self: start;
  }

  button {
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.5;
    cursor: wait;
  }

  .research-chart {
    width: 100%;
    min-width: 0;
    height: 320px;
  }

  p {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  table {
    width: 100%;
    font-size: 12px;
    text-align: left;
  }

  th,
  td {
    padding: 8px;
    border-bottom: 1px solid var(--strategy-border);
  }

  pre {
    max-height: 360px;
    overflow: auto;
    font-size: 12px;
  }

  textarea {
    box-sizing: border-box;
    width: 100%;
  }

  dd {
    margin: 4px 0 12px;
  }

  @media (max-width: 900px) {
    .research-main {
      grid-template-columns: 1fr;
    }

    table {
      display: block;
      overflow: auto;
    }
  }
</style>
