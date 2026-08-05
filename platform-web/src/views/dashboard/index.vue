<template>
  <RestoredProductSurface
    :state="dashboardSampleMeta.state"
    :source="dashboardSampleMeta.source"
    :as-of="dashboardSampleMeta.asOf"
    :actionable="dashboardSampleMeta.actionable"
    message="原首页产品结构已按参考提交选择性恢复；当前数值为明确标识的非实时样例。"
  >
    <PageWrapper dense :content-style="{ overflow: 'visible' }">
      <main
        class="home-dashboard"
        data-testid="dashboard-original-structure"
        aria-label="全球变量首页"
      >
        <div class="home-dashboard__frame">
          <section class="home-hero">
            <div class="home-hero__copy">
              <span>欢迎来到</span>
              <h1>全球变量</h1>
              <p>顺应时代大势，洞悉投资先机</p>
            </div>

            <div class="home-hero__summaries">
              <aside class="hero-side hero-side--market">
                <header>
                  <div>
                    <strong>全球市场概览</strong>
                    <span>非实时样例</span>
                  </div>
                  <RightOutlined />
                </header>

                <div class="market-mini-grid">
                  <article v-for="item in marketOverviewItems" :key="item.label">
                    <span>{{ item.label }}</span>
                    <svg viewBox="0 0 78 22" preserveAspectRatio="none" aria-hidden="true">
                      <polyline
                        :points="item.spark"
                        fill="none"
                        :stroke="item.color"
                        stroke-width="2.2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      />
                    </svg>
                    <strong>--</strong>
                  </article>
                </div>
              </aside>

              <aside class="hero-side hero-side--portfolio">
                <header>
                  <strong>投资组合总览</strong>
                  <RightOutlined />
                </header>

                <div class="portfolio-summary">
                  <div>
                    <span>总资产（估值）</span>
                    <strong>--</strong>
                  </div>
                  <div>
                    <span>今日收益</span>
                    <strong>--（--）</strong>
                  </div>
                  <div class="portfolio-ring" aria-label="组合配置样例图"></div>
                </div>
              </aside>
            </div>
          </section>

          <section class="dashboard-grid" aria-label="首页工作台">
            <article class="dashboard-panel panel-market">
              <header><h2>市场脉搏</h2></header>
              <div class="pulse-tabs" aria-label="市场脉搏视角">
                <button type="button" class="is-active">增长主线</button>
                <button type="button">资产传导</button>
                <button type="button">资金流向</button>
              </div>

              <div class="pulse-list">
                <button
                  v-for="item in pulseRows"
                  :key="item.title"
                  type="button"
                  class="pulse-row"
                  @click="goPath(item.path)"
                >
                  <span class="row-icon"><component :is="iconMap[item.icon]" /></span>
                  <span class="row-copy"><strong>{{ item.title }}</strong></span>
                  <svg viewBox="0 0 82 22" preserveAspectRatio="none" aria-hidden="true">
                    <polyline
                      :points="item.spark"
                      fill="none"
                      :stroke="item.color"
                      stroke-width="2.2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                  <span class="row-value">--</span>
                </button>
              </div>

              <button class="panel-link" type="button" @click="goPath('/hedge-board/macro')">
                查看全部市场分析
                <RightOutlined />
              </button>
            </article>

            <article class="dashboard-panel panel-portfolio">
              <header><h2>组合概览</h2></header>
              <div class="allocation-content">
                <div class="allocation-ring" aria-label="资产配置样例图"></div>
                <div class="allocation-legend">
                  <div v-for="item in allocationLegend" :key="item.label">
                    <i :style="{ background: item.color }"></i>
                    <span>{{ item.label }}</span>
                    <strong>--</strong>
                  </div>
                </div>
              </div>

              <div class="risk-metrics">
                <article v-for="item in allocationStats" :key="item">
                  <span>{{ item }}</span>
                  <strong>--</strong>
                </article>
              </div>

              <button class="panel-link" type="button" @click="goPath('/strategy/management')">
                查看组合详情
                <RightOutlined />
              </button>
            </article>

            <article class="dashboard-panel panel-strategy">
              <header><h2>策略概览</h2></header>
              <div class="strategy-list">
                <button
                  v-for="item in strategyRows"
                  :key="item.title"
                  type="button"
                  class="strategy-row"
                  @click="goPath(item.path)"
                >
                  <span class="row-icon"><component :is="iconMap[item.icon]" /></span>
                  <span class="row-copy">
                    <strong>{{ item.title }}</strong>
                    <em>--（--）</em>
                  </span>
                  <svg viewBox="0 0 82 22" preserveAspectRatio="none" aria-hidden="true">
                    <polyline
                      :points="item.spark"
                      fill="none"
                      :stroke="item.color"
                      stroke-width="2.2"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                    />
                  </svg>
                </button>
              </div>

              <button class="panel-link" type="button" @click="goPath('/strategy/index')">
                查看所有策略
                <RightOutlined />
              </button>
            </article>

            <article class="dashboard-panel panel-calendar">
              <header><h2>重要日历</h2></header>
              <div class="calendar-strip">
                <LeftOutlined />
                <strong>非实时日历样例</strong>
                <span>Sample</span>
                <RightOutlined />
              </div>

              <div class="calendar-list">
                <article v-for="item in calendarRows" :key="`${item.time}-${item.title}`">
                  <span class="calendar-time"><i></i>{{ item.time }}</span>
                  <strong>{{ item.region }}</strong>
                  <p>{{ item.title }}</p>
                  <em>预期：--<br />前值：--</em>
                </article>
              </div>

              <button class="panel-link" type="button" @click="goPath('/news-calendar/macro')">
                查看完整日历
                <RightOutlined />
              </button>
            </article>
          </section>
        </div>
      </main>
    </PageWrapper>
  </RestoredProductSurface>
</template>

<script setup lang="ts">
  import { useRouter } from 'vue-router';
  import {
    CalendarOutlined,
    ClusterOutlined,
    DatabaseOutlined,
    FundProjectionScreenOutlined,
    LeftOutlined,
    LineChartOutlined,
    RightOutlined,
  } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import {
    allocationLegend,
    allocationStats,
    calendarRows,
    dashboardSampleMeta,
    marketOverviewItems,
    pulseRows,
    strategyRows,
  } from '@/data/sample/dashboard';

  const router = useRouter();
  const iconMap = {
    calendar: CalendarOutlined,
    cluster: ClusterOutlined,
    database: DatabaseOutlined,
    line: LineChartOutlined,
    projection: FundProjectionScreenOutlined,
  } as const;

  function goPath(path: string) {
    router.push(path);
  }
</script>

<style scoped lang="less">
  .home-dashboard {
    --home-page-gutter: clamp(18px, 2vw, 42px);

    min-height: 100%;
    color: #1b2a38;
    background: linear-gradient(180deg, rgba(247, 250, 252, 0.34), #eff5fa 62%);
  }

  .home-dashboard__frame {
    width: 100%;
    padding-bottom: clamp(28px, 3vw, 48px);
  }

  .home-hero {
    min-height: clamp(480px, 41vw, 680px);
    padding: clamp(58px, 5vw, 92px) var(--home-page-gutter) clamp(44px, 4vw, 72px);
    display: grid;
    grid-template-columns: minmax(0, 1.42fr) minmax(380px, 0.58fr);
    gap: clamp(28px, 4vw, 72px);
    align-items: start;
    overflow: hidden;
    background: url('@/assets/images/home-hero-generated-20260726.png') center / cover no-repeat;
    box-shadow: 0 24px 60px rgba(156, 174, 195, 0.16);
  }

  .home-hero__copy {
    max-width: 620px;
    padding-top: clamp(10px, 2.6vw, 46px);
  }

  .home-hero__copy span {
    display: block;
    margin-bottom: 14px;
    color: #3e4b56;
    font-size: clamp(16px, 1.2vw, 19px);
    font-weight: 600;
  }

  .home-hero__copy h1 {
    margin: 0;
    color: #182633;
    font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', serif;
    font-size: clamp(50px, 4.2vw, 72px);
    font-weight: 600;
    line-height: 1.06;
    text-shadow: 0 8px 22px rgba(255, 255, 255, 0.72);
  }

  .home-hero__copy p {
    margin: 20px 0 0;
    color: #43525f;
    font-size: clamp(18px, 1.45vw, 23px);
    font-weight: 500;
  }

  .home-hero__summaries {
    display: grid;
    gap: 18px;
  }

  .hero-side,
  .dashboard-panel {
    min-width: 0;
    border: 1px solid rgba(232, 237, 243, 0.95);
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.82);
    box-shadow: 0 20px 50px rgba(136, 158, 184, 0.13);
    backdrop-filter: blur(18px);
  }

  .hero-side {
    padding: 24px;
  }

  .hero-side header,
  .dashboard-panel header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }

  .hero-side header div {
    display: grid;
    gap: 4px;
  }

  .hero-side header span {
    color: #84909c;
    font-size: 12px;
  }

  .market-mini-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
    margin-top: 22px;
  }

  .market-mini-grid article {
    display: grid;
    grid-template-columns: 1fr 70px auto;
    align-items: center;
    gap: 8px;
    font-size: 12px;
  }

  .market-mini-grid svg,
  .pulse-row svg,
  .strategy-row svg {
    width: 100%;
    height: 22px;
  }

  .portfolio-summary {
    display: grid;
    grid-template-columns: 1fr 1fr 92px;
    align-items: center;
    gap: 18px;
    margin-top: 22px;
  }

  .portfolio-summary > div:not(.portfolio-ring) {
    display: grid;
    gap: 8px;
  }

  .portfolio-summary span {
    color: #71808e;
    font-size: 12px;
  }

  .portfolio-ring,
  .allocation-ring {
    aspect-ratio: 1;
    border-radius: 50%;
    background: conic-gradient(#d9b576 0 32%, #8fb2d8 32% 55%, #d9dee5 55% 78%, #eee0c7 78%);
    box-shadow: inset 0 0 0 15px rgba(255, 255, 255, 0.88);
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 20px;
    padding: 22px var(--home-page-gutter) 0;
  }

  .dashboard-panel {
    display: grid;
    gap: 16px;
    padding: 24px;
  }

  .dashboard-panel h2 {
    margin: 0;
    font-size: 21px;
  }

  .pulse-tabs {
    display: flex;
    gap: 8px;
  }

  .pulse-tabs button,
  .panel-link {
    border: 0;
    background: transparent;
    cursor: pointer;
  }

  .pulse-tabs button {
    padding: 7px 12px;
    border-radius: 999px;
    color: #73808d;
  }

  .pulse-tabs button.is-active {
    background: #eef3f8;
    color: #233d56;
    font-weight: 700;
  }

  .pulse-list,
  .strategy-list,
  .calendar-list {
    display: grid;
    gap: 8px;
  }

  .pulse-row,
  .strategy-row {
    display: grid;
    grid-template-columns: 36px minmax(110px, 1fr) 82px auto;
    align-items: center;
    gap: 12px;
    padding: 12px 0;
    border: 0;
    border-bottom: 1px solid #edf1f5;
    background: transparent;
    color: inherit;
    text-align: left;
    cursor: pointer;
  }

  .row-icon {
    display: grid;
    width: 34px;
    height: 34px;
    place-items: center;
    border-radius: 10px;
    background: #edf3f8;
    color: #526f8a;
  }

  .row-copy {
    display: grid;
    gap: 4px;
  }

  .row-copy em {
    color: #8a96a2;
    font-size: 12px;
    font-style: normal;
  }

  .panel-link {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 6px;
    color: #45647f;
    font-weight: 700;
  }

  .allocation-content {
    display: grid;
    grid-template-columns: 150px 1fr;
    align-items: center;
    gap: 24px;
  }

  .allocation-legend {
    display: grid;
    gap: 10px;
  }

  .allocation-legend div {
    display: grid;
    grid-template-columns: 10px 1fr auto;
    align-items: center;
    gap: 8px;
  }

  .allocation-legend i {
    width: 9px;
    height: 9px;
    border-radius: 50%;
  }

  .risk-metrics {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .risk-metrics article {
    display: flex;
    justify-content: space-between;
    padding: 10px 12px;
    border-radius: 10px;
    background: #f7f9fb;
  }

  .calendar-strip {
    display: grid;
    grid-template-columns: auto 1fr auto auto;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border-radius: 10px;
    background: #f4f7fa;
  }

  .calendar-list article {
    display: grid;
    grid-template-columns: 70px 56px 1fr auto;
    align-items: center;
    gap: 10px;
    padding: 10px 0;
    border-bottom: 1px solid #edf1f5;
  }

  .calendar-list p,
  .calendar-list em {
    margin: 0;
  }

  .calendar-list em {
    color: #85919c;
    font-size: 12px;
    font-style: normal;
    text-align: right;
  }

  .calendar-time {
    color: #47617a;
    font-weight: 700;
  }

  @media (max-width: 1024px) {
    .home-hero {
      grid-template-columns: 1fr;
    }

    .home-hero__summaries {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 768px) {
    .home-hero {
      min-height: auto;
      padding-top: 42px;
    }

    .home-hero__summaries,
    .dashboard-grid {
      grid-template-columns: 1fr;
    }

    .portfolio-summary,
    .allocation-content {
      grid-template-columns: 1fr;
    }

    .portfolio-ring,
    .allocation-ring {
      width: 110px;
    }
  }

  @media (max-width: 520px) {
    .market-mini-grid {
      grid-template-columns: 1fr;
    }

    .pulse-row,
    .strategy-row {
      grid-template-columns: 34px 1fr;
    }

    .pulse-row svg,
    .strategy-row svg,
    .row-value {
      display: none;
    }

    .calendar-list article {
      grid-template-columns: 60px 1fr;
    }

    .calendar-list p,
    .calendar-list em {
      grid-column: 2;
      text-align: left;
    }
  }
</style>
