<template>
  <div class="fomc-panel">
    <p v-if="loading">加载会议概率…</p>
    <p v-else-if="error">{{ error }}</p>
    <p v-else-if="!meeting">暂无 FOMC 会议概率</p>
    <template v-else>
      <header
        ><h3>美联储 {{ meeting.meetingDate }} 的决定？</h3
        ><a :href="meeting.sourceUrl" target="_blank" rel="noopener noreferrer"
          >参考网页 ↗</a
        ></header
      >
      <nav aria-label="FOMC会议"
        ><button
          v-for="item in orderedMeetings"
          :key="item.id"
          :class="{ active: meeting.id === item.id }"
          :aria-pressed="meeting.id === item.id"
          @click="selectedId = item.id"
          >{{ item.meetingDate }}{{ item.closed ? ' · 已结束' : '' }}</button
        ></nav
      >
      <nav aria-label="图表范围"
        ><button
          v-for="years in [0.25, 1, 3, 5, 10, 0]"
          :key="years"
          :class="{ active: selectedYears === years }"
          :aria-pressed="selectedYears === years"
          @click="selectedYears = years"
          >{{ years === 0 ? '全部' : years === 0.25 ? '3个月' : `${years}年` }}</button
        ></nav
      >
      <div class="outcomes"
        ><button
          v-for="line in lines"
          :key="line.id"
          :aria-pressed="!hidden.has(line.id)"
          :class="{ muted: hidden.has(line.id) }"
          @click="toggle(line.id)"
          ><i :style="{ background: line.color }"></i>{{ label(line.label) }}
          <strong>{{ pct(line.probability) }}</strong></button
        ></div
      >
      <p v-if="feed?.fomcStatus === 'stale' || meeting.status === 'stale'"
        >部分历史暂不可用，保留已采集数据。</p
      >
      <div v-if="times.length" ref="chartHost" class="fomc-chart"
        ><svg
          :viewBox="`0 0 ${chartWidth} ${chartHeight}`"
          role="img"
          :aria-label="`${meeting.meetingDate} FOMC各结果历史概率`"
        >
          <g v-for="value in [0, 25, 50, 75, 100]" :key="value">
            <line
              x1="10"
              :x2="chartWidth - 60"
              :y1="y(value)"
              :y2="y(value)"
              stroke="#e0e4ea"
              stroke-dasharray="2 5"
            />
            <text :x="chartWidth - 49" :y="y(value) + 4">{{ value }}%</text>
          </g>
          <g v-for="line in lines" :key="line.id">
            <polyline
              v-if="!hidden.has(line.id)"
              :points="points(line.history)"
              fill="none"
              :stroke="line.color"
              stroke-width="2"
              vector-effect="non-scaling-stroke"
            />
            <circle
              v-if="!hidden.has(line.id) && line.history.length"
              :cx="x(new Date(line.history[line.history.length - 1].observedAt).getTime())"
              :cy="y(Number(line.history[line.history.length - 1].probability))"
              r="4"
              :fill="line.color"
            />
          </g>
          <text
            v-for="(time, index) in ticks"
            :key="index"
            :x="x(time)"
            :y="chartHeight - 7"
            :text-anchor="index === 0 ? 'start' : index === 4 ? 'end' : 'middle'"
          >
            {{ new Date(time).toISOString().slice(0, 10) }}
          </text>
        </svg></div
      >
      <p v-else>该会议暂无所选范围的历史数据。</p>
      <footer
        >来源：Polymarket · 更新 {{ new Date(meeting.updatedAt).toLocaleString('zh-CN') }}</footer
      >
    </template>
  </div>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
  import {
    getMacroExpectations,
    type MacroExpectationResponse,
    type MacroProbabilityPoint,
  } from '@/api/hedgeResearch';

  const chartHost = ref<HTMLElement | null>(null);
  const chartWidth = ref(1000);
  const chartHeight = ref(320);
  let observer: ResizeObserver | undefined;
  watch(
    chartHost,
    (element) => {
      observer?.disconnect();
      if (!element) return;
      observer = new ResizeObserver((entries: ResizeObserverEntry[]) => {
        const entry = entries[0];
        if (!entry) return;
        chartWidth.value = Math.max(360, entry.contentRect.width);
        chartHeight.value = Math.max(240, entry.contentRect.height);
      });
      observer.observe(element);
    },
    { flush: 'post' },
  );
  onBeforeUnmount(() => observer?.disconnect());
  const loading = ref(true);
  const error = ref('');
  const feed = ref<MacroExpectationResponse | null>(null);
  const selectedId = ref('');
  const selectedYears = ref(5);
  const hidden = ref(new Set<string>());
  const orderedMeetings = computed(() =>
    [...(feed.value?.fomcMeetings ?? [])].sort((a, b) =>
      a.meetingDate.localeCompare(b.meetingDate),
    ),
  );
  const meeting = computed(
    () =>
      orderedMeetings.value.find((m) => m.id === selectedId.value) ??
      orderedMeetings.value.find((m) => !m.closed && new Date(m.expiryAt).getTime() > Date.now()) ??
      orderedMeetings.value[orderedMeetings.value.length - 1],
  );
  function color(label: string) {
    return label === 'No change'
      ? '#82b8ff'
      : label === '25 bps increase'
      ? '#426bff'
      : label.includes('increase')
      ? '#edc500'
      : label === '25 bps decrease'
      ? '#ff8000'
      : '#de4d65';
  }
  function label(value: string) {
    return (
      (
        {
          'No change': '无变化',
          '25 bps increase': '加息25个基点',
          '50+ bps increase': '加息50个基点以上',
          '25 bps decrease': '降息25个基点',
          '50+ bps decrease': '降息50个基点以上',
        } as Record<string, string>
      )[value] ?? value
    );
  }
  const lines = computed(() =>
    (meeting.value?.outcomes ?? [])
      .map((v) => ({
        ...v,
        color: color(v.label),
        history: v.history.filter(
          (p) =>
            !selectedYears.value ||
            new Date(p.observedAt).getTime() >=
              Date.now() - selectedYears.value * 365.25 * 86400000,
        ),
      }))
      .sort((a, b) => b.probability - a.probability),
  );
  const times = computed(() =>
    lines.value
      .flatMap((v) => v.history.map((p) => new Date(p.observedAt).getTime()))
      .filter(Number.isFinite),
  );
  const extent = computed(() =>
    times.value.reduce(
      (result, time) => [Math.min(result[0], time), Math.max(result[1], time)],
      [Infinity, -Infinity],
    ),
  );
  const ticks = computed(() =>
    Array.from(
      { length: 5 },
      (_, i) => extent.value[0] + ((extent.value[1] - extent.value[0]) * i) / 4,
    ),
  );
  function x(time: number) {
    return (
      10 +
      ((time - extent.value[0]) / Math.max(1, extent.value[1] - extent.value[0])) *
        (chartWidth.value - 70)
    );
  }
  function y(value: number) {
    return chartHeight.value - 35 - (value * (chartHeight.value - 57)) / 100;
  }
  function points(history: MacroProbabilityPoint[]) {
    return history
      .map((p) => `${x(new Date(p.observedAt).getTime())},${y(Number(p.probability))}`)
      .join(' ');
  }
  function pct(v: number) {
    return v > 0 && v < 1 ? '<1%' : `${v.toFixed(1)}%`;
  }
  function toggle(id: string) {
    const next = new Set(hidden.value);
    next.has(id) ? next.delete(id) : next.add(id);
    hidden.value = next;
  }
  onMounted(async () => {
    try {
      feed.value = await getMacroExpectations();
    } catch (e) {
      error.value = e instanceof Error ? e.message : '会议数据加载失败';
    } finally {
      loading.value = false;
    }
  });
</script>
<style scoped>
  .fomc-panel {
    padding: 8px 4px;
    color: var(--strategy-text-1, #172233);
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  h3 {
    margin: 0 0 12px;
    font-size: 20px;
  }

  a,
  footer {
    color: #6d7988;
    font-size: 12px;
  }

  nav,
  .outcomes {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    margin: 12px 0;
  }

  button {
    padding: 7px 12px;
    border: 0;
    border-radius: 22px;
    background: #f3f4f6;
    color: inherit;
    cursor: pointer;
  }

  button.active {
    background: #272b32;
    color: white;
  }

  .outcomes button {
    padding: 3px 0;
    background: transparent;
    font-size: 12px;
  }

  .outcomes i {
    display: inline-block;
    width: 8px;
    height: 8px;
    margin-right: 5px;
    border-radius: 50%;
  }

  .muted {
    opacity: 0.35;
  }

  .fomc-chart {
    width: 100%;
    height: 320px;
  }

  svg {
    width: 100%;
    height: 100%;
    overflow: visible;
  }

  svg text {
    fill: #6d7988;
    font-size: 11px;
  }

  footer {
    margin-top: 8px;
  }
</style>
