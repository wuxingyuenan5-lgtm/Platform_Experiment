<template>
  <section class="macro-expectation-panel">
    <header class="panel-header">
      <div>
        <p>MARKET EXPECTATIONS</p>
        <h2>市场预期与事件概率</h2>
      </div>
      <div class="panel-actions">
        <ResearchSourceState v-if="response" :meta="response.events.meta" />
        <button type="button" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button>
      </div>
    </header>

    <div v-if="error" class="error-state">{{ error }}</div>
    <div v-if="loading && !events.length" class="loading-state">正在读取公开事件市场概率…</div>
    <div v-else-if="events.length" class="category-list">
      <section v-for="group in groupedEvents" :key="group.category" class="category-section">
        <header><h3>{{ categoryLabel(group.category) }}</h3><span>{{ group.events.length }}项</span></header>
        <div class="event-grid">
          <article v-for="event in group.events" :key="event.eventId" class="event-card">
            <div class="event-card__header">
              <span>{{ event.outcome }}</span>
              <strong>{{ formatProbability(event.currentProbabilityPct) }}</strong>
            </div>
            <h4>{{ event.title }}</h4>
            <svg viewBox="0 0 220 72" preserveAspectRatio="none" aria-label="事件概率历史曲线">
              <line x1="0" y1="18" x2="220" y2="18" />
              <line x1="0" y1="36" x2="220" y2="36" />
              <line x1="0" y1="54" x2="220" y2="54" />
              <polyline :points="historyPoints(event.history)" />
            </svg>
            <div class="event-metrics">
              <span>1日 <b :class="changeTone(event.change1dPctPoints)">{{ formatChange(event.change1dPctPoints) }}</b></span>
              <span>7日 <b :class="changeTone(event.change7dPctPoints)">{{ formatChange(event.change7dPctPoints) }}</b></span>
              <span>流动性 <b>{{ event.liquidityLabel || '—' }}</b></span>
            </div>
            <footer>
              <span>{{ formatExpiry(event.expiryAt) }}</span>
              <a v-if="event.sourceUrl" :href="event.sourceUrl" target="_blank" rel="noopener noreferrer">查看来源</a>
            </footer>
          </article>
        </div>
      </section>
    </div>
    <div v-else class="empty-state">暂无可用的市场预期事件。</div>
  </section>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import {
    getMacroExpectations,
    type MacroExpectationEvent,
    type MacroExpectationResponse,
    type MacroProbabilityPoint,
  } from '@/api/hedgeResearch';
  import ResearchSourceState from '../research/components/ResearchSourceState.vue';

  const response = ref<MacroExpectationResponse | null>(null);
  const loading = ref(false);
  const error = ref('');
  const events = computed(() => response.value?.events.data || []);
  const groupedEvents = computed(() => {
    const order: MacroExpectationEvent['category'][] = ['monetary_policy', 'macro', 'geopolitics', 'election'];
    return order
      .map((category) => ({ category, events: events.value.filter((event) => event.category === category) }))
      .filter((group) => group.events.length);
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

  function formatChange(value: string | number | null | undefined) {
    const parsed = number(value);
    return parsed == null ? '—' : `${parsed > 0 ? '+' : ''}${parsed.toFixed(1)}pp`;
  }

  function changeTone(value: string | number | null | undefined) {
    const parsed = number(value);
    return parsed == null ? '' : parsed > 0 ? 'is-positive' : parsed < 0 ? 'is-negative' : '';
  }

  function historyPoints(history: MacroProbabilityPoint[]) {
    const values = history.map((point) => number(point.probabilityPct)).filter((value): value is number => value != null);
    if (!values.length) return '0,36 220,36';
    if (values.length === 1) return `0,${72 - values[0] * .72} 220,${72 - values[0] * .72}`;
    return values
      .map((value, index) => `${(index / (values.length - 1) * 220).toFixed(2)},${(72 - value * .72).toFixed(2)}`)
      .join(' ');
  }

  function formatExpiry(value: string | null | undefined) {
    if (!value) return '无明确到期日';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '到期日未知';
    return `到期 ${parsed.toLocaleDateString('zh-CN')}`;
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
    box-shadow: 0 4px 16px rgba(15, 23, 42, .045);
  }
  .panel-header, .panel-actions, .category-section > header, .event-card__header, .event-metrics, .event-card footer { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .panel-header { align-items: flex-start; }
  .panel-header p { margin: 0 0 3px; color: var(--strategy-text-4); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
  h2, h3, h4 { margin: 0; color: var(--strategy-text-1); }
  h2 { font-size: 18px; }
  h3 { font-size: 15px; }
  h4 { min-height: 44px; margin-top: 10px; font-size: 14px; line-height: 1.55; }
  .panel-actions { flex-wrap: wrap; justify-content: flex-end; }
  .panel-actions button { height: 34px; padding: 0 12px; border: 1px solid var(--strategy-border); border-radius: 8px; background: var(--strategy-surface-2); color: var(--strategy-text-2); cursor: pointer; }
  .category-list { display: grid; gap: 18px; margin-top: 18px; }
  .category-section > header { margin-bottom: 10px; }
  .category-section > header span { color: var(--strategy-text-4); font-size: 12px; }
  .event-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 11px; }
  .event-card { min-width: 0; padding: 13px; border: 1px solid var(--strategy-border); border-radius: 11px; background: var(--strategy-surface-2); }
  .event-card__header span { overflow: hidden; color: var(--strategy-text-3); text-overflow: ellipsis; white-space: nowrap; }
  .event-card__header strong { color: var(--strategy-accent-strong); font-size: 24px; font-variant-numeric: tabular-nums; }
  .event-card svg { width: 100%; height: 72px; margin: 8px 0; }
  .event-card line { stroke: var(--strategy-border); stroke-width: 1; }
  .event-card polyline { fill: none; stroke: var(--strategy-accent-strong); stroke-width: 2; vector-effect: non-scaling-stroke; }
  .event-metrics { justify-content: flex-start; flex-wrap: wrap; }
  .event-metrics span { color: var(--strategy-text-4); font-size: 12px; }
  .event-metrics b { color: var(--strategy-text-2); font-weight: 700; }
  .event-card footer { margin-top: 10px; padding-top: 9px; border-top: 1px solid var(--strategy-border); color: var(--strategy-text-4); font-size: 12px; }
  .event-card footer a { color: var(--strategy-accent-strong); }
  .is-positive { color: var(--strategy-up) !important; }
  .is-negative { color: var(--strategy-down) !important; }
  .error-state, .loading-state, .empty-state { margin-top: 14px; padding: 28px; border-radius: 10px; background: var(--strategy-surface-2); color: var(--strategy-text-3); text-align: center; }
  .error-state { color: #dc2626; }
  @media (max-width: 1150px) { .event-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  @media (max-width: 720px) { .panel-header { flex-direction: column; } .event-grid { grid-template-columns: 1fr; } }
</style>
