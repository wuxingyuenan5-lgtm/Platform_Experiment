<template>
  <PageWrapper title="金融AI分析">
    <div class="financial-ai-page">
      <ProductNotConfiguredPanel
        title="金融AI分析数据源尚未配置"
        description="当前没有经过合同验证的推理Provider、研究来源或更新时间。为避免把演示案例误认为真实市场结论，正式页面不展示硬编码行情、机构预测或情景概率。"
        source="not-configured: financial-ai-provider"
      />

      <Card :bordered="false" title="启用条件" class="requirements-card">
        <ul>
          <li>明确的Provider Owner与请求超时；</li>
          <li>来源、截至时间、时区、单位和精度合同；</li>
          <li>Provider失败、无效Payload和全部失败时的Unavailable语义；</li>
          <li>不得将Fixture、Seed或静态示例作为正式研究结论。</li>
        </ul>
      </Card>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { Card } from 'ant-design-vue';
  import { PageWrapper } from '@/components/Page';
  import ProductNotConfiguredPanel from '@/components/ProductDataState/ProductNotConfiguredPanel.vue';
</script>

<style scoped>
  .financial-ai-page {
    display: grid;
    gap: 16px;
    padding: 12px 4px 18px;
  }

  .requirements-card {
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .requirements-card ul {
    margin: 0;
    padding-left: 20px;
    color: #59636e;
    line-height: 1.9;
  }
</style>
