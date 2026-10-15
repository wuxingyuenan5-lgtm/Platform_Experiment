<template>
  <div class="gold-research">
    <p v-if="error" class="gold-warning">{{ error }}</p>
    <template v-if="data?.conclusion">
      <div class="gold-controls"
        ><span class="gold-tag">{{ directionLabel(data.conclusion.directional_bias) }}</span
        ><span>{{ data.reportDate }} 日报</span
        ><span class="gold-meta">{{ data.source }} · {{ generated }}</span></div
      >
      <p v-if="data.status === 'stale'" class="gold-warning"
        >数据更新暂时中断，以下为最近取得的报告。</p
      >
      <p class="gold-headline">{{ data.conclusion.one_sentence }}</p>
      <p>{{ data.conclusion.reason }}</p>
      <div class="gold-points"
        ><p v-for="(point, i) in data.keyPoints" :key="i"
          ><span class="gold-tag">{{ i + 1 }}</span
          >{{ point }}</p
        ></div
      >
      <p class="gold-meta"
        >报告采用 CFTC {{ data.cftcDate || '日期未披露' }} 数据 ·
        {{
          data.quality === 'partial' ? '部分数据不完整' : '来源研判'
        }}。下方持仓面板展示独立更新的官方报告。</p
      >
      <details
        ><summary>查看关键价位与后续事件</summary>
        <div class="gold-table"
          ><table
            ><thead
              ><tr><th>类型</th><th>XAUUSD · 美元/盎司</th><th>依据</th></tr></thead
            ><tbody
              ><tr v-for="(level, i) in data.keyLevels" :key="i"
                ><td>{{ level.side === 'support' ? '支撑' : '阻力' }}</td
                ><td>{{ level.core_low }}–{{ level.core_high }}</td
                ><td style="white-space: normal">{{ level.reason }}</td></tr
              ></tbody
            ></table
          ></div
        >
        <p class="gold-meta">价位与事件判断来自该日期研报。</p>
        <div class="gold-events"
          ><article v-for="(event, i) in data.events" :key="i"
            ><small>{{ event.date }}</small
            ><h4>{{ event.event }}</h4
            ><p>{{ event.expected_impact }}</p
            ><a
              v-if="event.source_url"
              :href="event.source_url"
              target="_blank"
              rel="noopener noreferrer"
              >日程来源 ↗</a
            ></article
          ></div
        >
      </details>
      <a :href="data.sourceUrl" target="_blank" rel="noopener noreferrer"
        >阅读 GoldPulse 完整研报 ↗</a
      >
    </template>
    <p v-else-if="!error">{{ data ? '暂未取得 AI 研报。' : '正在读取最新研报…' }}</p>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, shallowRef } from 'vue';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import { goldRequest, directionLabel, type GoldReport } from './goldResearch';

  const data = shallowRef<GoldReport>();
  const error = ref('');
  const generated = computed(() =>
    data.value?.generatedAt
      ? new Date(data.value.generatedAt).toLocaleString('zh-CN', {
          timeZone: 'Asia/Shanghai',
          hour12: false,
        }) + ' 北京时间'
      : '生成时间未披露',
  );
  useDashboardRefresh(async () => {
    try {
      data.value = await goldRequest<GoldReport>('gold-report');
      error.value = '';
    } catch {
      error.value = 'AI 研报暂时不可用，请稍后重试。';
    }
  });
</script>
<style scoped src="./goldResearch.css"></style>
