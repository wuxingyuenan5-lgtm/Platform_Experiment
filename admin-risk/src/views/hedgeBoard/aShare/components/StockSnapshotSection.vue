<template>
  <section id="a-share-stock-snapshot" class="research-card stock-snapshot">
    <header class="research-card__header">
      <div>
        <p class="research-card__eyebrow">ONE-CLICK STOCK DATA</p>
        <h2>一键个股数据</h2>
      </div>
      <div v-if="snapshot" class="snapshot-meta">
        <span>{{ snapshot.securityName || snapshot.securityCode }}</span>
        <b>完整度 {{ Number(snapshot.completenessPct).toFixed(0) }}%</b>
      </div>
    </header>

    <form class="query-form" @submit.prevent="$emit('query', codeModel)">
      <label>
        <span>股票代码</span>
        <input v-model.trim="codeModel" maxlength="6" inputmode="numeric" placeholder="输入6位A股代码" />
      </label>
      <button type="submit" class="primary-button" :disabled="loading">
        {{ loading ? '查询中…' : '查询' }}
      </button>
      <button
        v-if="snapshot"
        type="button"
        class="toolbar-button"
        @click="$emit('addWatchlist', snapshot.securityCode, snapshot.securityName || snapshot.securityCode)"
      >
        加入自选
      </button>
      <button v-if="snapshot" type="button" class="toolbar-button" @click="toggleAll">
        {{ allExpanded ? '全部收起' : '全部展开' }}
      </button>
    </form>

    <div v-if="error" class="query-error">{{ error }}</div>
    <div v-if="loading" class="query-loading">
      <span class="loading-dot" /><span class="loading-dot" /><span class="loading-dot" />
      正在并行读取行情、估值、财务、信息与筹码数据
    </div>

    <div v-if="snapshot && !loading" class="module-list">
      <article v-for="definition in orderedDefinitions" :key="definition.key" class="snapshot-module">
        <button type="button" class="snapshot-module__header" @click="toggleModule(definition.key)">
          <span class="module-arrow">{{ expanded[definition.key] ? '▼' : '▶' }}</span>
          <span class="module-title"><strong>{{ definition.label }}</strong><small>{{ summary(definition.key) }}</small></span>
          <ResearchSourceState v-if="module(definition.key)" :meta="module(definition.key)!.meta" />
        </button>
        <div v-if="expanded[definition.key]" class="snapshot-module__body">
          <ResearchDataRenderer v-if="module(definition.key)?.data" :value="module(definition.key)?.data" />
          <div v-else class="research-empty">{{ module(definition.key)?.meta.message || '暂无数据' }}</div>
        </div>
      </article>
    </div>

    <div v-else-if="!loading && !error" class="research-empty">
      输入股票代码后，将按固定数据流程并行读取全部客观数据模块。
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, reactive, ref, watch } from 'vue';
  import type { ResearchModuleResult, StockSnapshotResponse } from '@/api/hedgeResearch';
  import ResearchDataRenderer from '../../research/components/ResearchDataRenderer.vue';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';

  const props = defineProps<{
    code: string;
    snapshot: StockSnapshotResponse | null;
    loading: boolean;
    error: string;
  }>();

  const emit = defineEmits<{
    (event: 'update:code', value: string): void;
    (event: 'query', code: string): void;
    (event: 'addWatchlist', code: string, name: string): void;
  }>();

  const definitions = [
    { key: 'quoteValuation', label: '行情与估值' },
    { key: 'consensus', label: '一致预期' },
    { key: 'financials', label: '财报速览' },
    { key: 'valuationPercentile', label: '历史估值分位' },
    { key: 'reports', label: '研报' },
    { key: 'announcements', label: '公告' },
    { key: 'news', label: '个股新闻' },
    { key: 'margin', label: '融资融券' },
    { key: 'holders', label: '股东户数' },
    { key: 'fundFlow', label: '资金流' },
    { key: 'dividends', label: '分红' },
    { key: 'blockTrades', label: '大宗交易' },
    { key: 'dragonTiger', label: '龙虎榜' },
    { key: 'lockup', label: '限售解禁' },
    { key: 'investorQa', label: '投资者互动' },
    { key: 'shenwan', label: '申万行业归属' },
  ] as const;

  const expanded = reactive<Record<string, boolean>>({});
  const codeModel = ref(props.code);
  const orderedDefinitions = computed(() => definitions);
  const allExpanded = computed(() => definitions.every((item) => expanded[item.key]));

  watch(
    () => props.code,
    (value) => {
      codeModel.value = value;
    },
  );
  watch(codeModel, (value) => emit('update:code', value));
  watch(
    () => props.snapshot?.securityCode,
    () => {
      definitions.forEach((item) => {
        expanded[item.key] = false;
      });
    },
  );

  function module(key: string): ResearchModuleResult | null {
    return props.snapshot?.modules[key] || null;
  }

  function toggleModule(key: string) {
    expanded[key] = !expanded[key];
  }

  function toggleAll() {
    const next = !allExpanded.value;
    definitions.forEach((item) => {
      expanded[item.key] = next;
    });
  }

  function summary(key: string) {
    const data = module(key)?.data;
    if (data == null) return module(key)?.meta.message || '暂无数据';
    if (Array.isArray(data)) return `${data.length}条记录`;
    if (typeof data !== 'object') return String(data);
    const record = data as Record<string, unknown>;
    const candidates: Record<string, () => string> = {
      quoteValuation: () => `${record.price ?? '—'} · PE ${record.peTtm ?? '—'} · PB ${record.pb ?? '—'}`,
      consensus: () => `前向PE ${record.forwardPe ?? '—'} · PEG ${record.peg ?? '—'} · 覆盖 ${record.analystCount ?? 0}`,
      financials: () => `${record.period ?? '最新报告期'} · ROE ${record.roe ?? '—'}`,
      valuationPercentile: () => `${record.period ?? '近5年'} · ${Object.keys((record.metrics as object) || {}).length}项指标`,
      fundFlow: () => `近20日主力净流入 ${record.mainNet20d ?? '—'}`,
      dragonTiger: () => `${Array.isArray(record.records) ? record.records.length : 0}次上榜`,
      lockup: () => `未来 ${Array.isArray(record.upcoming) ? record.upcoming.length : 0}项`,
      shenwan: () => `${record.swL1Name ?? '待匹配'} / ${record.swL2Name ?? '待匹配'}`,
    };
    if (candidates[key]) return candidates[key]();
    const firstArray = Object.values(record).find(Array.isArray) as unknown[] | undefined;
    return firstArray ? `${firstArray.length}条记录` : `${Object.keys(record).length}项数据`;
  }
</script>

<style scoped lang="less">
  .research-card { padding: 18px; border: 1px solid var(--strategy-border); border-radius: var(--strategy-radius-card); background: var(--strategy-surface); box-shadow: var(--strategy-shadow-soft); }
  .research-card__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 15px; }
  .research-card__eyebrow { margin: 0 0 3px; color: var(--strategy-text-4); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
  h2 { margin: 0; color: var(--strategy-text-1); font-size: 18px; }
  .snapshot-meta { display: flex; align-items: center; gap: 9px; color: var(--strategy-text-2); }
  .snapshot-meta b { padding: 5px 9px; border-radius: 999px; background: var(--strategy-accent-soft); color: var(--strategy-accent-strong); }
  .query-form { display: flex; align-items: flex-end; gap: 9px; flex-wrap: wrap; padding: 12px; border: 1px solid var(--strategy-border); border-radius: 11px; background: var(--strategy-surface-2); }
  .query-form label { display: grid; gap: 5px; flex: 1 1 240px; color: var(--strategy-text-3); font-size: 12px; }
  .query-form input { height: 38px; padding: 0 11px; border: 1px solid var(--strategy-border); border-radius: 8px; background: var(--strategy-surface); color: var(--strategy-text-1); font-size: 14px; }
  .primary-button, .toolbar-button { height: 38px; padding: 0 14px; border: 1px solid var(--strategy-border); border-radius: 8px; background: var(--strategy-surface); color: var(--strategy-text-2); cursor: pointer; }
  .primary-button { background: var(--strategy-accent-soft); color: var(--strategy-accent-strong); font-weight: 800; }
  .primary-button:disabled { cursor: wait; opacity: .65; }
  .query-error { margin-top: 10px; padding: 10px 12px; border-radius: 9px; background: rgba(239, 68, 68, .08); color: #dc2626; }
  .query-loading { display: flex; align-items: center; justify-content: center; gap: 6px; min-height: 120px; color: var(--strategy-text-3); }
  .loading-dot { width: 6px; height: 6px; border-radius: 999px; background: var(--strategy-accent-strong); animation: pulse 1s infinite alternate; }
  .loading-dot:nth-child(2) { animation-delay: .2s; }
  .loading-dot:nth-child(3) { animation-delay: .4s; margin-right: 5px; }
  .module-list { display: grid; gap: 8px; margin-top: 12px; }
  .snapshot-module { overflow: hidden; border: 1px solid var(--strategy-border); border-radius: 10px; }
  .snapshot-module__header { display: grid; grid-template-columns: 20px minmax(180px, 1fr) minmax(200px, auto); align-items: center; gap: 9px; width: 100%; padding: 11px 12px; border: 0; background: var(--strategy-surface-2); color: var(--strategy-text-2); text-align: left; cursor: pointer; }
  .module-arrow { color: var(--strategy-text-4); }
  .module-title { min-width: 0; }
  .module-title strong, .module-title small { display: block; }
  .module-title strong { color: var(--strategy-text-1); }
  .module-title small { margin-top: 3px; overflow: hidden; color: var(--strategy-text-3); text-overflow: ellipsis; white-space: nowrap; }
  .snapshot-module__body { padding: 12px; background: var(--strategy-surface); }
  .research-empty { padding: 30px; color: var(--strategy-text-3); text-align: center; }
  @keyframes pulse { from { opacity: .25; transform: translateY(1px); } to { opacity: 1; transform: translateY(-1px); } }
  @media (max-width: 760px) { .research-card__header { flex-direction: column; } .snapshot-module__header { grid-template-columns: 20px 1fr; } .snapshot-module__header :deep(.research-source-state) { grid-column: 2; } }
</style>
