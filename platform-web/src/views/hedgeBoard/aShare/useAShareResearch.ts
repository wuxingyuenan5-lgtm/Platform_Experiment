import { message } from 'ant-design-vue';
import { computed, onMounted, ref, watch } from 'vue';
import {
  getAShareDashboard,
  getStockSnapshot,
  type AShareDashboardResponse,
  type StockSnapshotResponse,
  type TurnoverThresholdStock,
} from '@/api/hedgeResearch';
import {
  getAccountResearchWatchlist,
  replaceAccountResearchWatchlist,
} from '@/api/platform/researchWatchlist';
import { UserSystemApiError } from '@/api/platform/userSystem';
import { copyText } from '@/utils/copyTextToClipboard';
import {
  normalizeStockCode,
  normalizeWatchlistItems,
  readWatchlist,
  readWatchlistDirty,
  writeWatchlist,
  writeWatchlistDirty,
  type WatchlistItem,
} from './aShareWatchlistLocalState';

export { normalizeStockCode };
export type { WatchlistItem };

function shanghaiDateStamp(date = new Date()) {
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date);
  const read = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value || '';
  return `${read('year')}-${read('month')}-${read('day')}`;
}

export function useAShareResearch() {
  const dashboard = ref<AShareDashboardResponse | null>(null);
  const dashboardLoading = ref(false);
  const dashboardError = ref('');
  const thresholdYuan = ref(10_000_000_000);
  const customThresholdYi = ref(100);
  const thresholdMode = ref<'50' | '100' | '200' | 'custom'>('100');

  const stockCode = ref('');
  const stockSnapshot = ref<StockSnapshotResponse | null>(null);
  const stockLoading = ref(false);
  const stockError = ref('');
  const watchlist = ref<WatchlistItem[]>(readWatchlist());
  const watchlistSyncState = ref<WatchlistSyncState>('local');
  const watchlistLastSyncedAt = ref('');
  let dashboardRequestSequence = 0;
  let stockRequestSequence = 0;
  let activeStockCode = '';
  let watchlistRemoteVersion = 0;
  let watchlistMutationSequence = 0;
  let watchlistSaveQueue: Promise<void> = Promise.resolve();

  const thresholdStocks = computed<TurnoverThresholdStock[]>(
    () => dashboard.value?.shenwan.data?.threshold?.stocks || [],
  );

  const thresholdIndustries = computed(
    () => dashboard.value?.shenwan.data?.threshold?.industries || [],
  );

  const watchlistGroups = computed(() => {
    const groups = new Map<string, WatchlistItem[]>();
    watchlist.value.forEach((item) => {
      const group = item.group || '默认分组';
      groups.set(group, [...(groups.get(group) || []), item]);
    });
    return Array.from(groups.entries()).map(([name, items]) => ({ name, items }));
  });

  async function loadDashboard() {
    const requestSequence = ++dashboardRequestSequence;
    const requestedThreshold = thresholdYuan.value;
    dashboardLoading.value = true;
    dashboardError.value = '';
    try {
      const result = await getAShareDashboard(requestedThreshold);
      if (requestSequence !== dashboardRequestSequence) return false;
      dashboard.value = result;
      return true;
    } catch (error) {
      if (requestSequence !== dashboardRequestSequence) return false;
      dashboardError.value = error instanceof Error ? error.message : 'A股投研数据加载失败';
      return false;
    } finally {
      if (requestSequence === dashboardRequestSequence) dashboardLoading.value = false;
    }
  }

  async function queryStock(code = stockCode.value) {
    const normalized = normalizeStockCode(code);
    if (!normalized) {
      stockError.value = '请输入6位A股代码，支持 600519、SH600519 或 600519.SH';
      return;
    }
    if (stockLoading.value && activeStockCode === normalized) return;

    stockCode.value = normalized;
    const requestSequence = ++stockRequestSequence;
    activeStockCode = normalized;
    stockLoading.value = true;
    stockError.value = '';
    if (stockSnapshot.value?.securityCode !== normalized) stockSnapshot.value = null;
    try {
      const result = await getStockSnapshot(normalized);
      if (requestSequence !== stockRequestSequence) return;
      stockSnapshot.value = result;
    } catch (error) {
      if (requestSequence !== stockRequestSequence) return;
      stockError.value = error instanceof Error ? error.message : '个股数据查询失败';
    } finally {
      if (requestSequence === stockRequestSequence) {
        stockLoading.value = false;
        activeStockCode = '';
      }
    }
  }

  function snapshotWatchlist() {
    return watchlist.value.map((item) => ({ ...item }));
  }

  function markWatchlistMutation() {
    watchlistMutationSequence += 1;
    writeWatchlistDirty(true);
  }

  async function persistWatchlistSnapshot(snapshot: WatchlistItem[]) {
    watchlistSyncState.value = 'syncing';
    try {
      let result;
      try {
        result = await replaceAccountResearchWatchlist(snapshot, watchlistRemoteVersion);
      } catch (error) {
        if (!(error instanceof UserSystemApiError) || error.code !== 'watchlist_version_conflict') {
          throw error;
        }
        const latest = await getAccountResearchWatchlist();
        watchlistRemoteVersion = latest.rowVersion;
        result = await replaceAccountResearchWatchlist(snapshot, watchlistRemoteVersion);
      }
      watchlistRemoteVersion = result.rowVersion;
      watchlistLastSyncedAt.value = result.updatedAt || '';
      writeWatchlistDirty(false);
      watchlistSyncState.value = 'synced';
    } catch {
      writeWatchlistDirty(true);
      watchlistSyncState.value = 'offline';
    }
  }

  function queueWatchlistSync() {
    const snapshot = snapshotWatchlist();
    watchlistSaveQueue = watchlistSaveQueue.then(() => persistWatchlistSnapshot(snapshot));
  }

  async function hydrateWatchlistFromAccount() {
    const mutationSequenceAtStart = watchlistMutationSequence;
    watchlistSyncState.value = 'syncing';
    try {
      const result = await getAccountResearchWatchlist();
      watchlistRemoteVersion = result.rowVersion;
      watchlistLastSyncedAt.value = result.updatedAt || '';
      const localChangedWhileLoading = watchlistMutationSequence !== mutationSequenceAtStart;
      if (readWatchlistDirty() || localChangedWhileLoading || result.rowVersion === 0) {
        queueWatchlistSync();
        return;
      }
      watchlist.value = normalizeWatchlistItems(result.items);
      watchlistSyncState.value = 'synced';
    } catch {
      watchlistSyncState.value = 'offline';
    }
  }

  function addToWatchlist(code: string, name: string, group = '默认分组') {
    const normalized = normalizeStockCode(code);
    if (!normalized || watchlist.value.some((item) => item.code === normalized)) return;
    watchlist.value.push({
      code: normalized,
      name: name.trim() || normalized,
      group: group.trim() || '默认分组',
    });
    markWatchlistMutation();
    queueWatchlistSync();
  }

  function removeFromWatchlist(code: string) {
    const normalized = normalizeStockCode(code);
    const next = watchlist.value.filter((item) => item.code !== normalized);
    if (next.length === watchlist.value.length) return;
    watchlist.value = next;
    markWatchlistMutation();
    queueWatchlistSync();
  }

  function moveWatchlistItem(code: string, direction: 'up' | 'down') {
    const normalized = normalizeStockCode(code);
    const index = watchlist.value.findIndex((item) => item.code === normalized);
    if (index < 0) return;
    const group = watchlist.value[index].group || '默认分组';
    const groupIndexes = watchlist.value.reduce<number[]>((indexes, item, itemIndex) => {
      if ((item.group || '默认分组') === group) indexes.push(itemIndex);
      return indexes;
    }, []);
    const groupPosition = groupIndexes.indexOf(index);
    const targetPosition = direction === 'up' ? groupPosition - 1 : groupPosition + 1;
    const targetIndex = groupIndexes[targetPosition];
    if (targetIndex == null) return;
    const next = [...watchlist.value];
    [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
    watchlist.value = next;
    markWatchlistMutation();
    queueWatchlistSync();
  }

  function setWatchlistGroup(code: string, group: string) {
    const normalized = normalizeStockCode(code);
    const item = watchlist.value.find((candidate) => candidate.code === normalized);
    const normalizedGroup = group.trim() || '默认分组';
    if (!item || item.group === normalizedGroup) return;
    item.group = normalizedGroup;
    markWatchlistMutation();
    queueWatchlistSync();
  }

  async function applyThresholdMode() {
    const thresholds = { '50': 50, '100': 100, '200': 200 } as const;
    const rawYi =
      thresholdMode.value === 'custom' ? customThresholdYi.value : thresholds[thresholdMode.value];
    const yi = Number(rawYi);
    if (!Number.isFinite(yi) || yi <= 0) {
      message.error('请输入大于0的成交额阈值。');
      return;
    }
    const normalizedYi = Math.max(1, yi);
    if (thresholdMode.value === 'custom') customThresholdYi.value = normalizedYi;
    thresholdYuan.value = normalizedYi * 100_000_000;
    const success = await loadDashboard();
    if (success) {
      message.success(
        `已更新：成交额 > ${normalizedYi}亿元，共 ${thresholdStocks.value.length} 只股票。`,
      );
    } else {
      message.error('阈值统计更新失败，已保留上一份有效数据。');
    }
  }

  function exportThresholdCsv() {
    const rows = thresholdStocks.value;
    if (!rows.length) {
      message.warning('当前阈值下没有可导出的股票明细。');
      return;
    }
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      message.error('当前环境不支持文件导出。');
      return;
    }
    try {
      const header = [
        '申万一级',
        '申万二级',
        '股票代码',
        '股票名称',
        '成交额（元）',
        '涨跌幅（%）',
      ];
      const body = rows.map((row) => [
        row.swL1Name,
        row.swL2Name,
        row.securityCode,
        row.securityName,
        String(row.turnoverYuan),
        row.returnPct == null ? '' : String(row.returnPct),
      ]);
      const csv = [header, ...body]
        .map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(','))
        .join('\n');
      const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `A股成交额阈值统计_${shanghaiDateStamp()}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      message.success(`已导出 ${rows.length} 只股票的CSV明细。`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '导出失败，请稍后重试。');
    }
  }

  async function copyThresholdSummary() {
    const industries = thresholdIndustries.value;
    if (!industries.length) {
      message.warning('当前阈值下没有可复制的行业统计。');
      return;
    }
    const thresholdYi = thresholdYuan.value / 100_000_000;
    const lines = [
      `口径：个股成交额 > ${thresholdYi}亿元`,
      `合计：${thresholdStocks.value.length}只，覆盖${industries.length}个申万二级行业`,
      ...industries.map((item) => `${item.swL1Name} / ${item.swL2Name}：${item.stockCount}只`),
    ];
    try {
      await copyText(lines.join('\n'), `已复制 ${industries.length} 个行业的统计结果。`);
    } catch (error) {
      message.error(error instanceof Error ? error.message : '复制失败，请检查浏览器权限。');
    }
  }

  watch(
    watchlist,
    (value) => {
      writeWatchlist(value);
    },
    { deep: true },
  );

  onMounted(() => {
    void loadDashboard();
    void hydrateWatchlistFromAccount();
  });

  return {
    dashboard,
    dashboardLoading,
    dashboardError,
    thresholdYuan,
    thresholdMode,
    customThresholdYi,
    thresholdStocks,
    thresholdIndustries,
    stockCode,
    stockSnapshot,
    stockLoading,
    stockError,
    watchlist,
    watchlistGroups,
    watchlistSyncState,
    watchlistLastSyncedAt,
    loadDashboard,
    queryStock,
    addToWatchlist,
    removeFromWatchlist,
    moveWatchlistItem,
    setWatchlistGroup,
    applyThresholdMode,
    exportThresholdCsv,
    copyThresholdSummary,
  };
}
