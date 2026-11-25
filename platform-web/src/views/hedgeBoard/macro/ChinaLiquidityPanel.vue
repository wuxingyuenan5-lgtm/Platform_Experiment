<template>
  <section aria-label="中国资金价格与货币信用">
    <p v-if="loading" role="status">正在读取中国流动性数据…</p>
    <p v-else-if="error" role="alert"
      >{{ error }} <button type="button" @click="load">重试</button></p
    >
    <template v-if="data">
      <FinancingChart
        title="资金价格 · DR007与7天逆回购利率"
        :rows="macroRows(['cn_dr007', 'cn_omo_7d'])"
        :lines="rateLines"
        allow-table
        note="银行间资金价格与政策利率按各自实际日期展示，缺失日期不填补。"
      />
      <p class="source">{{ macroSource(['cn_dr007', 'cn_omo_7d']) }}</p>
      <FinancingChart
        title="货币与信用 · 同比增速"
        :rows="macroRows(['cn_m2_yoy', 'cn_tsf_stock_yoy', 'cn_m1_yoy'], true)"
        :lines="moneyLines"
        allow-table
        note="M1自2025年起存在统计口径调整；月度日期为所属月份，不是公告日。"
      />
      <p class="source">{{ macroSource(['cn_m2_yoy', 'cn_tsf_stock_yoy', 'cn_m1_yoy']) }}</p>
      <FinancingChart
        title="M2与社融存量增速差"
        :rows="data.moneyCreditGap"
        :lines="[line('value', 'M2同比−社融存量同比', '百分点', '#2563eb', true)]"
        allow-table
        note="同月M2同比减社融存量同比，社融包含政府债券。"
      />
    </template>
  </section>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, onMounted, ref, shallowRef } from 'vue';
  import {
    getAShareCapital,
    type CapitalDashboard,
    type CapitalRow,
  } from '@/api/platform/aShareCapital';
  import FinancingChart, { type FinanceLine } from '../aShare/components/FinancingChart.vue';

  const data = shallowRef<CapitalDashboard>();
  const loading = ref(false);
  const error = ref('');
  let controller: AbortController | undefined;
  async function load() {
    controller?.abort();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    try {
      const result = await getAShareCapital(current.signal);
      if (!current.signal.aborted) data.value = result;
    } catch {
      if (!current.signal.aborted) error.value = '中国流动性数据读取失败';
    } finally {
      if (!current.signal.aborted) loading.value = false;
    }
  }
  onMounted(load);
  onBeforeUnmount(() => controller?.abort());

  const line = (
    key: string,
    name: string,
    unit: string,
    color: string,
    bar = false,
    right = false,
  ): FinanceLine => ({ key, name, unit, color, bar, right });
  const rateLines = [
    line('cn_dr007', 'DR007', '%', '#2563eb'),
    line('cn_omo_7d', '7天逆回购利率', '%', '#d49b26'),
  ];
  const moneyLines = [
    line('cn_m2_yoy', 'M2同比', '%', '#2563eb'),
    line('cn_tsf_stock_yoy', '社融存量同比', '%', '#d49b26'),
    line('cn_m1_yoy', 'M1同比', '%', '#0e9f78'),
  ];
  function macroRows(ids: string[], monthly = false) {
    const rows = new Map<string, CapitalRow>();
    for (const id of ids)
      for (const r of data.value?.macro[id]?.observations || []) {
        const date = monthly ? r.date.slice(0, 7) + '-01' : r.date;
        if (!rows.has(date)) rows.set(date, { date });
        rows.get(date)![id] = r.value;
      }
    return [...rows.values()].sort((a, b) => a.date.localeCompare(b.date));
  }
  function macroSource(ids: string[]) {
    return ids
      .map((id) => {
        const s = data.value?.macro[id];
        return s?.source
          ? `${s.label}：${s.source} · ${s.observationDate || '—'}${
              s.isStale || s.status !== 'ready' ? ' · 待更新' : ''
            }`
          : '暂无数据';
      })
      .join('；');
  }
</script>

<style scoped>
  .source {
    color: var(--strategy-text-3);
    font-size: 12px;
  }
</style>
