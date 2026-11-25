<template>
  <ChartExpand :title="title">
    <section class="capital-events" :aria-label="title">
      <header class="events-heading">
        <h3>{{ title }}</h3>
        <nav v-if="sourceKeys.length > 1" class="source-tabs" :aria-label="title + '分类'">
          <button
            v-for="key in sourceKeys"
            :key="key"
            type="button"
            :aria-pressed="tableKey === key"
            @click="tableKey = key"
            >{{ sources[key].label }}</button
          >
        </nav>
        <div class="table-controls">
          <label
            >搜索
            <input v-model="query" :aria-label="title + '搜索'" placeholder="代码、名称或股东"
          /></label>
          <label v-if="effectiveKey === 'holders'"
            >方向
            <select v-model="direction" :aria-label="title + '方向'"
              ><option value="">全部</option
              ><option>增持</option
              ><option>减持</option></select
            ></label
          >
          <label v-if="effectiveKey === 'unlocks'"
            >窗口
            <select v-model="unlockRange" aria-label="解禁窗口"
              ><option :value="30">未来30天</option
              ><option :value="90">未来90天</option
              ><option :value="0">已采集全部</option></select
            ></label
          >
          <span>{{ filteredRows.length }} 条</span>
        </div>
      </header>
      <p class="definition">{{ tableNote }}</p>
      <div class="source"
        ><a :href="tableSource.sourceUrl" target="_blank" rel="noopener noreferrer"
          >{{ tableSource.provider }} ↗</a
        >
        · {{ sourceState(tableSource) }} · {{ tableSource.observationDate || '—'
        }}<span v-if="tableSource.fetchedAt"> · 采集 {{ stamp(tableSource.fetchedAt) }}</span></div
      >
      <div class="table-scroll" tabindex="0" :aria-label="title + '数据表'"
        ><table
          ><thead
            ><tr
              ><th
                v-for="column in columns"
                :key="column.key"
                scope="col"
                :class="{ number: column.numeric }"
                >{{ column.label }}</th
              ></tr
            ></thead
          >
          <tbody
            ><tr v-for="(row, i) in pageRows" :key="`${effectiveKey}-${page}-${i}`"
              ><td
                v-for="column in columns"
                :key="column.key"
                :class="{ number: column.numeric }"
                >{{ cell(row, column) }}</td
              ></tr
            ></tbody
          >
        </table></div
      >
      <p v-if="!filteredRows.length" class="empty">{{
        tableSource.rows.length ? '没有匹配的记录' : '暂无可用数据'
      }}</p>
      <div v-if="filteredRows.length" class="pagination"
        ><button :disabled="page <= 1" @click="page--">上一页</button
        ><span>每页25条 · {{ page }} / {{ pageCount }}</span
        ><button :disabled="page >= pageCount" @click="page++">下一页</button></div
      >
    </section>
  </ChartExpand>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import type { CapitalRow, CapitalSource } from '@/api/platform/aShareCapital';
  import ChartExpand from '../../components/ChartExpand.vue';

  const props = defineProps<{
    title: string;
    sources: Record<string, CapitalSource>;
    sourceKeys: string[];
    asOf: string;
  }>();
  const tableKey = ref(props.sourceKeys[0]);
  const effectiveKey = computed(() => tableKey.value);
  const tableSource = computed(() => props.sources[effectiveKey.value]);
  const query = ref(''),
    direction = ref(''),
    unlockRange = ref(30),
    page = ref(1);
  const fmt = (value: unknown) =>
    value == null || value === '' || !Number.isFinite(Number(value))
      ? '—'
      : Number(value).toLocaleString('zh-CN', {
          maximumFractionDigits: Math.abs(Number(value)) < 0.01 ? 6 : 2,
        });
  const stamp = (value: string) =>
    new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false });
  const sourceState = (s: CapitalSource) =>
    s.status === 'error'
      ? s.rows.length
        ? '更新失败 · 保留历史'
        : '暂不可用'
      : s.isStale
      ? '待更新'
      : s.status === 'ready'
      ? '已采集'
      : '暂无数据';
  const tableNote = computed(
    () =>
      ({
        funds:
          '公开列表前300条中的境内发行股票、混合基金样本；可含港股配置。募集份额单位为亿份，来源可能在A/C份额重复披露产品规模，逐行展示、不汇总为入市金额。',
        buybacks:
          '最近一年更新的回购方案。已回购金额是该方案截至披露日的累计值；预案金额与实际实施分列，不能按更新日加总为每日回购资金。',
        holders:
          '近90天公告的股东持股变化。万股为数量；区间可能重叠，含非二级市场方式，不等同当天净流入。',
        unlocks:
          '公开解禁安排；参考市值为源站价格口径。已采集窗口：' +
          (tableSource.value.windowStart || '—') +
          ' 至 ' +
          (tableSource.value.windowEnd || '—') +
          '。',
      }[effectiveKey.value]),
  );
  interface Column {
    key: string;
    label: string;
    numeric?: boolean;
  }
  const columns = computed<Column[]>(() => {
    const base = [
      {
        key: 'date',
        label:
          effectiveKey.value === 'funds'
            ? '成立日'
            : effectiveKey.value === 'unlocks'
            ? '解禁日'
            : '公告更新日',
      },
      { key: 'code', label: '代码' },
      { key: 'name', label: '名称' },
    ];
    const extra: Record<string, Column[]> = {
      funds: [
        { key: 'kind', label: '类型' },
        { key: 'shares', label: '募集份额（亿份）', numeric: true },
        { key: 'manager', label: '管理人' },
      ],
      buybacks: [
        { key: 'progress', label: '进度' },
        { key: 'planDate', label: '方案公告日' },
        { key: 'lower', label: '计划下限（亿元）', numeric: true },
        { key: 'upper', label: '计划上限（亿元）', numeric: true },
        { key: 'amount', label: '累计已回购（亿元）', numeric: true },
        { key: 'asOf', label: '回购统计日' },
      ],
      holders: [
        { key: 'holder', label: '股东' },
        { key: 'direction', label: '方向' },
        { key: 'shares', label: '变动数量（万股）', numeric: true },
        { key: 'start', label: '区间起日' },
        { key: 'end', label: '区间止日' },
        { key: 'market', label: '方式' },
      ],
      unlocks: [
        { key: 'kind', label: '股份类型' },
        { key: 'shares', label: '解禁数量（万股）', numeric: true },
        { key: 'amount', label: '参考市值（亿元）', numeric: true },
        { key: 'ratio', label: '占总股本（%）', numeric: true },
      ],
    };
    return [...base, ...extra[effectiveKey.value]];
  });
  const progress: Record<string, string> = {
    '001': '董事会预案',
    '002': '股东大会通过',
    '003': '股东大会否决',
    '004': '实施中',
    '005': '停止实施',
    '006': '完成实施',
    '007': '提议',
  };
  const cell = (row: CapitalRow, c: Column) =>
    c.numeric
      ? fmt(row[c.key])
      : c.key === 'progress'
      ? progress[String(row.progress)] || '其他'
      : row[c.key] || '—';
  const filteredRows = computed(() => {
    const q = query.value.trim().toLowerCase();
    const end = Date.parse(props.asOf) + unlockRange.value * 86400000;
    return tableSource.value.rows
      .filter((r) => {
        if (
          q &&
          ![r.code, r.name, r.holder].some((v) =>
            String(v || '')
              .toLowerCase()
              .includes(q),
          )
        )
          return false;
        if (effectiveKey.value === 'holders' && direction.value && r.direction !== direction.value)
          return false;
        if (
          effectiveKey.value === 'unlocks' &&
          unlockRange.value &&
          (r.date < props.asOf || Date.parse(r.date) >= end)
        )
          return false;
        return true;
      })
      .sort((a, b) =>
        effectiveKey.value === 'unlocks'
          ? a.date.localeCompare(b.date)
          : b.date.localeCompare(a.date),
      );
  });
  const pageCount = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / 25)));
  const pageRows = computed(() => filteredRows.value.slice((page.value - 1) * 25, page.value * 25));
  watch([effectiveKey, query, direction, unlockRange, () => props.sources], () => {
    page.value = 1;
  });
</script>
<style scoped>
  .capital-events {
    min-width: 0;
    margin-top: 16px;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card, 14px);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
  }

  .events-heading,
  .source-tabs,
  .table-controls,
  .pagination {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }

  .events-heading {
    justify-content: space-between;
    min-height: 30px;
    padding-right: 42px;
  }

  h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 15px;
    font-weight: 600;
  }

  .definition,
  .source {
    margin: 10px 0;
    color: var(--strategy-text-3);
    font-size: 12px;
    line-height: 1.7;
  }

  .source {
    overflow-wrap: anywhere;
  }

  a {
    color: var(--strategy-accent);
  }

  button,
  input,
  select {
    box-sizing: border-box;
    min-height: 32px;
    padding: 5px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-control, 8px);
    background: var(--strategy-surface);
    color: inherit;
    font: inherit;
  }

  button {
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: var(--strategy-accent);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent);
  }

  button:disabled {
    opacity: 0.45;
    cursor: default;
  }

  button:focus-visible,
  input:focus-visible,
  select:focus-visible,
  .table-scroll:focus-visible {
    outline: 2px solid var(--strategy-accent);
    outline-offset: 2px;
  }

  .source-tabs {
    gap: 6px;
    font-size: 12px;
  }

  .table-controls {
    margin: 14px 0 10px;
    font-size: 12px;
  }

  label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  .table-controls > span {
    margin-left: auto;
    color: var(--strategy-text-3);
  }

  .table-scroll {
    max-height: 620px;
    overflow: auto;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
  }

  table {
    width: 100%;
    min-width: 800px;
    border-spacing: 0;
    border-collapse: separate;
    font-size: 12px;
    text-align: left;
  }

  th,
  td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--strategy-border);
    white-space: nowrap;
  }

  th {
    position: sticky;
    z-index: 1;
    top: 0;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-3);
    font-weight: 500;
  }

  tbody tr:last-child td {
    border-bottom: 0;
  }

  tbody tr:hover td {
    background: var(--strategy-surface-2);
  }

  .number {
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  .pagination {
    justify-content: flex-end;
    margin-top: 12px;
    font-size: 12px;
  }

  .empty {
    margin: 0;
    padding: 24px;
    color: var(--strategy-text-3);
    text-align: center;
  }

  @media (max-width: 600px) {
    .capital-events {
      padding: 12px;
    }

    .events-heading {
      align-items: flex-start;
    }

    .table-controls input {
      width: 160px;
      max-width: 100%;
    }

    .pagination {
      justify-content: center;
    }
  }
</style>
