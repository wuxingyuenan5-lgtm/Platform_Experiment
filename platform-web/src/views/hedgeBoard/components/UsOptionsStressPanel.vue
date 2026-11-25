<template>
  <section class="options-stress" aria-label="期权与流动性压力">
    <header class="stress-header">
      <div>
        <h2>美股期权微观结构与流动性踩踏监控仪表盘</h2>
        <p v-if="live" role="status">{{ liveStatus }}</p>
        <p v-else>2026-11-18 至 11-19 · OPEX 前基准与情景推演</p>
      </div>
      <a :href="sourceUrl" target="_blank" rel="noopener noreferrer">查看原站 ↗</a>
    </header>

    <div class="scenario-controls mode-controls" aria-label="数据模式">
      <button type="button" :aria-pressed="live" @click="live = true">最新收盘</button>
      <button type="button" :aria-pressed="!live" @click="live = false">历史情景</button>
      <button v-if="live && liveError" type="button" @click="loadLive">重试</button>
    </div>

    <section v-if="live" class="stress-card">
      <h3>综合压力与市场阶段</h3>
      <p>待补齐 SPX GEX、做市商总 Gamma 和估算净 Delta 后计算。</p>
    </section>
    <section v-else class="stress-overview" aria-label="压力与市场状态">
      <div class="stress-score">
        <h3>综合压力</h3>
        <strong :data-tone="scoreTone">{{ score }}<small> / 100</small></strong>
        <progress :value="score" max="100" aria-label="综合压力" :data-tone="scoreTone"></progress>
      </div>
      <div class="stress-scenarios">
        <h3 :data-tone="stageTone">{{ regimeTitle }}</h3>
        <div class="scenario-controls" aria-label="情景选择">
          <button
            v-for="(scenario, index) in scenarios"
            :key="scenario.label"
            type="button"
            :aria-pressed="activeScenario === index"
            @click="apply(index)"
            >{{ scenario.label }}</button
          >
          <button type="button" @click="apply(0)">重置为 11/19 基准</button>
        </div>
      </div>
    </section>

    <section v-if="!live" class="stress-card">
      <h3>四阶段演化与负反馈传导</h3>
      <p v-if="macroDefense" data-tone="risk">已触发宏观全面防御升级警报</p>
      <div class="stage-list">
        <div
          v-for="item in stages"
          :key="item.id"
          :aria-current="stage === item.id ? 'step' : undefined"
          :data-tone="stage === item.id ? stageTone : undefined"
        >
          <b>{{ item.id }} · {{ item.name }}</b>
          <small class="stage-state">{{
            item.id === stage ? '当前激活' : item.id < stage ? '已演进' : '观察中'
          }}</small>
          <p>{{ item.description }}</p>
        </div>
      </div>
      <p
        >相关性上升 → 离散交易亏损平仓 → 机械买盘消失、负 Gamma 与负 Delta 对冲放大抛压 → VIX 和
        VVIX 跳升、期限倒挂 → Vanna 触发 → 卖盘加速</p
      >
    </section>

    <div class="stress-grid">
      <article class="stress-card">
        <h3>波动率期限结构</h3>
        <p>{{ termState }} · 虚线为 Vanna 观察阈值 28</p>
        <div ref="termEl" class="stress-plot" role="img" :aria-label="termLabel"></div>
        <div class="reading-row">
          <span v-for="(label, index) in termLabels" :key="label"
            >{{ label }} <b>{{ formatReading(termValues[index], 1) }}</b></span
          >
        </div>
      </article>
      <article class="stress-card">
        <h3>期权流量扩散（Cboe Put/Call）</h3>
        <p>{{ flowIndex === null ? '等待同日成交比' : `${flowState} · ${flowDescription}` }}</p>
        <div ref="flowEl" class="stress-plot" role="img" :aria-label="flowLabel"></div>
        <div class="reading-row">
          <span v-for="(label, index) in flowLabels" :key="label"
            >{{ label }} <b>{{ formatReading(flowValues[index], 2) }}</b> /
            {{ flowLimits[index].toFixed(2) }}</span
          >
        </div>
      </article>
      <article v-if="live" class="stress-card dealer-card">
        <h3>做市商库存与对冲流</h3>
        <div v-for="gauge in gauges" :key="gauge.key" class="dealer-reading">
          <div
            ><span>{{ gauge.name }}</span
            ><strong>—</strong></div
          >
        </div>
        <p>待接入同口径敞口数据。</p>
      </article>
      <article v-else class="stress-card dealer-card">
        <h3>做市商库存与对冲流</h3>
        <p :data-tone="state.dealerGamma < 0 ? 'risk' : 'normal'">{{ dealerState }}</p>
        <div v-for="gauge in gauges" :key="gauge.key" class="dealer-reading">
          <div
            ><span>{{ gauge.name }}</span
            ><strong>{{ signed(state[gauge.key], gauge.digits) }} {{ gauge.unit }}</strong></div
          >
          <div class="dealer-track" aria-hidden="true">
            <span
              class="dealer-fill"
              :data-negative="state[gauge.key] < 0"
              :style="{
                width: (Math.abs(state[gauge.key]) / gauge.limit) * 50 + '%',
                left: Math.min(50, 50 + (state[gauge.key] / gauge.limit) * 50) + '%',
              }"
            ></span>
            <span v-if="gauge.key === 'dealerGamma'" class="dealer-floor"></span>
          </div>
          <div class="dealer-axis"
            ><span>−{{ gauge.limit }}</span
            ><span>0</span><span>+{{ gauge.limit }}</span></div
          >
        </div>
        <p
          >距 −8.6 十亿美元底线
          <strong :data-tone="dealerBuffer < 2 ? 'risk' : undefined"
            >{{
              dealerBuffer <= 0
                ? '已跌穿 ' + Math.abs(dealerBuffer).toFixed(1)
                : signed(dealerBuffer, 1)
            }}
            十亿美元</strong
          >
        </p>
      </article>
    </div>

    <section class="stress-card">
      <h3>{{ live ? '五大维度核心指标' : '五大维度核心指标与压力测试' }}</h3>
      <div class="indicator-groups">
        <div v-for="group in indicatorGroups" :key="group.name" class="input-group">
          <h4>{{ group.name }}</h4>
          <div v-if="live" class="live-readings">
            <div v-for="item in group.indicators" :key="item.key" class="live-reading">
              <span>{{ item.name }}</span>
              <b
                >{{ formatReading(liveValue(item.key), item.decimals) }}
                <small v-if="liveValue(item.key) !== null">{{ item.unit }}</small>
              </b>
            </div>
          </div>
          <template v-else>
            <div v-for="item in group.indicators" :key="item.key" class="indicator-row">
              <div
                ><label :for="'stress-number-' + item.key">{{ item.name }}</label
                ><small>{{ item.threshold }}</small></div
              >
              <input
                type="range"
                :aria-label="item.name + '滑块'"
                :min="item.min"
                :max="item.max"
                :step="item.step"
                :value="state[item.key]"
                @input="change(item.key, $event, item.min, item.max)"
              />
              <div class="number-field">
                <input
                  :id="'stress-number-' + item.key"
                  type="number"
                  :min="item.min"
                  :max="item.max"
                  :step="item.step"
                  :value="state[item.key].toFixed(item.decimals)"
                  @change="change(item.key, $event, item.min, item.max, item.decimals)"
                />
                <small v-if="item.unit">{{ item.unit }}</small>
              </div>
              <span class="signal" :data-tone="item.signal(state)">{{
                signalLabels[item.signal(state)]
              }}</span>
            </div>
          </template>
        </div>
      </div>
    </section>

    <section v-if="!live" class="stress-card">
      <h3>复盘清单</h3>
      <div class="review-grid">
        <div v-for="group in checklists" :key="group.id">
          <h4
            >{{ group.name }}
            <small
              >{{ group.items.filter((item) => item.matches(state)).length }} /
              {{ group.items.length }} 自动触发</small
            ></h4
          >
          <label
            v-for="(item, index) in group.items"
            :key="item.label"
            class="review-item"
            :data-triggered="item.matches(state)"
            :data-review="group.id"
          >
            <input
              type="checkbox"
              :checked="manual[group.id + index] ?? item.matches(state)"
              @change="manual[group.id + index] = ($event.target as HTMLInputElement).checked"
            />
            <span
              ><b>{{ item.label }}</b
              ><small>{{ item.condition }}</small></span
            >
            <span
              class="signal"
              :data-tone="
                item.matches(state) ? (group.id === 'risk' ? 'risk' : 'normal') : undefined
              "
              >{{
                group.id === 'risk'
                  ? item.matches(state)
                    ? '指标已触发'
                    : '未触发'
                  : item.matches(state)
                  ? '条件满足'
                  : '未满足'
              }}</span
            >
          </label>
        </div>
      </div>
    </section>

    <div v-if="!live" class="scenario-message" role="status">{{ scenarioMessage }}</div>
    <footer v-if="live">
      日度收盘来源：<a
        href="https://www.cboe.com/tradable_products/vix/vix_historical_data/"
        target="_blank"
        rel="noopener noreferrer"
        >Cboe 指数</a
      >
      ·
      <a
        href="https://www.cboe.com/markets/us/options/market-statistics/daily/"
        target="_blank"
        rel="noopener noreferrer"
        >Cboe 期权成交</a
      >
      ·
      <a
        href="https://www.nasdaq.com/market-activity/stocks/nvda/historical"
        target="_blank"
        rel="noopener noreferrer"
        >Nasdaq</a
      >
    </footer>
    <footer v-else
      >基准与规则取自原仪表盘，口径参考 LSEG Datastream、Cboe、SpotGamma 和
      Squeezemetrics。此页用于历史复盘和情景分析。</footer
    >
  </section>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, watchEffect } from 'vue';
  import { researchRequest } from '@/api/hedgeResearch';
  import { useECharts } from '@/hooks/web/useECharts';
  import type { IndicatorKey } from './optionsStressModel';
  import {
    checklists,
    indicatorGroups,
    marketStage,
    scenarios,
    sourceUrl,
    stages,
    stressScore,
  } from './optionsStressModel';

  interface LiveSnapshot {
    observationDate: string | null;
    status: 'partial' | 'stale' | 'no_data';
    pendingSeries: string[];
    readings: Record<IndicatorKey, string | null>;
    term: Record<'vix9d' | 'vix3m', string | null>;
  }
  const live = ref(true);
  const snapshot = ref<LiveSnapshot | null>(null);
  const liveError = ref(false);
  async function loadLive() {
    liveError.value = false;
    try {
      snapshot.value = await researchRequest<LiveSnapshot>({ url: '/research/us-options-stress' });
    } catch {
      liveError.value = true;
    }
  }
  onMounted(loadLive);
  const liveStatus = computed(() => {
    if (liveError.value) return '最新收盘读取失败';
    if (!snapshot.value) return '读取最新收盘…';
    if (snapshot.value.status === 'no_data') return '暂无已入库收盘数据';
    const count = Object.values(snapshot.value.readings).filter((value) => value !== null).length;
    const pending = snapshot.value.pendingSeries.length ? ' · 部分行情待更新' : '';
    const stale = snapshot.value.status === 'stale' ? ' · 行情更新滞后' : '';
    return `${snapshot.value.observationDate} 美股收盘 · ${count} / 14 项${pending}${stale}`;
  });
  const reading = (value: string | null | undefined) => (value == null ? null : Number(value));
  const liveValue = (key: IndicatorKey) => reading(snapshot.value?.readings[key]);
  const formatReading = (value: number | null, digits: number) => value?.toFixed(digits) ?? '—';

  const activeScenario = ref<number | null>(0);
  const state = ref({ ...scenarios[0].values });
  const manual = ref<Record<string, boolean>>({});
  const signalLabels = { normal: '正常', watch: '警戒', risk: '触发红线' };
  const score = computed(() => stressScore(state.value));
  const scoreTone = computed(() =>
    score.value >= 70 ? 'risk' : score.value >= 40 ? 'watch' : 'normal',
  );
  const stage = computed(() => marketStage(state.value));
  const stageTone = computed(() => ['normal', 'watch', 'risk', 'recovery'][stage.value - 1]);
  const macroDefense = computed(
    () =>
      stage.value === 3 &&
      ((state.value.pcIndex >= 1.25 && state.value.pcEquity >= 0.8) ||
        state.value.dealerGamma <= -8.6),
  );
  const regimeTitle = computed(() =>
    macroDefense.value
      ? '阶段三升级 · Vanna 踩踏与宏观全面防御'
      : `阶段 ${stage.value} · ${stages[stage.value - 1].name}`,
  );
  const scenarioMessage = ref('');
  let messageTimer: ReturnType<typeof setTimeout> | undefined;
  onBeforeUnmount(() => clearTimeout(messageTimer));
  function apply(index: number) {
    state.value = { ...scenarios[index].values };
    activeScenario.value = index;
    manual.value = {};
    scenarioMessage.value = '已切换至 ' + scenarios[index].label;
    clearTimeout(messageTimer);
    messageTimer = setTimeout(() => {
      scenarioMessage.value = '';
    }, 2000);
  }
  function change(key: IndicatorKey, event: Event, min: number, max: number, decimals?: number) {
    const field = event.target as HTMLInputElement;
    const requested = Number.isFinite(field.valueAsNumber) ? field.valueAsNumber : state.value[key];
    const reading = Math.max(min, Math.min(max, requested));
    state.value[key] = reading;
    if (decimals !== undefined) field.value = reading.toFixed(decimals);
    activeScenario.value = null;
  }
  const signed = (value: number, digits: number) => (value > 0 ? '+' : '') + value.toFixed(digits);
  const gauges = [
    { key: 'dealerGamma', name: 'Dealer Agg Gamma', unit: '十亿美元', limit: 10, digits: 1 },
    { key: 'spxGex', name: 'SPX GEX', unit: '十亿美元', limit: 130, digits: 1 },
    { key: 'netDelta', name: '估算净 Delta', unit: '', limit: 150, digits: 0 },
  ] as const;
  const dealerState = computed(() =>
    state.value.dealerGamma <= -8.6
      ? '跌至历史底线'
      : state.value.dealerGamma < 0
      ? '负 Gamma 区间'
      : '正 Gamma 区间',
  );
  const dealerBuffer = computed(() => state.value.dealerGamma + 8.6);
  const inverted = computed(() => {
    const ratios = live.value
      ? [liveValue('vixVxv'), liveValue('vix9dVix')]
      : [state.value.vixVxv, state.value.vix9dVix];
    if (ratios.some((ratio) => ratio !== null && ratio > 1)) return true;
    return ratios.includes(null) ? null : false;
  });
  const termState = computed(() =>
    inverted.value === null
      ? '等待同日期限数据'
      : inverted.value
      ? 'Backwardation 倒挂'
      : 'Contango 正向结构',
  );
  const termLabels = ['VIX9D', 'VIX 30D', 'VXV 3M'];
  const termValues = computed(() =>
    live.value
      ? [reading(snapshot.value?.term.vix9d), liveValue('vix'), reading(snapshot.value?.term.vix3m)]
      : [
          state.value.vix * state.value.vix9dVix,
          state.value.vix,
          state.value.vix / state.value.vixVxv,
        ].map((value) => Number(value.toFixed(1))),
  );
  const flowLabels = ['个股', '全市场', '指数'];
  const flowLimits = [0.8, 1.25, 1.25];
  const flowValues = computed(() =>
    live.value
      ? [liveValue('pcEquity'), liveValue('pcTotal'), liveValue('pcIndex')]
      : [state.value.pcEquity, state.value.pcTotal, state.value.pcIndex],
  );
  const flowIndex = computed(() => {
    const [equity, total, index] = flowValues.value;
    if (equity === null || total === null || index === null) return null;
    return index >= 1.25 && equity >= 0.8 ? 2 : equity >= 0.68 || total >= 1 ? 1 : 0;
  });
  const flowState = computed(() => ['结构平稳', '个股防御领先', '全面防御'][flowIndex.value ?? 0]);
  const flowDescription = computed(
    () =>
      ['指数维持常规对冲', '接近 2022 年初个股先行形态', '个股和指数防御需求同步升温'][
        flowIndex.value ?? 0
      ],
  );
  const termLabel = computed(() =>
    termLabels
      .map((label, index) => label + ' ' + formatReading(termValues.value[index], 1))
      .join('，'),
  );
  const flowLabel = computed(() =>
    flowLabels
      .map((label, index) => label + ' ' + formatReading(flowValues.value[index], 2))
      .join('，'),
  );
  const termEl = ref<HTMLDivElement>() as import('vue').Ref<HTMLDivElement>;
  const flowEl = ref<HTMLDivElement>() as import('vue').Ref<HTMLDivElement>;
  const termChart = useECharts(termEl);
  const flowChart = useECharts(flowEl);
  const chartFrame = {
    animation: false,
    grid: { left: 46, right: 16, top: 14, bottom: 52 },
    legend: { bottom: 0 },
    tooltip: { trigger: 'axis' as const },
  };
  watchEffect(() =>
    termChart.setOptions(
      {
        ...chartFrame,
        color: [inverted.value ? '#ba4155' : '#127b81', '#7a8495'],
        xAxis: { type: 'category', data: termLabels },
        yAxis: {
          type: 'value',
          min: (extent) => Math.min(10, Math.floor(extent.min / 5) * 5),
          max: (extent) => Math.max(40, Math.ceil(extent.max / 5) * 5),
        },
        series: [
          {
            name: '当前期限结构',
            type: 'line',
            smooth: 0.18,
            areaStyle: { opacity: 0.08 },
            symbolSize: 7,
            data: termValues.value.map((value) => value ?? '-'),
          },
          {
            name: 'Vanna 阈值',
            type: 'line',
            symbol: 'none',
            lineStyle: { type: 'dashed' },
            data: [28, 28, 28],
          },
        ],
      },
      false,
    ),
  );
  watchEffect(() =>
    flowChart.setOptions(
      {
        ...chartFrame,
        color: ['#315ba1', '#bd7b4b'],
        xAxis: { type: 'category', data: flowLabels },
        yAxis: {
          type: 'value',
          min: 0,
          max: (extent) => Math.max(1.6, Math.ceil(extent.max * 5) / 5),
        },
        series: [
          {
            name: '当前数值',
            type: 'bar',
            data: flowValues.value.map((value, i) => ({
              value: value ?? '-',
              itemStyle: { color: ['#64748b', '#ea580c', '#1d4ed8'][i] },
            })),
          },
          {
            name: '风险阈值',
            type: 'bar',
            data: flowLimits,
            itemStyle: {
              color: '#f8e2e7',
              borderColor: '#b64c61',
              borderWidth: 1,
              borderType: 'dashed',
            },
          },
        ],
      },
      false,
    ),
  );
</script>

<style scoped>
  .options-stress {
    display: grid;
    gap: 14px;
    min-width: 0;
    color: var(--strategy-text, #17324c);
  }

  .stress-header,
  .reading-row,
  .scenario-controls,
  .dealer-reading > div:not(.dealer-track) {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 16px;
  }

  .stress-header,
  .dealer-reading > div:not(.dealer-track) {
    justify-content: space-between;
  }

  .stress-header h2,
  h3,
  h4,
  p {
    margin: 0;
  }

  .stress-header h2 {
    font-size: 22px;
  }

  .stress-header p,
  .stress-card p,
  footer,
  small,
  .dealer-axis {
    color: var(--strategy-muted, #596e83);
    font-size: 12px;
  }

  .stress-header a {
    white-space: nowrap;
  }

  .stress-overview,
  .stress-card {
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--strategy-border, #d8e3ee);
    border-radius: 10px;
    background: var(--strategy-surface, #fff);
  }

  .stress-overview {
    display: grid;
    grid-template-columns: minmax(115px, 0.2fr) 1fr;
    gap: 18px;
  }

  .stress-score strong {
    font-size: 26px;
    font-variant-numeric: tabular-nums;
  }

  .stress-score progress {
    display: block;
    width: 100%;
    height: 8px;
    accent-color: #315ba1;
  }

  .stress-score progress[data-tone='risk'] {
    accent-color: #bd3750;
  }

  .stress-score progress[data-tone='watch'] {
    accent-color: #956423;
  }

  .stress-score progress[data-tone='normal'] {
    accent-color: #147270;
  }

  .scenario-controls {
    gap: 6px;
    margin-top: 8px;
  }

  .mode-controls {
    margin-top: 0;
  }

  .live-readings {
    display: grid;
    gap: 4px;
  }

  .live-reading {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    padding: 4px 8px;
    gap: 12px;
  }

  .live-reading b {
    font-variant-numeric: tabular-nums;
  }

  .scenario-controls button {
    padding: 4px 9px;
    border: 1px solid var(--strategy-border, #d8e3ee);
    border-radius: 5px;
    background: transparent;
    color: inherit;
  }

  .scenario-controls button[aria-pressed='true'] {
    border-color: #315ba1;
    background: #315ba1;
    color: #fff;
  }

  .stress-grid,
  .review-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .stress-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .dealer-card {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .stress-plot {
    width: 100%;
    height: 226px;
  }

  .reading-row {
    font-size: 12px;
  }

  .dealer-track {
    position: relative;
    height: 8px;
    border-radius: 3px;
    background: #dce5f0;
  }

  .dealer-track::after,
  .dealer-floor {
    content: '';
    position: absolute;
    width: 1px;
    height: 100%;
    background: #526581;
  }

  .dealer-track::after {
    left: 50%;
  }

  .dealer-floor {
    left: 7%;
    background: #97263b;
  }

  .dealer-fill {
    position: absolute;
    height: 100%;
    background: #14817f;
  }

  .dealer-fill[data-negative='true'] {
    background: #ba4155;
  }

  .dealer-axis {
    margin-top: 3px;
  }

  .indicator-groups {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 10px;
  }

  .input-group {
    min-width: 0;
    padding: 0 10px;
    border: 1px solid var(--strategy-border, #e4edf3);
    border-radius: 6px;
  }

  .input-group h4 {
    padding: 7px 0;
    border-bottom: 1px solid var(--strategy-border, #d8e3ee);
  }

  .indicator-row {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    align-items: center;
    gap: 4px 10px;
    padding: 7px 0;
    border-bottom: 1px solid var(--strategy-border, #e4edf3);
  }

  .indicator-row label,
  .review-item b {
    display: block;
  }

  .indicator-row input[type='range'] {
    grid-column: 1;
    grid-row: 2;
    width: 100%;
    min-width: 0;
    accent-color: #315ba1;
  }

  .number-field {
    display: flex;
    align-items: center;
    gap: 5px;
  }

  .indicator-row .signal {
    grid-column: 2;
    grid-row: 2;
  }

  .indicator-row:last-child {
    border-bottom: 0;
  }

  .number-field input {
    width: 76px;
    padding: 3px 5px;
    border: 1px solid var(--strategy-border, #d8e3ee);
    border-radius: 4px;
    background: transparent;
    color: inherit;
    font-variant-numeric: tabular-nums;
  }

  .signal {
    justify-self: end;
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }

  [data-tone='risk'] {
    color: #bd3750;
  }

  [data-tone='watch'] {
    color: #956423;
  }

  [data-tone='normal'] {
    color: #147270;
  }

  [data-tone='recovery'] {
    color: #315ba1;
  }

  .review-grid {
    margin-top: 10px;
  }

  .review-item {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: start;
    gap: 7px 10px;
    padding: 8px 0;
    border-bottom: 1px solid var(--strategy-border, #e4edf3);
  }

  .stage-list {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 10px 0;
  }

  .stage-list > div {
    padding-left: 8px;
    border-left: 2px solid var(--strategy-border, #d8e3ee);
  }

  .stage-list > div[aria-current='step'] {
    border-color: currentcolor;
  }

  .stage-state {
    display: block;
    margin: 3px 0;
  }

  .review-item[data-triggered='true'][data-review='risk'] {
    background: #bd375012;
  }

  .review-item[data-triggered='true'][data-review='reset'] {
    background: #14727012;
  }

  .scenario-message:not(:empty) {
    position: fixed;
    z-index: 20;
    right: 24px;
    bottom: 24px;
    padding: 9px 13px;
    border-radius: 6px;
    background: #17324c;
    color: #fff;
  }

  @media (max-width: 1100px) {
    .stress-grid,
    .indicator-groups {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 780px) {
    .stress-grid,
    .indicator-groups,
    .review-grid,
    .stage-list {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 480px) {
    .stress-overview {
      grid-template-columns: 1fr;
    }
  }
</style>
