<template>
  <div class="research-plot">
    <div class="plot-legend"
      ><span v-for="line in series" :key="line.name"
        ><i :style="{ background: line.color }"></i>{{ line.name }}</span
      ><button type="button" @click="table = !table">{{
        table ? '查看图表' : '查看数据'
      }}</button></div
    >
    <div v-if="table" class="plot-table"
      ><table
        ><thead
          ><tr
            ><th>时间</th
            ><th v-for="line in series" :key="line.name">{{ line.name }}（{{ unit }}）</th></tr
          ></thead
        ><tbody
          ><tr v-for="(label, i) in labels" :key="i"
            ><td>{{ label }}</td
            ><td v-for="line in series" :key="line.name">{{
              line.values[i]?.toFixed(2) ?? '—'
            }}</td></tr
          ></tbody
        ></table
      ></div
    >
    <template v-else>
      <svg viewBox="0 0 660 220" role="img" :aria-label="title" @mouseleave="hover = -1">
        <g v-for="tick in ticks" :key="tick">
          <line
            x1="52"
            x2="644"
            :y1="y(tick)"
            :y2="y(tick)"
            stroke="#e5ebf2"
            stroke-dasharray="3 4"
          />
          <text x="42" :y="y(tick) + 4" text-anchor="end">{{ tick.toFixed(1) }}</text>
        </g>
        <line v-if="min <= 0 && max >= 0" x1="52" x2="644" :y1="y(0)" :y2="y(0)" stroke="#b3c1d2" />
        <polyline
          v-for="line in series"
          :key="line.name"
          :points="line.values.map((v, i) => `${x(i)},${y(v)}`).join(' ')"
          fill="none"
          :stroke="line.color"
          stroke-width="2.3"
          stroke-linejoin="round"
        />
        <line
          v-if="hover >= 0"
          :x1="x(hover)"
          :x2="x(hover)"
          y1="14"
          y2="185"
          stroke="#71859c"
          stroke-dasharray="4 4"
        />
        <rect
          v-for="(_, i) in labels"
          :key="i"
          :x="x(i) - 296 / Math.max(labels.length - 1, 1)"
          y="10"
          :width="592 / Math.max(labels.length - 1, 1)"
          height="180"
          fill="transparent"
          @mouseenter="hover = i"
        />
        <text x="52" y="212">{{ labels[0] }}</text>
        <text class="axis-mid" x="348" y="212" text-anchor="middle">
          {{ labels[Math.floor(labels.length / 2)] }}
        </text>
        <text x="644" y="212" text-anchor="end">{{ labels[labels.length - 1] }}</text>
      </svg>
      <div class="plot-readout" aria-live="polite"
        ><span>{{ labels[active] }}</span
        ><strong v-for="line in series" :key="line.name" :style="{ color: line.color }"
          >{{ line.name }} {{ line.values[active]?.toFixed(2) }} {{ unit }}</strong
        ></div
      >
    </template>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';

  const props = defineProps<{
    title: string;
    unit: string;
    labels: string[];
    series: { name: string; color: string; values: number[] }[];
  }>();
  const table = ref(false);
  const hover = ref(-1);
  const all = computed(() => props.series.flatMap((s) => s.values));
  const rawMin = computed(() => Math.min(...all.value));
  const rawMax = computed(() => Math.max(...all.value));
  const pad = computed(() => Math.max((rawMax.value - rawMin.value) * 0.15, 0.2));
  const min = computed(() => rawMin.value - pad.value);
  const max = computed(() => rawMax.value + pad.value);
  const ticks = computed(() =>
    Array.from({ length: 4 }, (_, i) => min.value + ((max.value - min.value) * i) / 3),
  );
  const active = computed(() =>
    hover.value >= 0 && hover.value < props.labels.length ? hover.value : props.labels.length - 1,
  );
  const x = (i: number) => 52 + (i * 592) / Math.max(props.labels.length - 1, 1);
  const y = (v: number) => 185 - ((v - min.value) * 171) / (max.value - min.value);
</script>
<style scoped>
  .research-plot {
    min-width: 0;
  }

  .plot-legend {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    color: #53667e;
    font-size: 12px;
    gap: 14px;
  }

  .plot-legend span {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  i {
    width: 12px;
    height: 3px;
    border-radius: 3px;
  }

  button {
    margin-left: auto;
    border: 0;
    background: none;
    color: #366696;
    cursor: pointer;
  }

  svg {
    display: block;
    width: 100%;
    margin-top: 10px;
    overflow: hidden;
  }

  text {
    fill: #67798e;
    font: 11px 'Segoe UI', sans-serif;
  }

  .plot-readout {
    display: flex;
    flex-wrap: wrap;
    min-height: 24px;
    color: #67798e;
    font-size: 11px;
    gap: 14px;
  }

  .plot-readout strong {
    font-weight: 500;
  }

  .plot-table {
    max-height: 249px;
    margin-top: 10px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 8px;
    border-bottom: 1px solid #e5ebf2;
    text-align: right;
    white-space: nowrap;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  @media (max-width: 560px) {
    text {
      font-size: 20px;
    }

    .axis-mid {
      display: none;
    }
  }
</style>
