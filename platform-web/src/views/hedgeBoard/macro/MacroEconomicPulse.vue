<template>
  <div class="economic-pulse">
    <div class="pulse-toolbar">
      <div class="pulse-regions" role="group" aria-label="经济数据地区">
        <button
          v-for="item in regions"
          :key="item.key"
          type="button"
          :aria-pressed="region === item.key"
          :class="{ active: region === item.key }"
          @click="region = item.key"
          >{{ item.label }}</button
        >
      </div>
      <label>截至月份 <input v-model="endMonth" type="month" :max="latestMonth" /></label>
    </div>
    <p v-if="error" class="pulse-empty" role="status">经济数据暂不可用，请稍后刷新。</p>
    <p v-else-if="loading" class="pulse-empty" role="status">正在读取经济历史…</p>
    <div
      v-else
      class="pulse-table-scroll"
      tabindex="0"
      aria-label="各指标最近12个月数据，可横向滚动"
    >
      <table>
        <thead
          ><tr
            ><th>指标 / 单位</th><th>最新观测</th><th>较上期</th>
            <th v-for="month in months" :key="month">{{ month }}</th></tr
          ></thead
        >
        <tbody>
          <tr v-for="row in rows" :key="row.seriesId">
            <th scope="row">
              <a
                v-if="row.sourceUrl"
                :href="row.sourceUrl"
                target="_blank"
                rel="noopener noreferrer"
                >{{ row.label }}</a
              >
              <span v-else>{{ row.label }}</span>
              <small
                >{{ unitText(row.unit) }} · {{ frequencyText(row.frequency)
                }}<span v-if="row.status !== 'ready'">
                  · {{ row.status === 'stale' ? '待更新' : '部分数据待核对' }}</span
                ></small
              >
            </th>
            <td>{{ row.observationDate || '—' }}</td>
            <td>{{ format(periodDelta(row)) }}</td>
            <td
              v-for="month in months"
              :key="month"
              :style="{
                background: pulseColor(
                  values(row).get(month),
                  [...values(row).values()].slice(-36),
                ),
              }"
              :title="`${row.label} · ${month} · ${row.source} · ${unitText(row.unit)}`"
            >
              {{ format(values(row).get(month)) }}
            </td>
          </tr>
          <tr v-if="!rows.length"
            ><td :colspan="months.length + 3">该地区暂无可用经济历史。</td></tr
          >
        </tbody>
      </table>
    </div>
    <p class="pulse-definition"
      >红 / 蓝表示各指标相对自身最近36期偏高 /
      偏低，不代表利好或利空。缺失月份留空；季度值只显示在原始季度观测月。“较上期”为相邻月或季度的数值差。</p
    >
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, shallowRef } from 'vue';
  import { getMacroDashboardV1, type MacroDashboardSeries } from '@/api/hedgeResearch';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import { unitText, frequencyText } from '../charts/sourceSeriesOptions';
  import { periodValues, periodDelta, pulseMonths, pulseColor } from './economicPulse';

  const regions = [
    { key: 'economicPulseUs', label: '美国' },
    { key: 'economicPulseCn', label: '中国' },
    { key: 'economicPulseEurope', label: '欧元区' },
    { key: 'economicPulseJapan', label: '日本' },
  ];
  const region = ref('economicPulseUs');
  const groups = shallowRef<Record<string, MacroDashboardSeries[]>>({});
  const loading = ref(true),
    error = ref(false),
    endMonth = ref('');
  const latestMonth = computed(() => {
    const parts = new Intl.DateTimeFormat('en', {
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: '2-digit',
    }).formatToParts(new Date());
    return `${parts.find((part) => part.type === 'year')!.value}-${
      parts.find((part) => part.type === 'month')!.value
    }`;
  });
  const months = computed(() => pulseMonths(endMonth.value || latestMonth.value));
  const rows = computed(() =>
    (groups.value[region.value] || [])
      .filter((row) => ['monthly', 'quarterly'].includes(row.frequency))
      .map((row) => {
        const observations = row.observations.filter(
          (point) => point.date.slice(0, 7) <= (endMonth.value || latestMonth.value),
        );
        const lastValid = observations.map((point) => point.value !== null).lastIndexOf(true);
        const available = observations.slice(0, lastValid + 1);
        return { ...row, observations: available, observationDate: available.at(-1)?.date || null };
      }),
  );
  const values = periodValues;
  const format = (value: number | null | undefined) =>
    value == null || !Number.isFinite(value)
      ? '—'
      : value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  useDashboardRefresh(async () => {
    try {
      groups.value = (await getMacroDashboardV1()).groups;
      error.value = false;
      if (!endMonth.value) {
        endMonth.value =
          Object.values(groups.value)
            .flat()
            .filter((row) => ['monthly', 'quarterly'].includes(row.frequency))
            .flatMap((row) => row.observations.map((o) => o.date.slice(0, 7)))
            .filter((month) => month <= latestMonth.value)
            .sort()
            .at(-1) || latestMonth.value;
      }
    } catch {
      error.value = true;
    } finally {
      loading.value = false;
    }
  });
</script>

<style scoped>
  .economic-pulse {
    min-width: 0;
    padding: 4px 0;
    color: #183343;
    font-family: inherit;
  }

  .pulse-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    gap: 12px;
  }

  .pulse-regions {
    display: flex;
    gap: 7px;
  }

  .pulse-toolbar button,
  .pulse-toolbar input {
    padding: 5px 10px;
    border: 1px solid #dbe4ea;
    border-radius: 7px;
    background: #fff;
    color: inherit;
    font: inherit;
    font-size: 12px;
  }

  .pulse-toolbar button {
    cursor: pointer;
  }

  .pulse-toolbar button.active {
    border-color: #b4c9ff;
    background: #edf3ff;
    color: #165dff;
  }

  .pulse-toolbar label {
    font-size: 12px;
  }

  .pulse-table-scroll {
    max-height: 650px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-spacing: 0;
    border-collapse: separate;
    font-size: 12px;
    white-space: nowrap;
  }

  th,
  td {
    padding: 9px 10px;
    border-bottom: 1px solid #e8eef4;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }

  thead th {
    position: sticky;
    z-index: 2;
    top: 0;
    background: #f3f7fb;
    font-weight: 600;
  }

  th:first-child {
    position: sticky;
    z-index: 1;
    left: 0;
    min-width: 210px;
    max-width: 320px;
    background: #f8fafc;
    text-align: left;
    white-space: normal;
  }

  thead th:first-child {
    z-index: 3;
  }

  tbody th {
    font-weight: 500;
  }

  th a {
    color: inherit;
    text-decoration: none;
  }

  th a:hover {
    color: #165dff;
    text-decoration: underline;
  }

  small {
    display: block;
    margin-top: 3px;
    color: #718399;
    font-size: 10px;
    font-weight: 400;
  }

  .pulse-definition {
    margin: 10px 0 0;
    color: #718399;
    font-size: 11px;
    line-height: 1.7;
  }

  .pulse-empty {
    padding: 30px 12px;
    color: #718399;
    font-size: 12px;
  }
</style>
