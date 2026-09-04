<template>
  <section class="market-terminal__detail">
    <div class="market-terminal__panel-head market-terminal__panel-head--detail">
      <div class="market-terminal__detail-actions">
        <button type="button" class="market-terminal__toolbar-btn" @click="toggleEditMode">
          {{ editMode ? '完成编辑' : '编辑标的' }}
        </button>
        <button
          v-if="editMode"
          type="button"
          class="market-terminal__toolbar-btn"
          @click="openAddForm"
        >
          添加标的
        </button>
        <button
          v-if="editMode && hasSavedOverrides"
          type="button"
          class="market-terminal__toolbar-btn is-danger"
          @click="resetGroups"
        >
          恢复默认
        </button>
      </div>
    </div>

    <div v-if="editMode" class="market-terminal__editor-tip">
      当前为本地编辑模式。你可以添加、删除、上下排序，刷新后仍会保留在当前浏览器。
    </div>

    <section v-if="editMode && addFormVisible" class="market-terminal__editor-card">
      <div class="market-terminal__editor-grid">
        <label class="market-terminal__editor-field">
          <span>所属分组</span>
          <select v-model="addForm.groupLabel">
            <option v-for="group in editableGroups" :key="group.label" :value="group.label">
              {{ group.label }}
            </option>
          </select>
        </label>

        <label class="market-terminal__editor-field">
          <span>名称</span>
          <input v-model.trim="addForm.name" type="text" placeholder="例如：比特币" />
        </label>

        <label class="market-terminal__editor-field">
          <span>代码</span>
          <input
            v-model.trim="addForm.symbol"
            type="text"
            placeholder="例如：BTCUSD / SPY / 000300"
          />
        </label>

        <label class="market-terminal__editor-field market-terminal__editor-field--wide">
          <span>TradingView 代码</span>
          <input
            v-model.trim="addForm.tvSymbol"
            type="text"
            placeholder="例如：COINBASE:BTCUSD，可留空"
          />
        </label>
      </div>

      <div class="market-terminal__editor-actions">
        <button type="button" class="market-terminal__toolbar-btn" @click="submitAddRow">
          保存新增
        </button>
        <button type="button" class="market-terminal__toolbar-btn" @click="closeAddForm">
          取消
        </button>
      </div>
    </section>

    <div class="market-terminal__table-shell">
      <table class="market-terminal__table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column.key" :class="alignClass(column.align)">
              <button
                v-if="isSortableColumn(column.key)"
                type="button"
                class="market-terminal__head-sort"
                :class="{ 'is-active': tableSortState?.key === column.key }"
                @click="toggleTableSort(column.key)"
              >
                <span>{{ column.label }}</span>
                <b>{{ sortIndicator(tableSortState, column.key) }}</b>
              </button>
              <span v-else>{{ column.label }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <template v-for="group in displayGroups" :key="group.label">
            <tr class="market-terminal__group-row">
              <td :colspan="columns.length">
                <div class="market-terminal__group-meta">
                  <button
                    type="button"
                    class="market-terminal__group-toggle"
                    @click="toggleGroup(group.label)"
                  >
                    <span>{{ isGroupExpanded(group.label) ? '▼' : '▶' }}</span>
                    {{ group.label }}
                  </button>
                  <span v-if="editMode" class="market-terminal__group-count"
                    >{{ group.rows.length }} 项</span
                  >
                </div>
              </td>
            </tr>

            <tr
              v-for="row in isGroupExpanded(group.label) ? sortedGroupRows(group) : []"
              :key="row.id"
              class="market-terminal__table-row"
            >
              <td class="market-terminal__name-cell">
                <button
                  v-if="canOpenTickerChart(row.symbol, row.tvSymbol)"
                  type="button"
                  class="market-terminal__ticker-button"
                  @click="openTickerChart(row.symbol, row.name, row.tvSymbol)"
                >
                  <div class="market-terminal__name-wrap">
                    <strong>{{ row.name }}</strong>
                    <span>{{ row.symbol }}</span>
                  </div>
                </button>
                <div v-else class="market-terminal__name-wrap">
                  <strong>{{ row.name }}</strong>
                  <span>{{ row.symbol }}</span>
                </div>

                <div v-if="editMode" class="market-terminal__row-tools">
                  <button
                    type="button"
                    class="market-terminal__row-tool"
                    @click="moveRow(group.label, row.id, 'up')"
                  >
                    上移
                  </button>
                  <button
                    type="button"
                    class="market-terminal__row-tool"
                    @click="moveRow(group.label, row.id, 'down')"
                  >
                    下移
                  </button>
                  <button
                    type="button"
                    class="market-terminal__row-tool is-danger"
                    @click="removeRow(group.label, row.id)"
                  >
                    删除
                  </button>
                </div>
              </td>

              <td class="market-terminal__spark-cell is-center">
                <span
                  v-if="row.spark.length < 2"
                  class="market-terminal__spark-unavailable"
                  title="暂无可靠的 90 日历史数据"
                  >—</span
                >
                <button
                  v-else-if="canOpenTickerChart(row.symbol, row.tvSymbol)"
                  type="button"
                  class="market-terminal__spark-button"
                  @click="openTickerChart(row.symbol, row.name, row.tvSymbol)"
                >
                  <svg
                    class="market-terminal__sparkline"
                    viewBox="0 0 96 24"
                    preserveAspectRatio="none"
                  >
                    <polyline
                      :points="compactSparkline(row.spark, 96, 24)"
                      :class="sparkStrokeClass(row.d1)"
                    />
                  </svg>
                </button>
                <svg
                  v-else
                  class="market-terminal__sparkline"
                  viewBox="0 0 96 24"
                  preserveAspectRatio="none"
                >
                  <polyline
                    :points="compactSparkline(row.spark, 96, 24)"
                    :class="sparkStrokeClass(row.d1)"
                  />
                </svg>
              </td>

              <td class="is-right">{{ row.price }}</td>
              <td class="is-center"
                ><span class="market-chip" :class="chipTone(row.d1)">{{ row.d1 }}</span></td
              >
              <td class="is-center"
                ><span class="market-chip" :class="chipTone(row.ytd)">{{ row.ytd }}</span></td
              >
              <td class="is-center"
                ><span class="market-chip" :class="chipTone(row.qtd)">{{ row.qtd }}</span></td
              >
              <td class="is-center"
                ><span class="market-chip" :class="chipTone(row.w1)">{{ row.w1 }}</span></td
              >
              <td class="is-center"
                ><span class="market-chip" :class="chipTone(row.m1)">{{ row.m1 }}</span></td
              >
              <td class="is-center"
                ><span class="market-chip" :class="chipTone(row.y1)">{{ row.y1 }}</span></td
              >
              <td class="market-terminal__high-cell-td">
                <div class="market-terminal__high-cell">
                  <div class="market-terminal__high-track">
                    <i
                      :style="{ width: `${highWidth(row.high)}%` }"
                      :class="sparkStrokeClass(row.high)"
                    ></i>
                  </div>
                  <span :class="toneClass(parseTone(row.high))">{{ row.high }}</span>
                </div>
              </td>
              <td
                v-for="signalKey in signalColumnKeys"
                :key="`${row.id}-${signalKey}`"
                class="is-center"
                :class="arrowClass(String(row[signalKey]))"
              >
                {{ normalizeArrow(String(row[signalKey])) }}
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <section
      v-if="rotationButtonLabel && rotationHeatmap?.length"
      class="market-terminal__rotation"
    >
      <button type="button" class="market-terminal__rotation-button" @click="toggleRotation">
        <span>{{ rotationExpanded ? '▼' : '▶' }}</span>
        {{ rotationButtonLabel }}
      </button>

      <div v-if="rotationExpanded" class="market-terminal__rotation-heatmap">
        <table class="market-terminal__rotation-table">
          <thead>
            <tr>
              <th>
                <button
                  type="button"
                  class="market-terminal__rotation-sort"
                  :class="{ 'is-active': rotationSortState?.key === 'symbol' }"
                  @click="toggleRotationSort('symbol')"
                >
                  <span>板块</span>
                  <b>{{ sortIndicator(rotationSortState, 'symbol') }}</b>
                </button>
              </th>
              <th v-for="column in rotationColumns" :key="column.key">
                <button
                  type="button"
                  class="market-terminal__rotation-sort"
                  :class="{ 'is-active': rotationSortState?.key === column.key }"
                  @click="toggleRotationSort(column.key)"
                >
                  <span>{{ column.label }}</span>
                  <b>{{ sortIndicator(rotationSortState, column.key) }}</b>
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sortedRotationRows" :key="row.id">
              <td class="market-terminal__rotation-name">
                <strong>{{ row.symbol }}</strong>
                <span>{{ row.label }}</span>
              </td>
              <td :class="heatmapClass(row.d1)">{{ row.d1 }}</td>
              <td :class="heatmapClass(row.w1)">{{ row.w1 }}</td>
              <td :class="heatmapClass(row.m1)">{{ row.m1 }}</td>
              <td :class="heatmapClass(row.ytd)">{{ row.ytd }}</td>
              <td :class="heatmapClass(row.y1)">{{ row.y1 }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <Teleport to="body">
      <div
        v-if="chartModal.visible"
        class="market-terminal-chart-modal"
        @click.self="closeTickerChart"
      >
        <div class="market-terminal-chart-modal__dialog">
          <div class="market-terminal-chart-modal__header">
            <div>
              <p class="market-terminal-chart-modal__eyebrow">{{ chartModal.symbol }}</p>
              <h3>{{ chartModal.name || chartModal.symbol }} 走势图</h3>
            </div>
            <button
              type="button"
              class="market-terminal-chart-modal__close"
              @click="closeTickerChart"
            >
              关闭
            </button>
          </div>

          <div class="market-terminal-chart-modal__body">
            <div v-if="chartModal.error" class="market-terminal-chart-modal__state is-error">
              {{ chartModal.error }}
            </div>
            <div v-else-if="chartModal.loading" class="market-terminal-chart-modal__state">
              正在加载 {{ chartModal.symbol }} 的走势图...
            </div>
            <div
              ref="chartContainerRef"
              class="market-terminal-chart-modal__widget"
              :class="{ 'is-hidden': chartModal.loading }"
            ></div>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
  import type {
    RotationHeatmapRow,
    TerminalMarketId,
    TerminalTableColumn,
    TerminalTableGroup,
    TerminalTableRow,
    TerminalTone,
  } from '../nativeData/marketTerminal';

  interface ChartModalState {
    visible: boolean;
    loading: boolean;
    symbol: string;
    name: string;
    tvSymbol: string;
    error: string;
  }

  interface SortState {
    key: string;
    direction: 'desc' | 'asc';
  }

  interface AddFormState {
    groupLabel: string;
    name: string;
    symbol: string;
    tvSymbol: string;
  }

  const props = withDefaults(
    defineProps<{
      title?: string;
      columns: TerminalTableColumn[];
      groups: TerminalTableGroup[];
      marketId?: TerminalMarketId;
      rotationButtonLabel?: string;
      rotationHeatmap?: RotationHeatmapRow[];
    }>(),
    {
      title: '市场明细',
      marketId: 'us',
      rotationButtonLabel: '',
      rotationHeatmap: () => [],
    },
  );

  const STORAGE_PREFIX = 'vg_hedge_market_detail_';
  const signalColumnKeys = ['d10', 'd20', 'd50', 'd200', 'x2050'] as const;
  const rotationColumns = [
    { key: 'd1', label: '1D' },
    { key: 'w1', label: '1W' },
    { key: 'm1', label: '1M' },
    { key: 'ytd', label: 'YTD' },
    { key: 'y1', label: '1Y' },
  ] as const;

  const editableGroups = ref<TerminalTableGroup[]>([]);
  const expandedGroups = ref<Record<string, boolean>>({});
  const tableSortState = ref<SortState | null>(null);
  const rotationExpanded = ref(true);
  const rotationSortState = ref<SortState | null>(null);
  const editMode = ref(false);
  const addFormVisible = ref(false);
  const chartContainerRef = ref<HTMLDivElement | null>(null);
  const chartModal = ref<ChartModalState>({
    visible: false,
    loading: false,
    symbol: '',
    name: '',
    tvSymbol: '',
    error: '',
  });
  const addForm = ref<AddFormState>({
    groupLabel: '',
    name: '',
    symbol: '',
    tvSymbol: '',
  });

  let tradingViewScriptPromise: Promise<void> | null = null;

  const storageKey = computed(() => `${STORAGE_PREFIX}${props.marketId}`);
  const hasSavedOverrides = computed(() => {
    if (typeof window === 'undefined') return false;
    return Boolean(window.localStorage.getItem(storageKey.value));
  });

  const displayGroups = computed<TerminalTableGroup[]>(() => editableGroups.value);

  const sortedRotationRows = computed(() => {
    const rows = [...props.rotationHeatmap];
    const state = rotationSortState.value;
    if (!state) return rows;
    return rows.sort((left, right) =>
      compareValues(
        readRotationValue(left, state.key),
        readRotationValue(right, state.key),
        state.direction,
      ),
    );
  });

  watch(
    () => [props.groups, props.marketId] as const,
    () => {
      hydrateGroups();
    },
    { immediate: true, deep: true },
  );

  function hydrateGroups() {
    const fallbackGroups = cloneGroups(props.groups);
    const savedGroups = readSavedGroups();
    editableGroups.value = savedGroups ?? fallbackGroups;
    expandedGroups.value = Object.fromEntries(
      editableGroups.value.map((group) => [group.label, true]),
    );
    if (!addForm.value.groupLabel) {
      addForm.value.groupLabel = editableGroups.value[0]?.label || '';
    }
  }

  function cloneGroups(groups: TerminalTableGroup[]) {
    return groups.map((group) => ({
      label: group.label,
      rows: group.rows.map((row) => ({
        ...row,
        spark: [...row.spark],
      })),
    }));
  }

  function readSavedGroups() {
    if (typeof window === 'undefined') return null;
    const raw = window.localStorage.getItem(storageKey.value);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return null;
      return parsed.map(normalizeGroup).filter(Boolean) as TerminalTableGroup[];
    } catch {
      return null;
    }
  }

  function normalizeGroup(group: any): TerminalTableGroup | null {
    if (!group || typeof group.label !== 'string' || !Array.isArray(group.rows)) return null;
    return {
      label: group.label,
      rows: group.rows
        .map((row: any, index: number) => normalizeRow(group.label, row, index))
        .filter(Boolean) as TerminalTableRow[],
    };
  }

  function normalizeRow(groupLabel: string, row: any, index: number): TerminalTableRow | null {
    if (!row || typeof row.name !== 'string' || typeof row.symbol !== 'string') return null;
    const spark =
      Array.isArray(row.spark) && row.spark.length
        ? row.spark.map(Number)
        : buildPlaceholderSpark(row.symbol, index);
    return {
      id:
        typeof row.id === 'string'
          ? row.id
          : `${props.marketId}-${groupLabel}-${row.symbol}-${index}`,
      name: row.name,
      symbol: row.symbol,
      tvSymbol: typeof row.tvSymbol === 'string' ? row.tvSymbol : '',
      spark,
      price: typeof row.price === 'string' ? row.price : '0.00',
      d1: typeof row.d1 === 'string' ? row.d1 : '+0.00%',
      ytd: typeof row.ytd === 'string' ? row.ytd : '+0.00%',
      qtd: typeof row.qtd === 'string' ? row.qtd : '+0.00%',
      w1: typeof row.w1 === 'string' ? row.w1 : '+0.00%',
      m1: typeof row.m1 === 'string' ? row.m1 : '+0.00%',
      y1: typeof row.y1 === 'string' ? row.y1 : '+0.00%',
      high: typeof row.high === 'string' ? row.high : '0.0%',
      d10: typeof row.d10 === 'string' ? row.d10 : '▲',
      d20: typeof row.d20 === 'string' ? row.d20 : '▲',
      d50: typeof row.d50 === 'string' ? row.d50 : '▲',
      d200: typeof row.d200 === 'string' ? row.d200 : '▲',
      x2050: typeof row.x2050 === 'string' ? row.x2050 : '▲',
      x50200: typeof row.x50200 === 'string' ? row.x50200 : '▲',
    };
  }

  function persistGroups() {
    if (typeof window === 'undefined') return;
    window.localStorage.setItem(storageKey.value, JSON.stringify(editableGroups.value));
  }

  function toggleEditMode() {
    editMode.value = !editMode.value;
    if (!editMode.value) {
      addFormVisible.value = false;
    }
  }

  function openAddForm() {
    addFormVisible.value = true;
    addForm.value = {
      groupLabel: editableGroups.value[0]?.label || '',
      name: '',
      symbol: '',
      tvSymbol: '',
    };
  }

  function closeAddForm() {
    addFormVisible.value = false;
  }

  function submitAddRow() {
    const groupLabel = addForm.value.groupLabel.trim();
    const name = addForm.value.name.trim();
    const symbol = addForm.value.symbol.trim();
    if (!groupLabel || !name || !symbol) return;

    const targetGroup = editableGroups.value.find((group) => group.label === groupLabel);
    if (!targetGroup) return;

    targetGroup.rows.push({
      id: `${props.marketId}-${symbol}-${Date.now()}`,
      name,
      symbol,
      tvSymbol: addForm.value.tvSymbol.trim(),
      spark: buildPlaceholderSpark(symbol, targetGroup.rows.length),
      price: '0.00',
      d1: '+0.00%',
      ytd: '+0.00%',
      qtd: '+0.00%',
      w1: '+0.00%',
      m1: '+0.00%',
      y1: '+0.00%',
      high: '0.0%',
      d10: '▲',
      d20: '▲',
      d50: '▲',
      d200: '▲',
      x2050: '▲',
      x50200: '▲',
    });

    persistGroups();
    closeAddForm();
  }

  function removeRow(groupLabel: string, rowId: string) {
    const group = editableGroups.value.find((item) => item.label === groupLabel);
    if (!group) return;
    group.rows = group.rows.filter((row) => row.id !== rowId);
    persistGroups();
  }

  function moveRow(groupLabel: string, rowId: string, direction: 'up' | 'down') {
    const group = editableGroups.value.find((item) => item.label === groupLabel);
    if (!group) return;
    const currentIndex = group.rows.findIndex((row) => row.id === rowId);
    if (currentIndex === -1) return;
    const nextIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    if (nextIndex < 0 || nextIndex >= group.rows.length) return;
    const [current] = group.rows.splice(currentIndex, 1);
    group.rows.splice(nextIndex, 0, current);
    persistGroups();
  }

  function resetGroups() {
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem(storageKey.value);
    }
    editableGroups.value = cloneGroups(props.groups);
    expandedGroups.value = Object.fromEntries(
      editableGroups.value.map((group) => [group.label, true]),
    );
    addFormVisible.value = false;
  }

  function toggleGroup(label: string) {
    expandedGroups.value[label] = !expandedGroups.value[label];
  }

  function isGroupExpanded(label: string) {
    return expandedGroups.value[label] ?? true;
  }

  function toggleTableSort(key: string) {
    const current = tableSortState.value;
    if (!current || current.key !== key) {
      tableSortState.value = { key, direction: 'desc' };
      return;
    }
    if (current.direction === 'desc') {
      tableSortState.value = { key, direction: 'asc' };
      return;
    }
    tableSortState.value = null;
  }

  function toggleRotation() {
    rotationExpanded.value = !rotationExpanded.value;
  }

  function toggleRotationSort(key: string) {
    const current = rotationSortState.value;
    if (!current || current.key !== key) {
      rotationSortState.value = { key, direction: 'desc' };
      return;
    }
    if (current.direction === 'desc') {
      rotationSortState.value = { key, direction: 'asc' };
      return;
    }
    rotationSortState.value = null;
  }

  function sortIndicator(state: SortState | null | undefined, key: string) {
    if (!state || state.key !== key) return '↕';
    return state.direction === 'desc' ? '↓' : '↑';
  }

  function sortedGroupRows(group: TerminalTableGroup) {
    const rows = [...group.rows];
    const state = tableSortState.value;
    if (!state) return rows;
    return rows.sort((left, right) =>
      compareValues(
        readTableValue(left, state.key),
        readTableValue(right, state.key),
        state.direction,
      ),
    );
  }

  function isSortableColumn(key: string) {
    return key !== 'spark';
  }

  function readTableValue(row: TerminalTableRow, key: string) {
    if (key === 'name') return row.name;
    if (key === 'symbol') return row.symbol;
    if (key === 'price') return parseDisplayNumber(row.price);
    if (key === 'high') return parseDisplayNumber(row.high);
    if (['d1', 'ytd', 'qtd', 'w1', 'm1', 'y1'].includes(key))
      return parseDisplayNumber(row[key as keyof TerminalTableRow] as string);
    if (['d10', 'd20', 'd50', 'd200', 'x2050'].includes(key))
      return arrowScore(row[key as keyof TerminalTableRow] as string);
    return String(row[key as keyof TerminalTableRow] ?? '');
  }

  function readRotationValue(row: RotationHeatmapRow, key: string) {
    if (key === 'symbol') return `${row.symbol} ${row.label}`;
    return parseDisplayNumber(row[key as keyof RotationHeatmapRow] as string);
  }

  function compareValues(left: string | number, right: string | number, direction: 'desc' | 'asc') {
    const multiplier = direction === 'desc' ? -1 : 1;
    if (typeof left === 'number' && typeof right === 'number') {
      return (left - right) * multiplier;
    }
    return String(left).localeCompare(String(right), 'zh-Hans-CN') * multiplier;
  }

  function parseDisplayNumber(value: string) {
    const normalized = value.replace(/,/g, '').replace('%', '').trim().toUpperCase();
    if (normalized.endsWith('T')) return Number.parseFloat(normalized) * 1_000_000_000_000;
    if (normalized.endsWith('B')) return Number.parseFloat(normalized) * 1_000_000_000;
    if (normalized.endsWith('M')) return Number.parseFloat(normalized) * 1_000_000;
    return Number.parseFloat(normalized);
  }

  function arrowScore(value: string) {
    return parseTone(value) === 'negative' ? -1 : 1;
  }

  function parseTone(value: string): TerminalTone {
    return value.trim().startsWith('-') || value.includes('▼') ? 'negative' : 'positive';
  }

  function toneClass(tone?: TerminalTone) {
    return tone ? `is-${tone}` : '';
  }

  function chipTone(value: string) {
    return parseTone(value) === 'negative' ? 'is-down' : 'is-up';
  }

  function normalizeArrow(value: string) {
    return parseTone(value) === 'negative' ? '▼' : '▲';
  }

  function arrowClass(value: string) {
    return parseTone(value) === 'negative' ? 'is-arrow-down' : 'is-arrow-up';
  }

  function heatmapClass(value: string) {
    return [
      'market-terminal__rotation-cell',
      parseTone(value) === 'negative' ? 'is-negative-cell' : 'is-positive-cell',
    ];
  }

  function alignClass(align?: 'left' | 'right' | 'center') {
    if (align === 'right') return 'is-right';
    if (align === 'center') return 'is-center';
    return '';
  }

  function compactSparkline(series: number[], width: number, height: number) {
    const min = Math.min(...series);
    const max = Math.max(...series);

    return series
      .map((value, index) => {
        const x = (index / Math.max(series.length - 1, 1)) * width;
        const y =
          max === min ? height / 2 : height - 1 - ((value - min) / (max - min)) * (height - 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }

  function buildPlaceholderSpark(seed: string, offset: number) {
    const base =
      Array.from(seed).reduce((total, char) => total + char.charCodeAt(0), 0) + offset * 3;
    return Array.from({ length: 24 }, (_, index) => 10 + ((base + index * 7) % 12));
  }

  function sparkStrokeClass(value: string) {
    return parseTone(value) === 'negative' ? 'is-stroke-down' : 'is-stroke-up';
  }

  function highWidth(value: string) {
    const numeric = Number.parseFloat(value.replace('%', ''));
    const distance = Number.isFinite(numeric) ? Math.abs(numeric) : 0;
    return Math.max(36, Math.min(100, 100 - distance * 1.35));
  }

  const GLOBAL_TICKER_TO_TV_SYMBOL: Record<string, string> = {
    EWA: 'AMEX:EWA',
    EWC: 'AMEX:EWC',
    EWQ: 'AMEX:EWQ',
    EWG: 'AMEX:EWG',
    EWH: 'AMEX:EWH',
    EWI: 'AMEX:EWI',
    EWJ: 'AMEX:EWJ',
    EWN: 'AMEX:EWN',
    EWS: 'AMEX:EWS',
    EWP: 'AMEX:EWP',
    EWL: 'AMEX:EWL',
    EWU: 'AMEX:EWU',
    ARGT: 'AMEX:ARGT',
    EWZ: 'AMEX:EWZ',
    ECH: 'AMEX:ECH',
    MCHI: 'NASDAQ:MCHI',
    INDA: 'BATS:INDA',
    EIDO: 'AMEX:EIDO',
    EWM: 'AMEX:EWM',
    EWW: 'AMEX:EWW',
    EPHE: 'AMEX:EPHE',
    EPOL: 'AMEX:EPOL',
    RSX: 'AMEX:RSX',
    EZA: 'AMEX:EZA',
    EWY: 'AMEX:EWY',
    EWT: 'AMEX:EWT',
    THD: 'AMEX:THD',
    TUR: 'AMEX:TUR',
    VNM: 'AMEX:VNM',
    EFA: 'AMEX:EFA',
    EEM: 'AMEX:EEM',
    IEMG: 'NASDAQ:IEMG',
    VEA: 'AMEX:VEA',
    VWO: 'AMEX:VWO',
    VIGI: 'NYSEARCA:VIGI',
    AIA: 'NASDAQ:AIA',
  };
  function resolveTradingViewSymbol(marketId: TerminalMarketId, symbol: string, tvSymbol?: string) {
    if (tvSymbol) return tvSymbol;
    const normalized = symbol.trim().toUpperCase();
    if (marketId === 'global') {
      return GLOBAL_TICKER_TO_TV_SYMBOL[normalized] ?? '';
    }
    return '';
  }

  function canOpenTickerChart(symbol: string, tvSymbol?: string) {
    return Boolean(resolveTradingViewSymbol(props.marketId, symbol, tvSymbol));
  }

  async function ensureTradingViewScript() {
    if (typeof window === 'undefined') return;
    if (window.document.querySelector('script[data-tv-advanced-chart-script="true"]')) return;

    if (!tradingViewScriptPromise) {
      tradingViewScriptPromise = new Promise<void>((resolve, reject) => {
        const script = window.document.createElement('script');
        script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
        script.async = true;
        script.dataset.tvAdvancedChartScript = 'true';
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('TradingView 脚本加载失败'));
        window.document.head.appendChild(script);
      });
    }

    return tradingViewScriptPromise;
  }

  async function renderTradingViewChart(tvSymbol: string) {
    await nextTick();
    const host = chartContainerRef.value;
    if (!host) return;

    host.innerHTML = '';

    const container = document.createElement('div');
    container.className = 'tradingview-widget-container';

    const widget = document.createElement('div');
    widget.className = 'tradingview-widget-container__widget';

    const script = document.createElement('script');
    script.type = 'text/javascript';
    script.async = true;
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.text = JSON.stringify({
      autosize: true,
      symbol: tvSymbol,
      interval: 'D',
      timezone: 'Asia/Shanghai',
      theme: 'light',
      style: '1',
      locale: 'zh_CN',
      allow_symbol_change: true,
      calendar: false,
      support_host: 'https://www.tradingview.com',
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
      details: false,
      studies: ['Volume@tv-basicstudies'],
      withdateranges: true,
      range: '30D',
      backgroundColor: '#f7fafc',
      gridColor: 'rgba(101, 119, 139, 0.12)',
    });

    container.appendChild(widget);
    container.appendChild(script);
    host.appendChild(container);
  }

  async function openTickerChart(symbol: string, name: string, tvSymbolOverride?: string) {
    const tvSymbol = resolveTradingViewSymbol(props.marketId, symbol, tvSymbolOverride);
    if (!tvSymbol) return;

    chartModal.value = {
      visible: true,
      loading: true,
      symbol,
      name,
      tvSymbol,
      error: '',
    };

    try {
      await ensureTradingViewScript();
      await renderTradingViewChart(tvSymbol);
      chartModal.value.loading = false;
    } catch (error) {
      chartModal.value.loading = false;
      chartModal.value.error = error instanceof Error ? error.message : '图表加载失败';
    }
  }

  function closeTickerChart() {
    chartModal.value.visible = false;
    chartModal.value.loading = false;
    chartModal.value.error = '';

    if (chartContainerRef.value) {
      chartContainerRef.value.innerHTML = '';
    }
  }

  onBeforeUnmount(() => {
    if (chartContainerRef.value) {
      chartContainerRef.value.innerHTML = '';
    }
  });
</script>

<style lang="less" scoped>
  .market-terminal__detail,
  .market-terminal__rotation {
    padding: 12px;
    border: 1px solid rgb(201 213 226 / 72%);
    border-radius: 18px;
    background: linear-gradient(180deg, rgb(255 255 255 / 98%), rgb(243 248 252 / 96%)), #fff;
    box-shadow: 0 14px 28px rgb(15 23 42 / 4%);
  }

  .market-terminal__rotation {
    margin-top: 14px;
  }

  .market-terminal__panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .market-terminal__panel-head--detail {
    justify-content: flex-end;
    margin-bottom: 12px;
  }

  .market-terminal__detail-actions,
  .market-terminal__editor-actions,
  .market-terminal__row-tools {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .market-terminal__toolbar-btn,
  .market-terminal__row-tool {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 12px;
    border: 1px solid rgb(201 213 226 / 82%);
    border-radius: 999px;
    background: rgb(247 251 253 / 96%);
    color: #35586e;
    font-size: 12px;
    font-weight: 700;
  }

  .market-terminal__toolbar-btn.is-danger,
  .market-terminal__row-tool.is-danger {
    color: #c95b48;
  }

  .market-terminal__editor-tip {
    margin-bottom: 12px;
    padding: 10px 12px;
    border: 1px solid rgb(201 213 226 / 72%);
    border-radius: 12px;
    background: rgb(244 249 252 / 92%);
    color: #6e8395;
    font-size: 12px;
    line-height: 1.6;
  }

  .market-terminal__editor-card {
    margin-bottom: 12px;
    padding: 12px;
    border: 1px solid rgb(201 213 226 / 72%);
    border-radius: 14px;
    background: rgb(250 252 254 / 94%);
  }

  .market-terminal__editor-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 10px;
  }

  .market-terminal__editor-field {
    display: grid;
    gap: 6px;
  }

  .market-terminal__editor-field--wide {
    grid-column: span 3;
  }

  .market-terminal__editor-field span {
    color: #6e8395;
    font-size: 11px;
    font-weight: 700;
  }

  .market-terminal__editor-field input,
  .market-terminal__editor-field select {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid rgb(201 213 226 / 82%);
    border-radius: 10px;
    background: #fff;
    color: #18313c;
    font-size: 12px;
  }

  .market-terminal__table-shell,
  .market-terminal__rotation-heatmap {
    overflow-x: auto;
  }

  .market-terminal__table {
    width: 100%;
    min-width: 1400px;
    border-collapse: collapse;
    font-size: 12px;
  }

  .market-terminal__table th,
  .market-terminal__table td {
    padding: 10px;
    border-bottom: 1px solid rgb(201 213 226 / 52%);
  }

  .market-terminal__table th {
    color: #7b8ea0;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
  }

  .market-terminal__group-row td {
    padding: 10px;
    background: rgb(241 246 251 / 92%);
  }

  .market-terminal__group-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-start;
    gap: 12px;
  }

  .market-terminal__group-toggle,
  .market-terminal__rotation-button,
  .market-terminal__rotation-sort {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: none;
    background: transparent;
  }

  .market-terminal__group-toggle,
  .market-terminal__rotation-button {
    color: #18313c;
    font-size: 13px;
    font-weight: 700;
  }

  .market-terminal__group-count {
    color: #7b8ea0;
    font-size: 11px;
    font-weight: 700;
  }

  .market-terminal__head-sort {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    width: 100%;
    padding: 0;
    border: none;
    background: transparent;
    color: inherit;
    font: inherit;
  }

  .market-terminal__head-sort.is-active,
  .market-terminal__head-sort:hover {
    color: #35586e;
  }

  .market-terminal__rotation-sort {
    justify-content: center;
    width: 100%;
    padding: 6px 10px;
    border: 1px solid rgb(201 213 226 / 70%);
    border-radius: 999px;
    color: #73879a;
    font-size: 11px;
    font-weight: 700;
  }

  .market-terminal__rotation-sort.is-active,
  .market-terminal__rotation-sort:hover {
    border-color: rgb(96 125 159 / 56%);
    background: rgb(236 243 249 / 90%);
    color: #35586e;
  }

  .market-terminal__ticker-button,
  .market-terminal__spark-button {
    padding: 0;
    border: none;
    background: transparent;
  }

  .market-terminal__ticker-button {
    display: block;
    width: 100%;
    text-align: left;
  }

  .market-terminal__name-wrap {
    display: grid;
    gap: 4px;
  }

  .market-terminal__name-wrap strong {
    color: #18313c;
  }

  .market-terminal__name-wrap span {
    display: inline-flex;
    width: fit-content;
    padding: 2px 6px;
    border: 1px solid rgb(201 213 226 / 70%);
    border-radius: 6px;
    color: #73879a;
    font-size: 11px;
    font-weight: 700;
  }

  .market-terminal__row-tools {
    margin-top: 8px;
  }

  .market-terminal__row-tool {
    padding: 2px 8px;
    font-size: 11px;
  }

  .market-terminal__sparkline {
    width: 72px;
    height: 24px;
  }

  .market-terminal__sparkline polyline {
    stroke-width: 1.5;
    stroke-linecap: round;
    fill: none;
    stroke-linejoin: round;
  }

  .market-terminal__high-cell-td {
    padding-right: 12px;
    padding-left: 12px;
  }

  .market-terminal__high-cell {
    display: flex;
    position: relative;
    align-items: center;
    width: 100%;
    min-width: 136px;
    gap: 8px;
  }

  .market-terminal__high-track {
    flex: 1;
    width: 100%;
    min-width: 0;
    height: 4px;
    overflow: hidden;
    border-radius: 999px;
    background: rgb(148 163 184 / 18%);
  }

  .market-terminal__high-cell span {
    flex: 0 0 52px;
    width: 52px;
    text-align: right;
  }

  .market-terminal__high-track i {
    display: block;
    height: 100%;
  }

  .market-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 60px;
    padding: 4px 8px;
    border: 1px solid transparent;
    border-radius: 8px;
    background: transparent;
    font-weight: 700;
  }

  .market-chip.is-up {
    border-color: rgb(91 147 211 / 20%);
    background: rgb(91 147 211 / 12%);
    color: #5b93d3;
  }

  .market-chip.is-down {
    border-color: rgb(210 107 90 / 20%);
    background: rgb(210 107 90 / 12%);
    color: #d26b5a;
  }

  .market-terminal__rotation-table {
    width: 100%;
    min-width: 920px;
    margin-top: 12px;
    border-collapse: collapse;
  }

  .market-terminal__rotation-table th,
  .market-terminal__rotation-table td {
    padding: 10px 12px;
    border: 1px solid rgb(201 213 226 / 68%);
    font-size: 12px;
    text-align: center;
  }

  .market-terminal__rotation-name {
    text-align: left !important;
  }

  .market-terminal__rotation-name strong,
  .market-terminal__rotation-name span {
    display: block;
  }

  .market-terminal__rotation-name span {
    margin-top: 4px;
    color: #73879a;
    font-size: 11px;
  }

  .market-terminal__rotation-cell {
    font-weight: 700;
  }

  .market-terminal__rotation-cell.is-positive-cell {
    background: rgb(91 147 211 / 18%);
    color: #3777bf;
  }

  .market-terminal__rotation-cell.is-negative-cell {
    background: rgb(210 107 90 / 16%);
    color: #c95b48;
  }

  .is-right {
    text-align: right;
  }

  .is-center {
    text-align: center;
  }

  .is-positive,
  .is-stroke-up,
  .is-arrow-up {
    stroke: #5b93d3;
    color: #5b93d3;
  }

  .is-negative,
  .is-stroke-down,
  .is-arrow-down {
    stroke: #d26b5a;
    color: #d26b5a;
  }

  .market-terminal-chart-modal {
    display: flex;
    position: fixed;
    z-index: 2000;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: rgb(15 23 42 / 18%);
    inset: 0;
    backdrop-filter: blur(8px);
  }

  .market-terminal-chart-modal__dialog {
    width: min(72vw, calc(100vw - 48px));
    max-width: 1440px;
    min-height: min(78vh, 860px);
    padding: 22px 22px 18px;
    border: 1px solid rgb(201 213 226 / 90%);
    border-radius: 28px;
    background: linear-gradient(180deg, rgb(255 255 255 / 99%), rgb(244 249 252 / 98%)), #fff;
    box-shadow: 0 28px 80px rgb(15 23 42 / 14%);
  }

  .market-terminal-chart-modal__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 12px;
  }

  .market-terminal-chart-modal__eyebrow {
    margin: 0 0 6px;
    color: #7b8ea0;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .market-terminal-chart-modal__header h3 {
    margin: 0;
    color: #18313c;
    font-size: clamp(24px, 2.2vw, 42px);
    line-height: 1.08;
  }

  .market-terminal-chart-modal__close {
    padding: 10px 16px;
    border: 1px solid rgb(201 213 226 / 90%);
    border-radius: 999px;
    background: rgb(247 251 253 / 98%);
    color: #35586e;
    font-size: 13px;
    font-weight: 700;
  }

  .market-terminal-chart-modal__body {
    min-height: min(calc(78vh - 140px), 720px);
    overflow: hidden;
    border: 1px solid rgb(201 213 226 / 82%);
    border-radius: 20px;
    background: linear-gradient(180deg, rgb(252 254 255 / 98%), rgb(244 248 251 / 98%));
  }

  .market-terminal-chart-modal__state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: min(calc(78vh - 140px), 720px);
    padding: 24px;
    background: linear-gradient(180deg, rgb(251 253 255 / 98%), rgb(243 248 252 / 98%));
    color: #73879a;
    font-size: 14px;
    font-weight: 600;
  }

  .market-terminal-chart-modal__state.is-error {
    color: #c55a4b;
  }

  .market-terminal-chart-modal__widget {
    height: min(calc(78vh - 140px), 720px);
  }

  .market-terminal-chart-modal__widget.is-hidden {
    display: none;
  }

  :deep(.tradingview-widget-container),
  :deep(.tradingview-widget-container__widget) {
    width: 100%;
    height: 100%;
  }

  @media (max-width: 960px) {
    .market-terminal__editor-grid {
      grid-template-columns: 1fr;
    }

    .market-terminal__editor-field--wide {
      grid-column: span 1;
    }
  }
</style>
