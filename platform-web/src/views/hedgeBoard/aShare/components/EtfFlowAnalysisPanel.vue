<template>
  <section class="flow-analysis" aria-label="ETF资金流向与持有人">
    <header class="heading"
      ><div
        ><span class="eyebrow">ETF FLOW & OWNERSHIP</span><h2>资金流向与持有人</h2
        ><p>从资产类别、跟踪方向到基金持有人，观察资金流向的变化。</p></div
      ><div class="mode-switch"
        ><button :aria-pressed="mode === 'real'" @click="changeMode('real')">真实数据</button
        ><button :aria-pressed="mode === 'demo'" @click="changeMode('demo')"
          >全市场 Demo</button
        ></div
      ></header
    >
    <div v-if="mode === 'demo'" class="demo-notice" role="status"
      ><strong>Demo · 全部数值均为合成数据</strong
      ><span>用于展示尚缺数据的大类、行业和持有人功能，不代表实际资金动向。</span></div
    >
    <div class="controls">
      <div class="presets"
        ><button
          v-for="p in presets"
          :key="p.days"
          :aria-pressed="preset === p.days"
          @click="choosePreset(p.days)"
          >{{ p.label }}</button
        ><button :aria-pressed="preset === -1" @click="quarterComparison"
          >前三季度 / 四季度以来</button
        ></div
      >
      <div class="date-controls"
        ><label>观察期<input v-model="start" type="date" aria-label="观察期开始" /></label
        ><span>至</span><input v-model="end" type="date" aria-label="观察期结束" /><label
          >比较期<input v-model="previousStart" type="date" aria-label="比较期开始" /></label
        ><span>至</span><input v-model="previousEnd" type="date" aria-label="比较期结束" /><button
          :disabled="loading"
          @click="applyDates"
          >应用区间</button
        ><button :disabled="loading" @click="load">刷新</button></div
      >
    </div>
    <p v-if="loading" role="status">正在读取资金流向…</p>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <template v-if="data && !loading && !error">
      <p class="source"
        >{{ data.source }} · 数据截至 {{ data.date
        }}<span v-if="data.retrievedAt"> · 采集 {{ time(data.retrievedAt) }}</span
        ><br />{{ data.scope }}</p
      >
      <p class="source"
        >观察期 {{ data.start }} — {{ data.end }}（{{ sessionCount(data.start, data.end)
        }}{{ mode === 'real' ? '个交易日' : '个模拟工作日' }}）；比较期 {{ data.previousStart }} —
        {{ data.previousEnd }}（{{ sessionCount(data.previousStart, data.previousEnd) }}日）。{{
          isDemo
            ? '本页数值为合成样本。'
            : '净流入按相邻交易日份额变动 × 同日单位净值估算，沿用原始采集的份额折算处理。'
        }}</p
      >
      <div class="metrics"
        ><article
          ><span>{{ mode === 'real' ? '已跟踪样本' : '模拟样本' }}净流入</span
          ><strong :class="tone(data.summary.current.flow)"
            >{{ fmt(data.summary.current.flow) }}<small>亿元</small></strong
          ><span>{{ completeness(data.summary.current) }}</span></article
        ><article
          ><span>股票宽基净流入</span
          ><strong :class="tone(broadAsset?.current.flow)"
            >{{ fmt(broadAsset?.current.flow) }}<small>亿元</small></strong
          ><span
            >{{ broadAsset?.count || 0 }} 只ETF ·
            {{ broadAsset ? completeness(broadAsset.current) : '—' }}</span
          ></article
        ><article
          ><span>可得净流入最多的方向</span
          ><strong class="leader">{{ leader?.name || '暂无有效样本' }}</strong
          ><span
            >{{ fmt(leader?.current.flow) }} 亿元 ·
            {{ leader ? completeness(leader.current) : '—' }}</span
          ></article
        ><article
          ><span>原始输入覆盖</span><strong>{{ coverage }}<small>%</small></strong
          ><span
            >{{ data.summary.current.covered }} / {{ data.summary.current.expected }} 基金交易日 ·
            {{ data.funds.length }} 只ETF</span
          ></article
        ></div
      >
      <nav class="views" aria-label="资金流向分析视角"
        ><button
          v-for="v in views"
          :key="v.key"
          :aria-pressed="view === v.key"
          @click="view = v.key"
          >{{ v.label }}</button
        ></nav
      >
      <template v-if="view === 'landscape'">
        <EtfFlowChart
          :items="sorted(data.assets)"
          :demo="isDemo"
          :title="isDemo ? '全市场资产类别资金流向 · Demo' : '已跟踪样本 · 大类资金流向'"
          :note="flowNote"
        />
        <div class="chart-grid"
          ><EtfFlowChart
            :items="inflow"
            :demo="isDemo"
            title="细分方向 · 净流入 TOP 5"
            :note="flowNote" /><EtfFlowChart
            :items="outflow"
            :demo="isDemo"
            title="细分方向 · 净流出 TOP 5"
            :note="flowNote"
        /></div>
        <EtfFlowChart
          :items="sorted(sectors)"
          :demo="isDemo"
          title="行业与策略方向资金流向"
          :note="
            isDemo
              ? '各细分方向独立模拟，不代表真实行业排名。'
              : '按现有基金分类合计；仅覆盖目录内成员，不代表完整行业。部分值为可得合计。'
          "
        />
      </template>
      <template v-else-if="view === 'turn'">
        <EtfFlowChart
          :items="data.assets"
          kind="comparison"
          :demo="isDemo"
          title="资金转折 · 两阶段资金流向"
          :note="comparisonNote"
        />
        <div class="chart-grid"
          ><EtfFlowChart
            :items="broadGroups"
            kind="ratio"
            :demo="isDemo"
            title="宽基赎回与回补 · 占期初规模"
            note="各期净流入 ÷ 各自期初净资产规模。输入不完整或期初规模不可得时留空。" /><EtfFlowChart
            :items="broadGroups"
            kind="recovery"
            :demo="isDemo"
            title="宽基资金回补率"
            note="观察期净流入 ÷ 比较期净流出绝对值；仅前期净流出、后期净流入且两期完整时计算。超过100%表示金额已回补。"
        /></div>
        <EtfFlowChart
          :items="sectors"
          kind="comparison"
          :demo="isDemo"
          title="细分方向资金变化"
          :note="comparisonNote"
        />
        <div class="panel"
          ><h3>细分方向变化明细</h3
          ><div class="table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>方向</th><th>比较期（亿元）</th><th>观察期（亿元）</th
                  ><th>金额变化（亿元）</th><th>方向变化</th></tr
                ></thead
              ><tbody
                ><tr v-for="g in sectors" :key="g.name"
                  ><td>{{ g.name }}</td
                  ><td>{{ fmt(g.previous.flow) }}</td
                  ><td :class="tone(g.current.flow)">{{ fmt(g.current.flow) }}</td
                  ><td>{{ change(g) }}</td
                  ><td>{{ transition(g) }}</td></tr
                ></tbody
              ></table
            ></div
          ><p class="source"
            >金额变化＝观察期−比较期；两期长度不同时不代表流入速度变化。不完整区间不判断转向。</p
          ></div
        >
      </template>
      <template v-else>
        <div class="panel"
          ><h3>跟踪方向汇总</h3
          ><p class="source"
            >按已确认分类去重汇总；分类不等同于完整指数产品目录。点击方向筛选下方ETF。</p
          ><div class="table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>跟踪方向</th><th>ETF数</th><th>期初规模（亿元）</th
                  ><th>观察期净流入（亿元）</th><th>占期初规模</th><th>比较期（亿元）</th
                  ><th>观察期覆盖</th></tr
                ></thead
              ><tbody
                ><tr v-for="g in sorted(data.groups)" :key="g.name"
                  ><td
                    ><button
                      class="fund-link"
                      @click="
                        groupFilter = g.name;
                        assetFilter = '';
                      "
                      >{{ g.name }}</button
                    ></td
                  ><td>{{ g.count }}</td
                  ><td>{{ fmt(g.current.scale) }}</td
                  ><td :class="tone(g.current.flow)">{{ fmt(g.current.flow) }}</td
                  ><td>{{ pct(g.current.ratio) }}</td
                  ><td>{{ fmt(g.previous.flow) }}</td
                  ><td>{{ completeness(g.current) }}</td></tr
                ></tbody
              ></table
            ></div
          ></div
        >
        <div class="panel"
          ><header class="table-heading"
            ><h3>跟踪方向与ETF明细</h3><button @click="exportCsv">导出当前筛选</button></header
          ><div class="table-filters"
            ><input
              v-model="search"
              placeholder="搜索代码、名称或跟踪方向"
              aria-label="搜索ETF"
            /><select v-model="assetFilter" aria-label="ETF资产类别"
              ><option value="">全部资产类别</option
              ><option v-for="a in data.assets" :key="a.name">{{ a.name }}</option></select
            ><select v-model="groupFilter" aria-label="ETF跟踪方向"
              ><option value="">全部跟踪方向</option
              ><option v-for="g in data.groups" :key="g.name">{{ g.name }}</option></select
            ><select v-model="sortKey" aria-label="ETF排序"
              ><option value="flow">净流入金额</option
              ><option value="ratio">净流入／期初规模</option
              ><option value="change">两期金额变化</option></select
            ><button @click="ascending = !ascending">{{
              ascending ? '从低到高' : '从高到低'
            }}</button></div
          ><div class="table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>代码 / 名称</th><th>资产 / 跟踪方向</th><th>期初规模（亿元）</th
                  ><th>观察期净流入（亿元）</th><th>占期初规模</th><th>比较期（亿元）</th
                  ><th>输入覆盖</th><th>最近有效日</th></tr
                ></thead
              ><tbody
                ><tr
                  v-for="f in pagedFunds"
                  :key="f.code"
                  :class="{ selected: selectedFund === f.code }"
                  ><td
                    ><button class="fund-link" @click="selectedFund = f.code"
                      >{{ f.code }} · {{ f.name }}</button
                    ></td
                  ><td>{{ f.asset }} / {{ f.group }}</td
                  ><td>{{ fmt(f.current.scale) }}</td
                  ><td :class="tone(f.current.flow)">{{ fmt(f.current.flow) }}</td
                  ><td>{{ pct(f.current.ratio) }}</td
                  ><td>{{ fmt(f.previous.flow) }}</td
                  ><td>{{ completeness(f.current) }}</td
                  ><td>{{ f.sourceDate || '—' }}</td></tr
                ><tr v-if="!filteredFunds.length"><td colspan="8">没有匹配的ETF。</td></tr></tbody
              ></table
            ></div
          ><div class="pagination"
            ><span>{{ filteredFunds.length }} 只</span
            ><button :disabled="page === 1" @click="page--">上一页</button
            ><span>{{ page }} / {{ pages }}</span
            ><button :disabled="page === pages" @click="page++">下一页</button></div
          ></div
        >
        <div class="panel"
          ><header class="table-heading"
            ><h3>持有人结构</h3
            ><select v-model="selectedFund" aria-label="持有人分析ETF"
              ><option v-for="f in data.funds" :key="f.code" :value="f.code"
                >{{ f.code }} · {{ f.name }}</option
              ></select
            ></header
          ><template v-if="chosenFund && !isDemo"
            ><p class="source"
              >已归档的汇金／证金合并持仓口径 · 报告期
              {{
                chosenFund.reportDate || '未采集'
              }}。此处为历史披露，非当前持仓；该ETF的前十大机构名单及逐期增减未完整采集。</p
            ><div class="holding-metrics"
              ><span
                >合并持仓比例 <strong>{{ pct(chosenFund.holdingRatio) }}</strong></span
              ><span
                >合并持仓市值 <strong>{{ fmt(chosenFund.holdingValue) }} 亿元</strong></span
              ></div
            ><p class="source"
              >来源：平台既有基金定期报告整理归档；旧披露尚未逐条独立核验。ETF净申赎包含全部持有人，不能据此确认某个机构在买入。</p
            ></template
          ><template v-else-if="chosenFund"
            ><p class="demo-notice"
              >Demo ·
              虚构机构与持仓比例，示例报告期为2026-06-30与2026-09-30，独立于上方资金流区间。</p
            ><div class="table-scroll"
              ><table
                ><thead
                  ><tr
                    ><th>机构（虚构）</th><th>前期占比</th><th>本期占比</th><th>变化（百分点）</th
                    ><th>动向</th></tr
                  ></thead
                ><tbody
                  ><tr v-for="h in holders" :key="h.name"
                    ><td>{{ h.name }}</td
                    ><td>{{ h.before.toFixed(2) }}%</td><td>{{ h.after.toFixed(2) }}%</td
                    ><td :class="tone(String(h.delta))">{{ h.delta.toFixed(2) }}</td
                    ><td>{{ h.state }}</td></tr
                  ></tbody
                ></table
              ></div
            ><p class="source"
              >两期前十大持有人并集示例，退出者保留为零；真实披露未接入。</p
            ></template
          ></div
        >
      </template>
    </template>
  </section>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import {
    getEtfFlows,
    type FlowAnalysis,
    type FlowFund,
    type FlowGroup,
    type FlowPeriod,
  } from '@/api/etfFlows';
  import EtfFlowChart from './EtfFlowChart.vue';
  import { demoHolders, etfFlowDemo } from './etfFlowDemo';

  const props = defineProps<{ refreshKey?: number }>();
  const emit = defineEmits<{ ready: [] }>();
  const mode = ref<'real' | 'demo'>('real'),
    view = ref('landscape');
  const isDemo = computed(() => mode.value === 'demo');
  const data = shallowRef<FlowAnalysis>();
  const loading = ref(false),
    error = ref(''),
    preset = ref(20);
  const start = ref(''),
    end = ref(''),
    previousStart = ref(''),
    previousEnd = ref('');
  const params = shallowRef<Record<string, string | number>>({ days: 20 });
  const presets = [
    { days: 1, label: '近1日' },
    { days: 5, label: '近1周 · 5日' },
    { days: 20, label: '近1月 · 20日' },
    { days: 60, label: '近1季 · 60日' },
    { days: 250, label: '近1年 · 250日' },
  ];
  const views = [
    { key: 'landscape', label: '资金全景' },
    { key: 'turn', label: '阶段变化与回补' },
    { key: 'holders', label: '跟踪方向与持有人' },
  ];
  const search = ref(''),
    assetFilter = ref(''),
    groupFilter = ref(''),
    sortKey = ref('flow'),
    ascending = ref(false),
    page = ref(1),
    selectedFund = ref('');
  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    const current = (controller = new AbortController());
    loading.value = true;
    error.value = '';
    try {
      const result = isDemo.value
        ? etfFlowDemo(params.value)
        : await getEtfFlows(params.value, current.signal);
      if (current.signal.aborted) return;
      if (!result.sessions.length) throw new Error('empty');
      data.value = result;
      start.value = result.start;
      end.value = result.end;
      previousStart.value = result.previousStart;
      previousEnd.value = result.previousEnd;
      if (!result.funds.some((f) => f.code === selectedFund.value))
        selectedFund.value = result.funds[0]?.code || '';
    } catch {
      if (!current.signal.aborted)
        error.value = isDemo.value
          ? '此区间不在演示样本内，请选择2025-01-01至2026-11-09之间的有效比较区间。'
          : '资金流向读取失败或所选区间无可用样本，请检查区间后重试。';
    } finally {
      if (!current.signal.aborted) {
        loading.value = false;
        emit('ready');
      }
    }
  }
  function choosePreset(days: number) {
    preset.value = days;
    params.value = { days };
    void load();
  }
  function changeMode(value: 'real' | 'demo') {
    if (mode.value === value) return;
    mode.value = value;
    data.value = undefined;
    assetFilter.value = '';
    groupFilter.value = '';
    selectedFund.value = '';
    choosePreset(20);
  }
  function applyDates() {
    if (
      !start.value ||
      !end.value ||
      !previousStart.value ||
      !previousEnd.value ||
      start.value > end.value ||
      previousStart.value > previousEnd.value ||
      previousEnd.value >= start.value
    ) {
      error.value = '请填写有效起止日期，比较期须在观察期之前且不重叠。';
      return;
    }
    preset.value = 0;
    params.value = {
      start: start.value,
      end: end.value,
      previous_start: previousStart.value,
      previous_end: previousEnd.value,
    };
    void load();
  }
  function quarterComparison() {
    if (!data.value) return;
    const year = data.value.date.slice(0, 4);
    if (data.value.date < `${year}-10-01`) {
      error.value = '当前数据尚未覆盖四季度。';
      return;
    }
    preset.value = -1;
    params.value = {
      start: `${year}-10-01`,
      end: data.value.date,
      previous_start: `${year}-01-01`,
      previous_end: `${year}-09-30`,
    };
    void load();
  }
  watch(() => props.refreshKey, load, { immediate: true });
  onBeforeUnmount(() => controller?.abort());
  const fmt = (v: string | number | null | undefined) =>
    v == null || !Number.isFinite(Number(v))
      ? '—'
      : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  const pct = (v: string | null | undefined) => (v == null ? '—' : `${fmt(v)}%`);
  const tone = (v: string | null | undefined) =>
    v == null ? '' : Number(v) > 0 ? 'positive' : Number(v) < 0 ? 'negative' : '';
  const time = (v: string) =>
    new Date(v).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
  const completeness = (p: FlowPeriod) =>
    p.complete ? '完整' : `可得合计 ${p.covered}/${p.expected}`;
  const sessionCount = (a: string, b: string) =>
    data.value?.sessions.filter((d) => d >= a && d <= b).length || 0;
  const sorted = (rows: FlowGroup[]) =>
    [...rows].sort((a, b) =>
      a.current.flow == null
        ? 1
        : b.current.flow == null
        ? -1
        : Number(b.current.flow) - Number(a.current.flow),
    );
  const broadAsset = computed(() => data.value?.assets.find((a) => a.name === '股票宽基'));
  const broadNames = computed(
    () => new Set(data.value?.funds.filter((f) => f.asset === '股票宽基').map((f) => f.group)),
  );
  const broadGroups = computed(
    () => data.value?.groups.filter((g) => broadNames.value.has(g.name)) || [],
  );
  const sectors = computed(
    () =>
      data.value?.groups.filter(
        (g) =>
          !broadNames.value.has(g.name) &&
          data.value?.funds.some(
            (f) => f.group === g.name && ['行业主题', '行业与策略'].includes(f.asset),
          ),
      ) || [],
  );
  const inflow = computed(() =>
    sorted(sectors.value)
      .filter((g) => g.current.flow != null && Number(g.current.flow) > 0)
      .slice(0, 5),
  );
  const outflow = computed(() =>
    sorted(sectors.value)
      .filter((g) => g.current.flow != null && Number(g.current.flow) < 0)
      .reverse()
      .slice(0, 5),
  );
  const leader = computed(() =>
    sorted(data.value?.groups || []).find(
      (g) => g.current.flow != null && Number(g.current.flow) > 0,
    ),
  );
  const coverage = computed(() =>
    data.value?.summary.current.expected
      ? ((100 * data.value.summary.current.covered) / data.value.summary.current.expected).toFixed(
          1,
        )
      : '—',
  );
  const flowNote = computed(
    () =>
      `观察期 ${data.value?.start} — ${data.value?.end}；红色流入、绿色流出。缺失不补零，不完整分类显示可得合计。`,
  );
  const comparisonNote = computed(
    () =>
      `比较期 ${data.value?.previousStart} — ${data.value?.previousEnd}；观察期 ${data.value?.start} — ${data.value?.end}。两期金额未按天数标准化，缺数时为可得合计。`,
  );
  function change(g: FlowGroup) {
    return g.current.complete &&
      g.previous.complete &&
      g.current.flow != null &&
      g.previous.flow != null
      ? fmt(Number(g.current.flow) - Number(g.previous.flow))
      : '—';
  }
  function transition(g: FlowGroup) {
    if (!g.current.complete || !g.previous.complete) return '区间不完整';
    const a = Number(g.previous.flow),
      b = Number(g.current.flow);
    return a < 0 && b > 0
      ? '转为净流入'
      : a > 0 && b < 0
      ? '转为净流出'
      : b > 0
      ? '净流入'
      : b < 0
      ? '净流出'
      : '持平';
  }
  function sortValue(f: FlowFund): number | null {
    if (sortKey.value === 'ratio') return f.current.ratio == null ? null : Number(f.current.ratio);
    if (sortKey.value === 'change')
      return change(f) === '—' ? null : Number(f.current.flow) - Number(f.previous.flow);
    return f.current.flow == null ? null : Number(f.current.flow);
  }
  const filteredFunds = computed(() =>
    (data.value?.funds || [])
      .filter(
        (f) =>
          (!assetFilter.value || f.asset === assetFilter.value) &&
          (!groupFilter.value || f.group === groupFilter.value) &&
          `${f.code} ${f.name} ${f.group}`
            .toLowerCase()
            .includes(search.value.trim().toLowerCase()),
      )
      .sort((a, b) => {
        const x = sortValue(a),
          y = sortValue(b);
        return x == null ? (y == null ? 0 : 1) : y == null ? -1 : ascending.value ? x - y : y - x;
      }),
  );
  const pages = computed(() => Math.max(1, Math.ceil(filteredFunds.value.length / 15)));
  const pagedFunds = computed(() =>
    filteredFunds.value.slice((page.value - 1) * 15, page.value * 15),
  );
  watch([search, assetFilter, groupFilter, sortKey, ascending, data], () => {
    page.value = 1;
  });
  const chosenFund = computed(() => data.value?.funds.find((f) => f.code === selectedFund.value));
  const holders = computed(() => demoHolders(selectedFund.value));
  function exportCsv() {
    if (!data.value) return;
    const cell = (v: unknown) =>
      `"${String(v ?? '')
        .replace(/^[=+@-]/, "'$&")
        .replace(/"/g, '""')}"`;
    const rows = [
      [
        '状态',
        '观察期',
        '比较期',
        '代码',
        '名称',
        '类别',
        '方向',
        '净流入亿元',
        '期初规模亿元',
        '占期初规模百分比',
        '比较期净流入亿元',
        '覆盖',
        '应有',
        '最近有效日',
      ],
      ...filteredFunds.value.map((f) => [
        isDemo.value ? 'Demo合成数据' : completeness(f.current),
        `${data.value!.start}~${data.value!.end}`,
        `${data.value!.previousStart}~${data.value!.previousEnd}`,
        f.code,
        f.name,
        f.asset,
        f.group,
        f.current.flow,
        f.current.scale,
        f.current.ratio,
        f.previous.flow,
        f.current.covered,
        f.current.expected,
        f.sourceDate,
      ]),
    ];
    const url = URL.createObjectURL(
      new Blob(['\ufeff' + rows.map((r) => r.map(cell).join(',')).join('\r\n')], {
        type: 'text/csv;charset=utf-8',
      }),
    );
    const link = document.createElement('a');
    link.href = url;
    link.download = `ETF资金流向-${mode.value}-${data.value.end}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
</script>
<style scoped>
  .flow-analysis {
    min-width: 0;
    color: #243b53;
  }

  .heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 10px 0 18px;
    gap: 16px;
  }

  .eyebrow {
    color: #8d6b40;
    font-size: 10px;
    letter-spacing: 1.8px;
  }

  h2 {
    margin: 4px 0;
    font-size: 23px;
    font-weight: 600;
  }

  h3 {
    margin: 0 0 10px;
    font-size: 15px;
  }

  .heading p,
  .source {
    margin: 6px 0 14px;
    color: #64748b;
    font-size: 12px;
    line-height: 1.8;
  }

  button,
  select,
  input {
    max-width: 100%;
    padding: 6px 9px;
    border: 1px solid #dbe4ee;
    border-radius: 6px;
    background: #fff;
    color: #36516c;
    font-size: 12px;
  }

  button {
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.45;
    cursor: default;
  }

  button[aria-pressed='true'] {
    border-color: #34567e;
    background: #34567e;
    color: #fff;
  }

  .mode-switch,
  .presets,
  .date-controls,
  .views,
  .table-filters,
  .pagination {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    align-items: center;
  }

  .mode-switch {
    flex-shrink: 0;
  }

  .controls {
    padding: 14px;
    border: 1px solid #e1e7ee;
    border-radius: 10px;
    background: #f7f9fc;
  }

  .date-controls {
    margin-top: 12px;
  }

  .date-controls label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
  }

  .date-controls > span {
    color: #64748b;
    font-size: 12px;
  }

  .date-controls input {
    width: 135px;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 16px 0;
  }

  .metrics article {
    display: flex;
    flex-direction: column;
    padding: 16px;
    border: 1px solid #dbe4ee;
    border-radius: 9px;
    background: white;
    gap: 8px;
  }

  .metrics span {
    color: #64748b;
    font-size: 12px;
  }

  .metrics strong {
    font-size: 26px;
    font-variant-numeric: tabular-nums;
    line-height: 1.25;
  }

  .metrics strong.leader {
    font-size: 19px;
  }

  .metrics small {
    margin-left: 5px;
    font-size: 11px;
    font-weight: 400;
  }

  .views {
    margin: 18px 0;
  }

  .chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    margin: 14px 0;
  }

  .panel {
    margin: 14px 0;
    padding: 18px;
    border: 1px solid #dbe4ee;
    border-radius: 10px;
    background: #fff;
  }

  .table-scroll {
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 10px 12px;
    border-bottom: 1px solid #edf1f5;
    text-align: right;
    white-space: nowrap;
  }

  th {
    background: #f8fafc;
    color: #64748b;
    font-weight: 500;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  .table-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    gap: 12px;
  }

  .table-heading h3 {
    margin: 0;
  }

  .table-filters {
    margin-bottom: 12px;
  }

  .table-filters input {
    min-width: 220px;
  }

  .pagination {
    justify-content: flex-end;
    margin-top: 12px;
    font-size: 12px;
  }

  .fund-link {
    padding: 0;
    border: 0;
    background: none;
    color: #2864aa;
    text-align: left;
  }

  .selected {
    background: #f0f5fb;
  }

  .positive {
    color: #bd3e31;
  }

  .negative {
    color: #2b7a50;
  }

  .error {
    color: #b3382c;
    font-size: 13px;
  }

  .demo-notice {
    display: flex;
    flex-wrap: wrap;
    margin: 12px 0;
    padding: 12px 14px;
    border: 1px solid #efdab7;
    border-radius: 8px;
    background: #fff7e8;
    color: #8b621e;
    font-size: 12px;
    line-height: 1.8;
    gap: 8px;
  }

  .holding-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 28px;
    font-size: 13px;
  }

  .holding-metrics strong {
    margin-left: 12px;
    font-size: 22px;
  }

  @media (max-width: 1000px) {
    .metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .chart-grid {
      grid-template-columns: 1fr;
    }

    .heading {
      flex-direction: column;
      align-items: flex-start;
    }
  }

  @media (max-width: 520px) {
    .metrics {
      grid-template-columns: 1fr;
    }

    .panel {
      padding: 12px;
    }

    .date-controls {
      align-items: flex-end;
    }

    .table-filters input {
      width: 100%;
      min-width: 0;
    }
  }
</style>
