<template>
  <PageWrapper :title="pageTitle">
    <div class="hedge-board">
      <nav class="hedge-board__tabs" aria-label="对冲基金看板导航">
        <RouterLink
          v-for="item in hedgeBoardNav"
          :key="item.id"
          :to="item.path"
          class="hedge-board__tab"
          :class="{ 'is-active': item.id === activeCategory }"
        >
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <MarketTerminalPage
        v-if="isTerminalCategory && activeTerminalConfig"
        :config="activeTerminalConfig"
        :market-tabs="terminalTabs"
      />

      <div v-else class="terminal-content" :class="{ 'terminal-content--gold': useUnifiedResearchUi }">
        <section class="research-module" :class="{ 'research-module--gold': useUnifiedResearchUi }" :id="activeModule.id">
          <nav class="module-subnav" :class="{ 'module-subnav--gold': useUnifiedResearchUi }" :aria-label="`${activeModule.label} 子页导航`">
            <button
              v-for="(section, index) in visibleSections"
              :key="section.id"
              type="button"
              @click="jumpToSection(section.id)"
            >
              <span class="module-subnav__title-row">
                <span class="module-subnav__index">{{ String(index + 1).padStart(2, '0') }}</span>
                <strong>{{ getSectionTitle(section.id, section.title) }}</strong>
              </span>
            </button>
          </nav>

          <div v-if="activeModule.formula" class="formula-strip">
            <div>
              <span>核心公式</span>
              <strong>{{ activeModule.formula.title }}</strong>
            </div>
            <p>{{ activeModule.formula.description }}</p>
          </div>

          <section
            v-for="section in visibleSections"
            :id="section.id"
            :key="section.id"
            class="chart-section"
            :class="{ 'chart-section--gold': useUnifiedResearchUi }"
          >
            <div class="chart-section__heading">
              <div>
                <h4>{{ getSectionTitle(section.id, section.title) }}</h4>
              </div>
              <p>{{ getSectionDescription(section.id, section.description) }}</p>
            </div>

            <div class="widget-grid" :class="`widget-grid--${section.layout ?? 'three'}`">
              <article
                v-for="widget in section.widgets"
                :key="`${section.id}-${widget.title}`"
                class="widget-card"
              >
                <div class="widget-card__header">
                  <div class="widget-card__title-row">
                    <span class="widget-card__index">
                      {{ getWidgetSubtitle(widget.localKey, widget.subtitle) }}
                    </span>
                    <h5>{{ getWidgetTitle(widget.localKey, widget.title) }}</h5>
                  </div>
                </div>

                <WidgetErrorBoundary :widget-title="widget.title">
                  <LocalChartWidget
                    v-if="widget.kind === 'local-chart' && widget.localKey"
                    :widget="widget"
                  />
                  <TradingViewWidget v-else :widget="widget" />
                </WidgetErrorBoundary>
              </article>
            </div>
          </section>
        </section>
      </div>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import {
    computed,
    defineComponent,
    h,
    nextTick,
    onBeforeUnmount,
    onErrorCaptured,
    onMounted,
    PropType,
    ref,
    useSlots,
    watch,
  } from 'vue';
  import { RouterLink, useRoute } from 'vue-router';
  import { PageWrapper } from '@/components/Page';
  import MarketTerminalPage from './components/MarketTerminalPage.vue';
  import TerminalDetailPanel from './components/TerminalDetailPanel.vue';
  import {
    researchModules,
    type LocalWidgetKey,
    type ResearchModule,
    type WidgetConfig,
  } from './nativeData/dashboardClean';
  import { marketData } from './nativeData/generated/marketData';
  import {
    marketTerminalConfigs,
    type TerminalMarketId,
  } from './nativeData/marketTerminal';

  type HedgeCategory = 'macro' | 'gold' | 'crypto' | 'us' | 'global' | 'aShare';

  interface DualChartRow {
    date: string;
    left: number;
    right: number;
  }

  interface GroupedSeries {
    key: string;
    label: string;
    color: string;
  }

  interface WeeklyFlowRow {
    date: string;
    northAmerica: number;
    europe: number;
    asia: number;
    other: number;
    goldPrice: number;
  }

  interface SnapshotTableRow {
    name: string;
    symbol: string;
    price: string;
    d1: string;
    ytd: string;
    qtd: string;
    w1: string;
    m1: string;
    y1: string;
    high: string;
    d10: string;
    d20: string;
    d50: string;
    d200: string;
    x2050: string;
    x50200: string;
    spark: number[];
  }

  interface SnapshotTableGroup {
    label: string;
    rows: SnapshotTableRow[];
  }

  const CHART_WIDTH = 760;
  const CHART_HEIGHT = 320;
  const CHART_PADDING = { top: 28, right: 82, bottom: 50, left: 74 };
  const ETF_REFERENCE_URL =
    'https://china.gold.org/goldhub/data/gold-etfs-holdings-and-flows#from-login=1&login-type=wechat';
  const LOCAL_MARKET_DETAIL_TABLES: Record<'gold-market-detail-table' | 'crypto-market-detail-table', SnapshotTableGroup[]> = {
    'gold-market-detail-table': [
      {
        label: '贵金属',
        rows: [
          { name: '现货黄金', symbol: 'XAUUSD', price: '2,332.4', d1: '+0.80%', ytd: '+12.80%', qtd: '+3.10%', w1: '+1.60%', m1: '+3.10%', y1: '+18.40%', high: '-2.1%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [10, 11, 12, 13, 12, 11, 12, 13, 14, 15, 14, 13, 14, 15, 16, 16, 17, 18, 19, 18, 19, 20, 21, 22] },
          { name: '白银', symbol: 'XAGUSD', price: '29.74', d1: '+1.20%', ytd: '+15.60%', qtd: '+6.40%', w1: '+2.80%', m1: '+6.40%', y1: '+23.90%', high: '-4.7%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [7, 8, 9, 10, 10, 11, 12, 13, 12, 11, 12, 13, 14, 15, 15, 16, 17, 18, 18, 19, 20, 21, 22, 22] },
          { name: 'SPDR黄金ETF', symbol: 'GLD', price: '214.8', d1: '+0.70%', ytd: '+11.70%', qtd: '+2.60%', w1: '+1.40%', m1: '+2.60%', y1: '+16.10%', high: '-2.8%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [8, 9, 10, 10, 11, 11, 12, 13, 12, 12, 13, 14, 14, 15, 16, 16, 17, 17, 18, 19, 19, 20, 21, 21] },
          { name: '金矿股ETF', symbol: 'GDX', price: '36.20', d1: '-0.40%', ytd: '+9.30%', qtd: '+4.80%', w1: '+0.90%', m1: '+4.80%', y1: '+14.70%', high: '-7.3%', d10: '▼', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [14, 14, 15, 16, 15, 14, 13, 12, 13, 14, 15, 14, 13, 12, 13, 14, 15, 16, 17, 16, 15, 16, 17, 16] },
          { name: '金银比', symbol: 'XAUXAG', price: '78.40', d1: '-0.30%', ytd: '-1.90%', qtd: '-2.40%', w1: '-1.10%', m1: '-2.40%', y1: '-4.60%', high: '-9.8%', d10: '▼', d20: '▼', d50: '▼', d200: '▲', x2050: '▼', x50200: '▲', spark: [18, 18, 17, 17, 16, 16, 15, 15, 14, 14, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 8, 8, 8, 7] },
          { name: '铂金', symbol: 'XPTUSD', price: '983.1', d1: '+0.30%', ytd: '+5.40%', qtd: '+1.70%', w1: '+0.50%', m1: '+1.70%', y1: '+7.60%', high: '-12.3%', d10: '▲', d20: '▲', d50: '▼', d200: '▲', x2050: '▲', x50200: '▲', spark: [8, 8, 9, 9, 10, 10, 11, 10, 10, 11, 11, 12, 12, 13, 13, 12, 12, 13, 14, 14, 15, 15, 16, 16] },
        ],
      },
      {
        label: '商品横截面',
        rows: [
          { name: 'WTI原油', symbol: 'USOIL', price: '81.60', d1: '-0.70%', ytd: '+13.20%', qtd: '+4.10%', w1: '+1.90%', m1: '+4.10%', y1: '+8.70%', high: '-6.4%', d10: '▼', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [16, 17, 18, 18, 17, 16, 15, 14, 13, 12, 12, 13, 14, 15, 15, 16, 17, 18, 18, 19, 20, 19, 18, 17] },
          { name: '布伦特原油', symbol: 'BRENT', price: '84.10', d1: '-0.50%', ytd: '+11.80%', qtd: '+3.90%', w1: '+1.60%', m1: '+3.70%', y1: '+7.20%', high: '-5.9%', d10: '▼', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [15, 16, 16, 17, 16, 15, 14, 13, 13, 12, 12, 13, 14, 14, 15, 16, 17, 17, 18, 18, 19, 18, 17, 16] },
          { name: '铜', symbol: 'HG1!', price: '4.46', d1: '+0.50%', ytd: '+10.40%', qtd: '+2.10%', w1: '-1.30%', m1: '+2.10%', y1: '+17.80%', high: '-8.1%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [8, 8, 9, 10, 11, 12, 12, 13, 14, 15, 15, 16, 16, 17, 18, 18, 19, 20, 19, 20, 21, 22, 22, 21] },
          { name: '天然气', symbol: 'NG1!', price: '2.81', d1: '+1.10%', ytd: '+6.90%', qtd: '-2.50%', w1: '+4.30%', m1: '-2.50%', y1: '-8.20%', high: '-18.3%', d10: '▲', d20: '▲', d50: '▼', d200: '▼', x2050: '▼', x50200: '▼', spark: [6, 6, 7, 7, 8, 9, 9, 10, 10, 11, 12, 12, 11, 10, 10, 11, 12, 13, 14, 14, 15, 15, 16, 16] },
          { name: '彭博商品指数', symbol: 'BCOM', price: '101.3', d1: '+0.20%', ytd: '+5.80%', qtd: '+1.90%', w1: '+0.60%', m1: '+1.90%', y1: '+7.40%', high: '-3.2%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [8, 9, 10, 10, 10, 11, 11, 12, 12, 13, 13, 14, 14, 15, 15, 15, 16, 16, 17, 17, 18, 18, 19, 19] },
          { name: '白银ETF', symbol: 'SLV', price: '27.10', d1: '+1.00%', ytd: '+14.80%', qtd: '+5.50%', w1: '+2.30%', m1: '+5.50%', y1: '+21.60%', high: '-5.1%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [7, 8, 8, 9, 10, 10, 11, 12, 12, 13, 13, 14, 14, 15, 16, 16, 17, 18, 18, 19, 20, 20, 21, 21] },
        ],
      },
      {
        label: '矿业与权益代理',
        rows: [
          { name: '小盘金矿ETF', symbol: 'GDXJ', price: '45.87', d1: '-0.60%', ytd: '+7.80%', qtd: '+5.10%', w1: '+0.50%', m1: '+3.90%', y1: '+11.60%', high: '-8.9%', d10: '▼', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [12, 13, 14, 15, 14, 13, 12, 11, 11, 12, 13, 14, 13, 12, 12, 13, 14, 15, 16, 15, 14, 15, 15, 14] },
          { name: '巴里克黄金', symbol: 'GOLD', price: '18.46', d1: '-0.20%', ytd: '+10.10%', qtd: '+4.60%', w1: '+0.80%', m1: '+4.60%', y1: '+13.40%', high: '-9.7%', d10: '▼', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [11, 11, 12, 12, 13, 13, 12, 12, 13, 13, 14, 14, 13, 13, 14, 14, 15, 15, 16, 15, 15, 16, 16, 17] },
          { name: '纽曼矿业', symbol: 'NEM', price: '41.22', d1: '-0.50%', ytd: '+8.90%', qtd: '+3.90%', w1: '+0.70%', m1: '+3.90%', y1: '+12.80%', high: '-10.5%', d10: '▼', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [12, 12, 13, 14, 13, 12, 12, 11, 12, 13, 13, 14, 13, 13, 14, 14, 15, 15, 16, 15, 15, 16, 16, 15] },
          { name: '金矿股指数', symbol: 'HUI', price: '276.5', d1: '-0.80%', ytd: '+9.80%', qtd: '+5.30%', w1: '+0.60%', m1: '+4.20%', y1: '+15.90%', high: '-7.8%', d10: '▼', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [13, 13, 14, 15, 15, 14, 13, 13, 14, 15, 15, 14, 14, 15, 15, 16, 16, 17, 18, 17, 17, 18, 18, 17] },
        ],
      },
    ],
    'crypto-market-detail-table': [
      {
        label: '主要指数',
        rows: [
          { name: '比特币', symbol: 'BTC', price: '62,840', d1: '+1.50%', ytd: '+46.70%', qtd: '+8.20%', w1: '+3.80%', m1: '+8.20%', y1: '+112.50%', high: '-6.1%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [9, 10, 10, 11, 12, 12, 13, 14, 13, 14, 15, 16, 16, 17, 18, 18, 19, 20, 21, 21, 22, 23, 24, 24] },
          { name: '以太坊', symbol: 'ETH', price: '3,438', d1: '+1.10%', ytd: '+39.80%', qtd: '+6.60%', w1: '+2.90%', m1: '+6.60%', y1: '+84.30%', high: '-8.7%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [8, 8, 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 15, 16, 17, 17, 18, 19, 20, 20, 21, 22, 22, 23] },
          { name: 'Solana', symbol: 'SOL', price: '146.3', d1: '+2.60%', ytd: '+43.10%', qtd: '+11.40%', w1: '+5.20%', m1: '+11.40%', y1: '+97.70%', high: '-10.9%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [6, 7, 8, 9, 9, 10, 11, 12, 12, 13, 14, 15, 15, 16, 17, 18, 18, 19, 20, 21, 22, 22, 23, 24] },
          { name: 'BNB', symbol: 'BNB', price: '581.7', d1: '+0.90%', ytd: '+27.90%', qtd: '+4.50%', w1: '+2.10%', m1: '+4.50%', y1: '+69.40%', high: '-7.4%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [7, 8, 8, 9, 10, 10, 11, 12, 12, 13, 13, 14, 15, 15, 16, 16, 17, 18, 18, 19, 20, 20, 21, 21] },
          { name: 'XRP', symbol: 'XRP', price: '0.51', d1: '-0.60%', ytd: '-18.60%', qtd: '-3.70%', w1: '+1.20%', m1: '-3.70%', y1: '+4.90%', high: '-21.6%', d10: '▼', d20: '▼', d50: '▼', d200: '▲', x2050: '▼', x50200: '▼', spark: [14, 14, 13, 13, 12, 12, 11, 11, 10, 10, 9, 9, 8, 8, 7, 7, 7, 6, 6, 6, 5, 5, 5, 5] },
          { name: '狗狗币', symbol: 'DOGE', price: '0.124', d1: '+3.40%', ytd: '+22.30%', qtd: '+12.60%', w1: '+8.10%', m1: '+12.60%', y1: '+91.70%', high: '-15.8%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [5, 6, 6, 7, 8, 9, 9, 10, 11, 12, 12, 13, 14, 14, 15, 16, 17, 18, 18, 19, 20, 21, 22, 23] },
          { name: 'Toncoin', symbol: 'TON', price: '7.12', d1: '+0.70%', ytd: '+18.60%', qtd: '+5.40%', w1: '+1.40%', m1: '+5.40%', y1: '+66.80%', high: '-8.4%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13, 14, 15, 15, 16, 17, 17, 18, 19, 19, 20] },
        ],
      },
      {
        label: '扩散与代理',
        rows: [
          { name: '总市值', symbol: 'TOTAL', price: '2.31T', d1: '+1.20%', ytd: '+38.40%', qtd: '+6.90%', w1: '+2.70%', m1: '+6.90%', y1: '+76.20%', high: '-5.4%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [7, 8, 8, 9, 10, 10, 11, 12, 13, 13, 14, 15, 15, 16, 17, 18, 18, 19, 20, 20, 21, 22, 23, 23] },
          { name: '除BTC/ETH外', symbol: 'TOTAL3', price: '712B', d1: '+2.10%', ytd: '+34.70%', qtd: '+9.30%', w1: '+4.40%', m1: '+9.30%', y1: '+88.10%', high: '-9.2%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [7, 8, 8, 9, 10, 11, 11, 12, 13, 14, 14, 15, 15, 16, 17, 18, 18, 19, 20, 20, 21, 22, 23, 23] },
          { name: 'BTC主导率', symbol: 'BTC.D', price: '54.8%', d1: '-0.40%', ytd: '+2.30%', qtd: '-1.90%', w1: '-0.80%', m1: '-1.90%', y1: '+6.10%', high: '-4.3%', d10: '▼', d20: '▼', d50: '▼', d200: '▲', x2050: '▼', x50200: '▲', spark: [18, 18, 17, 17, 16, 16, 15, 15, 14, 14, 13, 13, 13, 12, 12, 11, 11, 10, 10, 10, 9, 9, 8, 8] },
          { name: 'Coinbase', symbol: 'COIN', price: '224.6', d1: '+1.70%', ytd: '+31.40%', qtd: '+10.80%', w1: '+6.20%', m1: '+10.80%', y1: '+54.90%', high: '-12.6%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [7, 8, 8, 9, 10, 10, 11, 12, 13, 13, 14, 15, 15, 16, 16, 17, 18, 19, 19, 20, 21, 22, 22, 23] },
          { name: 'MicroStrategy', symbol: 'MSTR', price: '1,487', d1: '+2.20%', ytd: '+63.80%', qtd: '+15.30%', w1: '+5.70%', m1: '+15.30%', y1: '+162.20%', high: '-9.4%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [6, 7, 8, 9, 9, 10, 11, 12, 13, 13, 14, 15, 16, 16, 17, 18, 19, 20, 20, 21, 22, 23, 24, 24] },
          { name: '现货BTC ETF', symbol: 'IBIT', price: '42.8', d1: '+1.40%', ytd: '+44.20%', qtd: '+7.80%', w1: '+3.40%', m1: '+7.80%', y1: '+98.30%', high: '-6.8%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [8, 9, 9, 10, 11, 11, 12, 13, 13, 14, 15, 15, 16, 17, 17, 18, 19, 20, 21, 21, 22, 22, 23, 24] },
        ],
      },
      {
        label: '交易所与链上Beta',
        rows: [
          { name: '现货ETH ETF预期', symbol: 'ETHBETA', price: '68.5', d1: '+1.80%', ytd: '+28.40%', qtd: '+9.70%', w1: '+4.10%', m1: '+9.70%', y1: '+58.20%', high: '-13.8%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [7, 8, 8, 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 15, 16, 17, 17, 18, 19, 20, 20, 21, 22, 22] },
          { name: '矿企代理', symbol: 'MARA', price: '21.8', d1: '+2.70%', ytd: '+19.80%', qtd: '+11.90%', w1: '+5.60%', m1: '+11.90%', y1: '+74.30%', high: '-18.6%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [5, 6, 7, 7, 8, 8, 9, 10, 10, 11, 12, 12, 13, 14, 14, 15, 16, 17, 18, 18, 19, 20, 21, 22] },
          { name: '矿企代理', symbol: 'RIOT', price: '11.4', d1: '+2.10%', ytd: '+14.60%', qtd: '+10.20%', w1: '+4.90%', m1: '+10.20%', y1: '+61.50%', high: '-20.9%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [6, 6, 7, 7, 8, 9, 9, 10, 10, 11, 11, 12, 13, 13, 14, 15, 15, 16, 17, 17, 18, 19, 20, 21] },
          { name: '去中心化Beta', symbol: 'UNI', price: '10.8', d1: '+1.30%', ytd: '+17.20%', qtd: '+8.80%', w1: '+3.60%', m1: '+8.80%', y1: '+42.70%', high: '-17.1%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 13, 13, 14, 14, 15, 15, 16, 17, 17, 18, 18, 19, 20] },
          { name: '链上高Beta', symbol: 'RNDR', price: '9.24', d1: '+2.90%', ytd: '+36.50%', qtd: '+13.60%', w1: '+6.30%', m1: '+13.60%', y1: '+109.80%', high: '-16.4%', d10: '▲', d20: '▲', d50: '▲', d200: '▲', x2050: '▲', x50200: '▲', spark: [5, 6, 6, 7, 8, 8, 9, 10, 11, 11, 12, 13, 13, 14, 15, 16, 16, 17, 18, 19, 19, 20, 21, 22] },
        ],
      },
    ],
  };

  const BTC_ETF_FLOW_ROWS: DualChartRow[] = [
    { date: '2026-05-28', left: 112, right: 68240 },
    { date: '2026-05-29', left: 86, right: 67680 },
    { date: '2026-05-30', left: -24, right: 67120 },
    { date: '2026-06-02', left: 158, right: 68860 },
    { date: '2026-06-03', left: 194, right: 69440 },
    { date: '2026-06-04', left: 76, right: 70120 },
    { date: '2026-06-05', left: 142, right: 70980 },
    { date: '2026-06-08', left: 121, right: 71340 },
    { date: '2026-06-09', left: 166, right: 71820 },
    { date: '2026-06-10', left: -18, right: 71260 },
    { date: '2026-06-11', left: 204, right: 72640 },
    { date: '2026-06-12', left: 187, right: 73480 },
  ];

  const BTC_TREASURY_FLOW_ROWS: ReadonlyArray<Record<string, number | string>> = [
    { date: '2026-03', listed: 18.4, private: 6.1, funds: 4.3 },
    { date: '2026-04', listed: 26.8, private: 7.9, funds: 5.7 },
    { date: '2026-05', listed: 31.2, private: 9.4, funds: 6.6 },
    { date: '2026-06', listed: 24.6, private: 8.7, funds: 5.3 },
    { date: '2026-07', listed: 36.1, private: 10.6, funds: 7.2 },
    { date: '2026-08', listed: 29.7, private: 9.1, funds: 6.2 },
  ];

  const route = useRoute();

  const moduleRoutes: Record<HedgeCategory, string> = {
    macro: '/hedge-board/macro',
    us: '/hedge-board/us',
    aShare: '/hedge-board/a-share',
    global: '/hedge-board/global',
    gold: '/hedge-board/gold',
    crypto: '/hedge-board/crypto',
  };

  const hedgeBoardNav: Array<{
    id: HedgeCategory;
    label: string;
    eyebrow: string;
    path: string;
    description: string;
  }> = [
    {
      id: 'macro',
      label: '宏观',
      eyebrow: 'Macro',
      path: moduleRoutes.macro,
      description: '流动性、通胀、利率与跨资产环境。',
    },
    {
      id: 'gold',
      label: '商品',
      eyebrow: 'Commodities',
      path: moduleRoutes.gold,
      description: '贵金属、能源、ETF 资金面与比价结构。',
    },
    {
      id: 'crypto',
      label: '加密',
      eyebrow: 'Crypto',
      path: moduleRoutes.crypto,
      description: 'BTC 主图、扩散结构与高 beta 风险偏好。',
    },
    {
      id: 'us',
      label: '美股',
      eyebrow: 'US',
      path: moduleRoutes.us,
      description: '复刻 MarketGrep 的温度终端与活跃度结构。',
    },
    {
      id: 'aShare',
      label: 'A股',
      eyebrow: 'A-Share',
      path: moduleRoutes.aShare,
      description: '沿用同一终端壳，重排为 A 股语境。',
    },
    {
      id: 'global',
      label: '全球',
      eyebrow: 'Global',
      path: moduleRoutes.global,
      description: '区域风险偏好、发达市场与新兴市场分化。',
    },
  ];

  const activeCategory = computed<HedgeCategory>(() => {
    const routeName = String(route.name ?? '');
    const routePath = route.path;

    if (routeName === 'HedgeUsBoard' || routePath.endsWith('/us')) return 'us';
    if (routeName === 'HedgeAShareBoard' || routePath.endsWith('/a-share')) return 'aShare';
    if (routeName === 'HedgeGlobalBoard' || routePath.endsWith('/global')) return 'global';
    if (routeName === 'HedgeGoldBoard' || routePath.endsWith('/gold')) return 'gold';
    if (routeName === 'HedgeCryptoBoard' || routePath.endsWith('/crypto')) return 'crypto';
    return 'macro';
  });

  const isTerminalCategory = computed(
    () =>
      activeCategory.value === 'us' ||
      activeCategory.value === 'global' ||
      activeCategory.value === 'aShare',
  );
  const activeTerminalConfig = computed(() =>
    isTerminalCategory.value
      ? marketTerminalConfigs[activeCategory.value as TerminalMarketId]
      : null,
  );
  const terminalTabs = computed(() => {
    if (activeCategory.value === 'aShare') {
      return [{ id: 'aShare' as TerminalMarketId, label: 'A股', path: moduleRoutes.aShare }];
    }

    return [
      { id: 'us' as TerminalMarketId, label: '美股', path: moduleRoutes.us },
      { id: 'global' as TerminalMarketId, label: '全球', path: moduleRoutes.global },
    ];
  });
  const activeBoardNav = computed(
    () => hedgeBoardNav.find((item) => item.id === activeCategory.value) ?? hedgeBoardNav[0],
  );
  const activeModule = computed<ResearchModule>(
    () => researchModules.find((module) => module.id === activeCategory.value) ?? researchModules[0],
  );
  const useUnifiedResearchUi = computed(() => true);
  const visibleSections = computed(() => activeModule.value.sections);

  const pageTitle = computed(() => `对冲基金看板 / ${activeBoardNav.value.label}`);

  function scrollPageTop() {
    if (typeof window === 'undefined') return;
    nextTick(() => {
      window.scrollTo({ top: 0, left: 0, behavior: 'auto' });
      document.documentElement.scrollTop = 0;
      document.body.scrollTop = 0;
      const scrollTargets = [
        document.querySelector('.scrollbar__wrap'),
        document.querySelector('.vben-layout-content'),
        document.querySelector('.ant-layout-content'),
        document.querySelector('.page-wrapper-content'),
      ].filter(Boolean) as HTMLElement[];
      scrollTargets.forEach((element) => {
        element.scrollTop = 0;
        element.scrollLeft = 0;
      });
    });
  }

  const sectionLabelOverrides: Record<string, { eyebrow?: string; title?: string; description?: string }> = {
    'gold-flows': {
      eyebrow: '资金面',
      title: 'ETF与资金面',
      description: '',
    },
    'gold-central-bank': {
      eyebrow: '官方部门',
      title: '央行购金',
      description: '',
    },
    'gold-main': {
      eyebrow: '价格',
      title: '黄金主图',
      description: '',
    },
    'gold-rates': {
      eyebrow: '利率与通胀',
      title: '利率与通胀',
      description: '',
    },
    'crypto-etf': {
      title: '加密资金面',
      description: '',
    },
  };

  const widgetTextOverrides: Record<string, { title?: string; subtitle?: string; sourceNote?: string }> = {
    'etf-weekly-flows': {
      title: '全球各地区ETF每周流入',
      subtitle: '',
      sourceNote: '',
    },
    'etf-ytd-summary': {
      title: '全球 ETF 年内汇总',
      subtitle: '',
      sourceNote: '',
    },
    'spdr-daily-flow': {
      title: '金价 vs SPDR 每日流量',
      subtitle: '',
      sourceNote: '',
    },
    'spdr-holdings-vs-price': {
      title: 'SPDR 持仓量 vs 黄金价格',
      subtitle: '',
      sourceNote: '',
    },
    'central-bank-holders': {
      title: '官方黄金储备前十',
      subtitle: '',
      sourceNote: '',
    },
    'central-bank-buyers': {
      title: '近一年持续增持的央行',
      subtitle: '',
      sourceNote: '',
    },
  };

  function getSectionEyebrow(sectionId: string, fallback: string) {
    return sectionLabelOverrides[sectionId]?.eyebrow ?? fallback;
  }

  function getSectionTitle(sectionId: string, fallback: string) {
    return sectionLabelOverrides[sectionId]?.title ?? fallback;
  }

  function getSectionDescription() {
    return '';
  }

  function getWidgetTitle(localKey: string | undefined, fallback: string) {
    if (!localKey) return fallback;
    return widgetTextOverrides[localKey]?.title ?? fallback;
  }

  function getWidgetSubtitle() {
    return '';
  }

  function getWidgetSourceNote() {
    return '';
  }

  function jumpToSection(sectionId: string) {
    nextTick(() => {
      const element = document.getElementById(sectionId);
      if (!element) return;
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  watch(
    () => route.fullPath,
    () => {
      scrollPageTop();
    },
    { immediate: true },
  );

  onMounted(() => {
    if (typeof window !== 'undefined' && 'scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }
    scrollPageTop();
  });

  const TradingViewWidget = defineComponent({
    name: 'TradingViewWidget',
    props: {
      widget: {
        type: Object as PropType<WidgetConfig>,
        required: true,
      },
    },
    setup(props) {
      const mountRef = ref<HTMLDivElement | null>(null);
      const loadFailed = ref(false);

      const renderWidget = () => {
        const mountNode = mountRef.value;
        if (!mountNode || !props.widget.scriptSrc || !props.widget.config) return;

        loadFailed.value = false;
        mountNode.innerHTML = '';

        try {
          const container = document.createElement('div');
          container.className = 'tradingview-widget-container';

          const widgetNode = document.createElement('div');
          widgetNode.className = 'tradingview-widget-container__widget';
          container.appendChild(widgetNode);

          const script = document.createElement('script');
          script.src = props.widget.scriptSrc;
          script.async = true;
          script.type = 'text/javascript';
          script.innerHTML = JSON.stringify(props.widget.config);
          script.onerror = () => {
            loadFailed.value = true;
            if (mountRef.value) mountRef.value.innerHTML = '';
          };

          container.appendChild(script);
          mountNode.appendChild(container);
        } catch (error) {
          console.error('[hedgeBoard] TradingView widget render failed:', props.widget.title, error);
          loadFailed.value = true;
          mountNode.innerHTML = '';
        }
      };

      onMounted(renderWidget);
      watch(() => props.widget, renderWidget, { deep: true });
      onBeforeUnmount(() => {
        if (mountRef.value) mountRef.value.innerHTML = '';
      });

      return () =>
        loadFailed.value
          ? h(
              'div',
              {
                class: 'local-empty',
                style: { minHeight: `${props.widget.height ?? 360}px` },
              },
              '该外部图表当前加载失败，页面主体已保留，可继续浏览其他模块。',
            )
          : h('div', {
              ref: mountRef,
              class: 'widget-frame',
              style: { minHeight: `${props.widget.height ?? 360}px` },
            });
    },
  });

  const WidgetErrorBoundary = defineComponent({
    name: 'WidgetErrorBoundary',
    props: {
      widgetTitle: {
        type: String,
        required: true,
      },
    },
    setup(props) {
      const slots = useSlots();
      const hasError = ref(false);

      onErrorCaptured((error) => {
        console.error('[hedgeBoard] Widget boundary captured:', props.widgetTitle, error);
        hasError.value = true;
        return false;
      });

      return () => {
        if (hasError.value) {
          return h(
            'div',
            {
              class: 'local-empty',
              style: { minHeight: '360px' },
            },
            `模块 "${props.widgetTitle}" 渲染失败，已自动跳过，不影响其他内容浏览。`,
          );
        }

        return slots.default ? slots.default() : null;
      };
    },
  });

  const MetricStrip = defineComponent({
    name: 'MetricStrip',
    props: {
      metrics: {
        type: Array as PropType<Array<[string, string]>>,
        required: true,
      },
    },
    setup(props) {
      return () =>
        h(
          'div',
          { class: 'metric-strip' },
          props.metrics.map(([label, value]) =>
            h('article', { key: `${label}-${value}` }, [h('span', label), h('strong', value)]),
          ),
        );
    },
  });

  const DualAxisChart = defineComponent({
    name: 'DualAxisChart',
    props: {
      rows: {
        type: Array as PropType<DualChartRow[]>,
        required: true,
      },
      leftLabel: {
        type: String,
        required: true,
      },
      rightLabel: {
        type: String,
        required: true,
      },
      leftUnit: {
        type: String,
        required: true,
      },
      rightUnit: {
        type: String,
        required: true,
      },
      leftColor: {
        type: String,
        required: true,
      },
      rightColor: {
        type: String,
        required: true,
      },
      barPositiveColor: {
        type: String,
        default: '',
      },
      barNegativeColor: {
        type: String,
        default: '',
      },
      barWidthRatio: {
        type: Number,
        default: 0.78,
      },
      leftAsBars: {
        type: Boolean,
        default: false,
      },
      divergingBars: {
        type: Boolean,
        default: false,
      },
      showRangeSlider: {
        type: Boolean,
        default: false,
      },
      windowSize: {
        type: Number,
        default: 8,
      },
    },
    setup(props) {
      const startIndex = ref(0);

      watch(
        () => [props.rows.length, props.windowSize],
        () => {
          const visibleCount = Math.max(2, Math.min(props.windowSize, props.rows.length || props.windowSize));
          const maxStart = Math.max(0, props.rows.length - visibleCount);
          if (startIndex.value > maxStart) startIndex.value = maxStart;
        },
        { immediate: true },
      );

      return () => {
        const visibleCount = props.showRangeSlider
          ? Math.max(2, Math.min(props.windowSize, props.rows.length || props.windowSize))
          : props.rows.length;
        const maxStart = Math.max(0, props.rows.length - visibleCount);
        const visibleRows =
          props.showRangeSlider && maxStart > 0
            ? props.rows.slice(startIndex.value, startIndex.value + visibleCount)
            : props.rows;
        const innerWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
        const innerHeight = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
        const leftValues = visibleRows.map((row) => row.left);
        const rightValues = visibleRows.map((row) => row.right);
        const leftRange = getRange(leftValues, props.divergingBars);
        const rightRange = getRange(rightValues);
        const zeroY = scaleY(0, leftRange.min, leftRange.max, innerHeight);

        const leftLinePath = props.leftAsBars
          ? ''
          : buildLinePath(
              visibleRows,
              (_row, index) => scaleX(index, props.rows.length, innerWidth),
              (row) => scaleY(row.left, leftRange.min, leftRange.max, innerHeight),
            );
        const rightLinePath = buildLinePath(
          visibleRows,
          (_row, index) => scaleX(index, visibleRows.length, innerWidth),
          (row) => scaleY(row.right, rightRange.min, rightRange.max, innerHeight),
        );
        const leftTicks = makeTicks(leftRange.min, leftRange.max, 4);
        const rightTicks = makeTicks(rightRange.min, rightRange.max, 4);
        const barWidth = Math.max(
          8,
          (innerWidth / Math.max(visibleRows.length, 1) - 10) * props.barWidthRatio,
        );

        return h('div', { class: 'local-widget-stack' }, [
          h(MetricStrip, {
            metrics: [
              [props.leftLabel, `${formatNumber(visibleRows.at(-1)?.left ?? 0)} ${props.leftUnit}`],
              [props.rightLabel, `${formatNumber(visibleRows.at(-1)?.right ?? 0)} ${props.rightUnit}`],
              ['更新', visibleRows.at(-1)?.date ?? '-'],
            ],
          }),
          h('div', { class: 'chart-topline' }, [
            h('div', { class: 'chart-axis-head' }, [
              h('span', `${props.leftLabel}（${props.leftUnit}）`),
              h('span', `${props.rightLabel}（${props.rightUnit}）`),
            ]),
            h('div', { class: 'chart-legend' }, [
              h('span', [h('i', { style: { backgroundColor: props.leftColor } }), props.leftLabel]),
              h('span', [h('i', { style: { backgroundColor: props.rightColor } }), props.rightLabel]),
            ]),
          ]),
          h('div', { class: 'chart-shell' }, [
            h(
              'svg',
              {
                viewBox: `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`,
                class: 'local-chart-svg',
                role: 'img',
              },
              [
                h(
                  'g',
                  {
                    transform: `translate(${CHART_PADDING.left},${CHART_PADDING.top})`,
                  },
                  [
                    ...leftTicks.flatMap((tick) => {
                      const y = scaleY(tick, leftRange.min, leftRange.max, innerHeight);
                      return [
                        h('line', {
                          key: `left-line-${tick}`,
                          x1: 0,
                          x2: innerWidth,
                          y1: y,
                          y2: y,
                          class: 'chart-grid-line',
                        }),
                        h(
                          'text',
                          {
                            key: `left-text-${tick}`,
                            x: -12,
                            y: y + 4,
                            textAnchor: 'end',
                            class: 'chart-axis-label',
                          },
                          formatAxis(tick),
                        ),
                      ];
                    }),
                    h('line', {
                      x1: 0,
                      x2: innerWidth,
                      y1: zeroY,
                      y2: zeroY,
                      class: 'chart-zero-line',
                    }),
                    ...rightTicks.map((tick) => {
                      const y = scaleY(tick, rightRange.min, rightRange.max, innerHeight);
                      return h(
                        'text',
                        {
                          key: `right-${tick}`,
                          x: innerWidth + 12,
                          y: y + 4,
                          textAnchor: 'start',
                          class: 'chart-axis-label',
                        },
                        formatAxis(tick),
                      );
                    }),
                    ...visibleRows
                      .map((row, index) => {
                        if (!props.leftAsBars) return null;
                        const x = scaleX(index, visibleRows.length, innerWidth);
                        const y = scaleY(row.left, leftRange.min, leftRange.max, innerHeight);
                        const height = Math.abs(zeroY - y);
                        const barY = row.left >= 0 ? y : zeroY;
                        return h('rect', {
                          key: `${row.date}-bar`,
                          x: x - barWidth / 2,
                          y: barY,
                          width: barWidth,
                          height: Math.max(height, 1),
                          rx: 2,
                          fill: props.divergingBars
                            ? row.left >= 0
                              ? props.barPositiveColor || '#0f8b6d'
                              : props.barNegativeColor || '#dc2626'
                            : props.leftColor,
                          opacity: 0.86,
                        });
                      })
                      .filter(Boolean),
                    leftLinePath
                      ? h('path', {
                          d: leftLinePath,
                          fill: 'none',
                          stroke: props.leftColor,
                          strokeWidth: 2.5,
                          strokeLinecap: 'round',
                        })
                      : null,
                    h('path', {
                      d: rightLinePath,
                      fill: 'none',
                      stroke: props.rightColor,
                      strokeWidth: 2.5,
                      strokeLinecap: 'round',
                    }),
                    ...renderDateLabels(visibleRows, innerWidth, innerHeight),
                  ].filter(Boolean),
                ),
              ],
            ),
          ]),
          props.showRangeSlider && maxStart > 0
            ? h('div', { class: 'chart-range' }, [
                h('span', visibleRows[0]?.date ?? ''),
                h('input', {
                  class: 'chart-range__input',
                  type: 'range',
                  min: 0,
                  max: maxStart,
                  value: startIndex.value,
                  onInput: (event: Event) => {
                    startIndex.value = Number((event.target as HTMLInputElement).value);
                  },
                }),
                h('span', visibleRows.at(-1)?.date ?? ''),
              ])
            : null,
        ]);
      };
    },
  });

  const TreasuryFlowChart = defineComponent({
    name: 'TreasuryFlowChart',
    setup() {
      const startIndex = ref(0);
      const windowSize = 4;

      return () => {
        const rows = BTC_TREASURY_FLOW_ROWS.slice(
          startIndex.value,
          startIndex.value + Math.min(windowSize, BTC_TREASURY_FLOW_ROWS.length),
        );
        const maxStart = Math.max(0, BTC_TREASURY_FLOW_ROWS.length - windowSize);
        const series = [
          { key: 'listed', label: '上市公司', color: '#356df3' },
          { key: 'private', label: '私营财库', color: '#6d93ad' },
          { key: 'funds', label: '基金 / 信托', color: '#9cb0c5' },
        ] as const;
        const allValues = rows.flatMap((row) => series.map((item) => Number(row[item.key])));
        const range = getRange(allValues);
        const innerWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
        const innerHeight = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
        const groupWidth = innerWidth / Math.max(rows.length, 1);
        const singleBarWidth = Math.min(26, Math.max(12, groupWidth / 4.2));
        const baseY = scaleY(0, Math.min(0, range.min), range.max, innerHeight);

        return h('div', { class: 'local-widget-stack' }, [
          h('div', { class: 'treasury-kpi' }, [
            h('span', '上市公司私营财库基金 / 信托'),
            h('strong', '40.43'),
          ]),
          h('div', { class: 'chart-topline' }, [
            h('div', { class: 'chart-axis-head' }, [h('span', '净流入（千枚 BTC）'), h('span', '')]),
            h(
              'div',
              { class: 'chart-legend' },
              series.map((item) =>
                h('span', [h('i', { style: { backgroundColor: item.color } }), item.label]),
              ),
            ),
          ]),
          h('div', { class: 'chart-shell' }, [
            h(
              'svg',
              {
                viewBox: `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`,
                class: 'local-chart-svg',
              },
              [
                h('g', { transform: `translate(${CHART_PADDING.left},${CHART_PADDING.top})` }, [
                  ...makeTicks(Math.min(0, range.min), range.max, 4).flatMap((tick) => {
                    const y = scaleY(tick, Math.min(0, range.min), range.max, innerHeight);
                    return [
                      h('line', {
                        x1: 0,
                        x2: innerWidth,
                        y1: y,
                        y2: y,
                        class: 'chart-grid-line',
                      }),
                      h(
                        'text',
                        {
                          x: -12,
                          y: y + 4,
                          textAnchor: 'end',
                          class: 'chart-axis-label',
                        },
                        formatAxis(tick),
                      ),
                    ];
                  }),
                  h('line', {
                    x1: 0,
                    x2: innerWidth,
                    y1: baseY,
                    y2: baseY,
                    class: 'chart-zero-line',
                  }),
                  ...rows.flatMap((row, rowIndex) => {
                    const centerX = scaleX(rowIndex, rows.length, innerWidth);
                    return series.map((item, seriesIndex) => {
                      const value = Number(row[item.key]);
                      const x =
                        centerX - singleBarWidth * 1.45 + seriesIndex * (singleBarWidth + 4);
                      const y = scaleY(value, Math.min(0, range.min), range.max, innerHeight);
                      const height = Math.abs(baseY - y);
                      return h('rect', {
                        x,
                        y: value >= 0 ? y : baseY,
                        width: singleBarWidth,
                        height: Math.max(1, height),
                        rx: 3,
                        fill: item.color,
                        opacity: 0.94,
                      });
                    });
                  }),
                  ...renderDateLabels(
                    rows.map((row) => ({ date: String(row.date), left: 0, right: 0 })),
                    innerWidth,
                    innerHeight,
                  ),
                ]),
              ],
            ),
          ]),
          maxStart > 0
            ? h('div', { class: 'chart-range' }, [
                h('span', String(rows[0]?.date ?? '')),
                h('input', {
                  class: 'chart-range__input',
                  type: 'range',
                  min: 0,
                  max: maxStart,
                  value: startIndex.value,
                  onInput: (event: Event) => {
                    startIndex.value = Number((event.target as HTMLInputElement).value);
                  },
                }),
                h('span', String(rows.at(-1)?.date ?? '')),
              ])
            : null,
        ]);
      };
    },
  });

  const GroupedBarChart = defineComponent({
    name: 'GroupedBarChart',
    props: {
      rows: {
        type: Array as PropType<ReadonlyArray<Record<string, number | string>>>,
        required: true,
      },
      series: {
        type: Array as PropType<GroupedSeries[]>,
        required: true,
      },
      unit: {
        type: String,
        required: true,
      },
    },
    setup(props) {
      return () => {
        const innerWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
        const innerHeight = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
        const values = props.rows.flatMap((row) => props.series.map((item) => Number(row[item.key] ?? 0)));
        const range = getRange(values, true);
        const zeroY = scaleY(0, range.min, range.max, innerHeight);
        const groupWidth = innerWidth / props.rows.length;
        const barWidth = Math.max(5, groupWidth / (props.series.length + 0.8));
        const ticks = makeTicks(range.min, range.max, 4);

        return h('div', { class: 'local-widget-stack' }, [
          h(
            'div',
            { class: 'chart-legend' },
            props.series.map((item) =>
              h('span', { key: item.key }, [
                h('i', { style: { backgroundColor: item.color } }),
                item.label,
              ]),
            ),
          ),
          h('div', { class: 'chart-shell' }, [
            h(
              'svg',
              {
                viewBox: `0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`,
                class: 'local-chart-svg',
                role: 'img',
              },
              [
                h(
                  'g',
                  { transform: `translate(${CHART_PADDING.left},${CHART_PADDING.top})` },
                  [
                    ...ticks.flatMap((tick) => {
                      const y = scaleY(tick, range.min, range.max, innerHeight);
                      return [
                        h('line', {
                          key: `tick-line-${tick}`,
                          x1: 0,
                          x2: innerWidth,
                          y1: y,
                          y2: y,
                          class: 'chart-grid-line',
                        }),
                        h(
                          'text',
                          {
                            key: `tick-text-${tick}`,
                            x: -12,
                            y: y + 4,
                            textAnchor: 'end',
                            class: 'chart-axis-label',
                          },
                          formatAxis(tick),
                        ),
                      ];
                    }),
                    ...props.rows.flatMap((row, rowIndex) =>
                      props.series.map((item, seriesIndex) => {
                        const raw = Number(row[item.key] ?? 0);
                        const x = rowIndex * groupWidth + seriesIndex * barWidth + groupWidth * 0.12;
                        const y = scaleY(raw, range.min, range.max, innerHeight);
                        const height = Math.abs(zeroY - y);
                        const barY = raw >= 0 ? y : zeroY;
                        return h('rect', {
                          key: `${String(row.date)}-${item.key}`,
                          x,
                          y: barY,
                          width: barWidth,
                          height: Math.max(height, 1),
                          rx: 2,
                          fill: item.color,
                          opacity: 0.88,
                        });
                      }),
                    ),
                    ...renderDateLabels(
                      props.rows.map((row) => ({
                        date: String(row.date),
                        left: 0,
                        right: 0,
                      })),
                      innerWidth,
                      innerHeight,
                    ),
                  ],
                ),
              ],
            ),
          ]),
          h('div', { class: 'chart-caption' }, '单位：' + props.unit),
        ]);
      };
    },
  });

  const EtfWeeklyFlowsPanel = defineComponent({
    name: 'EtfWeeklyFlowsPanel',
    setup() {
      return () => {
        const rows = buildWeeklyFlowRows();
        const panelHeight = 340;
        const innerWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
        const innerHeight = panelHeight - CHART_PADDING.top - CHART_PADDING.bottom;
        const flowValues = rows.flatMap((row) => {
          const positive = [row.northAmerica, row.europe, row.asia, row.other].filter((value) => value > 0);
          const negative = [row.northAmerica, row.europe, row.asia, row.other].filter((value) => value < 0);
          return [
            positive.reduce((sum, value) => sum + value, 0),
            negative.reduce((sum, value) => sum + value, 0),
          ];
        });
        const flowRange = getRange(flowValues, true);
        const goldRange = getRange(rows.map((row) => row.goldPrice));
        const zeroY = scaleY(0, flowRange.min, flowRange.max, innerHeight);
        const groupWidth = innerWidth / Math.max(rows.length, 1);
        const flowTicks = makeTicks(flowRange.min, flowRange.max, 4);
        const goldTicks = makeTicks(goldRange.min, goldRange.max, 4);
        const series = [
          { key: 'northAmerica', label: '北美', color: marketData.etf.regionColors['North America'] },
          { key: 'europe', label: '欧洲', color: marketData.etf.regionColors.Europe },
          { key: 'asia', label: '亚洲', color: marketData.etf.regionColors.Asia },
          { key: 'other', label: '其他', color: marketData.etf.regionColors.Other },
        ] as const;
        const barWidth = Math.max(14, groupWidth * 0.58);
        const goldPath = buildLinePath(
          rows.map((row) => ({ date: row.date, left: 0, right: row.goldPrice })),
          (_row, index) => scaleX(index, rows.length, innerWidth),
          (row) => scaleY(row.right, goldRange.min, goldRange.max, innerHeight),
        );

        return h('div', { class: 'local-widget-stack etf-weekly-panel' }, [
          h('div', { class: 'etf-weekly-panel__toolbar' }, [
            h('div', { class: 'etf-weekly-panel__toggle' }, [
              h('button', { type: 'button', class: 'is-active' }, '吨'),
              h('button', { type: 'button' }, '美元'),
            ]),
            h('div', { class: 'etf-weekly-panel__actions' }, [
              h('div', { class: 'etf-weekly-panel__periods' }, [
                h('button', { type: 'button' }, '每年'),
                h('button', { type: 'button' }, '季度'),
                h('button', { type: 'button' }, '每月'),
                h('button', { type: 'button', class: 'is-active' }, '每周'),
              ]),
              h(
                'a',
                {
                  class: 'etf-weekly-panel__link',
                  href: ETF_REFERENCE_URL,
                  target: '_blank',
                  rel: 'noreferrer',
                },
                '官方数据页',
              ),
            ]),
          ]),
          h('div', { class: 'etf-weekly-panel__axis-head' }, [
            h('span', '需求（吨）'),
            h('span', '黄金（美元/盎司）'),
          ]),
          h('div', { class: 'chart-shell chart-shell--etf-weekly' }, [
            h(
              'svg',
              {
                viewBox: `0 0 ${CHART_WIDTH} ${panelHeight}`,
                class: 'local-chart-svg',
                role: 'img',
              },
              [
                h(
                  'g',
                  { transform: `translate(${CHART_PADDING.left},${CHART_PADDING.top})` },
                  [
                    ...flowTicks.flatMap((tick) => {
                      const y = scaleY(tick, flowRange.min, flowRange.max, innerHeight);
                      return [
                        h('line', {
                          key: `flow-grid-${tick}`,
                          x1: 0,
                          x2: innerWidth,
                          y1: y,
                          y2: y,
                          class: 'chart-grid-line',
                        }),
                        h(
                          'text',
                          {
                            key: `flow-axis-${tick}`,
                            x: -12,
                            y: y + 4,
                            textAnchor: 'end',
                            class: 'chart-axis-label',
                          },
                          formatAxis(tick),
                        ),
                      ];
                    }),
                    h('line', {
                      x1: 0,
                      x2: innerWidth,
                      y1: zeroY,
                      y2: zeroY,
                      class: 'chart-zero-line',
                    }),
                    ...goldTicks.map((tick) => {
                      const y = scaleY(tick, goldRange.min, goldRange.max, innerHeight);
                      return h(
                        'text',
                        {
                          key: `gold-axis-${tick}`,
                          x: innerWidth + 12,
                          y: y + 4,
                          textAnchor: 'start',
                          class: 'chart-axis-label',
                        },
                        formatAxis(tick),
                      );
                    }),
                    ...rows.flatMap((row, rowIndex) => {
                      let positiveOffset = zeroY;
                      let negativeOffset = zeroY;
                      const centerX = rowIndex * groupWidth + groupWidth / 2;
                      return series.map((item) => {
                        const raw = row[item.key];
                        const barHeight = Math.abs(scaleY(raw, flowRange.min, flowRange.max, innerHeight) - zeroY);
                        if (raw >= 0) {
                          positiveOffset -= barHeight;
                          return h('rect', {
                            key: `${row.date}-${item.key}`,
                            x: centerX - barWidth / 2,
                            y: positiveOffset,
                            width: barWidth,
                            height: Math.max(barHeight, 1),
                            rx: 3,
                            fill: item.color,
                            opacity: 0.92,
                          });
                        }
                        const currentY = negativeOffset;
                        negativeOffset += barHeight;
                        return h('rect', {
                          key: `${row.date}-${item.key}`,
                          x: centerX - barWidth / 2,
                          y: currentY,
                          width: barWidth,
                          height: Math.max(barHeight, 1),
                          rx: 3,
                          fill: item.color,
                          opacity: 0.92,
                        });
                      });
                    }),
                    h('path', {
                      d: goldPath,
                      fill: 'none',
                      stroke: '#d3a13a',
                      strokeWidth: 2.5,
                      strokeLinecap: 'round',
                    }),
                    ...renderDateLabels(
                      rows.map((row) => ({ date: row.date, left: 0, right: 0 })),
                      innerWidth,
                      innerHeight,
                    ),
                  ],
                ),
              ],
            ),
          ]),
          h(
            'div',
            { class: 'chart-legend chart-legend--weekly etf-weekly-panel__legend' },
            [
              ...series.map((item) =>
                h('span', { key: item.key }, [h('i', { style: { backgroundColor: item.color } }), item.label]),
              ),
              h('span', { key: 'gold' }, [h('i', { style: { backgroundColor: '#d3a13a' } }), '金价（右轴）']),
            ],
          ),
        ]);
      };
    },
  });

  const YtdSummaryPanel = defineComponent({
    name: 'YtdSummaryPanel',
    setup() {
      return () => {
        const asia = marketData.etf.ytdSummary.find((item) => item.region === 'Asia');
        return h('div', { class: 'local-widget-stack ytd-module' }, [
          h('div', { class: 'ytd-module__metrics' }, [
            h('article', [h('span', '统计口径'), h('strong', 'Year to Date')]),
            h('article', [h('span', '最新周度'), h('strong', marketData.etf.latestWeek)]),
            h('article', [h('span', '亚洲需求'), h('strong', `${asia?.demandTonnes?.toFixed(2) ?? '0.00'} 吨`)]),
          ]),
          h('div', { class: 'ytd-module__table' }, [
            h('div', { class: 'ytd-module__table-head' }, [
              h('span', '地区'),
              h('span', '年内流量'),
              h('span', '持仓吨数'),
              h('span', '需求吨数'),
            ]),
            ...marketData.etf.ytdSummary.map((item) =>
              h('div', { key: item.region, class: 'ytd-module__table-row' }, [
                h('strong', regionLabel(item.region)),
                h('span', formatSigned(item.flowUsdMn) + ' 百万美元'),
                h('span', item.holdingsTonnes.toFixed(2) + ' 吨'),
                h('span', formatSigned(item.demandTonnes) + ' 吨'),
              ]),
            ),
          ]),
        ]);
      };
    },
  });

  const ReserveRanking = defineComponent({
    name: 'ReserveRanking',
    props: {
      rows: {
        type: Array as PropType<Array<{ label: string; value: number; sublabel: string; detail?: string }>>,
        required: true,
      },
      color: {
        type: String,
        required: true,
      },
      diverging: {
        type: Boolean,
        default: false,
      },
    },
    setup(props) {
      return () => {
        const maxAbs = Math.max(...props.rows.map((row) => Math.abs(row.value)), 1);
        return h(
          'div',
          { class: 'reserve-module' },
          props.rows.map((row) => {
            const width = `${(Math.abs(row.value) / maxAbs) * 100}%`;
            const tone = props.diverging ? (row.value >= 0 ? '#148b6a' : '#dc2626') : props.color;
            return h('article', { key: `${row.label}-${row.value}`, class: 'reserve-module__item' }, [
              h('div', { class: 'reserve-module__header' }, [
                h('div', { class: 'reserve-module__title' }, [h('strong', row.label), h('span', row.sublabel)]),
                row.detail ? h('span', { class: 'reserve-module__detail' }, row.detail) : null,
              ]),
              h('div', { class: 'reserve-module__track' }, [
                h('div', {
                  class: 'reserve-module__fill',
                  style: {
                    width,
                    backgroundColor: tone,
                    minWidth: props.diverging && row.value < 0 ? '12px' : undefined,
                  },
                }),
              ]),
              h('div', { class: 'reserve-module__value' }, formatSigned(row.value) + ' 吨'),
            ]);
          }),
        );
      };
    },
  });

  const SnapshotDetailTable = defineComponent({
    name: 'SnapshotDetailTable',
    props: {
      groups: {
        type: Array as PropType<SnapshotTableGroup[]>,
        required: true,
      },
    },
    setup(props) {
      return () =>
        h('div', { class: 'snapshot-table' }, [
          h('div', { class: 'snapshot-table__shell' }, [
            h('table', { class: 'snapshot-table__table' }, [
              h('thead', [
                h('tr', [
                  h('th', '名称 / 代码'),
                  h('th', { class: 'is-center' }, '30日'),
                  h('th', { class: 'is-right' }, '收盘'),
                  h('th', { class: 'is-center' }, '1D'),
                  h('th', { class: 'is-center' }, 'YTD'),
                  h('th', { class: 'is-center' }, 'QTD'),
                  h('th', { class: 'is-center' }, '1周'),
                  h('th', { class: 'is-center' }, '1月'),
                  h('th', { class: 'is-center' }, '1年'),
                  h('th', { class: 'is-center' }, '52周高'),
                  h('th', { class: 'is-center' }, '1H'),
                  h('th', { class: 'is-center' }, '4H'),
                  h('th', { class: 'is-center' }, '日线'),
                  h('th', { class: 'is-center' }, '3日线'),
                  h('th', { class: 'is-center' }, '周线'),
                ]),
              ]),
              h(
                'tbody',
                props.groups.flatMap((group) => [
                  h('tr', { key: `${group.label}-group`, class: 'snapshot-table__group-row' }, [
                    h('td', { colspan: 15 }, [
                      h('span', { class: 'snapshot-table__group-title' }, `▼ ${group.label}`),
                    ]),
                  ]),
                  ...group.rows.map((row) =>
                    h('tr', { key: row.symbol, class: 'snapshot-table__row' }, [
                      h('td', [
                        h('div', { class: 'snapshot-table__name-wrap' }, [
                          h('strong', row.name),
                          h('span', row.symbol),
                        ]),
                      ]),
                      h('td', { class: 'is-center' }, [
                        h(
                          'svg',
                          { class: 'snapshot-table__sparkline', viewBox: '0 0 96 24', preserveAspectRatio: 'none' },
                          [
                            h('polyline', {
                              points: compactSparkline(row.spark, 96, 24),
                              class: sparkStrokeClass(row.d1),
                            }),
                          ],
                        ),
                      ]),
                      h('td', { class: 'is-right' }, row.price),
                      h('td', { class: 'is-center' }, [h('span', { class: ['snapshot-table__chip', chipTone(row.d1)] }, row.d1)]),
                      h('td', { class: 'is-center' }, [h('span', { class: ['snapshot-table__chip', chipTone(row.ytd)] }, row.ytd)]),
                      h('td', { class: 'is-center' }, [h('span', { class: ['snapshot-table__chip', chipTone(row.qtd)] }, row.qtd)]),
                      h('td', { class: 'is-center' }, [h('span', { class: ['snapshot-table__chip', chipTone(row.w1)] }, row.w1)]),
                      h('td', { class: 'is-center' }, [h('span', { class: ['snapshot-table__chip', chipTone(row.m1)] }, row.m1)]),
                      h('td', { class: 'is-center' }, [h('span', { class: ['snapshot-table__chip', chipTone(row.y1)] }, row.y1)]),
                      h('td', { class: 'snapshot-table__high-cell-td' }, [
                        h('div', { class: 'snapshot-table__high-cell' }, [
                          h('div', { class: 'snapshot-table__high-track' }, [
                            h('i', {
                              class: sparkStrokeClass(row.high),
                              style: { width: `${highWidth(row.high)}%` },
                            }),
                          ]),
                          h('span', { class: toneClass(parseTone(row.high)) }, row.high),
                        ]),
                      ]),
                      h('td', { class: ['is-center', arrowClass(row.d10)] }, row.d10),
                      h('td', { class: ['is-center', arrowClass(row.d20)] }, row.d20),
                      h('td', { class: ['is-center', arrowClass(row.d50)] }, row.d50),
                      h('td', { class: ['is-center', arrowClass(row.d200)] }, row.d200),
                      h('td', { class: ['is-center', arrowClass(row.x2050)] }, row.x2050),
                    ]),
                  ),
                ]),
              ),
            ]),
          ]),
        ]);
    },
  });

  const LocalChartWidget = defineComponent({
    name: 'LocalChartWidget',
    props: {
      widget: {
        type: Object as PropType<WidgetConfig>,
        required: true,
      },
    },
    setup(props) {
      return () => {
        try {
          const key = props.widget.localKey as LocalWidgetKey;

          switch (key) {
            case 'spdr-daily-flow':
              return h(DualAxisChart, {
                  rows: marketData.spdr.history.slice(-60).map((point) => ({
                    date: point.date,
                    left: point.flowTonnes ?? 0,
                    right: point.goldPrice,
                  })),
                  leftLabel: 'SPDR 日流量',
                  rightLabel: '黄金价格',
                  leftUnit: '吨',
                  rightUnit: '美元/盎司',
                  leftColor: '#159a76',
                  rightColor: '#2f63f2',
                  barPositiveColor: '#18a17d',
                  barNegativeColor: '#de5d56',
                  barWidthRatio: 0.7,
                  leftAsBars: true,
                  divergingBars: true,
                });
            case 'spdr-holdings-vs-price':
              return h(DualAxisChart, {
                  rows: marketData.spdr.history.slice(-60).map((point) => ({
                    date: point.date,
                    left: point.tonnes,
                    right: point.goldPrice,
                  })),
                  leftLabel: 'SPDR 持仓量',
                  rightLabel: '黄金价格',
                  leftUnit: '吨',
                  rightUnit: '美元/盎司',
                  leftColor: '#d6ae4a',
                  rightColor: '#2f63f2',
                  barWidthRatio: 0.6,
                  leftAsBars: true,
                });
            case 'etf-weekly-flows':
              return h(EtfWeeklyFlowsPanel);
            case 'etf-ytd-summary':
              return h(YtdSummaryPanel);
            case 'central-bank-holders':
              return h(ReserveRanking, {
                rows: marketData.centralBank.topHolders.map((item) => ({
                  label: item.name,
                  value: item.tonnes,
                  sublabel: item.region,
                  detail: item.region,
                })),
                color: '#c7931a',
              });
            case 'central-bank-buyers':
              return h(ReserveRanking, {
                rows: marketData.centralBank.strategicBuyers.map((item) => ({
                  label: item.name,
                  value: item.deltaTonnes,
                  sublabel: item.startTonnes.toFixed(2) + ' → ' + item.endTonnes.toFixed(2) + ' 吨',
                  detail: item.startTonnes.toFixed(2) + ' → ' + item.endTonnes.toFixed(2) + ' 吨',
                })),
                color: '#165dff',
                diverging: true,
              });
            case 'gold-vs-nominal':
              return h(DualAxisChart, {
                rows: mergeGoldWithSeries('nominal10Y'),
                leftLabel: '黄金价格代理',
                rightLabel: '美国 10Y 名义利率',
                leftUnit: '美元/盎司',
                rightUnit: '%',
                leftColor: '#c7931a',
                rightColor: '#165dff',
              });
            case 'gold-vs-breakeven':
              return h(DualAxisChart, {
                rows: mergeGoldWithSeries('breakeven10Y'),
                leftLabel: '黄金价格代理',
                rightLabel: '10Y Breakeven',
                leftUnit: '美元/盎司',
                rightUnit: '%',
                leftColor: '#c7931a',
                rightColor: '#0f8b6d',
              });
            case 'gold-vs-real':
              return h(DualAxisChart, {
                rows: mergeGoldWithSeries('real10Y'),
                leftLabel: '黄金价格代理',
                rightLabel: '美国 10Y 实际利率',
                leftUnit: '美元/盎司',
                rightUnit: '%',
                leftColor: '#c7931a',
                rightColor: '#7c3aed',
              });
            case 'gold-vs-gvz':
              return h(DualAxisChart, {
                rows: mergeGoldWithGvz(),
                leftLabel: '黄金价格代理',
                rightLabel: 'GVZ',
                leftUnit: '美元/盎司',
                rightUnit: '指数点',
                leftColor: '#c7931a',
                rightColor: '#dc2626',
              });
            case 'gold-market-detail-table':
              return h(TerminalDetailPanel, {
                title: '市场明细',
                marketId: 'gold',
                columns: marketTerminalConfigs.gold.detailColumns,
                groups: marketTerminalConfigs.gold.detailGroups,
                rotationButtonLabel: marketTerminalConfigs.gold.rotationButtonLabel,
                rotationHeatmap: marketTerminalConfigs.gold.rotationHeatmap,
              });
            case 'macro-market-detail-table':
              return h(TerminalDetailPanel, {
                title: '市场明细',
                marketId: 'macro',
                columns: marketTerminalConfigs.macro.detailColumns,
                groups: marketTerminalConfigs.macro.detailGroups,
              });
            case 'crypto-market-detail-table':
              return h(TerminalDetailPanel, {
                title: '市场明细',
                marketId: 'crypto',
                columns: marketTerminalConfigs.crypto.detailColumns,
                groups: marketTerminalConfigs.crypto.detailGroups,
                rotationButtonLabel: marketTerminalConfigs.crypto.rotationButtonLabel,
                rotationHeatmap: marketTerminalConfigs.crypto.rotationHeatmap,
              });
            case 'btc-etf-flow':
              return h(DualAxisChart, {
                  rows: BTC_ETF_FLOW_ROWS,
                  leftLabel: 'BTC ETF 日净流量',
                  rightLabel: 'BTC 价格',
                  leftUnit: '百万美元',
                  rightUnit: '美元',
                  leftColor: '#1b9a7a',
                  rightColor: '#2f63f2',
                  barPositiveColor: '#1b9a7a',
                  barNegativeColor: '#df5a55',
                  barWidthRatio: 0.68,
                  leftAsBars: true,
                  divergingBars: true,
                  showRangeSlider: true,
                  windowSize: 8,
                });
            case 'btc-treasury-flow':
              return h(TreasuryFlowChart);
            default:
              return h('div', { class: 'local-empty' }, '该图表配置尚未接入。');
          }
        } catch (error) {
          console.error('[hedgeBoard] Local widget render failed:', props.widget.title, error);
          return h(
            'div',
            { class: 'local-empty' },
            '该研究卡片的数据格式暂未兼容，已自动跳过，不影响其他模块浏览。',
          );
        }
      };
    },
  });

  function mergeGoldWithSeries(key: 'nominal10Y' | 'real10Y' | 'breakeven10Y'): DualChartRow[] {
    const goldMap = new Map<string, number>(
      marketData.spdr.history.map((point) => [point.date as string, point.goldPrice]),
    );

    return marketData.treasury.history
      .filter((point) => goldMap.has(point.date as string))
      .slice(-120)
      .map((point) => ({
        date: point.date,
        left: goldMap.get(point.date as string) ?? 0,
        right: point[key],
      }));
  }

  function mergeGoldWithGvz(): DualChartRow[] {
    const goldMap = new Map<string, number>(
      marketData.spdr.history.map((point) => [point.date as string, point.goldPrice]),
    );

    return marketData.options.history
      .filter((point) => goldMap.has(point.date as string))
      .slice(-120)
      .map((point) => ({
        date: point.date,
        left: goldMap.get(point.date as string) ?? 0,
        right: point.gvz,
      }));
  }

  function buildWeeklyFlowRows(): WeeklyFlowRow[] {
    const goldMap = new Map<string, number>(
      marketData.spdr.history.map((point) => [point.date as string, point.goldPrice]),
    );
    let latestKnownGold = marketData.spot.price;

    return marketData.etf.weeklyFlows.map((row) => {
      const date = String(row.date);
      const matchedGold = goldMap.get(date);
      if (typeof matchedGold === 'number') {
        latestKnownGold = matchedGold;
      }
      return {
        date,
        northAmerica: Number(row['North America'] ?? 0),
        europe: Number(row.Europe ?? 0),
        asia: Number(row.Asia ?? 0),
        other: Number(row.Other ?? 0),
        goldPrice: latestKnownGold,
      };
    });
  }

  function renderDateLabels(rows: DualChartRow[], innerWidth: number, innerHeight: number) {
    const targetCount = 6;
    const step = Math.max(1, Math.floor(rows.length / targetCount));

    return rows
      .map((row, index) => {
        if (index % step !== 0 && index !== rows.length - 1) return null;
        const x = scaleX(index, rows.length, innerWidth);
        return h(
          'text',
          {
            key: `${row.date}-label`,
            x,
            y: innerHeight + 22,
            textAnchor: 'middle',
            class: 'chart-axis-label',
          },
          row.date.slice(5),
        );
      })
      .filter(Boolean);
  }

  function buildLinePath(
    rows: DualChartRow[],
    getX: (row: DualChartRow, index: number) => number,
    getY: (row: DualChartRow) => number,
  ) {
    return rows
      .map(
        (row, index) =>
          `${index === 0 ? 'M' : 'L'} ${getX(row, index).toFixed(2)} ${getY(row).toFixed(2)}`,
      )
      .join(' ');
  }

  function scaleX(index: number, total: number, innerWidth: number) {
    if (total <= 1) return 0;
    return (index / (total - 1)) * innerWidth;
  }

  function scaleY(value: number, min: number, max: number, innerHeight: number) {
    if (max === min) return innerHeight / 2;
    return innerHeight - ((value - min) / (max - min)) * innerHeight;
  }

  function getRange(values: number[], includeZero = false) {
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const rawMin = includeZero ? Math.min(0, minValue) : minValue;
    const rawMax = includeZero ? Math.max(0, maxValue) : maxValue;
    const padding = (rawMax - rawMin || 1) * 0.12;

    return {
      min: rawMin - padding,
      max: rawMax + padding,
    };
  }

  function makeTicks(min: number, max: number, count: number) {
    if (count <= 1) return [min, max];
    return Array.from({ length: count }, (_, index) => min + ((max - min) * index) / (count - 1));
  }

  function formatAxis(value: number) {
    return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(2);
  }

  function formatNumber(value: number) {
    return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(2);
  }

  function formatSigned(value: number) {
    const prefix = value > 0 ? '+' : '';
    return `${prefix}${formatNumber(value)}`;
  }

  function parseTone(value: string) {
    const numeric = Number(String(value).replace(/[^\d+-.]/g, ''));
    return Number.isFinite(numeric) ? numeric : 0;
  }

  function chipTone(value: string) {
    return parseTone(value) >= 0 ? 'is-positive-chip' : 'is-negative-chip';
  }

  function toneClass(value: number) {
    return value >= 0 ? 'is-positive-text' : 'is-negative-text';
  }

  function sparkStrokeClass(value: string) {
    return parseTone(value) >= 0 ? 'is-positive-line' : 'is-negative-line';
  }

  function arrowClass(value: string) {
    if (value === '▲') return 'is-positive-text';
    if (value === '▼') return 'is-negative-text';
    return '';
  }

  function highWidth(value: string) {
    const distance = Math.abs(parseTone(value));
    return Math.max(36, Math.min(100, 100 - distance * 1.35));
  }

  function compactSparkline(points: number[], width: number, height: number) {
    if (!points.length) return `0,${(height / 2).toFixed(2)} ${width},${(height / 2).toFixed(2)}`;

    const min = Math.min(...points);
    const max = Math.max(...points);
    const range = max - min || 1;

    return points
      .map((point, index) => {
        const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
        const y = height - ((point - min) / range) * height;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ');
  }

  function regionLabel(value: string) {
    switch (value) {
      case 'North America':
        return '北美';
      case 'Europe':
        return '欧洲';
      case 'Asia':
        return '亚洲';
      case 'Other':
        return '其他';
      default:
        return value;
    }
  }
</script>

<style lang="less" scoped>
  .hedge-board {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .hedge-board__tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .hedge-board__tab {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 78px;
    padding: 10px 16px;
    border: 1px solid var(--hedge-cool-border);
    border-radius: 999px;
    background: rgba(247, 251, 253, 0.94);
    color: #54636a;
    font-size: 13px;
    font-weight: 700;
    transition: all 0.2s ease;
  }

  .hedge-board__tab.is-active {
    border-color: rgba(22, 93, 255, 0.2);
    background: var(--hedge-cool-text);
    color: #fff;
    box-shadow: 0 10px 24px rgba(23, 50, 45, 0.12);
  }

  .terminal-page {
    display: grid;
    grid-template-columns: 260px minmax(0, 1fr);
    gap: 18px;
    min-height: calc(100vh - 140px);
  }

  .strategy-sidebar,
  .platform-topbar,
  .hero-panel,
  .strategy-strip__card,
  .module-subnav,
  .formula-strip,
  .source-strip,
  .chart-section,
  .widget-card {
    border: 1px solid var(--hedge-cool-border);
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(243, 248, 252, 0.96)),
      #fff;
    box-shadow: 0 18px 45px rgba(31, 41, 55, 0.05);
  }

  .strategy-sidebar {
    position: sticky;
    top: 88px;
    display: flex;
    flex-direction: column;
    gap: 18px;
    align-self: start;
    padding: 18px;
    border-radius: 24px;
  }

  .strategy-sidebar__brand p,
  .platform-topbar__title p,
  .eyebrow {
    margin: 0;
    color: #4f6b82;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  .strategy-sidebar__brand h1,
  .platform-topbar__title h2,
  .hero-panel__copy h2,
  .module-heading h3,
  .chart-section__heading h4,
  .widget-card__header h5 {
    margin: 0;
    color: var(--hedge-cool-text);
  }

  .strategy-sidebar__brand h1 {
    margin-top: 8px;
    font-size: 28px;
    line-height: 1.1;
  }

  .strategy-sidebar__brand span,
  .strategy-sidebar__intro p {
    color: var(--hedge-cool-muted);
    font-size: 13px;
    line-height: 1.8;
  }

  .strategy-sidebar__intro strong {
    color: var(--hedge-cool-text);
    font-size: 14px;
  }

  .strategy-sidebar__nav {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .strategy-sidebar__link {
    display: block;
    padding: 14px 16px;
    border: 1px solid rgba(201, 213, 226, 0.52);
    border-radius: 18px;
    background: rgba(243, 247, 250, 0.92);
    transition: all 0.2s ease;

    span,
    strong,
    small {
      display: block;
    }

    span {
      color: var(--hedge-cool-muted);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.14em;
    }

    strong {
      margin: 8px 0 6px;
      color: var(--hedge-cool-text);
      font-size: 16px;
    }

    small {
      color: var(--hedge-cool-muted);
      font-size: 12px;
      line-height: 1.7;
    }

    &:hover,
    &.is-active {
      transform: translateY(-1px);
      border-color: rgba(142, 164, 187, 0.72);
      background: linear-gradient(135deg, rgba(226, 236, 244, 0.96), rgba(248, 251, 253, 0.98));
    }
  }

  .terminal-content {
    display: flex;
    flex-direction: column;
    gap: 16px;
    min-width: 0;
  }

  .platform-topbar,
  .hero-panel,
  .module-subnav,
  .formula-strip,
  .source-strip,
  .chart-section {
    border-radius: 24px;
  }

  .platform-topbar,
  .hero-panel,
  .module-subnav,
  .formula-strip,
  .source-strip,
  .chart-section {
    padding: 22px;
  }

  .platform-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
  }

  .platform-topbar__title h2 {
    margin: 8px 0;
    font-size: 30px;
  }

  .platform-topbar__title span {
    color: var(--hedge-cool-muted);
    font-size: 13px;
  }

  .platform-topbar__meta {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;

    span {
      padding: 9px 12px;
      border-radius: 999px;
      background: rgba(243, 247, 250, 0.94);
      color: var(--hedge-cool-muted);
      font-size: 12px;
      font-weight: 700;
    }
  }

  .hero-panel {
    display: grid;
    grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.9fr);
    gap: 18px;
    background:
      radial-gradient(circle at top right, rgba(163, 190, 214, 0.28), transparent 34%),
      linear-gradient(135deg, #14312d, #284b45);
  }

  .hero-panel__copy h2,
  .hero-panel__copy .eyebrow,
  .hero-panel__copy .hero-panel__lead,
  .hero-panel__meta span,
  .hero-panel__meta strong {
    color: #f7f1e4;
  }

  .hero-panel__copy h2 {
    margin: 10px 0 14px;
    font-size: clamp(30px, 3vw, 44px);
    line-height: 1.05;
  }

  .hero-panel__lead {
    max-width: 780px;
    font-size: 14px;
    line-height: 1.9;
    opacity: 0.9;
  }

  .hero-panel__meta {
    display: grid;
    gap: 12px;

    article {
      padding: 16px 18px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.07);
    }

    span {
      display: block;
      margin-bottom: 8px;
      font-size: 12px;
      opacity: 0.75;
    }

    strong {
      font-size: 16px;
      line-height: 1.6;
    }
  }

  .strategy-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }

  .strategy-strip__card {
    display: block;
    padding: 18px 18px 16px;
    border-radius: 22px;
    transition: all 0.2s ease;

    span,
    strong,
    p {
      display: block;
    }

    span {
      color: var(--hedge-cool-muted);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.14em;
      text-transform: uppercase;
    }

    strong {
      margin: 10px 0 8px;
      color: var(--hedge-cool-text);
      font-size: 18px;
    }

    p {
      margin: 0;
      color: var(--hedge-cool-muted);
      font-size: 13px;
      line-height: 1.75;
    }

    &:hover,
    &.is-active {
      transform: translateY(-2px);
      border-color: rgba(142, 164, 187, 0.72);
      background: linear-gradient(135deg, rgba(226, 236, 244, 0.96), rgba(248, 251, 253, 0.98));
    }
  }

  .research-module {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .module-heading {
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    gap: 18px;
  }

  .module-heading h3 {
    margin-top: 8px;
    font-size: 34px;
    line-height: 1.08;
  }

  .module-heading__lead,
  .module-heading__summary p,
  .chart-section__heading p,
  .widget-card__header p,
  .widget-card__footer,
  .chart-caption {
    color: var(--hedge-cool-muted);
    font-size: 13px;
    line-height: 1.85;
  }

  .module-heading__summary {
    padding: 20px 22px;
    border: 1px solid var(--hedge-cool-border);
    border-radius: 22px;
    background: rgba(247, 251, 253, 0.9);
  }

  .module-heading__summary p {
    margin: 0;
  }

  .module-heading__tags,
  .source-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .module-heading__tags span,
  .source-strip a {
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(243, 247, 250, 0.94);
    color: var(--hedge-cool-muted);
    font-size: 12px;
    font-weight: 700;
  }

  .module-subnav {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .module-subnav button {
    flex: 1 1 180px;
    padding: 14px 16px;
    border: 1px solid rgba(201, 213, 226, 0.58);
    border-radius: 18px;
    background: rgba(242, 247, 251, 0.88);
    text-align: left;
    cursor: pointer;
  }

  .module-subnav__title-row {
    display: inline-flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 8px;
    color: var(--hedge-cool-text);
    font-size: 14px;
    font-weight: 700;
    line-height: 1.4;
  }

  .module-subnav__title-row strong {
    color: inherit;
    font-size: inherit;
    font-weight: inherit;
    line-height: inherit;
  }

  .module-subnav__index {
    color: inherit;
    font-size: inherit;
    font-weight: inherit;
    line-height: inherit;
    letter-spacing: 0.01em;
  }

  .formula-strip {
    display: grid;
    grid-template-columns: 280px minmax(0, 1fr);
    gap: 18px;
    background: linear-gradient(135deg, rgba(226, 236, 244, 0.96), rgba(248, 251, 253, 0.98));
  }

  .formula-strip span {
    display: block;
    color: var(--hedge-cool-muted);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  .formula-strip strong {
    display: block;
    margin-top: 8px;
    color: var(--hedge-cool-text);
    font-size: 18px;
  }

  .formula-strip p {
    margin: 0;
    color: var(--hedge-cool-muted);
    font-size: 14px;
    line-height: 1.9;
  }

  .chart-section__heading {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 18px;
    margin-bottom: 18px;
  }

  .chart-section__heading h4 {
    margin-top: 0;
    font-size: 28px;
  }

  .chart-section__heading p {
    max-width: 720px;
    margin: 0;
  }

  .widget-grid {
    display: grid;
    gap: 16px;
  }

  .widget-grid--hero {
    grid-template-columns: 1fr;
  }

  .widget-grid--two {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .widget-grid--three {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .widget-card {
    display: flex;
    flex-direction: column;
    border-radius: 22px;
    overflow: hidden;
  }

  .widget-card__header {
    padding: 18px 20px 10px;
  }

  .widget-card__title-row {
    display: flex;
    align-items: baseline;
    flex-wrap: wrap;
    gap: 12px;
  }

  .widget-card__header h5 {
    margin: 0;
    font-size: 18px;
    line-height: 1.3;
  }

  .widget-card__index,
  .widget-card__footer {
    margin: 8px 0 0;
  }

  .widget-card__index {
    margin: 0;
    color: var(--hedge-cool-text);
    font-size: 18px;
    font-weight: 700;
    line-height: 1.3;
    letter-spacing: 0.01em;
  }

  .widget-card__footer {
    padding: 12px 20px 18px;
    border-top: 1px solid rgba(201, 213, 226, 0.58);
  }

  .widget-frame,
  .local-widget-stack,
  .local-empty {
    padding: 0 20px 18px;
  }

  .local-empty {
    color: var(--hedge-cool-muted);
    font-size: 13px;
    line-height: 1.8;
  }

  .metric-strip {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 10px;
    margin-bottom: 14px;
  }

  .metric-strip article {
    padding: 12px 14px;
    border: 1px solid rgba(201, 213, 226, 0.58);
    border-radius: 16px;
    background: rgba(242, 247, 251, 0.88);
  }

  .metric-strip span {
    display: block;
    color: #7a7f86;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  .metric-strip strong {
    display: block;
    margin-top: 6px;
    color: var(--hedge-cool-text);
    font-size: 16px;
    line-height: 1.4;
  }

  .chart-shell {
    overflow: hidden;
    border: 1px solid rgba(201, 213, 226, 0.58);
    border-radius: 18px;
    background: #fff;
  }

  .local-chart-svg {
    display: block;
    width: 100%;
    height: auto;
  }

  .chart-grid-line {
    stroke: rgba(15, 23, 42, 0.08);
    stroke-width: 1;
  }

  .chart-axis-label {
    fill: #7a7f86;
    font-size: 11px;
  }

.chart-topline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 10px;
  }

  .chart-axis-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex: 1;
    color: var(--hedge-cool-muted);
    font-size: 11px;
    font-weight: 700;
  }

  .chart-axis-head span:last-child {
    text-align: right;
  }

  .chart-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 10px;
  }

  .chart-legend span {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    color: var(--hedge-cool-muted);
    font-size: 12px;
    font-weight: 700;
  }

  .chart-legend i {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .chart-zero-line {
    stroke: rgba(111, 125, 151, 0.38);
    stroke-width: 1.2;
    stroke-dasharray: 3 3;
  }

  .etf-weekly-panel {
    gap: 12px;
    padding-top: 4px;
  }

  .etf-weekly-panel__toolbar {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
  }

  .etf-weekly-panel__toggle,
  .etf-weekly-panel__periods {
    display: inline-flex;
    align-items: center;
    gap: 0;
    border: 1px solid var(--hedge-cool-border);
    border-radius: 10px;
    overflow: hidden;
    background: #f8f8f7;
  }

  .etf-weekly-panel__toggle button,
  .etf-weekly-panel__periods button {
    padding: 10px 14px;
    border: none;
    background: transparent;
    color: var(--hedge-cool-text);
    font-size: 13px;
    font-weight: 700;
  }

  .etf-weekly-panel__toggle button.is-active,
  .etf-weekly-panel__periods button.is-active {
    background: #35586e;
    color: #fff;
  }

  .etf-weekly-panel__actions {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-left: auto;
  }

  .etf-weekly-panel__link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 10px 14px;
    border-radius: 10px;
    background: #35586e;
    color: #fff;
    font-size: 13px;
    font-weight: 700;
  }

  .etf-weekly-panel__axis-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 18px 0 18px;
    color: var(--hedge-cool-muted);
    font-size: 13px;
  }

  .chart-shell--etf-weekly {
    border-radius: 0;
    border-left: none;
    border-right: none;
    border-bottom: none;
    background: transparent;
  }

.chart-legend--weekly {
    margin-top: 6px;
    margin-bottom: 0;
  }

  .etf-weekly-panel__legend {
    justify-content: flex-start;
    padding: 0 18px 6px;
  }

  :deep(.ytd-module) {
    gap: 18px;
    padding-top: 8px;
  }

  :deep(.ytd-module__metrics) {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }

  :deep(.ytd-module__metrics article) {
    min-height: 100px;
    padding: 14px 16px;
    border: 1px solid rgba(15, 23, 42, 0.07);
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  :deep(.ytd-module__metrics span) {
    display: block;
    color: rgba(0, 0, 0, 0.45);
    font-size: 12px;
  }

  :deep(.ytd-module__metrics strong) {
    display: block;
    margin-top: 12px;
    color: rgba(0, 0, 0, 0.88);
    font-size: 18px;
    line-height: 1.35;
  }

  :deep(.ytd-module__table) {
    border: 1px solid rgba(15, 23, 42, 0.07);
    border-radius: 10px;
    overflow: hidden;
    background: #fff;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  :deep(.ytd-module__table-head),
  :deep(.ytd-module__table-row) {
    display: grid;
    grid-template-columns: 1.1fr 1fr 1fr 1fr;
    gap: 12px;
    padding: 14px 16px;
    font-size: 14px;
  }

  :deep(.ytd-module__table-head) {
    background: #fafafa;
    color: rgba(0, 0, 0, 0.45);
    font-weight: 700;
    font-size: 12px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  :deep(.ytd-module__table-row) {
    border-top: 1px solid rgba(15, 23, 42, 0.07);
    color: rgba(0, 0, 0, 0.65);
    align-items: center;
  }

  :deep(.ytd-module__table-row strong) {
    color: rgba(0, 0, 0, 0.88);
    font-size: 15px;
  }

  :deep(.reserve-module) {
    display: grid;
    gap: 18px;
    padding-top: 4px;
  }

  :deep(.reserve-module__item) {
    display: grid;
    gap: 10px;
    padding: 2px 0;
  }

  :deep(.reserve-module__header) {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
  }

  :deep(.reserve-module__title strong) {
    display: block;
    color: rgba(0, 0, 0, 0.88);
    font-size: 15px;
    font-weight: 700;
  }

  :deep(.reserve-module__title span),
  :deep(.reserve-module__detail) {
    color: rgba(0, 0, 0, 0.45);
    font-size: 12px;
    line-height: 1.6;
  }

  :deep(.reserve-module__title span) {
    display: inline;
  }

  :deep(.reserve-module__track) {
    height: 12px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.18);
    overflow: hidden;
  }

  :deep(.reserve-module__fill) {
    height: 100%;
    border-radius: 999px;
  }

  :deep(.reserve-module__value) {
    color: rgba(0, 0, 0, 0.88);
    font-size: 14px;
    font-weight: 700;
  }

  .chart-section--gold .widget-card__header p {
    max-width: 920px;
    color: var(--hedge-cool-muted);
    line-height: 1.75;
  }

  .terminal-page--gold {
    display: block;
  }

  .terminal-content--gold {
    display: flex;
    flex-direction: column;
    gap: 18px;
    min-width: 0;
  }

  .research-module--gold {
    padding: 0;
    border: none;
    background: transparent;
    box-shadow: none;
    gap: 18px;
  }

  .module-subnav--gold {
    gap: 14px;
  }

  .module-subnav--gold button {
    flex: 1 1 220px;
    padding: 18px 20px;
    border: 1px solid var(--hedge-cool-border-strong);
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 248, 252, 0.98));
    box-shadow: 0 10px 28px rgba(31, 41, 55, 0.04);
  }

  .module-subnav--gold button strong {
    font-size: 18px;
  }

  .chart-section--gold {
    padding: 22px 24px 24px;
    border-radius: 20px;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 248, 252, 0.98)),
      #fff;
    box-shadow: 0 16px 36px rgba(31, 41, 55, 0.04);
  }

  .chart-section--gold .chart-section__heading {
    margin-bottom: 20px;
  }

  .chart-section--gold .chart-section__heading .eyebrow {
    color: #165dff;
  }

  .chart-section--gold .chart-section__heading h4 {
    font-size: 22px;
  }

  .chart-section--gold .widget-card {
    border: 1px solid rgba(201, 213, 226, 0.52);
    border-radius: 18px;
    background: #fff;
    box-shadow: none;
  }

  .chart-section--gold .widget-card__header {
    padding: 18px 18px 10px;
  }

  .chart-section--gold .widget-card__header h5 {
    font-size: 17px;
    letter-spacing: 0.01em;
  }

  .chart-section--gold .widget-card__index {
    font-size: 17px;
    letter-spacing: 0.01em;
  }

  .chart-section--gold .widget-card__footer {
    padding: 12px 18px 16px;
  }

  .chart-section--gold .widget-frame,
  .chart-section--gold .local-widget-stack,
  .chart-section--gold .local-empty {
    padding: 0 18px 16px;
  }

  .chart-section--gold .metric-strip article,
  .chart-section--gold .summary-table,
  .chart-section--gold .chart-shell {
    border-color: rgba(201, 213, 226, 0.58);
    background: #fff;
  }

  .market-matrix {
    padding: 0 18px 18px;
  }

  .market-matrix__table {
    border: 1px solid var(--hedge-cool-border);
    border-radius: 16px;
    overflow: hidden;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 248, 252, 0.96)),
      #fff;
  }

  .market-matrix__head,
  .market-matrix__row {
    display: grid;
    grid-template-columns: minmax(128px, 1.35fr) 96px 78px repeat(5, minmax(72px, 0.78fr));
    gap: 10px;
    align-items: center;
    padding: 12px 14px;
  }

  .market-matrix__head {
    border-bottom: 1px solid var(--hedge-cool-border);
    background: rgba(241, 246, 251, 0.92);
    color: #7b8ea0;
    font-size: 12px;
    font-weight: 700;
  }

  .market-matrix__row {
    border-bottom: 1px solid rgba(201, 213, 226, 0.52);
  }

  .market-matrix__row:last-child {
    border-bottom: 0;
  }

  .market-matrix__asset {
    display: grid;
    gap: 2px;
  }

  .market-matrix__asset strong,
  .market-matrix__close {
    color: var(--hedge-cool-text);
    font-size: 14px;
  }

  .market-matrix__asset span {
    color: var(--hedge-cool-muted);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .market-matrix__spark {
    height: 28px;
  }

  .market-matrix__spark svg {
    width: 100%;
    height: 100%;
  }

  .market-matrix__spark path {
    fill: none;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .market-matrix__spark .is-positive-line {
    stroke: #cc4b37;
  }

  .market-matrix__spark .is-negative-line {
    stroke: #5b93d3;
  }

  .market-matrix__cell {
    display: inline-flex;
    justify-content: center;
    align-items: center;
    min-height: 32px;
    border: 1px solid transparent;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
  }

  .market-matrix__cell.is-positive-cell {
    border-color: rgba(204, 75, 55, 0.14);
    background: rgba(204, 75, 55, 0.1);
    color: #c74432;
  }

  .market-matrix__cell.is-negative-cell {
    border-color: rgba(91, 147, 211, 0.14);
    background: rgba(91, 147, 211, 0.12);
    color: #3777bf;
  }

  .snapshot-table {
    padding: 0 18px 18px;
  }

  .snapshot-table__shell {
    overflow-x: auto;
    border: 1px solid var(--hedge-cool-border);
    border-radius: 16px;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 248, 252, 0.96)),
      #fff;
  }

  .snapshot-table__table {
    width: 100%;
    min-width: 1360px;
    border-collapse: collapse;
    color: var(--hedge-cool-text);
  }

  .snapshot-table__table th,
  .snapshot-table__table td {
    padding: 12px 14px;
    border-bottom: 1px solid rgba(201, 213, 226, 0.52);
    vertical-align: middle;
    white-space: nowrap;
  }

  .snapshot-table__table thead th {
    background: rgba(241, 246, 251, 0.92);
    color: #7b8ea0;
    font-size: 12px;
    font-weight: 700;
  }

  .snapshot-table__group-row td {
    background: rgba(241, 246, 251, 0.78);
    border-top: 1px solid rgba(201, 213, 226, 0.58);
    border-bottom-color: rgba(201, 213, 226, 0.58);
  }

  .snapshot-table__group-title {
    color: var(--hedge-cool-text);
    font-size: 14px;
    font-weight: 800;
  }

  .snapshot-table__name-wrap {
    display: grid;
    gap: 2px;
  }

  .snapshot-table__name-wrap strong {
    color: var(--hedge-cool-text);
    font-size: 14px;
  }

  .snapshot-table__name-wrap span {
    color: var(--hedge-cool-muted);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .snapshot-table__sparkline {
    width: 96px;
    height: 24px;
  }

  .snapshot-table__sparkline polyline {
    fill: none;
    stroke-width: 2.2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .snapshot-table__sparkline polyline.is-positive-line {
    stroke: #cc4b37;
  }

  .snapshot-table__sparkline polyline.is-negative-line {
    stroke: #5b93d3;
  }

  .snapshot-table__chip {
    display: inline-flex;
    min-width: 64px;
    justify-content: center;
    align-items: center;
    min-height: 32px;
    padding: 0 10px;
    border: 1px solid transparent;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 700;
  }

  .snapshot-table__chip.is-positive-chip {
    border-color: rgba(204, 75, 55, 0.14);
    background: rgba(204, 75, 55, 0.1);
    color: #c74432;
  }

  .snapshot-table__chip.is-negative-chip {
    border-color: rgba(91, 147, 211, 0.14);
    background: rgba(91, 147, 211, 0.12);
    color: #3777bf;
  }

  .snapshot-table__high-cell-td {
    padding-right: 12px;
    padding-left: 12px;
  }

  .snapshot-table__high-cell {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    min-width: 136px;
  }

  .snapshot-table__high-track {
    min-width: 0;
    flex: 1;
    width: 100%;
    height: 4px;
    border-radius: 999px;
    background: rgba(148, 163, 184, 0.18);
    overflow: hidden;
  }

  .snapshot-table__high-cell span {
    flex: 0 0 52px;
    width: 52px;
    text-align: right;
  }

  .snapshot-table__high-track i {
    display: block;
    height: 100%;
    border-radius: 999px;
  }

  .snapshot-table__high-track i.is-positive-line {
    background: #cc4b37;
  }

  .snapshot-table__high-track i.is-negative-line {
    background: #5b93d3;
  }

  .is-positive-text {
    color: #c74432;
  }

  .is-negative-text {
    color: #3777bf;
  }

  .hedge-board {
    --hedge-cool-border: rgba(201, 213, 226, 0.72);
    --hedge-cool-border-strong: rgba(175, 190, 207, 0.82);
    --hedge-cool-surface: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 248, 252, 0.96));
    --hedge-cool-surface-soft: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 251, 253, 0.96));
    --hedge-cool-pill: rgba(243, 247, 250, 0.94);
    --hedge-cool-shadow: 0 18px 45px rgba(15, 23, 42, 0.05);
    --hedge-cool-text: #18313c;
    --hedge-cool-muted: #6d8293;
    --hedge-cool-accent: #35586e;
  }

  .hedge-board__tab {
    border-color: var(--hedge-cool-border);
    background: var(--hedge-cool-pill);
    color: var(--hedge-cool-muted);
  }

  .hedge-board__tab.is-active {
    border-color: rgba(79, 114, 140, 0.4);
    background: linear-gradient(135deg, #183844, #35586e);
    color: #fff;
    box-shadow: 0 14px 30px rgba(24, 56, 68, 0.16);
  }

  .strategy-sidebar,
  .platform-topbar,
  .hero-panel,
  .strategy-strip__card,
  .module-subnav,
  .formula-strip,
  .source-strip,
  .chart-section,
  .widget-card {
    border-color: var(--hedge-cool-border);
    background: var(--hedge-cool-surface), #fff;
    box-shadow: var(--hedge-cool-shadow);
  }

  .strategy-sidebar__brand p,
  .platform-topbar__title p,
  .eyebrow {
    color: var(--hedge-cool-muted);
  }

  .strategy-sidebar__brand h1,
  .platform-topbar__title h2,
  .hero-panel__copy h2,
  .module-heading h3,
  .chart-section__heading h4,
  .widget-card__header h5,
  .strategy-sidebar__link strong,
  .strategy-strip__card strong,
  .formula-strip strong {
    color: var(--hedge-cool-text);
  }

  .strategy-sidebar__brand span,
  .strategy-sidebar__intro p,
  .module-heading__lead,
  .module-heading__summary p,
  .chart-section__heading p,
  .widget-card__header p,
  .widget-card__footer,
  .chart-caption,
  .platform-topbar__title span,
  .formula-strip p {
    color: var(--hedge-cool-muted);
  }

  .strategy-sidebar__link,
  .module-subnav button,
  .metric-strip article,
  .module-heading__summary,
  .chart-shell,
  .widget-card,
  .chart-section--gold .widget-card,
  .chart-section--gold {
    border-color: var(--hedge-cool-border);
    background: var(--hedge-cool-surface-soft), #fff;
    box-shadow: 0 14px 32px rgba(15, 23, 42, 0.04);
  }

  .strategy-sidebar__link span,
  .strategy-strip__card span,
  .formula-strip span,
  .metric-strip span {
    color: var(--hedge-cool-muted);
  }

  .strategy-sidebar__link small,
  .strategy-strip__card p {
    color: var(--hedge-cool-muted);
  }

  .strategy-sidebar__link:hover,
  .strategy-sidebar__link.is-active,
  .strategy-strip__card:hover,
  .strategy-strip__card.is-active {
    border-color: rgba(116, 146, 170, 0.42);
    background: linear-gradient(135deg, rgba(237, 244, 249, 0.96), rgba(255, 255, 255, 0.98));
  }

  .module-heading__tags span,
  .source-strip a,
  .platform-topbar__meta span {
    background: var(--hedge-cool-pill);
    color: var(--hedge-cool-muted);
  }

  .module-subnav button {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(245, 249, 252, 0.96));
  }

  .formula-strip {
    background: linear-gradient(135deg, rgba(236, 243, 248, 0.94), rgba(255, 255, 255, 0.98));
  }

  .chart-section--gold .chart-section__heading .eyebrow {
    color: var(--hedge-cool-accent);
  }

  .chart-section--gold .widget-card__header p {
    color: var(--hedge-cool-muted);
  }

  @media (max-width: 1280px) {
    .terminal-page {
      grid-template-columns: 1fr;
    }

    .strategy-sidebar {
      position: static;
    }

    .widget-grid--three {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .market-matrix__head,
    .market-matrix__row {
      grid-template-columns: minmax(128px, 1.2fr) 88px 72px repeat(5, minmax(66px, 0.8fr));
      gap: 8px;
      padding: 12px;
    }
  }

  @media (max-width: 960px) {
    .platform-topbar,
    .hero-panel,
    .module-heading,
    .formula-strip,
    .chart-section__heading {
      grid-template-columns: 1fr;
      flex-direction: column;
    }

    .widget-grid--two,
    .widget-grid--three {
      grid-template-columns: 1fr;
    }

    :deep(.ytd-module__metrics),
    :deep(.ytd-module__table-head),
    :deep(.ytd-module__table-row) {
      grid-template-columns: 1fr;
    }

    .etf-weekly-panel__toolbar,
    .etf-weekly-panel__actions {
      flex-direction: column;
      align-items: stretch;
    }

    .market-matrix {
      overflow-x: auto;
    }

    .market-matrix__table {
      min-width: 760px;
    }

    .snapshot-table {
      padding-inline: 0;
    }

    .snapshot-table__shell {
      border-radius: 0;
      border-left: none;
      border-right: none;
    }
  }

  @media (max-width: 768px) {
    .hedge-board__tabs {
      gap: 8px;
    }

    .platform-topbar,
    .hero-panel,
    .module-subnav,
    .formula-strip,
    .source-strip,
    .chart-section {
      padding: 18px;
      border-radius: 20px;
    }

    .strategy-sidebar {
      padding: 16px;
      border-radius: 20px;
    }

    .platform-topbar__title h2,
    .hero-panel__copy h2,
    .module-heading h3,
    .chart-section__heading h4 {
      font-size: 24px;
    }

    .widget-card__header,
    .widget-card__footer,
    .widget-frame,
    .local-widget-stack,
    .local-empty {
      padding-left: 16px;
      padding-right: 16px;
    }
  }
</style>
