import {
  computed,
  inject,
  onBeforeUnmount,
  provide,
  ref,
  shallowRef,
  type InjectionKey,
} from 'vue';
import Decimal from 'decimal.js';
import { researchRequest, type MacroDashboardSeries } from '@/api/hedgeResearch';
import type { FinanceLine, FinanceRow } from './FinancingChart.vue';

export interface Basis extends FinanceRow {
  family: string;
  contract: string;
  close: string | null;
  spot: string | null;
  basis: string | null;
  basisPct: string | null;
}
export interface Iv {
  date: string;
  underlying: string;
  month: string;
  value: string;
  main?: boolean;
  contracts: string[];
}
export interface Data {
  margin: MacroDashboardSeries[];
  marginIndex: { rows: { date: string; close: string | null }[]; sourceUrl?: string };
  basis: Basis[];
  iv: { rows?: Iv[] };
  ivIndices: {
    code: string;
    name: string;
    underlyings: string[];
    rows: { date: string; close: string | null }[];
    sourceUrl?: string;
    historySourceUrl?: string;
  }[];
  goldIv: MacroDashboardSeries[];
  futuresSource: { status?: string };
}

function createDomesticFinancing() {
  const data = shallowRef<Data>();
  const error = ref('');
  const loading = ref(false);
  const underlying = ref('IO');
  let updatedAt = 0;
  let pending: Promise<void> | undefined;
  let controller: AbortController | undefined;
  function reset() {
    controller?.abort();
    pending = undefined;
    data.value = undefined;
    error.value = '';
    loading.value = false;
    underlying.value = 'IO';
    updatedAt = 0;
  }
  function load(force = false): Promise<void> {
    if (pending) return pending;
    if (!force && data.value && Date.now() - updatedAt < 60_000) return Promise.resolve();
    const current = new AbortController();
    controller = current;
    loading.value = true;
    error.value = '';
    pending = researchRequest<Data>({
      method: 'GET',
      url: '/research/a-share/financing',
      signal: current.signal,
    })
      .then((result) => {
        if (!current.signal.aborted) {
          data.value = result;
          updatedAt = Date.now();
        }
      })
      .catch(() => {
        if (!current.signal.aborted) error.value = '两融与衍生品读取失败，请重试';
      })
      .finally(() => {
        if (!current.signal.aborted) {
          pending = undefined;
          loading.value = false;
        }
      });
    return pending;
  }
  onBeforeUnmount(reset);
  return { data, error, loading, underlying, load, reset };
}
const financingKey: InjectionKey<ReturnType<typeof createDomesticFinancing>> =
  Symbol('domestic-financing');

export function provideDomesticFinancing() {
  const state = createDomesticFinancing();
  provide(financingKey, state);
  return state;
}
export function useDomesticFinancing() {
  return inject(financingKey) ?? createDomesticFinancing();
}
export function useDomesticOptionIv() {
  const state = useDomesticFinancing();
  const { data, underlying } = state;
  const isIndexOption = computed(() => ['IO', 'HO', 'MO'].includes(underlying.value));
  const isSzseOption = computed(() => underlying.value.startsWith('159'));
  const ivIndex = computed(() =>
    data.value?.ivIndices?.find((index) => index.underlyings.includes(underlying.value)),
  );
  const ivLines = computed<FinanceLine[]>(() => [
    { key: 'iv', name: 'IV', color: '#2563eb', unit: '%' },
    {
      key: 'indexClose',
      name: ivIndex.value?.name || '对应指数',
      color: '#171717',
      unit: '点',
      right: true,
      width: 2,
    },
  ]);
  const ivRows = computed<FinanceRow[]>(() => {
    const closes = new Map(ivIndex.value?.rows.map((row) => [row.date, row.close]));
    const rows =
      data.value?.iv.rows?.filter(
        (r) => r.underlying === underlying.value && (!isIndexOption.value || r.main === true),
      ) || [];
    const days = new Map<string, Iv>();
    for (const r of rows)
      if (!days.has(r.date) || r.month < days.get(r.date)!.month) days.set(r.date, r);
    return [...days.values()]
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((r) => ({
        date: r.date,
        iv: r.value,
        indexClose: closes.get(r.date) ?? null,
        month: r.month,
        contract: r.contracts.join(' / '),
      }));
  });
  const latest = computed(() =>
    ivRows.value.filter((row) => row.iv != null && Number.isFinite(Number(row.iv))).slice(-2),
  );
  const summary = computed(() => {
    const current = latest.value.at(-1);
    const previous = latest.value.at(-2);
    const value = current ? new Decimal(String(current.iv)).toFixed(2) + '%' : '—';
    const change =
      current && previous ? new Decimal(String(current.iv)).minus(String(previous.iv)) : undefined;
    return {
      value,
      change: change == null ? '—' : (change.gt(0) ? '+' : '') + change.toFixed(2) + '个百分点',
      date: current?.date || '',
      previousDate: previous?.date || '',
      name: ivIndex.value?.name || underlying.value,
    };
  });
  return { ...state, isIndexOption, isSzseOption, ivRows, ivIndex, ivLines, summary };
}
