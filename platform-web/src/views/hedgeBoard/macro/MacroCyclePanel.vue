<template>
  <section class="cycle-analysis" :aria-label="compact ? '资产驱动周期' : '周期分析'">
    <h2 v-if="!compact">{{ mode ? chartTitle : '周期分析' }}</h2>
    <nav v-if="!compact && !mode" class="cycle-controls" aria-label="周期分析分类"
      ><button
        v-for="tab in tabs"
        :key="tab.id"
        :aria-pressed="view === tab.id"
        @click="view = tab.id"
        >{{ tab.label }}</button
      ></nav
    >
    <p v-if="loading && !data" role="status">正在读取周期研究数据…</p>
    <p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <template v-if="data">
      <p v-if="sourceWarnings.length" class="definition" role="status">{{
        sourceWarnings.join('；')
      }}</p>
      <ChartExpand :title="chartTitle">
        <div class="cycle-panel">
          <template v-if="view === 'economy'">
            <div class="cycle-controls"
              ><label
                >经济体
                <select v-model="country" aria-label="周期经济体"
                  ><option value="us">美国</option
                  ><option value="cn">中国</option></select
                ></label
              ><label
                >历史起始年
                <select v-model.number="startYear" aria-label="周期历史起始年"
                  ><option :value="1950">全历史</option
                  ><option :value="2005">2005</option
                  ><option :value="2015">2015</option
                  ><option :value="2020">2020</option></select
                ></label
              ><label
                >收益区间
                <select v-model.number="horizon" aria-label="经济周期收益区间"
                  ><option :value="0">阶段当月</option
                  ><option :value="3">随后3个月</option
                  ><option :value="6">随后6个月</option></select
                ></label
              ></div
            >
            <div class="cycle-cards"
              ><article
                ><span>最新共同观测月</span><strong>{{ latestRegime?.month || '—' }}</strong
                ><small>经济统计所属月，非发布日期</small></article
              ><article
                ><span>增长 / 通胀变化</span
                ><strong>{{
                  latestRegime
                    ? pct(latestRegime.growthDelta, 'pp') +
                      ' / ' +
                      pct(latestRegime.inflationDelta, 'pp')
                    : '—'
                }}</strong
                ><small>同比增速较3个月前变化</small></article
              ><article
                ><span>当前阶段</span
                ><strong class="phase">{{
                  latestRegime ? regimeNames[latestRegime.regime] || '边界持平' : '历史不足'
                }}</strong
                ><small>工业生产同比 × CPI同比</small></article
              ></div
            >
            <CycleChart :options="economicChart" label="增长与通胀周期轨迹" />
            <p class="definition"
              >阶段按工业生产同比、CPI同比各自较3个月前的方向划分。任一变化为零的月份不归入四象限。美国使用美联储工业生产与BLS
              CPI，中国使用国家统计局对应公开指标。</p
            >
            <h3>各阶段资产表现</h3>
            <div class="cycle-table" tabindex="0" role="region" aria-label="经济阶段资产表现"
              ><table
                ><thead
                  ><tr
                    ><th>阶段</th><th>资产</th><th>月份样本</th><th>平均收益</th><th>中位数</th
                    ><th>上涨概率</th><th>25%—75%分位</th></tr
                  ></thead
                ><tbody
                  ><tr v-for="r in economicReturns" :key="r.asset + r.name"
                    ><th>{{ r.name }}</th
                    ><td>{{ r.asset }}</td
                    ><td>{{ r.n }}</td
                    ><td>{{ pct(r.mean) }}</td
                    ><td>{{ pct(r.median) }}</td
                    ><td>{{ pct(r.win) }}</td
                    ><td>{{ pct(r.low) }} / {{ pct(r.high) }}</td></tr
                  ></tbody
                ></table
              ></div
            >
            <p class="definition"
              >使用当前留存修订数据做事后描述，不是按历史发布日期可交易的回测。随后3/6个月样本会重叠；各资产历史长度独立，样本不足5个不宜比较。</p
            >
          </template>
          <template v-else-if="view === 'policy'">
            <div class="cycle-controls"
              ><label
                >方向
                <select v-model.number="policyDirection" aria-label="政策周期方向"
                  ><option :value="-1">首次转为降息</option
                  ><option :value="1">首次转为加息</option></select
                ></label
              ><label
                >资产
                <select v-model="policyAsset" aria-label="政策周期资产"
                  ><option v-for="s in usdAssets" :key="s.id" :value="s.id">{{
                    s.label
                  }}</option></select
                ></label
              ></div
            >
            <div class="cycle-cards"
              ><article
                ><span>最新目标区间上限</span
                ><strong>{{ pct(policy.latest?.value ?? null) }}</strong
                ><small>{{ policy.latest?.date || '—' }}</small></article
              ><article
                ><span>最近一次利率调整</span><strong>{{ policy.lastChange || '—' }}</strong
                ><small>{{ policyPhase }}</small></article
              ><article
                ><span>样本内方向切换</span><strong>{{ policyEvents.length }} 次</strong
                ><small>序列始于2008年；不拼接此前政策口径</small></article
              ></div
            >
            <CycleChart :options="policyChart" label="政策方向切换前后资产走势" />
            <div class="cycle-table" tabindex="0" role="region" aria-label="政策周期事件收益"
              ><table
                ><thead
                  ><tr
                    ><th>生效日</th><th>目标上限</th><th>随后1个月</th><th>随后3个月</th
                    ><th>随后6个月</th><th>随后12个月</th></tr
                  ></thead
                ><tbody
                  ><tr v-for="e in policyEvents" :key="e.date"
                    ><th>{{ e.date }}</th
                    ><td>{{ pct(e.rate) }}</td
                    ><td v-for="n in [1, 3, 6, 12]" :key="n">{{
                      pct(eventReturn(assetPoints(policyAsset), e.date, n))
                    }}</td></tr
                  ></tbody
                ></table
              ></div
            >
            <p class="definition"
              >目标区间上限发生反向调整时识别一轮首次加息/降息；首次可见调整也列出，样本左端可能截断更早阶段。以生效日前最后一个收盘为基准，终点取目标日及其后7日内首个观测。图展示−90至+365日内有价格覆盖的事件；未到期留空。生效日与市场预期形成时点不同，历史事件数量有限。</p
            >
          </template>
          <template v-else-if="view === 'drivers'">
            <div class="cycle-controls"
              ><label v-if="!compact"
                >资产
                <select v-model="driverAsset" aria-label="驱动周期资产"
                  ><option value="us-gld">黄金 ETF · GLD</option
                  ><option value="us-spy">美股 SPY</option
                  ><option value="cn-hs300">沪深300</option
                  ><option value="btc-usd">BTC / USD</option></select
                ></label
              ><label
                >收益区间
                <select v-model.number="driverHorizon" aria-label="驱动周期收益区间"
                  ><option :value="0">条件当月</option
                  ><option :value="3">随后3个月</option
                  ><option :value="6">随后6个月</option></select
                ></label
              ></div
            >
            <h3>{{ label(effectiveDriver) }} · {{ driverConfig.labels.join(' × ') }}</h3>
            <CycleChart :options="driverChart" label="驱动条件下的收益分布" />
            <div class="cycle-table" tabindex="0" role="region" aria-label="驱动周期统计"
              ><table
                ><thead
                  ><tr
                    ><th>三个月变化条件</th><th>月份样本</th><th>平均收益</th><th>中位数</th
                    ><th>上涨概率</th><th>25%—75%分位</th></tr
                  ></thead
                ><tbody
                  ><tr v-for="r in driverReturns" :key="r.name"
                    ><th>{{ r.name }}</th
                    ><td>{{ r.n }}</td
                    ><td>{{ pct(r.mean) }}</td
                    ><td>{{ pct(r.median) }}</td
                    ><td>{{ pct(r.win) }}</td
                    ><td>{{ pct(r.low) }} / {{ pct(r.high) }}</td></tr
                  ></tbody
                ></table
              ></div
            >
            <p class="definition"
              >{{
                driverConfig.note
              }}
              两项指标均取月内最后观测，与3个月前比较方向；缺少中间月份不分类。样本不足5个月的分组不宜用于比较。条件与收益的关系为历史描述，不能据此认定因果；当前修订值不代表当时已公布值。</p
            >
            <a
              v-if="effectiveDriver === 'btc-usd'"
              href="#/hedge-board/crypto?view=crypto-onchain-toolbox"
              >查看既有减半周期对比 ↗</a
            >
          </template>
          <template v-else>
            <div class="cycle-controls"
              ><label
                >相对强弱窗口
                <select v-model.number="rotationMonths" aria-label="跨资产轮动窗口"
                  ><option :value="3">3个月</option
                  ><option :value="6">6个月</option
                  ><option :value="12">12个月</option></select
                ></label
              ></div
            >
            <h3>美元口径跨资产轮动 · 截至 {{ rotationData.latest?.month || '—' }}</h3>
            <CycleChart :options="rotationChart" label="跨资产滚动收益与相对强弱" />
            <h3>相关性变化 · {{ correlations.date || '—' }}</h3>
            <div class="cycle-table" tabindex="0" role="region" aria-label="跨资产相关性变化"
              ><table
                ><thead
                  ><tr
                    ><th>资产对</th><th>近20个共同收益区间</th><th>近60个共同收益区间</th></tr
                  ></thead
                ><tbody
                  ><tr v-for="r in correlations.pairs" :key="r.first + r.second"
                    ><th>{{ label(r.first) }} / {{ label(r.second) }}</th
                    ><td>{{ r.n20 == null ? '—' : r.n20.toFixed(2) }}</td
                    ><td>{{ r.n60 == null ? '—' : r.n60.toFixed(2) }}</td></tr
                  ></tbody
                ></table
              ></div
            >
            <div class="cycle-table" tabindex="0" role="region" aria-label="最新跨资产强弱排名"
              ><table
                ><thead
                  ><tr><th>排名</th><th>资产</th><th>区间价格收益</th></tr></thead
                ><tbody
                  ><tr v-for="(r, i) in rotationData.latest?.ranks || []" :key="r.id"
                    ><td>{{ i + 1 }}</td
                    ><th>{{ label(r.id) }}</th
                    ><td>{{ pct(r.value) }}</td></tr
                  ></tbody
                ></table
              ></div
            >
            <h3>领先资产变化</h3
            ><div class="cycle-table" tabindex="0" role="region" aria-label="轮动领先资产切换"
              ><table
                ><thead
                  ><tr><th>月份</th><th>领先资产</th><th>窗口收益</th></tr></thead
                ><tbody
                  ><tr v-for="r in leaderChanges" :key="r.month"
                    ><th>{{ r.month }}</th
                    ><td>{{ label(r.ranks[0].id) }}</td
                    ><td>{{ pct(r.ranks[0].value) }}</td></tr
                  ></tbody
                ></table
              ></div
            >
            <p class="definition"
              >SPY、GLD为美元ETF原始收盘，BTC为Blockchain.com跨交易所美元日均价，观测时点不同。以共同完整月份和相同月末区间比较价格收益，不含分红再投资；不把A股人民币收益混入美元排名。BTC缺数或待更新会缩短共同窗口。</p
            >
          </template>
        </div>
      </ChartExpand>
      <details class="cycle-panel"
        ><summary>数据来源与实际覆盖</summary
        ><div class="cycle-table"
          ><table
            ><thead
              ><tr
                ><th>序列</th><th>来源</th><th>首个有效日</th><th>最新有效日</th><th>状态</th></tr
              ></thead
            ><tbody
              ><tr v-for="s in sourceRows" :key="s.id"
                ><th>{{ s.label }}</th
                ><td
                  ><a :href="s.sourceUrl || undefined" target="_blank" rel="noreferrer">{{
                    s.source || '—'
                  }}</a></td
                ><td>{{ s.start || '—' }}</td
                ><td>{{ s.end || '—' }}</td
                ><td>{{
                  s.status === 'ready' && !s.isStale ? '已读取' : '待更新 / 不完整'
                }}</td></tr
              ></tbody
            ></table
          ></div
        ></details
      >
    </template>
  </section>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, shallowRef } from 'vue';
  import type { EChartsOption } from 'echarts';
  import { readCycleInputs, type CycleInputs } from '@/api/researchCycles';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import ChartExpand from '../components/ChartExpand.vue';
  import CycleChart from '../components/CycleChart.vue';
  import {
    cleanPoints,
    correlationWindows,
    conditionalReturns,
    dayNumber,
    driverRegimes,
    economicRegimes,
    monthRange,
    eventReturn,
    policyTurns,
    regimeNames,
    rotation,
  } from '../charts/cycleAnalysis';

  const props = defineProps<{ compact?: boolean; asset?: string; mode?: 'drivers' | 'rotation' }>();
  const tabs = [
    { id: 'economy', label: '经济周期' },
    { id: 'policy', label: '货币政策周期' },
    { id: 'drivers', label: '资产驱动周期' },
    { id: 'rotation', label: '跨资产轮动' },
  ];
  const view = ref(props.mode || (props.compact ? 'drivers' : 'economy')),
    data = shallowRef<CycleInputs>(),
    loading = ref(false),
    error = ref('');
  let active = true,
    controller: AbortController | undefined;
  onBeforeUnmount(() => {
    active = false;
    controller?.abort();
  });
  async function load() {
    loading.value = true;
    controller?.abort();
    controller = new AbortController();
    try {
      const result = await readCycleInputs(controller.signal);
      if (active) {
        data.value = result;
        error.value = '';
      }
    } catch {
      if (active) error.value = '周期数据读取失败';
    } finally {
      if (active) loading.value = false;
    }
  }
  useDashboardRefresh(load);
  const country = ref('us'),
    startYear = ref(2005),
    horizon = ref(0),
    policyDirection = ref(-1),
    policyAsset = ref('us-spy'),
    driverAsset = ref('us-gld'),
    driverHorizon = ref(0),
    rotationMonths = ref(6);
  const indicator = (key: string) => data.value?.indicators[key]?.observations || [];
  const assetPoints = (id: string) => data.value?.assets[id]?.observations || [];
  const labels: Record<string, string> = {
    'us-spy': '美股 SPY',
    'us-gld': '黄金 ETF · GLD',
    'btc-usd': 'BTC / USD',
    'cn-hs300': '沪深300',
  };
  const label = (id: string) => labels[id] || id;
  const pct = (v: number | null, unit = '%') => (v == null ? '—' : v.toFixed(2) + unit);
  const usdAssets = computed(() =>
    ['us-spy', 'us-gld', 'btc-usd'].map((id) => ({
      id,
      label: label(id),
      observations: assetPoints(id),
    })),
  );
  const regimes = computed(() =>
    economicRegimes(indicator(country.value + 'Growth'), indicator(country.value + 'Inflation')),
  );
  const latestRegime = computed(() => regimes.value.at(-1));
  const visibleRegimes = computed(() =>
    regimes.value.filter((r) => Number(r.month.slice(0, 4)) >= startYear.value),
  );
  const economicReturns = computed(() =>
    (country.value === 'cn' ? ['cn-hs300'] : ['us-spy', 'us-gld', 'btc-usd']).flatMap((id) =>
      conditionalReturns(assetPoints(id), visibleRegimes.value, horizon.value).map((r) => ({
        ...r,
        asset: label(id),
      })),
    ),
  );
  const policy = computed(() => policyTurns(indicator('policy')));
  const policyEvents = computed(() =>
    policy.value.events.filter((e) => e.direction === policyDirection.value),
  );
  const policyPhase = computed(() =>
    !policy.value.lastChange || !policy.value.latest
      ? '暂无可识别调整'
      : (dayNumber(policy.value.latest.date) - dayNumber(policy.value.lastChange) >= 90
          ? '暂停调整≥90日 · '
          : '') + (policy.value.direction > 0 ? '最近方向：加息' : '最近方向：降息'),
  );
  const effectiveDriver = computed(() =>
    props.compact
      ? props.asset?.startsWith('cn-')
        ? 'cn-hs300'
        : props.asset?.startsWith('us-')
        ? 'us-spy'
        : props.asset === 'btc'
        ? 'btc-usd'
        : 'us-gld'
      : driverAsset.value,
  );
  const driverConfig = computed(
    () =>
      ({
        'us-gld': {
          keys: ['realYield', 'dollar'],
          labels: ['实际利率', '美元指数'],
          note: '黄金使用GLD ETF作为长历史价格代理，非本页XAUUSD现货序列。',
        },
        'us-spy': {
          keys: ['usGrowth', 'usInflation'],
          labels: ['工业生产同比', 'CPI同比'],
          note: '美股使用SPY价格收益，观察增长与通胀驱动。',
        },
        'cn-hs300': {
          keys: ['cnProfit', 'cnCredit'],
          labels: ['工业企业累计利润同比', '社融存量同比'],
          note: 'A股使用沪深300代理；工业企业累计利润不等于上市公司单季盈利，年初缺月保留。',
        },
        'btc-usd': {
          keys: ['liquidity', 'realYield'],
          labels: ['美元净流动性', '实际利率'],
          note: 'BTC使用美元跨交易所日均价，区别于月度表的Binance BTC/USDT。',
        },
      }[effectiveDriver.value]!),
  );
  const driverNames = computed(() => {
    const [a, b] = driverConfig.value.labels;
    return [`${a}↑ / ${b}↓`, `${a}↑ / ${b}↑`, `${a}↓ / ${b}↑`, `${a}↓ / ${b}↓`];
  });
  const driverReturns = computed(() =>
    conditionalReturns(
      assetPoints(effectiveDriver.value),
      driverRegimes(indicator(driverConfig.value.keys[0]), indicator(driverConfig.value.keys[1])),
      driverHorizon.value,
    ).map((r, i) => ({ ...r, name: driverNames.value[i] })),
  );
  const rotationData = computed(() => rotation(usdAssets.value, rotationMonths.value));
  const correlations = computed(() => correlationWindows(usdAssets.value));
  const leaderChanges = computed(() =>
    rotationData.value.history
      .filter((r, i, a) => i === 0 || r.ranks[0].id !== a[i - 1].ranks[0].id)
      .slice(-15)
      .reverse(),
  );
  const baseChart = {
    tooltip: {
      trigger: 'axis',
      valueFormatter: (v: unknown) => {
        const value = Array.isArray(v) ? v.at(-1) : v;
        return pct(value == null ? null : Number(value), view.value === 'economy' ? ' pp' : '%');
      },
    },
    legend: { type: 'scroll' },
    grid: { left: 65, right: 25, top: 45, bottom: 70 },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 10 }],
  };
  const economicChart = computed<EChartsOption>(
    () =>
      ({
        ...baseChart,
        xAxis: { type: 'category', data: economicTimeline.value.map((r) => r.month) },
        yAxis: { type: 'value', name: '变化 · pp' },
        series: [
          {
            name: '增长同比变化',
            type: 'line',
            showSymbol: false,
            data: economicTimeline.value.map((r) => r.growthDelta),
          },
          {
            name: '通胀同比变化',
            type: 'line',
            showSymbol: false,
            data: economicTimeline.value.map((r) => r.inflationDelta),
          },
        ],
      } as EChartsOption),
  );
  const economicTimeline = computed(() => {
    const rows = visibleRegimes.value,
      map = new Map(rows.map((r) => [r.month, r]));
    return monthRange(rows[0]?.month, rows.at(-1)?.month).map((month) => ({
      month,
      growthDelta: map.get(month)?.growthDelta ?? null,
      inflationDelta: map.get(month)?.inflationDelta ?? null,
    }));
  });
  const policyChart = computed<EChartsOption>(
    () =>
      ({
        ...baseChart,
        xAxis: { type: 'value', name: '距生效日日历天', min: -90, max: 365 },
        yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
        series: policyEvents.value.flatMap((e) => {
          const p = cleanPoints(assetPoints(policyAsset.value)),
            base = p.filter((x) => x.date < e.date).at(-1);
          if (!base || dayNumber(e.date) - dayNumber(base.date) > 7) return [];
          const visible = p.filter(
            (x) =>
              dayNumber(x.date) - dayNumber(e.date) >= -90 &&
              dayNumber(x.date) - dayNumber(e.date) <= 365,
          );
          return [
            {
              name: e.date,
              type: 'line',
              showSymbol: false,
              connectNulls: false,
              data: visible.flatMap((x, i, a) => {
                const day = dayNumber(x.date) - dayNumber(e.date),
                  gap = i > 0 && dayNumber(x.date) - dayNumber(a[i - 1].date) > 7;
                return [...(gap ? [[day - 1, null]] : []), [day, (x.value / base.value - 1) * 100]];
              }),
            },
          ];
        }),
      } as EChartsOption),
  );
  const driverChart = computed<EChartsOption>(() => ({
    tooltip: { trigger: 'axis', valueFormatter: (v) => pct(v == null ? null : Number(v)) },
    legend: {},
    grid: { left: 65, right: 25, top: 45, bottom: 95 },
    xAxis: {
      type: 'category',
      data: driverNames.value,
      axisLabel: { interval: 0, rotate: 15, fontSize: 10 },
    },
    yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
    series: [
      {
        name: '平均收益',
        type: 'bar',
        data: driverReturns.value.map((r) => r.mean),
        barMaxWidth: 45,
      },
      {
        name: '中位数',
        type: 'bar',
        data: driverReturns.value.map((r) => r.median),
        barMaxWidth: 45,
      },
    ],
  }));
  const rotationChart = computed<EChartsOption>(
    () =>
      ({
        ...baseChart,
        xAxis: { type: 'category', data: rotationTimeline.value.map((r) => r.month) },
        yAxis: { type: 'value', axisLabel: { formatter: '{value}%' } },
        series: usdAssets.value.map((s) => ({
          name: s.label,
          type: 'line',
          showSymbol: false,
          data: rotationTimeline.value.map(
            (r) => r.ranks.find((v) => v.id === s.id)?.value ?? null,
          ),
        })),
      } as EChartsOption),
  );
  const rotationTimeline = computed(() => {
    const rows = rotationData.value.history,
      map = new Map(rows.map((r) => [r.month, r]));
    return monthRange(rows[0]?.month, rows.at(-1)?.month).map((month) => ({
      month,
      ranks: map.get(month)?.ranks || [],
    }));
  });
  const chartTitle = computed(() => tabs.find((t) => t.id === view.value)?.label || '周期分析');
  const sourceRows = computed(() =>
    [
      ...Object.entries(data.value?.indicators || {}),
      ...Object.entries(data.value?.assets || {}),
    ].map(([id, s]) => {
      const points = cleanPoints(s.observations || [], false);
      return { ...s, id, start: points[0]?.date, end: points.at(-1)?.date };
    }),
  );
  const sourceWarnings = computed(() => {
    const ids =
      view.value === 'economy'
        ? [
            country.value + 'Growth',
            country.value + 'Inflation',
            ...(country.value === 'cn' ? ['cn-hs300'] : ['us-spy', 'us-gld', 'btc-usd']),
          ]
        : view.value === 'policy'
        ? ['policy', policyAsset.value]
        : view.value === 'drivers'
        ? [...driverConfig.value.keys, effectiveDriver.value]
        : ['us-spy', 'us-gld', 'btc-usd'];
    return sourceRows.value
      .filter((s) => ids.includes(s.id) && (s.status !== 'ready' || s.isStale))
      .map(
        (s) => `${labels[s.id] || s.label || s.id}：${s.end || '暂无有效数据'} · 待更新 / 不完整`,
      );
  });
</script>
<style scoped lang="less" src="../components/cyclePanels.less"></style>
<style scoped>
  .phase {
    font-size: 17px;
  }

  .cycle-analysis a {
    color: #165dff;
  }
</style>
