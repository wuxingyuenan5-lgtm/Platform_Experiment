<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { PageWrapper } from '@/components/Page';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import ResearchWorkspace from '../components/ResearchWorkspace.vue';
  import { hedgeBoardNav } from '../composables/useHedgeBoardPage';
  import ToolGroupSection from './components/ToolGroupSection.vue';
  import { loadTradingToolCategory, type TradingToolCategoryId } from './data/catalog';
  import type { TradingToolCategory, TradingToolGroup } from './data/marketTools';

  const route = useRoute();
  const router = useRouter();
  const boardTabs = hedgeBoardNav.map((item) => ({ key: item.id, label: item.label }));
  function selectBoard(key: string) {
    const destination = hedgeBoardNav.find((item) => item.id === key);
    if (destination) void router.push(destination.path);
  }

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
    {
      id: 'general',
      title: '\u7efc\u5408\u5de5\u5177',
      path: '/hedge-board/trading-tools/general',
    },
  ];

  const categoryIds = new Set<TradingToolCategoryId>([
    'macro',
    'equity',
    'crypto',
    'metal',
    'quant',
    'general',
  ]);

  const activeCategoryId = computed<TradingToolCategoryId>(() => {
    const categoryId = String(route.meta?.toolCategory || 'macro') as TradingToolCategoryId;
    return categoryIds.has(categoryId) ? categoryId : 'macro';
  });

  const activeCategory = ref<TradingToolCategory | null>(null);
  const query = ref('');
  const loading = ref(false);
  const loadError = ref(false);
  let categoryRequestId = 0;

  watch(
    activeCategoryId,
    async (categoryId) => {
      const requestId = ++categoryRequestId;
      activeCategory.value = null;
      query.value = '';
      loading.value = true;
      loadError.value = false;
      try {
        const category = await loadTradingToolCategory(categoryId);
        if (requestId === categoryRequestId) activeCategory.value = category;
      } catch {
        if (requestId === categoryRequestId) loadError.value = true;
      } finally {
        if (requestId === categoryRequestId) loading.value = false;
      }
    },
    { immediate: true },
  );

  const displayTitle = computed(() => activeCategory.value?.title ?? '交易工具');

  const activeGroups = computed<TradingToolGroup[]>(() => activeCategory.value?.groups ?? []);
  const filteredGroups = computed(() => {
    const keywords = query.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return activeGroups.value
      .map((group) => ({
        ...group,
        tools: group.tools.filter((tool) => {
          const text =
            `${group.title} ${tool.name} ${tool.domain} ${tool.description}`.toLowerCase();
          return keywords.every((keyword) => text.includes(keyword));
        }),
      }))
      .filter((group) => group.tools.length);
  });
  const totalCount = computed(() =>
    activeGroups.value.reduce((sum, group) => sum + group.tools.length, 0),
  );
  const filteredCount = computed(() =>
    filteredGroups.value.reduce((sum, group) => sum + group.tools.length, 0),
  );

  const pageTitle = computed(() => `\u5bf9\u51b2\u57fa\u91d1\u770b\u677f / ${displayTitle.value}`);
</script>

<template>
  <PageWrapper :title="pageTitle">
    <div class="trading-tools-page">
      <section class="strategy-top-toolbar"
        ><div class="strategy-top-toolbar__left"
          ><CompactSegmentTabs
            :items="boardTabs"
            model-value="tradingTools"
            @update:model-value="selectBoard" /></div
      ></section>
      <ResearchWorkspace
        :pages="categoryTabs.map((item) => ({ key: item.id, label: item.title, path: item.path }))"
        :active="activeCategoryId"
        label="交易工具"
      >
        <div class="trading-tools-page__search">
          <input
            v-model="query"
            type="search"
            aria-label="搜索当前分类工具"
            placeholder="搜索工具名称、网站或用途"
          />
          <button v-if="query" type="button" @click="query = ''">清空</button>
          <span role="status">{{
            loading ? '正在加载工具…' : `${filteredCount} / ${totalCount} 个工具`
          }}</span>
        </div>

        <section class="trading-tools-page__catalog">
          <p v-if="loadError" role="alert">工具目录加载失败，请刷新页面重试。</p>
          <p v-else-if="!loading && !filteredCount">没有匹配的工具，可修改关键词或切换分类。</p>
          <ToolGroupSection v-for="group in filteredGroups" :key="group.id" :group="group" />
        </section>
      </ResearchWorkspace>
    </div>
  </PageWrapper>
</template>

<style scoped lang="less">
  .strategy-top-toolbar {
    padding: 10px 12px;
    border: 1px solid #edf0f4;
    border-radius: 16px;
    background: #fff;
  }

  :global(#app:has(.trading-tools-page)) {
    min-width: 0;
  }

  .trading-tools-page {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding-bottom: 28px;
  }

  .trading-tools-page__category-nav {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }

  .trading-tools-page__search {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
    color: #64748b;
    font-size: 13px;

    input {
      flex: 1;
      min-width: 180px;
      padding: 10px 14px;
      border: 1px solid #c1cfdc;
      border-radius: 10px;
      background: #fff;
      color: #18313c;
    }

    button {
      padding: 7px 12px;
      border: 1px solid #c1cfdc;
      border-radius: 8px;
      background: #fff;
      cursor: pointer;
    }
  }

  .trading-tools-page__category-pill {
    padding: 10px 16px;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease,
      background-color 0.2s ease;
    border: 1px solid rgb(193 207 220 / 88%);
    border-radius: 999px;
    background: linear-gradient(180deg, rgb(255 255 255 / 98%), rgb(243 248 252 / 96%));
    color: #2f5368;
    font-size: 13px;
    text-decoration: none;
  }

  .trading-tools-page__category-pill:hover {
    transform: translateY(-1px);
    border-color: rgb(88 119 142 / 60%);
    box-shadow: 0 12px 24px rgb(15 23 42 / 5%);
  }

  .trading-tools-page__category-pill.is-active {
    border-color: rgb(78 114 143 / 75%);
    background: linear-gradient(180deg, rgb(228 237 245 / 98%), rgb(238 245 250 / 98%));
    box-shadow: 0 10px 24px rgb(15 23 42 / 6%);
    color: #18313c;
  }

  .trading-tools-page__catalog {
    display: flex;
    flex-direction: column;
    padding: 20px;
    border: 1px solid rgb(193 207 220 / 88%);
    border-radius: 16px;
    background: linear-gradient(180deg, rgb(255 255 255 / 98%), rgb(247 250 252 / 98%));
    box-shadow: 0 18px 42px rgb(15 23 42 / 4%);
    gap: 24px;
  }

  @media (max-width: 900px) {
    .trading-tools-page__catalog {
      padding: 22px 18px;
    }
  }
</style>
