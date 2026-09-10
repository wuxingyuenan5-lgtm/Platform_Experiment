<template>
  <article class="records-card">
    <header class="records-head">
      <div
        ><h3>订单信息</h3
        ><p class="records-description">{{
          currentSection.description || '按场所查看当前持仓、委托与成交，完整编号可展开核对。'
        }}</p></div
      >
      <button type="button" class="refresh-btn" @click="resetFilters">重置筛选</button>
    </header>
    <div class="records-tabs" aria-label="订单记录类别">
      <button
        v-for="item in tabs"
        :key="item.key"
        type="button"
        :class="{ 'is-active': item.key === activeTab }"
        :aria-pressed="item.key === activeTab"
        @click="$emit('update:activeTab', item.key)"
        >{{ item.label }}</button
      >
    </div>
    <section class="records-filters" aria-label="筛选订单记录">
      <label class="records-filter records-search"
        ><span>搜索</span><input v-model="search" type="search" placeholder="标的、订单号、成交号"
      /></label>
      <label v-if="hasAction" class="records-filter records-filter--compact"
        ><span>开仓 / 平仓</span>
        <select v-model="actionFilter" aria-label="开仓 / 平仓"
          ><option value="">全部操作</option
          ><option value="open">开仓</option
          ><option value="close">平仓</option
          ><option value="reverse">反向开平</option
          ><option value="risk_reduction">异常处理</option
          ><option value="unknown">开平待核对</option
          ><option v-if="currentSection.rows.some((r) => r._action === 'mixed')" value="mixed"
            >多项操作</option
          ></select
        >
      </label>
      <label v-if="venueOptions.length" class="records-filter records-filter--compact"
        ><span>场所</span>
        <select v-model="venueFilter" aria-label="场所"
          ><option value="">全部场所</option
          ><option v-for="item in venueOptions" :key="item">{{ item }}</option></select
        >
      </label>
      <label v-if="statusOptions.length" class="records-filter records-filter--compact"
        ><span>状态</span>
        <select v-model="statusFilter" aria-label="订单状态"
          ><option value="">全部状态</option
          ><option v-for="item in statusOptions" :key="item">{{ item }}</option></select
        >
      </label>
      <template v-if="hasTime">
        <label class="records-filter records-filter--compact"
          ><span>开始日期 · 北京时间</span><input v-model="startDate" type="date"
        /></label>
        <label class="records-filter records-filter--compact"
          ><span>结束日期 · 北京时间</span><input v-model="endDate" type="date" :min="startDate"
        /></label>
      </template>
    </section>
    <p v-if="error" class="records-summary cell-warning" role="alert">{{ error }}</p>
    <div class="records-summary" aria-live="polite" :aria-busy="loading">
      <span v-if="loading">正在读取记录…</span>
      <span
        >显示 <strong>{{ filteredRows.length }}</strong> / {{ currentSection.rows.length }} 条</span
      >
      <span v-if="hasAction"
        >开仓 {{ filteredRows.filter((r) => r._action === 'open').length }} · 平仓
        {{ filteredRows.filter((r) => r._action === 'close').length }}</span
      >
      <span v-if="timeWarnings" class="cell-warning"
        >{{ timeWarnings }} 条时间待核对，可展开查看依据</span
      >
      <span v-if="startDate && endDate && startDate > endDate" class="cell-warning"
        >开始日期不能晚于结束日期</span
      >
    </div>
    <div class="records-table">
      <table>
        <thead
          ><tr
            ><th v-for="column in currentColumns" :key="column.key" scope="col">{{
              column.label
            }}</th
            ><th scope="col">详情</th></tr
          ></thead
        >
        <tbody>
          <template v-for="(row, index) in pagedRows" :key="rowKey(row, index)">
            <tr :class="{ 'is-expanded': expanded === rowKey(row, index) }">
              <td v-for="column in currentColumns" :key="column.key">
                <span
                  :class="[
                    cellClass(row[column.key] || '--'),
                    {
                      'action-badge': column.key === 'action',
                      'action-close': column.key === 'action' && row._action === 'close',
                    },
                  ]"
                  >{{ row[column.key] || '--' }}</span
                >
                <small
                  v-if="column.key === 'time' && row.timeLabel"
                  class="cell-note"
                  :class="{ 'cell-warning': row.timeWarning }"
                  >{{ row.timeLabel
                  }}<template v-if="row.timeWarning"> · {{ row.timeWarning }}</template></small
                >
              </td>
              <td
                ><button
                  v-if="detailFor(row).fields.length || detailFor(row).sections?.length"
                  type="button"
                  class="detail-toggle"
                  :aria-expanded="expanded === rowKey(row, index)"
                  @click="expanded = expanded === rowKey(row, index) ? '' : rowKey(row, index)"
                  >{{ expanded === rowKey(row, index) ? '收起' : '展开' }}</button
                ><span v-else class="cell-muted">—</span></td
              >
            </tr>
            <tr v-if="expanded === rowKey(row, index)" class="records-detail"
              ><td :colspan="currentColumns.length + 1">
                <dl class="detail-fields"
                  ><div v-for="(item, fieldIndex) in detailFor(row).fields" :key="fieldIndex"
                    ><dt>{{ item.label }}</dt
                    ><dd>{{ item.value }}</dd></div
                  ></dl
                >
                <section
                  v-for="section in detailFor(row).sections || []"
                  :key="section.title"
                  class="detail-section"
                >
                  <h4
                    >{{ section.title }} <span>{{ section.rows.length }} 笔</span></h4
                  >
                  <div class="records-table"
                    ><table
                      ><thead
                        ><tr
                          ><th v-for="column in section.columns" :key="column.key">{{
                            column.label
                          }}</th></tr
                        ></thead
                      >
                      <tbody
                        ><tr
                          v-for="(child, childIndex) in section.rows"
                          :key="child._key || childIndex"
                          ><td v-for="column in section.columns" :key="column.key"
                            ><span>{{ child[column.key] || '--' }}</span
                            ><small
                              v-if="column.key === 'time' && child.timeLabel"
                              class="cell-note"
                              :class="{ 'cell-warning': child.timeWarning }"
                              >{{ child.timeLabel
                              }}<template v-if="child.timeWarning">
                                · {{ child.timeWarning }}</template
                              ></small
                            ></td
                          ></tr
                        ><tr v-if="!section.rows.length"
                          ><td :colspan="section.columns.length" class="records-empty"
                            >暂无记录</td
                          ></tr
                        ></tbody
                      >
                    </table></div
                  >
                </section>
              </td></tr
            >
          </template>
          <tr v-if="!pagedRows.length"
            ><td :colspan="currentColumns.length + 1" class="records-empty">{{
              loading
                ? '记录加载中…'
                : error
                ? '记录读取失败，请刷新后重试'
                : !currentSection.rows.length && currentSection.emptyMessage
                ? currentSection.emptyMessage
                : '当前筛选条件下暂无记录'
            }}</td></tr
          >
        </tbody>
      </table>
    </div>
    <footer class="records-pagination"
      ><span>第 {{ currentPage }} / {{ totalPages }} 页</span>
      <div class="records-pagination__actions"
        ><label
          >每页
          <select v-model.number="pageSize" aria-label="每页条数"
            ><option :value="10">10</option
            ><option :value="20">20</option
            ><option :value="50">50</option></select
          >
          条</label
        ><button type="button" :disabled="currentPage <= 1" @click="currentPage -= 1">上一页</button
        ><button type="button" :disabled="currentPage >= totalPages" @click="currentPage += 1"
          >下一页</button
        ></div
      >
    </footer>
  </article>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import type { StrategyTableSection, StrategyTableTab } from '@/data/sample/strategy';
  import { recordMatches } from '../composables/strategyTradeRecords';
  const props = defineProps<{
    tabs: StrategyTableTab[];
    activeTab: string;
    tables: Record<string, StrategyTableSection>;
    compact?: boolean;
    loading?: boolean;
    error?: string;
  }>();
  defineEmits<{ (e: 'update:activeTab', value: string): void }>();
  const currentSection = computed<StrategyTableSection>(
    () => props.tables[props.activeTab] ?? { columns: [], rows: [] },
  );
  const identityColumns = computed(() =>
    currentSection.value.columns.filter((c) =>
      [
        'orderId',
        'fillId',
        'instructionId',
        'batchId',
        'eventId',
        'planId',
        'ticket',
        'commandId',
      ].includes(c.key),
    ),
  );
  const currentColumns = computed(() =>
    currentSection.value.columns.filter((c) => !identityColumns.value.includes(c)),
  );
  const startDate = ref(''),
    endDate = ref(''),
    statusFilter = ref(''),
    actionFilter = ref(''),
    venueFilter = ref(''),
    search = ref(''),
    expanded = ref('');
  const pageSize = ref(10),
    currentPage = ref(1);
  const options = (key: string) =>
    Array.from(
      new Set(
        currentSection.value.rows.map((row) => row[key]).filter((value) => value && value !== '--'),
      ),
    );
  const statusOptions = computed(() => options('status'));
  const venueOptions = computed(() => options('venue'));
  const hasAction = computed(() => currentSection.value.columns.some((c) => c.key === 'action'));
  const hasTime = computed(() =>
    currentSection.value.columns.some((c) => /time$|^date$/i.test(c.key)),
  );
  const filteredRows = computed(() =>
    currentSection.value.rows.filter((row) =>
      recordMatches(row, {
        startDate: startDate.value,
        endDate: endDate.value,
        action: actionFilter.value,
        status: statusFilter.value,
        venue: venueFilter.value,
        search: search.value,
      }),
    ),
  );
  const timeWarnings = computed(() => filteredRows.value.filter((r) => r.timeWarning).length);
  const totalPages = computed(() =>
    Math.max(1, Math.ceil(filteredRows.value.length / pageSize.value)),
  );
  const pagedRows = computed(() =>
    filteredRows.value.slice(
      (currentPage.value - 1) * pageSize.value,
      currentPage.value * pageSize.value,
    ),
  );
  const rowKey = (row: Record<string, string>, index: number) =>
    row._key || `${props.activeTab}-${(currentPage.value - 1) * pageSize.value + index}`;
  function detailFor(
    row: Record<string, string>,
  ): NonNullable<StrategyTableSection['details']>[string] {
    return (
      currentSection.value.details?.[row._key] || {
        fields: identityColumns.value.map((column) => ({
          label: column.label,
          value: row[column.key] || '--',
        })),
      }
    );
  }
  watch(
    () => [
      startDate.value,
      endDate.value,
      statusFilter.value,
      actionFilter.value,
      venueFilter.value,
      search.value,
      pageSize.value,
    ],
    () => {
      currentPage.value = 1;
      expanded.value = '';
    },
  );
  watch(() => props.activeTab, resetFilters);
  watch(totalPages, (value) => {
    if (currentPage.value > value) currentPage.value = value;
  });
  function resetFilters() {
    startDate.value = '';
    endDate.value = '';
    statusFilter.value = '';
    actionFilter.value = '';
    venueFilter.value = '';
    search.value = '';
    currentPage.value = 1;
    expanded.value = '';
  }
  function cellClass(value: string) {
    if (!value || value === '--') return 'cell-muted';
    if (['结果未知', '需人工处理', '有异常委托', '开平待核对'].includes(value))
      return 'cell-warning';
    if (['已拒绝', '失败', '已撤单'].includes(value)) return 'cell-negative';
    if (['已成交', '已完成', '委托均已成交'].includes(value)) return 'cell-positive';
    return '';
  }
</script>
<style scoped lang="less">
  .records-card {
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .records-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 16px 10px;
    gap: 16px;
  }

  .records-head h3 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-section-title);
    font-weight: 800;
    letter-spacing: 0.01em;
  }

  .records-head__meta {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .records-total {
    display: none;
  }

  .refresh-btn {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
    cursor: pointer;
  }

  .records-filters {
    display: flex;
    flex-wrap: wrap;
    gap: var(--strategy-space-2);
    padding: 14px 16px;
    border-bottom: 1px solid var(--strategy-border-soft);
    background: var(--strategy-table-head-bg);
  }

  .records-filter {
    display: flex;
    flex-direction: column;
    gap: 6px;
    min-width: 160px;
  }

  .records-filter--compact {
    min-width: 120px;
  }

  .records-filter span {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
  }

  .records-filter input,
  .records-filter select {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
  }

  .records-tabs {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0 16px;
    padding: 5px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-card);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
  }

  .records-tabs button {
    height: var(--strategy-tab-height);
    padding: 0 16px;
    border: none;
    background: transparent;
    border-radius: var(--strategy-radius-control);
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    cursor: pointer;
  }

  .records-tabs .is-active {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    font-weight: 800;
    box-shadow: inset 0 0 0 1px var(--strategy-accent-ring);
  }

  .records-table {
    overflow-x: auto;
  }

  .records-table table {
    width: 100%;
    min-width: 920px;
    border-collapse: collapse;
  }

  .records-table th,
  .records-table td {
    padding: 12px 14px;
    border-bottom: 1px solid var(--strategy-border-soft);
    white-space: nowrap;
    text-align: left;
  }

  .records-table th {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-base);
    font-weight: 700;
    background: var(--strategy-table-head-bg);
  }

  .records-table td {
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-base);
    font-weight: 500;
  }

  .records-empty {
    color: #8a97ab;
    text-align: center !important;
  }

  .records-pagination {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px 16px 16px;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
  }

  .records-pagination__actions {
    display: flex;
    gap: 8px;
  }

  .records-pagination__actions button {
    height: var(--strategy-control-height);
    padding: 0 var(--strategy-space-2);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
    box-shadow: var(--strategy-shadow-soft);
    cursor: pointer;
  }

  .records-pagination__actions button:disabled {
    color: #b5bfcd;
    cursor: not-allowed;
  }

  .cell-positive {
    color: var(--strategy-success);
    font-weight: 700;
  }

  .cell-negative {
    color: var(--strategy-danger);
    font-weight: 700;
  }

  .cell-muted {
    color: var(--strategy-text-faint);
  }

  .cell-identity {
    display: inline-block;
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    vertical-align: middle;
  }

  @media (max-width: 860px) {
    .records-head,
    .records-pagination {
      flex-direction: column;
      align-items: flex-start;
    }
  }

  .records-description {
    margin: 7px 0 0;
    color: var(--strategy-text-3);
    font-size: 12px;
    line-height: 1.65;
    max-width: 760px;
  }
  .records-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    padding: 12px 16px;
    color: var(--strategy-text-3);
    font-size: 12px;
  }
  .records-summary strong {
    color: var(--strategy-text-1);
  }
  .records-search {
    flex: 1;
    min-width: 200px;
    max-width: 360px;
  }
  .records-filter--compact {
    min-width: 110px;
  }
  .cell-note {
    display: block;
    font-size: 11px;
    line-height: 1.7;
    color: var(--strategy-text-3);
    font-weight: 400;
  }
  .cell-warning {
    color: #a16207;
  }
  .action-badge {
    display: inline-block;
    padding: 3px 8px;
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    border-radius: 5px;
    font-weight: 600;
  }
  .action-close {
    background: #fff7ed;
    color: #9a3412;
  }
  .detail-toggle {
    border: 0;
    background: transparent;
    color: var(--strategy-accent-strong);
    cursor: pointer;
    padding: 6px 4px;
  }
  .records-detail > td {
    padding: 18px !important;
    background: var(--strategy-table-head-bg);
    white-space: normal;
  }
  .detail-fields {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px 28px;
    margin: 0;
  }
  .detail-fields dt {
    color: var(--strategy-text-3);
    font-size: 11px;
    margin-bottom: 4px;
  }
  .detail-fields dd {
    margin: 0;
    font-size: 12px;
    font-weight: 400;
    overflow-wrap: anywhere;
    white-space: normal;
    user-select: text;
  }
  .detail-section {
    margin-top: 20px;
  }
  .detail-section h4 {
    margin: 0 0 10px;
    color: var(--strategy-text-1);
  }
  .detail-section h4 span {
    margin-left: 10px;
    font-size: 11px;
    color: var(--strategy-text-3);
    font-weight: 400;
  }
  .detail-section table {
    background: var(--strategy-surface);
  }
  .is-expanded {
    background: var(--strategy-accent-soft);
  }
  button:focus-visible,
  input:focus-visible,
  select:focus-visible {
    outline: 2px solid var(--strategy-accent-strong);
    outline-offset: 2px;
  }
  .records-pagination__actions {
    align-items: center;
  }
  .records-pagination select {
    padding: 6px;
    border: 1px solid var(--strategy-border);
    border-radius: 5px;
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
  }
</style>
