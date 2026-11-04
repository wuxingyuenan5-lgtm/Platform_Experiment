<template
  ><div
    ><p v-if="loading">正在读取数据…</p><p v-if="error" role="alert">{{ error }}</p
    ><FinancingChart
      embedded
      v-if="rows.length && card.display !== 'table'"
      :title="card.title"
      :rows="rows"
      :lines="lines"
    /><div v-else-if="rows.length" class="series-table"
      ><table
        ><thead
          ><tr
            ><th>日期</th
            ><th v-for="line in lines" :key="line.key">{{ line.name }}（{{ line.unit }}）</th></tr
          ></thead
        ><tbody
          ><tr v-for="row in tableRows" :key="row.date"
            ><td>{{ row.date }}</td
            ><td v-for="line in lines" :key="line.key">{{
              formatCell(row[line.key as 'a' | 'b'])
            }}</td></tr
          ></tbody
        ></table
      ></div
    ><p v-else-if="!loading && !error">所选范围暂无有效数据</p
    ><nav v-if="card.display === 'table' && rows.length" class="pagination" aria-label="数据表分页"
      ><button :disabled="tablePage === 0" @click="tablePage--">上一页</button
      ><span>{{ tablePage + 1 }} / {{ Math.ceil(rows.length / 100) }} 页 · {{ rows.length }}条</span
      ><button :disabled="(tablePage + 1) * 100 >= rows.length" @click="tablePage++"
        >下一页</button
      ></nav
    >
    <footer
      ><span v-for="s in sources" :key="s.id"
        >{{ s.name }} · {{ s.frequency }} · {{ s.asOf || '暂无日期' }}
        <a v-if="s.sourceUrl" :href="s.sourceUrl" target="_blank" rel="noopener noreferrer"
          >来源 ↗</a
        ></span
      ></footer
    ></div
  ></template
>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue';
  import { loadChartSeries, type SeriesData, type WorkspaceCard } from '@/api/workspace';
  import FinancingChart from '@/views/hedgeBoard/aShare/components/FinancingChart.vue';

  const props = defineProps<{ card: WorkspaceCard }>();
  const sources = ref<SeriesData[]>([]),
    loading = ref(false),
    error = ref('');
  let controller: AbortController | undefined;
  watch(
    () => [props.card.seriesA, props.card.seriesB],
    async () => {
      controller?.abort();
      const active = new AbortController();
      controller = active;
      loading.value = true;
      error.value = '';
      sources.value = [];
      try {
        const r = await Promise.all(
          [props.card.seriesA, props.card.seriesB]
            .filter(Boolean)
            .map((id) => loadChartSeries(id, active.signal)),
        );
        if (!active.signal.aborted) sources.value = r;
      } catch (e) {
        if (!active.signal.aborted) error.value = String(e);
      } finally {
        if (!active.signal.aborted) loading.value = false;
      }
    },
    { immediate: true },
  );
  const formatCell = (v: unknown) =>
    v == null ? '—' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 6 });
  const numeric = (v: unknown) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  const rows = computed(() => {
    const map = new Map<string, { date: string; a: number | null; b: number | null }>();
    sources.value.forEach((s, i) => {
      let base: number | null = null,
        previous: number | null = null;
      for (const p of [...s.observations].sort((a, b) => a.date.localeCompare(b.date))) {
        let value = numeric(p.value);
        if (
          (props.card.start && p.date < props.card.start) ||
          (props.card.end && p.date > props.card.end)
        )
          continue;
        if (base == null && value != null && value !== 0) base = value;
        const original = value;
        if (props.card.transform === 'index')
          value = base == null || value == null ? null : (value / base) * 100;
        else if (props.card.transform === 'return')
          value =
            previous == null || previous === 0 || value == null
              ? null
              : (value / previous - 1) * 100;
        previous = original;
        const row = map.get(p.date) || { date: p.date, a: null, b: null };
        row[i === 0 ? 'a' : 'b'] = value;
        map.set(p.date, row);
      }
    });
    return [...map.values()].sort((a, b) => a.date.localeCompare(b.date));
  });
  const tablePage = ref(0);
  const tableRows = computed(() =>
    [...rows.value].reverse().slice(tablePage.value * 100, (tablePage.value + 1) * 100),
  );
  watch(rows, () => {
    tablePage.value = 0;
  });
  const lines = computed(() =>
    sources.value.map((s, i) => ({
      key: i === 0 ? 'a' : 'b',
      name: s.name,
      color: i === 0 ? '#2864ec' : '#171717',
      unit:
        props.card.transform === 'index'
          ? '基期=100'
          : props.card.transform === 'return'
          ? '%'
          : s.unit,
      right: props.card.transform === 'level' && i === 1,
    })),
  );
  onBeforeUnmount(() => controller?.abort());</script
><style scoped>
  .pagination {
    display: flex;
    gap: 12px;
    align-items: center;
    margin: 10px 0;
    font-size: 12px;
  }

  .series-table {
    max-height: 420px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
  }

  th,
  td {
    padding: 9px 12px;
    border-bottom: 1px solid #e4ebf3;
    text-align: right;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  thead {
    position: sticky;
    top: 0;
    background: #f4f8fc;
  }

  footer {
    display: grid;
    padding: 8px;
    color: #708397;
    font-size: 11px;
    gap: 5px;
  }

  a {
    color: #2864ec;
  }
</style>
