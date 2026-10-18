<template>
  <section class="cross-asset" aria-labelledby="cross-asset-title">
    <header>
      <div><h3 id="cross-asset-title">跨资产同窗比较</h3><p>美股 · 黄金 · 比特币</p></div>
      <div class="controls" aria-label="比较区间">
        <button
          v-for="window in [30, 90, 180]"
          :key="window"
          type="button"
          :aria-pressed="days === window"
          @click="days = window"
          >{{ window }}天</button
        >
        <button type="button" :disabled="loading" @click="load">刷新</button>
      </div>
    </header>
    <p v-if="loading" role="status">正在读取比较数据…</p>
    <p v-else-if="error" role="alert">比较数据暂不可用，请稍后刷新。</p>
    <template v-else-if="data?.dates.length">
      <div class="summary">
        <span
          >{{ data.dates[0] }} — {{ data.dates.at(-1) }} ·
          {{ data.dates.length }} 个共同观测日</span
        >
        <span
          >同期美国10年期收益率：<b>{{ format(data.yieldChangeBp, 'bp') }}</b></span
        >
      </div>
      <ChartExpand title="跨资产同窗比较">
        <div class="plot">
          <svg
            viewBox="0 0 900 260"
            role="img"
            aria-label="以共同起点100归一化的价格走势，左右方向键查看数值"
            tabindex="0"
            @pointermove="moveHover"
            @pointerleave="hover = null"
            @focus="hover = data.dates.length - 1"
            @blur="hover = null"
            @keydown.left.prevent="stepHover(-1)"
            @keydown.right.prevent="stepHover(1)"
          >
            <g v-for="tick in ticks" :key="tick">
              <line x1="48" x2="880" :y1="y(tick)" :y2="y(tick)" />
              <text x="4" :y="y(tick) + 4">{{ tick.toFixed(0) }}</text>
            </g>
            <polyline
              v-for="(asset, index) in data.assets"
              :key="asset.id"
              :points="path(asset.normalized)"
              :stroke="colors[index]"
            />
            <text x="48" y="253">{{ data.dates[0] }}</text>
            <text x="880" y="253" text-anchor="end">{{ data.dates.at(-1) }}</text>
            <line
              v-if="hover != null"
              :x1="x(hover)"
              :x2="x(hover)"
              y1="15"
              y2="225"
              class="cursor"
            />
          </svg>
          <div v-if="hover != null" class="hover-values" role="status">
            <b>{{ data.dates[hover] }}</b>
            <span
              v-for="(asset, index) in data.assets"
              :key="asset.id"
              :style="{ color: colors[index] }"
              >{{ asset.label }} {{ format(asset.normalized[hover]) }}</span
            >
          </div>
        </div>
      </ChartExpand>
      <div class="table-scroll" tabindex="0" role="region" aria-label="跨资产比较指标，可横向滚动">
        <table
          ><thead
            ><tr
              ><th>资产</th><th>区间价格收益</th><th>共同观测日回撤</th><th>与美股相关性</th
              ><th>美股下跌时平均收益</th></tr
            ></thead
          >
          <tbody
            ><tr v-for="(asset, index) in data.assets" :key="asset.id">
              <th
                ><i :style="{ background: colors[index] }"></i>{{ asset.label
                }}<small
                  >{{ asset.source
                  }}{{ asset.status !== 'ready' ? ' · 待更新／不完整' : '' }}</small
                ></th
              >
              <td>{{ format(asset.returnPct, '%') }}</td
              ><td>{{ format(asset.drawdownPct, '%') }}</td
              ><td>{{ format(asset.correlation20) }}</td>
              <td
                >{{ format(asset.downsideMeanPct, '%')
                }}<small>{{ asset.downsideSamples }} 个下跌区间</small></td
              >
            </tr></tbody
          >
        </table>
      </div>
      <p v-if="data.unavailable.length">暂无足够历史：{{ data.unavailable.join('、') }}</p>
      <p class="definition"
        >美元价格收益，不含分红；黄金使用 GLD
        ETF。仅匹配各市场已结束日期，不补齐缺失日；各市场收盘时刻不同。相关性取最近20个共同收益区间，至少10个；下跌平均至少5个样本。历史相关性不保证未来对冲效果。</p
      >
    </template>
    <p v-else>暂无足够的共同日期历史。</p>
  </section>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue';
  import { getCrossAssetComparison, type CrossAssetComparison } from '@/api/hedgeResearch';
  import ChartExpand from './ChartExpand.vue';

  const days = ref(90);
  const data = ref<CrossAssetComparison | null>(null);
  const loading = ref(false);
  const error = ref(false);
  const hover = ref<number | null>(null);
  let request = 0;
  const colors = ['#147d92', '#b17a24', '#775bb8'];
  async function load() {
    const id = ++request;
    loading.value = true;
    error.value = false;
    hover.value = null;
    try {
      const result = await getCrossAssetComparison(days.value);
      if (id === request) data.value = result;
    } catch {
      if (id === request) error.value = true;
    } finally {
      if (id === request) loading.value = false;
    }
  }
  watch(days, load, { immediate: true });
  onBeforeUnmount(() => {
    ++request;
  });
  const values = computed(
    () => data.value?.assets.flatMap((a) => a.normalized.map(Number)).filter(Number.isFinite) ?? [],
  );
  const bounds = computed(() => {
    const low = Math.min(100, ...values.value),
      high = Math.max(100, ...values.value);
    const pad = Math.max(2, (high - low) * 0.1);
    return [low - pad, high + pad];
  });
  const ticks = computed(() =>
    Array.from(
      { length: 5 },
      (_, i) => bounds.value[0] + ((bounds.value[1] - bounds.value[0]) * i) / 4,
    ),
  );
  const y = (value: number) =>
    225 - ((value - bounds.value[0]) / (bounds.value[1] - bounds.value[0])) * 210;
  const x = (index: number) =>
    48 + (index / Math.max(1, (data.value?.dates.length ?? 1) - 1)) * 832;
  function stepHover(step: number) {
    const last = (data.value?.dates.length ?? 1) - 1;
    hover.value = Math.max(0, Math.min(last, (hover.value ?? last) + step));
  }
  function moveHover(event: PointerEvent) {
    const svg = event.currentTarget as SVGSVGElement;
    const matrix = svg.getScreenCTM();
    if (!matrix) return;
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const ratio = (point.matrixTransform(matrix.inverse()).x - 48) / 832;
    hover.value = Math.max(
      0,
      Math.min(
        (data.value?.dates.length ?? 1) - 1,
        Math.round(ratio * ((data.value?.dates.length ?? 1) - 1)),
      ),
    );
  }
  const path = (points: string[]) =>
    points
      .map((value, i) => `${48 + (i / Math.max(1, points.length - 1)) * 832},${y(Number(value))}`)
      .join(' ');
  const format = (value: string | null, suffix = '') =>
    value == null || !Number.isFinite(Number(value)) ? '—' : `${Number(value).toFixed(2)}${suffix}`;
</script>
<style scoped>
  .cross-asset {
    min-width: 0;
    margin: 16px 0;
    padding: 20px;
    border: 1px solid #dce5ec;
    border-radius: 16px;
    background: #fff;
    color: #233c4a;
  }

  header,
  .summary,
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  h3 {
    margin: 0;
    font-size: 17px;
  }

  p {
    margin: 8px 0;
    color: #657989;
    font-size: 12px;
  }

  button {
    padding: 6px 12px;
    border: 1px solid #d5e1e9;
    border-radius: 8px;
    background: #f7fafc;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: #71aeb9;
    background: #e4f1f3;
    color: #0d667a;
  }

  button:focus-visible,
  .table-scroll:focus-visible {
    outline: 2px solid #147d92;
    outline-offset: 2px;
  }

  .summary {
    margin-top: 12px;
    font-size: 12px;
  }

  .plot {
    width: 100%;
    padding: 12px 0;
  }

  svg {
    display: block;
    width: 100%;
    min-height: 180px;
    max-height: 320px;
  }

  polyline {
    stroke-width: 2;
    fill: none;
    vector-effect: non-scaling-stroke;
  }

  :deep(.chart-expand__surface[aria-modal='true']) svg {
    height: calc(100vh - 120px);
    max-height: none;
  }

  line {
    stroke: #e5edf2;
  }

  text {
    fill: #657989;
    font-size: 11px;
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    min-width: 650px;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 10px;
    border-bottom: 1px solid #e5edf2;
    text-align: right;
  }

  th:first-child {
    text-align: left;
  }

  small {
    display: block;
    margin-top: 4px;
    color: #657989;
    font-size: 10px;
    font-weight: normal;
  }

  i {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 6px;
    border-radius: 50%;
  }

  .definition {
    line-height: 1.7;
  }

  .cursor {
    stroke-dasharray: 4;
    stroke: #8194a2;
  }

  .hover-values {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    min-height: 20px;
    font-size: 12px;
  }

  @media (max-width: 600px) {
    .cross-asset {
      padding: 12px;
    }
  }
</style>
