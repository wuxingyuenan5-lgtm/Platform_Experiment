<template>
  <PageWrapper :title="pageTitle">
    <div class="placeholder-page">
      <section class="hero enter-y">
        <div class="hero-copy">
          <div class="eyebrow">{{ eyebrow }}</div>
          <h1>{{ heading }}</h1>
          <p>{{ summary }}</p>
        </div>
        <div class="hero-status">
          <div class="status-label">当前阶段</div>
          <div class="status-value">{{ status }}</div>
          <div class="status-note">{{ statusNote }}</div>
        </div>
      </section>

      <section class="grid">
        <div class="panel enter-y">
          <div class="panel-title">本页定位</div>
          <ul class="bullet-list">
            <li v-for="item in goals" :key="item">{{ item }}</li>
          </ul>
        </div>

        <div class="panel enter-y">
          <div class="panel-title">下一步建设</div>
          <ul class="bullet-list">
            <li v-for="item in nextSteps" :key="item">{{ item }}</li>
          </ul>
        </div>
      </section>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import { useRoute } from 'vue-router';
  import { PageWrapper } from '@/components/Page';

  type PlaceholderMeta = {
    eyebrow?: string;
    heading?: string;
    summary?: string;
    status?: string;
    statusNote?: string;
    goals?: string[];
    nextSteps?: string[];
  };

  const route = useRoute();

  const placeholder = computed<PlaceholderMeta>(() => {
    return (route.meta?.placeholder as PlaceholderMeta) || {};
  });

  const pageTitle = computed(() => String(route.meta?.title || placeholder.value.heading || '模块占位页'));
  const eyebrow = computed(() => placeholder.value.eyebrow || 'PLATFORM MODULE');
  const heading = computed(() => placeholder.value.heading || pageTitle.value);
  const summary = computed(
    () => placeholder.value.summary || '该模块已预留在统一平台结构中，当前先作为骨架页保留，后续按业务优先级继续填充。',
  );
  const status = computed(() => placeholder.value.status || '待建设');
  const statusNote = computed(
    () => placeholder.value.statusNote || '信息架构已预留，当前版本先确认方向与入口位置。',
  );
  const goals = computed(
    () =>
      placeholder.value.goals || [
        '保留未来并入统一平台的稳定入口',
        '让导航结构提前适配新的产品骨架',
        '避免后续整合时再次大幅改菜单',
      ],
  );
  const nextSteps = computed(
    () =>
      placeholder.value.nextSteps || [
        '补齐业务口径与核心指标定义',
        '确定最终页面信息结构与交互方式',
        '按优先级逐步替换为真实业务页面',
      ],
  );
</script>

<style scoped>
  .placeholder-page {
    padding: 20px;
  }

  .hero {
    display: grid;
    grid-template-columns: minmax(0, 1.8fr) minmax(260px, 0.8fr);
    gap: 24px;
    padding: 28px 30px;
    background:
      linear-gradient(135deg, rgba(22, 60, 52, 0.06), rgba(122, 154, 192, 0.08)),
      linear-gradient(180deg, #ffffff, #f3f7fb);
    border: 1px solid rgba(196, 207, 221, 0.2);
    border-radius: 18px;
    box-shadow: 0 18px 40px rgba(113, 137, 165, 0.08);
  }

  .eyebrow {
    margin-bottom: 10px;
    color: #6d8198;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.18em;
  }

  .hero h1 {
    margin: 0;
    color: #172126;
    font-size: 32px;
    font-weight: 700;
    line-height: 1.2;
  }

  .hero p {
    max-width: 720px;
    margin: 14px 0 0;
    color: #55606d;
    font-size: 15px;
    line-height: 1.9;
  }

  .hero-status {
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 22px 24px;
    background: rgba(255, 255, 255, 0.78);
    border: 1px solid rgba(128, 101, 42, 0.14);
    border-radius: 16px;
  }

  .status-label {
    color: #7a828f;
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .status-value {
    margin-top: 10px;
    color: #17332e;
    font-size: 26px;
    font-weight: 700;
  }

  .status-note {
    margin-top: 8px;
    color: #5d6876;
    line-height: 1.8;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    margin-top: 20px;
  }

  .panel {
    padding: 24px;
    background: #fff;
    border: 1px solid #ebe6dc;
    border-radius: 16px;
    box-shadow: 0 10px 28px rgba(28, 35, 40, 0.05);
  }

  .panel-title {
    margin-bottom: 14px;
    color: #1d2730;
    font-size: 16px;
    font-weight: 700;
  }

  .bullet-list {
    margin: 0;
    padding-left: 18px;
    color: #55606d;
    line-height: 1.9;
  }

  .bullet-list li + li {
    margin-top: 8px;
  }

  @media (max-width: 980px) {
    .hero,
    .grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 768px) {
    .placeholder-page {
      padding: 12px;
    }

    .hero {
      padding: 22px 18px;
    }

    .hero h1 {
      font-size: 26px;
    }
  }
</style>
