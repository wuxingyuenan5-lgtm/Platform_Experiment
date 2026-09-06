<template>
  <section id="a-share-watchlist-pool" class="pool-card">
    <header class="pool-head"
      ><div><h2>自选股与核心股票池</h2></div
      ><button type="button" class="toolbar" :disabled="loading" @click="load">{{
        loading ? '刷新中…' : '刷新数据'
      }}</button></header
    >
    <div v-if="error" class="error">{{ error }}</div>
    <template v-if="data">
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
                @click="emit('query', row.code || '')"
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
                @click="emit('query', row.code || '')"
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
                @click="emit('query', row.code || '')"
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
                @click="emit('query', row.code || '')"
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
          <div><h3>强弱矩阵</h3><p>今日涨幅 × 20日涨幅；点击标的查看个股数据。</p></div>
          <span class="matrix-legend">红色上涨 · 绿色下跌 · 灰色为混合信号</span>
        </div>
        <div class="matrix-grid">
          <div
            v-for="bucket in matrixBuckets"
            :key="bucket.key"
            class="matrix-quadrant"
            :class="bucket.key"
          >
            <h4
              >{{ bucket.label }}<small>{{ bucket.rows.length }}只</small></h4
            >
            <button
              v-for="row in bucket.rows.slice(0, 12)"
              :key="row.instrument_id"
              type="button"
              @click="emit('query', row.code || '')"
            >
              <span>{{ row.name }}</span
              ><b :class="tone(row.change)">{{ formatPct(row.change) }}</b>
            </button>
            <p v-if="!bucket.rows.length" class="empty">暂无数据</p>
          </div>
        </div>
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
            :style="{ background: heatColor(tile[heatPeriod]) }"
            :title="`${tile.name} · ${tile.industry}`"
            @click="emit('query', tile.code || '')"
            ><span>{{ tile.name }}</span
            ><b>{{ formatPct(tile[heatPeriod]) }}</b
            ><small>{{ tile.industry }}</small></button
          ><div v-if="!heatTiles.length" class="empty">暂无数据</div></div
        ></section
      >
      <div class="pool-toolbar"
        ><input v-model.trim="query" type="search" placeholder="搜索名称 / 行业 / 代码" /><select
          v-model="filter"
          ><option value="">全部股票</option
          ><option value="__focus__">★ 近期关注（{{ focusCodes.length }}）</option
          ><option v-for="basket in baskets" :key="basket.key" :value="`basket:${basket.key}`"
            >{{ basket.name }}（{{ basket.count }}）</option
          ><option v-for="industry in industries" :key="industry" :value="`industry:${industry}`">{{
            industry
          }}</option></select
        ><button
          v-if="filter === '__focus__'"
          type="button"
          class="primary"
          @click="
            focusInput = '';
            focusOpen = true;
          "
          >添加关注</button
        ></div
      >
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
              ><th class="left" @click="sortBy('name')">名称 ↕</th><th class="left">行业</th
              ><th @click="sortBy('price')">现价 ↕</th><th @click="sortBy('change')">今日 ↕</th
              ><th @click="sortBy('change_5d')">5日 ↕</th
              ><th @click="sortBy('change_20d')">20日 ↕</th><th @click="sortBy('ytd')">YTD ↕</th
              ><th @click="sortBy('amount_yi')">成交额(亿) ↕</th
              ><th @click="sortBy('mcap_yi')">市值(亿) ↕</th><th></th></tr></thead
          ><tbody
            ><tr v-for="row in visibleRows" :key="row.instrument_id"
              ><td class="left"
                ><button type="button" class="stock-link" @click="$emit('query', row.code || '')">{{
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
              ><td>{{ formatNumber(row.mcap_yi) }}</td
              ><td
                ><button
                  v-if="filter === '__focus__'"
                  type="button"
                  class="remove"
                  @click="removeFocus(row.code || '')"
                  >取消关注</button
                ></td
              ></tr
            ><tr v-if="!visibleRows.length"
              ><td colspan="10" class="empty">暂无匹配股票</td></tr
            ></tbody
          ></table
        ></div
      >
    </template>
    <div v-else-if="!loading" class="empty"
      >暂无股票池数据；数据源不可用时不会伪造 0 或静态行情。</div
    >
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';

  interface Stock {
    instrument_id: string;
    code?: string;
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
  }
  type Period = 'change' | 'change_5d' | 'change_20d' | 'ytd';
  interface PoolPayload {
    summary: {
      tracked_count: number;
      breadth: { up: number; down: number; flat: number };
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
    definitions?: { research_baskets?: Array<{ key: string; name: string; count: number }> };
  }
  const emit = defineEmits<{ (event: 'query', code: string): void }>();
  const data = ref<PoolPayload | null>(null);
  const loading = ref(false);
  const error = ref('');
  const query = ref('');
  const filter = ref('');
  const sortKey = ref<keyof Stock | null>(null);
  const sortDirection = ref<'asc' | 'desc'>('desc');
  const focusCodes = ref<string[]>(
    JSON.parse(localStorage.getItem('vg_vibe_focus_codes') || '[]') as string[],
  );
  const focusOpen = ref(false);
  const focusInput = ref('');
  const rankingPeriod = ref<Period>('change');
  const heatPeriod = ref<Period>('change');
  const baskets = computed(() => data.value?.definitions?.research_baskets || []);
  const industries = computed(() =>
    [
      ...new Set((data.value?.stocks || []).map((x) => x.industry).filter(Boolean) as string[]),
    ].sort((a, b) => a.localeCompare(b, 'zh-CN')),
  );
  const visibleRows = computed(() => {
    if (!data.value) return [];
    const q = query.value.toLowerCase();
    const basketCodes = filter.value.startsWith('basket:')
      ? new Set(
          data.value.stocks
            .filter((x) => x.research_baskets?.includes(filter.value.slice(7)))
            .map((x) => x.code),
        )
      : null;
    const industry = filter.value.startsWith('industry:') ? filter.value.slice(9) : '';
    let rows = data.value.stocks.filter(
      (x) =>
        (!q || `${x.name} ${x.code} ${x.industry}`.toLowerCase().includes(q)) &&
        (filter.value !== '__focus__' || focusCodes.value.includes(x.code || '')) &&
        (!industry || x.industry === industry) &&
        (!basketCodes || basketCodes.has(x.code)),
    );
    if (sortKey.value) {
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
    return [...rows]
      .sort((a, b) => Number(b[rankingPeriod.value] || 0) - Number(a[rankingPeriod.value] || 0))
      .slice(0, 8);
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
  const matrixBuckets = computed(() => {
    const rows = (data.value?.stocks || []).filter(
      (row) => Number.isFinite(Number(row.change)) && Number.isFinite(Number(row.change_20d)),
    );
    const byStrength = (a: Stock, b: Stock) =>
      Math.abs(Number(b.change)) +
      Math.abs(Number(b.change_20d)) -
      (Math.abs(Number(a.change)) + Math.abs(Number(a.change_20d)));
    return [
      {
        key: 'improving',
        label: '改善（今日涨 / 20日跌）',
        rows: rows
          .filter((row) => Number(row.change) >= 0 && Number(row.change_20d) < 0)
          .sort(byStrength),
      },
      {
        key: 'leading',
        label: '领涨（今日涨 / 20日涨）',
        rows: rows
          .filter((row) => Number(row.change) >= 0 && Number(row.change_20d) >= 0)
          .sort(byStrength),
      },
      {
        key: 'lagging',
        label: '领跌（今日跌 / 20日跌）',
        rows: rows
          .filter((row) => Number(row.change) < 0 && Number(row.change_20d) < 0)
          .sort(byStrength),
      },
      {
        key: 'weakening',
        label: '转弱（今日跌 / 20日涨）',
        rows: rows
          .filter((row) => Number(row.change) < 0 && Number(row.change_20d) >= 0)
          .sort(byStrength),
      },
    ];
  });
  const heatTiles = computed(() =>
    [...(data.value?.heatmap || [])]
      .sort((a, b) => Number(b.weight || 0) - Number(a.weight || 0))
      .slice(0, 80),
  );
  async function load() {
    loading.value = true;
    error.value = '';
    try {
      const response = await fetch(`/vibe-research/api/stock-pool?_ts=${Date.now()}`, {
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(`股票池数据请求失败（HTTP ${response.status}）`);
      const payload = (await response.json()) as { data?: PoolPayload };
      data.value = payload.data || null;
    } catch (e) {
      error.value = e instanceof Error ? e.message : '股票池数据请求失败';
    } finally {
      loading.value = false;
    }
  }
  function sortBy(key: keyof Stock) {
    if (sortKey.value !== key) {
      sortKey.value = key;
      sortDirection.value = 'desc';
    } else sortDirection.value = sortDirection.value === 'desc' ? 'asc' : 'desc';
  }
  function addFocus() {
    const codes = focusInput.value.match(/\d{6}/g) || [];
    focusCodes.value = [...new Set([...focusCodes.value, ...codes])];
    localStorage.setItem('vg_vibe_focus_codes', JSON.stringify(focusCodes.value));
    focusInput.value = '';
    focusOpen.value = false;
  }
  function removeFocus(code: string) {
    focusCodes.value = focusCodes.value.filter((x) => x !== code);
    localStorage.setItem('vg_vibe_focus_codes', JSON.stringify(focusCodes.value));
  }
  function heatColor(value: unknown) {
    const n = Number(value);
    if (!Number.isFinite(n)) return '#334155';
    const x = Math.min(1, Math.abs(n) / 0.08);
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
  onMounted(load);
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

  .sub-panel-head p {
    margin: 3px 0 0;
    color: var(--strategy-text-4);
    font-size: 11px;
  }

  .matrix-legend {
    color: var(--strategy-text-4);
    font-size: 11px;
    white-space: nowrap;
  }

  .matrix-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }

  .matrix-quadrant {
    min-width: 0;
    padding: 9px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: color-mix(in srgb, var(--strategy-surface) 92%, #64748b 8%);
  }

  .matrix-quadrant h4 {
    display: flex;
    justify-content: space-between;
    gap: 4px;
    margin: 0 0 5px;
    color: var(--strategy-text-2);
    font-size: 11px;
  }

  .matrix-quadrant h4 small {
    color: var(--strategy-text-4);
    font-size: 10px;
    font-weight: 400;
  }

  .matrix-quadrant button {
    display: flex;
    justify-content: space-between;
    width: 100%;
    padding: 4px 0;
    border: 0;
    border-bottom: 1px solid color-mix(in srgb, var(--strategy-border) 70%, transparent);
    background: transparent;
    color: var(--strategy-text-2);
    font-size: 11px;
    text-align: left;
    cursor: pointer;
  }

  .matrix-quadrant button:last-of-type {
    border-bottom: 0;
  }

  .matrix-quadrant.improving,
  .matrix-quadrant.leading {
    box-shadow: inset 3px 0 0 var(--strategy-up, #ef4444);
  }

  .matrix-quadrant.lagging,
  .matrix-quadrant.weakening {
    box-shadow: inset 3px 0 0 var(--strategy-down, #10b981);
  }

  .heat-panel {
    padding-bottom: 12px;
  }

  .heatmap {
    display: grid;
    grid-template-columns: repeat(8, minmax(0, 1fr));
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
    min-width: 900px;
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
    .pool-head {
      flex-direction: column;
    }

    .pool-grid {
      grid-template-columns: 1fr;
    }

    .heatmap {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .leader-grid,
    .matrix-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
