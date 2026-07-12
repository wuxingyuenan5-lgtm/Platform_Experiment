<template>
  <PageWrapper :title="pageTitle">
    <div class="news-layout">
      <aside class="section-sidebar">
        <RouterLink
          v-for="item in sectionTabs"
          :key="item.path"
          :to="item.path"
          :class="{ 'is-active': section === item.key }"
        >
          <component :is="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </aside>

      <div class="section-content">
        <template v-if="section === 'macro'">
          <TradingViewEconomicCalendarPanel />
        </template>

        <template v-else-if="section === 'news'">
          <section class="panel-card">
            <header class="section-head">
              <div>
                <div class="eyebrow">NEWS DIGEST</div>
                <h2>新闻整理</h2>
              </div>
            </header>

            <div class="news-asset-tabs">
              <button
                v-for="asset in newsDigestSections"
                :key="asset.key"
                type="button"
                :class="{ 'is-active': activeNewsAsset === asset.key }"
                @click="activeNewsAsset = asset.key"
              >
                <span>{{ asset.index }}</span>
                <strong>{{ asset.label }}</strong>
              </button>
            </div>

            <section v-if="activeNewsSection" class="digest-shell">
              <article class="feature-card">
                <div class="eyebrow">{{ activeNewsSection.eyebrow }}</div>
                <h3>{{ activeNewsSection.items[0].title }}</h3>
                <p>{{ activeNewsSection.items[0].summary }}</p>
                <div class="meta-row">
                  <span>{{ activeNewsSection.items[0].publishedAt }}</span>
                  <span>{{ activeNewsSection.items[0].source }}</span>
                  <span>重要度 P{{ activeNewsSection.items[0].importance }}</span>
                </div>
              </article>

              <div class="digest-grid">
                <article
                  v-for="item in activeNewsSection.items.slice(1)"
                  :key="item.id"
                  class="digest-card"
                >
                  <div class="digest-card__head">
                    <h4>{{ item.title }}</h4>
                    <em :class="newsBiasClass(item.bias)">{{ newsBiasLabel(item.bias) }}</em>
                  </div>
                  <p>{{ item.summary }}</p>
                  <div class="meta-row">
                    <span>{{ item.publishedAt }}</span>
                    <span>{{ item.source }}</span>
                  </div>
                </article>
              </div>
            </section>
          </section>
        </template>

        <template v-else>
          <section class="wealth-page">
            <header class="wealth-header">
              <div>
                <h2>理财信息</h2>
              </div>

              <div class="wealth-actions">
                <Button type="default" @click="refreshWealth">刷新数据</Button>
                <Button type="default" @click="openEmbeddedUrl">打开参考页面</Button>
              </div>
            </header>

            <div class="wealth-toolbar">
              <Select v-model:value="wealthFilters.exchange" class="wealth-select" :options="exchangeOptions" />
              <Select v-model:value="wealthFilters.frequency" class="wealth-select" :options="frequencyOptions" />
              <Select v-model:value="wealthFilters.lock" class="wealth-select" :options="lockOptions" />
              <Input
                v-model:value="wealthFilters.keyword"
                class="wealth-search"
                allow-clear
                placeholder="按稳定币币种 CEX 搜索..."
              >
                <template #prefix>
                  <SearchOutlined />
                </template>
              </Input>
            </div>

            <div class="wealth-table-head">
              <span>活动</span>
              <button type="button" class="yield-sort" @click="toggleYieldSort">
                实时年利率
                <DownOutlined :class="{ 'is-desc': wealthSortOrder === 'desc' }" />
              </button>
              <span>标签</span>
              <span>到期时间</span>
            </div>

            <div class="wealth-list">
              <article v-for="item in filteredWealthCampaigns" :key="item.id" class="wealth-row">
                <div class="wealth-campaign">
                  <div class="wealth-icon" :style="{ background: item.iconBg, color: item.iconColor }">
                    <component :is="item.icon" />
                  </div>
                  <div class="wealth-campaign__meta">
                    <div class="wealth-campaign__title">
                      <strong>{{ item.name }}</strong>
                      <span v-if="item.hot" class="hot-tag">热门</span>
                    </div>
                    <p>{{ item.platform }}</p>
                  </div>
                </div>

                <div class="wealth-yield">
                  <strong>{{ item.apy }}</strong>
                  <p>{{ item.apyNote }}</p>
                </div>

                <div class="wealth-tags">
                  <span v-for="tag in item.tags" :key="tag.text" :class="['wealth-chip', tag.tone]">
                    {{ tag.text }}
                  </span>
                </div>

                <div class="wealth-expiry">
                  <strong :class="{ 'is-urgent': item.daysLeft <= 1 }">
                    {{ item.expiryLabel }}
                  </strong>
                  <p>{{ item.expiryNote }}</p>
                  <div class="wealth-progress">
                    <div class="wealth-progress__value" :style="{ width: `${item.progress}%` }"></div>
                  </div>
                </div>

                <div class="wealth-actions-inline">
                  <button type="button" @click="toggleFavorite(item.id)">
                    <StarOutlined :class="{ 'is-favorite': favorites.has(item.id) }" />
                  </button>
                  <button type="button" @click="openEmbeddedUrl">
                    <AppstoreOutlined />
                  </button>
                </div>
              </article>
            </div>
          </section>
        </template>
      </div>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, reactive, ref } from 'vue';
  import type { Component } from 'vue';
  import { RouterLink, useRoute } from 'vue-router';
  import { Button, Input, Select } from 'ant-design-vue';
  import {
    AppstoreOutlined,
    BankOutlined,
    CalendarOutlined,
    DownOutlined,
    FileSearchOutlined,
    FundOutlined,
    SearchOutlined,
    StarOutlined,
  } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import TradingViewEconomicCalendarPanel from '@/views/hedgeBoard/tradingTools/components/TradingViewEconomicCalendarPanel.vue';
  import { newsDigestSections, type NewsAssetKey } from './newsDigestData';

  type NewsSection = 'macro' | 'news' | 'wealth';
  type SortOrder = 'desc' | 'asc';

  interface WealthTag {
    text: string;
    tone: 'neutral' | 'green' | 'blue' | 'pink' | 'purple' | 'orange';
  }

  interface WealthCampaign {
    id: string;
    name: string;
    platform: string;
    exchange: string;
    frequency: string;
    lock: string;
    apy: string;
    apyValue: number;
    apyNote: string;
    tags: WealthTag[];
    expiryLabel: string;
    expiryNote: string;
    daysLeft: number;
    progress: number;
    icon: Component;
    iconBg: string;
    iconColor: string;
    hot?: boolean;
  }

  const route = useRoute();
  const activeNewsAsset = ref<NewsAssetKey>('macro');
  const wealthSortOrder = ref<SortOrder>('desc');
  const favorites = ref(new Set<string>());

  const wealthFilters = reactive({
    exchange: 'all',
    frequency: 'all',
    lock: 'all',
    keyword: '',
  });

  const section = computed<NewsSection>(() => {
    const value = route.meta.newsSection;
    if (value === 'news' || value === 'wealth') return value;
    return 'macro';
  });

  const pageTitle = computed(() => '新闻日历与理财');

  const sectionTabs: Array<{ key: NewsSection; label: string; path: string; icon: Component }> = [
    { key: 'macro', label: '宏观日历', path: '/news-calendar/macro', icon: CalendarOutlined },
    { key: 'news', label: '新闻整理', path: '/news-calendar/news', icon: FileSearchOutlined },
    { key: 'wealth', label: '理财信息', path: '/news-calendar/wealth', icon: FundOutlined },
  ];

  const wealthEmbeddedUrl = computed(() =>
    typeof route.meta.embeddedUrl === 'string'
      ? route.meta.embeddedUrl
      : 'https://app.barker.money/campaigns',
  );

  const exchangeOptions = [
    { value: 'all', label: '全部交易所' },
    { value: 'gate', label: 'Gate' },
    { value: 'aave', label: 'Aave' },
    { value: 'binance', label: 'Binance' },
    { value: 'bitget', label: 'Bitget' },
    { value: 'okx', label: 'OKX' },
    { value: 'bybit', label: 'Bybit' },
  ];

  const frequencyOptions = [
    { value: 'all', label: '不限频度' },
    { value: 'daily', label: '每日派息' },
    { value: 'fixed', label: '锁仓固定' },
    { value: 'floating', label: '利率浮动' },
  ];

  const lockOptions = [
    { value: 'all', label: '不限锁定日期' },
    { value: 'short', label: '7天以内' },
    { value: 'mid', label: '30天以内' },
    { value: 'long', label: '长期' },
  ];

  const wealthCampaigns = ref<WealthCampaign[]>([
    {
      id: 'usd1-gate',
      name: 'USD1',
      platform: 'Gate 主站 → 活动',
      exchange: 'gate',
      frequency: 'daily',
      lock: 'long',
      apy: '15.00%',
      apyValue: 15,
      apyNote: '$10,000 本金到期总收益 $123.29（预期一个月）',
      tags: [
        { text: '无限额', tone: 'neutral' },
        { text: '每天派息', tone: 'green' },
        { text: '持有即可，利息发 USD1', tone: 'blue' },
      ],
      expiryLabel: '长期',
      expiryNote: '随时关注活动规则',
      daysLeft: 99,
      progress: 74,
      icon: BankOutlined,
      iconBg: '#172033',
      iconColor: '#5d82ff',
      hot: true,
    },
    {
      id: 'gho-aave',
      name: 'GHO',
      platform: 'Gate 主站 → 链上',
      exchange: 'aave',
      frequency: 'daily',
      lock: 'mid',
      apy: '13.36%',
      apyValue: 13.36,
      apyNote: '$5,000 本金到期总收益 $58.56（预期一个月）',
      tags: [
        { text: '额度 $5,000', tone: 'neutral' },
        { text: '每天 08:00 派息', tone: 'green' },
        { text: '账回 2 天', tone: 'pink' },
      ],
      expiryLabel: '长期',
      expiryNote: '额度 $5,000',
      daysLeft: 99,
      progress: 64,
      icon: AppstoreOutlined,
      iconBg: '#1a2132',
      iconColor: '#4c6fff',
    },
    {
      id: 'lorenzo-binance',
      name: 'Lorenzo USD1',
      platform: 'Binance 主站 → 链上',
      exchange: 'binance',
      frequency: 'fixed',
      lock: 'short',
      apy: '13.05%',
      apyValue: 13.05,
      apyNote: '$10,000 本金到期总收益 $3.57',
      tags: [
        { text: '无限额', tone: 'neutral' },
        { text: '派息 BANK 代币', tone: 'purple' },
      ],
      expiryLabel: '还剩 1 天',
      expiryNote: '截止 2026-06-19 07:59',
      daysLeft: 1,
      progress: 18,
      icon: BankOutlined,
      iconBg: '#1e232f',
      iconColor: '#ffcd3c',
    },
    {
      id: 'usdgo-bitget',
      name: 'USDGO',
      platform: 'Bitget 主站 → 活期赚币',
      exchange: 'bitget',
      frequency: 'floating',
      lock: 'mid',
      apy: '12.00%',
      apyValue: 12,
      apyNote: '$10,000 本金到期总收益 $65.75',
      tags: [
        { text: '额度 $300,000', tone: 'neutral' },
        { text: '每小时派息', tone: 'green' },
        { text: '利率浮动', tone: 'blue' },
      ],
      expiryLabel: '还剩 20 天',
      expiryNote: '截止 2026-07-08 23:59',
      daysLeft: 20,
      progress: 36,
      icon: AppstoreOutlined,
      iconBg: '#2ad0da',
      iconColor: '#103247',
    },
    {
      id: 'pharos-okx',
      name: 'Pharos USDC',
      platform: 'OKX 主站 → 锁定',
      exchange: 'okx',
      frequency: 'fixed',
      lock: 'mid',
      apy: '11.49%',
      apyValue: 11.49,
      apyNote: '$10,000 本金到期总收益 $122.74',
      tags: [
        { text: '无限额', tone: 'neutral' },
        { text: '锁仓 91 天', tone: 'orange' },
        { text: '账回 7 天', tone: 'pink' },
      ],
      expiryLabel: '还剩 32 天',
      expiryNote: '截止 2026-07-20 19:00',
      daysLeft: 32,
      progress: 31,
      icon: FundOutlined,
      iconBg: '#1b1f28',
      iconColor: '#f5f7fb',
    },
    {
      id: 'usd1-bybit',
      name: 'USD1',
      platform: 'Bybit 主站 → 持仓赚币',
      exchange: 'bybit',
      frequency: 'daily',
      lock: 'mid',
      apy: '11.43%',
      apyValue: 11.43,
      apyNote: '$10,000 本金到期总收益 $93.93',
      tags: [
        { text: '无限额', tone: 'neutral' },
        { text: '派息 WLFI 代币', tone: 'purple' },
        { text: '每天约 14:00 派息', tone: 'green' },
      ],
      expiryLabel: '还剩 30 天',
      expiryNote: '截止 2026-07-18 08:00',
      daysLeft: 30,
      progress: 52,
      icon: BankOutlined,
      iconBg: '#202530',
      iconColor: '#ffffff',
    },
  ]);

  const filteredWealthCampaigns = computed(() => {
    const keyword = wealthFilters.keyword.trim().toLowerCase();

    const rows = wealthCampaigns.value.filter((item) => {
      if (wealthFilters.exchange !== 'all' && item.exchange !== wealthFilters.exchange) return false;
      if (wealthFilters.frequency !== 'all' && item.frequency !== wealthFilters.frequency) return false;

      if (wealthFilters.lock === 'short' && item.daysLeft > 7) return false;
      if (wealthFilters.lock === 'mid' && (item.daysLeft <= 7 || item.daysLeft > 30)) return false;
      if (wealthFilters.lock === 'long' && item.daysLeft <= 30) return false;

      if (!keyword) return true;
      return [item.name, item.platform].join(' ').toLowerCase().includes(keyword);
    });

    return [...rows].sort((a, b) =>
      wealthSortOrder.value === 'desc' ? b.apyValue - a.apyValue : a.apyValue - b.apyValue,
    );
  });

  const activeNewsSection = computed(
    () =>
      newsDigestSections.find((item) => item.key === activeNewsAsset.value) ??
      newsDigestSections[0],
  );

  function toggleYieldSort() {
    wealthSortOrder.value = wealthSortOrder.value === 'desc' ? 'asc' : 'desc';
  }

  function refreshWealth() {
    wealthCampaigns.value = [...wealthCampaigns.value];
  }

  function openEmbeddedUrl() {
    window.open(wealthEmbeddedUrl.value, '_blank', 'noopener,noreferrer');
  }

  function toggleFavorite(id: string) {
    const next = new Set(favorites.value);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    favorites.value = next;
  }

  function newsBiasClass(bias: string) {
    if (bias === 'bull') return 'is-bull';
    if (bias === 'bear') return 'is-bear';
    return 'is-flat';
  }

  function newsBiasLabel(bias: string) {
    if (bias === 'bull') return '偏多';
    if (bias === 'bear') return '偏空';
    return '中性';
  }
</script>

<style scoped>
  .news-layout {
    display: grid;
    grid-template-columns: 160px minmax(0, 1fr);
    gap: 22px;
    min-height: calc(100vh - 200px);
  }

  .section-sidebar {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px;
    border: 1px solid rgba(221, 229, 238, 0.96);
    border-radius: 24px;
    background: linear-gradient(180deg, #fbfcfe 0%, #f3f7fb 100%);
    box-shadow: 0 12px 36px rgba(148, 170, 196, 0.1);
    align-self: start;
    position: sticky;
    top: 12px;
  }

  .section-sidebar a {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 14px;
    border-radius: 16px;
    color: #627387;
    font-size: 14px;
    font-weight: 700;
    text-decoration: none;
    transition: all 0.2s ease;
  }

  .section-sidebar a.is-active,
  .section-sidebar a:hover {
    color: #1a4250;
    background: rgba(231, 239, 247, 0.92);
  }

  .section-content {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .panel-card {
    border: 1px solid rgba(221, 229, 238, 0.96);
    border-radius: 28px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(245, 248, 252, 0.96));
    box-shadow: 0 14px 40px rgba(150, 172, 196, 0.12);
    padding: 24px;
  }

  .section-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 18px;
  }

  .eyebrow,
  .wealth-eyebrow {
    margin-bottom: 8px;
    color: #7c9890;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.22em;
    text-transform: uppercase;
  }

  .section-head h2,
  .wealth-header h2 {
    margin: -2px 0 0;
    color: #1f2d3a;
    font-size: 30px;
    font-weight: 700;
  }

  .event-list {
    display: grid;
    gap: 14px;
  }

  .event-row {
    display: grid;
    grid-template-columns: 100px minmax(0, 1fr) 90px;
    gap: 18px;
    align-items: center;
    padding: 18px;
    border: 1px solid rgba(229, 235, 241, 0.92);
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.82);
  }

  .event-time {
    color: #1f2d3a;
    font-size: 20px;
    font-weight: 700;
  }

  .event-main strong,
  .feature-card h3,
  .digest-card h4 {
    color: #1f2d3a;
  }

  .event-main p,
  .feature-card p,
  .digest-card p,
  .wealth-header p {
    color: #6d7d8f;
    line-height: 1.8;
  }

  .event-tag {
    justify-self: end;
    padding: 8px 14px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 700;
  }

  .event-tag.high {
    color: #b34e4e;
    background: rgba(255, 233, 233, 0.92);
  }

  .event-tag.medium {
    color: #886439;
    background: rgba(255, 245, 226, 0.92);
  }

  .news-asset-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 18px;
  }

  .news-asset-tabs button {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    height: 40px;
    padding: 0 14px;
    border: 1px solid rgba(221, 229, 238, 0.96);
    border-radius: 999px;
    background: #fff;
    color: #637386;
    font-weight: 700;
    cursor: pointer;
  }

  .news-asset-tabs button.is-active {
    color: #1a4250;
    border-color: rgba(195, 207, 220, 0.96);
    background: rgba(237, 243, 249, 0.95);
  }

  .digest-shell {
    display: grid;
    gap: 18px;
  }

  .feature-card,
  .digest-card {
    border: 1px solid rgba(229, 235, 241, 0.92);
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.86);
    padding: 20px;
  }

  .digest-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .digest-card__head {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }

  .digest-card__head em {
    font-style: normal;
    font-size: 12px;
    font-weight: 700;
  }

  .digest-card__head .is-bull {
    color: #1f936a;
  }

  .digest-card__head .is-bear {
    color: #c95d5d;
  }

  .digest-card__head .is-flat {
    color: #76879a;
  }

  .meta-row {
    display: flex;
    flex-wrap: wrap;
    gap: 14px;
    color: #8c9aaa;
    font-size: 12px;
  }

  .wealth-page {
    min-height: calc(100vh - 190px);
    padding: 4px 2px 0;
  }

  .wealth-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    margin-bottom: 18px;
  }

  .wealth-header p {
    margin: 10px 0 0;
    max-width: 860px;
  }

  .wealth-source {
    display: block;
    margin-top: 12px;
    color: #6170ff;
    font-size: 14px;
    font-weight: 700;
  }

  .wealth-actions {
    display: flex;
    gap: 10px;
  }

  .wealth-toolbar {
    display: grid;
    grid-template-columns: 170px 170px 170px minmax(240px, 1fr);
    gap: 14px;
    justify-content: end;
    margin-bottom: 26px;
  }

  .wealth-select :deep(.ant-select-selector),
  .wealth-search :deep(.ant-input-affix-wrapper) {
    height: 48px !important;
    border-radius: 16px !important;
    border: 1px solid rgba(232, 235, 244, 0.96) !important;
    box-shadow: 0 12px 28px rgba(164, 178, 208, 0.08);
  }

  .wealth-table-head {
    display: grid;
    grid-template-columns: 1.35fr 0.84fr 1.16fr 0.68fr;
    align-items: center;
    gap: 20px;
    padding: 0 22px 12px;
    color: #8a95a7;
    font-size: 14px;
    font-weight: 700;
  }

  .yield-sort {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 0;
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }

  .yield-sort :deep(.anticon) {
    font-size: 11px;
    transition: transform 0.2s ease;
  }

  .yield-sort :deep(.is-desc) {
    transform: rotate(180deg);
  }

  .wealth-list {
    display: grid;
    gap: 14px;
  }

  .wealth-row {
    display: grid;
    grid-template-columns: 1.35fr 0.84fr 1.16fr 0.68fr 60px;
    align-items: center;
    gap: 20px;
    padding: 18px 22px;
    border: 1px solid rgba(235, 238, 246, 0.96);
    border-radius: 24px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 10px 30px rgba(176, 189, 220, 0.08);
  }

  .wealth-campaign {
    display: flex;
    align-items: center;
    gap: 18px;
  }

  .wealth-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
    border-radius: 18px;
    font-size: 28px;
    flex: 0 0 auto;
  }

  .wealth-campaign__title {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .wealth-campaign__title strong {
    color: #2a3345;
    font-size: 18px;
    font-weight: 700;
  }

  .wealth-campaign__meta p,
  .wealth-yield p,
  .wealth-expiry p {
    margin: 4px 0 0;
    color: #9aa2b2;
    font-size: 14px;
  }

  .hot-tag {
    display: inline-flex;
    align-items: center;
    height: 22px;
    padding: 0 8px;
    border-radius: 999px;
    background: rgba(255, 191, 113, 0.2);
    color: #ff8f1f;
    font-size: 12px;
    font-weight: 700;
  }

  .wealth-yield {
    text-align: center;
  }

  .wealth-yield strong {
    color: #6874ff;
    font-size: 26px;
    font-weight: 800;
  }

  .wealth-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .wealth-chip {
    display: inline-flex;
    align-items: center;
    height: 28px;
    padding: 0 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
  }

  .wealth-chip.neutral {
    background: #eff3f7;
    color: #7c8699;
  }

  .wealth-chip.green {
    background: #dff8ee;
    color: #2aa781;
  }

  .wealth-chip.blue {
    background: #e4f4ff;
    color: #4e99cf;
  }

  .wealth-chip.pink {
    background: #ffe4e9;
    color: #ff6d8c;
  }

  .wealth-chip.purple {
    background: #efe4ff;
    color: #8d63ff;
  }

  .wealth-chip.orange {
    background: #fff0d8;
    color: #f0a934;
  }

  .wealth-expiry {
    text-align: center;
  }

  .wealth-expiry strong {
    color: #2a3345;
    font-size: 18px;
    font-weight: 700;
  }

  .wealth-expiry strong.is-urgent {
    color: #ff4d5a;
  }

  .wealth-progress {
    width: 124px;
    height: 6px;
    margin: 10px auto 0;
    border-radius: 999px;
    background: #e8ebf5;
    overflow: hidden;
  }

  .wealth-progress__value {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #6b63ff, #7e72ff);
  }

  .wealth-actions-inline {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
  }

  .wealth-actions-inline button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: 0;
    background: transparent;
    color: #7d70ff;
    font-size: 18px;
    cursor: pointer;
  }

  .wealth-actions-inline :deep(.is-favorite) {
    color: #5d62ff;
  }

  @media (max-width: 1400px) {
    .wealth-toolbar {
      grid-template-columns: repeat(2, minmax(220px, 1fr));
    }

    .wealth-table-head,
    .wealth-row {
      grid-template-columns: 1.2fr 0.9fr 1fr 0.8fr;
    }

    .wealth-actions-inline {
      grid-column: 1 / -1;
      justify-content: flex-end;
    }
  }

  @media (max-width: 1200px) {
    .news-layout {
      grid-template-columns: 1fr;
    }

    .section-sidebar {
      position: static;
      flex-direction: row;
      flex-wrap: wrap;
    }

    .digest-grid {
      grid-template-columns: 1fr;
    }

    .wealth-header {
      flex-direction: column;
    }

    .wealth-table-head {
      display: none;
    }

    .wealth-row {
      grid-template-columns: 1fr;
      align-items: flex-start;
    }

    .wealth-yield,
    .wealth-expiry {
      text-align: left;
    }

    .wealth-progress {
      margin-left: 0;
    }
  }

  @media (max-width: 760px) {
    .event-row {
      grid-template-columns: 1fr;
    }

    .event-tag {
      justify-self: start;
    }

    .section-head,
    .wealth-actions {
      flex-direction: column;
    }

    .wealth-toolbar {
      grid-template-columns: 1fr;
    }
  }
</style>
