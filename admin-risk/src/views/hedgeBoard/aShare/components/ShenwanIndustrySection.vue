<template>
  <section id="a-share-shenwan" class="research-card">
    <header class="research-card__header">
      <div>
        <p class="research-card__eyebrow">SHENWAN INDUSTRIES</p>
        <h2>申万板块</h2>
      </div>
      <ResearchSourceState v-if="module" :meta="module.meta" />
    </header>

    <template v-if="data">
      <div class="section-title-row">
        <div>
          <h3>申万二级成交额 Top 10</h3>
          <p>默认按当日行业总成交额降序。</p>
        </div>
      </div>
      <div class="table-shell">
        <table class="market-table market-table--top">
          <thead>
            <tr>
              <th>排名</th>
              <th class="is-left">申万二级</th>
              <th class="is-left">所属申万一级</th>
              <th>涨跌幅</th>
              <th class="is-right">成交额</th>
              <th>全市场成交占比</th>
              <th class="is-right">净流入</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in data.sw2Top" :key="row.swL2Code">
              <td>{{ row.rank }}</td>
              <td class="is-left"><strong>{{ row.swL2Name }}</strong><small>{{ row.swL2Code }}</small></td>
              <td class="is-left">{{ row.swL1Name }}</td>
              <td :class="toneClass(row.returnPct)">{{ formatPct(row.returnPct) }}</td>
              <td class="is-right">{{ formatMoney(row.turnoverYuan) }}</td>
              <td>{{ formatPct(row.marketSharePct, false) }}</td>
              <td class="is-right" :class="toneClass(row.netInflowYuan)">{{ formatMoney(row.netInflowYuan) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <button type="button" class="collapse-button" @click="fullExpanded = !fullExpanded">
        <span>{{ fullExpanded ? '▼' : '▶' }}</span>
        全部申万二级行业
      </button>
      <div v-if="fullExpanded" class="full-panel">
        <div class="filter-row">
          <label>
            <span>申万一级</span>
            <select v-model="l1Filter">
              <option value="">全部</option>
              <option v-for="name in l1Options" :key="name" :value="name">{{ name }}</option>
            </select>
          </label>
          <label class="filter-row__search">
            <span>搜索二级行业</span>
            <input v-model.trim="searchText" type="search" placeholder="输入行业名称或代码" />
          </label>
          <label>
            <span>排序</span>
            <select v-model="sortKey">
              <option value="turnover">成交额</option>
              <option value="return">涨跌幅</option>
              <option value="share">市场占比</option>
            </select>
          </label>
        </div>
        <div class="table-shell">
          <table class="market-table">
            <thead>
              <tr>
                <th>排名</th>
                <th class="is-left">申万二级</th>
                <th class="is-left">所属一级</th>
                <th>涨跌幅</th>
                <th class="is-right">成交额</th>
                <th>市场占比</th>
                <th class="is-right">净流入</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredAllRows" :key="row.swL2Code">
                <td>{{ row.rank }}</td>
                <td class="is-left"><strong>{{ row.swL2Name }}</strong><small>{{ row.swL2Code }}</small></td>
                <td class="is-left">{{ row.swL1Name }}</td>
                <td :class="toneClass(row.returnPct)">{{ formatPct(row.returnPct) }}</td>
                <td class="is-right">{{ formatMoney(row.turnoverYuan) }}</td>
                <td>{{ formatPct(row.marketSharePct, false) }}</td>
                <td class="is-right" :class="toneClass(row.netInflowYuan)">{{ formatMoney(row.netInflowYuan) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="threshold-panel">
        <div class="section-title-row">
          <div>
            <h3>个股成交额阈值统计</h3>
            <p>严格按个股当日成交额大于阈值统计，不含等于阈值的个股。</p>
          </div>
          <div class="threshold-actions">
            <button type="button" @click="$emit('copy')">复制统计</button>
            <button type="button" @click="$emit('export')">导出明细</button>
          </div>
        </div>
        <div class="threshold-controls">
          <label v-for="option in thresholdOptions" :key="option.value" class="radio-option">
            <input
              type="radio"
              name="turnover-threshold"
              :checked="thresholdMode === option.value"
              @change="$emit('update:thresholdMode', option.value)"
            />
            {{ option.label }}
          </label>
          <label v-if="thresholdMode === 'custom'" class="custom-threshold">
            <input
              type="number"
              min="1"
              step="1"
              :value="customThresholdYi"
              @input="$emit('update:customThresholdYi', Number(($event.target as HTMLInputElement).value))"
            />
            <span>亿元</span>
          </label>
          <button type="button" class="primary-button" @click="$emit('applyThreshold')">应用</button>
        </div>

        <div class="threshold-summary">
          <span>当前口径：成交额 {{ data.threshold.operator }} {{ formatMoney(data.threshold.thresholdYuan) }}</span>
          <span>共 {{ data.threshold.stocks.length }} 只</span>
          <span>覆盖 {{ data.threshold.industries.length }} 个申万二级行业</span>
          <span v-if="data.unmatchedSecurityCodes.length">待匹配 {{ data.unmatchedSecurityCodes.length }} 只</span>
        </div>

        <div class="table-shell">
          <table class="market-table threshold-table">
            <thead>
              <tr>
                <th class="is-left">申万一级</th>
                <th class="is-left">申万二级</th>
                <th>超过阈值的个股数量</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="row in data.threshold.industries" :key="row.swL2Code">
                <tr class="is-clickable" @click="toggleThresholdIndustry(row.swL2Code)">
                  <td class="is-left">{{ row.swL1Name }}</td>
                  <td class="is-left"><strong>{{ row.swL2Name }}</strong></td>
                  <td><button type="button" class="count-button">{{ row.stockCount }}</button></td>
                </tr>
                <tr v-if="expandedThresholdIndustry === row.swL2Code" class="detail-row">
                  <td colspan="3">
                    <div class="threshold-stock-grid">
                      <article v-for="stock in thresholdStocks(row.swL2Code)" :key="stock.securityCode">
                        <div><strong>{{ stock.securityName }}</strong><span>{{ stock.securityCode }}</span></div>
                        <b>{{ formatMoney(stock.turnoverYuan) }}</b>
                        <em :class="toneClass(stock.returnPct)">{{ formatPct(stock.returnPct) }}</em>
                      </article>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </template>
    <div v-else class="research-empty">{{ module?.meta.message || '暂无申万行业数据' }}</div>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type {
    AShareResearchAggregation,
    ResearchModuleResult,
    ShenwanLevel2Aggregate,
  } from '@/api/hedgeResearch';
  import ResearchSourceState from '../../research/components/ResearchSourceState.vue';

  const props = defineProps<{
    module?: ResearchModuleResult<AShareResearchAggregation> | null;
    thresholdMode: '50' | '100' | '200' | 'custom';
    customThresholdYi: number;
  }>();

  defineEmits<{
    (event: 'update:thresholdMode', value: '50' | '100' | '200' | 'custom'): void;
    (event: 'update:customThresholdYi', value: number): void;
    (event: 'applyThreshold'): void;
    (event: 'copy'): void;
    (event: 'export'): void;
  }>();

  const data = computed(() => props.module?.data || null);
  const fullExpanded = ref(false);
  const l1Filter = ref('');
  const searchText = ref('');
  const sortKey = ref<'turnover' | 'return' | 'share'>('turnover');
  const expandedThresholdIndustry = ref('');
  const thresholdOptions = [
    { value: '50' as const, label: '50亿元' },
    { value: '100' as const, label: '100亿元' },
    { value: '200' as const, label: '200亿元' },
    { value: 'custom' as const, label: '自定义' },
  ];

  const l1Options = computed(() =>
    Array.from(new Set((data.value?.sw2All || []).map((row) => row.swL1Name))).sort(),
  );

  const filteredAllRows = computed(() => {
    const query = searchText.value.toLowerCase();
    const rows = [...(data.value?.sw2All || [])].filter((row) => {
      const matchesL1 = !l1Filter.value || row.swL1Name === l1Filter.value;
      const matchesSearch =
        !query || row.swL2Name.toLowerCase().includes(query) || row.swL2Code.toLowerCase().includes(query);
      return matchesL1 && matchesSearch;
    });
    return rows.sort((left, right) => {
      const read = (row: ShenwanLevel2Aggregate) => {
        if (sortKey.value === 'return') return Number(row.returnPct || 0);
        if (sortKey.value === 'share') return Number(row.marketSharePct || 0);
        return Number(row.turnoverYuan || 0);
      };
      return read(right) - read(left);
    });
  });

  function toggleThresholdIndustry(code: string) {
    expandedThresholdIndustry.value = expandedThresholdIndustry.value === code ? '' : code;
  }

  function thresholdStocks(code: string) {
    return (data.value?.threshold.stocks || []).filter((stock) => stock.swL2Code === code);
  }

  function numeric(value: string | number | null | undefined) {
    const result = Number(value);
    return Number.isFinite(result) ? result : null;
  }

  function formatMoney(value: string | number | null | undefined) {
    const result = numeric(value);
    if (result == null) return '—';
    if (Math.abs(result) >= 1_000_000_000_000) return `${(result / 1_000_000_000_000).toFixed(2)}万亿`;
    if (Math.abs(result) >= 100_000_000) return `${(result / 100_000_000).toFixed(2)}亿`;
    if (Math.abs(result) >= 10_000) return `${(result / 10_000).toFixed(2)}万`;
    return result.toLocaleString('zh-CN');
  }

  function formatPct(value: string | number | null | undefined, signed = true) {
    const result = numeric(value);
    if (result == null) return '—';
    return `${signed && result > 0 ? '+' : ''}${result.toFixed(2)}%`;
  }

  function toneClass(value: string | number | null | undefined) {
    const result = numeric(value);
    return result == null ? '' : result > 0 ? 'is-positive' : result < 0 ? 'is-negative' : '';
  }
</script>

<style scoped lang="less">
  .research-card { padding: 18px; border: 1px solid var(--strategy-border); border-radius: var(--strategy-radius-card); background: var(--strategy-surface); box-shadow: var(--strategy-shadow-soft); }
  .research-card__header, .section-title-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
  .research-card__header { margin-bottom: 18px; }
  .research-card__eyebrow { margin: 0 0 3px; color: var(--strategy-text-4); font-size: 11px; font-weight: 800; letter-spacing: .12em; }
  h2, h3, p { margin: 0; }
  h2 { color: var(--strategy-text-1); font-size: 18px; }
  h3 { color: var(--strategy-text-1); font-size: 15px; }
  .section-title-row p { margin-top: 4px; color: var(--strategy-text-3); font-size: 12px; }
  .table-shell { overflow-x: auto; margin-top: 12px; border: 1px solid var(--strategy-border); border-radius: 12px; }
  .market-table { width: 100%; min-width: 860px; border-collapse: collapse; font-variant-numeric: tabular-nums; }
  th, td { padding: 11px 12px; border-bottom: 1px solid var(--strategy-border); color: var(--strategy-text-2); text-align: center; }
  th { background: var(--strategy-surface-2); color: var(--strategy-text-3); font-size: 12px; white-space: nowrap; }
  tbody tr:last-child td { border-bottom: 0; }
  tbody tr:not(.detail-row):hover { background: var(--strategy-accent-soft); }
  td strong, td small { display: block; }
  td small { margin-top: 2px; color: var(--strategy-text-4); }
  .is-left { text-align: left; }
  .is-right { text-align: right; }
  .is-positive { color: var(--strategy-up, #ef4444) !important; font-weight: 700; }
  .is-negative { color: var(--strategy-down, #10b981) !important; font-weight: 700; }
  .collapse-button { width: 100%; margin-top: 14px; padding: 11px 14px; border: 1px solid var(--strategy-border); border-radius: 10px; background: var(--strategy-surface-2); color: var(--strategy-text-2); text-align: left; cursor: pointer; }
  .full-panel { margin-top: 12px; }
  .filter-row, .threshold-controls, .threshold-actions, .threshold-summary { display: flex; align-items: flex-end; gap: 10px; flex-wrap: wrap; }
  .filter-row label { display: grid; gap: 5px; color: var(--strategy-text-3); font-size: 12px; }
  .filter-row__search { flex: 1 1 260px; }
  select, input { min-height: 36px; padding: 0 10px; border: 1px solid var(--strategy-border); border-radius: 8px; background: var(--strategy-surface); color: var(--strategy-text-1); }
  .threshold-panel { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--strategy-border); }
  .threshold-actions button, .primary-button { min-height: 34px; padding: 0 12px; border: 1px solid var(--strategy-border); border-radius: 8px; background: var(--strategy-surface-2); color: var(--strategy-text-2); cursor: pointer; }
  .primary-button { background: var(--strategy-accent-soft); color: var(--strategy-accent-strong); font-weight: 700; }
  .threshold-controls { margin-top: 14px; align-items: center; }
  .radio-option { display: inline-flex; align-items: center; gap: 5px; color: var(--strategy-text-2); }
  .radio-option input { min-height: auto; }
  .custom-threshold { display: inline-flex; align-items: center; gap: 6px; }
  .custom-threshold input { width: 100px; }
  .threshold-summary { margin-top: 12px; align-items: center; }
  .threshold-summary span { padding: 5px 9px; border-radius: 999px; background: var(--strategy-surface-2); color: var(--strategy-text-3); font-size: 12px; }
  .is-clickable { cursor: pointer; }
  .count-button { min-width: 40px; padding: 4px 10px; border: 0; border-radius: 999px; background: var(--strategy-accent-soft); color: var(--strategy-accent-strong); font-weight: 800; cursor: pointer; }
  .detail-row td { padding: 14px; background: var(--strategy-surface-2); }
  .threshold-stock-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; }
  .threshold-stock-grid article { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; align-items: center; gap: 10px; padding: 10px; border: 1px solid var(--strategy-border); border-radius: 9px; background: var(--strategy-surface); text-align: left; }
  .threshold-stock-grid div strong, .threshold-stock-grid div span { display: block; }
  .threshold-stock-grid div span { color: var(--strategy-text-4); font-size: 12px; }
  .threshold-stock-grid b, .threshold-stock-grid em { white-space: nowrap; font-style: normal; }
  .research-empty { padding: 30px; color: var(--strategy-text-3); text-align: center; }
  @media (max-width: 900px) { .threshold-stock-grid { grid-template-columns: 1fr; } }
  @media (max-width: 640px) { .research-card__header, .section-title-row { flex-direction: column; } }
</style>
