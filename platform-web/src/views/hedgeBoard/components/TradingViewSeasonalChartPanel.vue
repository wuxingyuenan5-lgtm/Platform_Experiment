<template>
  <div class="seasonal-chart-panel">
    <div class="seasonal-chart-panel__toolbar">
      <div class="seasonal-chart-panel__meta">
        <span class="seasonal-chart-panel__status" :class="`is-${status}`"></span>
        <span>{{ statusLabel }}</span>
        <span class="seasonal-chart-panel__source">TradingView · {{ symbol }}</span>
      </div>
      <span class="seasonal-chart-panel__hint">近五年 · 日线 · 按日历年对齐</span>
    </div>

    <div
      ref="stageRef"
      class="seasonal-chart-panel__stage"
      :class="{ 'is-ready': status === 'ready' }"
    >
      <tv-seasonal-chart
        :symbol="symbol"
        theme="light"
        locale="zh_CN"
        show-average
        show-series-labels
        :aria-label="`${title ?? symbol} Seasonal Chart`"
      >
        <div class="seasonal-chart-panel__empty">正在加载 TradingView Seasonal Chart…</div>
      </tv-seasonal-chart>
      <div v-if="status === 'error'" class="seasonal-chart-panel__error">
        TradingView 组件暂时无法加载，请检查网络后刷新页面。
      </div>
    </div>

    <div class="seasonal-chart-panel__legend">
      <span class="seasonal-chart-panel__legend-dot"></span>
      <span>数据由 TradingView 提供 · 页面不请求平台行情 API</span>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { onBeforeUnmount, onMounted, ref } from 'vue';
  import { ensureTradingViewSeasonalScript } from './tradingViewSeasonalChart';

  const props = defineProps<{
    symbol: string;
    title?: string;
  }>();

  const stageRef = ref<HTMLDivElement | null>(null);
  const status = ref<'loading' | 'ready' | 'error'>('loading');
  const statusLabel = ref('加载中');
  let intersectionObserver: IntersectionObserver | null = null;

  const renderWidget = async () => {
    if (!stageRef.value) return;
    try {
      await ensureTradingViewSeasonalScript();
      status.value = 'ready';
      statusLabel.value = '可用';
    } catch (error) {
      console.error('[hedgeBoard] TradingView Seasonal Chart render failed:', props.symbol, error);
      status.value = 'error';
      statusLabel.value = '不可用';
    }
  };

  onMounted(() => {
    const stageNode = stageRef.value;
    if (!stageNode) return;
    if (typeof IntersectionObserver === 'undefined') {
      void renderWidget();
      return;
    }
    intersectionObserver = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          void renderWidget();
          intersectionObserver?.disconnect();
          intersectionObserver = null;
        }
      },
      { rootMargin: '240px 0px', threshold: 0.01 },
    );
    intersectionObserver.observe(stageNode);
  });

  onBeforeUnmount(() => {
    intersectionObserver?.disconnect();
    intersectionObserver = null;
  });
</script>

<style scoped>
  .seasonal-chart-panel {
    min-width: 0;
    color: #172b4d;
  }

  .seasonal-chart-panel__toolbar,
  .seasonal-chart-panel__meta,
  .seasonal-chart-panel__legend {
    display: flex;
    align-items: center;
  }

  .seasonal-chart-panel__toolbar {
    justify-content: space-between;
    gap: 12px;
    min-height: 28px;
    margin-bottom: 8px;
    font-size: 12px;
  }

  .seasonal-chart-panel__meta {
    min-width: 0;
    gap: 7px;
    color: #526581;
    white-space: nowrap;
  }

  .seasonal-chart-panel__source {
    color: #7a8ba6;
  }

  .seasonal-chart-panel__hint {
    flex: none;
    color: #7a8ba6;
    white-space: nowrap;
  }

  .seasonal-chart-panel__status,
  .seasonal-chart-panel__legend-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: #9aaac0;
  }

  .seasonal-chart-panel__status.is-loading {
    animation: seasonal-pulse 1.2s ease-in-out infinite;
    background: #2f6fed;
  }

  .seasonal-chart-panel__status.is-ready,
  .seasonal-chart-panel__legend-dot {
    background: #0f9d72;
  }

  .seasonal-chart-panel__status.is-error {
    background: #d84a5a;
  }

  .seasonal-chart-panel__stage {
    position: relative;
    height: 390px;
    min-height: 390px;
    overflow: hidden;
    border: 1px solid #d9e2ef;
    border-radius: 10px;
    background: #fff;
  }

  .seasonal-chart-panel__stage.is-ready {
    min-height: 390px;
  }

  .seasonal-chart-panel__stage tv-seasonal-chart {
    display: block;
    width: 100%;
    height: 100%;
    min-height: 390px;
  }

  .seasonal-chart-panel__empty {
    display: grid;
    min-height: 390px;
    place-items: center;
    padding: 24px;
    color: #7a8ba6;
    font-size: 13px;
    text-align: center;
  }

  .seasonal-chart-panel__error {
    display: grid;
    position: absolute;
    padding: 24px;
    background: rgb(255 255 255 / 92%);
    color: #b54747;
    font-size: 13px;
    text-align: center;
    inset: 0;
    place-items: center;
  }

  .seasonal-chart-panel__legend {
    gap: 7px;
    margin-top: 8px;
    color: #7a8ba6;
    font-size: 11px;
  }

  @keyframes seasonal-pulse {
    0%,
    100% {
      opacity: 0.45;
    }

    50% {
      opacity: 1;
    }
  }

  @media (max-width: 700px) {
    .seasonal-chart-panel__toolbar {
      flex-direction: column;
      align-items: flex-start;
      gap: 5px;
    }

    .seasonal-chart-panel__stage,
    .seasonal-chart-panel__stage.is-ready,
    .seasonal-chart-panel__stage tv-seasonal-chart,
    .seasonal-chart-panel__empty {
      height: 330px;
      min-height: 330px;
    }
  }
</style>
