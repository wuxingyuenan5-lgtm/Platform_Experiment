<template>
  <section class="panel funding-chart-panel">
    <div class="panel-title">
      <h3>真实组合与执行状态</h3>
    </div>

    <p v-if="!positionGroups.length" class="state-text">暂无真实 Funding 组合。</p>

    <div v-else class="group-list">
      <article v-for="item in positionGroups" :key="item.instructionId" class="group-card">
        <header>
          <strong>{{ item.perpetualSymbol }} / {{ item.spotSymbol }}</strong>
          <span>{{ item.status }}</span>
        </header>
        <div class="group-grid">
          <div
            ><span>永续累计成交</span><strong>{{ item.cumulativePerpetualFill }}</strong></div
          >
          <div
            ><span>现货累计成交</span><strong>{{ item.cumulativeSpotFill }}</strong></div
          >
          <div
            ><span>已对冲数量</span><strong>{{ item.hedgedQuantity }}</strong></div
          >
          <div
            ><span>残余数量</span><strong>{{ item.residualQuantity }}</strong></div
          >
          <div
            ><span>资金费</span><strong>{{ item.fundingFees ?? '尚无数据' }}</strong></div
          >
          <div
            ><span>手续费</span><strong>{{ item.fees ?? '尚无数据' }}</strong></div
          >
          <div
            ><span>asOf</span><strong>{{ item.asOf }}</strong></div
          >
          <div
            ><span>执行状态</span
            ><strong>{{ item.workspaceState?.executionState ?? item.status }}</strong></div
          >
        </div>
      </article>
    </div>

    <div v-if="context" class="meta-strip">
      <span>现货 step {{ context.quantityStep?.spot }}</span>
      <span>永续 step {{ context.quantityStep?.perpetual }}</span>
      <span>现货 min {{ context.minimumQuantity?.spot }}</span>
      <span>永续 min {{ context.minimumQuantity?.perpetual }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    context: Record<string, any> | null;
    positionGroups: Array<Record<string, any>>;
  }>();
</script>

<style scoped lang="less">
  .funding-chart-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .group-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .group-card {
    padding: 14px;
    border-radius: 12px;
    background: rgb(12 18 35 / 72%);
  }

  .group-card header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .group-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
  }

  .group-grid div,
  .meta-strip span {
    display: flex;
    flex-direction: column;
    gap: 4px;
    color: var(--strategy-text-2);
  }

  .meta-strip {
    display: flex;
    gap: 18px;
    flex-wrap: wrap;
  }

  .state-text {
    color: var(--strategy-text-2);
  }
</style>
