<template>
  <div class="market-terminal">
    <p v-if="['us', 'global'].includes(config.id)" role="status">
      {{
        marketLoading
          ? '正在读取数据…'
          : marketError
          ? '数据暂不可用'
          : marketSnapshot?.status === 'stale'
          ? '当前显示最近保留的数据'
          : marketSnapshot?.status === 'partial'
          ? '部分数据暂不可用'
          : !marketSnapshot?.rows.length
          ? '暂无数据'
          : `数据日期：${marketSnapshot.asOf ?? '—'}`
      }}
    </p>
    <HedgeBoardSubnav
      v-if="displayConfig.id === 'us'"
      :sections="[
        { id: 'us-market-overview', title: '大盘表现' },
        { id: detailSectionId, title: '美股市场明细' },
        ...(displayConfig.rotationButtonLabel
          ? [{ id: 'us-market-rotation', title: displayConfig.rotationButtonLabel }]
          : []),
      ]"
      module-label="美股"
      unified
      :resolve-title="(_id, title) => title"
      @jump="jumpToMarketSection"
    />
    <section
      :id="`${displayConfig.id}-market-overview`"
      v-if="displayOverviewCards.length"
      class="market-terminal__overview-strip"
      :class="{
        'is-single': !(displayConfig.breadthCards?.length || displayConfig.volatilityCards?.length),
      }"
    >
      <article class="market-terminal__overview-panel">
        <div class="market-terminal__panel-head">
          <h3>大盘表现</h3>
          <div v-if="displayConfig.overviewChip" class="market-terminal__mini-chip">{{
            displayConfig.overviewChip
          }}</div>
        </div>

        <div class="market-terminal__market-grid">
          <button
            v-for="item in displayOverviewCards"
            :key="item.id"
            type="button"
            class="market-terminal__market-card"
            :class="{ 'is-clickable': canOpenTickerChart(item.symbol) }"
            @click="openTickerChart(item.symbol, item.label)"
          >
            <span class="market-terminal__market-symbol">{{ item.symbol }}</span>
            <div class="market-terminal__market-head">
              <strong>{{ item.label }}</strong>
              <em :class="toneClass(item.tone)">{{ item.change }}</em>
            </div>
            <svg
              class="market-terminal__market-spark"
              viewBox="0 0 80 22"
              preserveAspectRatio="none"
            >
              <polyline
                :points="compactSparkline(item.spark, 80, 22)"
                :class="sparkStrokeClass(item.change)"
              />
            </svg>
          </button>
        </div>

        <div class="market-terminal__subhead">主题指数</div>

        <div class="market-terminal__market-grid">
          <button
            v-for="item in displayMoverCards"
            :key="item.id"
            type="button"
            class="market-terminal__market-card market-terminal__market-card--mover"
            :class="{ 'is-clickable': canOpenTickerChart(item.symbol) }"
            @click="openTickerChart(item.symbol, item.label)"
          >
            <span class="market-terminal__market-category">{{ item.category }}</span>
            <span class="market-terminal__market-symbol">{{ item.symbol }}</span>
            <div class="market-terminal__market-head">
              <strong>{{ item.label }}</strong>
              <em :class="toneClass(item.tone)">{{ item.change }}</em>
            </div>
            <span v-if="item.price" class="market-terminal__market-price">{{ item.price }}</span>
            <svg
              class="market-terminal__market-spark"
              viewBox="0 0 80 22"
              preserveAspectRatio="none"
            >
              <polyline
                :points="compactSparkline(item.spark, 80, 22)"
                :class="sparkStrokeClass(item.change)"
              />
            </svg>
          </button>
        </div>
      </article>

      <div
        v-if="displayConfig.breadthCards?.length || displayConfig.volatilityCards?.length"
        class="market-terminal__overview-side"
      >
        <article class="market-terminal__side-panel">
          <div class="market-terminal__panel-head">
            <h3>大盘广度</h3>
            <span class="market-terminal__info-dot">i</span>
          </div>
          <p class="market-terminal__side-subtitle">{{ displayConfig.breadthSubtitle }}</p>

          <div v-if="displayConfig.breadthCards?.length" class="market-terminal__breadth-grid">
            <article
              v-for="item in displayConfig.breadthCards"
              :key="item.id"
              class="market-terminal__breadth-card"
            >
              <div class="market-terminal__breadth-head">
                <strong>{{ item.title }}</strong>
                <span>{{ item.value }}</span>
              </div>
              <div class="market-terminal__breadth-meta">
                <b>{{ item.tag }}</b>
                <em>{{ item.delta }}</em>
              </div>
              <div class="market-terminal__breadth-track">
                <i :style="{ width: `${parsePercent(item.value)}%` }"></i>
              </div>
            </article>
          </div>
        </article>

        <article v-if="displayConfig.volatilityCards?.length" class="market-terminal__side-panel">
          <div class="market-terminal__panel-head">
            <h3>波动与相关性</h3>
            <span class="market-terminal__info-dot">i</span>
          </div>

          <div class="market-terminal__vol-grid">
            <article
              v-for="item in displayConfig.volatilityCards"
              :key="item.id"
              class="market-terminal__vol-card"
            >
              <div class="market-terminal__vol-top">
                <span>{{ item.title }}</span>
                <b :class="badgeClass(item.badgeTone)">{{ item.badge }}</b>
              </div>
              <strong>{{ item.value }}</strong>
              <p>{{ item.description }}</p>
              <small>{{ item.ranges }}</small>
            </article>
          </div>
        </article>
      </div>
    </section>

    <section
      :id="detailSectionId"
      class="market-terminal__detail-section market-detail-section-shell"
    >
      <div class="market-terminal__panel-head market-detail-section-heading">
        <h4>{{ marketDetailTitle }}</h4>
        <button
          type="button"
          class="market-terminal__toolbar-btn market-detail-section-toggle"
          :aria-expanded="marketDetailExpanded"
          aria-controls="market-terminal-detail-content"
          @click="marketDetailExpanded = !marketDetailExpanded"
        >
          {{ marketDetailExpanded ? '收起' : '展开' }}
        </button>
      </div>
      <TerminalDetailPanel
        v-if="marketDetailExpanded"
        id="market-terminal-detail-content"
        title="市场明细"
        :market-id="displayConfig.id"
        :columns="displayConfig.detailColumns"
        :groups="displayConfig.detailGroups"
        :readonly="readonlyDetails"
        @index-chart="(code, name) => emit('index-chart', code, name)"
      />
    </section>

    <section
      :id="`${displayConfig.id}-market-rotation`"
      v-if="displayConfig.rotationButtonLabel"
      class="market-terminal__rotation"
    >
      <button type="button" class="market-terminal__rotation-button" @click="toggleRotation">
        <span>{{ rotationExpanded ? '▼' : '▶' }}</span>
        {{ displayConfig.rotationButtonLabel }}
      </button>

      <div
        v-if="rotationExpanded && displayConfig.rotationHeatmap?.length"
        class="market-terminal__rotation-heatmap"
      >
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
                <small class="market-terminal__rotation-source">
                  <a
                    v-if="row.sourceUrl"
                    :href="row.sourceUrl"
                    target="_blank"
                    rel="noopener noreferrer"
                    >{{ row.source }}</a
                  >
                  <span v-else-if="row.source">{{ row.source }}</span>
                  {{ row.observationDate || '暂无数据'
                  }}{{
                    row.dataStatus === 'stale'
                      ? ' · 待更新'
                      : row.dataStatus === 'partial'
                      ? ' · 部分数据'
                      : ''
                  }}
                </small>
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

      <div
        v-else-if="rotationExpanded && displayConfig.rotationSections?.length"
        class="market-terminal__rotation-grid"
      >
        <article
          v-for="section in displayConfig.rotationSections"
          :key="section.id"
          class="market-terminal__rotation-panel"
        >
          <h4>{{ section.title }}</h4>
          <div class="market-terminal__rotation-list">
            <span
              v-for="item in section.items"
              :key="item.id"
              class="market-terminal__rotation-chip"
            >
              {{ item.label }}
              <b>{{ item.symbol }}</b>
            </span>
          </div>
        </article>
      </div>

      <div
        v-else-if="rotationExpanded && displayConfig.rotationList?.length"
        class="market-terminal__rotation-list"
      >
        <span
          v-for="item in displayConfig.rotationList"
          :key="item.id"
          class="market-terminal__rotation-chip"
        >
          {{ item.label }}
          <b>{{ item.symbol }}</b>
        </span>
      </div>
    </section>

    <Teleport to="body">
      <div
        v-if="chartModal.visible"
        class="market-terminal-chart-modal"
        @click.self="closeTickerChart"
      >
        <ChartExpand
          :title="`${chartModal.name || chartModal.symbol} 走势`"
          class="market-terminal-chart-modal__dialog"
        >
          <div class="market-terminal-chart-modal__header">
            <div>
              <p class="market-terminal-chart-modal__eyebrow">{{ chartModal.symbol }}</p>
              <h3>{{ chartModal.name || chartModal.symbol }} 走势</h3>
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
              正在加载 {{ chartModal.symbol }} 的走势...
            </div>
            <div
              ref="chartContainerRef"
              class="market-terminal-chart-modal__widget"
              :class="{ 'is-hidden': chartModal.loading }"
            ></div>
          </div>
        </ChartExpand>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
  import HedgeBoardSubnav from './HedgeBoardSubnav.vue';
  import ChartExpand from './ChartExpand.vue';
  import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
  import {
    getMarketDetail,
    type MarketDetailResponse,
    AShareDashboardResponse,
    AShareIndexSnapshot,
  } from '@/api/hedgeResearch';
  import { mergeTerminalMarket } from '../nativeData/marketDetailAdapter';

  import TerminalDetailPanel from './TerminalDetailPanel.vue';
  import type {
    MarketTerminalPageConfig,
    OverviewCard,
    RotationHeatmapRow,
    TerminalMarketId,
    TerminalTone,
  } from '../nativeData/marketTerminal';

  function jumpToMarketSection(id: string) {
    document.getElementById(id)?.scrollIntoView({
      behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',
      block: 'start',
    });
  }

  interface MarketTab {
    id: TerminalMarketId;
    label: string;
    path: string;
  }

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

  const props = defineProps<{
    config: MarketTerminalPageConfig;
    marketTabs: MarketTab[];
    detailSectionId?: string;
    dashboard?: AShareDashboardResponse | null;
    readonlyDetails?: boolean;
  }>();

  const marketSnapshot = ref<MarketDetailResponse | null>(null);
  const marketLoading = ref(false);
  const marketError = ref(false);
  let marketRequestId = 0;
  let marketTimer: ReturnType<typeof setInterval> | undefined;
  const displayConfig = computed(() =>
    ['us', 'global'].includes(props.config.id)
      ? mergeTerminalMarket(props.config, marketSnapshot.value?.rows ?? [])
      : props.config,
  );
  async function loadMarket() {
    const market = props.config.id;
    if (market !== 'us' && market !== 'global') return;
    const requestId = ++marketRequestId;
    marketLoading.value = true;
    try {
      const result = await getMarketDetail(market);
      if (requestId === marketRequestId) {
        marketSnapshot.value = result;
        marketError.value = false;
      }
    } catch {
      if (requestId === marketRequestId) marketError.value = true;
    } finally {
      if (requestId === marketRequestId) marketLoading.value = false;
    }
  }
  watch(
    () => props.config.id,
    () => {
      ++marketRequestId;
      marketSnapshot.value = null;
      clearInterval(marketTimer);
      void loadMarket();
      if (['us', 'global'].includes(props.config.id))
        marketTimer = setInterval(loadMarket, 300_000);
    },
    { immediate: true },
  );
  onBeforeUnmount(() => {
    ++marketRequestId;
    clearInterval(marketTimer);
  });

  const emit = defineEmits<{ (event: 'index-chart', code: string, name: string): void }>();
  const rotationExpanded = ref(true);
  const marketDetailExpanded = ref(false);
  const rotationSortState = ref<SortState | null>(null);
  const chartContainerRef = ref<HTMLDivElement | null>(null);
  const chartModal = ref<ChartModalState>({
    visible: false,
    loading: false,
    symbol: '',
    name: '',
    tvSymbol: '',
    error: '',
  });
  const aShareSnapshots = computed<AShareIndexSnapshot[]>(() =>
    props.config.id === 'aShare' ? props.dashboard?.marketDetail.data || [] : [],
  );

  const aShareCoreCodes = ['000300', '000852', '399006', '000688'];
  const aShareThemeCodes = ['931071', '931238', '932082', 'H30590'];
  const asNumber = (value: string | number | null | undefined) => {
    const parsed = value == null ? NaN : Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const asChange = (value: string | number | null | undefined) => {
    const parsed = asNumber(value);
    return parsed == null ? '—' : `${parsed > 0 ? '+' : ''}${parsed.toFixed(2)}%`;
  };
  const toOverviewCard = (
    row: AShareIndexSnapshot | undefined,
    code: string,
    fallback: string,
  ): OverviewCard => {
    const value = asNumber(row?.return1dPct);
    return {
      id: `a-live-${code}`,
      symbol: code,
      label: row?.name || fallback,
      change: asChange(row?.return1dPct),
      price: row?.close == null ? undefined : String(row.close),
      spark: (row?.spark || []).map(Number).filter(Number.isFinite),
      tone: value == null ? 'neutral' : value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral',
    };
  };
  const displayOverviewCards = computed(() => {
    if (props.config.id !== 'aShare') return displayConfig.value.overviewCards || [];
    const labels: Record<string, string> = {
      '000300': '沪深300',
      '000852': '中证1000',
      '399006': '创业板指',
      '000688': '科创50',
    };
    return aShareCoreCodes.map((code) =>
      toOverviewCard(
        aShareSnapshots.value.find((row) => row.code === code),
        code,
        labels[code],
      ),
    );
  });
  const displayMoverCards = computed(() => {
    if (props.config.id !== 'aShare') return displayConfig.value.moverCards || [];
    const labels: Record<string, string> = {
      '931071': 'AI',
      '931238': '金股',
      '932082': '医药',
      H30590: '机器人',
    };
    return aShareThemeCodes.map((code) =>
      toOverviewCard(
        aShareSnapshots.value.find((row) => row.code === code),
        code,
        labels[code],
      ),
    );
  });

  const marketDetailTitle = computed(
    () =>
      ({
        us: '美股市场明细',
        global: '全球市场明细',
        aShare: 'A股市场明细',
        gold: '商品市场明细',
        crypto: '加密市场明细',
      }[props.config.id] ?? '市场明细'),
  );

  let tradingViewScriptPromise: Promise<void> | null = null;
  const rotationColumns = [
    { key: 'd1', label: '1日' },
    { key: 'w1', label: '1周' },
    { key: 'm1', label: '1月' },
    { key: 'ytd', label: '年初至今' },
    { key: 'y1', label: '过去1年' },
  ] as const;
  const sortedRotationRows = computed(() => {
    const rows = [...(displayConfig.value.rotationHeatmap ?? [])];
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

  const MACRO_TICKER_TO_TV_SYMBOL: Record<string, string> = {
    VIX: 'CBOE:VIX',
    DSPX: 'INDEX:DSPX',
    DXY: 'TVC:DXY',
    US2Y: 'TVC:US02Y',
    US10Y: 'TVC:US10Y',
    US30Y: 'TVC:US30Y',
    CN02Y: 'TVC:CN02Y',
    CN10Y: 'TVC:CN10Y',
    CN30Y: 'TVC:CN30Y',
    USDCNH: 'FX_IDC:USDCNH',
    TLT: 'NASDAQ:TLT',
    HYG: 'AMEX:HYG',
    MOVE: 'TVC:MOVE',
    DFF: 'FRED:DFF',
    SOFR: 'FRED:SOFR',
    DFII10: 'FRED:DFII10',
    T10YIE: 'FRED:T10YIE',
    CPIAUCSL: 'FRED:CPIAUCSL',
    PCEPI: 'FRED:PCEPI',
    UNRATE: 'FRED:UNRATE',
    M2SL: 'FRED:M2SL',
    WALCL: 'FRED:WALCL',
    WDTGAL: 'FRED:WDTGAL',
    RRPONTTLD: 'FRED:RRPONTTLD',
    NETLIQ: 'FRED:WALCL-FRED:WDTGAL-FRED:RRPONTTLD',
  };

  const US_TICKER_TO_TV_SYMBOL: Record<string, string> = {
    SPY: 'AMEX:SPY',
    QQQ: 'NASDAQ:QQQ',
    DIA: 'AMEX:DIA',
    DJI: 'TVC:DJI',
    GDX: 'AMEX:GDX',
    IWM: 'AMEX:IWM',
    MDY: 'AMEX:MDY',
    MAGS: 'NASDAQ:MAGS',
    RSP: 'AMEX:RSP',
    QQEW: 'NASDAQ:QQEW',
    SCHD: 'AMEX:SCHD',
    XLK: 'AMEX:XLK',
    XLV: 'AMEX:XLV',
    XLF: 'AMEX:XLF',
    XLY: 'AMEX:XLY',
    XLC: 'AMEX:XLC',
    XLI: 'AMEX:XLI',
    XLP: 'AMEX:XLP',
    XLE: 'AMEX:XLE',
    XLU: 'AMEX:XLU',
    XLRE: 'AMEX:XLRE',
    XLB: 'AMEX:XLB',
    SOXX: 'NASDAQ:SOXX',
    ITA: 'AMEX:ITA',
    IBB: 'NASDAQ:IBB',
    KRE: 'AMEX:KRE',
    XHB: 'AMEX:XHB',
    ARKK: 'AMEX:ARKK',
    IBIT: 'NASDAQ:IBIT',
    BOTZ: 'NYSEARCA:BOTZ',
    CLOU: 'NASDAQ:CLOU',
    ICLN: 'NASDAQ:ICLN',
    XSD: 'AMEX:XSD',
  };

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

  const A_SHARE_TICKER_TO_TV_SYMBOL: Record<string, string> = {
    '000300': 'SSE:000300',
    '000016': 'SSE:000016',
    '399006': 'SZSE:399006',
    '000852': 'SSE:000852',
    '000688': 'SSE:000688',
    '931071': 'SSE:931071',
    '931238': 'SSE:931238',
    '932082': 'SSE:932082',
    H30590: 'SSE:H30590',
    证券: 'SSE:512000',
    芯片: 'SSE:512760',
    电新: 'SZSE:159755',
    银行: 'SSE:512800',
    消费: 'SZSE:159928',
    黄金: 'SSE:518880',
  };

  const GOLD_TICKER_TO_TV_SYMBOL: Record<string, string> = {
    XAUUSD: 'OANDA:XAUUSD',
    GLD: 'AMEX:GLD',
    XAGUSD: 'OANDA:XAGUSD',
    GDX: 'AMEX:GDX',
    GDXJ: 'AMEX:GDXJ',
    XAUXAG: 'OANDA:XAUUSD',
    'XAU/COPPER': 'OANDA:XAUUSD/VANTAGE:COPPER',
    USOIL: 'TVC:USOIL',
    BRENT: 'TVC:UKOIL',
    'HG1!': 'COMEX:HG1!',
    'NG1!': 'NYMEX:NG1!',
    BCOM: 'TVC:BCOM',
    SPGSCI: 'SP:SPGSCI',
    PLATINUM: 'OANDA:XPTUSD',
    PALLADIUM: 'OANDA:XPDUSD',
  };

  const CRYPTO_TICKER_TO_TV_SYMBOL: Record<string, string> = {
    BTC: 'BINANCE:BTCUSDT',
    ETH: 'BINANCE:ETHUSDT',
    SOL: 'BINANCE:SOLUSDT',
    BNB: 'BINANCE:BNBUSDT',
    XRP: 'BINANCE:XRPUSDT',
    DOGE: 'BINANCE:DOGEUSDT',
    TON: 'BINANCE:TONUSDT',
    TOTAL: 'CRYPTOCAP:TOTAL',
    TOTAL2: 'CRYPTOCAP:TOTAL2',
    TOTAL3: 'CRYPTOCAP:TOTAL3',
    'BTC.D': 'CRYPTOCAP:BTC.D',
    USDC: 'CRYPTOCAP:USDC',
    COIN: 'NASDAQ:COIN',
    HOOD: 'NASDAQ:HOOD',
    BMNR: 'NASDAQ:BMNR',
    CRCL: 'NYSE:CRCL',
    MSTR: 'NASDAQ:MSTR',
    IBIT: 'NASDAQ:IBIT',
    'OTHERS.D': 'CRYPTOCAP:OTHERS.D',
    'USDT.D': 'CRYPTOCAP:USDT.D',
    ETHBETA: 'BINANCE:ETHUSDT',
    MARA: 'NASDAQ:MARA',
    RIOT: 'NASDAQ:RIOT',
    UNI: 'BINANCE:UNIUSDT',
    RNDR: 'BINANCE:RNDRUSDT',
  };

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
    if (!state || state.key !== key) return '⇅';
    return state.direction === 'desc' ? '↓' : '↑';
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

  function parseTone(value: string): TerminalTone {
    const normalized = value.trim();
    return normalized.startsWith('-') || normalized.includes('▼') ? 'negative' : 'positive';
  }

  function toneClass(tone?: TerminalTone) {
    return tone ? `is-${tone}` : '';
  }

  function badgeClass(tone?: TerminalTone) {
    return tone ? `is-badge-${tone}` : 'is-badge-neutral';
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

  function sparkStrokeClass(value: string) {
    return parseTone(value) === 'negative' ? 'is-stroke-down' : 'is-stroke-up';
  }

  function parsePercent(value: string) {
    return Number.parseFloat(value.replace('%', '')) || 0;
  }

  function heatmapClass(value: string) {
    return [
      'market-terminal__rotation-cell',
      parseTone(value) === 'negative' ? 'is-negative-cell' : 'is-positive-cell',
    ];
  }

  function resolveTradingViewSymbol(marketId: TerminalMarketId, symbol: string, tvSymbol?: string) {
    if (tvSymbol) return tvSymbol;
    const normalized = symbol.trim().toUpperCase();
    if (marketId === 'macro') {
      return MACRO_TICKER_TO_TV_SYMBOL[normalized] ?? '';
    }
    if (marketId === 'us') {
      return US_TICKER_TO_TV_SYMBOL[normalized] ?? '';
    }
    if (marketId === 'global') {
      return GLOBAL_TICKER_TO_TV_SYMBOL[normalized] ?? '';
    }
    if (marketId === 'aShare') {
      return (
        A_SHARE_TICKER_TO_TV_SYMBOL[symbol.trim()] ?? A_SHARE_TICKER_TO_TV_SYMBOL[normalized] ?? ''
      );
    }
    if (marketId === 'gold') {
      return GOLD_TICKER_TO_TV_SYMBOL[normalized] ?? '';
    }
    if (marketId === 'crypto') {
      return CRYPTO_TICKER_TO_TV_SYMBOL[normalized] ?? '';
    }
    return '';
  }

  function canOpenTickerChart(symbol: string, tvSymbol?: string) {
    return Boolean(resolveTradingViewSymbol(props.config.id, symbol, tvSymbol));
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
    const tvSymbol = resolveTradingViewSymbol(props.config.id, symbol, tvSymbolOverride);
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
      chartModal.value.error = error instanceof Error ? error.message : '走势图加载失败';
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
  @import './marketDetailSection.less';

  .market-terminal {
    --terminal-border: rgb(201 213 226 / 72%);
    --terminal-border-strong: rgb(170 186 203 / 82%);
    --terminal-panel-bg: linear-gradient(180deg, rgb(255 255 255 / 98%), rgb(243 248 252 / 96%));
    --terminal-card-bg: linear-gradient(180deg, rgb(255 255 255 / 98%), rgb(247 250 252 / 96%));
    --terminal-chip-bg: rgb(240 246 250 / 96%);
    --terminal-text: #16303a;
    --terminal-muted: #6e8395;
    --terminal-accent: #2d5b74;
    --terminal-shadow: 0 18px 40px rgb(15 23 42 / 6%);

    display: flex;
    flex-direction: column;
    gap: 14px;
    width: 100%;
    min-width: 0;
    max-width: 100%;
    container: market-terminal / inline-size;
  }

  .market-terminal__overview-strip,
  .market-terminal__detail,
  .market-terminal__rotation {
    border: 1px solid var(--terminal-border);
    border-radius: 18px;
    background: var(--terminal-panel-bg), #fff;
    box-shadow: var(--terminal-shadow);
  }

  .market-terminal__detail-section {
    display: grid;
    min-width: 0;
  }

  .market-terminal__detail-section .market-detail-section-heading {
    margin-bottom: 0;
  }

  .market-terminal__overview-strip {
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
    min-width: 0;
    max-width: 100%;
    padding: 12px;
    gap: 12px;
  }

  .market-terminal__overview-strip.is-single {
    grid-template-columns: 1fr;
  }

  .market-terminal__overview-panel,
  .market-terminal__side-panel {
    min-width: 0;
    padding: 12px;
    border: 1px solid rgb(201 213 226 / 58%);
    background: rgb(255 255 255 / 92%);
  }

  .market-terminal__overview-side {
    display: grid;
    min-width: 0;
    gap: 12px;
  }

  .market-terminal__panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 8px;
  }

  .market-terminal__panel-head h3 {
    margin: 0;
    color: var(--terminal-accent);
    font-size: 14px;
  }

  .market-terminal__mini-chip,
  .market-terminal__info-dot {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--terminal-border-strong);
    background: var(--terminal-chip-bg);
    color: var(--terminal-text);
    font-size: 11px;
    font-weight: 700;
  }

  .market-terminal__mini-chip {
    padding: 6px 10px;
  }

  .market-terminal__info-dot {
    width: 18px;
    height: 18px;
    border-radius: 50%;
  }

  .market-terminal__market-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .market-terminal__market-card {
    min-width: 0;
    padding: 10px;
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    border: 1px solid rgb(201 213 226 / 78%);
    background: var(--terminal-card-bg);
    text-align: left;
  }

  .market-terminal__market-card--mover {
    border-color: rgb(176 193 210 / 80%);
  }

  .market-terminal__market-card.is-clickable:hover,
  .market-terminal__name-button.is-clickable:hover {
    transform: translateY(-1px);
    border-color: rgb(116 146 170 / 68%);
    box-shadow: 0 14px 32px rgb(15 23 42 / 8%);
  }

  .market-terminal__market-symbol,
  .market-terminal__market-category,
  .market-terminal__vol-top span {
    display: block;
    color: var(--terminal-muted);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .market-terminal__market-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
    margin-top: 6px;
  }

  .market-terminal__market-head strong {
    color: var(--terminal-text);
    font-size: 14px;
    line-height: 1.25;
  }

  .market-terminal__market-head em {
    font-size: 14px;
    font-style: normal;
    font-weight: 800;
  }

  .market-terminal__market-price {
    display: block;
    margin-top: 10px;
    color: var(--terminal-muted);
    font-size: 12px;
    font-weight: 700;
  }

  .market-terminal__market-spark {
    display: block;
    width: 100%;
    height: 28px;
    margin-top: 8px;
  }

  .market-terminal__market-spark polyline,
  .market-terminal__sparkline polyline {
    stroke-width: 1.5;
    stroke-linecap: round;
    fill: none;
    stroke-linejoin: round;
  }

  .market-terminal__subhead {
    margin: 14px 0 10px;
    padding-top: 12px;
    border-top: 1px solid var(--terminal-border);
    color: var(--terminal-muted);
    font-size: 12px;
    font-weight: 700;
  }

  .market-terminal__side-subtitle {
    margin: 0 0 10px;
    color: var(--terminal-muted);
    font-size: 12px;
  }

  .market-terminal__breadth-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .market-terminal__breadth-card {
    min-width: 0;
    padding: 10px;
    border: 1px dashed rgb(191 205 218 / 74%);
    background: rgb(246 250 252 / 92%);
  }

  .market-terminal__breadth-head,
  .market-terminal__breadth-meta,
  .market-terminal__vol-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .market-terminal__breadth-head strong,
  .market-terminal__vol-card strong {
    color: var(--terminal-text);
    font-size: 14px;
  }

  .market-terminal__vol-top {
    flex-wrap: wrap;
  }

  .market-terminal__breadth-head span {
    color: var(--terminal-muted);
    font-weight: 800;
  }

  .market-terminal__breadth-meta {
    margin-top: 8px;
    color: var(--terminal-muted);
    font-size: 11px;
  }

  .market-terminal__breadth-meta em {
    color: #5b89ac;
    font-style: normal;
    font-weight: 700;
  }

  .market-terminal__breadth-track {
    height: 5px;
    margin-top: 10px;
    background: rgb(120 141 162 / 16%);
  }

  .market-terminal__breadth-track i {
    display: block;
    height: 100%;
    background: #6a8198;
  }

  .market-terminal__vol-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
  }

  .market-terminal__vol-card {
    min-width: 0;
    padding: 10px;
    border: 1px dashed rgb(191 205 218 / 74%);
    background: rgb(246 250 252 / 92%);
  }

  .market-terminal__vol-card p,
  .market-terminal__vol-card small {
    display: block;
    margin: 8px 0 0;
    color: #617073;
    font-size: 12px;
    line-height: 1.6;
  }

  .market-terminal__detail {
    padding: 12px;
  }

  .market-terminal__panel-head--detail {
    margin-bottom: 12px;
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
    color: #88959a;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
  }

  .market-terminal__group-row td {
    padding: 8px 10px;
    background: rgb(241 246 251 / 92%);
  }

  .market-terminal__group-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-start;
    gap: 12px;
  }

  .market-terminal__group-toggle {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: #18313c;
    font-size: 13px;
    font-weight: 700;
  }

  .market-terminal__sort-button,
  .market-terminal__rotation-sort {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border: 1px solid rgb(201 213 226 / 70%);
    border-radius: 999px;
    background: transparent;
    color: var(--terminal-muted);
    font-size: 11px;
    font-weight: 700;
  }

  .market-terminal__sort-button.is-active,
  .market-terminal__rotation-sort.is-active,
  .market-terminal__sort-button:hover,
  .market-terminal__rotation-sort:hover {
    border-color: rgb(116 146 170 / 68%);
    background: rgb(236 243 249 / 92%);
    color: var(--terminal-accent);
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
    color: var(--terminal-accent);
  }

  .market-terminal__name-button {
    display: block;
    width: 100%;
    padding: 0;
    transition: transform 0.2s ease;
    border: none;
    background: transparent;
    text-align: left;
  }

  .market-terminal__spark-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    padding: 0;
    border: none;
    background: transparent;
  }

  .market-terminal__name-button.is-clickable .market-terminal__name-wrap strong,
  .market-terminal__name-button.is-clickable .market-terminal__name-wrap span {
    cursor: pointer;
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
    border: 1px solid rgb(201 213 226 / 86%);
    color: var(--terminal-muted);
    font-size: 11px;
    font-weight: 700;
  }

  .market-terminal__sparkline {
    width: 72px;
    height: 24px;
  }

  .market-terminal__high-cell-td {
    padding-right: 12px;
    padding-left: 12px;
  }

  .market-terminal__high-cell {
    display: flex;
    align-items: center;
    width: 100%;
    min-width: 136px;
  }

  .market-terminal__high-track {
    flex: 1;
    width: 100%;
    height: 4px;
    overflow: hidden;
    border-radius: 999px;
    background: rgb(184 198 212 / 24%);
  }

  .market-terminal__high-cell span {
    flex: 0 0 52px;
    width: 52px;
    margin-left: 8px;
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

  .market-terminal__rotation {
    padding: 12px;
  }

  .market-terminal__rotation-button {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    border: none;
    background: transparent;
    color: var(--terminal-text);
    font-size: 13px;
    font-weight: 700;
  }

  .market-terminal__rotation-sort {
    justify-content: center;
    width: 100%;
  }

  .market-terminal__overview-panel,
  .market-terminal__side-panel,
  .market-terminal__market-card,
  .market-terminal__rotation-panel,
  .market-terminal__rotation-chip {
    border-radius: 12px;
  }

  .market-terminal__rotation-table {
    width: 100%;
    min-width: 920px;
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
    position: sticky;
    z-index: 1;
    left: 0;
    background: #f8fbfd;
    text-align: left !important;
  }

  .market-terminal__rotation-source {
    display: block;
    margin-top: 4px;
    color: #64748b;
    font-size: 11px;
    white-space: nowrap;
  }

  .market-terminal__rotation-name strong,
  .market-terminal__rotation-name span {
    display: block;
  }

  .market-terminal__rotation-name span {
    margin-top: 4px;
    color: var(--terminal-muted);
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

  .market-terminal__rotation-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 12px;
  }

  .market-terminal__rotation-panel {
    padding: 12px;
    border: 1px solid rgb(201 213 226 / 62%);
    background: rgb(246 250 252 / 92%);
  }

  .market-terminal__rotation-panel h4 {
    margin: 0 0 10px;
    color: #18313c;
    font-size: 13px;
  }

  .market-terminal__rotation-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }

  .market-terminal__rotation-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    border: 1px solid rgb(201 213 226 / 72%);
    background: rgb(255 255 255 / 86%);
    color: #5f7485;
    font-size: 12px;
    font-weight: 700;
  }

  .market-terminal__rotation-chip b {
    color: #18313c;
  }

  .market-terminal-chart-modal {
    display: flex;
    position: fixed;
    z-index: 1200;
    align-items: center;
    justify-content: center;
    padding: 32px;
    background: rgb(9 20 17 / 46%);
    inset: 0;
    backdrop-filter: blur(8px);
  }

  .market-terminal-chart-modal__dialog {
    width: min(72vw, 1440px);
    max-width: calc(100vw - 48px);
    overflow: hidden;
    border: 1px solid rgb(201 213 226 / 82%);
    border-radius: 24px;
    background: linear-gradient(180deg, rgb(255 255 255 / 99%), rgb(244 248 252 / 98%)), #fff;
    box-shadow: 0 30px 80px rgb(15 23 42 / 18%);
  }

  .market-terminal-chart-modal__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 20px;
    padding: 20px 24px 12px;
  }

  .market-terminal-chart-modal__eyebrow {
    margin: 0 0 6px;
    color: var(--terminal-muted);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .market-terminal-chart-modal__header h3 {
    margin: 0;
    color: var(--terminal-text);
    font-size: 24px;
    line-height: 1.2;
  }

  .market-terminal-chart-modal__close {
    padding: 10px 14px;
    border: 1px solid rgb(201 213 226 / 82%);
    border-radius: 999px;
    background: rgb(245 249 252 / 96%);
    color: var(--terminal-text);
    font-size: 12px;
    font-weight: 700;
  }

  .market-terminal-chart-modal__body {
    height: min(78vh, 860px);
    padding: 0 12px 12px;
  }

  .market-terminal-chart-modal__state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: min(78vh, 860px);
    background: linear-gradient(180deg, rgb(251 253 255 / 98%), rgb(243 248 252 / 98%));
    color: var(--terminal-muted);
    font-size: 14px;
    font-weight: 700;
  }

  .market-terminal-chart-modal__state.is-error {
    color: #c95b48;
  }

  .market-terminal-chart-modal__widget {
    height: min(78vh, 860px);
  }

  .market-terminal-chart-modal__widget.is-hidden {
    display: none;
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

  .is-badge-neutral,
  .is-badge-negative,
  .is-badge-accent {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    padding: 4px 8px;
    border: 1px solid rgb(201 213 226 / 72%);
    background: rgb(243 247 250 / 94%);
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
  }

  .is-badge-negative {
    color: #d26b5a;
  }

  .is-badge-accent {
    color: #4b77b9;
  }

  @container market-terminal (max-width: 1000px) {
    .market-terminal__overview-strip {
      grid-template-columns: 1fr;
    }

    .market-terminal__vol-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @container market-terminal (max-width: 560px) {
    .market-terminal__market-grid,
    .market-terminal__breadth-grid,
    .market-terminal__vol-grid,
    .market-terminal__rotation-grid {
      grid-template-columns: 1fr;
    }

    .market-terminal-chart-modal {
      padding: 16px;
    }

    .market-terminal-chart-modal__dialog {
      width: calc(100vw - 32px);
    }

    .market-terminal-chart-modal__header {
      flex-direction: column;
      align-items: stretch;
    }

    .market-terminal-chart-modal__body,
    .market-terminal-chart-modal__state,
    .market-terminal-chart-modal__widget {
      min-height: 520px;
    }
  }
</style>
