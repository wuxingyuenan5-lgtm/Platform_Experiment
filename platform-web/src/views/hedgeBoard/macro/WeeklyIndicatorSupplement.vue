<template>
  <section class="weekly-supplement" aria-label="周报补充指标" :data-batch="batchId">
    <header class="weekly-supplement__heading">
      <div><span class="weekly-supplement__eyebrow">2026.11.04</span><h2>周报补充指标</h2></div>
      <div class="weekly-supplement__actions">
        <span v-if="items.length">{{ items.length }} 项 · {{ available }} 项有数据</span>
        <button :disabled="loading" @click="load">{{ loading ? '读取中…' : '刷新' }}</button>
      </div>
    </header>
    <p v-if="error" class="weekly-supplement__error" role="alert">{{ error }}</p>
    <p v-if="loading && !items.length" role="status">正在读取补充指标…</p>
    <template v-if="items.length">
      <div class="weekly-supplement__filters">
        <label
          >分类
          <select v-model="group"
            ><option value="">全部</option
            ><option v-for="name in groups" :key="name" :value="name">{{ name }}</option></select
          ></label
        >
        <label>查找指标 <input v-model="search" type="search" placeholder="指标名称" /></label>
      </div>
      <div class="weekly-supplement__table">
        <table>
          <thead
            ><tr><th>指标</th><th>最近观测</th><th>观察日期</th><th>状态</th></tr></thead
          >
          <tbody>
            <tr v-for="item in filtered" :key="item.id" :class="{ selected: selected === item.id }">
              <td
                ><button :aria-pressed="selected === item.id" @click="select(item.id)">{{
                  item.label
                }}</button
                ><small>{{ item.group }}</small></td
              >
              <td
                >{{ format(item.series.latestValue) }}<small>{{ item.unit }}</small></td
              >
              <td>{{ item.series.observationDate || '—' }}</td>
              <td
                ><span
                  class="weekly-supplement__status"
                  :class="{ muted: item.series.status !== 'ready' }"
                  >{{ status(item.series.status) }}</span
                ></td
              >
            </tr>
            <tr v-if="!filtered.length"><td colspan="4">没有匹配的指标</td></tr>
          </tbody>
        </table>
      </div>
      <article
        v-if="selectedItem"
        class="weekly-supplement__detail"
        :aria-label="selectedItem.label + '详情'"
      >
        <header
          ><h3>{{ selectedItem.label }}</h3
          ><div v-if="detail?.series.observations.length"
            ><button :aria-pressed="!tableView" @click="tableView = false">图表</button
            ><button :aria-pressed="tableView" @click="tableView = true">数据</button></div
          ></header
        >
        <p v-if="selectedItem.definition">{{ selectedItem.definition }}</p>
        <p v-if="detailLoading" role="status">正在读取历史…</p>
        <p v-else-if="detailError" role="alert">{{ detailError }}</p>
        <template v-else-if="detail?.series.observations.length">
          <SourceSeriesPlot
            v-if="!tableView"
            :key="detail.id"
            :series="[detail.series]"
            :colors="['#2563a6']"
            :state-key="batchId + ':' + detail.id"
          />
          <div v-else class="weekly-supplement__history"
            ><table
              ><thead
                ><tr
                  ><th>观察日期</th><th>{{ detail.unit }}</th></tr
                ></thead
              ><tbody
                ><tr v-for="row in history" :key="row.date"
                  ><td>{{ row.date }}</td
                  ><td>{{ format(row.value) }}</td></tr
                ></tbody
              ></table
            ></div
          >
          <p class="weekly-supplement__source"
            >数据来源：<a
              v-if="detail.series.sourceUrl"
              :href="detail.series.sourceUrl"
              target="_blank"
              rel="noopener noreferrer"
              >{{ detail.series.source }}</a
            ><span v-else>{{ detail.series.source }}</span></p
          >
        </template>
        <p v-else class="weekly-supplement__empty">暂无可核验的历史数据</p>
        <p class="weekly-supplement__reference"
          >指标参考：{{ selectedItem.reportTitle }} · {{ selectedItem.reportDate }} · 第
          {{ selectedItem.page }} 页</p
        >
      </article>
    </template>
  </section>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue';
  import { getWeeklySupplement, type WeeklyIndicator } from '@/api/platform/weeklyIndicators';
  import SourceSeriesPlot from '../charts/SourceSeriesPlot.vue';
  import { weeklyDetailGroup } from './detailGroups';
  import { useResearchViewState } from '../composables/researchWorkspace';

  const props = defineProps<{ section: string; detailGroup?: string }>();
  const batchId = 'weekly-reports-20261104';
  const items = shallowRef<WeeklyIndicator[]>([]);
  const detail = shallowRef<WeeklyIndicator | null>(null);
  const loading = ref(false);
  const detailLoading = ref(false);
  const error = ref('');
  const detailError = ref('');
  const group = useResearchViewState('weekly-group', '');
  const search = useResearchViewState('weekly-search', '');
  const selected = useResearchViewState('weekly-selected', '');
  const tableView = useResearchViewState('weekly-table', false);
  let overviewController: AbortController | undefined;
  let detailController: AbortController | undefined;
  const groups = computed(() => [...new Set(items.value.map((item) => item.group))]);
  const available = computed(
    () => items.value.filter((item) => item.series.latestValue != null).length,
  );
  const filtered = computed(() =>
    items.value.filter(
      (item) =>
        (!group.value || item.group === group.value) &&
        item.label.toLowerCase().includes(search.value.trim().toLowerCase()),
    ),
  );
  const selectedItem = computed(() => items.value.find((item) => item.id === selected.value));
  const history = computed(() => [...(detail.value?.series.observations || [])].reverse());
  const format = (value: string | number | null | undefined) =>
    value == null || !Number.isFinite(Number(value))
      ? '—'
      : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 4 });
  const status = (value: string) =>
    ({
      ready: '有数据',
      stale: '历史数据',
      degraded: '更新异常',
      error: '暂不可用',
      no_data: '暂无数据',
    }[value] || '待复核');

  async function select(id: string) {
    detailController?.abort();
    const controller = new AbortController();
    detailController = controller;
    selected.value = id;
    detail.value = null;
    detailError.value = '';
    detailLoading.value = true;
    try {
      const data = await getWeeklySupplement(props.section, controller.signal, id);
      if (!controller.signal.aborted)
        detail.value = data.items.find((item) => item.id === id) || null;
    } catch {
      if (!controller.signal.aborted) detailError.value = '历史数据读取失败，请重新选择指标。';
    } finally {
      if (!controller.signal.aborted) detailLoading.value = false;
    }
  }
  async function load() {
    overviewController?.abort();
    const controller = new AbortController();
    overviewController = controller;
    loading.value = true;
    error.value = '';
    try {
      const data = await getWeeklySupplement(props.section, controller.signal);
      if (controller.signal.aborted) return;
      items.value = data.items.filter(
        (item) =>
          !props.detailGroup || weeklyDetailGroup(props.section, item.id) === props.detailGroup,
      );
      const id = items.value.some((item) => item.id === selected.value)
        ? selected.value
        : (items.value.find((item) => item.series.latestValue != null) || items.value[0])?.id;
      if (id) await select(id);
    } catch {
      if (!controller.signal.aborted) error.value = '补充指标读取失败，请重试。';
    } finally {
      if (!controller.signal.aborted) loading.value = false;
    }
  }
  onMounted(load);
  onBeforeUnmount(() => {
    overviewController?.abort();
    detailController?.abort();
  });
</script>

<style scoped lang="less">
  .weekly-supplement {
    min-width: 0;
    margin-top: 32px;
    padding: 22px;
    border: 1px solid #d8e1ec;
    border-top: 3px solid #7d94b0;
    border-radius: 12px;
    background: #fff;
    color: #24364b;

    @media (max-width: 600px) {
      padding: 14px;

      &__filters input {
        max-width: 180px;
      }
    }

    &__heading,
    &__actions,
    &__filters,
    &__detail > header {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
    }

    &__eyebrow {
      color: #708198;
      font-size: 11px;
      letter-spacing: 1px;
    }

    h2 {
      margin: 4px 0 0;
      font-size: 19px;
      font-weight: 650;
    }

    h3 {
      margin: 0;
      font-size: 16px;
    }

    button,
    select,
    input {
      padding: 6px 10px;
      border: 1px solid #d5dfe9;
      border-radius: 6px;
      background: #fff;
      color: inherit;
    }

    button {
      cursor: pointer;
    }

    button:focus-visible,
    select:focus-visible,
    input:focus-visible {
      outline: 2px solid #2563a6;
      outline-offset: 2px;
    }

    button[aria-pressed='true'] {
      background: #edf4fb;
      color: #1f5d99;
    }

    button:disabled {
      opacity: 0.6;
      cursor: wait;
    }

    &__actions {
      color: #64748b;
      font-size: 12px;
    }

    &__filters {
      justify-content: flex-start;
      margin: 20px 0 12px;
      font-size: 12px;
    }

    &__filters label {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    &__table {
      max-height: 470px;
      overflow: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }

    th {
      position: sticky;
      top: 0;
      background: #f0f4f8;
      color: #52687e;
      text-align: left;
    }

    th,
    td {
      padding: 10px 12px;
      border-bottom: 1px solid #e8eef4;
      white-space: nowrap;
    }

    td:first-child {
      min-width: 230px;
      white-space: normal;
    }

    td button {
      padding: 0;
      border: 0;
      background: transparent;
      text-align: left;
    }

    small {
      display: block;
      margin-top: 3px;
      color: #738397;
      font-size: 11px;
    }

    tr.selected {
      background: #f2f7fd;
    }

    &__status {
      color: #317459;
      font-size: 12px;
    }

    &__status.muted {
      color: #7b6d54;
    }

    &__detail {
      margin-top: 20px;
      padding-top: 20px;
      border-top: 1px solid #dbe4ed;
    }

    &__detail p {
      margin: 10px 0;
      color: #64748b;
      font-size: 12px;
      line-height: 1.7;
    }

    &__history {
      max-height: 360px;
      overflow: auto;
    }

    &__detail &__empty {
      padding: 35px 12px;
      background: #f8fafc;
      text-align: center;
    }

    &__error {
      color: #9b493f;
      font-size: 13px;
    }

    a {
      color: #24629a;
    }
  }
</style>
