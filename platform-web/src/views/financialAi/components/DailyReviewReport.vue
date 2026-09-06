<template>
  <article class="review-report">
    <header class="report-hero">
      <div>
        <p class="eyebrow">AI DAILY REVIEW · {{ report.report_meta?.report_date || '—' }}</p>
        <h2>{{ report.report_meta?.report_name || 'AI 当日复盘' }}</h2>
        <p>{{ report.report_meta?.headline || '等待模型形成总判断。' }}</p>
      </div>
      <div class="report-meta"
        ><span>{{ report.report_meta?.report_cutoff || '收盘后' }}</span
        ><small v-if="report.report_meta?.china_market_date"
          >中国市场：{{ report.report_meta.china_market_date }}</small
        ></div
      >
    </header>

    <section v-if="report.summary" class="report-section">
      <header
        ><h3>90秒摘要</h3><small>{{ report.summary.kicker }}</small></header
      >
      <div class="summary-grid">
        <div>
          <b>{{ report.summary.overnight_title || '全球与隔夜变化' }}</b>
          <ol v-if="report.summary.overnight_changes?.length" class="summary-list"
            ><li v-for="item in report.summary.overnight_changes" :key="item.title"
              ><strong>{{ item.title }}</strong> {{ item.text }}</li
            ></ol
          ><p v-else>{{ report.summary.overnight }}</p>
          <b class="subhead">{{ report.summary.china_title || '中国市场结构变化' }}</b>
          <ol v-if="report.summary.china_changes?.length" class="summary-list"
            ><li v-for="item in report.summary.china_changes" :key="item.title"
              ><strong>{{ item.title }}</strong> {{ item.text }}</li
            ></ol
          ><p v-else>{{ report.summary.china }}</p>
        </div>
        <div>
          <article v-if="report.summary.priority_card" class="priority-card"
            ><small>{{ report.summary.priority_card.label || '明天最高优先级' }}</small
            ><b>{{ report.summary.priority_card.title }}</b
            ><p>{{ report.summary.priority_card.note }}</p></article
          ><article
            v-for="item in report.summary.priorities || []"
            :key="item.head"
            class="priority"
            ><b>{{ item.head }}</b
            ><span>{{ item.text }}</span></article
          >
        </div>
      </div>
    </section>

    <section v-if="report.assets_review?.items?.length" class="report-section">
      <header
        ><h3>大类资产走势与主流解释</h3><small>{{ report.assets_review.kicker }}</small></header
      >
      <div class="asset-grid">
        <article v-for="item in report.assets_review.items" :key="`${item.asset}-${item.move}`">
          <b>{{ item.asset }}</b
          ><strong>{{ item.move }}</strong
          ><p>{{ item.meaning }}</p>
        </article>
      </div>
    </section>

    <section v-if="report.china_market" class="report-section">
      <header
        ><h3>{{ report.china_market.title || '今日中国市场' }}</h3
        ><small>{{ report.china_market.kicker }}</small></header
      >
      <p v-if="report.china_market.priority" class="priority-line"
        ><b>今天真正重要的：</b>{{ report.china_market.priority }}</p
      ><p v-if="report.china_market.warning" class="warning">{{ report.china_market.warning }}</p>
      <div v-if="report.china_market.switch?.length" class="switch-grid"
        ><article v-for="item in report.china_market.switch.slice(0, 2)" :key="item.label"
          ><small>{{ item.label }}</small
          ><strong :class="item.cls">{{ item.metric }}</strong
          ><p>{{ item.note }}</p></article
        ></div
      >
      <div class="summary-grid">
        <div v-if="report.china_market.breadth"
          ><b>{{ field(report.china_market.breadth, 'title', '市场宽度') }}</b
          ><div v-if="typeof report.china_market.breadth !== 'string'" class="breadth"
            ><span
              class="up-bar"
              :style="{ width: `${report.china_market.breadth.up_pct ?? 50}%` }"
            ></span
            ><span
              class="down-bar"
              :style="{ width: `${report.china_market.breadth.down_pct ?? 50}%` }"
            ></span></div
          ><p>{{ describeBreadth(report.china_market.breadth, '上涨', '下跌') }}</p></div
        >
        <div v-if="report.china_market.industry"
          ><b>{{ field(report.china_market.industry, 'title', '行业与情绪') }}</b
          ><div v-if="typeof report.china_market.industry !== 'string'" class="breadth"
            ><span
              class="up-bar"
              :style="{ width: `${report.china_market.industry.up_pct ?? 50}%` }"
            ></span
            ><span
              class="down-bar"
              :style="{ width: `${report.china_market.industry.down_pct ?? 50}%` }"
            ></span></div
          ><p>{{ describeBreadth(report.china_market.industry, '上涨行业', '下跌行业') }}</p></div
        >
      </div>
    </section>

    <section v-if="report.mainlines?.items?.length" class="report-section">
      <header
        ><h3>三条统一市场主线</h3><small>{{ report.mainlines.kicker }}</small></header
      >
      <ol class="mainlines">
        <li v-for="item in report.mainlines.items" :key="item.title">
          <div class="tags"
            ><span v-for="tag in item.tags || []" :key="tag">{{ tag }}</span></div
          >
          <b>{{ item.title }}</b
          ><p v-for="paragraph in item.paras || []" :key="paragraph">{{ paragraph }}</p
          ><p v-if="item.evidence"><strong>证据与分歧：</strong>{{ item.evidence }}</p
          ><small v-if="item.counter_evidence">反方证据：{{ item.counter_evidence }}</small
          ><small v-if="item.validation">明日继续验证：{{ item.validation }}</small>
        </li>
      </ol>
    </section>

    <section v-if="validationRows.length" class="report-section">
      <header
        ><h3>明日验证清单</h3><small>{{ validationKicker }}</small></header
      >
      <div class="check-grid">
        <article v-for="item in validationRows" :key="item.subject || item.question">
          <small v-if="item.subject">{{ item.subject }}</small
          ><b>{{ item.question }}</b
          ><p>观察：{{ item.look || item.signal }}</p
          ><small>判断含义：{{ item.meaning || item.invalidation }}</small>
        </article>
      </div>
    </section>

    <section v-if="report.previous_review?.rows?.length" class="report-section">
      <header
        ><h3>前期观点复盘</h3><small>{{ report.previous_review.kicker }}</small></header
      >
      <div class="table-wrap"
        ><table
          ><thead
            ><tr><th>原判断</th><th>新增事实</th><th>状态</th><th>框架调整</th></tr></thead
          ><tbody>
            <tr v-for="row in report.previous_review.rows" :key="row.judgment"
              ><td>{{ row.judgment }}</td
              ><td>{{ row.facts }}</td
              ><td>{{ row.state }}</td
              ><td>{{ row.adjust }}</td></tr
            >
          </tbody></table
        ></div
      >
    </section>

    <section v-if="report.funding_industry?.items?.length" class="report-section">
      <header
        ><h3>资金、仓位与产业数据点评</h3
        ><small>{{ report.funding_industry.kicker }}</small></header
      >
      <div class="check-grid"
        ><article v-for="item in report.funding_industry.items" :key="item.label"
          ><b>{{ item.label }}</b
          ><strong v-if="item.metric" :class="item.cls">{{ item.metric }}</strong
          ><p>{{ item.fact || item.note }}</p
          ><small>{{ item.interpretation }}</small></article
        ></div
      >
    </section>

    <section
      v-if="report.tracking?.rows?.length || report.tracking?.items?.length"
      class="report-section"
    >
      <header
        ><h3>后续跟踪框架</h3><small>{{ report.tracking.kicker }}</small></header
      >
      <div v-if="report.tracking.rows?.length" class="table-wrap"
        ><table
          ><thead
            ><tr
              ><th>主题</th><th>当前判断</th><th>支持证据</th><th>反方证据</th><th>下一验证</th
              ><th>证伪条件</th><th>周期</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in report.tracking.rows" :key="row.topic"
              ><td
                ><b>{{ row.topic }}</b></td
              ><td>{{ row.judgment }}</td
              ><td>{{ row.support }}</td
              ><td>{{ row.counter }}</td
              ><td>{{ row.next }}</td
              ><td>{{ row.falsify }}</td
              ><td>{{ row.period }}</td></tr
            ></tbody
          ></table
        ></div
      ><ul v-else class="tracking"
        ><li v-for="item in report.tracking.items" :key="item">{{ item }}</li></ul
      >
    </section>

    <section v-if="eventRows.length" class="report-section">
      <header
        ><h3>今日关注与未来7天事件</h3><small>{{ report.events.kicker }}</small></header
      >
      <div class="table-wrap"
        ><table
          ><thead
            ><tr><th>北京时间</th><th>事件</th><th>影响市场</th><th>核心验证变量</th></tr></thead
          ><tbody>
            <tr v-for="item in eventRows" :key="`${item.time}-${item.event}`"
              ><td>{{ item.time }}</td
              ><td>{{ item.event }}</td
              ><td>{{ item.market || item.markets }}</td
              ><td>{{ item.variable || item.var }}</td></tr
            >
          </tbody></table
        ></div
      >
    </section>

    <section v-if="report.sources?.length" class="report-section">
      <header><h3>来源与口径</h3><small>只展示本次底稿实际包含的数据源</small></header>
      <ul class="sources"
        ><li v-for="source in report.sources" :key="source">{{ source }}</li></ul
      >
    </section>
  </article>
</template>

<script setup lang="ts">
  import { computed } from 'vue';

  type BreadthBlock = {
    title?: string;
    up?: string;
    down?: string;
    up_pct?: number;
    down_pct?: number;
    note?: string;
  };
  type ValidationRow = {
    subject?: string;
    question?: string;
    look?: string;
    meaning?: string;
    signal?: string;
    invalidation?: string;
  };
  type EventRow = {
    time?: string;
    event?: string;
    market?: string;
    markets?: string;
    variable?: string;
    var?: string;
  };
  export interface DailyReviewPayload {
    report_meta?: {
      report_name?: string;
      report_date?: string;
      report_cutoff?: string;
      china_market_date?: string;
      headline?: string;
    };
    summary?: {
      kicker?: string;
      overnight_title?: string;
      overnight?: string;
      overnight_changes?: Array<{ title: string; text: string }>;
      china_title?: string;
      china?: string;
      china_changes?: Array<{ title: string; text: string }>;
      priority_card?: { label?: string; title?: string; note?: string };
      priorities?: Array<{ head: string; text: string }>;
    };
    assets_review?: {
      kicker?: string;
      items?: Array<{ asset: string; move: string; meaning: string }>;
    };
    china_market?: {
      title?: string;
      kicker?: string;
      priority?: string;
      warning?: string;
      switch?: Array<{ label?: string; metric?: string; cls?: string; note?: string }>;
      breadth?: string | BreadthBlock;
      industry?: string | BreadthBlock;
    };
    mainlines?: {
      kicker?: string;
      items?: Array<{
        title: string;
        tags?: string[];
        paras?: string[];
        evidence?: string;
        counter_evidence?: string;
        validation?: string;
      }>;
    };
    tomorrow_validation?: {
      kicker?: string;
      items?: Array<{ question: string; signal: string; invalidation: string }>;
    };
    today_validation?: { kicker?: string; rows?: ValidationRow[] };
    previous_review?: {
      kicker?: string;
      rows?: Array<{ judgment: string; facts: string; state: string; adjust: string }>;
    };
    funding_industry?: {
      kicker?: string;
      items?: Array<{
        label: string;
        fact?: string;
        interpretation?: string;
        metric?: string;
        cls?: string;
        note?: string;
      }>;
    };
    tracking?: {
      kicker?: string;
      items?: string[];
      rows?: Array<{
        topic?: string;
        judgment?: string;
        support?: string;
        counter?: string;
        next?: string;
        falsify?: string;
        period?: string;
      }>;
    };
    events?: {
      kicker?: string;
      items?: EventRow[];
      rows?: EventRow[];
    };
    sources?: string[];
  }

  const props = defineProps<{ report: DailyReviewPayload }>();
  const validationRows = computed<ValidationRow[]>(
    () => props.report.today_validation?.rows || props.report.tomorrow_validation?.items || [],
  );
  const validationKicker = computed(
    () => props.report.today_validation?.kicker || props.report.tomorrow_validation?.kicker || '',
  );
  const eventRows = computed<EventRow[]>(
    () => props.report.events?.rows || props.report.events?.items || [],
  );
  const field = (value: string | BreadthBlock, key: keyof BreadthBlock, fallback: string) =>
    typeof value === 'string' ? fallback : String(value[key] || fallback);
  const describeBreadth = (value: string | BreadthBlock, upLabel: string, downLabel: string) =>
    typeof value === 'string'
      ? value
      : `${upLabel} ${value.up || '—'} / ${downLabel} ${value.down || '—'}${
          value.note ? `；${value.note}` : ''
        }`;
</script>

<style scoped lang="less">
  .review-report {
    display: grid;
    gap: 14px;
  }

  .report-hero,
  .report-section {
    border: 1px solid #dbe4ed;
    border-radius: 10px;
    background: #fff;
  }

  .report-hero {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
    padding: 24px;
    border-top: 3px solid #2f6fed;
  }

  .report-hero h2,
  .report-section h3 {
    margin: 0;
    color: #17212f;
  }

  .report-hero p {
    margin: 7px 0 0;
    color: #667085;
  }

  .report-hero > span {
    padding: 5px 9px;
    border-radius: 999px;
    background: #eef4ff;
    color: #2f6fed;
    font-size: 12px;
    white-space: nowrap;
  }

  .report-meta {
    display: grid;
    justify-items: end;
    gap: 6px;
  }

  .report-meta span {
    padding: 5px 9px;
    border-radius: 999px;
    background: #eef4ff;
    color: #2f6fed;
    font-size: 12px;
    white-space: nowrap;
  }

  .eyebrow {
    margin: 0 0 5px !important;
    color: #758196 !important;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  .report-section {
    padding: 20px;
  }

  .report-section > header {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
  }

  .report-section > header small,
  p,
  small {
    color: #667085;
    line-height: 1.65;
  }

  .summary-grid,
  .asset-grid,
  .check-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .asset-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .summary-grid > div,
  .asset-grid article,
  .check-grid article {
    padding: 14px;
    border: 1px solid #e4eaf1;
    border-radius: 8px;
    background: #fbfcfe;
  }

  .summary-grid p,
  .asset-grid p,
  .check-grid p {
    margin: 7px 0 0;
  }

  .summary-list {
    display: grid;
    gap: 7px;
    margin: 8px 0 16px;
    padding-left: 20px;
    color: #667085;
  }

  .summary-list strong,
  .subhead {
    margin-right: 5px;
    color: #344054;
  }

  .priority-card,
  .priority {
    display: grid;
    gap: 5px;
    padding: 13px;
    border-left: 3px solid #2f6fed;
    background: #f4f7ff;
  }

  .priority + .priority {
    margin-top: 8px;
  }

  .priority-line,
  .warning {
    padding: 10px 12px;
    border-radius: 7px;
    background: #f4f7ff;
  }

  .warning {
    background: #fff7ed;
    color: #9a3412;
  }

  .switch-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 10px;
  }

  .switch-grid article {
    padding: 13px;
    border: 1px solid #e4eaf1;
    border-radius: 8px;
  }

  .switch-grid strong,
  .funding-industry strong {
    display: block;
    margin-top: 4px;
    font-size: 18px;
  }

  .up {
    color: #c0362c;
  }

  .down {
    color: #087a55;
  }

  .breadth {
    display: flex;
    height: 5px;
    margin: 10px 0;
    overflow: hidden;
    border-radius: 999px;
    background: #e5e7eb;
  }

  .up-bar {
    background: #c0362c;
  }

  .down-bar {
    background: #087a55;
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-bottom: 5px;
  }

  .tags span {
    padding: 2px 7px;
    border-radius: 999px;
    background: #eef4ff;
    color: #2f6fed;
    font-size: 11px;
  }

  .asset-grid strong {
    display: block;
    margin-top: 5px;
    color: #2f6fed;
  }

  .mainlines,
  .tracking,
  .sources {
    display: grid;
    gap: 10px;
    margin: 0;
    padding-left: 22px;
  }

  .mainlines li {
    padding-left: 5px;
  }

  .mainlines p {
    margin: 5px 0;
  }

  .table-wrap {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }

  th,
  td {
    padding: 10px;
    border-bottom: 1px solid #e4eaf1;
    text-align: left;
    vertical-align: top;
  }

  th {
    background: #f7f9fc;
    color: #344054;
  }

  td {
    color: #667085;
  }

  @media (max-width: 900px) {
    .asset-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 620px) {
    .report-hero,
    .report-section > header {
      flex-direction: column;
    }

    .summary-grid,
    .asset-grid,
    .check-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
