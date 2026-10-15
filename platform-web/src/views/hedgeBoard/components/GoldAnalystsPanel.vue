<template>
  <div class="gold-research" :aria-busy="loading">
    <div class="gold-authors"
      ><button :class="{ active: !author }" @click="author = ''">全部分析师</button
      ><button
        v-for="item in visibleAuthors"
        :key="item.id"
        :class="{ active: author === item.id }"
        :title="[item.platform, ...(item.styleTags || [])].join(' · ')"
        @click="author = item.id"
        >{{ item.nameZh || item.name }}</button
      ><button v-if="(data?.analysts.length || 0) > 5" @click="allAuthors = !allAuthors">{{
        allAuthors ? '收起' : `更多 ${(data?.analysts.length || 0) - 5} 位`
      }}</button></div
    >
    <div class="gold-controls"
      ><label
        >观点
        <select v-model="stance"
          ><option value="">全部</option
          ><option value="bull">看多</option
          ><option value="bear">看空</option
          ><option value="conditional">条件</option
          ><option value="mixed">分歧</option
          ><option value="neutral">中性</option
          ><option value="unspecified">未明确</option></select
        ></label
      ><form @submit.prevent="search"
        ><input
          v-model="input"
          aria-label="搜索分析师文章"
          placeholder="搜索标题、观点或资产"
        /><button type="submit">搜索</button></form
      ><span class="gold-meta">{{ data?.total ?? '—' }} 篇 · GoldPulse 观点整理</span></div
    >
    <p v-if="error" class="gold-warning">{{ error }}</p
    ><p v-if="data?.status === 'stale'" class="gold-warning">更新暂时中断，保留最近取得的观点。</p>
    <p v-if="loading && !data">正在读取观点…</p>
    <template v-if="data">
      <article v-for="article in data?.articles" :key="article.id" class="gold-article">
        <small>{{ article.date || '日期未披露' }} · {{ authorName(article.analystId) }}</small>
        <h3>{{ article.headlineChinese || article.title }}</h3>
        <div
          ><span v-for="(view, i) in article.views.slice(0, 3)" :key="i" class="gold-tag"
            >{{ view.assetName }} · {{ directionLabel(view.stance) }} ·
            {{ view.horizonText || '期限未明确' }}</span
          ><span v-if="article.views.length > 3" class="gold-meta"
            >+{{ article.views.length - 3 }} 条观点</span
          ></div
        >
        <template v-if="article.views.length">
          <p>{{ article.summary }}</p>
          <details
            ><summary>展开 {{ article.views.length }} 条观点与条件</summary
            ><div v-for="view in article.views" :key="view.id" class="gold-view"
              ><b>{{ view.assetName }} · {{ directionLabel(view.stance) }}</b
              ><small> · {{ view.horizonText }}</small
              ><p>{{ view.thesis }}</p
              ><ul v-if="view.drivers?.length"
                ><li v-for="(driver, i) in view.drivers" :key="i">{{ driver.text }}</li></ul
              ><p v-for="scenario in view.scenarios" :key="scenario.id"
                ><b>{{ scenario.label }}：</b>{{ scenario.conditionText }} {{ scenario.outcome }}</p
              ><p v-for="level in view.levels" :key="level.id"
                >{{ level.expressionRaw }} {{ level.confirmationText }}</p
              ></div
            ><p v-for="(warning, i) in article.warnings" :key="i" class="gold-meta">{{
              warning
            }}</p></details
          >
        </template>
        <p v-else class="gold-meta">正文观点尚未读取。</p>
        <a
          v-if="article.urlOriginal"
          :href="article.urlOriginal"
          target="_blank"
          rel="noopener noreferrer"
          >阅读作者原文 ↗</a
        >
      </article>
      <p v-if="data && !data.articles.length">没有符合当前筛选的文章。</p>
    </template>
    <div class="gold-pagination"
      ><button :disabled="page <= 1 || loading" @click="page--">上一页</button
      ><span>{{ page }} / {{ pages }}</span
      ><button :disabled="page >= pages || loading" @click="page++">下一页</button></div
    >
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, shallowRef, watch } from 'vue';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import { goldRequest, directionLabel, type AnalystPage } from './goldResearch';

  const data = shallowRef<AnalystPage>();
  const author = ref('');
  const stance = ref('');
  const input = ref('');
  const query = ref('');
  const page = ref(1);
  const allAuthors = ref(false);
  const error = ref('');
  const loading = ref(true);
  let generation = 0;
  const visibleAuthors = computed(() =>
    allAuthors.value ? data.value?.analysts : data.value?.analysts.slice(0, 5),
  );
  const pages = computed(() => Math.max(1, Math.ceil((data.value?.total || 0) / 12)));
  const authorName = (id: string) => {
    const person = data.value?.analysts.find((a) => a.id === id);
    return person?.name || id;
  };
  async function load() {
    const token = ++generation;
    loading.value = true;
    try {
      const result = await goldRequest<AnalystPage>('analyst-views', {
        author: author.value,
        stance: stance.value,
        query: query.value,
        page: page.value,
      });
      if (token === generation) {
        data.value = result;
        error.value = '';
      }
    } catch {
      if (token === generation) error.value = '分析师观点暂时不可用，请稍后重试。';
    } finally {
      if (token === generation) loading.value = false;
    }
  }
  function search() {
    query.value = input.value.trim();
  }
  watch([author, stance, query], () => {
    if (page.value !== 1) page.value = 1;
    else void load();
  });
  watch(page, () => void load());
  useDashboardRefresh(load);
</script>
<style scoped src="./goldResearch.css"></style>
