<template>
  <section
    class="observation-panel"
    :aria-label="
      {
        daily: '宽基ETF资金全景',
        intraday: '盘中ETF监测',
        heatmap: '宽基月度资金表',
        support: '历史大额申购信号对照',
      }[mode]
    "
  >
    <p v-if="loading" role="status">正在读取 ETF 资金观测…</p>
    <p v-if="error" class="observation-notice" role="status"
      >{{ error }}<button @click="load">重试</button></p
    >
    <div
      v-if="mode === 'daily' && snapshot && !flowOnly"
      class="overview-stats"
      :aria-label="mode === 'daily' ? '宽基ETF统计' : '25只ETF统计'"
    >
      <div
        v-for="card in summaryCards"
        :key="card.label"
        class="stat-card"
        :title="card.definition"
      >
        <div class="stat-label">{{ card.label }}</div>
        <div class="stat-value" :class="card.tone">{{ card.value }}</div>
        <div class="stat-detail">{{ card.detail }}</div>
      </div>
    </div>
    <p v-if="mode !== 'intraday' && provenance && !flowOnly" class="observation-provenance">{{
      provenance
    }}</p>
    <EtfDailyFlowPanel
      v-if="mode === 'daily' && snapshot"
      :reference="snapshot.reference"
      :flow-only="flowOnly"
    />
    <div v-else-if="mode !== 'daily'" ref="host" class="etf-observation"></div>
    <Teleport v-if="mode === 'intraday' && provenanceTarget && provenance" :to="provenanceTarget">
      <span class="intraday-provenance" :title="provenance">{{ provenance }}</span>
    </Teleport>
    <Teleport v-if="mode === 'intraday' && forecastTarget" :to="forecastTarget">
      <AllATurnoverForecast :refresh-key="refreshKey" />
    </Teleport>
    <FinancingChart
      v-if="mode === 'daily' && innovationRows.length && !flowOnly"
      title="双创购买比例"
      :rows="innovationRows"
      :lines="innovationLines"
      :initial-range="1095"
      :axis-names="['净申购占比（%）', '成交额占比（%）']"
      :bounds="[-100, 100]"
      mark-overflow
      :note="`净申购占比左轴固定−100%～+100%，成交额占比使用右轴；三角标记表示超出范围，悬浮查看实际值。日度数据截至 ${
        innovationRows.at(-1)?.date || '—'
      }。`"
    />
  </section>
</template>

<script setup lang="ts">
  import {
    computed,
    nextTick,
    onActivated,
    onDeactivated,
    onBeforeUnmount,
    onMounted,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { getEtfObservation, type ObservationSnapshot } from '@/api/etfObservation';
  import EtfDailyFlowPanel from './EtfDailyFlowPanel.vue';
  import { flowDailyAverage } from './etfFlowAnalysis';
  import AllATurnoverForecast from './AllATurnoverForecast.vue';
  import FinancingChart, { type FinanceRow, type FinanceLine } from './FinancingChart.vue';
  import layout from './etfObservation/layout.html?raw';
  import { mountEtfObservation } from './etfObservation/renderer';
  import './etfObservation/reference.css';

  const props = withDefaults(
    defineProps<{
      mode?: 'daily' | 'intraday' | 'heatmap' | 'support';
      flowOnly?: boolean;
      refreshKey?: number;
    }>(),
    { mode: 'intraday' },
  );
  const emit = defineEmits<{ ready: [] }>();
  const host = ref<HTMLElement>();
  const forecastTarget = shallowRef<HTMLElement | null>(null);
  const provenanceTarget = shallowRef<HTMLElement | null>(null);
  let pageActive = true;
  function prepareLayout(element: HTMLElement) {
    element.innerHTML = layout;
    forecastTarget.value = element.querySelector('#allATurnoverForecast');
    provenanceTarget.value = element.querySelector('#chart')?.parentElement || null;
    provenanceTarget.value?.classList.add('intraday-primary-chart');
    element.querySelector('.top')?.remove();
    const keep = ['daily', 'heatmap'].includes(props.mode)
      ? ['etf-observation-part3']
      : props.mode === 'support'
      ? ['etf-observation-part2']
      : ['etf-observation-part1'];
    element.querySelectorAll<HTMLElement>('.part').forEach((part) => {
      if (!keep.includes(part.id)) part.remove();
    });
    function fold(label: string, nodes: Element[]) {
      if (!nodes.length) return;
      const box = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = label;
      box.append(summary);
      nodes[0].before(box);
      nodes.forEach((node) => box.append(node));
    }
    if (props.mode === 'intraday') {
      element.querySelectorAll('#etf-observation-part1 > .pt').forEach((node) => node.remove());
      element.querySelector('#etfTable')?.closest('.table-wrap')?.remove();
    } else if (props.mode === 'heatmap') {
      element
        .querySelectorAll('.chart-wrap, .part > .pt, .part > .sub, footer')
        .forEach((node) => node.remove());
    } else {
      element.querySelector('#etf-observation-part2 > .pt')!.textContent = '历史大额申购信号对照';
    }
    element.querySelectorAll('footer').forEach((footer) => fold('统计口径', [footer]));
  }
  const loading = ref(true),
    error = ref('');
  const snapshot = shallowRef<ObservationSnapshot>();
  const summary = computed(() =>
    props.mode === 'intraday' ? snapshot.value?.intradaySummary : snapshot.value?.summary,
  );
  function formatStat(value: string | null | undefined, digits = 1, signed = false) {
    if (value == null || !Number.isFinite(Number(value))) return '—';
    const number = Number(value);
    return `${signed && number > 0 ? '+' : ''}${number.toLocaleString('zh-CN', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    })}`;
  }
  const summaryCards = computed(() => {
    const current = summary.value;
    const scope = props.mode === 'daily' ? '宽基ETF' : '25只ETF';
    const date = current?.date || '暂无数据';
    const partial =
      props.mode === 'daily' &&
      current?.coveredCount != null &&
      current.coveredCount < current.basketCount;
    const flowDefinition = `${scope}：同日单位净值×交易所份额变动；按已取得成员汇总，全部缺失时留空。`;
    const flows = [
      {
        label: `${scope} · 最新${partial ? '' : '完整'}日净流入`,
        value: current?.flow1Yi,
        days: 1,
        detail: `${date}${
          current?.basketCount
            ? ` · ${partial ? `覆盖${current.coveredCount}/` : ''}${current.basketCount}只`
            : ''
        }`,
      },
      {
        label: `${scope} · 近5日累计 | 日均`,
        value: current?.flow5Yi,
        days: 5,
        detail: `${date} · 5交易日`,
      },
      {
        label: `${scope} · 近20日累计 | 日均`,
        value: current?.flow20Yi,
        days: 20,
        detail: `${date} · 20交易日`,
      },
    ].map(({ label, value, days, detail }) => {
      const total = formatStat(value, 2, true).replace(/,/g, '');
      const average = formatStat(flowDailyAverage(value, days)?.toString(), 2, true);
      return {
        label,
        value: days === 1 ? `${formatStat(value, 2, true)} 亿元` : `${total} | ${average}亿元`,
        detail,
        tone: Number(value) > 0 ? 'positive' : Number(value) < 0 ? 'negative' : '',
        definition: flowDefinition + (days > 1 ? `日均为未取位累计值÷${days}个交易日。` : ''),
      };
    });
    const futures = current?.futures;
    const innovation = snapshot.value?.reference.broadInnovationRatio?.rows?.at(-1);
    const innovationCard = {
      label: '双创成交额比例',
      value: `${formatStat(innovation?.turnoverPct, 2)}%`,
      detail: `双创样本 / 宽基ETF · ${innovation?.date || '暂无数据'}${
        innovation?.covered < innovation?.expected
          ? ` · 覆盖${innovation.covered}/${innovation.expected}`
          : ''
      }`,
      tone: '',
      definition:
        '159915、588000、159949、588080、159952中已上市成员的同日成交额合计 ÷ 宽基ETF目录同日成交额合计 × 100%；缺数按已取得成员计算并标明覆盖，全部缺失或分母为零时留空。',
    };
    const futuresCard = {
      label: `${futures?.member || '中信期货'}净空头变动(手)`,
      value: formatStat(futures?.netShortChange, 0, true),
      detail: `${futures?.date || '暂无数据'} 四品种合计${
        futures?.status && futures.status !== 'ready' ? ' · 更新异常' : ''
      }`,
      tone:
        Number(futures?.netShortChange) > 0
          ? 'positive'
          : Number(futures?.netShortChange) < 0
          ? 'negative'
          : '',
      definition: `IH/IF/IC/IM卖单增减−买单增减，会员全部客户合计。来源：${
        futures?.sourceUrl || '暂无已采集数据'
      }`,
    };
    return props.mode === 'daily'
      ? [...flows, innovationCard, futuresCard]
      : [...flows, innovationCard];
  });
  const innovationRows = computed<FinanceRow[]>(
    () => snapshot.value?.reference.broadInnovationRatio?.rows || [],
  );
  const innovationLines: FinanceLine[] = [
    {
      key: 'netSubscriptionPct',
      name: '双创申购比例',
      color: '#2864ec',
      unit: '%',
      defaultSelected: false,
    },
    { key: 'turnoverPct', name: '双创成交额比例', color: '#d18a30', unit: '%', right: true },
  ];
  let dispose: ReturnType<typeof mountEtfObservation> | undefined,
    active = true;
  let lastRead = 0;
  let refreshTimer: ReturnType<typeof setInterval> | undefined;
  function referenceVersion(data?: ObservationSnapshot) {
    return `${data?.sources.reference?.sha256 || data?.sources.reference?.retrievedAt || ''}|${
      data?.sources.reference?.status || ''
    }|${JSON.stringify(data?.summary)}|${JSON.stringify(data?.intradaySummary)}`;
  }
  let pending: Promise<ObservationSnapshot> | undefined;
  const provenance = computed(() => {
    const data = snapshot.value;
    if (!data || props.mode === 'daily') return '';
    const dates = data.reference.broadDailyData?.dates || [];
    const source = data.sources.live;
    if (props.mode !== 'intraday') {
      const amounts = data.reference.broadDailyData?.amount || [];
      const amountDate = dates.findLast((_: string, i: number) => amounts[i] != null);
      return `宽基ETF统计 · 成交额截至 ${amountDate || '暂无数据'} · 净申购完整日至 ${
        data.summary?.date || '暂无数据'
      } · ${data.sources.reference?.sourceLabel || '历史留存数据'}${
        data.sources.reference?.status !== 'ready' ? ' · 部分份额／净值待齐或更新异常' : ''
      }`;
    }
    return `分时截至 ${
      source?.observationTime ||
      source?.observationDate ||
      data.reference.initData?.date ||
      '暂无数据'
    } · ${source?.sourceLabel || '历史留存数据'}${
      source?.status !== 'ready' ? ' · 更新异常，当前数据存在延迟' : ''
    }`;
  });
  async function read(force = false): Promise<ObservationSnapshot> {
    if (!force && snapshot.value && Date.now() - lastRead < 1000) return snapshot.value;
    if (!pending) {
      pending = getEtfObservation()
        .then((data) => {
          if (active) {
            if (
              props.mode === 'intraday' ||
              referenceVersion(snapshot.value) !== referenceVersion(data)
            )
              snapshot.value = data;
            lastRead = Date.now();
          }
          return data;
        })
        .finally(() => {
          pending = undefined;
        });
    }
    return pending;
  }
  async function request(path: string) {
    const data = await read();
    const url = new URL(path, 'http://localhost');
    if (url.pathname === '/api/kline') {
      const rows = data.live.klines?.[url.searchParams.get('symbol') || ''];
      if (!rows?.length) throw new Error('分钟数据暂不可用');
      return url.searchParams.get('datalen') === '1' ? rows.slice(-1) : rows;
    }
    if (url.pathname === '/api/hq') {
      const codes = new Set(
        (url.searchParams.get('codes') || '').split(',').map((code) => code.slice(2)),
      );
      const rows = data.live.hq?.data?.diff?.filter((row) => codes.has(row.f12));
      if (!rows?.length) throw new Error('行情快照暂不可用');
      return { data: { diff: rows } };
    }
    throw new Error('未知ETF数据类型');
  }
  async function renderReference(data: ObservationSnapshot) {
    forecastTarget.value = null;
    await nextTick();
    dispose?.();
    if (host.value) {
      prepareLayout(host.value);
      const reference =
        props.mode === 'support'
          ? {
              ...data.reference,
              dailyData: data.reference.broadDailyData,
              cmpData: data.reference.broadCmpData,
            }
          : data.reference;
      dispose = mountEtfObservation(host.value, structuredClone(reference), request, {
        live: props.mode === 'intraday',
        onUpdateError: (message: string) => {
          if (active) error.value = message;
        },
      });
      if (!pageActive) dispose.pause();
    }
  }
  async function refreshArchived() {
    if (!active || !pageActive || document.hidden || props.mode === 'intraday') return;
    const previous = referenceVersion(snapshot.value);
    try {
      const data = await read(true);
      if (active && pageActive && previous !== referenceVersion(data)) await renderReference(data);
      if (active) error.value = '';
    } catch (cause) {
      if (active) error.value = cause instanceof Error ? cause.message : 'ETF资金观测暂不可用';
    }
  }
  function startRefresh() {
    if (!refreshTimer && props.mode !== 'intraday')
      refreshTimer = setInterval(refreshArchived, 300000);
  }
  function stopRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = undefined;
  }
  async function load() {
    loading.value = true;
    error.value = '';
    try {
      const data = await read(true);
      if (!active) return;
      if (
        !(props.mode === 'intraday' ? data.reference.dailyData : data.reference.broadData)?.dates
          ?.length
      )
        throw new Error('ETF历史尚未取得，请稍后重试。');
      await renderReference(data);
    } catch (cause) {
      if (active) error.value = cause instanceof Error ? cause.message : 'ETF资金观测暂不可用';
    } finally {
      if (active) {
        loading.value = false;
        emit('ready');
      }
    }
  }
  onMounted(() => {
    if (props.mode === 'intraday' && host.value) prepareLayout(host.value);
    void load();
    startRefresh();
    document.addEventListener('visibilitychange', refreshArchived);
  });
  watch(() => props.refreshKey, load);
  onDeactivated(() => {
    pageActive = false;
    stopRefresh();
    dispose?.pause();
  });
  onActivated(() => {
    pageActive = true;
    dispose?.resume();
    startRefresh();
    void refreshArchived();
  });
  onBeforeUnmount(() => {
    active = false;
    stopRefresh();
    document.removeEventListener('visibilitychange', refreshArchived);
    dispose?.();
  });
</script>

<style scoped>
  .etf-observation :deep(.intraday-primary-chart) {
    position: relative;
  }

  .intraday-provenance {
    position: absolute;
    top: 34px;
    right: 16px;
    left: 16px;
    overflow: hidden;
    color: #64748b;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .overview-stats {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 12px;
  }

  .stat-card {
    padding: 12px 14px;
    border: 1px solid #dbe4ee;
    border-radius: 10px;
    background: #fff;
  }

  .stat-label,
  .stat-detail {
    color: #64748b;
    font-size: 12px;
  }

  .stat-value {
    margin: 4px 0;
    color: #182c45;
    font-size: 24px;
    font-weight: 700;
    line-height: 1.25;
  }

  .positive {
    color: #ef5350;
  }

  .negative {
    color: #2fa36b;
  }

  @media (max-width: 1100px) {
    .overview-stats {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 480px) {
    .overview-stats {
      grid-template-columns: 1fr;
    }
  }

  .observation-panel :deep(details) {
    margin: 14px 0;
    padding: 12px;
    border: 1px solid #dbe4ee;
    border-radius: 8px;
  }

  .observation-panel :deep(summary) {
    color: #3d5067;
    font-weight: 600;
    cursor: pointer;
  }

  .observation-panel {
    min-width: 0;
  }

  .observation-provenance,
  .observation-notice {
    margin: 0 0 10px;
    color: #5a6472;
    font-size: 12px;
  }

  .observation-notice button {
    margin-left: 10px;
    cursor: pointer;
  }
</style>
