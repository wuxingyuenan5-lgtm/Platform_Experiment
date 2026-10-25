<template>
  <section class="theme-workbench">
    <header class="page-heading"
      ><div
        ><h2>主题与行业</h2
        ><p
          >{{ market === 'cn' ? 'A股' : '美股' }} · {{ data.date || '暂无收盘数据' }}
          <span>收盘</span></p
        ></div
      >
      <div class="view-tabs" role="group" aria-label="观察视角"
        ><button :aria-pressed="mode === 'themes'" @click="mode = 'themes'">投资主线</button
        ><button :aria-pressed="mode === 'styles'" @click="mode = 'styles'">风格轮动</button
        ><button :aria-pressed="mode === 'industries'" @click="mode = 'industries'"
          >行业对照</button
        ></div
      >
    </header>
    <ThemeStrengthOverview
      v-if="mode === 'themes'"
      :themes="data.items.filter((t) => t.kind !== 'satellite')"
      @select="focusTheme"
    />
    <div v-if="mode === 'themes'" class="workspace-grid">
      <aside class="mainline-nav" aria-label="主线选择">
        <div class="nav-heading"
          ><h3>主线强弱</h3
          ><select v-model="order" aria-label="主线排列"
            ><option value="returnPct">当日</option
            ><option value="return5">近5日</option
            ><option value="return20">近20日</option
            ><option value="relative20">20日相对基准</option
            ><option value="catalog">目录顺序</option></select
          ></div
        >
        <div class="list-caption"
          ><span>成员涨跌幅中位数</span><span>{{ periodLabel }}</span></div
        >
        <button
          v-for="row in sorted.filter((t) => t.kind !== 'style' && t.kind !== 'satellite')"
          :key="row.name"
          class="mainline"
          :aria-pressed="active?.name === row.name"
          @click="selectTheme(row.name)"
        >
          <span class="mainline-top"
            ><strong>{{ row.name }}</strong
            ><b :class="tone(currentValue(row))">{{
              fmt(currentValue(row), order === 'relative20' ? 'pp' : '%')
            }}</b></span
          >
          <span class="strength-track"
            ><i
              :class="tone(currentValue(row))"
              :style="{
                width: strengthWidth(row),
                left: (currentValue(row) || 0) >= 0 ? '50%' : undefined,
                right: (currentValue(row) || 0) < 0 ? '50%' : undefined,
              }"
            ></i
          ></span>
          <span class="mainline-bottom"
            ><span>{{ row.expected }}只 · {{ row.segments.length }}个环节</span
            ><span v-if="!rankable(row)">样本不足</span><span v-else>查看 →</span></span
          >
        </button>
        <details class="satellite-nav"
          ><summary>卫星主题</summary
          ><button
            v-for="row in data.items.filter((t) => t.kind === 'satellite')"
            :key="row.name"
            class="style-link"
            :aria-pressed="active?.name === row.name"
            @click="selectTheme(row.name)"
            >{{ row.name }} <span>→</span></button
          ></details
        >
        <p class="nav-note">{{ data.uniqueStocks }}只独立股票 · 主线可交叉归属</p>
      </aside>
      <div v-if="active" ref="detailPane" class="detail-pane">
        <section class="theme-summary">
          <div class="detail-heading"
            ><div
              ><span class="eyebrow">{{ active.kind === 'style' ? '风格观察' : '当前主线' }}</span
              ><h3>{{ active.name }}</h3></div
            ><span class="universe-count">{{
              active.kind === 'style' ? 'ETF独立比较' : `${active.expected}只代表股票`
            }}</span></div
          >
          <div v-if="active.kind !== 'style'" class="metrics">
            <div
              ><span>近20日表现</span
              ><strong :class="tone(active.return20)">{{ fmt(active.return20) }}</strong
              ><small>{{ coverage(active.return20Count, active.expected) }}有效</small></div
            >
            <div
              ><span>20日超额表现</span
              ><strong :class="tone(active.relative20)">{{ fmt(active.relative20, 'pp') }}</strong
              ><small>相对{{ data.benchmark?.name }}</small></div
            >
            <div
              ><span>今日上涨股票</span><strong>{{ fmt(active.advancingPct) }}</strong
              ><small>{{ coverage(active.covered, active.expected) }}有效</small></div
            >
            <div
              ><span>站上20日均线</span><strong>{{ fmt(active.above20Pct) }}</strong
              ><small>{{ coverage(active.above20Count, active.expected) }}有效</small></div
            >
          </div>
        </section>
        <section v-if="active.kind !== 'style'" class="members-panel">
          <header class="section-heading"
            ><h4>产业链环节</h4><small>点击环节筛选股票 · 右侧为20日表现</small></header
          >
          <div class="segments" role="group" aria-label="产业链环节"
            ><button :aria-pressed="!segment" @click="segment = ''"
              >全部环节 <span>{{ active.expected }}</span></button
            ><button
              v-for="row in active.segmentMetrics"
              :key="row.name"
              :aria-pressed="segment === row.name"
              @click="segment = segment === row.name ? '' : row.name"
              ><span>{{ row.name }}</span
              ><b :class="tone(row.return20)">{{ fmt(row.return20) }}</b></button
            ></div
          >
          <div class="member-toolbar"
            ><h4
              >{{ segment || '成员股票' }} <small>{{ members.length }}只</small></h4
            ><div
              ><select v-if="market === 'cn'" v-model="industry" aria-label="主题内行业筛选"
                ><option value="">全部行业</option
                ><option v-for="name in industryOptions" :key="name" :value="name">{{
                  name
                }}</option></select
              ><input
                v-model="search"
                aria-label="搜索主题股票"
                placeholder="搜索名称 / 代码" /></div
          ></div>
          <div
            class="table-scroll member-table"
            tabindex="0"
            role="region"
            aria-label="主线成员股票"
            ><table
              ><thead
                ><tr
                  ><th>股票</th><th>产业链环节</th><th>当日</th><th>5日</th><th>20日</th></tr
                ></thead
              ><tbody
                ><tr
                  v-for="row in members"
                  :key="row.code"
                  :class="{ selected: selectedStock === row.code }"
                  ><th
                    ><button
                      class="stock-button"
                      @click="selectedStock = selectedStock === row.code ? '' : row.code"
                      >{{ row.name
                      }}<small
                        >{{ row.code }}<span v-if="row.industry"> · {{ row.industry }}</span
                        ><span v-if="row.status !== 'ready'"> · 待更新</span></small
                      ></button
                    ></th
                  ><td class="segment-cell">{{ row.segments.join(' / ') }}</td
                  ><td :class="tone(row.returnPct)">{{ fmt(row.returnPct) }}</td
                  ><td :class="tone(row.return5)">{{ fmt(row.return5) }}</td
                  ><td :class="tone(row.return20)">{{ fmt(row.return20) }}</td></tr
                ><tr v-if="!members.length"
                  ><td colspan="5" class="empty">没有符合条件的股票</td></tr
                ></tbody
              ></table
            ></div
          >
          <div v-if="stock" class="stock-detail"
            ><header class="section-heading"
              ><div
                ><h4>{{ stock.name }} · {{ stock.code }}</h4
                ><p
                  >{{ stock.date }} · {{ stock.source }}
                  <span>20日相对基准 {{ fmt(stock.relative20, 'pp') }}</span></p
                ></div
              ><button @click="selectedStock = ''" aria-label="关闭股票走势">关闭 ×</button></header
            ><VibeTimeChart
              v-if="stock.history?.length"
              :key="`${market}:${stock.code}`"
              :title="`${stock.name} · 收盘价格`"
              y-label="价格"
              :dates="stock.history.map((p) => p.date)"
              :series="[
                {
                  name: stock.name,
                  color: '#2864ec',
                  type: 'line',
                  values: stock.history.map((p) => num(p.value)),
                },
              ]"
            /><p v-else>暂无可用历史价格</p
            ><div class="stock-meta"
              ><span>归属主线：{{ stock.themes?.join(' / ') }}</span
              ><a
                v-if="stock.sourceUrl"
                :href="stock.sourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                >行情来源 ↗</a
              ></div
            ></div
          >
        </section>
        <div v-if="active.overlaps?.length || active.related?.length" class="connections"
          ><span>关联主线</span
          ><button v-for="item in active.overlaps" :key="item.name" @click="selectTheme(item.name)"
            >{{ item.name }} <small>{{ item.count }}只重合</small> ↗</button
          ><button v-for="name in active.related" :key="name" @click="selectTheme(name)"
            >{{ name }} ↗</button
          ></div
        >
        <details class="reference-panel" :open="active.kind === 'style'" :key="active.name"
          ><summary
            >参考 ETF
            <span>{{ active.references?.length || 0 }}个工具 · 独立于个股统计</span></summary
          ><div class="table-scroll" tabindex="0" role="region" aria-label="主线参考ETF"
            ><table
              ><thead
                ><tr><th>ETF / 覆盖范围</th><th>当日</th><th>5日</th><th>20日</th></tr></thead
              ><tbody
                ><tr v-for="row in active.references" :key="row.code"
                  ><th
                    ><a :href="row.url" target="_blank" rel="noopener noreferrer"
                      >{{ row.name }} · {{ row.code }} ↗</a
                    ><small>{{ row.coverage }} · {{ row.scope }} · {{ row.date || '—' }}</small></th
                  ><td :class="tone(row.return1)">{{ fmt(row.return1) }}</td
                  ><td :class="tone(row.return5)">{{ fmt(row.return5) }}</td
                  ><td :class="tone(row.return20)">{{ fmt(row.return20) }}</td></tr
                ></tbody
              ></table
            ></div
          ></details
        >
      </div>
    </div>
    <EquityStylePanel
      v-else-if="mode === 'styles'"
      :data="data.styles"
      :benchmark="data.benchmark?.name || ''"
      :market="market"
    />
    <section v-else class="industry-panel">
      <p class="industry-note">{{
        market === 'cn'
          ? '申万一级行业 · 独立于主题归属；行情与估值按有效样本统计。'
          : 'GICS 11行业ETF · 价格表现单独比较，不与个股样本混合。'
      }}</p>
      <div class="table-scroll" tabindex="0" role="region" aria-label="行业独立对照"
        ><table v-if="market === 'cn'"
          ><thead
            ><tr
              ><th>行业</th><th>样本数</th><th>当日涨跌中位数</th><th>上涨占比</th
              ><th>成交额占比</th><th>PE中位数</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in industries" :key="row.code"
              ><th>{{ row.name }}</th
              ><td>{{ row.count }}</td
              ><td :class="tone(row.medianReturn)">{{ fmt(row.medianReturn) }}</td
              ><td>{{ fmt(row.advancingPct) }}</td
              ><td>{{ fmt(row.amountSharePct) }}</td
              ><td>{{ fmt(row.medianPe, '') }}</td></tr
            ></tbody
          ></table
        ><table v-else
          ><thead
            ><tr
              ><th>行业</th><th>ETF</th><th>当日</th><th>5日</th><th>20日</th><th>观测日</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in data.sectors" :key="row.code"
              ><th>{{ row.name }}</th
              ><td>{{ row.code }}</td
              ><td :class="tone(row.return1)">{{ fmt(row.return1) }}</td
              ><td :class="tone(row.return5)">{{ fmt(row.return5) }}</td
              ><td :class="tone(row.return20)">{{ fmt(row.return20) }}</td
              ><td>{{ row.date || '—' }}</td></tr
            ></tbody
          ></table
        ></div
      >
    </section>
    <details class="method"
      ><summary>统计口径与覆盖</summary
      ><p
        >5日、20日为基准交易日窗口内的成员涨跌幅中位数；相对表现为20日涨跌幅减去基准同期涨跌幅。至少3只且覆盖80%成员时参与对应排序。上涨占比只使用当日有效股票，均线占比只使用完整20日历史。样本中位数不是组合收益。</p
      ><p
        >{{
          market === 'cn'
            ? 'A股使用腾讯前复权日线与收盘快照，比较基准为沪深300价格指数。'
            : '美股使用已结束交易日的Yahoo收盘价格，基准为SPY价格表现；不含分红再投资。行业对照为行业ETF，不代表成分股广度。'
        }}
        缺失交易日不补零；来源返回的持平收盘价按原值保留。各主题可重叠，跨主题不合计成交额。</p
      ><p
        >当前目录生效日
        {{ data.effectiveFrom || '—' }}。此前多周期表现为当前成员回溯，不是历史可交易回测。</p
      ></details
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, watch } from 'vue';
  import type {
    EquityThemes,
    EquityTheme,
    EquityDistribution,
    EquityValue,
    ThemeMember,
  } from '@/api/equityObservatory';
  import { useResearchViewState } from '../composables/researchWorkspace';
  import VibeTimeChart from '../aShare/components/VibeTimeChart.vue';
  import ThemeStrengthOverview from './ThemeStrengthOverview.vue';
  import EquityStylePanel from './EquityStylePanel.vue';

  const props = defineProps<{
    market: 'cn' | 'us';
    data: EquityThemes;
    industries: Array<
      EquityDistribution & { code: string; name: string; amountSharePct: EquityValue }
    >;
  }>();
  const mode = useResearchViewState('theme-view', 'themes');
  const selected = useResearchViewState('theme-selected', '');
  const segment = useResearchViewState('theme-segment', '');
  const industry = useResearchViewState('theme-industry', '');
  const search = useResearchViewState('theme-search', '');
  const order = useResearchViewState('theme-order', 'return20');
  const selectedStock = useResearchViewState('theme-stock', '');
  const detailPane = ref<HTMLElement | null>(null);
  const num = (value: EquityValue | undefined): number | null =>
    value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
  const formatter = new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const fmt = (value: EquityValue | undefined, suffix = '%') =>
    num(value) == null ? '—' : `${formatter.format(num(value)!)}${suffix}`;
  const tone = (value: EquityValue | undefined) =>
    num(value) == null || num(value) === 0 ? '' : num(value)! > 0 ? 'positive' : 'negative';
  const coverage = (count: number | undefined, expected: number) => `${count ?? 0}/${expected}只`;
  function rankable(row: EquityTheme) {
    const field = order.value === 'catalog' ? 'returnPct' : order.value;
    return Boolean(row[`${field}Rankable` as keyof EquityTheme]);
  }
  const sorted = computed(() => {
    if (order.value === 'catalog') return props.data.items;
    const field = order.value === 'returnPct' ? 'medianReturn' : order.value;
    return [...props.data.items].sort((a, b) => {
      const av = rankable(a) ? num(a[field as keyof EquityTheme] as EquityValue) : null;
      const bv = rankable(b) ? num(b[field as keyof EquityTheme] as EquityValue) : null;
      if (av == null || bv == null) return av == null ? (bv == null ? 0 : 1) : -1;
      return bv - av;
    });
  });
  const active = computed(
    () => props.data.items.find((row) => row.name === selected.value) || props.data.items[0],
  );
  function selectTheme(name: string) {
    selected.value = name;
    segment.value = '';
    industry.value = '';
    search.value = '';
    selectedStock.value = '';
  }
  async function focusTheme(name: string) {
    selectTheme(name);
    await nextTick();
    detailPane.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  const industryOptions = computed(() =>
    [...new Set((active.value?.members || []).map((row) => row.industry || '待补齐'))].sort(),
  );
  const members = computed(() => {
    const map = new Map<string, ThemeMember & { segments: string[] }>();
    for (const row of active.value?.members || []) {
      if (segment.value && row.segment !== segment.value) continue;
      if (industry.value && (row.industry || '待补齐') !== industry.value) continue;
      if (!`${row.name} ${row.code}`.toLowerCase().includes(search.value.trim().toLowerCase()))
        continue;
      const existing = map.get(row.code);
      if (existing) existing.segments.push(row.segment);
      else map.set(row.code, { ...row, segments: [row.segment] });
    }
    return [...map.values()];
  });
  const stock = computed(() => members.value.find((row) => row.code === selectedStock.value));
  watch(
    () => active.value?.name,
    () => {
      if (segment.value && !active.value?.segments.includes(segment.value)) segment.value = '';
    },
  );

  const periodLabel = computed(
    () =>
      ({ returnPct: '当日', return5: '5日', return20: '20日', relative20: '相对基准' }[
        order.value
      ] || '20日'),
  );
  const currentValue = (row: EquityTheme) =>
    num(
      row[
        (order.value === 'catalog' ? 'return20' : order.value) as keyof EquityTheme
      ] as EquityValue,
    );
  const maxMagnitude = computed(() =>
    Math.max(1, ...props.data.items.map((row) => Math.abs(currentValue(row) || 0))),
  );
  const strengthWidth = (row: EquityTheme) =>
    `${(Math.abs(currentValue(row) || 0) / maxMagnitude.value) * 48}%`;
</script>
<style scoped>
  .theme-workbench {
    min-width: 0;
    padding: 24px;
    border: 1px solid rgb(201 213 226 / 72%);
    border-radius: 18px;
    background: linear-gradient(180deg, rgb(255 255 255 / 98%), rgb(243 248 252 / 96%)), #fff;
    box-shadow: 0 18px 40px rgb(15 23 42 / 6%);
    color: #26364b;
    font-family: inherit;
  }

  .page-heading,
  .detail-heading,
  .section-heading,
  .member-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .page-heading {
    margin-bottom: 24px;
  }

  h2,
  h3,
  h4,
  p {
    margin: 0;
  }

  h2 {
    font-size: 24px;
    font-weight: 650;
    letter-spacing: -0.6px;
  }

  .page-heading p {
    margin-top: 8px;
    color: #66758a;
    font-size: 12px;
  }

  .page-heading p span {
    margin-left: 8px;
    color: #8a96a6;
  }

  h4 {
    font-size: 14px;
    font-weight: 600;
  }

  small {
    color: #77869a;
    font-size: 11px;
    font-weight: 400;
  }

  button,
  select,
  input {
    padding: 7px 10px;
    border: 1px solid #dce3ed;
    border-radius: 6px;
    background: #fff;
    color: inherit;
    font: inherit;
    font-size: 12px;
  }

  button {
    cursor: pointer;
  }

  button:focus-visible,
  select:focus-visible,
  input:focus-visible,
  .table-scroll:focus-visible,
  summary:focus-visible {
    outline: 2px solid #2c65c8;
    outline-offset: 3px;
  }

  button:hover {
    background: #f3f7fd;
  }

  .view-tabs {
    display: flex;
    padding: 4px;
    border-radius: 8px;
    background: #f3f8fc;
    gap: 3px;
  }

  .view-tabs button {
    padding: 8px 18px;
    border: 0;
    background: transparent;
    color: #68768a;
  }

  .view-tabs button[aria-pressed='true'] {
    background: #fff;
    box-shadow: 0 1px 4px #21385512;
    color: #255baf;
  }

  .workspace-grid {
    display: grid;
    grid-template-columns: 270px minmax(0, 1fr);
    gap: 22px;
    align-items: start;
  }

  .mainline-nav {
    overflow: hidden;
    border: 1px solid #dfe6ef;
    border-radius: 10px;
    background: #fff;
  }

  .nav-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 16px 12px;
  }

  .nav-heading h3 {
    font-size: 15px;
  }

  .nav-heading select {
    max-width: 125px;
    background: #f8fafd;
    font-size: 11px;
  }

  .list-caption {
    display: flex;
    justify-content: space-between;
    padding: 0 16px 10px;
    color: #8a96a6;
    font-size: 10px;
  }

  .mainline {
    display: block;
    position: relative;
    width: 100%;
    padding: 13px 16px;
    border: 0;
    border-top: 1px solid #edf0f5;
    border-radius: 0;
    background: #fff;
    text-align: left;
  }

  .mainline[aria-pressed='true'] {
    background: #edf4ff;
    box-shadow: inset 3px 0 #356fd1;
  }

  .mainline-top,
  .mainline-bottom {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 7px;
  }

  .mainline-top strong {
    font-size: 12px;
    font-weight: 550;
  }

  .mainline-top b {
    font-size: 14px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .mainline-bottom {
    margin-top: 6px;
    color: #8a97a8;
    font-size: 10px;
  }

  .strength-track {
    display: block;
    position: relative;
    height: 4px;
    margin-top: 9px;
    border-radius: 3px;
    background: #f0f3f8;
  }

  .strength-track::after {
    content: '';
    position: absolute;
    top: -2px;
    left: 50%;
    height: 8px;
    border-left: 1px solid #b8c4d6;
  }

  .strength-track i {
    position: absolute;
    height: 4px;
    border-radius: 3px;
    background: #8292a8;
  }

  .strength-track i.positive {
    background: #d77b80;
  }

  .strength-track i.negative {
    background: #5d9f95;
  }

  .style-heading {
    padding: 17px 16px 7px;
    background: #f8fafc;
    color: #8390a2;
    font-size: 10px;
  }

  .style-link {
    display: flex;
    justify-content: space-between;
    width: 100%;
    padding: 12px 16px;
    border: 0;
    border-radius: 0;
    background: #f8fafc;
    text-align: left;
  }

  .style-link[aria-pressed='true'] {
    background: #edf4ff;
    color: #255baf;
  }

  .nav-note {
    padding: 12px 16px;
    border-top: 1px solid #edf0f5;
    color: #8b98aa;
    font-size: 10px;
  }

  .detail-pane {
    display: grid;
    min-width: 0;
    gap: 16px;
  }

  .theme-summary,
  .members-panel,
  .reference-panel,
  .industry-panel {
    overflow: hidden;
    border: 1px solid #dfe6ef;
    border-radius: 10px;
    background: #fff;
  }

  .theme-summary {
    padding: 24px;
  }

  .eyebrow {
    display: block;
    margin-bottom: 8px;
    color: #7d8ba0;
    font-size: 11px;
  }

  .detail-heading h3 {
    font-size: 24px;
    font-weight: 600;
    letter-spacing: -0.6px;
  }

  .universe-count {
    padding: 6px 9px;
    border-radius: 5px;
    background: #f1f5fa;
    color: #657a98;
    font-size: 11px;
    white-space: nowrap;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 24px;
    gap: 12px;
  }

  .metrics > div {
    min-width: 0;
    padding-left: 16px;
    border-left: 1px solid #e7edf4;
  }

  .metrics > div:first-child {
    padding: 0;
    border: 0;
  }

  .metrics span {
    display: block;
    color: #748297;
    font-size: 11px;
  }

  .metrics strong {
    display: block;
    margin: 9px 0 6px;
    font-size: 24px;
    font-weight: 550;
    letter-spacing: -0.8px;
    font-variant-numeric: tabular-nums;
  }

  .metrics small {
    display: block;
    font-size: 10px;
    line-height: 1.6;
  }

  .section-heading {
    padding: 18px 20px 12px;
  }

  .segments {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    padding: 0 20px 20px;
  }

  .segments button {
    display: flex;
    align-items: center;
    padding: 8px 10px;
    border-color: #e7ecf3;
    background: #f8fafd;
    font-size: 11px;
    gap: 14px;
  }

  .segments button[aria-pressed='true'] {
    border-color: #b1c9ef;
    background: #eaf2ff;
    color: #255baf;
  }

  .segments b {
    font-weight: 500;
    font-variant-numeric: tabular-nums;
  }

  .member-toolbar {
    padding: 15px 20px;
    border-top: 1px solid #edf1f6;
  }

  .member-toolbar h4 small {
    margin-left: 8px;
  }

  .member-toolbar > div {
    display: flex;
    gap: 8px;
  }

  .member-toolbar input {
    width: 170px;
    background: #f8fafd;
  }

  .member-toolbar select {
    max-width: 130px;
  }

  .table-scroll {
    overflow: auto;
    background: #fff;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 13px 16px;
    border-bottom: 1px solid #e9eef5;
    text-align: right;
    white-space: nowrap;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  thead th {
    position: sticky;
    z-index: 1;
    top: 0;
    background: #f3f8fc;
    color: #5a6f8a;
    font-size: 11px;
    font-weight: 500;
  }

  tbody tr:nth-child(even) {
    background: #f8fafc;
  }

  tbody tr:hover {
    background: #eff5fc;
  }

  tbody tr.selected {
    background: #eaf2ff;
  }

  tbody th {
    font-weight: 500;
  }

  tbody th small {
    display: block;
    margin-top: 5px;
    font-size: 10px;
  }

  .member-table {
    max-height: 430px;
    border-top: 1px solid #dde6f1;
  }

  .stock-button {
    max-width: 235px;
    padding: 0;
    border: 0;
    background: transparent;
    font-size: 12px;
    line-height: 1.5;
    text-align: left;
    white-space: normal;
  }

  .stock-button small {
    display: block;
    margin-top: 4px;
    font-size: 10px;
  }

  .segment-cell {
    max-width: 180px;
    color: #748297;
    font-size: 11px;
    text-align: left;
    white-space: normal;
  }

  .positive {
    color: #bd515e;
  }

  .negative {
    color: #288477;
  }

  .empty {
    padding: 35px;
    color: #8190a5;
    text-align: center;
  }

  .stock-detail {
    padding: 0 20px 15px;
    border-top: 1px solid #d9e4f1;
    background: #f7faff;
  }

  .stock-detail .section-heading {
    padding-right: 0;
    padding-left: 0;
  }

  .stock-detail p {
    margin-top: 6px;
    color: #78899f;
    font-size: 10px;
  }

  .stock-meta {
    display: flex;
    justify-content: space-between;
    margin-top: 10px;
    color: #748297;
    font-size: 11px;
    gap: 12px;
  }

  a {
    color: #3565a8;
  }

  .connections {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    padding: 0 2px;
    color: #75869d;
    font-size: 11px;
    gap: 8px;
  }

  .connections button {
    padding: 5px 9px;
    border-color: #dae3ef;
    background: #f8fafd;
    font-size: 11px;
  }

  .connections small {
    margin-left: 4px;
  }

  .reference-panel summary {
    padding: 17px 20px;
    font-size: 13px;
    font-weight: 550;
    cursor: pointer;
  }

  .reference-panel summary span {
    margin-left: 12px;
    color: #8090a5;
    font-size: 10px;
    font-weight: 400;
  }

  .reference-panel .table-scroll {
    border-top: 1px solid #dce5ef;
  }

  .industry-panel {
    padding: 20px;
  }

  .industry-note {
    margin: 0 0 18px;
    color: #718299;
    font-size: 12px;
  }

  .method {
    margin-top: 20px;
    color: #8592a4;
    font-size: 11px;
  }

  .method summary {
    cursor: pointer;
  }

  .method p {
    max-width: 1000px;
    margin: 8px 0;
    font-size: 11px;
    line-height: 1.9;
  }

  @media (min-width: 1550px) {
    .workspace-grid {
      grid-template-columns: 300px minmax(0, 1fr);
    }

    .mainline-top strong {
      font-size: 13px;
    }

    .mainline {
      padding: 14px 18px;
    }

    .metrics strong {
      font-size: 28px;
    }
  }

  @media (max-width: 1100px) {
    .workspace-grid {
      grid-template-columns: 225px minmax(0, 1fr);
      gap: 14px;
    }

    .theme-workbench {
      padding: 18px;
    }

    .theme-summary {
      padding: 20px;
    }

    .metrics {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }

    .metrics > div:nth-child(3) {
      padding-left: 0;
      border: 0;
    }

    .member-toolbar {
      flex-wrap: wrap;
    }

    .section-heading {
      flex-wrap: wrap;
    }

    .detail-heading h3 {
      font-size: 21px;
    }
  }

  @media (max-width: 760px) {
    .theme-workbench {
      padding: 12px;
    }

    .page-heading {
      flex-wrap: wrap;
      align-items: flex-start;
      gap: 10px;
    }

    .workspace-grid {
      grid-template-columns: 1fr;
    }

    .mainline-nav {
      display: flex;
      flex-wrap: nowrap;
      align-items: stretch;
      overflow: auto;
    }

    .nav-heading,
    .list-caption,
    .style-heading,
    .nav-note {
      display: none;
    }

    .mainline {
      flex: 0 0 180px;
      border-right: 1px solid #e3eaf3;
    }

    .style-link {
      flex: 0 0 180px;
      align-items: center;
    }

    .theme-summary {
      padding: 18px;
    }

    .section-heading,
    .member-toolbar {
      padding: 14px;
    }

    .segments {
      padding: 0 14px 15px;
    }

    .member-toolbar > div {
      width: 100%;
    }

    .member-toolbar input {
      flex: 1;
      min-width: 0;
    }

    .metrics strong {
      font-size: 23px;
    }

    .view-tabs button {
      padding: 7px 13px;
    }

    .reference-panel summary span {
      display: block;
      margin: 7px 0 0 15px;
    }
  }
</style>
