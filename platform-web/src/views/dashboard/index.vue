<template>
  <PageWrapper dense :content-style="{ overflow: 'visible' }">
    <main class="home-dashboard">
      <section class="home-hero">
        <div>
          <span class="eyebrow">PLATFORM 0.9.3</span>
          <h1>全球变量金融平台</h1>
          <p>正式首页只展示具有明确Owner、来源和更新时间的数据。</p>
        </div>
      </section>

      <section class="state-grid" aria-label="首页数据状态">
        <ProductNotConfiguredPanel
          title="全球市场概览尚未配置"
          description="首页聚合层没有独立Market Provider Owner。市场研究请进入Hedge Board查看带来源和截至时间的数据。"
          source="not-configured: dashboard-market-aggregate"
        />
        <ProductNotConfiguredPanel
          title="组合总览尚未配置"
          description="首页未注册组合聚合Service。账户与财务事实请进入个人账号、数据和财务页面读取。"
          source="not-configured: dashboard-portfolio-aggregate"
        />
        <ProductNotConfiguredPanel
          title="策略总览尚未配置"
          description="首页未注册策略摘要Owner，不展示静态收益、随机曲线或示例策略结果。"
          source="not-configured: dashboard-strategy-aggregate"
        />
        <ProductNotConfiguredPanel
          title="重要日历尚未配置"
          description="首页未注册日历Provider，不展示硬编码日期、预期值或前值。"
          source="not-configured: dashboard-calendar-provider"
        />
      </section>

      <section class="navigation-panel">
        <h2>正式产品入口</h2>
        <div class="navigation-grid">
          <Button type="primary" @click="goPath('/hedge-board/macro')">研究与Hedge Board</Button>
          <Button @click="goPath('/strategy/platform')">交易平台与Runtime状态</Button>
          <Button @click="goPath('/risk/detail')">风控与监控</Button>
          <Button @click="goPath('/account/index')">个人账号与持仓</Button>
        </div>
      </section>
    </main>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { Button } from 'ant-design-vue';
  import { useRouter } from 'vue-router';
  import { PageWrapper } from '@/components/Page';
  import ProductNotConfiguredPanel from '@/components/ProductDataState/ProductNotConfiguredPanel.vue';

  const router = useRouter();

  function goPath(path: string) {
    router.push(path);
  }
</script>

<style scoped>
  .home-dashboard {
    display: grid;
    gap: 18px;
    padding: 18px;
  }

  .home-hero,
  .navigation-panel {
    padding: 22px;
    border: 1px solid rgba(214, 223, 232, 0.92);
    border-radius: 12px;
    background: #fff;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .eyebrow {
    color: #6c8fb1;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.14em;
  }

  h1,
  h2 {
    margin: 8px 0;
    color: #172126;
  }

  p {
    margin: 0;
    color: #59636e;
  }

  .state-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .navigation-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 16px;
  }

  @media (max-width: 768px) {
    .home-dashboard {
      padding: 12px;
    }

    .state-grid {
      grid-template-columns: 1fr;
    }

    .navigation-grid :deep(.ant-btn) {
      width: 100%;
    }
  }
</style>
