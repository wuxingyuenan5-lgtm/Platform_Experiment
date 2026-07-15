<script setup lang="ts">
  import { computed } from 'vue';
  import { useRoute, RouterLink } from 'vue-router';
  import { PageWrapper } from '@/components/Page';
  import ToolGroupSection from './components/ToolGroupSection.vue';
  import {
    tradingToolCategoryMap,
    type TradingToolCategoryId,
  } from './data/marketTools';

  const route = useRoute();

  const categoryTabs: Array<{
    id: TradingToolCategoryId;
    title: string;
    path: string;
  }> = [
    { id: 'macro', title: '\u5b8f\u89c2\u5de5\u5177', path: '/hedge-board/trading-tools/macro' },
    { id: 'equity', title: '\u80a1\u5e02\u5de5\u5177', path: '/hedge-board/trading-tools/equity' },
    { id: 'crypto', title: '\u52a0\u5bc6\u5de5\u5177', path: '/hedge-board/trading-tools/crypto' },
    { id: 'metal', title: '\u91d1\u5c5e\u5de5\u5177', path: '/hedge-board/trading-tools/metal' },
    { id: 'quant', title: '\u91cf\u5316\u5de5\u5177', path: '/hedge-board/trading-tools/quant' },
    { id: 'general', title: '\u7efc\u5408\u5de5\u5177', path: '/hedge-board/trading-tools/general' },
  ];

  const activeCategoryId = computed<TradingToolCategoryId>(() => {
    const categoryId = String(route.meta?.toolCategory || 'macro') as TradingToolCategoryId;
    return tradingToolCategoryMap[categoryId] ? categoryId : 'macro';
  });

  const activeCategory = computed(() => tradingToolCategoryMap[activeCategoryId.value]);

  const displayTitle = computed(() => activeCategory.value.title);

  const activeGroups = computed(() => activeCategory.value.groups);

  const pageTitle = computed(
    () => `\u5bf9\u51b2\u57fa\u91d1\u770b\u677f / ${displayTitle.value}`,
  );
</script>

<template>
  <PageWrapper :title="pageTitle">
    <div class="trading-tools-page">
      <nav class="trading-tools-page__category-nav">
        <RouterLink
          v-for="item in categoryTabs"
          :key="item.id"
          :to="item.path"
          class="trading-tools-page__category-pill"
          :class="{ 'is-active': item.id === activeCategoryId }"
        >
          {{ item.title }}
        </RouterLink>
      </nav>

      <section class="trading-tools-page__catalog">
        <ToolGroupSection
          v-for="group in activeGroups"
          :key="group.id"
          :group="group"
        />
      </section>
    </div>
  </PageWrapper>
</template>

<style scoped lang="less">
  .trading-tools-page {
    display: flex;
    flex-direction: column;
    gap: 28px;
    padding-bottom: 28px;
  }

  .trading-tools-page__category-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .trading-tools-page__category-pill {
    border: 1px solid rgba(193, 207, 220, 0.88);
    border-radius: 999px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(243, 248, 252, 0.96));
    padding: 10px 16px;
    font-size: 13px;
    color: #2f5368;
    text-decoration: none;
    transition:
      transform 0.2s ease,
      border-color 0.2s ease,
      box-shadow 0.2s ease,
      background-color 0.2s ease;
  }

  .trading-tools-page__category-pill:hover {
    transform: translateY(-1px);
    border-color: rgba(88, 119, 142, 0.6);
    box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
  }

  .trading-tools-page__category-pill.is-active {
    border-color: rgba(78, 114, 143, 0.75);
    background: linear-gradient(180deg, rgba(228, 237, 245, 0.98), rgba(238, 245, 250, 0.98));
    color: #18313c;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  }

  .trading-tools-page__catalog {
    display: flex;
    flex-direction: column;
    gap: 34px;
    border: 1px solid rgba(193, 207, 220, 0.88);
    border-radius: 24px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 252, 0.98));
    padding: 28px;
    box-shadow: 0 18px 42px rgba(15, 23, 42, 0.04);
  }

  @media (max-width: 900px) {
    .trading-tools-page__catalog {
      padding: 22px 18px;
    }
  }
</style>
