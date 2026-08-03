<template>
  <div class="strategy-management-page">
    <ProductNotConfiguredPanel
      title="策略管理目录尚未配置"
      description="当前没有正式的策略目录Service、Repository或权限写入合同。为避免把测试持仓、隔离身份和静态PnL误认为真实策略事实，本页不展示模拟策略数据。Cross Venue正式Workspace与Runtime事实继续由交易平台页面承载。"
      source="not-configured: strategy-catalog-owner"
    />
  </div>
</template>

<script setup lang="ts">
  import ProductNotConfiguredPanel from '@/components/ProductDataState/ProductNotConfiguredPanel.vue';
</script>

<style scoped>
  .strategy-management-page {
    padding: 16px;
  }

  @media (max-width: 768px) {
    .strategy-management-page {
      padding: 12px;
    }
  }
</style>
