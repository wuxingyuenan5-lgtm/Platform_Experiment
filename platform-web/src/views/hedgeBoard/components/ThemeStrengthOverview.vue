<template>
  <div class="theme-strength">
    <div class="leader-grid">
      <section v-for="group in groups" :key="group.field" class="sub-panel leader-panel">
        <h3>{{ group.label }}</h3>
        <div class="leader-columns">
          <div v-for="side in sides" :key="side.key">
            <h4>{{ side.label }}</h4>
            <button
              v-for="row in group[side.key]"
              :key="row.code"
              class="leader-row"
              type="button"
              @click="select(row.code)"
            >
              <span>{{ row.name }}</span
              ><small>{{ row.industry }}</small>
              <b :class="tone(row[group.field])">{{ formatPct(row[group.field]) }}</b>
            </button>
            <div v-if="!group[side.key].length" class="empty">暂无有效数据</div>
          </div>
        </div>
      </section>
    </div>
    <section class="sub-panel matrix-panel">
      <div class="sub-panel-head">
        <div class="matrix-heading"><span>STRENGTH MAP</span><h3>强弱矩阵</h3></div>
        <div class="matrix-legend">
          <span class="matrix-legend--leader">领涨 {{ matrixQuadrants.leader }}</span>
          <span class="matrix-legend--improving">改善 {{ matrixQuadrants.improving }}</span>
          <span class="matrix-legend--weakening">转弱 {{ matrixQuadrants.weakening }}</span>
          <span class="matrix-legend--lagging">领跌 {{ matrixQuadrants.lagging }}</span>
        </div>
      </div>
      <div v-if="matrixPoints.length" class="matrix-wrap">
        <svg viewBox="0 0 1000 420" preserveAspectRatio="xMidYMid meet" aria-label="主题强弱矩阵">
          <rect x="52" y="52" width="448" height="158" class="matrix-zone matrix-zone--improving" />
          <rect x="500" y="52" width="448" height="158" class="matrix-zone matrix-zone--leader" />
          <rect x="52" y="210" width="448" height="158" class="matrix-zone matrix-zone--lagging" />
          <rect
            x="500"
            y="210"
            width="448"
            height="158"
            class="matrix-zone matrix-zone--weakening"
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
          <text x="70" y="76" class="matrix-quadrant-label">改善</text>
          <text x="930" y="76" text-anchor="end" class="matrix-quadrant-label">领涨</text>
          <text x="70" y="348" class="matrix-quadrant-label">领跌</text>
          <text x="930" y="348" text-anchor="end" class="matrix-quadrant-label">转弱</text>
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
            tabindex="0"
            role="button"
            :aria-label="`${point.row.name}，今日${formatPct(point.row.change)}，20日${formatPct(
              point.row.change_20d,
            )}`"
            @focus="matrixHoverId = point.row.instrument_id"
            @blur="matrixHoverId = null"
            @keydown.enter="select(point.row.code)"
            :class="{ 'is-hover': matrixHoverId === point.row.instrument_id }"
            @mouseenter="matrixHoverId = point.row.instrument_id"
            @mouseleave="matrixHoverId = null"
            @click="select(point.row.code)"
          >
            <circle
              :cx="point.x"
              :cy="point.y"
              :r="point.radius"
              :class="point.positive ? 'is-positive' : point.negative ? 'is-negative' : 'is-mixed'"
            />
            <line
              v-if="Math.abs(point.labelY - point.y) > 20"
              :x1="point.x"
              :y1="point.y"
              :x2="point.labelX"
              :y2="point.labelY - 4"
              class="matrix-label-link"
            />
            <text
              :x="point.labelX"
              :y="point.labelY"
              :text-anchor="point.labelAnchor"
              class="matrix-label"
            >
              {{ point.row.name }}
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
  </div>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type { EquityTheme } from '@/api/equityObservatory';
  import { themeStrengthRows, strengthRanking, strengthMatrix } from './themeStrength';

  const props = defineProps<{ themes: EquityTheme[] }>();
  const emit = defineEmits<{ (event: 'select', name: string): void }>();
  const select = (name: string) => emit('select', name);
  const sides = [
    { key: 'up', label: '最强' },
    { key: 'down', label: '最弱' },
  ] as const;
  const rows = computed(() => themeStrengthRows(props.themes));
  const groups = computed(() =>
    [
      { field: 'change' as const, label: '今日最强 / 最弱' },
      { field: 'change_5d' as const, label: '5日强弱排行' },
      { field: 'change_20d' as const, label: '20日强弱排行' },
    ].map((group) => ({ ...group, ...strengthRanking(rows.value, group.field) })),
  );
  const matrix = computed(() => strengthMatrix(rows.value));
  const matrixPoints = computed(() => matrix.value.points);
  const matrixDomain = computed(() => matrix.value.domain);
  const matrixQuadrants = computed(() => matrix.value.quadrants);
  const matrixHoverId = ref<string | null>(null);
  const formatPct = (n: number | null) =>
    n === null ? '—' : `${n > 0 ? '+' : ''}${(n * 100).toFixed(2)}%`;
  const tone = (n: number | null) => (n === null ? '' : n > 0 ? 'up' : n < 0 ? 'down' : '');
</script>
<style scoped lang="less">
  .theme-strength {
    --strategy-bg: #fbfcfe;
    --strategy-surface: #fff;
    --strategy-surface-2: #f7f9fc;
    --strategy-border: #d9e3ee;
    --strategy-text-1: #10233d;
    --strategy-text-2: #354d68;
    --strategy-text-3: #60758f;
    --strategy-text-4: #7b8da4;
    --strategy-accent: #1d4ed8;
    --strategy-accent-soft: #eaf2ff;
    --strategy-accent-strong: #1d4ed8;
    --strategy-accent-ring: rgb(29 78 216 / 16%);
    --strategy-up: #df4b47;
    --strategy-down: #0e9f78;
    --strategy-radius-card: 14px;
    --strategy-radius-control: 8px;
    --strategy-tab-height: 36px;
    --strategy-font-base: 13px;
    --strategy-shadow: 0 12px 28px rgb(26 54 93 / 6%);

    display: grid;
    gap: 14px;
    margin-bottom: 24px;
  }

  .sub-panel {
    min-width: 0;
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
    margin-top: 10px;
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
    border: 1px solid color-mix(in srgb, var(--strategy-border) 70%, #64748b 30%);
    border-radius: 11px;
    background: #fbfcfe;
    box-shadow: inset 0 1px 0 rgb(255 255 255 / 80%);
  }

  .matrix-wrap svg {
    display: block;
    width: 100%;
    height: 100%;
  }

  .matrix-heading h3 {
    margin: 0;
  }

  .matrix-legend {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 5px;
  }

  .matrix-legend span {
    padding: 4px 7px;
    border-radius: 99px;
    font-size: 10px;
    font-variant-numeric: tabular-nums;
  }

  .matrix-legend--leader {
    background: #fee2e2;
    color: #b91c1c;
  }

  .matrix-legend--improving {
    background: #fff7ed;
    color: #c2410c;
  }

  .matrix-legend--weakening {
    background: #ecfdf5;
    color: #047857;
  }

  .matrix-legend--lagging {
    background: #eff6ff;
    color: #1d4ed8;
  }

  .matrix-zone {
    stroke-width: 1;
    stroke: #e2e8f0;
  }

  .matrix-zone--leader {
    fill: #fff1f2;
  }

  .matrix-zone--improving {
    fill: #fffaf0;
  }

  .matrix-zone--weakening {
    fill: #f0fdf4;
  }

  .matrix-zone--lagging {
    fill: #f0f7ff;
  }

  .matrix-axis {
    stroke-width: 1;
    stroke-dasharray: 3 5;
    stroke: #94a3b8;
  }

  .matrix-axis-label,
  .matrix-quadrant-label {
    fill: var(--strategy-text-3);
    font-size: 12px;
  }

  .matrix-quadrant-label {
    fill: #64748b;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .matrix-point {
    cursor: pointer;
  }

  .matrix-point circle {
    stroke-width: 1.5;
    stroke: #fff;
    opacity: 0.9;
    filter: drop-shadow(0 1px 1px rgb(15 23 42 / 18%));
  }

  .matrix-point circle.is-positive {
    fill: #ef4444;
  }

  .matrix-point circle.is-negative {
    fill: #10b981;
  }

  .matrix-point circle.is-mixed {
    fill: #94a3b8;
  }

  .matrix-point.is-hover circle {
    stroke-width: 3;
    stroke: var(--strategy-accent-strong);
    opacity: 1;
  }

  .matrix-label-link {
    stroke-width: 0.6;
    stroke: #94a3b8;
    pointer-events: none;
  }

  .matrix-label {
    stroke-width: 3px;
    stroke: #fff;
    fill: var(--strategy-text-1);
    font-size: 10px;
    font-weight: 500;
    paint-order: stroke;
    pointer-events: none;
  }

  .empty {
    padding: 26px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  .matrix-heading > span {
    display: block;
    margin-bottom: 3px;
    color: var(--strategy-accent-strong);
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  button,
  select {
    font: inherit;
  }

  button:focus-visible,
  select:focus-visible,
  .matrix-point:focus-visible {
    outline: 2px solid var(--strategy-accent);
    outline-offset: 3px;
  }

  .leader-panel:first-child {
    grid-column: 1 / -1;
  }

  .up {
    color: var(--strategy-up, #ef4444) !important;
  }

  .down {
    color: var(--strategy-down, #10b981) !important;
  }

  @media (max-width: 1100px) {
    .leader-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 600px) {
    .matrix-legend {
      justify-content: flex-start;
    }

    .sub-panel-head {
      flex-wrap: wrap;
      gap: 8px;
    }
  }
</style>
