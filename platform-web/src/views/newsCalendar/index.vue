<template>
  <PageWrapper :title="pageTitle">
    <main class="news-page">
      <div class="news-layout">
        <aside class="section-sidebar" aria-label="新闻日历与理财导航">
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

        <section class="section-content">
          <section v-if="section === 'macro'" class="panel-card calendar-panel">
            <header class="section-head">
              <div>
                <span>MACRO CALENDAR</span>
                <h2>宏观日历</h2>
              </div>
            </header>
            <TradingViewEconomicCalendarPanel />
          </section>

          <section v-else-if="section === 'news'" class="panel-card">
            <header class="section-head">
              <div>
                <span>NEWS DIGEST</span>
                <h2>新闻整理</h2>
              </div>
            </header>

            <nav class="news-asset-tabs" aria-label="新闻资产分类">
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
            </nav>

            <section v-if="activeNewsSection" class="digest-shell">
              <article class="feature-card">
                <div class="eyebrow">{{ activeNewsSection.eyebrow }}</div>
                <h3>{{ activeNewsSection.items[0].title }}</h3>
                <p>{{ activeNewsSection.items[0].summary }}</p>
                <div class="impact-row">
                  <span>{{ activeNewsSection.items[0].publishedAt }}</span>
                  <span>{{ activeNewsSection.items[0].source }}</span>
                  <span>重要度 P{{ activeNewsSection.items[0].importance }}</span>
                  <em :class="newsBiasClass(activeNewsSection.items[0].bias)">
                    {{ newsBiasLabel(activeNewsSection.items[0].bias) }}
                  </em>
                </div>
                <p class="section-description">{{ activeNewsSection.description }}</p>
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
                  <div class="impact-row">
                    <span>{{ item.publishedAt }}</span>
                    <span>{{ item.source }}</span>
                    <span>P{{ item.importance }}</span>
                  </div>
                </article>
              </div>
            </section>
          </section>

          <section v-else class="wealth-page">
            <header class="wealth-header">
              <div>
                <span>WEALTH INFORMATION</span>
                <h2>理财信息</h2>
              </div>
              <div class="wealth-actions">
                <button type="button" class="wealth-reference-button" @click="openEmbeddedUrl">
                  打开参考页面
                </button>
              </div>
            </header>

            <div class="wealth-toolbar">
              <label>
                <span>平台</span>
                <select v-model="wealthFilters.exchange">
                  <option value="all">全部平台</option>
                  <option v-for="item in exchangeOptions" :key="item.value" :value="item.value">
                    {{ item.label }}
                  </option>
                </select>
              </label>
              <label>
                <span>派息</span>
                <select v-model="wealthFilters.frequency">
                  <option value="all">不限派息</option>
                  <option value="daily">每日派息</option>
                  <option value="fixed">固定期限</option>
                  <option value="floating">浮动利率</option>
                </select>
              </label>
              <label>
                <span>期限</span>
                <select v-model="wealthFilters.lock">
                  <option value="all">不限期限</option>
                  <option value="short">7 天以内</option>
                  <option value="mid">30 天以内</option>
                  <option value="long">长期</option>
                </select>
              </label>
              <label class="wealth-search">
                <span>搜索</span>
                <input v-model="wealthFilters.keyword" placeholder="搜索平台、币种或活动" />
              </label>
            </div>

            <div class="wealth-table-head">
              <span>活动</span>
              <span>平台 / 币种</span>
              <button type="button" @click="toggleYieldSort">
                收益率 {{ wealthSortOrder === 'desc' ? '↓' : '↑' }}
              </button>
              <span>期限 / 锁仓</span>
              <span>到期时间</span>
              <span>活动说明</span>
            </div>

            <div v-if="!filteredWealthCampaigns.length" class="wealth-empty">暂无匹配活动</div>
            <div v-else class="wealth-list">
              <article v-for="item in filteredWealthCampaigns" :key="item.id" class="wealth-row">
                <div class="wealth-campaign">
                  <strong>{{ item.name }}</strong>
                  <div class="wealth-tags">
                    <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
                  </div>
                </div>
                <div>
                  <strong>{{ item.platform }}</strong>
                  <p>{{ item.coin }}</p>
                </div>
                <div class="wealth-yield">
                  <strong>{{ item.apy }}</strong>
                  <p>{{ item.apyNote }}</p>
                </div>
                <div>
                  <strong>{{ lockLabel(item.lock) }}</strong>
                  <p>{{ frequencyLabel(item.frequency) }}</p>
                </div>
                <div class="wealth-expiry">
                  <strong :class="{ 'is-urgent': item.daysLeft <= 1 }">{{
                    item.expiryLabel
                  }}</strong>
                  <p>{{ item.expiryNote }}</p>
                </div>
                <p class="wealth-description">{{ item.description }}</p>
              </article>
            </div>
          </section>
        </section>
      </div>
    </main>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, reactive, ref, type Component } from 'vue';
  import { RouterLink, useRoute } from 'vue-router';
  import { CalendarOutlined, FileSearchOutlined, FundOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import {
    newsDigestSections,
    wealthCampaigns,
    type NewsAssetKey,
    type NewsDigestItem,
    type WealthFrequency,
    type WealthLock,
  } from '@/data/sample/news';
  import TradingViewEconomicCalendarPanel from '@/views/hedgeBoard/tradingTools/components/TradingViewEconomicCalendarPanel.vue';

  type NewsSection = 'macro' | 'news' | 'wealth';
  type SortOrder = 'desc' | 'asc';

  const route = useRoute();
  const activeNewsAsset = ref<NewsAssetKey>('macro');
  const wealthSortOrder = ref<SortOrder>('desc');
  const wealthFilters = reactive({
    exchange: 'all',
    frequency: 'all',
    lock: 'all',
    keyword: '',
  });

  const section = computed<NewsSection>(() => {
    if (route.path.endsWith('/news')) return 'news';
    if (route.path.endsWith('/wealth')) return 'wealth';
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
  const exchangeOptions = [
    { value: 'gate', label: 'Gate' },
    { value: 'aave', label: 'Aave' },
    { value: 'binance', label: 'Binance' },
    { value: 'bitget', label: 'Bitget' },
    { value: 'okx', label: 'OKX' },
    { value: 'bybit', label: 'Bybit' },
  ];
  const activeNewsSection = computed(
    () =>
      newsDigestSections.find((item) => item.key === activeNewsAsset.value) ??
      newsDigestSections[0],
  );
  const filteredWealthCampaigns = computed(() => {
    const keyword = wealthFilters.keyword.trim().toLowerCase();
    const rows = wealthCampaigns.filter((item) => {
      if (wealthFilters.exchange !== 'all' && item.exchange !== wealthFilters.exchange)
        return false;
      if (wealthFilters.frequency !== 'all' && item.frequency !== wealthFilters.frequency)
        return false;
      if (wealthFilters.lock !== 'all' && item.lock !== wealthFilters.lock) return false;
      if (!keyword) return true;
      return [item.name, item.platform, item.coin].join(' ').toLowerCase().includes(keyword);
    });
    return rows
      .slice()
      .sort((left, right) =>
        wealthSortOrder.value === 'desc'
          ? right.apyValue - left.apyValue
          : left.apyValue - right.apyValue,
      );
  });

  function toggleYieldSort() {
    wealthSortOrder.value = wealthSortOrder.value === 'desc' ? 'asc' : 'desc';
  }
  function openEmbeddedUrl() {
    const url = String(route.meta.embeddedUrl || 'https://app.barker.money/campaigns');
    window.open(url, '_blank', 'noopener,noreferrer');
  }
  function newsBiasClass(bias: NewsDigestItem['bias']) {
    return { bull: 'is-bull', neutral: 'is-flat', bear: 'is-bear' }[bias];
  }
  function newsBiasLabel(bias: NewsDigestItem['bias']) {
    return { bull: '偏多', neutral: '中性', bear: '偏空' }[bias];
  }
  function frequencyLabel(value: WealthFrequency) {
    return { daily: '每日派息', fixed: '固定期限', floating: '浮动利率' }[value];
  }
  function lockLabel(value: WealthLock) {
    return { short: '7 天以内', mid: '30 天以内', long: '长期' }[value];
  }
</script>

<style scoped lang="less">
  .news-page {
    padding: 16px;
  }
  .news-layout {
    display: grid;
    grid-template-columns: 180px minmax(0, 1fr);
    gap: 16px;
    min-width: 0;
  }
  .section-sidebar {
    position: sticky;
    top: 12px;
    display: grid;
    align-self: start;
    gap: 7px;
    padding: 8px;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    background: #fff;
  }
  .section-sidebar a {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 10px 12px;
    border-radius: 7px;
    color: #526173;
  }
  .section-sidebar a.is-active {
    background: #eaf4ff;
    color: #1769aa;
    font-weight: 700;
  }
  .section-content {
    min-width: 0;
  }
  .panel-card,
  .wealth-page {
    display: grid;
    gap: 16px;
    padding: 18px;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #fff;
  }
  .section-head,
  .wealth-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 14px;
  }
  .section-head span,
  .wealth-header span {
    color: #6c7d90;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.14em;
  }
  .wealth-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .wealth-reference-button {
    height: 34px;
    padding: 0 14px;
    border: 1px solid #d8e2ee;
    border-radius: 8px;
    background: #fff;
    color: #294a67;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
  }
  .wealth-reference-button:hover {
    border-color: #aac7df;
    background: #edf6ff;
  }
  h2 {
    margin: 4px 0 0;
    color: #172033;
    font-size: 20px;
  }
  .news-asset-tabs {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 8px;
  }
  .news-asset-tabs button {
    display: grid;
    gap: 4px;
    min-width: 0;
    padding: 10px;
    border: 1px solid #e3e8ef;
    border-radius: 8px;
    background: #fff;
    color: #647084;
    text-align: left;
  }
  .news-asset-tabs button.is-active {
    border-color: #aac7df;
    background: #edf6ff;
    color: #294a67;
  }
  .digest-shell {
    display: grid;
    grid-template-columns: minmax(280px, 0.9fr) minmax(0, 1.35fr);
    gap: 12px;
  }
  .feature-card,
  .digest-card {
    padding: 16px;
    border: 1px solid #e3e8ef;
    border-radius: 10px;
    background: #fafbfd;
  }
  .eyebrow {
    color: #6c7d90;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }
  .feature-card h3 {
    margin: 10px 0;
    color: #172033;
    font-size: 22px;
  }
  .feature-card p,
  .digest-card p,
  .wealth-description {
    margin: 8px 0 0;
    color: #667085;
    line-height: 1.65;
  }
  .section-description {
    padding-top: 10px;
    border-top: 1px solid #e4e9f0;
  }
  .digest-grid {
    display: grid;
    gap: 10px;
  }
  .digest-card__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
  }
  .digest-card h4 {
    margin: 0;
    color: #172033;
    font-size: 16px;
  }
  .impact-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    color: #8490a0;
    font-size: 11px;
  }
  .impact-row em,
  .digest-card__head em {
    font-style: normal;
    font-weight: 800;
  }
  .is-bull {
    color: #087a55;
  }
  .is-flat {
    color: #667085;
  }
  .is-bear {
    color: #b42318;
  }
  .wealth-toolbar {
    display: grid;
    grid-template-columns: repeat(3, minmax(140px, 180px)) minmax(220px, 1fr);
    gap: 10px;
  }
  .wealth-toolbar label {
    display: grid;
    gap: 6px;
  }
  .wealth-toolbar span {
    color: #667085;
    font-size: 12px;
    font-weight: 700;
  }
  .wealth-toolbar select,
  .wealth-toolbar input {
    height: 36px;
    min-width: 0;
    padding: 0 10px;
    border: 1px solid #dce3eb;
    border-radius: 8px;
    background: #fff;
  }
  .wealth-table-head,
  .wealth-row {
    display: grid;
    grid-template-columns: 1.1fr 0.9fr 0.8fr 0.7fr 0.8fr 1.15fr;
    align-items: start;
    gap: 12px;
  }
  .wealth-table-head {
    padding: 0 12px;
    color: #778396;
    font-size: 12px;
    font-weight: 700;
  }
  .wealth-table-head button {
    border: 0;
    background: transparent;
    color: inherit;
    text-align: left;
  }
  .wealth-list {
    display: grid;
    gap: 8px;
  }
  .wealth-empty {
    padding: 28px 16px;
    border: 1px dashed #d8e0ea;
    border-radius: 10px;
    background: #fafbfd;
    color: #667085;
    text-align: center;
  }
  .wealth-row {
    padding: 14px;
    border: 1px solid #e5eaf0;
    border-radius: 10px;
    background: #fafbfd;
  }
  .wealth-row strong {
    color: #172033;
  }
  .wealth-row p {
    margin: 4px 0 0;
    color: #7b8798;
    font-size: 12px;
  }
  .wealth-yield strong {
    color: #225a96;
    font-size: 20px;
  }
  .wealth-expiry .is-urgent {
    color: #b42318;
  }
  .wealth-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 8px;
  }
  .wealth-tags span {
    padding: 4px 7px;
    border-radius: 999px;
    background: #eef3f8;
    color: #526b82;
    font-size: 11px;
  }
  @media (max-width: 1200px) {
    .news-asset-tabs {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
    .wealth-table-head,
    .wealth-row {
      grid-template-columns: 1fr 0.8fr 0.75fr;
    }
  }
  @media (max-width: 900px) {
    .news-layout,
    .digest-shell,
    .wealth-toolbar {
      grid-template-columns: 1fr;
    }
    .section-sidebar {
      position: static;
      display: flex;
      overflow-x: auto;
    }
    .section-sidebar a {
      flex: 0 0 auto;
    }
    .wealth-table-head {
      display: none;
    }
  }
  @media (max-width: 620px) {
    .news-asset-tabs {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .wealth-row {
      grid-template-columns: 1fr;
    }
  }
</style>
