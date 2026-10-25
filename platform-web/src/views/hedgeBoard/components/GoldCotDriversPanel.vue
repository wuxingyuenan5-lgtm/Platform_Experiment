<template>
  <div class="gold-research">
    <p v-if="error" class="gold-warning">{{ error }}</p>
    <div v-show="history.length">
      <div class="gold-controls">
        <button :class="{ active: view === 'history' }" @click="view = 'history'"
          >持仓占比与金价</button
        >
        <button :class="{ active: view === 'changes' }" @click="view = 'changes'"
          >持仓区间变动</button
        >
        <label
          >开始
          <select v-model="start"
            ><option v-for="r in history" :key="r.date" :value="r.date" :disabled="r.date >= end">{{
              r.date
            }}</option></select
          ></label
        >
        <label
          >结束
          <select v-model="end"
            ><option
              v-for="r in history"
              :key="r.date"
              :value="r.date"
              :disabled="r.date <= start"
              >{{ r.date }}</option
            ></select
          ></label
        >
        <button @click="weekly">最近一周</button>
        <button @click="table = !table">{{ table ? '查看图表' : '查看数据' }}</button>
      </div>
      <p class="gold-meta"
        >CFTC · COMEX 黄金期货 · 报告日 {{ history.at(-1)?.date
        }}{{ data?.status === 'stale' ? ' · 数据待更新' : '' }}</p
      >
      <div
        v-show="!table"
        ref="chartRef"
        :class="['cot-chart', { 'cot-chart--history': view === 'history' }]"
        role="img"
        aria-label="黄金持仓分析，可悬停查看明细并拖动时间轴缩放"
      ></div>
      <div v-if="table" class="gold-table"
        ><table>
          <template v-if="view === 'changes'"
            ><thead
              ><tr><th>分类</th><th>多头变动 · 手</th><th>空头变动 · 手</th></tr></thead
            ><tbody
              ><tr v-for="r in changes" :key="r.label"
                ><td>{{ r.label }}</td
                ><td>{{ formatCount(r.long) }}</td
                ><td>{{ formatCount(r.short) }}</td></tr
              ></tbody
            ></template
          >
          <template v-else
            ><thead
              ><tr
                ><th>报告日</th><th>总未平仓量</th><th>资产管理多头（含套利）/ OI</th
                ><th>资产管理空头（含套利）/ OI</th></tr
              ></thead
            ><tbody
              ><tr v-for="r in selected" :key="r.date"
                ><td>{{ r.date }}</td
                ><td>{{ formatCount(r.openInterest) }}</td
                ><td>{{ share(r, 'long') }}</td
                ><td>{{ share(r, 'short') }}</td></tr
              ></tbody
            ></template
          >
        </table></div
      >
      <p class="gold-meta"
        >套利持仓分别计入多头与空头；区间变动为结束日减开始日。报告通常于周五发布截至周二的持仓。</p
      >
      <p class="gold-meta"
        >黄金现货：{{ price?.source || '暂无行情' }} · {{ price?.observations[0]?.date || '—' }} 至
        {{ price?.observationDate || '—' }}{{ price?.isStale ? ' · 行情待更新' : '' }}</p
      >
    </div>
    <p v-if="!history.length && !error">正在读取黄金持仓…</p>
    <GoldReferenceSnapshots group="cot" />
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, shallowRef, watch, nextTick, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import { getCommodityDashboardV1, type MacroDashboardSeries } from '@/api/hedgeResearch';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import GoldReferenceSnapshots from './GoldReferenceSnapshots.vue';
  import { useResearchViewState } from '../composables/researchWorkspace';
  import { goldRequest, formatCount, type GoldPositions, type PositionRow } from './goldResearch';
  import { cotChanges, cotChangeOptions, cotHistoryOptions } from '../charts/goldCotOptions';

  const data = shallowRef<GoldPositions>();
  const price = shallowRef<MacroDashboardSeries>();
  const error = ref('');
  const view = useResearchViewState<'history' | 'changes'>('gold-cot-view', 'history');
  const start = useResearchViewState('gold-cot-start', '');
  const end = useResearchViewState('gold-cot-end', '');
  const table = ref(false);
  const history = computed(() => data.value?.scopes?.futures?.history || []);
  const selected = computed(() =>
    history.value.filter((r) => r.date >= start.value && r.date <= end.value),
  );
  const changes = computed(() =>
    selected.value.length >= 2 ? cotChanges(selected.value[0], selected.value.at(-1)!) : [],
  );
  const share = (r: PositionRow, key: 'long' | 'short') =>
    r.categories.managed.spreading == null
      ? '—'
      : `${formatCount(
          ((r.categories.managed[key] + r.categories.managed.spreading) / r.openInterest) * 100,
        )}%`;
  function weekly() {
    start.value = history.value.at(-2)?.date || '';
    end.value = history.value.at(-1)?.date || '';
    view.value = 'changes';
  }
  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>, 'light');
  watch([selected, price, view, table, chartRef], async () => {
    await nextTick();
    if (selected.value.length < 2 || table.value) return;
    chart.setOptions(
      view.value === 'changes'
        ? cotChangeOptions(selected.value[0], selected.value.at(-1)!)
        : cotHistoryOptions(history.value, price.value?.observations || [], start.value, end.value),
      true,
    );
    chart.getInstance()?.resize();
  });
  useDashboardRefresh(async () => {
    const results = await Promise.allSettled([
      goldRequest<GoldPositions>('gold-positioning'),
      getCommodityDashboardV1(),
    ]);
    if (results[0].status === 'fulfilled') {
      data.value = results[0].value;
      if (!history.value.some((r) => r.date === end.value))
        end.value = history.value.at(-1)?.date || '';
      if (!history.value.some((r) => r.date === start.value))
        start.value = history.value.at(-157)?.date || history.value[0]?.date || '';
    }
    if (results[1].status === 'fulfilled')
      price.value = results[1].value.groups.goldDrivers?.find(
        (s) => s.seriesId === 'xauusd_daily_close',
      );
    error.value = results.some((r) => r.status === 'rejected')
      ? '部分数据暂不可用，已保留上次有效数据。'
      : '';
  });
</script>
<style scoped src="./goldResearch.css"></style>
<style scoped>
  .cot-chart {
    width: 100%;
    height: 420px;
  }

  .cot-chart--history {
    height: 560px;
  }
</style>
