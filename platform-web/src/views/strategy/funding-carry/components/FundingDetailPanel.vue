<template>
  <section class="panel funding-detail-panel">
    <div class="panel-title">
      <h3>共享 UTA / 门控 / 当前指令</h3>
    </div>

    <p v-if="!context" class="state-text">尚未同步 Funding execution context。</p>

    <template v-else>
      <div class="detail-grid">
        <div>
          <span>总可用余额</span>
          <strong>{{ context.availableBalance?.availableBalance ?? '尚无数据' }}</strong>
        </div>
        <div>
          <span>活动预约</span>
          <strong>{{ context.activeReservation?.activeReserved ?? '0' }}</strong>
        </div>
        <div>
          <span>Funding 已预约</span>
          <strong>{{ context.activeReservation?.fundingReserved ?? '0' }}</strong>
        </div>
        <div>
          <span>Cross 已预约</span>
          <strong>{{ context.activeReservation?.crossReserved ?? '0' }}</strong>
        </div>
        <div>
          <span>Live Write</span>
          <strong>{{ context.runtime?.liveWriteEnabled === true ? 'true' : 'false' }}</strong>
        </div>
        <div>
          <span>controlled-live readiness</span>
          <strong>{{
            context.controlledLiveReadiness?.ready === true ? 'ready' : 'blocked'
          }}</strong>
        </div>
      </div>

      <div class="claim-list">
        <strong>共享资源占用</strong>
        <ul v-if="context.sharedResourceClaims?.length">
          <li v-for="item in context.sharedResourceClaims" :key="item.resourceKey">
            {{ item.resourceCategory }} / {{ item.symbol }} / {{ item.ownerType }}
          </li>
        </ul>
        <p v-else class="state-text">当前无活动 claim。</p>
      </div>

      <div v-if="workspace" class="timeline-block">
        <strong>服务端执行状态</strong>
        <ul v-if="workspace.timeline?.length">
          <li v-for="entry in workspace.timeline" :key="`${entry.code}:${entry.at}`">
            {{ entry.code }} · {{ entry.status }} · {{ entry.at }}
          </li>
        </ul>
        <p v-else class="state-text">尚无执行状态。</p>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
  defineProps<{
    context: Record<string, any> | null;
    workspace: Record<string, any> | null;
  }>();
</script>

<style scoped lang="less">
  .funding-detail-panel {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .detail-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .detail-grid div {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 12px;
    border-radius: 12px;
    background: rgb(12 18 35 / 72%);
  }

  .claim-list,
  .timeline-block {
    padding: 12px;
    border-radius: 12px;
    background: rgb(12 18 35 / 72%);
  }

  .state-text {
    color: var(--strategy-text-2);
  }
</style>
