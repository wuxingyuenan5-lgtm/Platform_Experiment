<template>
  <section class="viewpoints" aria-label="观点跟踪">
    <header
      ><h2>观点跟踪</h2
      ><input v-model="search" aria-label="搜索观点来源" placeholder="搜索作者、平台、研究方向"
    /></header>
    <nav aria-label="观点分类">
      <button
        v-for="item in categories"
        :key="item.id"
        :aria-pressed="category === item.id"
        @click="category = item.id"
        >{{ item.label }}</button
      >
    </nav>
    <div class="viewpoints__filters">
      <label
        >平台
        <select v-model="platform" aria-label="观点来源平台"
          ><option value="">全部</option
          ><option v-for="item in platforms" :key="item">{{ item }}</option></select
        ></label
      >
      <label><input v-model="priority" type="checkbox" />重点关注</label
      ><span>{{ visible.length }} 个来源</span>
    </div>
    <div class="viewpoints__sources">
      <article v-for="item in visible" :key="item.id">
        <div
          ><strong>{{ item.name }}</strong
          ><small>{{ item.platform }}{{ item.priority ? ' · 重点关注' : '' }}</small></div
        >
        <p>{{ item.focus }}</p>
        <div class="viewpoints__actions"
          ><a :href="item.url" target="_blank" rel="noopener noreferrer"
            >{{ item.platform === '微信公众号' ? '种子文章' : '打开来源' }} ↗</a
          ><button
            :aria-expanded="editing === item.id"
            @click="editing = editing === item.id ? '' : item.id"
            >备注{{ notes[item.id] ? ' · 已记录' : '' }}</button
          ></div
        >
        <textarea
          v-if="editing === item.id"
          v-model="notes[item.id]"
          :aria-label="`${item.name}备注`"
          placeholder="记录关注主题或阅读笔记"
        ></textarea>
      </article>
      <p v-if="!visible.length">没有匹配的来源。</p>
    </div>
    <section v-if="category === 'metals'" class="viewpoints__articles"
      ><h3>金属分析师跟踪</h3><GoldAnalystsPanel
    /></section>
  </section>
</template>
<script setup lang="ts">
  import { computed, defineAsyncComponent, ref } from 'vue';
  import { useStorage } from '@vueuse/core';
  import { useUserStore } from '@/store/modules/user';
  import sources from '../nativeData/viewpointSources.json';

  const GoldAnalystsPanel = defineAsyncComponent(() => import('./GoldAnalystsPanel.vue'));
  const user = useUserStore();
  const notes = useStorage<Record<string, string>>(
    `viewpoint-notes:${user.getUserInfo.userId || 'anonymous'}`,
    {},
  );
  const category = ref('crypto'),
    search = ref(''),
    platform = ref(''),
    priority = ref(false),
    editing = ref('');
  const categories = [
    { id: 'crypto', label: '加密观点跟踪' },
    { id: 'metals', label: '金属观点跟踪' },
    { id: 'us', label: '美股观点跟踪' },
    { id: 'macro', label: '宏观观点跟踪' },
    { id: 'a-share', label: 'A股观点跟踪' },
    { id: 'quant', label: '固收与量化' },
    { id: 'other', label: '其他市场观点' },
  ];
  const platforms = [...new Set(sources.map((item) => item.platform))];
  const visible = computed(() =>
    sources
      .filter(
        (item) =>
          item.categories.includes(category.value) &&
          (!platform.value || item.platform === platform.value) &&
          (!priority.value || item.priority) &&
          `${item.name} ${item.focus} ${item.platform}`
            .toLowerCase()
            .includes(search.value.trim().toLowerCase()),
      )
      .sort(
        (a, b) => Number(b.priority) - Number(a.priority) || a.name.localeCompare(b.name, 'zh-CN'),
      ),
  );
</script>
<style scoped>
  .viewpoints {
    color: var(--strategy-text-1);
  }

  header,
  nav,
  .viewpoints__filters,
  .viewpoints__actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }

  header {
    justify-content: space-between;
    margin-bottom: 18px;
  }

  h2 {
    margin: 0;
    font-size: 20px;
  }

  h3 {
    margin: 0 0 16px;
  }

  input,
  select,
  button,
  textarea {
    padding: 7px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 7px;
    background: var(--strategy-surface);
    color: inherit;
    font: inherit;
  }

  header input {
    width: min(340px, 100%);
  }

  button {
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent);
  }

  .viewpoints__filters {
    margin: 16px 0;
    font-size: 13px;
  }

  label {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .viewpoints__sources {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    padding: 2px;
  }

  article {
    min-width: 0;
    padding: 16px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
  }

  strong,
  small {
    display: block;
  }

  small,
  p {
    margin: 6px 0 12px;
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  a {
    color: var(--strategy-accent);
  }

  textarea {
    display: block;
    width: 100%;
    min-height: 90px;
    margin-top: 12px;
    resize: vertical;
  }

  .viewpoints__articles {
    margin-top: 24px;
    padding: 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
  }

  button:focus-visible,
  a:focus-visible,
  input:focus-visible,
  select:focus-visible,
  textarea:focus-visible {
    outline: 2px solid var(--strategy-accent);
    outline-offset: 2px;
  }

  @media (max-width: 1100px) {
    .viewpoints__sources {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 650px) {
    .viewpoints__sources {
      grid-template-columns: minmax(0, 1fr);
    }
  }
</style>
