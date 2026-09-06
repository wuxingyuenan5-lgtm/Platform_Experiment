<template>
  <section id="a-share-watchlist-pool" ref="poolRoot" class="pool-card">
    <header class="pool-head"
      ><div><h2>自选股与核心股票池</h2></div
      ><button type="button" class="toolbar" :disabled="loading" @click="load">{{
        loading ? '刷新中…' : '刷新数据'
      }}</button></header
    >
    <div v-if="error" class="error">{{ error }}</div>
    <template v-if="data">
      <div class="pool-kpis">
        <div class="pool-kpi"
          ><span>股票池</span><strong>{{ data.summary.tracked_count }}</strong
          ><small>只</small></div
        >
        <div class="pool-kpi"
          ><span>上涨</span><strong class="up">{{ data.summary.breadth.up }}</strong
          ><small>只</small></div
        >
        <div class="pool-kpi"
          ><span>下跌</span><strong class="down">{{ data.summary.breadth.down }}</strong
          ><small>只</small></div
        >
        <div class="pool-kpi"
          ><span>中位涨幅</span
          ><strong :class="tone(data.summary.breadth.median)">{{
            formatPct(data.summary.breadth.median)
          }}</strong></div
        >
        <div class="pool-kpi"
          ><span>平均涨幅</span
          ><strong :class="tone(data.summary.avg_change)">{{
            formatPct(data.summary.avg_change)
          }}</strong></div
        >
        <div class="pool-kpi"
          ><span>成交额</span><strong>{{ formatNumber(data.summary.total_amount_yi) }}</strong
          ><small>亿</small></div
        >
      </div>
      <section class="breadth-panel">
        <h3>股票池涨跌宽度</h3>
        <div class="breadth-track"
          ><i
            v-for="(count, index) in breadthBins"
            :key="index"
            :class="`breadth-${index}`"
            :style="{ width: `${(count / breadthTotal) * 100}%` }"
          ></i
        ></div>
        <div class="breadth-labels"
          ><span>≤ -5%</span><span>-5% ~ -1%</span><span>-1% ~ +1%</span><span>+1% ~ +5%</span
          ><span>≥ +5%</span></div
        >
      </section>
      <div class="pool-grid">
        <section class="sub-panel"
          ><div class="sub-panel-head"
            ><h3>行业 / 指数强弱</h3
            ><select v-model="rankingPeriod"
              ><option value="change">今日</option
              ><option value="change_5d">5日</option
              ><option value="change_20d">20日</option
              ><option value="ytd">YTD</option></select
            ></div
          ><div class="rank-list"
            ><div v-for="row in rankingRows" :key="row.code" class="rank-row"
              ><span>{{ row.name }}</span
              ><i
                ><b
                  :class="tone(row[rankingPeriod])"
                  :style="{
                    width: `${Math.min(
                      100,
                      (Math.abs(Number(row[rankingPeriod] || 0)) / rankingMax) * 100,
                    )}%`,
                  }"
                ></b></i
              ><strong :class="tone(row[rankingPeriod])">{{
                formatPct(row[rankingPeriod])
              }}</strong></div
            ><div v-if="!rankingRows.length" class="empty">暂无数据</div></div
          ></section
        >
        <section class="sub-panel"
          ><h3>今日最强 / 最弱</h3
          ><div class="leader-columns"
            ><div
              ><h4>最强</h4
              ><button
                v-for="row in leaders.today.up"
                :key="row.instrument_id"
                type="button"
                class="leader-row"
                @click="openStockData(row.code)"
                ><span>{{ row.name }}</span
                ><small>{{ row.industry || '—' }}</small
                ><b class="up">{{ formatPct(row.change) }}</b></button
              ></div
            ><div
              ><h4>最弱</h4
              ><button
                v-for="row in leaders.today.down"
                :key="row.instrument_id"
                type="button"
                class="leader-row"
                @click="openStockData(row.code)"
                ><span>{{ row.name }}</span
                ><small>{{ row.industry || '—' }}</small
                ><b class="down">{{ formatPct(row.change) }}</b></button
              ></div
            ></div
          ></section
        >
      </div>
      <section class="leader-grid">
        <section v-for="group in leaderGroups" :key="group.key" class="sub-panel leader-panel">
          <h3>{{ group.label }}</h3>
          <div class="leader-columns">
            <div>
              <h4>最强</h4>
              <button
                v-for="row in group.up"
                :key="row.instrument_id"
                type="button"
                class="leader-row"
                @click="openStockData(row.code)"
              >
                <span>{{ row.name }}</span
                ><small>{{ row.industry || '—' }}</small
                ><b class="up">{{ formatPct(row[group.field]) }}</b>
              </button>
            </div>
            <div>
              <h4>最弱</h4>
              <button
                v-for="row in group.down"
                :key="row.instrument_id"
                type="button"
                class="leader-row"
                @click="openStockData(row.code)"
              >
                <span>{{ row.name }}</span
                ><small>{{ row.industry || '—' }}</small
                ><b class="down">{{ formatPct(row[group.field]) }}</b>
              </button>
            </div>
          </div>
        </section>
      </section>
      <section class="sub-panel matrix-panel">
        <div class="sub-panel-head">
          <h3>强弱矩阵</h3>
        </div>
        <div v-if="matrixPoints.length" class="matrix-wrap">
          <svg
            viewBox="0 0 1000 420"
            preserveAspectRatio="xMidYMid meet"
            aria-label="股票池强弱矩阵"
          >
            <rect
              x="0"
              y="0"
              :width="matrixPoints.length ? 1000 : 0"
              height="420"
              class="matrix-bg"
            />
            <line
              :x1="52 + (matrixDomain.x / (2 * matrixDomain.x)) * 896"
              y1="0"
              :x2="52 + (matrixDomain.x / (2 * matrixDomain.x)) * 896"
              y2="420"
              class="matrix-axis"
            />
            <line
              x1="0"
              :y1="420 - 52 - (matrixDomain.y / (2 * matrixDomain.y)) * 316"
              x2="1000"
              :y2="420 - 52 - (matrixDomain.y / (2 * matrixDomain.y)) * 316"
              class="matrix-axis"
            />
            <text x="65" y="25" class="matrix-quadrant-label">改善</text>
            <text x="935" y="25" text-anchor="end" class="matrix-quadrant-label">领涨</text>
            <text x="65" y="405" class="matrix-quadrant-label">领跌</text>
            <text x="935" y="405" text-anchor="end" class="matrix-quadrant-label">转弱</text>
            <text x="500" y="414" text-anchor="middle" class="matrix-axis-label">20日涨幅 →</text>
            <text
              x="16"
              y="210"
              text-anchor="middle"
              class="matrix-axis-label"
              transform="rotate(-90 16 210)"
            >
              今日涨幅 ↑
            </text>
            <g
              v-for="point in matrixPoints"
              :key="point.row.instrument_id"
              class="matrix-point"
              :class="{ 'is-hover': matrixHoverId === point.row.instrument_id }"
              @mouseenter="matrixHoverId = point.row.instrument_id"
              @mouseleave="matrixHoverId = null"
              @click="openStockData(point.row.code)"
            >
              <circle
                :cx="point.x"
                :cy="point.y"
                r="5"
                :class="
                  point.positive ? 'is-positive' : point.negative ? 'is-negative' : 'is-mixed'
                "
              />
              <text
                v-if="matrixHoverId === point.row.instrument_id"
                :x="point.x + 8"
                :y="point.y - 8"
                class="matrix-label"
              >
                {{ point.row.name }} {{ formatPct(point.row.change) }}
              </text>
              <title>
                {{ point.row.name }} · {{ point.row.code || '—' }} · 今日
                {{ formatPct(point.row.change) }} · 20日 {{ formatPct(point.row.change_20d) }}
              </title>
            </g>
          </svg>
        </div>
        <div v-else class="empty">暂无数据</div>
      </section>
      <section class="sub-panel heat-panel"
        ><div class="sub-panel-head"
          ><h3>股票池热力图</h3
          ><select v-model="heatPeriod"
            ><option value="change">今日</option
            ><option value="change_5d">5日</option
            ><option value="change_20d">20日</option
            ><option value="ytd">YTD</option></select
          ></div
        ><div class="heatmap"
          ><button
            v-for="tile in heatTiles"
            :key="tile.instrument_id"
            type="button"
            class="heat-tile"
            :class="[tile.size, { 'group-start': tile.groupStart }]"
            :style="{ background: heatColor(tile[heatPeriod], heatMaxAbs) }"
            :title="`${tile.name} · ${tile.industry || '—'} · ${formatPct(tile[heatPeriod])}`"
            @click="openStockData(tile.code)"
            ><span>{{ tile.name }}</span
            ><b>{{ formatPct(tile[heatPeriod]) }}</b
            ><small>{{ tile.industry }}</small></button
          ><div v-if="!heatTiles.length" class="empty">暂无数据</div></div
        ><div v-if="heatTiles.length" class="heat-legend"
          ><div class="heat-legend-gradient"></div
          ><div class="heat-legend-scale"
            ><span>-{{ formatPct(heatMaxAbs) }}</span
            ><span>0%</span><span>+{{ formatPct(heatMaxAbs) }}</span></div
          ></div
        ></section
      >
      <div class="detail-head"
        ><h3>股票池明细</h3
        ><div class="pool-toolbar"
          ><input v-model.trim="query" type="search" placeholder="搜索名称 / 行业 / 代码" /><select
            v-model="filter"
            ><option value="">全部股票</option
            ><option value="__focus__">★ 近期关注（{{ focusCodes.length }}）</option
            ><option v-for="basket in baskets" :key="basket.key" :value="`basket:${basket.key}`"
              >{{ basket.name }}（{{ basket.count }}）</option
            ><option
              v-for="industry in industries"
              :key="industry"
              :value="`industry:${industry}`"
              >{{ industry }}</option
            ></select
          ><button
            v-if="filter === '__focus__'"
            type="button"
            class="primary"
            @click="
              focusInput = '';
              focusOpen = true;
            "
            >添加关注</button
          ><template v-else
            ><button type="button" class="toolbar" @click="editOpen = true">＋ 编辑池子</button
            ><button type="button" class="toolbar" :disabled="loading" @click="load">{{
              loading ? '刷新中…' : '刷新'
            }}</button></template
          ></div
        ></div
      >
      <div v-if="operationMessage" class="operation-message">{{ operationMessage }}</div>
      <div v-if="focusOpen" class="focus-form"
        ><input
          v-model="focusInput"
          placeholder="输入 6 位代码，可空格分隔"
          @keyup.enter="addFocus"
        /><button type="button" class="primary" @click="addFocus">保存</button
        ><button type="button" class="toolbar" @click="focusOpen = false">取消</button></div
      >
      <div class="table-shell"
        ><table
          ><thead
            ><tr
              ><th class="left" @click="sortBy('name')">名称 {{ sortIndicator('name') }}</th
              ><th class="left" @click="sortBy('industry')">行业 {{ sortIndicator('industry') }}</th
              ><th @click="sortBy('price')">现价 {{ sortIndicator('price') }}</th
              ><th @click="sortBy('change')">今日 {{ sortIndicator('change') }}</th
              ><th @click="sortBy('change_5d')">5日 {{ sortIndicator('change_5d') }}</th
              ><th @click="sortBy('change_20d')">20日 {{ sortIndicator('change_20d') }}</th
              ><th @click="sortBy('ytd')">YTD {{ sortIndicator('ytd') }}</th
              ><th @click="sortBy('amount_yi')">成交额(亿) {{ sortIndicator('amount_yi') }}</th
              ><th @click="sortBy('turnover')">换手率 {{ sortIndicator('turnover') }}</th
              ><th @click="sortBy('mcap_yi')">市值(亿) {{ sortIndicator('mcap_yi') }}</th
              ><th @click="sortBy('pe_ttm')">PE TTM {{ sortIndicator('pe_ttm') }}</th
              ><th @click="sortBy('pb')">PB {{ sortIndicator('pb') }}</th
              ><th></th></tr></thead
          ><tbody
            ><tr v-for="row in visibleRows" :key="row.instrument_id"
              ><td class="left"
                ><button type="button" class="stock-link" @click="openStockData(row.code)">{{
                  row.name
                }}</button
                ><small>{{ row.code }}{{ row.exchange ? `.${row.exchange}` : '' }}</small></td
              ><td class="left">{{ row.industry || '—' }}</td
              ><td>{{ formatNumber(row.price) }}</td
              ><td :class="tone(row.change)">{{ formatPct(row.change) }}</td
              ><td :class="tone(row.change_5d)">{{ formatPct(row.change_5d) }}</td
              ><td :class="tone(row.change_20d)">{{ formatPct(row.change_20d) }}</td
              ><td :class="tone(row.ytd)">{{ formatPct(row.ytd) }}</td
              ><td>{{ formatNumber(row.amount_yi) }}</td
              ><td>{{ formatPct(row.turnover) }}</td
              ><td>{{ formatNumber(row.mcap_yi) }}</td
              ><td>{{ formatNumber(row.pe_ttm) }}</td
              ><td>{{ formatNumber(row.pb) }}</td
              ><td
                ><button
                  v-if="filter === '__focus__'"
                  type="button"
                  class="remove"
                  @click="removeFocus(row.code || '')"
                  >取消关注</button
                ><button
                  v-else
                  type="button"
                  class="remove"
                  title="从核心股票池移除"
                  @click="removePool(row)"
                  >×</button
                ></td
              ></tr
            ><tr v-if="!visibleRows.length"
              ><td colspan="13" class="empty">{{
                filter === '__focus__' ? '暂无关注股票' : '暂无匹配股票'
              }}</td></tr
            ></tbody
          ></table
        ></div
      >
      <div v-if="editOpen" class="modal-mask" @click.self="editOpen = false"
        ><div class="modal"
          ><h3>编辑池子</h3><label class="modal-label">粘贴证券代码</label
          ><input v-model="batchInput" class="modal-input" placeholder="600519, 000858 …" />
          <div class="modal-actions"
            ><button type="button" class="toolbar" :disabled="syncing" @click="syncPool">{{
              syncing ? '同步中…' : '同步 GitHub'
            }}</button
            ><button type="button" class="primary" @click="addBatch">批量添加</button
            ><button type="button" class="toolbar" @click="editOpen = false">关闭</button></div
          ></div
        ></div
      >
    </template>
    <div v-else-if="!loading" class="empty"
      >暂无股票池数据；数据源不可用时不会伪造 0 或静态行情。</div
    >
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, onBeforeUnmount, ref } from 'vue';

  interface Stock {
    instrument_id: string;
    code?: string | null;
    exchange?: string;
    name: string;
    industry?: string;
    research_baskets?: string[];
    price?: number | null;
    change?: number | null;
    change_5d?: number | null;
    change_20d?: number | null;
    ytd?: number | null;
    amount_yi?: number | null;
    mcap_yi?: number | null;
    turnover?: number | null;
    pe_ttm?: number | null;
    pb?: number | null;
  }
  type Period = 'change' | 'change_5d' | 'change_20d' | 'ytd';
  interface PoolPayload {
    meta?: { report_date?: string; generated_at?: string };
    summary: {
      tracked_count: number;
      breadth: { up: number; down: number; flat: number; median?: number | null };
      avg_change?: number | null;
      total_amount_yi?: number | null;
    };
    stocks: Stock[];
    indices?: Array<Stock & { code: string }>;
    heatmap?: Array<Stock & { weight?: number }>;
    leaders?: {
      today?: { up: Stock[]; down: Stock[] };
      '5d'?: { up: Stock[]; down: Stock[] };
      '20d'?: { up: Stock[]; down: Stock[] };
    };
    definitions?: {
      focus_codes?: string[];
      research_baskets?: Array<{ key: string; name: string; codes?: string[]; count: number }>;
    };
  }
  const emit = defineEmits<{ (event: 'query', code: string): void }>();
  const data = ref<PoolPayload | null>(null);
  const loading = ref(true);
  const error = ref('');
  const operationMessage = ref('');
  const query = ref('');
  const filter = ref('');
  const sortKey = ref<keyof Stock | null>(null);
  const sortDirection = ref<'asc' | 'desc' | null>(null);
  const focusCodes = ref<string[]>([]);
  const focusOpen = ref(false);
  const focusInput = ref('');
  const editOpen = ref(false);
  const batchInput = ref('');
  const syncing = ref(false);
  const poolRoot = ref<HTMLElement | null>(null);
  let poolObserver: IntersectionObserver | null = null;
  const matrixHoverId = ref<string | null>(null);
  const rankingPeriod = ref<Period>('change');
  const heatPeriod = ref<Period>('change');
  const baskets = computed(() => data.value?.definitions?.research_baskets || []);
  const breadthBins = computed(() => {
    const bins = [0, 0, 0, 0, 0];
    for (const row of data.value?.stocks || []) {
      const value = Number(row.change);
      if (!Number.isFinite(value)) continue;
      if (value <= -0.05) bins[0] += 1;
      else if (value < -0.01) bins[1] += 1;
      else if (value <= 0.01) bins[2] += 1;
      else if (value < 0.05) bins[3] += 1;
      else bins[4] += 1;
    }
    return bins;
  });
  const breadthTotal = computed(() =>
    Math.max(
      1,
      breadthBins.value.reduce((total, count) => total + count, 0),
    ),
  );
  const industries = computed(() =>
    [
      ...new Set((data.value?.stocks || []).map((x) => x.industry).filter(Boolean) as string[]),
    ].sort((a, b) => a.localeCompare(b, 'zh-CN')),
  );
  const visibleRows = computed(() => {
    if (!data.value) return [];
    const q = query.value.toLowerCase();
    const basketCodes = filter.value.startsWith('basket:')
      ? new Set(baskets.value.find((basket) => basket.key === filter.value.slice(7))?.codes || [])
      : null;
    const industry = filter.value.startsWith('industry:') ? filter.value.slice(9) : '';
    let rows = data.value.stocks.filter(
      (x) =>
        (!q || `${x.name} ${x.code} ${x.industry}`.toLowerCase().includes(q)) &&
        (filter.value !== '__focus__' || focusCodes.value.includes(x.code || '')) &&
        (!industry || x.industry === industry) &&
        (!basketCodes || basketCodes.has(x.code)),
    );
    if (sortKey.value && sortDirection.value) {
      const key = sortKey.value;
      rows = [...rows].sort((a, b) => {
        const av = a[key];
        const bv = b[key];
        if (typeof av === 'number' && typeof bv === 'number')
          return (av - bv) * (sortDirection.value === 'desc' ? -1 : 1);
        return (
          String(av || '').localeCompare(String(bv || ''), 'zh-CN') *
          (sortDirection.value === 'desc' ? -1 : 1)
        );
      });
    }
    return rows;
  });
  const rankingRows = computed(() => {
    const rows = (data.value?.indices || []).filter((x) =>
      Number.isFinite(Number(x[rankingPeriod.value])),
    );
    const sorted = [...rows].sort(
      (a, b) => Number(b[rankingPeriod.value] || 0) - Number(a[rankingPeriod.value] || 0),
    );
    return [...sorted.slice(0, 8), ...sorted.slice(-8)].filter(
      (row, index, all) => all.findIndex((candidate) => candidate.code === row.code) === index,
    );
  });
  const rankingMax = computed(() =>
    Math.max(
      ...rankingRows.value.map((x) => Math.abs(Number(x[rankingPeriod.value] || 0))),
      0.0001,
    ),
  );
  const leaders = computed(
    () =>
      data.value?.leaders || {
        today: { up: [], down: [] },
        '5d': { up: [], down: [] },
        '20d': { up: [], down: [] },
      },
  );
  const leaderGroups = computed(() => [
    {
      key: '5d',
      label: '5日强弱排行',
      field: 'change_5d' as const,
      up: leaders.value['5d']?.up || [],
      down: leaders.value['5d']?.down || [],
    },
    {
      key: '20d',
      label: '20日强弱排行',
      field: 'change_20d' as const,
      up: leaders.value['20d']?.up || [],
      down: leaders.value['20d']?.down || [],
    },
  ]);
  const heatTiles = computed(() => {
    const rows = [...(data.value?.heatmap || [])]
      .sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0))
      .slice(0, 120)
      .sort((a, b) => {
        const industry = (a.industry || '~').localeCompare(b.industry || '~', 'zh-CN');
        if (industry !== 0) return industry;
        return Number(b[heatPeriod.value] || 0) - Number(a[heatPeriod.value] || 0);
      });
    const weights = rows.map((row) => Number(row.weight || 1)).sort((a, b) => a - b);
    const quantile = (p: number) => weights[Math.floor((weights.length - 1) * p)] || 1;
    const q60 = quantile(0.6);
    const q82 = quantile(0.82);
    const q94 = quantile(0.94);
    return rows.map((row, index) => ({
      ...row,
      size:
        Number(row.weight || 0) >= q94
          ? 's4'
          : Number(row.weight || 0) >= q82
          ? 's3'
          : Number(row.weight || 0) >= q60
          ? 's2'
          : 's1',
      groupStart: index === 0 || rows[index - 1]?.industry !== row.industry,
    }));
  });
  const heatMaxAbs = computed(() => {
    const values = heatTiles.value
      .map((row) => Math.abs(Number(row[heatPeriod.value] || 0)))
      .filter((value) => Number.isFinite(value) && value > 0)
      .sort((a, b) => a - b);
    return values.length
      ? Math.max(values[Math.min(Math.floor(values.length * 0.9), values.length - 1)], 0.005)
      : 0.08;
  });
  const matrixRows = computed(() =>
    (data.value?.stocks || []).filter(
      (row) => Number.isFinite(Number(row.change)) && Number.isFinite(Number(row.change_20d)),
    ),
  );
  const matrixDomain = computed(() => ({
    x: Math.max(0.01, ...matrixRows.value.map((row) => Math.abs(Number(row.change_20d || 0)))),
    y: Math.max(0.01, ...matrixRows.value.map((row) => Math.abs(Number(row.change || 0)))),
  }));
  const matrixPoints = computed(() => {
    const W = 1000;
    const H = 420;
    const pad = 52;
    const domain = matrixDomain.value;
    const x = (value: number) => pad + ((value + domain.x) / (2 * domain.x)) * (W - pad * 2);
    const y = (value: number) => H - pad - ((value + domain.y) / (2 * domain.y)) * (H - pad * 2);
    return matrixRows.value.map((row) => ({
      row,
      x: x(Number(row.change_20d || 0)),
      y: y(Number(row.change || 0)),
      positive: Number(row.change || 0) >= 0 && Number(row.change_20d || 0) >= 0,
      negative: Number(row.change || 0) < 0 && Number(row.change_20d || 0) < 0,
    }));
  });
  async function load() {
    loading.value = true;
    error.value = '';
    try {
      const [response, focusResponse] = await Promise.all([
        fetch(`/vibe-research/api/stock-pool?_ts=${Date.now()}`, { cache: 'no-store' }),
        fetch(`/vibe-research/api/stock-pool/focus?_ts=${Date.now()}`, { cache: 'no-store' }),
      ]);
      if (!response.ok) throw new Error(`股票池数据请求失败（HTTP ${response.status}）`);
      const payload = (await response.json()) as { data?: PoolPayload };
      data.value = payload.data || null;
      if (!focusCodes.value.length && payload.data?.definitions?.focus_codes) {
        focusCodes.value = [...payload.data.definitions.focus_codes];
      }
      if (focusResponse.ok) {
        const focusPayload = (await focusResponse.json()) as { data?: { codes?: string[] } };
        if (Array.isArray(focusPayload.data?.codes))
          focusCodes.value = [...focusPayload.data.codes];
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : '股票池数据请求失败';
    } finally {
      loading.value = false;
    }
  }
  async function saveFocus(next: string[]) {
    const previous = [...focusCodes.value];
    focusCodes.value = next;
    try {
      const response = await fetch('/vibe-research/api/stock-pool/focus', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codes: next }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      operationMessage.value = `近期关注已保存（${next.length} 只）`;
    } catch (e) {
      focusCodes.value = previous;
      operationMessage.value = `近期关注保存失败：${e instanceof Error ? e.message : '未知错误'}`;
    }
  }
  function sortBy(key: keyof Stock) {
    if (sortKey.value !== key) {
      sortKey.value = key;
      sortDirection.value = 'desc';
    } else if (sortDirection.value === 'desc') sortDirection.value = 'asc';
    else {
      sortKey.value = null;
      sortDirection.value = null;
    }
  }
  async function addFocus() {
    const codes = focusInput.value.match(/\d{6}/g) || [];
    if (!codes.length) return;
    await saveFocus([...new Set([...focusCodes.value, ...codes])]);
    focusInput.value = '';
    focusOpen.value = false;
  }
  async function removeFocus(code: string) {
    await saveFocus(focusCodes.value.filter((x) => x !== code));
  }
  async function addBatch() {
    const codes = (batchInput.value.match(/\d{5,6}/g) || []).slice(0, 50);
    if (!codes.length) {
      operationMessage.value = '未识别到证券代码';
      return;
    }
    try {
      const response = await fetch('/vibe-research/api/stock-pool/add-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ codes }),
      });
      const payload = (await response.json()) as {
        data?: { ok?: boolean; added?: string[]; failed?: string[]; count?: number };
        error?: string;
      };
      if (!response.ok || !payload.data?.ok)
        throw new Error(payload.error || `HTTP ${response.status}`);
      operationMessage.value = `已添加 ${payload.data.added?.length || 0} 只，股票池共 ${
        payload.data.count || 0
      } 只`;
      batchInput.value = '';
      editOpen.value = false;
      await load();
    } catch (e) {
      operationMessage.value = `批量添加失败：${e instanceof Error ? e.message : '未知错误'}`;
    }
  }
  async function removePool(row: Stock) {
    if (!window.confirm(`确定将「${row.name}」从核心股票池移除？`)) return;
    try {
      const response = await fetch(
        `/vibe-research/api/stock-pool/remove?instrument_id=${encodeURIComponent(
          row.instrument_id,
        )}`,
        { method: 'DELETE' },
      );
      const payload = (await response.json()) as {
        data?: { ok?: boolean; count?: number };
        error?: string;
      };
      if (!response.ok || !payload.data?.ok)
        throw new Error(payload.error || `HTTP ${response.status}`);
      operationMessage.value = `已移除 ${row.name}，股票池共 ${payload.data.count || 0} 只`;
      await load();
    } catch (e) {
      operationMessage.value = `移除失败：${e instanceof Error ? e.message : '未知错误'}`;
    }
  }
  async function syncPool() {
    syncing.value = true;
    try {
      const response = await fetch('/vibe-research/api/stock-pool/sync', { method: 'POST' });
      const payload = (await response.json()) as {
        data?: { ok?: boolean; commit?: string };
        error?: string;
      };
      if (!response.ok || !payload.data?.ok)
        throw new Error(payload.error || `HTTP ${response.status}`);
      operationMessage.value = payload.data.commit
        ? `股票池已同步（${payload.data.commit}）`
        : '股票池已同步';
    } catch (e) {
      operationMessage.value = `同步失败：${e instanceof Error ? e.message : '未知错误'}`;
    } finally {
      syncing.value = false;
    }
  }
  function heatColor(value: unknown, maxAbs = heatMaxAbs.value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '#334155';
    const x = Math.min(1, Math.abs(n) / Math.max(maxAbs, 0.005));
    return n >= 0
      ? `rgb(${Math.round(138 + 84 * x)},${Math.round(56 - 18 * x)},${Math.round(56 - 16 * x)})`
      : `rgb(28,${Math.round(108 + 62 * x)},${Math.round(70 + 8 * x)})`;
  }
  function formatNumber(value: unknown) {
    const n = Number(value);
    return Number.isFinite(n) ? n.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '—';
  }
  function formatPct(value: unknown) {
    const n = Number(value);
    return Number.isFinite(n) ? `${n > 0 ? '+' : ''}${(n * 100).toFixed(2)}%` : '—';
  }
  function tone(value: unknown) {
    const n = Number(value);
    return Number.isFinite(n) ? (n > 0 ? 'up' : n < 0 ? 'down' : '') : '';
  }
  function sortIndicator(key: keyof Stock) {
    return sortKey.value === key
      ? sortDirection.value === 'desc'
        ? '↓'
        : sortDirection.value === 'asc'
        ? '↑'
        : '↕'
      : '↕';
  }
  function openStockData(code: string | null | undefined) {
    if (code) {
      emit('query', code);
      requestAnimationFrame(() => {
        document.getElementById('a-share-stock-snapshot')?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      });
    }
  }
  onMounted(() => {
    if (typeof IntersectionObserver === 'undefined' || !poolRoot.value) {
      void load();
      return;
    }
    poolObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          poolObserver?.disconnect();
          poolObserver = null;
          void load();
        }
      },
      { rootMargin: '640px 0px' },
    );
    poolObserver.observe(poolRoot.value);
  });
  onBeforeUnmount(() => poolObserver?.disconnect());
</script>

<style scoped lang="less">
  .pool-card {
    display: grid;
    gap: 14px;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .pool-head {
    display: flex;
    justify-content: space-between;
    gap: 14px;
  }

  .pool-head h2 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 20px;
  }

  .pool-kpis {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 10px;
  }

  .pool-kpi {
    min-width: 0;
    padding: 12px 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 9px;
    background: var(--strategy-surface-2);
  }

  .pool-kpi span,
  .pool-kpi small {
    color: var(--strategy-text-3);
    font-size: 11px;
  }

  .pool-kpi strong {
    display: inline-block;
    margin-top: 5px;
    color: var(--strategy-text-1);
    font-size: 22px;
    font-variant-numeric: tabular-nums;
  }

  .pool-kpi small {
    margin-left: 4px;
  }

  .breadth-panel {
    padding: 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface-2);
  }

  .breadth-panel h3 {
    margin: 0 0 10px;
    color: var(--strategy-text-1);
    font-size: 15px;
  }

  .breadth-track {
    display: flex;
    height: 18px;
    overflow: hidden;
    border-radius: 6px;
    background: var(--strategy-border);
  }

  .breadth-track i {
    display: block;
    min-width: 1px;
  }

  .breadth-0 {
    background: #15803d;
  }

  .breadth-1 {
    background: #22c55e;
  }

  .breadth-2 {
    background: #94a3b8;
  }

  .breadth-3 {
    background: #f87171;
  }

  .breadth-4 {
    background: #dc2626;
  }

  .breadth-labels {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    margin-top: 6px;
    color: var(--strategy-text-3);
    font-size: 10px;
  }

  .breadth-labels span:nth-child(n + 2) {
    text-align: center;
  }

  .breadth-labels span:last-child {
    text-align: right;
  }

  .toolbar,
  .primary,
  .remove {
    min-height: 34px;
    padding: 0 11px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-2);
    cursor: pointer;
  }

  .primary {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    font-weight: 700;
  }

  .error {
    padding: 10px;
    border-radius: 8px;
    background: #fef2f2;
    color: #dc2626;
  }

  .pool-grid {
    display: grid;
    grid-template-columns: 1.2fr 1fr;
    gap: 14px;
  }

  .sub-panel {
    padding: 14px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface-2);
  }

  .sub-panel h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 15px;
  }

  .sub-panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .sub-panel-head select {
    height: 28px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
  }

  .rank-list {
    display: grid;
    gap: 6px;
  }

  .rank-row {
    display: grid;
    grid-template-columns: 120px 1fr 64px;
    align-items: center;
    gap: 8px;
    color: var(--strategy-text-2);
    font-size: 12px;
  }

  .rank-row i {
    height: 7px;
    overflow: hidden;
    border-radius: 99px;
    background: var(--strategy-border);
  }

  .rank-row i b {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: var(--strategy-accent);
  }

  .rank-row strong {
    text-align: right;
  }

  .leader-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .leader-columns h4 {
    margin: 0 0 5px;
    color: var(--strategy-text-3);
    font-size: 11px;
  }

  .leader-row {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 3px 6px;
    width: 100%;
    padding: 5px 0;
    border: 0;
    border-bottom: 1px solid var(--strategy-border);
    background: transparent;
    text-align: left;
    cursor: pointer;
  }

  .leader-row span {
    color: var(--strategy-text-1);
    font-size: 12px;
  }

  .leader-row small {
    grid-column: 1;
    color: var(--strategy-text-4);
    font-size: 10px;
  }

  .leader-row b {
    grid-column: 2;
    grid-row: 1 / span 2;
    align-self: center;
    font-size: 12px;
  }

  .leader-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .leader-panel {
    min-width: 0;
  }

  .matrix-wrap {
    overflow: hidden;
    aspect-ratio: 1000 / 420;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface);
  }

  .matrix-wrap svg {
    display: block;
    width: 100%;
    height: 100%;
  }

  .matrix-bg {
    fill: color-mix(in srgb, var(--strategy-surface) 94%, #64748b 6%);
  }

  .matrix-axis {
    stroke-width: 1;
    stroke-dasharray: 4 4;
    stroke: var(--strategy-text-4);
  }

  .matrix-axis-label,
  .matrix-quadrant-label {
    fill: var(--strategy-text-3);
    font-size: 12px;
  }

  .matrix-quadrant-label {
    fill: var(--strategy-text-4);
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .matrix-point {
    cursor: pointer;
  }

  .matrix-point circle {
    stroke-width: 1.2;
    stroke: var(--strategy-surface);
    opacity: 0.82;
  }

  .matrix-point circle.is-positive {
    fill: #22c55e;
  }

  .matrix-point circle.is-negative {
    fill: #ef4444;
  }

  .matrix-point circle.is-mixed {
    fill: #94a3b8;
  }

  .matrix-point.is-hover circle {
    stroke-width: 2.5;
    stroke: var(--strategy-accent-strong);
    opacity: 1;
  }

  .matrix-label {
    stroke-width: 3px;
    stroke: var(--strategy-surface);
    fill: var(--strategy-text-1);
    font-size: 11px;
    font-weight: 700;
    paint-order: stroke;
  }

  .heat-panel {
    padding-bottom: 12px;
  }

  .heatmap {
    display: grid;
    grid-auto-flow: dense;
    grid-template-columns: repeat(12, minmax(0, 1fr));
    gap: 5px;
  }

  .heat-tile {
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 58px;
    padding: 5px;
    border: 0;
    border-radius: 6px;
    color: #fff;
    text-align: left;
    cursor: pointer;
  }

  .heat-tile.s1 {
    grid-column: span 1;
    grid-row: span 1;
  }

  .heat-tile.s2 {
    grid-column: span 2;
    grid-row: span 1;
  }

  .heat-tile.s3 {
    grid-column: span 2;
    grid-row: span 2;
  }

  .heat-tile.s4 {
    grid-column: span 3;
    grid-row: span 2;
  }

  .heat-tile.group-start {
    border-left: 3px solid rgb(255 255 255 / 75%);
  }

  .heat-tile span {
    overflow: hidden;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .heat-tile b {
    font-size: 11px;
  }

  .heat-tile small {
    overflow: hidden;
    opacity: 0.8;
    font-size: 9px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .heat-legend {
    display: grid;
    gap: 5px;
    margin-top: 12px;
  }

  .heat-legend-gradient {
    height: 9px;
    border-radius: 99px;
    background: linear-gradient(
      90deg,
      #1caa4e 0%,
      #1c6c46 28%,
      #8896a8 50%,
      #8a3838 72%,
      #de2628 100%
    );
  }

  .heat-legend-scale {
    display: flex;
    justify-content: space-between;
    color: var(--strategy-text-4);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  .detail-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .detail-head h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 15px;
  }

  .operation-message {
    padding: 8px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-2);
    font-size: 12px;
  }

  .modal-mask {
    display: grid;
    place-items: center;
    position: fixed;
    z-index: 60;
    inset: 0;
    background: rgb(15 23 42 / 45%);
  }

  .modal {
    width: min(500px, 92vw);
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface);
    box-shadow: 0 24px 70px rgb(15 23 42 / 25%);
  }

  .modal h3 {
    margin: 0 0 14px;
    color: var(--strategy-text-1);
  }

  .modal-label {
    display: block;
    margin-bottom: 6px;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .modal-input {
    width: 100%;
    height: 38px;
    padding: 0 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-1);
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 16px;
  }

  .pool-toolbar,
  .focus-form {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .pool-toolbar input,
  .pool-toolbar select,
  .focus-form input {
    height: 36px;
    padding: 0 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
  }

  .pool-toolbar input {
    flex: 1 1 280px;
  }

  .table-shell {
    overflow: auto;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
  }

  table {
    width: 100%;
    min-width: 1180px;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 9px 10px;
    border-bottom: 1px solid var(--strategy-border);
    color: var(--strategy-text-2);
    font-size: 12px;
    text-align: center;
    white-space: nowrap;
  }

  th {
    background: var(--strategy-surface-2);
    color: var(--strategy-text-3);
    cursor: pointer;
  }

  .left {
    text-align: left;
  }

  .stock-link {
    padding: 0;
    border: 0;
    background: none;
    color: var(--strategy-text-1);
    font-weight: 700;
    cursor: pointer;
  }

  .stock-link + small {
    display: block;
    margin-top: 2px;
    color: var(--strategy-text-4);
    font-size: 10px;
  }

  .up {
    color: var(--strategy-up, #ef4444) !important;
  }

  .down {
    color: var(--strategy-down, #10b981) !important;
  }

  .remove {
    min-height: 28px;
    padding: 0 7px;
    color: #dc2626;
  }

  .empty {
    padding: 26px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  @media (max-width: 900px) {
    .pool-kpis {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .pool-head {
      flex-direction: column;
    }

    .pool-grid {
      grid-template-columns: 1fr;
    }

    .heatmap {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .leader-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .matrix-axis-label,
    .matrix-quadrant-label {
      font-size: 10px;
    }
  }

  @media (max-width: 560px) {
    .pool-kpis {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
