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
          <ProductDataStatusAlert :meta="macroMeta" class="mb-4" />
          <TradingViewEconomicCalendarPanel />
        </template>

        <ProductNotConfiguredPanel
          v-else-if="section === 'news'"
          title="新闻聚合Provider尚未配置"
          description="当前没有正式新闻Provider、来源校验、发布时间合同或去重策略。为避免把静态摘要误认为最新新闻，本页不展示硬编码标题和观点。"
          source="not-configured: news-aggregation-provider"
        />

        <div v-else class="wealth-state">
          <ProductNotConfiguredPanel
            title="理财活动数据源尚未配置"
            description="当前没有经过合同验证的活动Provider、实时年利率、额度和到期时间。固定APY与示例活动已从正式路径移除。"
            source="not-configured: wealth-campaign-provider"
          />
          <Button type="default" @click="openReference">打开外部参考页面</Button>
          <p>外部页面由第三方维护，不构成Platform数据、推荐或收益承诺。</p>
        </div>
      </div>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, type Component } from 'vue';
  import { RouterLink, useRoute } from 'vue-router';
  import { Button } from 'ant-design-vue';
  import { CalendarOutlined, FileSearchOutlined, FundOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import ProductDataStatusAlert from '@/components/ProductDataState/ProductDataStatusAlert.vue';
  import ProductNotConfiguredPanel from '@/components/ProductDataState/ProductNotConfiguredPanel.vue';
  import type { ProductDataMeta } from '@/api/platform/productDataState';
  import TradingViewEconomicCalendarPanel from '@/views/hedgeBoard/tradingTools/components/TradingViewEconomicCalendarPanel.vue';

  type NewsSection = 'macro' | 'news' | 'wealth';

  const route = useRoute();
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
  const macroMeta = computed<ProductDataMeta>(() => ({
    status: 'ready',
    source: 'TradingView Economic Calendar',
    timezone: 'widget-defined',
    unit: 'economic event',
    precision: 'provider-defined',
    message: '该组件直接读取第三方公开日历；Platform不缓存或改写事件数值。',
  }));

  function openReference() {
    const target =
      typeof route.meta.embeddedUrl === 'string'
        ? route.meta.embeddedUrl
        : 'https://app.barker.money/campaigns';
    window.open(target, '_blank', 'noopener,noreferrer');
  }
</script>

<style scoped>
  .news-layout {
    display: grid;
    grid-template-columns: 190px minmax(0, 1fr);
    gap: 16px;
    min-width: 0;
    padding: 16px;
  }

  .section-sidebar {
    display: flex;
    flex-direction: column;
    gap: 6px;
    align-self: start;
    padding: 8px;
    border: 1px solid #e7edf3;
    border-radius: 8px;
    background: #fff;
  }

  .section-sidebar a {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 10px 12px;
    border-radius: 6px;
    color: #59636e;
  }

  .section-sidebar a.is-active {
    color: #1769aa;
    background: #edf6ff;
    font-weight: 600;
  }

  .section-content {
    min-width: 0;
  }

  .wealth-state {
    display: grid;
    gap: 14px;
  }

  .wealth-state :deep(.ant-btn) {
    justify-self: start;
  }

  .wealth-state p {
    margin: 0;
    color: #59636e;
    font-size: 13px;
  }

  @media (max-width: 768px) {
    .news-layout {
      grid-template-columns: 1fr;
      padding: 12px;
    }

    .section-sidebar {
      flex-direction: row;
      overflow-x: auto;
    }

    .section-sidebar a {
      flex: 0 0 auto;
    }
  }
</style>
