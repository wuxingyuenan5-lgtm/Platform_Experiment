<template>
  <RestoredProductSurface
    state="sample"
    source="sample:dashboard-restoration"
    as-of="2026-08-05 · 非实时"
    :actionable="false"
    message="首页聚合数据 Owner 尚未配置；当前恢复信息架构和观察面板，数值仅用于界面验收。"
  >
    <main class="dashboard-restored">
      <header class="hero">
        <div>
          <p class="eyebrow">GLOBAL VARIABLE · RESEARCH DESK</p>
          <h1>全球变量</h1>
          <p>把宏观、权益、商品、加密与风险状态集中到同一观察入口。</p>
        </div>
        <div class="hero__status">
          <span>市场状态</span>
          <strong>观察模式</strong>
          <small>样例快照，不构成交易信号</small>
        </div>
      </header>

      <section class="metric-grid">
        <article v-for="item in metrics" :key="item.label" class="metric-card">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.note }}</small>
        </article>
      </section>

      <section class="content-grid">
        <article class="panel panel--wide">
          <div class="panel__head">
            <div>
              <span>跨资产观察</span>
              <h2>风险偏好温度</h2>
            </div>
            <em>Sample</em>
          </div>
          <div v-for="item in heat" :key="item.name" class="heat-row">
            <span>{{ item.name }}</span>
            <div class="heat-track">
              <i :style="{ width: `${item.score}%` }"></i>
            </div>
            <strong>{{ item.view }}</strong>
          </div>
        </article>

        <article class="panel">
          <div class="panel__head">
            <h2>今日关注</h2>
            <em>只读</em>
          </div>
          <ul class="focus-list">
            <li v-for="item in focus" :key="item.title">
              <span>{{ item.time }}</span>
              <div>
                <strong>{{ item.title }}</strong>
                <small>{{ item.note }}</small>
              </div>
            </li>
          </ul>
        </article>

        <article class="panel">
          <div class="panel__head">
            <h2>组合风险</h2>
            <em>只读</em>
          </div>
          <dl class="risk-list">
            <div v-for="item in risks" :key="item.label">
              <dt>{{ item.label }}</dt>
              <dd>{{ item.value }}</dd>
            </div>
          </dl>
        </article>
      </section>
    </main>
  </RestoredProductSurface>
</template>

<script setup lang="ts">
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';

  const metrics = [
    { label: 'A股风险偏好', value: '62', note: '中性偏进攻' },
    { label: '美元流动性', value: '48', note: '边际收敛' },
    { label: '商品趋势', value: '71', note: '有色相对占优' },
    { label: '波动率状态', value: '36', note: '未进入压力区' },
  ];

  const heat = [
    { name: '中国权益', score: 66, view: '偏强' },
    { name: '美国权益', score: 55, view: '中性' },
    { name: '贵金属', score: 73, view: '偏强' },
    { name: '工业金属', score: 69, view: '偏强' },
    { name: '加密资产', score: 47, view: '震荡' },
  ];

  const focus = [
    {
      time: '09:30',
      title: 'A股开盘结构',
      note: '观察成交扩散与大小盘同步性',
    },
    {
      time: '15:00',
      title: '商品日盘收市',
      note: '关注铜、金与碳酸锂趋势持续性',
    },
    {
      time: '21:30',
      title: '美股开盘窗口',
      note: '核对美元、利率与风险资产联动',
    },
  ];

  const risks = [
    { label: '集中度', value: '可控' },
    { label: '流动性', value: '正常' },
    { label: '跨市场敞口', value: '待复核' },
    { label: 'Live Write', value: '关闭' },
  ];
</script>

<style scoped>
  .dashboard-restored {
    display: grid;
    gap: 16px;
    padding: 4px;
    color: #172033;
  }

  .hero {
    display: flex;
    justify-content: space-between;
    gap: 24px;
    padding: 28px;
    border-radius: 18px;
    background: linear-gradient(135deg, #101a2e, #203a63);
    color: white;
  }

  .hero h1 {
    margin: 4px 0 8px;
    font-size: 34px;
  }

  .hero p {
    margin: 0;
    color: #cbd7e8;
  }

  .eyebrow {
    font-size: 11px;
    letter-spacing: 0.18em;
  }

  .hero__status {
    display: grid;
    min-width: 180px;
    align-content: center;
    gap: 4px;
    padding: 16px;
    border: 1px solid rgb(255 255 255 / 18%);
    border-radius: 14px;
    background: rgb(255 255 255 / 8%);
  }

  .hero__status strong {
    font-size: 24px;
  }

  .hero__status small {
    color: #cbd7e8;
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }

  .metric-card,
  .panel {
    border: 1px solid #e4e9f0;
    border-radius: 14px;
    background: #fff;
    box-shadow: 0 8px 24px rgb(26 39 66 / 5%);
  }

  .metric-card {
    display: grid;
    gap: 6px;
    padding: 18px;
  }

  .metric-card span,
  .metric-card small,
  .panel small {
    color: #6b7587;
  }

  .metric-card strong {
    font-size: 28px;
  }

  .content-grid {
    display: grid;
    grid-template-columns: 1.5fr 1fr 1fr;
    gap: 12px;
  }

  .panel {
    padding: 18px;
  }

  .panel__head {
    display: flex;
    align-items: start;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .panel__head h2 {
    margin: 2px 0 0;
    font-size: 17px;
  }

  .panel__head em {
    padding: 4px 8px;
    border-radius: 999px;
    background: #fff5d6;
    color: #8a6210;
    font-size: 11px;
    font-style: normal;
  }

  .heat-row {
    display: grid;
    grid-template-columns: 80px 1fr 50px;
    align-items: center;
    gap: 10px;
    margin: 14px 0;
  }

  .heat-track {
    height: 7px;
    overflow: hidden;
    border-radius: 999px;
    background: #edf1f6;
  }

  .heat-track i {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #5a83d8, #26a477);
  }

  .focus-list {
    display: grid;
    gap: 14px;
    padding: 0;
    margin: 0;
    list-style: none;
  }

  .focus-list li {
    display: grid;
    grid-template-columns: 48px 1fr;
    gap: 10px;
  }

  .focus-list li > span {
    color: #6a79a2;
    font-weight: 700;
  }

  .focus-list div {
    display: grid;
    gap: 3px;
  }

  .risk-list {
    display: grid;
    gap: 12px;
    margin: 0;
  }

  .risk-list div {
    display: flex;
    justify-content: space-between;
    padding-bottom: 10px;
    border-bottom: 1px solid #eef1f5;
  }

  .risk-list dt {
    color: #6b7587;
  }

  .risk-list dd {
    margin: 0;
    font-weight: 700;
  }

  @media (max-width: 1100px) {
    .metric-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .content-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 640px) {
    .hero {
      flex-direction: column;
    }

    .metric-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
