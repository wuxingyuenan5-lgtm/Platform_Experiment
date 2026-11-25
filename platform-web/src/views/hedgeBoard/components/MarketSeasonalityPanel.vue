<template>
  <ChartExpand :title="title">
    <section class="market-seasonality" :aria-label="title">
      <header>
        <h2>{{ title }}</h2>
        <label
          >分析标的
          <select v-model="asset" :aria-label="title + '标的'"
            ><option v-for="item in choices" :key="item.id" :value="item.id">{{
              item.label
            }}</option></select
          ></label
        >
      </header>
      <SeasonalityPanel :key="asset" :asset="asset" />
    </section>
  </ChartExpand>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type { SeasonalAsset } from '@/api/seasonality';
  import ChartExpand from './ChartExpand.vue';
  import SeasonalityPanel from './SeasonalityPanel.vue';

  const props = defineProps<{ market: 'us' | 'cn' }>();
  const title = computed(() => (props.market === 'us' ? '美股月度统计分析' : 'A股月度统计分析'));
  const choices = computed<Array<{ id: SeasonalAsset; label: string }>>(() =>
    props.market === 'us'
      ? [
          { id: 'us-spy', label: '标普500 ETF · SPY' },
          { id: 'us-ndx', label: '纳斯达克100指数' },
          { id: 'us-dow', label: '道琼斯工业指数' },
        ]
      : [
          { id: 'cn-hs300', label: '沪深300' },
          { id: 'cn-csi1000', label: '中证1000' },
          { id: 'cn-chinext', label: '创业板指' },
          { id: 'cn-star50', label: '科创50' },
        ],
  );
  const asset = ref<SeasonalAsset>(choices.value[0].id);
</script>
<style scoped>
  .market-seasonality {
    min-width: 0;
    margin-top: 16px;
    padding: 18px;
    border: 1px solid var(--strategy-border, #dbe4ee);
    border-radius: 14px;
    background: var(--strategy-surface, #fff);
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
    padding-right: 42px;
  }

  h2 {
    margin: 0;
    color: var(--strategy-text-1, #17364d);
    font-size: 16px;
    font-weight: 600;
  }

  label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
  }

  select {
    padding: 5px 9px;
    border: 1px solid var(--strategy-border, #dbe4ee);
    border-radius: 7px;
    background: #fff;
    color: inherit;
    font: inherit;
  }
</style>
