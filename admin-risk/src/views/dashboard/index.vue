<template>
  <PageWrapper dense :content-style="{ overflow: 'visible' }">
    <main class="home-dashboard">
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
          </div>
        </section>

        <section class="dashboard-grid" aria-label="首页工作台">
          <article class="dashboard-panel panel-market">
            <header>
              <div>
                <h2>市场脉搏</h2>
                <p>捕捉全球投资机会的温度信号</p>
              </div>
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
              <div>
                <h2>组合概览</h2>
                <p>全局视角掌握资产配置</p>
              </div>
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
              <div>
                <h2>策略概览</h2>
                <p>多策略协同，稳健致远</p>
              </div>
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
              <div>
                <h2>重要日历</h2>
                <p>把握关键事件与市场脉动</p>
              </div>
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
      </div>
    </main>
  </PageWrapper>
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
    --home-page-gutter: clamp(16px, 1.6vw, 30px);
    --home-section-gap: clamp(20px, 1.5vw, 28px);

    min-height: 100%;
    background: linear-gradient(180deg, rgba(247, 250, 252, 0.34), rgba(239, 245, 250, 0.98) 62%),
      #f4f8fb;
  }

  .home-dashboard__frame {
    width: min(100%, 1840px);
    margin: 0 auto;
    padding: 0 var(--home-page-gutter) clamp(28px, 3vw, 48px);
  }

  .home-hero {
    min-height: clamp(500px, 37vw, 620px);
    padding: clamp(58px, 5.8vw, 96px) clamp(34px, 4vw, 70px);
    display: grid;
    grid-template-columns: minmax(0, 1.2fr) minmax(420px, 0.8fr);
    gap: clamp(28px, 3vw, 52px);
    align-items: center;
    overflow: hidden;
    border-radius: 0 0 30px 30px;
    background: url('@/assets/images/home-butterfly-topology.png') center center / cover no-repeat;
    box-shadow: 0 24px 60px rgba(156, 174, 195, 0.16);
  }

  .home-hero__copy {
    min-width: 0;
    max-width: 650px;
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
    min-width: 0;
    align-self: stretch;
    display: grid;
    grid-template-rows: repeat(2, minmax(0, 1fr));
    gap: clamp(16px, 1.4vw, 24px);
  }

  .hero-side,
  .dashboard-panel {
    min-width: 0;
    border: 1px solid rgba(232, 237, 243, 0.95);
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.76);
    box-shadow: 0 20px 50px rgba(136, 158, 184, 0.13);
    backdrop-filter: blur(18px);
  }

  .hero-side {
    padding: clamp(22px, 1.8vw, 30px);
    display: flex;
    flex-direction: column;
  }

  .hero-side header,
  .dashboard-panel header {
    min-width: 0;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
  }

  .hero-side header > div,
  .dashboard-panel header > div {
    min-width: 0;
  }

  .hero-side header strong,
  .dashboard-panel h2 {
    margin: 0;
    color: #1b2a38;
    font-size: clamp(20px, 1.45vw, 24px);
    font-weight: 600;
  }

  .hero-side header span,
  .dashboard-panel p {
    display: block;
    margin: 7px 0 0;
    color: #8592a3;
    font-size: 14px;
    line-height: 1.6;
  }

  .market-mini-grid {
    margin-top: clamp(20px, 1.6vw, 28px);
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: clamp(12px, 1vw, 18px);
  }

  .market-mini-grid article {
    min-width: 0;
    display: grid;
    gap: 9px;
  }

  .market-mini-grid span {
    overflow: hidden;
    color: #6d7b8a;
    font-size: 13px;
    font-weight: 600;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .market-mini-grid svg {
    width: min(100%, 76px);
    height: 22px;
  }

  .market-mini-grid strong {
    color: #1d2d3b;
    font-size: 17px;
  }

  .portfolio-summary {
    flex: 1;
    margin-top: 18px;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr)) 100px;
    align-items: center;
    gap: clamp(14px, 1.2vw, 20px);
  }

  .portfolio-summary > div:not(.portfolio-ring) {
    min-width: 0;
  }

  .portfolio-summary span {
    color: #7c8998;
    font-size: 14px;
  }

  .portfolio-summary strong {
    display: block;
    margin-top: 12px;
    overflow: hidden;
    color: #1d2d3b;
    font-size: clamp(20px, 1.45vw, 25px);
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .portfolio-ring,
  .allocation-ring {
    position: relative;
    flex: none;
    border-radius: 50%;
    background: conic-gradient(#dec49a 0 31%, #8fb2d8 31% 51%, #dce4ec 51% 73%, #f1e4c9 73% 100%);
  }

  .portfolio-ring {
    width: 100px;
    height: 100px;
    justify-self: end;
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
    margin-top: var(--home-section-gap);
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: var(--home-section-gap);
    align-items: stretch;
  }

  .dashboard-panel {
    min-height: 440px;
    padding: clamp(24px, 2vw, 34px);
    display: flex;
    flex-direction: column;
  }

  .pulse-tabs {
    margin: 26px 0 18px;
    display: flex;
    gap: clamp(18px, 2vw, 30px);
    overflow-x: auto;
    scrollbar-width: none;
  }

  .pulse-tabs::-webkit-scrollbar {
    display: none;
  }

  .pulse-tabs button {
    position: relative;
    flex: none;
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
    right: 0;
    bottom: 0;
    left: 0;
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
    min-width: 0;
    display: grid;
    grid-template-columns: 42px minmax(0, 1fr) minmax(64px, 84px) 26px;
    align-items: center;
    gap: 14px;
    padding: 8px;
    border: none;
    border-radius: 12px;
    background: transparent;
    text-align: left;
    cursor: pointer;
    transition: background-color 160ms ease;
  }

  .strategy-row {
    grid-template-columns: 44px minmax(0, 1fr) minmax(70px, 90px);
  }

  .pulse-row:hover,
  .strategy-row:hover {
    background: rgba(244, 247, 250, 0.9);
  }

  .pulse-row:focus-visible,
  .strategy-row:focus-visible,
  .panel-link:focus-visible,
  .pulse-tabs button:focus-visible {
    outline: 2px solid rgba(31, 85, 85, 0.32);
    outline-offset: 3px;
  }

  .pulse-row svg,
  .strategy-row svg {
    width: 100%;
    min-width: 0;
    height: 22px;
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

  .row-copy strong,
  .row-copy em {
    display: block;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .row-copy strong {
    color: #203140;
    font-size: 16px;
    font-weight: 600;
  }

  .row-copy em,
  .row-value {
    margin-top: 5px;
    color: #8a97a6;
    font-size: 14px;
    font-style: normal;
  }

  .row-value {
    display: block;
  }

  .allocation-content {
    margin-top: 30px;
    display: grid;
    grid-template-columns: minmax(130px, 150px) minmax(0, 1fr);
    gap: clamp(22px, 2vw, 34px);
    align-items: center;
  }

  .allocation-ring {
    width: min(100%, 150px);
    aspect-ratio: 1;
  }

  .allocation-legend {
    min-width: 0;
    display: grid;
    gap: 14px;
  }

  .allocation-legend div {
    min-width: 0;
    display: grid;
    grid-template-columns: 10px minmax(0, 1fr) auto;
    gap: 10px;
    align-items: center;
    color: #788695;
    font-size: 14px;
  }

  .allocation-legend i {
    width: 10px;
    height: 10px;
    border-radius: 50%;
  }

  .allocation-legend span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .risk-metrics {
    margin-top: 28px;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px 24px;
  }

  .risk-metrics article {
    min-width: 0;
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
    margin: 24px 0 18px;
    padding-bottom: 18px;
    display: grid;
    grid-template-columns: 26px minmax(0, 1fr) auto 26px;
    gap: 14px;
    align-items: center;
    border-bottom: 1px solid rgba(231, 236, 242, 0.95);
    color: #c09152;
  }

  .calendar-strip strong {
    min-width: 0;
    justify-self: center;
    overflow: hidden;
    color: #243443;
    font-size: 16px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .calendar-strip span {
    color: #647384;
    font-size: 14px;
  }

  .calendar-list article {
    min-width: 0;
    display: grid;
    grid-template-columns: 78px 52px minmax(0, 1fr) 68px;
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
    flex: none;
    border-radius: 50%;
    background: #c09152;
  }

  .calendar-list strong,
  .calendar-list p,
  .calendar-list em {
    min-width: 0;
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

  .calendar-list p {
    overflow-wrap: anywhere;
  }

  .calendar-list em {
    color: #9aa5b2;
    text-align: right;
  }

  .panel-link {
    margin-top: auto;
    padding: 24px 0 0;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    align-self: flex-start;
    border: none;
    background: transparent;
    color: #c09152;
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
  }

  @media (max-width: 1599px) {
    .home-hero {
      min-height: auto;
      grid-template-columns: minmax(0, 1fr);
      align-items: start;
    }

    .home-hero__copy {
      max-width: 720px;
      padding: clamp(10px, 1.5vw, 24px) 0;
    }

    .home-hero__summaries {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      grid-template-rows: none;
    }
  }

  @media (max-width: 1399px) {
    .dashboard-panel {
      min-height: 420px;
      padding: 24px;
    }

    .pulse-row,
    .strategy-row {
      gap: 11px;
    }

    .calendar-list article {
      grid-template-columns: 72px 48px minmax(0, 1fr) 64px;
      gap: 8px;
    }
  }

  @media (max-width: 1199px) {
    .home-hero {
      padding: 48px 28px 32px;
    }

    .home-hero__summaries {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 1079px) {
    .dashboard-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 760px) {
    .home-dashboard__frame {
      padding-right: 14px;
      padding-left: 14px;
    }

    .home-hero {
      padding: 40px 20px 24px;
      border-radius: 0 0 22px 22px;
    }

    .hero-side,
    .dashboard-panel {
      border-radius: 18px;
    }

    .market-mini-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .portfolio-summary {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .portfolio-ring {
      grid-column: 1 / -1;
      justify-self: start;
    }

    .pulse-row {
      grid-template-columns: 42px minmax(0, 1fr) 26px;
    }

    .pulse-row svg {
      display: none;
    }

    .strategy-row {
      grid-template-columns: 44px minmax(0, 1fr);
    }

    .strategy-row svg {
      display: none;
    }

    .allocation-content {
      grid-template-columns: minmax(110px, 130px) minmax(0, 1fr);
    }

    .calendar-list article {
      grid-template-columns: 76px minmax(0, 1fr);
      gap: 6px 12px;
    }

    .calendar-list p {
      grid-column: 2;
    }

    .calendar-list em {
      grid-column: 2;
      text-align: left;
    }
  }
</style>
