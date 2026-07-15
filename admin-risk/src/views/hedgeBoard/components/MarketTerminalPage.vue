<template>
  <div class="market-terminal">
    <section v-if="config.overviewCards?.length" class="market-terminal__overview-strip">
      <article class="market-terminal__overview-panel">
        <div class="market-terminal__panel-head">
          <h3>大盘表现</h3>
          <div v-if="config.overviewChip" class="market-terminal__mini-chip">{{ config.overviewChip }}</div>
        </div>

        <div class="market-terminal__market-grid">
          <button
            v-for="item in config.overviewCards"
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
            <svg class="market-terminal__market-spark" viewBox="0 0 80 22" preserveAspectRatio="none">
              <polyline :points="compactSparkline(item.spark, 80, 22)" :class="sparkStrokeClass(item.change)" />
            </svg>
          </button>
        </div>

        <div class="market-terminal__subhead">当日最大波动</div>

        <div class="market-terminal__market-grid">
          <button
            v-for="item in config.moverCards"
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
            <svg class="market-terminal__market-spark" viewBox="0 0 80 22" preserveAspectRatio="none">
              <polyline :points="compactSparkline(item.spark, 80, 22)" :class="sparkStrokeClass(item.change)" />
            </svg>
          </button>
        </div>
      </article>

      <div v-if="config.breadthCards?.length || config.volatilityCards?.length" class="market-terminal__overview-side">
        <article class="market-terminal__side-panel">
          <div class="market-terminal__panel-head">
            <h3>大盘广度</h3>
            <span class="market-terminal__info-dot">i</span>
          </div>
          <p class="market-terminal__side-subtitle">{{ config.breadthSubtitle }}</p>

          <div v-if="config.breadthCards?.length" class="market-terminal__breadth-grid">
            <article
              v-for="item in config.breadthCards"
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
                <i :style="{ width: `${parsePercent(item.value)}%` }" />
              </div>
            </article>
          </div>
        </article>

        <article v-if="config.volatilityCards?.length" class="market-terminal__side-panel">
          <div class="market-terminal__panel-head">
            <h3>波动与相关性</h3>
            <span class="market-terminal__info-dot">i</span>
          </div>

          <div class="market-terminal__vol-grid">
            <article
              v-for="item in config.volatilityCards"
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

    <TerminalDetailPanel
      title="市场明细"
      :market-id="config.id"
      :columns="config.detailColumns"
      :groups="config.detailGroups"
    />

    <section v-if="config.rotationButtonLabel" class="market-terminal__rotation">
      <button type="button" class="market-terminal__rotation-button" @click="toggleRotation">
        <span>{{ rotationExpanded ? '▼' : '▶' }}</span>
        {{ config.rotationButtonLabel }}
      </button>

      <div v-if="rotationExpanded && config.rotationHeatmap?.length" class="market-terminal__rotation-heatmap">
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

      <div v-else-if="rotationExpanded && config.rotationSections?.length" class="market-terminal__rotation-grid">
        <article
          v-for="section in config.rotationSections"
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

      <div v-else-if="rotationExpanded && config.rotationList?.length" class="market-terminal__rotation-list">
        <span
          v-for="item in config.rotationList"
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
        <div class="market-terminal-chart-modal__dialog">
          <div class="market-terminal-chart-modal__header">
            <div>
              <p class="market-terminal-chart-modal__eyebrow">{{ chartModal.symbol }}</p>
              <h3>{{ chartModal.name || chartModal.symbol }} 走势</h3>
            </div>
            <button type="button" class="market-terminal-chart-modal__close" @click="closeTickerChart">
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
            />
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, ref } from 'vue';
  import TerminalDetailPanel from './TerminalDetailPanel.vue';
  import type {
    MarketTerminalPageConfig,
    RotationHeatmapRow,
    TerminalMarketId,
    TerminalTableGroup,
    TerminalTableRow,
    TerminalTone,
  } from '../nativeData/marketTerminal';

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
  }>();

  const expandedGroups = ref<Record<string, boolean>>(
    Object.fromEntries(props.config.detailGroups.map((group) => [group.label, true])),
  );
  const tableSortState = ref<SortState | null>(null);
  const rotationExpanded = ref(true);
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

  let tradingViewScriptPromise: Promise<void> | null = null;
  const rotationColumns = [
    { key: 'd1', label: '1日' },
    { key: 'w1', label: '1周' },
    { key: 'm1', label: '1月' },
    { key: 'ytd', label: '年初至今' },
    { key: 'y1', label: '过去1年' },
  ] as const;
  const signalColumnKeys = ['d10', 'd20', 'd50', 'd200', 'x2050'] as const;
  const sortedRotationRows = computed(() => {
    const rows = [...(props.config.rotationHeatmap ?? [])];
    const state = rotationSortState.value;
    if (!state) return rows;
    return rows.sort((left, right) => compareValues(readRotationValue(left, state.key), readRotationValue(right, state.key), state.direction));
  });
  const displayGroups = computed<TerminalTableGroup[]>(() => {
    const baseGroups = props.config.detailGroups.map((group) => ({
      ...group,
      rows: group.rows.filter((row) => !(props.config.id === 'gold' && row.id === 'gold-ratio-row')),
    }));

    if (props.config.id === 'gold') {
      return [
        ...baseGroups,
        {
          label: '相对比价',
          rows: [
            buildRatioRow('gold-ratio-xs', '金银比', 'XAU/XAG', '78.40', '-0.30%', '-1.90%', '-2.40%', '-1.10%', '-2.40%', '-4.60%', '-9.8%', [18, 18, 17, 17, 16, 16, 15, 15, 14, 14, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 8, 8, 8, 7], 'OANDA:XAUUSD/OANDA:XAGUSD'),
            buildRatioRow('gold-ratio-xc', '金铜比', 'XAU/COPPER', '523.1', '+0.20%', '+1.80%', '+0.90%', '+0.60%', '+0.90%', '+4.60%', '-6.2%', [14, 14, 15, 15, 15, 14, 13, 12, 12, 11, 10, 10, 9, 9, 8, 8, 8, 9, 10, 10, 11, 12, 12, 13], 'OANDA:XAUUSD/VANTAGE:COPPER'),
            buildRatioRow('gold-ratio-xo', '金油比', 'XAU/OIL', '28.6', '+0.50%', '-0.40%', '-1.20%', '-0.20%', '-1.20%', '+8.10%', '-7.4%', [10, 10, 11, 11, 12, 13, 13, 14, 14, 14, 13, 12, 12, 11, 11, 10, 10, 10, 11, 11, 12, 12, 13, 13], 'OANDA:XAUUSD/TVC:USOIL'),
            buildRatioRow('gold-ratio-xe', '金股比', 'XAU/SPX', '0.42', '+0.80%', '+6.20%', '+3.10%', '+1.10%', '+3.10%', '+9.80%', '-2.9%', [7, 7, 8, 8, 9, 10, 10, 11, 11, 12, 13, 13, 14, 15, 15, 16, 17, 17, 18, 19, 19, 20, 20, 21], 'OANDA:XAUUSD/SP:SPX'),
          ],
        },
      ];
    }

    if (props.config.id === 'crypto') {
      return [
        ...baseGroups,
        {
          label: '相对比价',
          rows: [
            buildRatioRow('crypto-ratio-btc-eth', 'BTC / ETH', 'BTC/ETH', '18.28', '+0.40%', '+4.90%', '+1.10%', '+0.70%', '+1.10%', '+15.20%', '-3.6%', [12, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 16, 17, 17, 18, 18, 18, 18, 19, 19, 19, 18, 18, 18], 'BINANCE:BTCUSDT/BINANCE:ETHUSDT'),
            buildRatioRow('crypto-ratio-btc-spx', 'BTC / SPX', 'BTC/SPX', '10.43', '+1.10%', '+36.80%', '+7.60%', '+3.20%', '+7.60%', '+76.40%', '-4.9%', [6, 7, 8, 9, 9, 10, 11, 11, 12, 13, 13, 14, 15, 15, 16, 17, 18, 18, 19, 20, 21, 21, 22, 23], 'COINBASE:BTCUSD/SP:SPX'),
            buildRatioRow('crypto-ratio-btc-xau', 'BTC / XAU', 'BTC/XAU', '26.94', '+0.70%', '+29.10%', '+5.20%', '+2.30%', '+5.20%', '+80.30%', '-3.1%', [8, 8, 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 15, 16, 17, 18, 18, 19, 20, 20, 21, 22, 23, 23], 'COINBASE:BTCUSD/OANDA:XAUUSD'),
            buildRatioRow('crypto-ratio-mstr-btc', 'MSTR / BTC', 'MSTR/BTC', '0.0237', '+0.60%', '+11.30%', '+2.80%', '+1.10%', '+2.80%', '+23.40%', '-5.7%', [10, 10, 10, 11, 11, 12, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16, 16, 17, 17, 18, 18, 18, 19], 'NASDAQ:MSTR/COINBASE:BTCUSD'),
            buildRatioRow('crypto-ratio-crcl-btc', 'CRCL / BTC', 'CRCL/BTC', '0.00189', '+0.90%', '+18.40%', '+4.20%', '+1.90%', '+4.20%', '+41.60%', '-4.4%', [9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 16, 16, 17, 17, 18, 18, 18, 19, 19, 20], 'NYSE:CRCL/COINBASE:BTCUSD'),
          ],
        },
      ];
    }

    return baseGroups;
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
    '证券': 'SSE:512000',
    '芯片': 'SSE:512760',
    '电新': 'SZSE:159755',
    '银行': 'SSE:512800',
    '消费': 'SZSE:159928',
    '黄金': 'SSE:518880',
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

  function toggleGroup(label: string) {
    expandedGroups.value[label] = !expandedGroups.value[label];
  }

  function isGroupExpanded(label: string) {
    return expandedGroups.value[label] ?? true;
  }

  function toggleRotation() {
    rotationExpanded.value = !rotationExpanded.value;
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

  function sortedGroupRows(group: TerminalTableGroup) {
    const rows = [...group.rows];
    const state = tableSortState.value;
    if (!state) return rows;
    return rows.sort((left, right) => compareValues(readTableValue(left, state.key), readTableValue(right, state.key), state.direction));
  }

  function buildRatioRow(
    id: string,
    name: string,
    symbol: string,
    price: string,
    d1: string,
    ytd: string,
    qtd: string,
    w1: string,
    m1: string,
    y1: string,
    high: string,
    spark: number[],
    tvSymbol: string,
  ): TerminalTableRow {
    return {
      id,
      name,
      symbol,
      tvSymbol,
      price,
      d1,
      ytd,
      qtd,
      w1,
      m1,
      y1,
      high,
      spark,
      d10: '▲',
      d20: '▲',
      d50: '▲',
      d200: '▲',
      x2050: '▲',
      x50200: '▲',
    };
  }

  function isSortableColumn(key: string) {
    return key !== 'spark';
  }

  function readTableValue(row: TerminalTableRow, key: string) {
    if (key === 'name') return row.name;
    if (key === 'symbol') return row.symbol;
    if (key === 'price') return parseDisplayNumber(row.price);
    if (key === 'high') return parseDisplayNumber(row.high);
    if (['d1', 'ytd', 'qtd', 'w1', 'm1', 'y1'].includes(key)) return parseDisplayNumber(row[key as keyof TerminalTableRow] as string);
    if (['d10', 'd20', 'd50', 'd200', 'x2050'].includes(key)) return arrowScore(row[key as keyof TerminalTableRow] as string);
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
    const normalized = value.trim();
    return normalized.startsWith('-') || normalized.includes('▼') ? 'negative' : 'positive';
  }

  function toneClass(tone?: TerminalTone) {
    return tone ? `is-${tone}` : '';
  }

  function badgeClass(tone?: TerminalTone) {
    return tone ? `is-badge-${tone}` : 'is-badge-neutral';
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
        const y = max === min ? height / 2 : height - 1 - ((value - min) / (max - min)) * (height - 2);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  }

  function sparkStrokeClass(value: string) {
    return parseTone(value) === 'negative' ? 'is-stroke-down' : 'is-stroke-up';
  }

  function highWidth(value: string) {
    const numeric = Number.parseFloat(value.replace('%', ''));
    const distance = Number.isFinite(numeric) ? Math.abs(numeric) : 0;
    return Math.max(36, Math.min(100, 100 - distance * 1.35));
  }

  function parsePercent(value: string) {
    return Number.parseFloat(value.replace('%', '')) || 0;
  }

  function heatmapClass(value: string) {
    return ['market-terminal__rotation-cell', parseTone(value) === 'negative' ? 'is-negative-cell' : 'is-positive-cell'];
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
      return A_SHARE_TICKER_TO_TV_SYMBOL[symbol.trim()] ?? A_SHARE_TICKER_TO_TV_SYMBOL[normalized] ?? '';
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
  .market-terminal {
    --terminal-border: rgba(201, 213, 226, 0.72);
    --terminal-border-strong: rgba(170, 186, 203, 0.82);
    --terminal-panel-bg: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 248, 252, 0.96));
    --terminal-card-bg: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 252, 0.96));
    --terminal-chip-bg: rgba(240, 246, 250, 0.96);
    --terminal-text: #16303a;
    --terminal-muted: #6e8395;
    --terminal-accent: #2d5b74;
    --terminal-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .market-terminal__overview-strip,
  .market-terminal__detail,
  .market-terminal__rotation {
    border: 1px solid var(--terminal-border);
    border-radius: 18px;
    background: var(--terminal-panel-bg), #fff;
    box-shadow: var(--terminal-shadow);
  }

  .market-terminal__overview-strip {
    display: grid;
    grid-template-columns: 1.05fr 1fr;
    gap: 12px;
    padding: 12px;
  }

  .market-terminal__overview-panel,
  .market-terminal__side-panel {
    padding: 12px;
    border: 1px solid rgba(201, 213, 226, 0.58);
    background: rgba(255, 255, 255, 0.92);
  }

  .market-terminal__overview-side {
    display: grid;
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
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }

  .market-terminal__market-card {
    padding: 10px;
    border: 1px solid rgba(201, 213, 226, 0.78);
    background: var(--terminal-card-bg);
    text-align: left;
    transition:
      transform 0.2s ease,
      box-shadow 0.2s ease,
      border-color 0.2s ease;
  }

  .market-terminal__market-card--mover {
    border-color: rgba(176, 193, 210, 0.8);
  }

  .market-terminal__market-card.is-clickable:hover,
  .market-terminal__name-button.is-clickable:hover {
    transform: translateY(-1px);
    border-color: rgba(116, 146, 170, 0.68);
    box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
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
    font-style: normal;
    font-size: 14px;
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
    fill: none;
    stroke-width: 1.5;
    stroke-linecap: round;
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
    padding: 10px;
    border: 1px dashed rgba(191, 205, 218, 0.74);
    background: rgba(246, 250, 252, 0.92);
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
    font-style: normal;
    color: #5b89ac;
    font-weight: 700;
  }

  .market-terminal__breadth-track {
    height: 5px;
    margin-top: 10px;
    background: rgba(120, 141, 162, 0.16);
  }

  .market-terminal__breadth-track i {
    display: block;
    height: 100%;
    background: #6a8198;
  }

  .market-terminal__vol-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
  }

  .market-terminal__vol-card {
    padding: 10px;
    border: 1px dashed rgba(191, 205, 218, 0.74);
    background: rgba(246, 250, 252, 0.92);
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
    padding: 10px 10px;
    border-bottom: 1px solid rgba(201, 213, 226, 0.52);
  }

  .market-terminal__table th {
    color: #88959a;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
  }

  .market-terminal__group-row td {
    background: rgba(241, 246, 251, 0.92);
    padding: 8px 10px;
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
    border: 1px solid rgba(201, 213, 226, 0.7);
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
    border-color: rgba(116, 146, 170, 0.68);
    background: rgba(236, 243, 249, 0.92);
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
    border: none;
    background: transparent;
    text-align: left;
    transition: transform 0.2s ease;
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
    border: 1px solid rgba(201, 213, 226, 0.86);
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
    background: rgba(184, 198, 212, 0.24);
    border-radius: 999px;
    overflow: hidden;
  }

  .market-terminal__high-cell span {
    flex: 0 0 52px;
    margin-left: 8px;
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
    background: transparent;
    font-weight: 700;
  }

  .market-chip.is-up {
    border-color: rgba(91, 147, 211, 0.2);
    background: rgba(91, 147, 211, 0.12);
    color: #5b93d3;
  }

  .market-chip.is-down {
    border-color: rgba(210, 107, 90, 0.2);
    background: rgba(210, 107, 90, 0.12);
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
    width: 100%;
    justify-content: center;
  }

  .market-terminal__rotation-table {
    width: 100%;
    min-width: 920px;
    border-collapse: collapse;
  }

  .market-terminal__rotation-table th,
  .market-terminal__rotation-table td {
    padding: 10px 12px;
    border: 1px solid rgba(201, 213, 226, 0.68);
    text-align: center;
    font-size: 12px;
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
    color: var(--terminal-muted);
    font-size: 11px;
  }

  .market-terminal__rotation-cell {
    font-weight: 700;
  }

  .market-terminal__rotation-cell.is-positive-cell {
    background: rgba(91, 147, 211, 0.18);
    color: #3777bf;
  }

  .market-terminal__rotation-cell.is-negative-cell {
    background: rgba(210, 107, 90, 0.16);
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
    border: 1px solid rgba(201, 213, 226, 0.62);
    background: rgba(246, 250, 252, 0.92);
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
    border: 1px solid rgba(201, 213, 226, 0.72);
    background: rgba(255, 255, 255, 0.86);
    color: #5f7485;
    font-size: 12px;
    font-weight: 700;
  }

  .market-terminal__rotation-chip b {
    color: #18313c;
  }

  .market-terminal-chart-modal {
    position: fixed;
    inset: 0;
    z-index: 1200;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 32px;
    background: rgba(9, 20, 17, 0.46);
    backdrop-filter: blur(8px);
  }

  .market-terminal-chart-modal__dialog {
    width: min(72vw, 1440px);
    max-width: calc(100vw - 48px);
    border: 1px solid rgba(201, 213, 226, 0.82);
    border-radius: 24px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(244, 248, 252, 0.98)), #fff;
    box-shadow: 0 30px 80px rgba(15, 23, 42, 0.18);
    overflow: hidden;
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
    border: 1px solid rgba(201, 213, 226, 0.82);
    border-radius: 999px;
    background: rgba(245, 249, 252, 0.96);
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
    background: linear-gradient(180deg, rgba(251, 253, 255, 0.98), rgba(243, 248, 252, 0.98));
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
    color: #5b93d3;
    stroke: #5b93d3;
  }

  .is-negative,
  .is-stroke-down,
  .is-arrow-down {
    color: #d26b5a;
    stroke: #d26b5a;
  }

  .is-badge-neutral,
  .is-badge-negative,
  .is-badge-accent {
    display: inline-flex;
    align-items: center;
    padding: 4px 8px;
    border: 1px solid rgba(201, 213, 226, 0.72);
    background: rgba(243, 247, 250, 0.94);
    font-size: 11px;
    font-weight: 700;
  }

  .is-badge-negative {
    color: #d26b5a;
  }

  .is-badge-accent {
    color: #4b77b9;
  }

  @media (max-width: 1280px) {
    .market-terminal__overview-strip {
      grid-template-columns: 1fr;
    }

    .market-terminal__vol-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 960px) {
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





