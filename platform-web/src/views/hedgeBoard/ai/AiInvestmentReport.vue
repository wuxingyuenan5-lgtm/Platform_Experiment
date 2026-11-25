<template>
  <section class="investment-report" aria-label="兴证AI投资专题">
    <header class="report-head">
      <div
        ><p class="kicker">策略研究笔记 / AI投资篇</p><h2>从资本开支，追踪景气兑现</h2
        ><p class="subtitle">兴证策略张启尧团队 · 22个研究主题</p></div
      >
      <div class="edition"
        ><span>本次新增</span><strong>{{ charts.length }}<small> 图表</small></strong
        ><p>2张产业图谱 · 21段回撤</p></div
      >
    </header>
    <div class="source-strip"
      ><span>报告发布：{{ reportSource.published }}</span
      ><span>数据时点：各图分别列示</span><span class="snapshot-key">报告快照 {{ snapshots }}</span
      ><span class="demo-key">Demo {{ charts.length - snapshots }} · 模拟数据</span></div
    >
    <nav class="report-nav" aria-label="新增专题分类"
      ><button
        v-for="g in reportGroups"
        :key="g.key"
        :aria-pressed="group === g.key"
        :class="{ active: group === g.key }"
        @click="group = g.key"
        ><small>{{ g.ids }}</small
        >{{ g.name }}</button
      ></nav
    >
    <div class="report-tools"
      ><label
        >查找主题 / 指标
        <input v-model="search" type="search" placeholder="Capex、GPU、估值…" /></label
      ><label
        >数据范围
        <select v-model="status"
          ><option value="all">全部图表</option
          ><option value="snapshot">仅报告快照</option
          ><option value="demo">仅Demo</option></select
        ></label
      ><span>{{ visible.length }} 个主题</span
      ><button
        v-if="search || status !== 'all'"
        @click="
          search = '';
          status = 'all';
        "
        >清除筛选</button
      ></div
    >
    <p v-if="!visible.length" class="empty">当前分类没有匹配内容。可切换分类或清除筛选。</p>
    <article v-for="topic in visible" :key="topic.id" class="topic" :data-topic="topic.id">
      <header class="topic-head"
        ><span class="topic-index">{{ String(topic.id).padStart(2, '0') }}</span
        ><div
          ><h3>{{ topic.title }}</h3
          ><p>{{ topic.question }}</p></div
        ><small>PDF p.{{ topic.page }}</small></header
      >
      <div v-if="topic.map" class="chain-map"
        ><section v-for="layer in topic.map" :key="layer.name"
          ><h4>{{ layer.name }}</h4
          ><div
            ><span v-for="item in layer.items" :key="item">{{ item }}</span></div
          ></section
        ><p>来源：报告第{{ topic.page }}页 · 分类转录</p></div
      >
      <div class="chart-grid"
        ><VisibleChart v-for="chart in topic.charts" :key="chart.id" :height="530"
          ><Safe :widget-title="chart.title"><AiReportChart :chart="chart" /></Safe></VisibleChart
      ></div>
      <div v-if="topic.id === 6" class="drawdown-panel">
        <div class="drawdown-summary"
          ><p v-for="cycle in ['科网', 'AI']" :key="cycle"
            ><strong>{{ cycle }}周期</strong><span>{{ drawdownSummary(cycle).count }} 段样本</span
            ><span>平均回撤 {{ drawdownSummary(cycle).depth }}%</span
            ><span>平均 {{ drawdownSummary(cycle).days }} 天</span></p
          ></div
        >
        <details
          ><summary>查看报告回撤明细（21段）</summary
          ><div class="table-wrap"
            ><table
              ><thead
                ><tr
                  ><th>周期</th><th>开始</th><th>结束</th><th>回撤</th><th>持续天数</th></tr
                ></thead
              ><tbody
                ><tr v-for="r in drawdowns" :key="r[1]"
                  ><td>{{ r[0] }}</td
                  ><td>{{ r[1] }}</td
                  ><td>{{ r[2] }}</td
                  ><td>{{ r[3] }}%</td><td>{{ r[4] }}</td></tr
                ></tbody
              ></table
            ></div
          ></details
        >
      </div>
    </article>
    <footer class="report-foot"
      ><strong>{{ reportSource.title }}</strong
      ><p
        >报告快照按原图标签和表格转录，保留原观察时点。Demo曲线与散点为固定模拟样本，用于展示研究方法，不是报告逐点数据或最新市场读数。</p
      ><details
        ><summary>研究口径与覆盖</summary
        ><p
          >图中一致预期、租赁价格和行业组合未接入原始历史。分类地图为报告整理；第2题材料图中不可辨认的单元未补造。第5题行业排名与第20题行业覆盖仅复刻精选对象。图表支持图例开关、悬浮数值、长序列缩放、放大、数据表和CSV。</p
        ><p
          >旧版产业总览、财报、ARR、CDS及其数据来源仍在各自分区。专题中的研究假说不构成实时交易信号。</p
        ></details
      ></footer
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import VisibleChart from '../components/VisibleChart';
  import Safe from '../components/WidgetErrorBoundary';
  import AiReportChart from './AiReportChart.vue';
  import {
    reportSource,
    reportGroups,
    reportTopics,
    drawdowns,
    drawdownSummary,
  } from './investmentReport';

  const group = ref('capex'),
    search = ref(''),
    status = ref('all');
  const charts = reportTopics.flatMap((t) => t.charts);
  const snapshots = charts.filter((c) => c.status === 'snapshot').length;
  const visible = computed(() =>
    reportTopics
      .filter((t) => t.group === group.value)
      .map((t) => ({
        ...t,
        charts: t.charts.filter((c) => status.value === 'all' || c.status === status.value),
      }))
      .filter(
        (t) =>
          (status.value === 'all' || t.charts.length > 0) &&
          [t.title, t.question, ...t.charts.map((c) => c.title)]
            .join(' ')
            .toLowerCase()
            .includes(search.value.trim().toLowerCase()),
      ),
  );
</script>
<style scoped>
  .investment-report {
    min-width: 0;
    color: #294359;
    font-family: inherit;
  }

  .report-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 26px 24px;
    border-left: 4px solid #b33d49;
    border-radius: 0 10px 10px 0;
    background: #f4f7fa;
    gap: 24px;
  }

  .kicker {
    margin: 0 0 8px;
    color: #9e4953;
    font-size: 12px;
    letter-spacing: 1px;
  }

  .report-head h2 {
    margin: 0;
    font-family: 'Noto Serif SC', 'Source Han Serif SC', SimSun, serif;
    font-size: 26px;
    font-weight: 700;
    letter-spacing: 1px;
    line-height: 1.45;
  }

  .subtitle {
    margin: 10px 0 0;
    color: #698095;
    font-size: 12px;
  }

  .edition {
    flex-shrink: 0;
    text-align: right;
  }

  .edition > span {
    color: #9e4953;
    font-size: 11px;
  }

  .edition strong {
    display: block;
    font-size: 28px;
    font-variant-numeric: tabular-nums;
  }

  .edition small {
    font-size: 12px;
    font-weight: 400;
  }

  .edition p {
    margin: 0;
    color: #698095;
    font-size: 11px;
  }

  .source-strip {
    display: flex;
    flex-wrap: wrap;
    padding: 13px 0;
    border-bottom: 1px solid #e2e9ef;
    color: #728296;
    font-size: 11px;
    gap: 8px 24px;
  }

  .snapshot-key {
    color: #347260;
  }

  .demo-key {
    color: #986329;
  }

  .report-nav {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
    margin: 18px 0;
  }

  .report-nav button {
    padding: 12px;
    border: 1px solid #dce5ed;
    border-radius: 7px;
    background: #fff;
    color: #547086;
    font-size: 13px;
    text-align: left;
    cursor: pointer;
  }

  .report-nav small {
    margin-right: 10px;
    color: #97a4b0;
    font-size: 11px;
  }

  .report-nav button.active {
    border-color: #b33d49;
    background: #fbf1f2;
    color: #9c3541;
  }

  .report-nav button.active small {
    color: #b3616a;
  }

  .report-tools {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 16px 0 25px;
    color: #718398;
    font-size: 12px;
    gap: 12px;
  }

  .report-tools label {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .report-tools input,
  .report-tools select {
    max-width: 100%;
    padding: 6px 9px;
    border: 1px solid #dce4eb;
    border-radius: 5px;
    background: #fff;
    color: #36516a;
  }

  .report-tools button {
    border: 0;
    background: transparent;
    color: #9c3541;
    cursor: pointer;
  }

  .topic {
    margin: 28px 0 36px;
  }

  .topic-head {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    margin-bottom: 16px;
  }

  .topic-index {
    min-width: 30px;
    padding-top: 6px;
    border-top: 2px solid #b33d49;
    color: #ad4e59;
    font-size: 19px;
    font-variant-numeric: tabular-nums;
  }

  .topic-head h3 {
    margin: 0 0 6px;
    color: #263e54;
    font-size: 18px;
  }

  .topic-head p {
    margin: 0;
    color: #738497;
    font-size: 12px;
    line-height: 1.7;
  }

  .topic-head > small {
    flex-shrink: 0;
    margin-left: auto;
    color: #8595a5;
    font-size: 10px;
  }

  .chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .chart-grid > :only-child {
    grid-column: 1/-1;
  }

  .chain-map {
    overflow: hidden;
    border: 1px solid #dce5ed;
    border-radius: 10px;
  }

  .chain-map section {
    display: grid;
    grid-template-columns: 180px 1fr;
    border-bottom: 1px solid #e6ecf1;
  }

  .chain-map h4 {
    display: flex;
    align-items: center;
    margin: 0;
    padding: 18px;
    background: #eef3f7;
    font-size: 13px;
  }

  .chain-map section > div {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 15px;
    background: white;
  }

  .chain-map span {
    padding: 6px 10px;
    border: 1px solid #f0e3e5;
    border-radius: 4px;
    background: #f8f1f2;
    color: #86505a;
    font-size: 12px;
  }

  .chain-map > p {
    margin: 12px 16px;
    color: #778a9e;
    font-size: 11px;
  }

  .drawdown-panel {
    margin-top: 14px;
    padding: 14px;
    border: 1px solid #dce5ed;
    border-radius: 8px;
    font-size: 12px;
  }

  .drawdown-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 12px 30px;
  }

  .drawdown-summary p {
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
    margin: 0 0 10px;
  }

  .drawdown-summary span {
    color: #6f8293;
  }

  .table-wrap {
    max-height: 360px;
    margin-top: 10px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 8px;
    border-bottom: 1px solid #edf0f4;
    text-align: left;
    white-space: nowrap;
  }

  th {
    position: sticky;
    top: 0;
    background: #f3f6f8;
  }

  summary {
    width: fit-content;
    cursor: pointer;
  }

  .report-foot {
    padding: 20px 0;
    border-top: 1px solid #dce5ed;
    color: #7c8c9b;
    font-size: 11px;
    line-height: 1.9;
  }

  .report-foot strong {
    color: #566e82;
    font-weight: 500;
  }

  .report-foot p {
    margin: 7px 0;
  }

  .empty {
    padding: 40px 10px;
    color: #718398;
    text-align: center;
  }

  button:focus-visible,
  input:focus-visible,
  select:focus-visible,
  summary:focus-visible {
    outline: 2px solid #39799e;
    outline-offset: 3px;
  }

  @media (max-width: 1000px) {
    .chart-grid {
      grid-template-columns: 1fr;
    }

    .report-head h2 {
      font-size: 22px;
    }
  }

  @media (max-width: 600px) {
    .report-head {
      padding: 18px 14px;
    }

    .report-head h2 {
      font-size: 19px;
    }

    .edition {
      display: none;
    }

    .report-nav {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .report-nav small {
      display: block;
      margin-bottom: 4px;
    }

    .topic-head > small {
      display: none;
    }

    .topic-head h3 {
      font-size: 16px;
    }

    .chain-map section {
      grid-template-columns: 1fr;
    }

    .chain-map h4 {
      padding: 12px;
    }

    .report-tools label {
      flex-wrap: wrap;
    }

    .report-tools input {
      width: 180px;
    }
  }
</style>
