<template>
  <section class="macro-expectation-panel">
    <header class="panel-header">
      <div>
        <h2>市场预期与事件概率</h2>
      </div>
      <div class="panel-actions">
        <ResearchSourceState v-if="sourceMeta" :meta="sourceMeta" />
        <button type="button" :disabled="loading" @click="load">{{
          loading ? '刷新中…' : '刷新'
        }}</button>
      </div>
    </header>

    <div v-if="error" class="error-state">{{ error }}</div>
    <div v-if="loading && !events.length" class="loading-state">正在读取市场预期数据…</div>
    <div v-else-if="response" class="category-list">
      <section v-for="group in groupedEvents" :key="group.category" class="category-section">
        <header
          ><h3>{{ categoryLabel(group.category) }}</h3
          ><span>{{ group.events.length }}项</span></header
        >
        <div v-if="!group.events.length" class="category-empty">当前没有符合筛选条件的事件。</div>
        <div v-else class="event-grid">
          <article v-for="event in group.events" :key="event.id" class="event-card">
            <div class="event-card__header">
              <span>市场隐含概率</span>
              <strong>{{ formatProbability(event.probability) }}</strong>
            </div>
            <h4 :title="event.originalLabel || undefined">{{ event.label }}</h4>
            <svg
              v-if="event.chart.count"
              viewBox="0 0 220 72"
              preserveAspectRatio="none"
              aria-label="事件概率历史曲线"
            >
              <line x1="0" y1="18" x2="220" y2="18" />
              <line x1="0" y1="36" x2="220" y2="36" />
              <line x1="0" y1="54" x2="220" y2="54" />
              <polyline v-if="event.chart.count > 1" :points="event.chart.points" />
              <circle
                v-else-if="event.chart.single"
                :cx="event.chart.single.x"
                :cy="event.chart.single.y"
                r="3"
              />
            </svg>
            <p v-if="event.chart.count < 2" class="history-empty">{{
              event.chart.count ? '仅有一次观测，尚无历史走势' : '暂无历史观测'
            }}</p>
            <div class="event-metrics">
              <span
                >1日
                <b :class="changeTone(event.chart.change1d)">{{
                  formatChange(event.chart.change1d)
                }}</b></span
              >
              <span
                >7日
                <b :class="changeTone(event.chart.change7d)">{{
                  formatChange(event.chart.change7d)
                }}</b></span
              >
              <span>来源 <b>Polymarket</b></span>
            </div>
            <footer>
              <span>{{ formatUpdated(event.chart.lastAt) }}</span>
              <a
                :href="event.sourceUrl || response?.sourceUrl || dataFileUrl"
                target="_blank"
                rel="noopener noreferrer"
                >查看来源</a
              >
            </footer>
          </article>
        </div>
      </section>
    </div>
    <div v-else class="empty-state">{{ emptyMessage }}</div>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import {
    getMacroExpectations,
    type MacroExpectationEvent,
    type MacroExpectationResponse,
    type ResearchSourceMeta,
  } from '@/api/hedgeResearch';
  import ResearchSourceState from '../research/components/ResearchSourceState.vue';

  import { probabilityHistory } from './probabilityHistory';

  const dataFileUrl = 'https://polymarket.com/markets';

  const response = ref<MacroExpectationResponse | null>(null);
  const loading = ref(false);
  const error = ref('');

  const events = computed(() =>
    (response.value?.events || [])
      .filter((event) => event.category !== 'monetary_policy')
      .map((event) => ({ ...event, chart: probabilityHistory(event.history) })),
  );
  const sourceMeta = computed<ResearchSourceMeta | null>(() => {
    if (!response.value) return null;
    const status: ResearchSourceMeta['status'] =
      response.value.status === 'not_configured' ? 'no_data' : response.value.status;
    return {
      source: response.value.source,
      sourceTimestamp: response.value.updatedAt,
      fetchedAt: response.value.updatedAt,
      status,
      isStale: response.value.status === 'stale',
      message:
        response.value.status === 'not_configured' ? '官方数据源尚未配置，未生成替代概率' : null,
    };
  });
  const emptyMessage = computed(() => {
    if (!response.value) return '暂无可用的市场预期事件。';
    return {
      ready: '暂无可用的市场预期事件。',
      no_data: '当前配置未产生可用的市场预期数据。',
      not_configured: '市场预期官方数据源尚未配置。',
      stale: '上一份有效数据暂无事件。',
      error: '市场预期数据暂不可用。',
    }[response.value.status];
  });
  const groupedEvents = computed(() => {
    const order: MacroExpectationEvent['category'][] = ['macro', 'geopolitics', 'election'];
    return order.map((category) => ({
      category,
      events: events.value.filter((event) => event.category === category),
    }));
  });

  async function load() {
    loading.value = true;
    error.value = '';
    try {
      response.value = await getMacroExpectations();
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : '事件概率加载失败';
    } finally {
      loading.value = false;
    }
  }

  function categoryLabel(category: MacroExpectationEvent['category']) {
    return {
      monetary_policy: '货币政策',
      macro: '宏观经济',
      geopolitics: '地缘政治',
      election: '选举与政策',
    }[category];
  }

  function number(value: string | number | null | undefined) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }

  function formatProbability(value: string | number) {
    const parsed = number(value);
    return parsed == null ? '—' : `${parsed.toFixed(1)}%`;
  }

  function formatChange(value: number | null) {
    return value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(1)}pp`;
  }

  function changeTone(value: number | null) {
    return value == null ? '' : value > 0 ? 'is-positive' : value < 0 ? 'is-negative' : '';
  }

  function formatUpdated(timestamp: number | undefined) {
    return timestamp == null
      ? '更新时间未知'
      : `更新 ${new Date(timestamp).toLocaleString('zh-CN', { hour12: false })}`;
  }
  onMounted(() => void load());
</script>

<style scoped lang="less">
  .macro-expectation-panel {
    --strategy-surface: #fff;
    --strategy-surface-2: #f8fafc;
    --strategy-border: #e2e8f0;
    --strategy-text-1: #111827;
    --strategy-text-2: #334155;
    --strategy-text-3: #64748b;
    --strategy-text-4: #94a3b8;
    --strategy-accent-soft: #eef2ff;
    --strategy-accent-strong: #4338ca;
    --strategy-up: #ef4444;
    --strategy-down: #10b981;

    margin: 14px 16px 32px;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 14px;
    background: var(--strategy-surface);
    box-shadow: 0 4px 16px rgb(15 23 42 / 4.5%);
  }

  .panel-header,
  .panel-actions,
  .category-section > header,
  .event-card__header,
  .event-metrics,
  .event-card footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .panel-header {
    align-items: flex-start;
  }

  .panel-header p {
    margin: 0 0 3px;
    color: var(--strategy-text-4);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  h2,
  h3,
  h4 {
    margin: 0;
    color: var(--strategy-text-1);
  }

  h2 {
    font-size: 18px;
  }

  h3 {
    font-size: 15px;
  }

  h4 {
    min-height: 44px;
    margin-top: 10px;
    font-size: 14px;
    line-height: 1.55;
  }

  .panel-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .panel-actions button {
    height: 34px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 8px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-2);
    cursor: pointer;
  }

  .category-list {
    display: grid;
    gap: 18px;
    margin-top: 18px;
  }

  .category-section > header {
    margin-bottom: 10px;
  }

  .category-section > header span {
    color: var(--strategy-text-4);
    font-size: 12px;
  }

  .category-empty {
    padding: 14px;
    border: 1px dashed var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .event-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 11px;
  }

  .event-card {
    min-width: 0;
    padding: 13px;
    border: 1px solid var(--strategy-border);
    border-radius: 11px;
    background: var(--strategy-surface-2);
  }

  .event-card__header span {
    overflow: hidden;
    color: var(--strategy-text-3);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .event-card__header strong {
    color: var(--strategy-accent-strong);
    font-size: 24px;
    font-variant-numeric: tabular-nums;
  }

  .event-card svg {
    width: 100%;
    height: 72px;
    margin: 8px 0;
  }

  .event-card line {
    stroke-width: 1;
    stroke: var(--strategy-border);
  }

  .event-card circle {
    fill: var(--strategy-accent-strong);
  }

  .history-empty {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .event-card polyline {
    stroke-width: 2;
    stroke: var(--strategy-accent-strong);
    fill: none;
    vector-effect: non-scaling-stroke;
  }

  .event-metrics {
    flex-wrap: wrap;
    justify-content: flex-start;
  }

  .event-metrics span {
    color: var(--strategy-text-4);
    font-size: 12px;
  }

  .event-metrics b {
    color: var(--strategy-text-2);
    font-weight: 700;
  }

  .event-card footer {
    margin-top: 10px;
    padding-top: 9px;
    border-top: 1px solid var(--strategy-border);
    color: var(--strategy-text-4);
    font-size: 12px;
  }

  .event-card footer a {
    color: var(--strategy-accent-strong);
  }

  .is-positive {
    color: var(--strategy-up) !important;
  }

  .is-negative {
    color: var(--strategy-down) !important;
  }

  .error-state,
  .loading-state,
  .empty-state {
    margin-top: 14px;
    padding: 28px;
    border-radius: 10px;
    background: var(--strategy-surface-2);
    color: var(--strategy-text-3);
    text-align: center;
  }

  .error-state {
    color: #dc2626;
  }

  @media (max-width: 1150px) {
    .event-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 720px) {
    .panel-header {
      flex-direction: column;
    }

    .event-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
