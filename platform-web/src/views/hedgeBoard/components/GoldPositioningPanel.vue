<template>
  <div class="gold-research">
    <div class="gold-controls">
      <label
        >持仓口径
        <select v-model="scope"
          ><option value="futures">分项 · 期货</option
          ><option value="combined">分项 · 期货 + 期权</option
          ><option value="legacy">传统 · 期货</option></select
        ></label
      >
      <label
        >历史区间
        <select v-model.number="weeks"
          ><option :value="13">13 周</option
          ><option :value="52">52 周</option
          ><option :value="156">156 周</option
          ><option :value="0">全部</option></select
        ></label
      >
      <label
        >图表
        <select v-model="metric"
          ><option value="net">净持仓</option
          ><option value="long">多头</option
          ><option value="short">空头</option></select
        ></label
      >
    </div>
    <p v-if="error" class="gold-warning">{{ error }}</p>
    <template v-if="current">
      <p class="gold-meta"
        >报告日 {{ current.latest.date }} · CFTC / COMEX 黄金 ·
        {{ data?.status === 'stale' ? '数据待更新' : '周度持仓' }}</p
      >
      <div class="gold-kpis">
        <article
          ><span>{{ primary.label }}净持仓</span><b>{{ formatCount(primary.net) }}</b
          ><small>周变化 {{ formatCount(primary.weeklyChange) }} 手</small></article
        >
        <article
          ><span>未平仓量</span><b>{{ formatCount(current.latest.openInterest) }}</b
          ><small>{{ formatCount(current.latest.traders) }} 位报告交易者</small></article
        >
        <article
          ><span>净持仓 / 未平仓量</span><b>{{ formatCount(primary.netShare) }}%</b
          ><small
            >52 周分位 {{ formatCount(primary.percentile52) }}% · 156 周
            {{ formatCount(primary.percentile156) }}%</small
          ></article
        >
        <article
          ><span>资产管理机构期权等价净持仓</span><b>{{ formatCount(data?.optionsEquivalent) }}</b
          ><small>同日报告：期货加期权减期货 · 手</small></article
        >
      </div>
      <div class="gold-plot"
        ><SourceSeriesPlot :series="series" :colors="colors" unit-label="手"
      /></div>
      <div class="gold-controls gold-meta"
        ><span v-for="(item, i) in series" :key="item.seriesId"
          ><span :style="{ color: colors[i] }">●</span> {{ item.label }}</span
        ></div
      >
      <div class="gold-table"
        ><table
          ><thead
            ><tr
              ><th>交易者分类</th><th>多头</th><th>空头</th><th>套利</th><th>净持仓</th
              ><th>周变动</th><th>4 周</th><th>13 周</th></tr
            ></thead
          ><tbody
            ><tr v-for="(group, key) in current.latest.categories" :key="key"
              ><td>{{ group.label }}</td
              ><td
                >{{ formatCount(group.long)
                }}<small>Δ {{ formatCount(group.longChange) }}</small></td
              ><td
                >{{ formatCount(group.short)
                }}<small>Δ {{ formatCount(group.shortChange) }}</small></td
              ><td>{{ formatCount(group.spreading) }}</td
              ><td>{{ formatCount(group.net) }}</td
              ><td>{{ formatCount(group.weeklyChange) }}</td
              ><td>{{ formatCount(group.change4w) }}</td
              ><td>{{ formatCount(group.change13w) }}</td></tr
            ></tbody
          ></table
        ></div
      >
      <p class="gold-meta"
        >单位：手。通常周五发布截至周二的持仓。分位按净持仓占未平仓量计算；不足完整窗口显示
        —。传统非商业与分项资产管理机构分类不同。</p
      >
      <a :href="current.sourceUrl" target="_blank" rel="noopener noreferrer">CFTC 官方数据 ↗</a>
    </template>
    <p v-else-if="!error">{{ data ? '暂无黄金持仓报告。' : '正在读取黄金持仓…' }}</p>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, shallowRef } from 'vue';
  import { type MacroDashboardSeries } from '@/api/hedgeResearch';
  import SourceSeriesPlot from '../charts/SourceSeriesPlot.vue';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import { goldRequest, formatCount, type GoldPositions } from './goldResearch';

  const data = shallowRef<GoldPositions>();
  const colors = ['#b98028', '#3367d6', '#8696a7', '#8e69b0', '#3c9a89'];
  const scope = ref('futures');
  const weeks = ref(52);
  const metric = ref<'net' | 'long' | 'short'>('net');
  const error = ref('');
  const current = computed(() => data.value?.scopes?.[scope.value]);
  const primary = computed(
    () => current.value!.latest.categories[scope.value === 'legacy' ? 'noncommercial' : 'managed'],
  );
  const series = computed(() => {
    if (!current.value) return [];
    const history = weeks.value
      ? current.value.history.filter(
          (r) =>
            new Date(r.date).getTime() >
            new Date(current.value!.latest.date).getTime() - weeks.value * 7 * 86400000,
        )
      : current.value.history;
    return Object.entries(current.value.latest.categories).map(
      ([key, category]) =>
        ({
          seriesId: `gold-${scope.value}-${key}-${metric.value}`,
          label: category.label,
          unit: 'contracts',
          status: data.value?.status,
          isStale: data.value?.status === 'stale',
          observationDate: current.value!.latest.date,
          latestValue: String(category[metric.value]),
          source: 'CFTC',
          observations: history.map((row) => ({
            date: row.date,
            value: String(row.categories[key][metric.value]),
          })),
        } as MacroDashboardSeries),
    );
  });
  useDashboardRefresh(async () => {
    try {
      data.value = await goldRequest<GoldPositions>('gold-positioning');
      error.value = '';
    } catch {
      error.value = '黄金持仓暂时不可用，请稍后重试。';
    }
  });
</script>
<style scoped src="./goldResearch.css"></style>
