import { computed, onMounted, ref, watch } from 'vue';
import {
  getAShareDashboard,
  getStockSnapshot,
  type AShareDashboardResponse,
  type StockSnapshotResponse,
  type TurnoverThresholdStock,
} from '@/api/hedgeResearch';

export interface WatchlistItem {
  code: string;
  name: string;
  group: string;
}

const WATCHLIST_STORAGE_KEY = 'vg_a_share_watchlist_v1';
const DEFAULT_WATCHLIST: WatchlistItem[] = [
  { code: '600519', name: '贵州茅台', group: '核心观察' },
  { code: '300750', name: '宁德时代', group: '核心观察' },
];

function readWatchlist(): WatchlistItem[] {
  if (typeof window === 'undefined') return [...DEFAULT_WATCHLIST];
  try {
    const payload = JSON.parse(window.localStorage.getItem(WATCHLIST_STORAGE_KEY) || '[]');
    if (!Array.isArray(payload) || !payload.length) return [...DEFAULT_WATCHLIST];
    return payload.filter(
      (item): item is WatchlistItem =>
        typeof item?.code === 'string' && /^\d{6}$/.test(item.code) && typeof item?.name === 'string',
    );
  } catch {
    return [...DEFAULT_WATCHLIST];
  }
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
  let stockRequestSequence = 0;

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
    dashboardLoading.value = true;
    dashboardError.value = '';
    try {
      dashboard.value = await getAShareDashboard(thresholdYuan.value);
    } catch (error) {
      dashboardError.value = error instanceof Error ? error.message : 'A股投研数据加载失败';
    } finally {
      dashboardLoading.value = false;
    }
  }

  async function queryStock(code = stockCode.value) {
    const normalized = code.trim();
    if (!/^\d{6}$/.test(normalized)) {
      stockError.value = '请输入6位A股代码';
      return;
    }
    stockCode.value = normalized;
    const requestSequence = ++stockRequestSequence;
    stockLoading.value = true;
    stockError.value = '';
    stockSnapshot.value = null;
    try {
      const result = await getStockSnapshot(normalized);
      if (requestSequence !== stockRequestSequence) return;
      stockSnapshot.value = result;
    } catch (error) {
      if (requestSequence !== stockRequestSequence) return;
      stockError.value = error instanceof Error ? error.message : '个股数据查询失败';
    } finally {
      if (requestSequence === stockRequestSequence) stockLoading.value = false;
    }
  }

  function addToWatchlist(code: string, name: string, group = '默认分组') {
    if (!/^\d{6}$/.test(code) || watchlist.value.some((item) => item.code === code)) return;
    watchlist.value.push({ code, name: name || code, group });
  }

  function removeFromWatchlist(code: string) {
    watchlist.value = watchlist.value.filter((item) => item.code !== code);
  }

  function moveWatchlistItem(code: string, direction: 'up' | 'down') {
    const index = watchlist.value.findIndex((item) => item.code === code);
    const target = direction === 'up' ? index - 1 : index + 1;
    if (index < 0 || target < 0 || target >= watchlist.value.length) return;
    const next = [...watchlist.value];
    [next[index], next[target]] = [next[target], next[index]];
    watchlist.value = next;
  }

  function setWatchlistGroup(code: string, group: string) {
    const item = watchlist.value.find((candidate) => candidate.code === code);
    if (item) item.group = group.trim() || '默认分组';
  }

  function applyThresholdMode() {
    const thresholds = { '50': 50, '100': 100, '200': 200 } as const;
    const yi = thresholdMode.value === 'custom' ? customThresholdYi.value : thresholds[thresholdMode.value];
    thresholdYuan.value = Math.max(1, Number(yi) || 1) * 100_000_000;
    void loadDashboard();
  }

  function exportThresholdCsv() {
    const rows = thresholdStocks.value;
    if (!rows.length || typeof window === 'undefined') return;
    const header = ['申万一级', '申万二级', '股票代码', '股票名称', '成交额（元）', '涨跌幅（%）'];
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
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `A股成交额阈值统计_${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  async function copyThresholdSummary() {
    const lines = thresholdIndustries.value.map(
      (item) => `${item.swL1Name} / ${item.swL2Name}：${item.stockCount}只`,
    );
    if (!lines.length || !navigator.clipboard) return;
    await navigator.clipboard.writeText(lines.join('\n'));
  }

  watch(
    watchlist,
    (value) => {
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(value));
      }
    },
    { deep: true },
  );

  onMounted(() => {
    void loadDashboard();
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
