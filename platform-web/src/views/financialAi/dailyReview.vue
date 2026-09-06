<template>
  <PageWrapper title="AI当日复盘">
    <main class="page">
      <section class="hero"
        ><div
          ><p class="eyebrow">DAILY MARKET REVIEW · {{ tradeDate }}</p
          ><h2>当日市场复盘</h2
          ><p
            >市场事实、结构主线、资金温度与下一交易日验证清单集中在一份可保存的研究底稿中。</p
          ></div
        ><div class="actions"
          ><button class="quiet" :disabled="loading" @click="load">{{
            loading ? '更新中…' : '更新数据'
          }}</button
          ><button v-if="aiLoading" class="danger" @click="cancelAi">停止生成</button
          ><button v-else class="primary" :disabled="!dashboard" @click="runAiReview"
            >生成 AI 复盘</button
          ><button class="quiet" :disabled="!dashboard" @click="saveReview">保存</button
          ><button class="quiet" :disabled="!dashboard" @click="downloadMarkdown">下载 MD</button
          ><button class="quiet" :disabled="!dashboard" @click="downloadHtml">下载 HTML</button
          ><button class="quiet" :disabled="!dashboard" @click="printPdf">打印 / PDF</button></div
        ></section
      >
      <section v-if="error" class="notice error">{{ error }}</section
      ><section v-else-if="loading && !dashboard" class="notice">正在构建当日事实底稿…</section>
      <template v-else-if="dashboard">
        <nav class="view-tabs"
          ><button
            v-for="item in views"
            :key="item.key"
            :class="{ active: view === item.key }"
            @click="view = item.key"
            >{{ item.name }}</button
          ></nav
        >
        <section class="metric-grid"
          ><article
            ><span>市场宽度</span><strong>{{ breadth?.breadthState || '待确认' }}</strong
            ><small>上涨 {{ breadth?.up ?? '—' }} / 下跌 {{ breadth?.down ?? '—' }}</small></article
          ><article
            ><span>短线情绪</span><strong>{{ breadth?.speculationState || '待确认' }}</strong
            ><small
              >涨停 {{ emotion?.limitUpCount ?? '—' }} · 跌停
              {{ emotion?.limitDownCount ?? '—' }}</small
            ></article
          ><article
            ><span>封板率</span><strong>{{ pct(emotion?.sealRatePct) }}</strong
            ><small>炸板 {{ emotion?.brokenBoardCount ?? '—' }} 只</small></article
          ><article
            ><span>连板高度</span><strong>{{ emotion?.highestBoardCount ?? '—' }} 板</strong
            ><small>连板股 {{ emotion?.consecutiveBoardCount ?? '—' }} 只</small></article
          ></section
        >
        <section v-if="assetRows.length" class="card">
          <header
            ><div><p class="eyebrow">CROSS-ASSET TAPE</p><h3>海内外大类资产总览</h3></div
            ><span class="fact-tag">平台数据</span></header
          ><div class="asset-grid"
            ><article v-for="item in assetRows" :key="item.key"
              ><small>{{ item.group }}</small
              ><b>{{ item.label }}</b
              ><strong>{{ item.value }}</strong
              ><em>{{ item.unit }}</em></article
            ></div
          ></section
        >
        <section v-if="view !== 'research'" class="card brief"
          ><header
            ><div><p class="eyebrow">90 SECOND BRIEF</p><h3>90 秒摘要</h3></div
            ><span class="fact-tag">事实</span></header
          ><p>{{ quickBrief }}</p
          ><div class="index-strip"
            ><article v-for="item in indices" :key="item.code"
              ><b>{{ item.name }}</b
              ><strong :class="Number(item.return1dPct) >= 0 ? 'up' : 'down'">{{
                pct(item.return1dPct)
              }}</strong
              ><small>{{ item.close ?? '—' }}</small></article
            ></div
          ></section
        >
        <section v-if="view !== 'overview'" class="two-column">
          <article class="card"
            ><header
              ><div><p class="eyebrow">OVERNIGHT DRIVERS</p><h3>隔夜与盘前驱动</h3></div
              ><span class="verify-tag">待验证</span></header
            ><p
              >当前底稿已确认指数、宽度与行业表现；外盘、政策及公司事件由已接入 AI
              在复盘正文中归纳。没有来源支持的叙事不得视为事实。</p
            ></article
          >
          <article class="card"
            ><header
              ><div><p class="eyebrow">PREVIOUS REVIEW</p><h3>前期观点复盘</h3></div
              ><span class="inference-tag">历史记录</span></header
            ><p>{{
              previousReview || '本浏览器尚无此前保存的复盘；保存本次结果后可用于下一交易日对照。'
            }}</p></article
          >
        </section>
        <section v-if="view !== 'overview'" class="two-column">
          <article class="card"
            ><header
              ><div><p class="eyebrow">MARKET STRUCTURE</p><h3>中国市场结构</h3></div
              ><span class="fact-tag">事实</span></header
            ><ul class="rank"
              ><li v-for="item in topIndustries" :key="item.swL2Code"
                ><b>{{ item.swL2Name }}</b
                ><span>{{ pct(item.returnPct) }}</span
                ><small>{{ amount(item.turnoverYuan) }}</small></li
              ></ul
            ></article
          >
          <article class="card"
            ><header
              ><div><p class="eyebrow">MAIN LINES</p><h3>主线与情绪龙头</h3></div
              ><span class="inference-tag">观察</span></header
            ><ul class="leaders"
              ><li v-for="item in leaders" :key="item.securityCode"
                ><b>{{ item.securityName }}</b
                ><span>{{ item.boardCount }}板</span><small>{{ item.securityCode }}</small></li
              ><li v-if="!leaders.length">暂无连续涨停龙头数据</li></ul
            ><p class="note"
              >成交领先不等于趋势确认，需结合持续性、资金回流和次日承接验证。</p
            ></article
          >
        </section>
        <section v-if="view !== 'overview'" class="card"
          ><header
            ><div><p class="eyebrow">CAPITAL & INDUSTRY</p><h3>资金与行业追踪</h3></div
            ><span class="fact-tag">事实</span></header
          ><div class="industry-grid"
            ><article v-for="item in thresholdStocks" :key="item.securityCode"
              ><b>{{ item.securityName }}</b
              ><span>{{ item.swL2Name }}</span
              ><strong>{{ amount(item.turnoverYuan) }}</strong
              ><small>{{ pct(item.returnPct) }}</small></article
            ><p v-if="!thresholdStocks.length">暂无超过平台阈值的活跃个股。</p></div
          ></section
        >
        <section class="card ai-card"
          ><header
            ><div><p class="eyebrow">AI SYNTHESIS</p><h3>AI 复盘结论</h3></div
            ><span class="inference-tag">推断 · 待复核</span></header
          ><p v-if="aiError" class="error-text">{{ aiError }}</p
          ><DailyReviewReport v-else-if="reviewObject" :report="reviewObject" />
          <pre v-else-if="aiResult">{{ aiResult }}</pre
          ><div v-else class="empty"
            ><p
              >点击“生成 AI
              复盘”，模型会基于本页事实底稿输出：隔夜驱动、结构主线、反方证据、事件日历和明日验证清单。</p
            ><RouterLink to="/financial-ai/ai-connection">前往接入 AI</RouterLink></div
          ></section
        >
        <section class="two-column"
          ><article class="card"
            ><header
              ><div><p class="eyebrow">NEXT SESSION</p><h3>下一交易日验证清单</h3></div
              ><span class="verify-tag">验证</span></header
            ><ol class="checklist"
              ><li>成交领先行业能否保持前列，还是仅为单日脉冲。</li
              ><li>涨停、炸板与晋级率是否同步改善。</li
              ><li>指数涨跌与市场宽度是否继续同向。</li
              ><li>高成交个股能否出现缩量承接或资金回流。</li></ol
            ></article
          ><article class="card"
            ><header
              ><div><p class="eyebrow">SOURCES</p><h3>数据来源与状态</h3></div></header
            ><ul class="sources"
              ><li v-for="item in sources" :key="item.name"
                ><b>{{ item.name }}</b
                ><span :class="item.ok ? 'ok' : 'warn'">{{ item.status }}</span
                ><small>{{ item.source }}</small></li
              ></ul
            ></article
          ></section
        >
        <section class="card"
          ><header
            ><div><p class="eyebrow">EVENT CALENDAR</p><h3>今日关注与未来 7 天事件</h3></div
            ><span class="verify-tag">验证</span></header
          ><div class="event-grid"
            ><article v-for="item in events" :key="item.id"
              ><b>{{ item.label }}</b
              ><strong>{{ Number(item.probability).toFixed(1) }}%</strong
              ><small>{{ item.category }}</small></article
            ><p v-if="!events.length">当前没有接入可用的事件概率数据。</p></div
          ></section
        >
      </template>
      <section v-else class="notice">尚未加载当日数据。点击“更新数据”后再生成复盘。</section>
    </main>
  </PageWrapper>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { PageWrapper } from '@/components/Page';
  import {
    getAShareDashboard,
    getCommodityDashboardV1,
    getCryptoDashboardV1,
    getMacroDashboardV1,
    getMacroExpectations,
    type AShareDashboardResponse,
    type MacroDashboardResponse,
    type MacroExpectationEvent,
  } from '@/api/hedgeResearch';
  import { streamFinancialAi } from '@/api/financialAi';
  import DailyReviewReport, { type DailyReviewPayload } from './components/DailyReviewReport.vue';

  const dashboard = ref<AShareDashboardResponse | null>(null),
    loading = ref(false),
    error = ref(''),
    aiLoading = ref(false),
    aiResult = ref(''),
    aiError = ref(''),
    view = ref('all');
  const events = ref<MacroExpectationEvent[]>([]);
  const assetDashboards = ref<Record<string, MacroDashboardResponse | null>>({
    宏观: null,
    商品: null,
    加密资产: null,
  });
  let controller: AbortController | null = null;
  const views = [
    { key: 'all', name: '完整复盘' },
    { key: 'overview', name: '管理层摘要' },
    { key: 'research', name: '研究视图' },
  ];
  const breadth = computed(() => dashboard.value?.breadth.data),
    emotion = computed(() => dashboard.value?.emotion.data),
    indices = computed(() => dashboard.value?.marketDetail.data || []),
    topIndustries = computed(() => dashboard.value?.shenwan.data?.sw2Top.slice(0, 8) || []),
    leaders = computed(() => dashboard.value?.emotion.data?.leaders.slice(0, 8) || []),
    thresholdStocks = computed(
      () => dashboard.value?.shenwan.data?.threshold.stocks.slice(0, 12) || [],
    ),
    tradeDate = computed(
      () => breadth.value?.tradeDate || dashboard.value?.generatedAt.slice(0, 10) || '—',
    );
  const formatAssetValue = (value: unknown) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return String(value ?? '—');
    if (Math.abs(numeric) >= 1_000_000_000) return `${(numeric / 1_000_000_000).toFixed(2)}B`;
    if (Math.abs(numeric) >= 1_000_000) return `${(numeric / 1_000_000).toFixed(2)}M`;
    if (Math.abs(numeric) >= 1_000)
      return numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
    return numeric.toLocaleString('zh-CN', { maximumFractionDigits: 4 });
  };
  const assetRows = computed(() =>
    Object.entries(assetDashboards.value).flatMap(([group, payload]) =>
      Object.values(payload?.groups || {})
        .flat()
        .filter((series) => series.latestValue != null)
        .slice(0, 6)
        .map((series) => ({
          key: `${group}-${series.seriesId}`,
          group,
          label: series.label,
          value: formatAssetValue(series.latestValue),
          unit: series.unit,
          source: series.source,
        })),
    ),
  );
  const reviewObject = computed<DailyReviewPayload | null>(() => {
    if (!aiResult.value.trim()) return null;
    try {
      const clean = aiResult.value
        .trim()
        .replace(/^```(?:json)?\s*/i, '')
        .replace(/\s*```$/, '');
      const jsonStart = clean.indexOf('{');
      const jsonEnd = clean.lastIndexOf('}');
      if (jsonStart < 0 || jsonEnd <= jsonStart) return null;
      const parsed = JSON.parse(clean.slice(jsonStart, jsonEnd + 1)) as DailyReviewPayload;
      return parsed.report_meta || parsed.summary ? parsed : null;
    } catch {
      return null;
    }
  });
  const quickBrief = computed(
    () =>
      `当日市场呈“${breadth.value?.breadthState || '待确认'}”格局，上涨 ${
        breadth.value?.up ?? '—'
      } 家、下跌 ${breadth.value?.down ?? '—'} 家；短线情绪为“${
        breadth.value?.speculationState || '待确认'
      }”，涨停 ${emotion.value?.limitUpCount ?? '—'} 家、跌停 ${
        emotion.value?.limitDownCount ?? '—'
      } 家，连板高度 ${emotion.value?.highestBoardCount ?? '—'} 板。成交额领先方向为 ${
        topIndustries.value
          .slice(0, 3)
          .map((i) => i.swL2Name)
          .join('、') || '待确认'
      }。`,
  );
  const previousReview = computed(() => {
    const keys = Object.keys(localStorage)
      .filter((key) => key.startsWith('vg-daily-review-') && !key.endsWith(tradeDate.value))
      .sort()
      .reverse();
    const value = keys[0] ? localStorage.getItem(keys[0]) : '';
    return value ? value.replace(/^#.*$/m, '').replace(/\s+/g, ' ').trim().slice(0, 260) : '';
  });
  const sources = computed(() => {
    if (!dashboard.value) return [];
    const rows = [
      { name: '指数行情', meta: dashboard.value.marketDetail.meta },
      { name: '市场宽度', meta: dashboard.value.breadth.meta },
      { name: '申万行业', meta: dashboard.value.shenwan.meta },
      { name: '短线情绪', meta: dashboard.value.emotion.meta },
    ];
    return rows.map(({ name, meta }) => ({
      name,
      source: meta.source,
      status: meta.status,
      ok: ['ready', 'partial'].includes(meta.status),
    }));
  });
  const pct = (v: unknown) =>
    Number.isFinite(Number(v)) ? `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(2)}%` : '—';
  const amount = (v: unknown) =>
    Number.isFinite(Number(v)) ? `${(Number(v) / 1e8).toFixed(1)}亿元` : '—';
  async function load() {
    loading.value = true;
    error.value = '';
    try {
      const [market, macro, macroDashboard, commodityDashboard, cryptoDashboard] =
        await Promise.all([
          getAShareDashboard(),
          getMacroExpectations().catch(() => null),
          getMacroDashboardV1().catch(() => null),
          getCommodityDashboardV1().catch(() => null),
          getCryptoDashboardV1().catch(() => null),
        ]);
      dashboard.value = market;
      events.value = macro?.events || [];
      assetDashboards.value = {
        宏观: macroDashboard,
        商品: commodityDashboard,
        加密资产: cryptoDashboard,
      };
    } catch (e) {
      error.value = e instanceof Error ? e.message : '市场底稿暂不可用';
    } finally {
      loading.value = false;
    }
  }
  async function runAiReview() {
    if (!dashboard.value) return;
    controller = new AbortController();
    aiLoading.value = true;
    aiResult.value = '';
    aiError.value = '';
    try {
      await streamFinancialAi(
        `生成完整当日复盘，只返回合法 JSON，不要 Markdown 代码围栏。所有数字必须来自底稿，不得补造。JSON 结构严格为：
{"report_meta":{"report_name":"AI 当日复盘","report_date":"YYYY-MM-DD","report_cutoff":"数据截止时点","china_market_date":"中国市场日期","headline":"一句话判断"},"summary":{"kicker":"摘要标签","overnight_title":"全球与隔夜变化","overnight_changes":[{"title":"变化标题","text":"事实与含义"}],"china_title":"中国市场结构变化","china_changes":[{"title":"变化标题","text":"事实与含义"}],"priority_card":{"label":"明天最高优先级","title":"核心问题","note":"核心验证信号"},"priorities":[{"head":"优先项","text":"说明"}]},"assets_review":{"kicker":"跨资产验证","items":[{"asset":"资产","move":"走势数字","meaning":"谨慎解释"}]},"china_market":{"title":"今日中国市场","kicker":"结构验证","priority":"今天真正重要的事","warning":"口径或数据风险","switch":[{"label":"结构维度","metric":"今日状态","cls":"up/down/flat","note":"变化说明"}],"breadth":{"title":"市场宽度","up":"上涨数","down":"下跌数","up_pct":50,"down_pct":50,"note":"口径"},"industry":{"title":"申万行业宽度","up":"上涨行业数","down":"下跌行业数","up_pct":50,"down_pct":50,"note":"口径"}},"mainlines":{"kicker":"证据链","items":[{"tags":["事实/推断/待验证"],"title":"主线","paras":["主线推演"],"evidence":"证据与分歧","validation":"明日继续验证"}]},"today_validation":{"kicker":"下一交易日","rows":[{"subject":"观察对象","question":"今天留下的问题","look":"明天看什么","meaning":"判断含义"}]},"previous_review":{"kicker":"历史对照","rows":[{"judgment":"原判断","facts":"新增事实","state":"兑现/部分兑现/未兑现/无法判断","adjust":"框架调整"}]},"funding_industry":{"kicker":"资金与产业","items":[{"label":"项目","metric":"核心数字","cls":"up/down/flat","note":"数据点评"}]},"tracking":{"kicker":"跟踪框架","rows":[{"topic":"主题","judgment":"当前判断","support":"支持证据","counter":"反方证据","next":"下一验证","falsify":"证伪条件","period":"周期"}]},"events":{"kicker":"未来7天","rows":[{"time":"北京时间","event":"事件","markets":"影响市场","var":"验证变量"}]},"sources":["数据源及口径"]}。主线最多3条，资产5-8项，验证清单至少4项。若底稿缺少行业、事件或历史判断，保留对应字段并写明无法判断；明确区分事实、推断和待验证，不给买卖建议。`,
        {
          market: dashboard.value,
          crossAssets: assetDashboards.value,
          events: events.value,
          previousReview: previousReview.value,
        },
        (t) => (aiResult.value += t),
        controller.signal,
      );
    } catch (e) {
      if ((e as Error).name !== 'AbortError')
        aiError.value = e instanceof Error ? e.message : 'AI复盘失败';
    } finally {
      aiLoading.value = false;
      controller = null;
    }
  }
  function cancelAi() {
    controller?.abort();
  }
  function markdown() {
    return `# ${tradeDate.value} 当日市场复盘\n\n## 90秒摘要\n${quickBrief.value}\n\n## AI复盘\n${
      aiResult.value || '尚未生成'
    }\n\n## 下一交易日验证清单\n1. 成交领先行业持续性\n2. 情绪指标是否同步改善\n3. 指数与市场宽度是否同向\n4. 高成交个股承接情况\n`;
  }
  function saveReview() {
    localStorage.setItem(`vg-daily-review-${tradeDate.value}`, markdown());
  }
  function downloadMarkdown() {
    const url = URL.createObjectURL(
      new Blob([markdown()], { type: 'text/markdown;charset=utf-8' }),
    );
    const a = document.createElement('a');
    a.href = url;
    a.download = `市场复盘-${tradeDate.value}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }
  function downloadHtml() {
    const escaped = markdown().replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const html = `<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>${tradeDate.value} 当日市场复盘</title><style>body{max-width:1080px;margin:40px auto;padding:0 24px;font:15px/1.7 system-ui;color:#17212f}pre{white-space:pre-wrap}h1{border-bottom:2px solid #2f6fed;padding-bottom:12px}</style><body><pre>${escaped}</pre></body></html>`;
    const url = URL.createObjectURL(new Blob([html], { type: 'text/html;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `市场复盘-${tradeDate.value}.html`;
    anchor.click();
    URL.revokeObjectURL(url);
  }
  function printPdf() {
    window.print();
  }
</script>
<style scoped lang="less">
  .page {
    display: grid;
    gap: 14px;
    padding: 12px 4px 28px;
    color: #344054;
  }

  .hero,
  .card,
  .notice,
  .metric-grid article {
    border: 1px solid #dbe4ed;
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 2px 8px rgb(15 23 42/5%);
  }

  .hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    padding: 20px;
  }

  .eyebrow {
    margin: 0 0 4px;
    color: #758196;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  h2,
  h3 {
    margin: 0;
    color: #17212f;
  }

  p {
    color: #667085;
    line-height: 1.65;
  }

  .actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  button,
  .empty a {
    min-height: 36px;
    padding: 0 13px;
    border-radius: 7px;
    font-weight: 700;
  }

  .primary {
    border: 1px solid #2f6fed;
    background: #2f6fed;
    color: #fff;
  }

  .quiet {
    border: 1px solid #d5dee8;
    background: #fff;
    color: #526174;
  }

  .danger {
    border: 1px solid #e7b4b0;
    background: #fff5f4;
    color: #b42318;
  }

  .view-tabs {
    display: flex;
    width: max-content;
    padding: 5px;
    border: 1px solid #dbe4ed;
    border-radius: 9px;
    background: #f4f7fa;
    gap: 6px;
  }

  .view-tabs button {
    border: 0;
    background: transparent;
    color: #667085;
  }

  .view-tabs button.active {
    background: #fff;
    box-shadow: 0 1px 4px rgb(15 23 42/10%);
    color: #1f5cc4;
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }

  .metric-grid article {
    display: grid;
    gap: 6px;
    padding: 15px;
  }

  .metric-grid span,
  .metric-grid small {
    color: #667085;
  }

  .metric-grid strong {
    color: #17212f;
    font-size: 20px;
  }

  .card {
    padding: 18px;
  }

  .card header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .fact-tag,
  .inference-tag,
  .verify-tag {
    padding: 4px 8px;
    border-radius: 99px;
    font-size: 11px;
    font-weight: 800;
  }

  .fact-tag {
    background: #eaf8f3;
    color: #087a55;
  }

  .inference-tag {
    background: #eef5ff;
    color: #1f5cc4;
  }

  .verify-tag {
    background: #fff6dd;
    color: #8a6400;
  }

  .index-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-top: 14px;
  }

  .index-strip article {
    display: grid;
    padding: 11px;
    border-radius: 7px;
    background: #f7f9fc;
    gap: 4px;
  }

  .index-strip strong {
    font-size: 17px;
  }

  .up {
    color: #c0362c;
  }

  .down {
    color: #087a55;
  }

  .index-strip small {
    color: #758196;
  }

  .two-column {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }

  .rank,
  .leaders,
  .sources {
    margin: 12px 0 0;
    padding: 0;
    list-style: none;
  }

  .rank li,
  .leaders li,
  .sources li {
    display: grid;
    grid-template-columns: 1fr auto auto;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid #edf0f3;
  }

  .rank small,
  .leaders small,
  .sources small {
    color: #758196;
  }

  .note {
    padding: 10px;
    border-left: 3px solid #f0b429;
    background: #fffaf0;
    font-size: 12px;
  }

  .industry-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 9px;
    margin-top: 14px;
  }

  .industry-grid article {
    display: grid;
    gap: 4px;
    padding: 11px;
    border: 1px solid #e4eaf0;
    border-radius: 7px;
    background: #fbfcfe;
  }

  .industry-grid span,
  .industry-grid small {
    color: #758196;
  }

  .asset-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 9px;
    margin-top: 14px;
  }

  .asset-grid article {
    display: grid;
    min-width: 0;
    gap: 4px;
    padding: 11px;
    border: 1px solid #e4eaf0;
    border-radius: 7px;
    background: #fbfcfe;
  }

  .asset-grid small,
  .asset-grid em {
    overflow: hidden;
    color: #758196;
    font-size: 11px;
    font-style: normal;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .asset-grid strong {
    color: #17212f;
    font-size: 17px;
  }

  .ai-card {
    border-left: 4px solid #2f6fed;
  }

  .ai-card pre {
    max-height: 620px;
    margin: 14px 0 0;
    overflow: auto;
    color: #344054;
    font: inherit;
    line-height: 1.75;
    white-space: pre-wrap;
  }

  .empty a {
    display: inline-flex;
    align-items: center;
    margin-top: 8px;
    border: 1px solid #2f6fed;
    color: #1f5cc4;
    text-decoration: none;
  }

  .checklist {
    margin: 12px 0 0;
    padding-left: 22px;
  }

  .checklist li {
    padding: 6px;
  }

  .event-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 9px;
    margin-top: 14px;
  }

  .event-grid article {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 6px;
    padding: 12px;
    border: 1px solid #e2e8ef;
    border-radius: 7px;
    background: #fbfcfe;
  }

  .event-grid article b {
    grid-column: 1/-1;
  }

  .event-grid strong {
    color: #1f5cc4;
    font-size: 18px;
  }

  .ok {
    color: #087a55;
  }

  .warn,
  .error-text,
  .error {
    color: #b42318;
  }

  .notice {
    padding: 14px 16px;
  }

  button:focus-visible,
  a:focus-visible {
    outline: 3px solid rgb(47 111 237/22%);
    outline-offset: 2px;
  }

  @media (max-width: 900px) {
    .hero {
      flex-direction: column;
      align-items: flex-start;
    }

    .metric-grid,
    .two-column,
    .asset-grid,
    .industry-grid,
    .index-strip,
    .event-grid {
      grid-template-columns: 1fr 1fr;
    }
  }

  @media (max-width: 560px) {
    .metric-grid,
    .two-column,
    .asset-grid,
    .industry-grid,
    .index-strip,
    .event-grid {
      grid-template-columns: 1fr;
    }

    .view-tabs {
      width: 100%;
      overflow: auto;
    }
  }

  @media print {
    .hero,
    .view-tabs,
    .metric-grid,
    .card:not(.ai-card) {
      display: none;
    }

    .page,
    .ai-card {
      padding: 0;
      border: 0;
      box-shadow: none;
    }
  }
</style>
