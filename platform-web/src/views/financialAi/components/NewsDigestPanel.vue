<template>
  <section id="news-digest" class="news-panel" data-testid="financial-ai-news-digest">
    <header><h2>新闻整理</h2></header>
    <nav class="asset-tabs" aria-label="新闻资产分类">
      <button
        v-for="asset in newsDigestSections"
        :key="asset.key"
        type="button"
        :class="{ 'is-active': activeAsset === asset.key }"
        @click="activeAsset = asset.key"
      >
        <span>{{ asset.index }}</span
        ><strong>{{ asset.label }}</strong>
      </button>
    </nav>
    <section v-if="activeSection" class="digest-shell">
      <article class="feature-card">
        <div class="eyebrow">{{ activeSection.eyebrow }}</div>
        <h3>{{ activeSection.items[0].title }}</h3>
        <p>{{ activeSection.items[0].summary }}</p>
        <div class="impact-row">
          <span>{{ activeSection.items[0].publishedAt }}</span>
          <span>{{ activeSection.items[0].source }}</span>
          <span>重要度 P{{ activeSection.items[0].importance }}</span>
          <em :class="biasClass(activeSection.items[0].bias)">{{
            biasLabel(activeSection.items[0].bias)
          }}</em>
        </div>
        <p class="section-description">{{ activeSection.description }}</p>
      </article>
      <div class="digest-grid">
        <article v-for="item in activeSection.items.slice(1)" :key="item.id" class="digest-card">
          <div class="digest-card-head">
            <h4>{{ item.title }}</h4
            ><em :class="biasClass(item.bias)">{{ biasLabel(item.bias) }}</em>
          </div>
          <p>{{ item.summary }}</p>
          <div class="impact-row"
            ><span>{{ item.publishedAt }}</span
            ><span>{{ item.source }}</span
            ><span>P{{ item.importance }}</span></div
          >
        </article>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { newsDigestSections, type NewsAssetKey, type NewsDigestItem } from '@/data/sample/news';

  const activeAsset = ref<NewsAssetKey>('macro');
  const activeSection = computed(
    () =>
      newsDigestSections.find((item) => item.key === activeAsset.value) ?? newsDigestSections[0],
  );
  function biasClass(bias: NewsDigestItem['bias']) {
    return { bull: 'is-bull', neutral: 'is-flat', bear: 'is-bear' }[bias];
  }
  function biasLabel(bias: NewsDigestItem['bias']) {
    return { bull: '偏多', neutral: '中性', bear: '偏空' }[bias];
  }
</script>

<style scoped lang="less">
  .news-panel {
    display: grid;
    gap: 16px;
    padding: 18px;
    border: 1px solid #dbe4ed;
    border-radius: 8px;
    background: #fff;
    box-shadow: 0 1px 3px rgb(15 23 42 / 6%);
  }

  h2 {
    margin: 0;
    color: #17212f;
    font-size: 22px;
    font-weight: 800;
  }

  .asset-tabs {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 8px;
  }

  .asset-tabs button {
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

  .asset-tabs button.is-active {
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

  h3 {
    margin: 10px 0;
    color: #172033;
    font-size: 22px;
  }

  h4 {
    margin: 0;
    color: #172033;
    font-size: 16px;
  }

  p {
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

  .digest-card-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
  }

  .impact-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
    color: #8490a0;
    font-size: 11px;
  }

  em {
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

  @media (max-width: 1200px) {
    .asset-tabs {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
  }

  @media (max-width: 900px) {
    .digest-shell {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 620px) {
    .asset-tabs {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
