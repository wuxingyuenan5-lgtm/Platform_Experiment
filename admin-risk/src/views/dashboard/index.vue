<template>
  <PageWrapper dense>
    <main class="home-dashboard">
      <section class="home-hero">
        <div class="home-hero__copy">
          <span>欢迎来到</span>
          <h1>全球变量</h1>
          <p>顺应时代大势，洞悉投资先机</p>
        </div>

        <aside class="hero-side hero-side--market">
          <header>
            <div>
              <strong>全球市场概览</strong>
              <span>更新于 18:02 UTC+8</span>
            </div>
            <RightOutlined />
          </header>

          <div class="market-mini-grid">
            <article v-for="item in marketOverviewItems" :key="item.label">
              <span>{{ item.label }}</span>
              <svg viewBox="0 0 78 22" preserveAspectRatio="none">
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
            <div class="portfolio-ring"></div>
          </div>
        </aside>
      </section>

      <section class="dashboard-grid" aria-label="首页工作台">
        <article class="dashboard-panel panel-market">
          <header>
            <h2>市场脉搏</h2>
            <p>捕捉全球投资机会的温度信号</p>
          </header>

          <div class="pulse-tabs">
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
              <span class="row-icon"><component :is="item.icon" /></span>
              <span class="row-copy">
                <strong>{{ item.title }}</strong>
                <em>{{ item.desc }}</em>
              </span>
              <svg viewBox="0 0 82 22" preserveAspectRatio="none">
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
          <header>
            <h2>组合概览</h2>
            <p>全局视角掌握资产配置</p>
          </header>

          <div class="allocation-content">
            <div class="allocation-ring"></div>
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
          <header>
            <h2>策略概览</h2>
            <p>多策略协同，稳健致远</p>
          </header>

          <div class="strategy-list">
            <button
              v-for="item in strategyRows"
              :key="item.title"
              type="button"
              class="strategy-row"
              @click="goPath(item.path)"
            >
              <span class="row-icon"><component :is="item.icon" /></span>
              <span class="row-copy">
                <strong>{{ item.title }}</strong>
                <em>--（--）</em>
              </span>
              <svg viewBox="0 0 82 22" preserveAspectRatio="none">
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
          <header>
            <h2>重要日历</h2>
            <p>把握关键事件与市场脉动</p>
          </header>

          <div class="calendar-strip">
            <LeftOutlined />
            <strong>2026年07月17日</strong>
            <span>星期五</span>
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
    </main>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { useRouter } from 'vue-router';
  import {
    CalendarOutlined,
    ClusterOutlined,
    DatabaseOutlined,
    DeploymentUnitOutlined,
    FundProjectionScreenOutlined,
    LeftOutlined,
    LineChartOutlined,
    RightOutlined,
  } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';

  const router = useRouter();

  const marketOverviewItems = [
    { label: '全球股票', color: '#d59b42', spark: '0,15 12,11 24,14 36,8 48,13 60,9 72,12 78,7' },
    { label: '大宗商品', color: '#6ca6ee', spark: '0,12 12,9 24,14 36,6 48,13 60,8 72,13 78,9' },
    { label: '美元指数', color: '#d59b42', spark: '0,13 12,10 24,12 36,9 48,13 60,10 72,12 78,9' },
    { label: '风险收益比', color: '#b6c0ca', spark: '0,12 12,10 24,11 36,8 48,10 60,9 72,10 78,8' },
  ];

  const pulseRows = [
    {
      title: 'AI + 生产力',
      desc: '科技成长驱动新周期',
      path: '/hedge-board/us',
      color: '#d59b42',
      spark: '0,15 12,12 24,13 36,9 48,11 60,8 72,10 82,7',
      icon: DatabaseOutlined,
    },
    {
      title: 'Breakevens vs Gold',
      desc: '通胀对冲与黄金趋势',
      path: '/hedge-board/gold',
      color: '#6ca6ee',
      spark: '0,13 12,15 24,10 36,16 48,11 60,14 72,10 82,13',
      icon: FundProjectionScreenOutlined,
    },
    {
      title: 'DXY vs US10Y',
      desc: '美元利率与收益率联动',
      path: '/hedge-board/macro',
      color: '#b6c0ca',
      spark: '0,11 12,10 24,12 36,10 48,11 60,9 72,10 82,8',
      icon: LineChartOutlined,
    },
  ];

  const allocationLegend = [
    { label: '权益类', color: '#dfc89e' },
    { label: '固收类', color: '#8fb2d8' },
    { label: '大宗商品', color: '#eee0c7' },
    { label: '加密资产', color: '#c9cdd3' },
    { label: '现金及其他', color: '#e9edf2' },
  ];

  const allocationStats = ['组合波动率（年化）', '最大回撤', '夏普比率', 'VaR（95%）'];

  const strategyRows = [
    {
      title: '宏观对冲策略',
      path: '/strategy/management',
      color: '#d59b42',
      spark: '0,15 12,11 24,14 36,9 48,13 60,8 72,12 82,9',
      icon: FundProjectionScreenOutlined,
    },
    {
      title: '跨资产配置策略',
      path: '/strategy/management',
      color: '#6ca6ee',
      spark: '0,12 12,14 24,10 36,16 48,11 60,15 72,10 82,13',
      icon: ClusterOutlined,
    },
    {
      title: '事件驱动策略',
      path: '/strategy/management',
      color: '#b6c0ca',
      spark: '0,10 12,11 24,9 36,11 48,10 60,9 72,10 82,9',
      icon: CalendarOutlined,
    },
  ];

  const calendarRows = [
    { time: '09:30', region: '中国', title: '规模以上工业增加值' },
    { time: '17:00', region: '欧元区', title: 'CPI 终值（同比）' },
    { time: '20:30', region: '美国', title: '零售销售月率' },
    { time: '22:00', region: '美国', title: '密歇根大学消费者信心指数初值' },
  ];

  function goPath(path: string) {
    router.push(path);
  }
</script>

<style scoped lang="less">
  .home-dashboard {
    min-height: calc(100vh - 64px);
    padding: 0 26px 34px;
    background:
      linear-gradient(180deg, rgba(247, 250, 252, 0.3), rgba(239, 245, 250, 0.96) 58%),
      #f4f8fb;
  }

  .home-hero {
    position: relative;
    min-height: 560px;
    padding: 88px 58px 86px;
    display: grid;
    grid-template-columns: minmax(0, 1fr) 390px;
    grid-template-rows: repeat(2, minmax(0, 1fr));
    gap: 26px;
    overflow: hidden;
    border-radius: 0 0 30px 30px;
    background: url('@/assets/images/home-butterfly-topology.png') center center / cover no-repeat;
    box-shadow: 0 24px 60px rgba(156, 174, 195, 0.16);
  }

  .home-hero::before {
    display: none;
  }

  .home-hero::after {
    display: none;
  }

  .home-hero__copy {
    position: relative;
    z-index: 1;
    max-width: 520px;
    grid-row: 1 / 3;
    align-self: center;
  }

  .home-hero__copy span {
    display: block;
    margin-bottom: 14px;
    color: #3e4b56;
    font-size: 18px;
    font-weight: 600;
  }

  .home-hero__copy h1 {
    margin: 0;
    color: #182633;
    font-family: 'Noto Serif SC', 'Songti SC', 'SimSun', serif;
    font-size: 60px;
    font-weight: 600;
    line-height: 1.06;
    letter-spacing: 0;
    text-shadow: 0 8px 22px rgba(255, 255, 255, 0.72);
  }

  .home-hero__copy p {
    margin: 20px 0 0;
    color: #43525f;
    font-size: 21px;
    font-weight: 500;
  }

  .hero-side,
  .dashboard-panel {
    border: 1px solid rgba(232, 237, 243, 0.95);
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.72);
    box-shadow: 0 20px 50px rgba(136, 158, 184, 0.13);
    backdrop-filter: blur(18px);
  }

  .hero-side {
    position: relative;
    z-index: 2;
    padding: 26px 28px;
  }

  .hero-side--market {
    grid-column: 2;
    grid-row: 1;
  }

  .hero-side--portfolio {
    grid-column: 2;
    grid-row: 2;
  }

  .hero-side header,
  .dashboard-panel header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
  }

  .hero-side header strong,
  .dashboard-panel h2 {
    margin: 0;
    color: #1b2a38;
    font-size: 23px;
    font-weight: 600;
  }

  .hero-side header span,
  .dashboard-panel p {
    display: block;
    margin: 7px 0 0;
    color: #8592a3;
    font-size: 15px;
    line-height: 1.6;
  }

  .market-mini-grid {
    margin-top: 26px;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
  }

  .market-mini-grid article {
    display: grid;
    gap: 10px;
  }

  .market-mini-grid span {
    color: #6d7b8a;
    font-size: 14px;
    font-weight: 600;
  }

  .market-mini-grid svg {
    width: 76px;
    height: 22px;
  }

  .market-mini-grid strong {
    color: #1d2d3b;
    font-size: 17px;
  }

  .portfolio-summary {
    height: calc(100% - 32px);
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 106px;
    align-items: center;
    gap: 18px;
  }

  .portfolio-summary span {
    color: #7c8998;
    font-size: 15px;
  }

  .portfolio-summary strong {
    display: block;
    margin-top: 14px;
    color: #1d2d3b;
    font-size: 24px;
  }

  .portfolio-ring,
  .allocation-ring {
    border-radius: 50%;
    background: conic-gradient(#dec49a 0 31%, #8fb2d8 31% 51%, #dce4ec 51% 73%, #f1e4c9 73% 100%);
    position: relative;
  }

  .portfolio-ring {
    width: 106px;
    height: 106px;
  }

  .portfolio-ring::after,
  .allocation-ring::after {
    content: '';
    position: absolute;
    inset: 24%;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.96);
  }

  .dashboard-grid {
    position: relative;
    z-index: 3;
    margin-top: -46px;
    display: grid;
    grid-template-columns: minmax(280px, 0.95fr) minmax(280px, 1.05fr) minmax(320px, 1.1fr) minmax(320px, 1.18fr);
    gap: 24px;
  }

  .dashboard-panel {
    min-height: 500px;
    padding: 30px 32px 26px;
    display: flex;
    flex-direction: column;
  }

  .pulse-tabs {
    margin: 28px 0 18px;
    display: flex;
    gap: 28px;
  }

  .pulse-tabs button {
    position: relative;
    padding: 0 0 10px;
    border: none;
    background: transparent;
    color: #768392;
    font-size: 15px;
    font-weight: 500;
    cursor: pointer;
  }

  .pulse-tabs button.is-active {
    color: #1d2d3b;
  }

  .pulse-tabs button.is-active::after {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 2px;
    border-radius: 999px;
    background: #c09152;
  }

  .pulse-list,
  .strategy-list,
  .calendar-list {
    display: grid;
    gap: 18px;
  }

  .pulse-row,
  .strategy-row {
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr) 84px 26px;
    align-items: center;
    gap: 14px;
    padding: 0;
    border: none;
    background: transparent;
    text-align: left;
    cursor: pointer;
  }

  .strategy-row {
    grid-template-columns: 44px minmax(0, 1fr) 90px;
  }

  .row-icon {
    width: 42px;
    height: 42px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: #f4f7fa;
    color: #c09152;
    font-size: 20px;
  }

  .row-copy {
    min-width: 0;
  }

  .row-copy strong {
    display: block;
    color: #203140;
    font-size: 17px;
    font-weight: 600;
  }

  .row-copy em,
  .row-value {
    display: block;
    margin-top: 5px;
    color: #8a97a6;
    font-size: 14px;
    font-style: normal;
  }

  .allocation-content {
    margin-top: 34px;
    display: grid;
    grid-template-columns: 150px minmax(0, 1fr);
    gap: 28px;
    align-items: center;
  }

  .allocation-ring {
    width: 150px;
    height: 150px;
  }

  .allocation-legend {
    display: grid;
    gap: 14px;
  }

  .allocation-legend div {
    display: grid;
    grid-template-columns: 10px minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    color: #788695;
    font-size: 15px;
  }

  .allocation-legend i {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .risk-metrics {
    margin-top: 30px;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 20px 26px;
  }

  .risk-metrics article {
    display: grid;
    gap: 8px;
  }

  .risk-metrics span {
    color: #8a97a6;
    font-size: 14px;
  }

  .risk-metrics strong {
    color: #1d2d3b;
    font-size: 19px;
  }

  .calendar-strip {
    margin: 26px 0 18px;
    padding-bottom: 18px;
    display: grid;
    grid-template-columns: 26px minmax(0, 1fr) auto 26px;
    gap: 14px;
    align-items: center;
    border-bottom: 1px solid rgba(231, 236, 242, 0.95);
    color: #c09152;
  }

  .calendar-strip strong {
    justify-self: center;
    color: #243443;
    font-size: 17px;
  }

  .calendar-strip span {
    color: #647384;
    font-size: 15px;
  }

  .calendar-list article {
    display: grid;
    grid-template-columns: 82px 54px minmax(0, 1fr) 70px;
    gap: 10px;
    align-items: start;
  }

  .calendar-time {
    display: flex;
    align-items: center;
    gap: 9px;
    color: #697889;
    font-size: 14px;
  }

  .calendar-time i {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #c09152;
  }

  .calendar-list strong,
  .calendar-list p,
  .calendar-list em {
    margin: 0;
    color: #5d6c7d;
    font-size: 14px;
    font-style: normal;
    line-height: 1.55;
  }

  .calendar-list strong {
    color: #263847;
    font-weight: 600;
  }

  .calendar-list em {
    color: #9aa5b2;
    text-align: right;
  }

  .panel-link {
    margin-top: auto;
    padding: 0;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    align-self: flex-start;
    border: none;
    background: transparent;
    color: #c09152;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
  }

  @media (max-width: 1500px) {
    .home-hero {
      grid-template-columns: 1fr;
      grid-template-rows: auto;
    }

    .dashboard-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 900px) {
    .home-dashboard {
      padding: 0 14px 24px;
    }

    .home-hero {
      padding: 46px 24px 28px;
    }

    .home-hero__copy h1 {
      font-size: 48px;
    }

    .portfolio-summary,
    .dashboard-grid,
    .allocation-content {
      grid-template-columns: 1fr;
    }

    .market-mini-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
