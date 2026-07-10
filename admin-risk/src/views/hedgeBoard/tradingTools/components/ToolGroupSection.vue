<script setup lang="ts">
  import ToolLinkCard from './ToolLinkCard.vue';
  import type { TradingToolGroup } from '../data/marketTools';

  defineProps<{
    group: TradingToolGroup;
  }>();
</script>

<template>
  <section class="tool-group-section">
    <div class="tool-group-section__head">
      <h3>{{ group.title }}</h3>
    </div>

    <div class="tool-group-section__grid">
      <ToolLinkCard
        v-for="tool in group.tools"
        :key="tool.id"
        :tool="tool"
      />
    </div>
  </section>
</template>

<style scoped lang="less">
  .tool-group-section {
    display: flex;
    flex-direction: column;
    gap: 22px;
  }

  .tool-group-section__head {
    border-bottom: 1px solid rgba(204, 216, 227, 0.9);
    padding-bottom: 18px;
  }

  .tool-group-section__head h3 {
    margin: 0;
    font-size: 24px;
    line-height: 1.2;
    color: #18313c;
  }

  .tool-group-section__grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 18px;
  }

  @media (max-width: 900px) {
    .tool-group-section__grid {
      grid-template-columns: 1fr;
    }
  }
</style>
