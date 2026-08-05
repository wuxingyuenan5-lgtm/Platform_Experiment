<template>
  <PageWrapper :title="pageTitle">
    <main class="news-page" data-testid="news-calendar-original-structure">
      <header class="page-identity">
        <div><span>NEWS · CALENDAR · WEALTH</span><h1>新闻日历与理财</h1></div>
        <b>{{ sectionLabel }}</b>
      </header>

      <div class="news-layout">
        <aside class="section-sidebar" aria-label="新闻日历与理财导航">
          <RouterLink v-for="item in sectionTabs" :key="item.path" :to="item.path" :class="{ 'is-active': section === item.key }">
            <component :is="item.icon" /><span>{{ item.label }}</span>
          </RouterLink>
        </aside>

        <section class="section-content">
          <template v-if="section === 'macro'">
            <RestoredProductDataBanner state="live" source="TradingView Economic Calendar" as-of="provider-defined" :actionable="false" message="宏观日历直接读取第三方公开 Widget；Platform 不缓存或改写事件数值。" />
            <TradingViewEconomicCalendarPanel />
          </template>

          <RestoredProductSurface v-else-if="section === 'news'" :state="newsSampleMeta.state" :source="newsSampleMeta.source" :as-of="newsSampleMeta.asOf" :actionable="newsSampleMeta.actionable" message="原新闻资产切换、重点卡片和摘要网格已恢复；全部内容为明确样例，不冒充实时新闻。">
            <section class="panel-card" data-testid="news-digest-original-structure">
              <header class="section-head"><div><span>NEWS DIGEST</span><h2>新闻整理</h2></div><em>Sample</em></header>
              <nav class="news-asset-tabs" aria-label="新闻资产分类">
                <button v-for="asset in newsDigestSections" :key="asset.key" type="button" :class="{ 'is-active': activeNewsAsset === asset.key }" @click="activeNewsAsset = asset.key">
                  <span>{{ asset.index }}</span><strong>{{ asset.label }}</strong>
                </button>
              </nav>
              <section v-if="activeNewsSection" class="digest-shell">
                <article class="feature-card">
                  <div class="eyebrow">{{ activeNewsSection.eyebrow }}</div>
                  <h3>{{ activeNewsSection.items[0].title }}</h3>
                  <p>{{ activeNewsSection.items[0].summary }}</p>
                  <div class="meta-row"><span>{{ activeNewsSection.items[0].publishedAt }}</span><span>{{ activeNewsSection.items[0].source }}</span><span>重要度 P{{ activeNewsSection.items[0].importance }}</span></div>
                </article>
                <div class="digest-grid">
                  <article v-for="item in activeNewsSection.items.slice(1)" :key="item.id" class="digest-card">
                    <div class="digest-card__head"><h4>{{ item.title }}</h4><em :class="`bias-${item.bias}`">{{ biasLabel(item.bias) }}</em></div>
                    <p>{{ item.summary }}</p>
                    <div class="meta-row"><span>{{ item.publishedAt }}</span><span>{{ item.source }}</span></div>
                  </article>
                </div>
              </section>
            </section>
          </RestoredProductSurface>

          <RestoredProductSurface v-else :state="wealthSampleMeta.state" :source="wealthSampleMeta.source" :as-of="wealthSampleMeta.asOf" :actionable="wealthSampleMeta.actionable" message="原筛选、收益排序和活动列表结构已恢复；样例利率不构成事实、推荐、收益承诺或申购入口。">
            <section class="wealth-page" data-testid="wealth-original-structure">
              <header class="wealth-header"><div><span>WEALTH INFORMATION</span><h2>理财信息</h2></div><div><button type="button" disabled>刷新数据</button><button type="button" disabled>打开参考页面</button></div></header>
              <div class="wealth-toolbar">
                <select v-model="wealthFilters.frequency" aria-label="派息频度"><option value="all">不限频度</option><option value="daily">每日派息</option><option value="fixed">锁仓固定</option><option value="floating">利率浮动</option></select>
                <select v-model="wealthFilters.lock" aria-label="锁定期限"><option value="all">不限锁定日期</option><option value="short">7天以内</option><option value="mid">30天以内</option><option value="long">长期</option></select>
                <input v-model="wealthFilters.keyword" placeholder="按活动名称搜索…" />
              </div>
              <div class="wealth-table-head"><span>活动</span><button type="button" @click="yieldDesc = !yieldDesc">示例年利率 {{ yieldDesc ? '↓' : '↑' }}</button><span>标签</span><span>到期时间</span></div>
              <div class="wealth-list">
                <article v-for="item in filteredWealthCampaigns" :key="item.id" class="wealth-row">
                  <div class="wealth-campaign"><strong>{{ item.name }}</strong><p>{{ item.platform }}</p></div>
                  <div class="wealth-yield"><strong>{{ item.apy }}</strong><p>{{ item.apyNote }}</p></div>
                  <div class="wealth-tags"><span v-for="tag in item.tags" :key="tag">{{ tag }}</span></div>
                  <div class="wealth-expiry"><strong>{{ item.expiryLabel }}</strong><p>{{ item.expiryNote }}</p></div>
                  <button type="button" disabled data-write-action="true">不可申购</button>
                </article>
              </div>
            </section>
          </RestoredProductSurface>
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
  import RestoredProductDataBanner from '@/components/ProductDataState/RestoredProductDataBanner.vue';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import { newsDigestSections, newsSampleMeta, wealthCampaigns, wealthSampleMeta, type NewsAssetKey } from '@/data/sample/news';
  import TradingViewEconomicCalendarPanel from '@/views/hedgeBoard/tradingTools/components/TradingViewEconomicCalendarPanel.vue';

  type NewsSection = 'macro' | 'news' | 'wealth';
  const route = useRoute();
  const activeNewsAsset = ref<NewsAssetKey>('macro');
  const yieldDesc = ref(true);
  const wealthFilters = reactive({ frequency: 'all', lock: 'all', keyword: '' });
  const section = computed<NewsSection>(() => route.meta.newsSection === 'news' || route.meta.newsSection === 'wealth' ? route.meta.newsSection : 'macro');
  const pageTitle = computed(() => '新闻日历与理财');
  const sectionLabel = computed(() => ({ macro: '宏观日历', news: '新闻整理', wealth: '理财信息' })[section.value]);
  const sectionTabs: Array<{ key: NewsSection; label: string; path: string; icon: Component }> = [
    { key: 'macro', label: '宏观日历', path: '/news-calendar/macro', icon: CalendarOutlined },
    { key: 'news', label: '新闻整理', path: '/news-calendar/news', icon: FileSearchOutlined },
    { key: 'wealth', label: '理财信息', path: '/news-calendar/wealth', icon: FundOutlined },
  ];
  const activeNewsSection = computed(() => newsDigestSections.find((item) => item.key === activeNewsAsset.value));
  const filteredWealthCampaigns = computed(() => wealthCampaigns
    .filter((item) => wealthFilters.frequency === 'all' || item.frequency === wealthFilters.frequency)
    .filter((item) => wealthFilters.lock === 'all' || item.lock === wealthFilters.lock)
    .filter((item) => item.name.toLowerCase().includes(wealthFilters.keyword.trim().toLowerCase()))
    .slice()
    .sort((left, right) => yieldDesc.value ? right.apyValue - left.apyValue : left.apyValue - right.apyValue));
  function biasLabel(value: 'positive' | 'neutral' | 'negative') { return ({ positive: '偏正面', neutral: '中性', negative: '偏负面' })[value]; }
</script>

<style scoped lang="less">
  .news-page { display: grid; gap: 14px; padding: 16px; }
  .page-identity { display: flex; align-items: flex-end; justify-content: space-between; gap: 14px; padding: 18px 20px; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; }
  .page-identity span, .section-head span, .wealth-header span { color: #6c8fb1; font-size: 11px; letter-spacing: .15em; }
  h1 { margin: 4px 0 0; font-size: 25px; }
  .page-identity b { padding: 6px 10px; border-radius: 999px; background: #eef4fa; color: #45647f; font-size: 12px; }
  .news-layout { display: grid; grid-template-columns: 190px minmax(0, 1fr); gap: 16px; min-width: 0; }
  .section-sidebar { display: flex; flex-direction: column; align-self: start; gap: 6px; padding: 8px; border: 1px solid #e7edf3; border-radius: 10px; background: #fff; }
  .section-sidebar a { display: flex; align-items: center; gap: 9px; padding: 10px 12px; border-radius: 7px; color: #59636e; }
  .section-sidebar a.is-active { background: #edf6ff; color: #1769aa; font-weight: 600; }
  .section-content { min-width: 0; }
  .panel-card, .wealth-page { display: grid; gap: 16px; padding: 18px; border: 1px solid #e2e8f0; border-radius: 14px; background: #fff; }
  .section-head, .wealth-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
  h2 { margin: 4px 0 0; font-size: 20px; }
  .section-head em { padding: 4px 8px; border-radius: 999px; background: #fff5d6; color: #8a6210; font-size: 11px; font-style: normal; }
  .news-asset-tabs { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .news-asset-tabs button { display: flex; align-items: center; gap: 8px; padding: 11px; border: 1px solid #e3e8ef; border-radius: 10px; background: #fff; color: #667085; }
  .news-asset-tabs button.is-active { border-color: #abc5dc; background: #edf5fb; color: #294a67; }
  .news-asset-tabs span { font-size: 11px; }
  .digest-shell { display: grid; grid-template-columns: .9fr 1.3fr; gap: 12px; }
  .feature-card, .digest-card { padding: 16px; border: 1px solid #e3e8ef; border-radius: 12px; background: #fafbfd; }
  .feature-card h3 { margin: 8px 0; font-size: 21px; }
  .feature-card p, .digest-card p { color: #667085; line-height: 1.65; }
  .digest-grid { display: grid; gap: 10px; }
  .digest-card__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
  .digest-card h4 { margin: 0; font-size: 16px; }
  .digest-card em { font-size: 11px; font-style: normal; }
  .bias-positive { color: #087a55; } .bias-neutral { color: #667085; } .bias-negative { color: #b42318; }
  .meta-row { display: flex; flex-wrap: wrap; gap: 8px; color: #8490a0; font-size: 11px; }
  .wealth-header > div:last-child, .wealth-toolbar { display: flex; flex-wrap: wrap; gap: 8px; }
  .wealth-header button, .wealth-row > button { padding: 8px 11px; border: 0; border-radius: 8px; background: #e7ecf3; color: #748094; }
  .wealth-toolbar select, .wealth-toolbar input { height: 36px; padding: 0 10px; border: 1px solid #dce3eb; border-radius: 8px; background: #fff; }
  .wealth-toolbar input { flex: 1; min-width: 180px; }
  .wealth-table-head, .wealth-row { display: grid; grid-template-columns: 1.1fr .8fr 1fr .7fr auto; align-items: center; gap: 12px; }
  .wealth-table-head { padding: 0 12px; color: #778396; font-size: 12px; }
  .wealth-table-head button { border: 0; background: transparent; color: inherit; text-align: left; }
  .wealth-list { display: grid; gap: 8px; }
  .wealth-row { padding: 14px; border: 1px solid #e5eaf0; border-radius: 11px; background: #fafbfd; }
  .wealth-campaign p, .wealth-yield p, .wealth-expiry p { margin: 4px 0 0; color: #7b8798; font-size: 12px; }
  .wealth-yield strong { color: #225a96; font-size: 20px; }
  .wealth-tags { display: flex; flex-wrap: wrap; gap: 5px; }
  .wealth-tags span { padding: 4px 7px; border-radius: 999px; background: #eef3f8; color: #526b82; font-size: 11px; }
  @media (max-width: 980px) { .news-layout, .digest-shell { grid-template-columns: 1fr; } .section-sidebar { flex-direction: row; overflow-x: auto; } .section-sidebar a { flex: 0 0 auto; } .wealth-table-head { display: none; } .wealth-row { grid-template-columns: 1fr 1fr; } }
  @media (max-width: 620px) { .page-identity, .section-head, .wealth-header { flex-direction: column; align-items: stretch; } .news-asset-tabs { grid-template-columns: repeat(2, 1fr); } .wealth-row { grid-template-columns: 1fr; } }
</style>
