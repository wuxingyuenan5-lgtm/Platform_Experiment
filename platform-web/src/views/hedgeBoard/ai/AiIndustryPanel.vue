<template>
  <section class="ai-board" aria-label="美股AI产业研究">
    <header class="board-head"
      ><div
        ><p class="eyebrow">AI INDUSTRY · US EQUITIES</p><h2>AI产业</h2
        ><p class="muted">资本投入 → 需求兑现 → 现金回报 → 信用与融资</p></div
      ><div class="head-right"
        ><span>{{
          data?.generatedAt ? '更新检查 ' + new Date(data.generatedAt).toLocaleString('zh-CN') : ''
        }}</span
        ><button :disabled="loading" @click="load">{{
          loading ? '读取中…' : '刷新本地数据'
        }}</button></div
      ></header
    >
    <p v-if="error" class="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <p v-if="loading && !data" class="loading">正在读取AI产业研究数据…</p>
    <template v-if="data">
      <div class="stats"
        ><article
          ><small>产业链覆盖</small
          ><strong
            >{{ data.companies.filter((c) => c.latest).length }} /
            {{ data.companies.length }}</strong
          ><span>云、芯片、硬件、电力、软件、安全</span></article
        ><article
          ><small>四大云厂商 · 同季现金Capex</small
          ><strong>{{ compact(lastCapex?.capex) }} <em>十亿美元</em></strong
          ><span
            >{{ lastCapex?.date || '暂无共同季度' }} · MSFT / AMZN / GOOGL / META</span
          ></article
        ><article
          ><small>经营现金流减Capex · 同季合计</small
          ><strong>{{ compact(lastCapex?.fcf) }} <em>十亿美元</em></strong
          ><span>公司整体口径，不等同于纯AI投入</span></article
        ><article
          ><small>ARR披露覆盖 / CDS覆盖</small
          ><strong>{{ arrCoverage }} / {{ data.cds.length }}</strong
          ><span>公司数；不同产品ARR不相加</span></article
        ></div
      >
      <nav class="tabs" aria-label="AI研究分区"
        ><button
          v-for="item in tabs"
          :key="item.key"
          :class="{ active: tab === item.key }"
          :aria-pressed="tab === item.key"
          @click="tab = item.key"
          >{{ item.name }}</button
        ></nav
      >
      <div class="filters"
        ><label
          >产业环节
          <select v-model="sector"
            ><option value="">全部环节</option
            ><option v-for="s in sectors" :key="s">{{ s }}</option></select
          ></label
        ><label>搜索 <input v-model="search" placeholder="代码 / 公司" /></label
        ><label
          >公司
          <select v-model="selected"
            ><option v-for="c in data.companies" :key="c.ticker" :value="c.ticker"
              >{{ c.ticker }} · {{ c.name }}</option
            ></select
          ></label
        ><div class="period-switch"
          ><button :class="{ active: period === 'quarter' }" @click="period = 'quarter'"
            >单季</button
          ><button :class="{ active: period === 'ttm' }" @click="period = 'ttm'">TTM</button></div
        ></div
      >
      <p v-if="detailError && tab !== 'details'" class="error" role="alert"
        >{{ selected }}：{{ detailError }} <button @click="loadDetail">重试公司历史</button></p
      >
      <p v-if="detailLoading && tab !== 'overview' && tab !== 'details'" class="muted"
        >正在读取 {{ selected }} 的历史数据…</p
      >
      <template v-if="tab === 'overview'">
        <article class="card"
          ><header
            ><h3>产业链财务比较</h3
            ><span class="muted">金额：十亿美元；各公司最新财季不同，日期分别列示</span></header
          ><div class="table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>公司 / 环节</th><th>财季结束</th
                  ><th><button @click="sortBy('revenue')">收入 ↕</button></th
                  ><th><button @click="sortBy('revenueYoy')">收入同比 ↕</button></th
                  ><th><button @click="sortBy('capex')">Capex ↕</button></th
                  ><th>Capex/收入</th><th>经营现金流</th
                  ><th><button @click="sortBy('fcf')">自由现金流 ↕</button></th
                  ><th>经营利润率</th><th>SBC/收入</th><th>核对</th></tr
                ></thead
              ><tbody
                ><tr
                  v-for="c in visibleCompanies"
                  :key="c.ticker"
                  :class="{ selected: c.ticker === selected }"
                  @click="selected = c.ticker"
                  ><td
                    ><button
                      class="company-link"
                      @click.stop="
                        selected = c.ticker;
                        tab = 'details';
                      "
                      >{{ c.ticker }} · {{ c.name }}</button
                    ><small>{{ c.sector }}</small></td
                  ><td
                    >{{ c.periodEnd || '—'
                    }}<small v-if="c.status === 'stale'">历史或来源待更新</small></td
                  ><td>{{ compact(values(c).revenue) }}</td
                  ><td>{{
                    period === 'quarter' ? format(c.latest?.yoy?.revenue, 'percent') : '—'
                  }}</td
                  ><td>{{ compact(values(c).capex) }}</td
                  ><td>{{ format(values(c).capexRevenue, 'percent') }}</td
                  ><td>{{ compact(values(c).cfo) }}</td
                  ><td :class="tone(values(c).fcf)">{{ compact(values(c).fcf) }}</td
                  ><td>{{ format(values(c).operatingMargin, 'percent') }}</td
                  ><td>{{ format(values(c).sbcRevenue, 'percent') }}</td
                  ><td
                    ><span :class="checkStatus(c) === '有差异' ? 'warning' : 'muted'">{{
                      checkStatus(c)
                    }}</span></td
                  ></tr
                ></tbody
              ></table
            ><p v-if="!visibleCompanies.length" class="muted">没有符合筛选的公司</p></div
          ></article
        >
        <div class="two-column"
          ><Safe widget-title="云厂商资本开支"
            ><AiChart
              title="四大云厂商 · 季度现金资本开支"
              :rows="cloudRows"
              :lines="cloudLines" /></Safe
          ><Safe widget-title="投入与现金回报"
            ><AiChart
              title="四大云厂商 · 投入与现金回报"
              :rows="cloudRows"
              :lines="cashLines"
              note="仅汇总四家公司起止日完全一致的季度；不包含租赁非现金新增资产。" /></Safe
        ></div>
      </template>
      <template v-if="tab === 'capex'">
        <Safe widget-title="资本开支历史"
          ><AiChart
            title="四大云厂商 · 季度现金资本开支"
            :rows="cloudRows"
            :lines="cloudLines"
            :note="data.metricDefinitions?.capex"
        /></Safe>
        <div class="two-column"
          ><Safe widget-title="公司现金回报"
            ><AiChart
              :title="selected + ' · Capex与经营现金流'"
              :rows="companyRows"
              :lines="cashLines" /></Safe
          ><Safe widget-title="投入强度"
            ><AiChart
              :title="selected + ' · 投入强度'"
              :rows="companyRows"
              :lines="intensityLines"
              unit="%" /></Safe
        ></div>
        <article class="card"
          ><h3>公司披露 · 投入与商业化</h3
          ><div class="table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>公司</th><th>披露项目</th><th>披露值</th><th>观察期末</th><th>口径</th
                  ><th>原文</th></tr
                ></thead
              ><tbody
                ><tr v-for="d in disclosures" :key="d.ticker + d.name"
                  ><td>{{ d.ticker }}</td
                  ><td>{{ d.name }}</td
                  ><td
                    >{{ d.qualifier }}{{ format(d.value)
                    }}{{ d.upper ? ' — ' + format(d.upper) : '' }}</td
                  ><td>{{ d.date }}</td
                  ><td>{{ d.basis }}</td
                  ><td
                    ><a :href="d.sourceUrl" target="_blank" rel="noopener noreferrer"
                      >公司披露 ↗</a
                    ></td
                  ></tr
                ></tbody
              ></table
            ><p v-if="!disclosures.length" class="muted">暂无通过口径核验的公司披露</p></div
          ></article
        >
      </template>
      <template v-if="tab === 'demand'">
        <article class="card"
          ><header
            ><h3>ARR、RPO与需求兑现</h3
            ><label
              >指标类型
              <select v-model="kpiKind"
                ><option value="">全部</option
                ><option v-for="kind in kpiKinds" :key="kind">{{ kind }}</option></select
              ></label
            ></header
          ><p class="definition"
            >ARR是经常性合同金额的年化存量；RPO是尚未确认的履约义务，包含未来多年收入。云/数据中心收入包含非AI业务，不作为纯AI收入。</p
          ><div class="table-scroll demand-table"
            ><table
              ><thead
                ><tr
                  ><th>公司</th><th>指标</th><th>类别</th><th>最新值</th><th>观察日期</th
                  ><th>来源</th></tr
                ></thead
              ><tbody
                ><tr
                  v-for="k in allKpis"
                  :key="k.id"
                  :class="{ selected: k.id === kpiId }"
                  @click="kpiId = k.id"
                  ><td>{{ k.ticker }}</td
                  ><td
                    ><button class="company-link" @click="kpiId = k.id">{{ k.name }}</button></td
                  ><td>{{ k.kind }}</td
                  ><td>{{ format(k.latest.value, k.unit) }}</td
                  ><td>{{ k.latest.date }}</td
                  ><td
                    ><a :href="k.sourceUrl" target="_blank" rel="noopener noreferrer"
                      >经营指标 ↗</a
                    ></td
                  ></tr
                ></tbody
              ></table
            ><p v-if="!allKpis.length" class="muted"
              >该筛选下暂无公开披露；未以年化收入代替ARR。</p
            ></div
          ></article
        >
        <Safe widget-title="经营指标历史"
          ><AiChart
            :key="activeKpi?.id || 'empty'"
            :title="activeKpi ? activeKpi.ticker + ' · ' + activeKpi.name : '选择经营指标'"
            :rows="kpiRows"
            :lines="[{ key: 'value', name: activeKpi?.name || '指标', color: '#2563eb' }]"
            :unit="
              activeKpi?.unit === 'USD' ? '十亿美元' : activeKpi?.unit === 'percent' ? '%' : '数量'
            "
            :note="activeKpi ? activeKpi.basis + ' · ' + activeKpi.source : ''"
        /></Safe>
        <article v-if="disclosures.length" class="card"
          ><h3>AI产品ARR · 公司原文</h3
          ><div class="disclosures"
            ><article v-for="d in disclosures.filter((x) => x.kind === 'ARR')" :key="d.name"
              ><small>{{ d.ticker }} · {{ d.date }}</small
              ><h4>{{ d.name }}</h4
              ><strong>{{ d.qualifier }}{{ format(d.value) }}</strong
              ><p>{{ d.basis }}</p
              ><a :href="d.sourceUrl" target="_blank" rel="noopener noreferrer"
                >公司原文 ↗</a
              ></article
            ></div
          ></article
        >
      </template>
      <template v-if="tab === 'returns'">
        <div class="company-stats"
          ><article
            v-for="key in [
              'revenue',
              'operatingMargin',
              'fcf',
              'fcfMargin',
              'sbcRevenue',
              'interestCoverage',
            ]"
            :key="key"
            ><small>{{ label[key] }} · {{ period === 'ttm' ? 'TTM' : '单季' }}</small
            ><strong>{{
              percentage(key)
                ? format(values(current)[key], 'percent')
                : key === 'interestCoverage'
                ? format(values(current)[key], 'times')
                : compact(values(current)[key])
            }}</strong
            ><span v-if="!percentage(key) && key !== 'interestCoverage'">十亿美元</span></article
          ></div
        >
        <div class="two-column"
          ><Safe widget-title="利润率"
            ><AiChart
              :title="selected + ' · 利润率与现金回报'"
              :rows="companyRows"
              :lines="marginLines"
              unit="%" /></Safe
          ><Safe widget-title="费用投入"
            ><AiChart
              :title="selected + ' · 研发、股份薪酬与折旧'"
              :rows="companyRows"
              :lines="expenseLines" /></Safe
        ></div>
        <Safe widget-title="现金转换"
          ><AiChart
            :title="selected + ' · 利润与经营现金流'"
            :rows="companyRows"
            :lines="[
              { key: 'netIncome', name: '净利润', color: '#2563eb' },
              { key: 'cfo', name: '经营现金流', color: '#059669' },
              { key: 'fcf', name: '自由现金流', color: '#172b3a' },
            ]"
        /></Safe>
      </template>
      <template v-if="tab === 'credit'">
        <article class="card"
          ><h3>CDS · 信用违约掉期</h3
          ><p class="definition"
            >约5年、美元高级公司CDS；只绘制明确报告的成交运行利差（日中位数），散点表示有成交的日期。不是连续收盘报价，未把固定票息或模型估值当作成交价格。</p
          ><div class="two-column"
            ><article v-for="c in data.cds" :key="c.ticker"
              ><div class="cds-head"
                ><strong>{{ c.ticker }} · {{ format(c.latest.value, 'bp') }}</strong
                ><span>{{ c.latest.date }} · {{ c.latest.trades }}笔成交</span
                ><a :href="c.sourceUrl" target="_blank" rel="noopener noreferrer">成交整理 ↗</a
                ><a :href="c.upstreamUrl" target="_blank" rel="noopener noreferrer">DTCC ↗</a
                ><span v-if="c.health.status !== 'ready'" class="warning"
                  >保留上次成功结果</span
                ></div
              ><Safe :widget-title="c.ticker + ' CDS'"
                ><AiChart
                  :title="c.ticker + ' · 已报告CDS成交利差'"
                  :rows="c.history.map((p) => ({ date: p.date, value: p.value }))"
                  :lines="[
                    {
                      key: 'value',
                      name: c.ticker + ' CDS',
                      color: c.ticker === 'ORCL' ? '#d97706' : '#2563eb',
                      scatter: true,
                    },
                  ]"
                  unit="bp" /></Safe></article></div
          ><p v-if="!data.cds.length" class="muted">暂无通过核验的公开成交利差</p></article
        >
        <div class="two-column"
          ><Safe widget-title="现金与债务"
            ><AiChart
              :title="selected + ' · 现金与已披露长期债务'"
              :rows="balanceRows"
              :lines="debtLines"
              note="现金不含短期投资；债务分流动与非流动列示，缺值不视为零；融资租赁不与债务重复相加。" /></Safe
          ><Safe widget-title="利息覆盖"
            ><AiChart
              :title="selected + ' · 利息覆盖与Capex现金压力'"
              :rows="companyRows"
              :lines="[
                { key: 'interestCoverage', name: '经营利润 / 利息费用', color: '#2563eb' },
                { key: 'capexCfo', name: 'Capex / CFO', color: '#dc2626', right: true, unit: '%' },
              ]"
              unit="倍" /></Safe
        ></div>
        <article class="card"
          ><h3>{{ selected }} · 资产负债表与融资</h3
          ><div class="company-stats"
            ><article
              v-for="key in [
                'cash',
                'shortInvestments',
                'debtCurrent',
                'debtNoncurrent',
                'leaseLiability',
                'rpo',
                'receivables',
                'inventory',
              ]"
              :key="key"
              ><small>{{ label[key] }}</small
              ><strong>{{ compact(current?.latest?.balance?.[key]) }}</strong
              ><span>十亿美元 · {{ current?.periodEnd }}</span></article
            ></div
          ></article
        >
      </template>
      <template v-if="tab === 'details'">
        <article class="card"
          ><header
            ><div
              ><h3>{{ selected }} · {{ current?.name }}</h3
              ><p class="muted">{{ current?.sector }} · 最新财季 {{ current?.periodEnd }}</p></div
            ><a
              v-if="current?.filingsUrl"
              :href="current.filingsUrl"
              target="_blank"
              rel="noopener noreferrer"
              >SEC公司申报 ↗</a
            ></header
          ><p v-if="detailLoading" class="muted">读取季度历史…</p
          ><p v-if="detailError" class="error"
            >{{ detailError }} <button @click="loadDetail">重试</button></p
          ><div class="period-switch"
            ><button
              :class="{ active: historyPeriod === 'quarters' }"
              @click="historyPeriod = 'quarters'"
              >季度历史</button
            ><button
              :class="{ active: historyPeriod === 'annual' }"
              @click="historyPeriod = 'annual'"
              >财年历史</button
            ></div
          ><div class="table-scroll history-table"
            ><table
              ><thead
                ><tr
                  ><th>真实起止日期</th
                  ><th v-for="key in historyKeys" :key="key">{{ label[key] }}</th></tr
                ></thead
              ><tbody
                ><tr v-for="r in historyRows" :key="r.start + r.end"
                  ><td>{{ r.start }}<br />{{ r.end }}</td
                  ><td
                    v-for="key in historyKeys"
                    :key="key"
                    :class="tone(key === 'fcf' ? r.values[key] : null)"
                    >{{
                      percentage(key) ? format(r.values[key], 'percent') : compact(r.values[key])
                    }}</td
                  ></tr
                ></tbody
              ></table
            ></div
          ><p class="definition"
            >金额：十亿美元。{{ data.metricDefinitions?.period }}
            {{ data.metricDefinitions?.vintage }}</p
          ></article
        >
        <article class="card"
          ><h3>关键财务值 · 第二来源复核</h3
          ><div class="table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>项目</th><th>共同财年期末</th><th>SEC原值（USD）</th><th>第二来源（USD）</th
                  ><th>差异</th><th>结果</th></tr
                ></thead
              ><tbody
                ><tr v-for="c in current?.crossChecks || []" :key="c.metric"
                  ><td>{{ label[c.metric] }}</td
                  ><td>{{ c.date }}</td
                  ><td>{{ format(c.primary) }}</td
                  ><td>{{ format(c.secondary) }}</td
                  ><td>{{ format(c.differencePct, 'percent') }}</td
                  ><td
                    ><a
                      :href="c.sourceUrl"
                      target="_blank"
                      rel="noopener noreferrer"
                      :class="c.status === 'consistent' ? 'positive' : 'warning'"
                      >{{ c.status === 'consistent' ? '一致（≤1%）' : '存在差异' }} ↗</a
                    ></td
                  ></tr
                ></tbody
              ></table
            ></div
          ><p class="definition"
            >复核仅涵盖表中共同年度。ARR等经营指标来自公开经营表，未逐项完成独立原文交叉核验。</p
          ></article
        >
        <article class="card"
          ><h3>最新季度 · 取数口径</h3
          ><details
            ><summary>展开SEC标签、申报日期与季度推导</summary
            ><div class="table-scroll"
              ><table
                ><thead
                  ><tr
                    ><th>指标</th><th>SEC标签</th><th>申报日期</th><th>季度计算</th><th>累计基期</th
                    ><th>申报编号</th></tr
                  ></thead
                ><tbody
                  ><tr v-for="(p, key) in current?.latest?.provenance || {}" :key="key"
                    ><td>{{ label[key] || key }}</td
                    ><td>{{ p.tag }}</td
                    ><td>{{ p.filed }}</td
                    ><td>{{ p.basis === 'reported' ? '直接报告' : '相邻累计差分' }}</td
                    ><td>{{ p.baseEnd || '—' }}</td
                    ><td>{{ p.accn }}</td></tr
                  ></tbody
                ></table
              ></div
            ></details
          ><p class="definition"
            >{{ data.metricDefinitions?.capex }} {{ data.metricDefinitions?.fcf }}</p
          ></article
        >
      </template>
      <footer class="source-footer"
        ><span>SEC / 公司披露 / Stock Analysis / DTCC公开成交整理</span
        ><span v-if="sourceIssues.length" class="warning"
          >{{ sourceIssues.length }}项补充来源待更新</span
        ><span v-if="staleCompanies.length" class="warning"
          >{{ staleCompanies.join('、') }}：财报历史或来源待补齐</span
        ><details
          ><summary>指标定义与数据覆盖</summary
          ><p v-for="(definition, key) in data.metricDefinitions" :key="key">{{ definition }}</p
          ><p
            >SEC财报与经营指标每日检查；CDS每4小时检查。数据为最近已披露期间，不代表实时行情；来源失败时保留最后成功数据及原日期。</p
          ></details
        ></footer
      >
    </template>
  </section>
</template>
<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue';
  import { researchRequest } from '@/api/hedgeResearch';
  import Safe from '../components/WidgetErrorBoundary';
  import AiChart, { type AiLine } from './AiChart.vue';
  import {
    type AiDashboard,
    type Company,
    type AccountingRow,
    compact,
    format,
    label,
    numeric,
    percentage,
  } from './model';

  const data = ref<AiDashboard | null>(null),
    loading = ref(false),
    error = ref('');
  const selected = ref('MSFT'),
    sector = ref(''),
    search = ref(''),
    period = ref('quarter'),
    tab = ref('overview');
  const detail = ref<Company | null>(null),
    detailLoading = ref(false),
    detailError = ref('');
  const historyPeriod = ref<'quarters' | 'annual'>('quarters'),
    kpiKind = ref(''),
    kpiId = ref('');
  const sortKey = ref('revenue'),
    descending = ref(true);
  const tabs = [
    { key: 'overview', name: '产业总览' },
    { key: 'capex', name: '资本开支' },
    { key: 'demand', name: 'ARR与订单' },
    { key: 'returns', name: '盈利与现金回报' },
    { key: 'credit', name: 'CDS与融资' },
    { key: 'details', name: '公司财务明细' },
  ];
  async function load() {
    loading.value = true;
    error.value = '';
    try {
      data.value = await researchRequest<AiDashboard>({
        url: '/research/equity/ai',
        method: 'GET',
      });
      await loadDetail();
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'AI研究数据读取失败';
    } finally {
      loading.value = false;
    }
  }
  let detailSequence = 0;
  async function loadDetail() {
    const sequence = ++detailSequence;
    detailLoading.value = true;
    detailError.value = '';
    detail.value = null;
    try {
      const result = await researchRequest<Company>({
        url: '/research/equity/ai/' + selected.value,
        method: 'GET',
      });
      if (sequence === detailSequence) detail.value = result;
    } catch (e) {
      if (sequence === detailSequence)
        detailError.value = e instanceof Error ? e.message : '公司历史读取失败';
    } finally {
      if (sequence === detailSequence) detailLoading.value = false;
    }
  }
  onMounted(load);
  watch(selected, loadDetail);
  const current = computed(() =>
    detail.value?.ticker === selected.value
      ? detail.value
      : data.value?.companies.find((c) => c.ticker === selected.value),
  );
  const values = (c: Company | undefined) =>
    (period.value === 'ttm' ? c?.latest?.ttm : c?.latest)?.values || {};
  const sectors = computed(() => [...new Set(data.value?.companies.map((c) => c.sector) || [])]);
  const lastCapex = computed(() => data.value?.capexHistory.filter((r) => r.capex != null).at(-1));
  const arrCoverage = computed(
    () =>
      data.value?.companies.filter(
        (c) =>
          c.operatingKpis?.some((k) => k.kind === 'ARR') ||
          c.disclosures?.some((d) => d.kind === 'ARR'),
      ).length || 0,
  );
  const sourceIssues = computed(
    () =>
      data.value?.companies.flatMap((c) =>
        Object.entries(c.sources || {})
          .filter(([, s]) => s.status !== 'ready')
          .map(([key, s]) => ({ ...s, key, ticker: c.ticker })),
      ) || [],
  );
  const staleCompanies = computed(
    () => data.value?.companies.filter((c) => c.status !== 'ready').map((c) => c.ticker) || [],
  );
  const filteredCompanies = computed(
    () =>
      data.value?.companies.filter(
        (c) =>
          (!sector.value || c.sector === sector.value) &&
          (!search.value ||
            (c.ticker + ' ' + c.name).toLowerCase().includes(search.value.toLowerCase())),
      ) || [],
  );
  const visibleCompanies = computed(() =>
    [...filteredCompanies.value].sort((a, b) => {
      const val = (c: Company) =>
        numeric(
          sortKey.value === 'revenueYoy'
            ? period.value === 'quarter'
              ? c.latest?.yoy?.revenue
              : null
            : values(c)[sortKey.value],
        );
      const x = val(a),
        y = val(b);
      return x == null
        ? y == null
          ? 0
          : 1
        : y == null
        ? -1
        : (descending.value ? -1 : 1) * (x - y);
    }),
  );
  const sortBy = (key: string) => {
    if (sortKey.value === key) descending.value = !descending.value;
    else {
      sortKey.value = key;
      descending.value = true;
    }
  };
  const tone = (v: unknown) =>
    numeric(v) == null ? '' : Number(v) < 0 ? 'negative' : Number(v) > 0 ? 'positive' : '';
  const checkStatus = (c: Company) =>
    c.crossChecks?.some((x) => x.status === 'difference')
      ? '有差异'
      : c.crossChecks?.length
      ? `${c.crossChecks.length}项已核对`
      : '待核对';
  const cloudRows = computed(
    () =>
      data.value?.capexHistory.map(
        (r) =>
          Object.fromEntries(
            Object.entries(r).map(([k, v]) => [
              k,
              k === 'date' ? v : numeric(v) == null ? null : Number(v) / 1e9,
            ]),
          ) as { date: string; [key: string]: unknown },
      ) || [],
  );
  const toChartRow = (r: AccountingRow) => {
    const v = period.value === 'ttm' ? r.ttm?.values : r.values;
    return {
      date: r.end,
      ...Object.fromEntries(
        Object.entries(v || {}).map(([k, x]) => [
          k,
          numeric(x) == null
            ? null
            : percentage(k) || k === 'interestCoverage'
            ? Number(x)
            : Number(x) / 1e9,
        ]),
      ),
    };
  };
  const companyRows = computed(() => detail.value?.quarters?.map(toChartRow) || []);
  const balanceRows = computed(
    () =>
      detail.value?.quarters?.map((r) => ({
        date: r.end,
        ...Object.fromEntries(
          Object.entries(r.balance || {}).map(([k, v]) => [
            k,
            numeric(v) == null ? null : Number(v) / 1e9,
          ]),
        ),
      })) || [],
  );
  const cloudLines: AiLine[] = [
    { key: 'MSFT', name: 'Microsoft', color: '#2563eb' },
    { key: 'AMZN', name: 'Amazon', color: '#f59e0b' },
    { key: 'GOOGL', name: 'Alphabet', color: '#059669' },
    { key: 'META', name: 'Meta', color: '#8b5cf6' },
  ];
  const cashLines: AiLine[] = [
    { key: 'capex', name: '现金Capex', color: '#2563eb', bar: true },
    { key: 'cfo', name: '经营现金流', color: '#059669' },
    { key: 'fcf', name: '自由现金流', color: '#172b3a' },
  ];
  const intensityLines: AiLine[] = [
    { key: 'capexRevenue', name: 'Capex / 收入', color: '#2563eb' },
    { key: 'capexCfo', name: 'Capex / 经营现金流', color: '#d97706' },
    { key: 'daRevenue', name: '折旧摊销 / 收入', color: '#8b5cf6' },
  ];
  const marginLines: AiLine[] = [
    { key: 'grossMargin', name: '毛利率', color: '#2563eb' },
    { key: 'operatingMargin', name: '经营利润率', color: '#059669' },
    { key: 'fcfMargin', name: '自由现金流率', color: '#172b3a' },
  ];
  const expenseLines: AiLine[] = [
    { key: 'rd', name: '研发费用', color: '#2563eb' },
    { key: 'sbc', name: '股份薪酬', color: '#8b5cf6' },
    { key: 'da', name: '折旧摊销', color: '#d97706' },
  ];
  const debtLines: AiLine[] = [
    { key: 'cash', name: '现金及现金等价物', color: '#059669' },
    { key: 'debtCurrent', name: '一年内到期长期债务', color: '#f59e0b' },
    { key: 'debtNoncurrent', name: '非流动长期债务', color: '#2563eb' },
    { key: 'leaseLiability', name: '融资租赁负债', color: '#8b5cf6' },
  ];
  const disclosures = computed(() =>
    filteredCompanies.value.flatMap((c) =>
      (c.disclosures || []).map((d) => ({ ...d, ticker: c.ticker })),
    ),
  );
  const kpiKinds = computed(() => [
    ...new Set(
      data.value?.companies.flatMap((c) => c.operatingKpis?.map((k) => k.kind) || []) || [],
    ),
  ]);
  const allKpis = computed(() =>
    filteredCompanies.value.flatMap((c) =>
      (c.operatingKpis || [])
        .filter((k) => !kpiKind.value || k.kind === kpiKind.value)
        .map((k) => ({ ...k, ticker: c.ticker, id: c.ticker + ':' + k.name })),
    ),
  );
  const activeKpi = computed(
    () =>
      allKpis.value.find((k) => k.id === kpiId.value) ||
      allKpis.value.find((k) => k.kind === 'ARR') ||
      allKpis.value[0],
  );
  const kpiRows = computed(
    () =>
      activeKpi.value?.history.map((r) => ({
        date: r.date,
        value:
          numeric(r.value) == null
            ? null
            : Number(r.value) / (activeKpi.value?.unit === 'USD' ? 1e9 : 1),
      })) || [],
  );
  const historyKeys = [
    'revenue',
    'grossMargin',
    'operatingIncome',
    'operatingMargin',
    'cfo',
    'capex',
    'fcf',
    'rd',
    'sbc',
    'da',
    'interest',
    'leaseAdditions',
  ];
  const historyRows = computed(() => [...(detail.value?.[historyPeriod.value] || [])].reverse());
</script>
<style scoped>
  .ai-board {
    min-width: 0;
    padding: 4px 0 16px;
    color: #15364d;
    font-size: 13px;
  }

  .board-head,
  .card > header {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  .board-head {
    margin: 4px 0 18px;
  }

  .eyebrow {
    margin: 0 0 6px;
    color: #2563eb;
    font-size: 10px;
    letter-spacing: 1.7px;
  }

  h2 {
    margin: 0;
    font-size: 24px;
  }

  h3 {
    margin: 0 0 12px;
    font-size: 15px;
  }

  h4 {
    font-size: 14px;
  }

  .muted,
  .head-right,
  .source-footer {
    color: #71849a;
    font-size: 12px;
  }

  .head-right {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }

  .stats,
  .company-stats {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 16px 0;
  }

  .stats article,
  .company-stats article {
    min-width: 0;
    padding: 16px;
    border: 1px solid #e1e9f1;
    border-radius: 9px;
    background: #f6f9fd;
  }

  small {
    display: block;
    margin-bottom: 7px;
    color: #71849a;
    font-size: 11px;
  }

  .stats strong,
  .company-stats strong {
    display: block;
    font-size: 24px;
    font-weight: 650;
  }

  .stats em {
    font-size: 12px;
    font-style: normal;
    font-weight: 400;
  }

  .stats span,
  .company-stats span {
    display: block;
    margin-top: 6px;
    color: #71849a;
    font-size: 11px;
  }

  .tabs {
    display: flex;
    flex-wrap: wrap;
    margin-bottom: 16px;
    padding: 0 0 12px;
    border-bottom: 1px solid #e2eaf2;
    gap: 7px;
  }

  .tabs button {
    padding: 7px 15px;
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 16px;
    gap: 12px;
  }

  .filters label {
    display: flex;
    align-items: center;
    color: #65809a;
    font-size: 12px;
    gap: 7px;
  }

  button,
  input,
  select {
    max-width: 100%;
    padding: 5px 9px;
    border: 1px solid #d9e4ed;
    border-radius: 6px;
    background: #fff;
    color: inherit;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.6;
    cursor: wait;
  }

  button.active {
    border-color: #bbd0ff;
    background: #edf3ff;
    color: #2563eb;
  }

  input {
    width: 155px;
  }

  .period-switch {
    display: flex;
    gap: 5px;
  }

  .card {
    min-width: 0;
    margin-bottom: 16px;
    padding: 18px;
    border: 1px solid #dce6ef;
    border-radius: 11px;
    background: #fff;
  }

  .two-column {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: stretch;
    margin: 16px 0;
    gap: 16px;
  }

  .two-column > * {
    min-width: 0;
  }

  .table-scroll {
    max-width: 100%;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  th,
  td {
    padding: 10px 11px;
    border-bottom: 1px solid #eaf0f5;
    text-align: right;
  }

  th {
    position: sticky;
    z-index: 1;
    top: 0;
    background: #f5f8fc;
    color: #526e89;
    font-weight: 500;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  td small {
    margin: 5px 0 0;
    font-size: 10px;
  }

  th button,
  .company-link {
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
  }

  .company-link {
    color: #2563eb;
    text-align: left;
  }

  tbody tr:hover,
  tbody tr.selected {
    background: #f2f6ff;
  }

  tbody tr {
    cursor: pointer;
  }

  .positive {
    color: #059669;
  }

  .negative,
  .warning {
    color: #c46b20;
  }

  .error {
    padding: 14px;
    border-radius: 8px;
    background: #fff1f1;
    color: #bf3e3e;
  }

  .loading {
    padding: 45px;
    text-align: center;
  }

  .history-table {
    max-height: 560px;
  }

  .demand-table {
    max-height: 450px;
  }

  .definition {
    margin: 12px 0;
    color: #71849a;
    font-size: 12px;
    line-height: 1.8;
  }

  .cds-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin-bottom: 12px;
    font-size: 12px;
    gap: 10px;
  }

  .cds-head strong {
    font-size: 18px;
  }

  .source-footer {
    display: flex;
    flex-wrap: wrap;
    padding: 10px 0;
    line-height: 1.8;
    gap: 15px;
  }

  .source-footer details {
    width: 100%;
  }

  summary {
    color: #5b7994;
    font-size: 12px;
    cursor: pointer;
  }

  a {
    color: #2563eb;
  }

  .disclosures {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }

  .disclosures article {
    padding: 16px;
    border: 1px solid #e3eaf3;
    border-radius: 8px;
    background: #f7faff;
  }

  .disclosures strong {
    font-size: 20px;
  }

  .disclosures p {
    color: #71849a;
    font-size: 12px;
  }

  details table {
    margin-top: 12px;
  }

  button:focus-visible,
  a:focus-visible,
  input:focus-visible,
  select:focus-visible {
    outline: 2px solid #2563eb;
    outline-offset: 2px;
  }

  @media (max-width: 1200px) {
    .stats,
    .company-stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .two-column {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 600px) {
    .stats,
    .company-stats,
    .disclosures {
      grid-template-columns: 1fr;
    }

    .filters {
      flex-direction: column;
      align-items: stretch;
    }

    .tabs button {
      padding: 6px 9px;
    }

    .card {
      padding: 12px;
    }

    .head-right span {
      display: none;
    }
  }
</style>
