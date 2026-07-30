import { message } from 'ant-design-vue';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
  getAShareAccountWatchlist,
  getAShareDashboard,
  getStockSnapshot,
  replaceAShareAccountWatchlist,
  type AShareDashboardResponse,
  type StockSnapshotResponse,
  type TurnoverThresholdStock,
} from '@/api/hedgeResearch';
import { copyText } from '@/utils/copyTextToClipboard';

export interface WatchlistItem {
  code: string;
  name: string;
  group: string;
}

export type WatchlistSyncState = 'loading' | 'saving' | 'synced' | 'local' | 'error';

const WATCHLIST_STORAGE_KEY = 'vg_a_share_watchlist_v1';
const DEFAULT_WATCHLIST: WatchlistItem[] = [
  { code: '600519', name: '贵州茅台', group: '核心观察' },
  { code: '300750', name: '宁德时代', group: '核心观察' },
];

export function normalizeStockCode(value: string) {
  const compact = value.trim().toUpperCase().replace(/\s+/g, '');
  const match = compact.match(/^(?:(?:SH|SZ|BJ)[.:-]?)?(\d{6})(?:[.:-]?(?:SH|SZ|BJ))?$/);
  return match?.[1] || '';
}

function normalizeWatchlistItem(item: unknown): WatchlistItem | null {
  if (!item || typeof item !== 'object') return null;
  const record = item as Record<string, unknown>;
  const code = typeof record.code === 'string' ? normalizeStockCode(record.code) : '';
  if (!code) return null;
  const name = typeof record.name === 'string' ? record.name.trim() : '';
  const group = typeof record.group === 'string' ? record.group.trim() : '';
  return {
    code,
    name: name || code,
    group: group || '默认分组',
  };
}

function sanitizeWatchlist(items: unknown[]): WatchlistItem[] {
  const seen = new Set<string>();
  return items.reduce<WatchlistItem[]>((result, candidate) => {
    const normalized = normalizeWatchlistItem(candidate);
    if (!normalized || seen.has(normalized.code)) return result;
    seen.add(normalized.code);
    result.push(normalized);
    return result;
  }, []);
}

function readWatchlist(): WatchlistItem[] {
  if (typeof window === 'undefined') return [...DEFAULT_WATCHLIST];
  try {
    const stored = window.localStorage.getItem(WATCHLIST_STORAGE_KEY);
    if (stored === null) return [...DEFAULT_WATCHLIST];
    const payload = JSON.parse(stored);
    if (!Array.isArray(payload)) return [...DEFAULT_WATCHLIST];
    return sanitizeWatchlist(payload);
  } catch {
    return [...DEFAULT_WATCHLIST];
  }
}

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
  const watchlistVersion = ref(0);
  const watchlistSyncState = ref<WatchlistSyncState>('loading');
  const watchlistSyncMessage = ref('正在读取账号自选股');
  let dashboardRequestSequence = 0;
  let stockRequestSequence = 0;
  let watchlistSaveSequence = 0;
  let activeStockCode = '';
  let watchlistSyncTimer: number | undefined;

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

  function accountItems() {
    return watchlist.value.map((item) => ({
      securityCode: item.code,
      securityName: item.name,
      group: item.group,
    }));
  }

  function applyAccountWatchlist(
    items: Array<{ securityCode: string; securityName: string; group: string }>,
  ) {
    watchlist.value = sanitizeWatchlist(
      items.map((item) => ({
        code: item.securityCode,
        name: item.securityName,
        group: item.group,
      })),
    );
  }

  async function saveAccountWatchlist(options: { silent?: boolean } = {}) {
    const requestSequence = ++watchlistSaveSequence;
    watchlistSyncState.value = 'saving';
    watchlistSyncMessage.value = '正在同步到账号';
    try {
      const result = await replaceAShareAccountWatchlist({
        expectedVersion: watchlistVersion.value,
        items: accountItems(),
      });
      if (requestSequence !== watchlistSaveSequence) return false;
      watchlistVersion.value = result.version;
      applyAccountWatchlist(result.items);
      watchlistSyncState.value = 'synced';
      watchlistSyncMessage.value = '已同步到账号';
      return true;
    } catch (error) {
      if (requestSequence !== watchlistSaveSequence) return false;
      const status = (error as Error & { status?: number }).status;
      if (status === 409) {
        try {
          const latest = await getAShareAccountWatchlist();
          watchlistVersion.value = latest.version;
          applyAccountWatchlist(latest.items);
          watchlistSyncState.value = 'error';
          watchlistSyncMessage.value = '检测到其他设备更新，已载入账号最新版本';
          if (!options.silent) message.warning(watchlistSyncMessage.value);
          return false;
        } catch {
          // Fall through to the local cache state below.
        }
      }
      watchlistSyncState.value = 'local';
      watchlistSyncMessage.value = '账号同步暂不可用，已保存在本机';
      if (!options.silent) message.warning(watchlistSyncMessage.value);
      return false;
    }
  }

  function scheduleWatchlistSync() {
    if (typeof window === 'undefined') return;
    if (watchlistSyncTimer !== undefined) window.clearTimeout(watchlistSyncTimer);
    watchlistSyncState.value = 'saving';
    watchlistSyncMessage.value = '等待同步到账号';
    watchlistSyncTimer = window.setTimeout(() => {
      watchlistSyncTimer = undefined;
      void saveAccountWatchlist({ silent: true });
    }, 450);
  }

  async function loadAccountWatchlist() {
    watchlistSyncState.value = 'loading';
    watchlistSyncMessage.value = '正在读取账号自选股';
    try {
      const result = await getAShareAccountWatchlist();
      watchlistVersion.value = result.version;
      if (result.version === 0) {
        await saveAccountWatchlist({ silent: true });
        return;
      }
      applyAccountWatchlist(result.items);
      watchlistSyncState.value = 'synced';
      watchlistSyncMessage.value = '已同步到账号';
    } catch {
      watchlistSyncState.value = 'local';
      watchlistSyncMessage.value = '账号同步暂不可用，当前使用本机缓存';
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
    scheduleWatchlistSync();
  }

  function removeFromWatchlist(code: string) {
    const normalized = normalizeStockCode(code);
    watchlist.value = watchlist.value.filter((item) => item.code !== normalized);
    scheduleWatchlistSync();
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
    scheduleWatchlistSync();
  }

  function setWatchlistGroup(code: string, group: string) {
    const normalized = normalizeStockCode(code);
    const item = watchlist.value.find((candidate) => candidate.code === normalized);
    if (item) {
      item.group = group.trim() || '默认分组';
      scheduleWatchlistSync();
    }
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
      if (typeof window === 'undefined') return;
      try {
        window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(value));
      } catch {
        // Keep the in-memory watchlist usable when browser storage is unavailable.
      }
    },
    { deep: true },
  );

  onMounted(() => {
    void loadDashboard();
    void loadAccountWatchlist();
  });

  onBeforeUnmount(() => {
    if (watchlistSyncTimer !== undefined && typeof window !== 'undefined') {
      window.clearTimeout(watchlistSyncTimer);
      watchlistSyncTimer = undefined;
      void saveAccountWatchlist({ silent: true });
    }
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
    watchlistSyncMessage,
    loadDashboard,
    queryStock,
    addToWatchlist,
    removeFromWatchlist,
    moveWatchlistItem,
    setWatchlistGroup,
    loadAccountWatchlist,
    saveAccountWatchlist,
    applyThresholdMode,
    exportThresholdCsv,
    copyThresholdSummary,
  };
}
