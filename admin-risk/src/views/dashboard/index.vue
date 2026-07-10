<template>
  <PageWrapper dense>
    <div class="dashboard-home">
      <section class="hero-card">
        <div class="hero-card__copy">
          <p class="hero-card__eyebrow">GLOBAL VARIABLES SIGNAL DESK</p>
          <h1>从全球变量新闻里<br />筛出真正会传导到资产价格的信号</h1>
          <p class="hero-card__lead">
            这不是新闻列表，而是基金研究流程里的前置筛选层。先看变量，后看观点；先看传导，后看结论。
          </p>

          <div class="hero-card__actions">
            <button type="button" class="primary" @click="goPath('/hedge-board/macro')">
              开始探索变量信号
            </button>
            <button type="button" class="secondary" @click="goPath('/financial-ai/index')">
              了解 VARIABLE GLOBAL
            </button>
          </div>
        </div>

        <div class="hero-card__art" aria-hidden="true"></div>
      </section>

      <section class="ticker-card">
        <article v-for="item in tickerItems" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <em :class="item.tone">{{ item.change }}</em>
        </article>
      </section>

      <section class="concept-card">
        <div class="concept-card__headline">
          <div>
            <h2>滚动动画概念</h2>
            <p
              >随首页滚动，视觉从“蝴蝶触水”逐步收敛为抽象信号与拓扑图谱，象征信息的提炼与变量的传导。</p
            >
          </div>
        </div>

        <div class="concept-grid">
          <button
            v-for="item in portalCards"
            :key="item.title"
            type="button"
            class="concept-item"
            @click="goPath(item.path)"
          >
            <div class="concept-item__meta">{{ item.label }}</div>
            <h3>{{ item.title }}</h3>
            <p>{{ item.desc }}</p>
            <span>{{ item.cta }}</span>
          </button>
        </div>

        <div class="concept-progress">
          <span>0%</span>
          <div class="concept-progress__line">
            <i></i>
            <i></i>
            <i></i>
          </div>
          <span>100%</span>
        </div>
      </section>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { useRouter } from 'vue-router';
  import { PageWrapper } from '@/components/Page';

  const router = useRouter();

  const tickerItems = [
    { label: 'DXY 美元指数', value: '104.18', change: '+0.08%', tone: 'is-up' },
    { label: '黄金 XAU/USD', value: '2,348.20', change: '+0.21%', tone: 'is-up' },
    { label: '原油 WTI', value: '92.14', change: '+1.05%', tone: 'is-up' },
    { label: '比特币 BTC', value: '62,405', change: '-0.44%', tone: 'is-down' },
    { label: '纳斯达克 NQ', value: '20,116', change: '-0.38%', tone: 'is-down' },
    { label: '沪深300', value: '3,628', change: '+0.41%', tone: 'is-up' },
    { label: '离岸人民币 USDCNH', value: '7.2321', change: '+0.06%', tone: 'is-up' },
  ];

  const portalCards = [
    {
      label: 'A. Opening（初始状态）',
      title: '对冲基金看板',
      desc: '宏观、黄金、加密、全球等变量看板统一入口。',
      cta: '进入对冲基金看板 →',
      path: '/hedge-board/macro',
    },
    {
      label: 'B. Transition（过渡阶段）',
      title: '新闻日历与理财',
      desc: '保留你原本的新闻整理、宏观日历和理财信息结构。',
      cta: '进入新闻日历与理财 →',
      path: '/news-calendar/wealth',
    },
    {
      label: 'C. Pinned Symbol（固定状态）',
      title: '策略研究与金融AI',
      desc: '承接策略管理、交易平台以及金融 AI 分析入口。',
      cta: '进入策略与金融AI →',
      path: '/financial-ai/index',
    },
  ];

  function goPath(path: string) {
    router.push(path);
  }
</script>

<style scoped>
  .dashboard-home {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 16px 4px 24px;
    background:
      radial-gradient(circle at top right, rgba(210, 222, 235, 0.3), transparent 28%),
      linear-gradient(180deg, #f8fafc 0%, #eef3f8 100%);
  }

  .hero-card,
  .ticker-card,
  .concept-card {
    border: 1px solid rgba(223, 231, 239, 0.96);
    border-radius: 30px;
    background: rgba(255, 255, 255, 0.92);
    box-shadow: 0 18px 50px rgba(151, 170, 192, 0.12);
    overflow: hidden;
  }

  .hero-card {
    display: grid;
    grid-template-columns: minmax(420px, 0.95fr) minmax(0, 1.05fr);
    min-height: 372px;
  }

  .hero-card__copy {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 20px;
    padding: 48px 56px;
  }

  .hero-card__eyebrow {
    margin: 0;
    color: #99a6b8;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.28em;
  }

  .hero-card__copy h1 {
    margin: 0;
    color: #1f2d3a;
    font-size: 56px;
    line-height: 1.16;
    font-weight: 700;
  }

  .hero-card__lead {
    max-width: 560px;
    margin: 0;
    color: #667788;
    font-size: 17px;
    line-height: 1.9;
  }

  .hero-card__actions {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
  }

  .hero-card__actions button {
    height: 50px;
    padding: 0 24px;
    border-radius: 16px;
    border: 1px solid rgba(212, 221, 231, 0.95);
    font-size: 15px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .hero-card__actions .primary {
    color: #fff;
    background: linear-gradient(135deg, #183f45 0%, #1f5555 100%);
    border-color: transparent;
  }

  .hero-card__actions .secondary {
    color: #667788;
    background: rgba(255, 255, 255, 0.9);
  }

  .hero-card__art {
    min-height: 372px;
    background:
      linear-gradient(90deg, rgba(255, 255, 255, 0.02), rgba(255, 255, 255, 0)),
      url('@/assets/images/home-hero-art-locked.png') center center / cover no-repeat;
  }

  .ticker-card {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 0;
    padding: 10px 20px;
  }

  .ticker-card article {
    display: grid;
    justify-items: center;
    gap: 8px;
    padding: 16px 10px;
    border-right: 1px solid rgba(230, 236, 242, 0.95);
  }

  .ticker-card article:last-child {
    border-right: none;
  }

  .ticker-card span {
    color: #79889a;
    font-size: 13px;
  }

  .ticker-card strong {
    color: #1f2d3a;
    font-size: 34px;
    line-height: 1;
    font-weight: 700;
  }

  .ticker-card em {
    font-style: normal;
    font-size: 14px;
    font-weight: 700;
  }

  .ticker-card em.is-up {
    color: #1d8f68;
  }

  .ticker-card em.is-down {
    color: #d15b5b;
  }

  .concept-card {
    padding: 28px 34px 30px;
  }

  .concept-card__headline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;
  }

  .concept-card__headline h2 {
    margin: 0 0 8px;
    color: #1f2d3a;
    font-size: 28px;
    font-weight: 700;
  }

  .concept-card__headline p {
    margin: 0;
    color: #718192;
    font-size: 15px;
    line-height: 1.8;
  }

  .concept-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 20px;
  }

  .concept-item {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
    min-height: 256px;
    padding: 24px 24px 22px;
    border: 1px solid rgba(226, 233, 240, 0.94);
    border-radius: 24px;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.66), rgba(255, 255, 255, 0.96)),
      url('@/assets/images/home-hero-art-locked.png') center center / cover no-repeat;
    text-align: left;
    cursor: pointer;
    transition:
      transform 0.18s ease,
      box-shadow 0.18s ease;
  }

  .concept-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 14px 34px rgba(143, 166, 192, 0.15);
  }

  .concept-item__meta {
    color: #8e9bad;
    font-size: 12px;
    font-weight: 700;
  }

  .concept-item h3 {
    margin: 0;
    color: #1f2d3a;
    font-size: 30px;
    line-height: 1.2;
    font-weight: 700;
  }

  .concept-item p {
    margin: 0;
    color: #6f7f92;
    font-size: 15px;
    line-height: 1.75;
  }

  .concept-item span {
    margin-top: auto;
    color: #193f45;
    font-size: 14px;
    font-weight: 700;
  }

  .concept-progress {
    display: grid;
    grid-template-columns: 48px minmax(0, 1fr) 48px;
    gap: 18px;
    align-items: center;
    margin-top: 24px;
    color: #445468;
    font-size: 15px;
  }

  .concept-progress__line {
    position: relative;
    height: 2px;
    background: rgba(195, 205, 214, 0.92);
  }

  .concept-progress__line i {
    position: absolute;
    top: 50%;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #173f45;
    transform: translate(-50%, -50%);
  }

  .concept-progress__line i:nth-child(1) {
    left: 0;
  }

  .concept-progress__line i:nth-child(2) {
    left: 50%;
  }

  .concept-progress__line i:nth-child(3) {
    left: 100%;
  }

  @media (max-width: 1280px) {
    .hero-card {
      grid-template-columns: 1fr;
    }

    .hero-card__art {
      min-height: 280px;
    }

    .ticker-card {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .concept-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 760px) {
    .hero-card__copy {
      padding: 34px 24px;
    }

    .hero-card__copy h1 {
      font-size: 38px;
    }

    .hero-card__actions {
      flex-direction: column;
    }

    .ticker-card {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
</style>
