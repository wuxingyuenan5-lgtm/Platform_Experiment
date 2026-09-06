<template>
  <PageWrapper title="资讯雷达">
    <main class="page">
      <section class="hero"
        ><div
          ><p class="eyebrow">RESEARCH INTELLIGENCE</p><h2>资讯雷达</h2
          ><p
            >事件概率、自选股公告、个股新闻与十二赛道公开资讯，统一保留原始来源和 AI 研判链路。</p
          ></div
        ><div class="actions"
          ><button class="quiet" :disabled="loading" @click="loadAll(true)">{{
            loading ? '更新中…' : '刷新全部'
          }}</button
          ><button v-if="aiLoading" class="danger" @click="cancelAi">停止提炼</button
          ><button v-else class="primary" :disabled="!currentContext.length" @click="summarize"
            >AI 批量提炼</button
          ><button
            v-if="tab === 'investment-news'"
            class="quiet"
            :disabled="bulk.running || loading || !industries.some((item) => item.items.length)"
            @click="summarizeAllIndustries"
            >{{ bulk.running ? `提炼中 ${bulk.done}/${bulk.total}` : '一键提炼全部赛道' }}</button
          ></div
        ></section
      >
      <nav class="main-tabs"
        ><button
          v-for="item in tabs"
          :key="item.key"
          :class="{ active: tab === item.key }"
          @click="tab = item.key"
          >{{ item.name }}<small>{{ item.count }}</small></button
        ></nav
      >
      <section v-if="error" class="notice error">{{ error }}</section>
      <section v-if="partialFailures.length" class="notice warning"
        >{{ partialFailures.length }} 个公开来源本次加载失败：{{
          partialFailures.map((item) => item.source).join('、')
        }}。其他来源结果仍可用。</section
      >
      <section v-if="aiResult || aiError" class="card ai-summary"
        ><header
          ><div><p class="eyebrow">AI DIGEST</p><h3>AI 情报提炼（待复核）</h3></div
          ><button class="quiet" @click="saveNote">保存为研究笔记</button></header
        ><p v-if="aiError" class="error">{{ aiError }}</p
        ><pre v-else>{{ aiResult }}</pre>
      </section>

      <section v-if="tab === 'events'" class="card"
        ><header
          ><div><p class="eyebrow">EVENT PROBABILITY</p><h3>关键事件概率</h3></div
          ><span>{{ macroStatus }}</span></header
        ><div class="event-grid"
          ><article v-for="item in events" :key="item.id"
            ><span>{{ categoryName(item.category) }}</span
            ><b>{{ item.label }}</b
            ><strong>{{ Number(item.probability).toFixed(1) }}%</strong
            ><small>更新 {{ formatDate(item.history.at(-1)?.observedAt) }}</small></article
          ><p v-if="!events.length" class="empty">当前没有可用的事件概率数据。</p></div
        ></section
      >

      <template v-else-if="tab === 'filings' || tab === 'stock-news'">
        <section class="filters"
          ><label
            >自选分组<select v-model="groupFilter"
              ><option value="">全部分组</option
              ><option v-for="item in groups" :key="item" :value="item">{{ item }}</option></select
            ></label
          ><label
            >个股<select v-model="stockFilter"
              ><option value="">全部个股</option
              ><option v-for="item in filteredWatchlist" :key="item.code" :value="item.code"
                >{{ item.name }} {{ item.code }}</option
              ></select
            ></label
          ><label
            >时间范围<select v-model.number="days"
              ><option :value="1">近1日</option
              ><option :value="3">近3日</option
              ><option :value="7">近7日</option
              ><option :value="30">近30日</option
              ><option :value="0">全部日期</option></select
            ></label
          ><label v-if="tab === 'filings'" class="check"
            ><input v-model="earningsOnly" type="checkbox" />仅财报/业绩</label
          ><button v-if="tab === 'filings'" class="quiet" @click="halfYearOpen = true"
            >半年报追踪</button
          ></section
        >
        <section class="card"
          ><header
            ><div
              ><p class="eyebrow">WATCHLIST FEED</p
              ><h3>{{ tab === 'filings' ? '自选股公告' : '自选股公开新闻' }}</h3></div
            ><span>{{ visibleWatchItems.length }} 条</span></header
          ><a
            v-for="item in visibleWatchItems"
            :key="item.id"
            :href="item.url || undefined"
            :target="item.url ? '_blank' : undefined"
            class="feed-row"
            ><time>{{ formatDate(item.date) }}</time
            ><span>{{ item.stockName }} · {{ item.stockCode }}</span
            ><strong>{{ item.title }}</strong
            ><em>{{ item.source }}</em></a
          ><p v-if="!visibleWatchItems.length" class="empty"
            >当前筛选条件下无数据。先在 A 股研究中加入自选股，再刷新本页。</p
          ></section
        >
      </template>

      <template v-else>
        <nav class="industry-tabs"
          ><button
            v-for="item in industries"
            :key="item.key"
            :class="{ active: item.key === industryKey }"
            @click="industryKey = item.key"
            ><i :style="{ background: item.accent }"></i>{{ item.name
            }}<small>{{ item.items.length }}</small></button
          ></nav
        >
        <section class="card"
          ><header
            ><div
              ><p class="eyebrow">INVESTMENT NEWS</p
              ><h3>{{ activeIndustry?.name || '公开资讯' }}</h3></div
            ><div class="industry-actions"
              ><span>来源直达 · {{ generatedAt }}</span
              ><button
                class="quiet"
                :disabled="aiLoading || !activeIndustry?.items.length"
                @click="summarizeIndustry(activeIndustry)"
                >{{
                  industryDigests[activeIndustry?.key || ''] ? '重新提炼' : '提炼本赛道'
                }}</button
              ></div
            ></header
          ><article v-if="industryDigests[activeIndustry?.key || '']" class="industry-digest"
            ><div
              ><p class="eyebrow">AI TODAY DIGEST</p><b>{{ activeIndustry?.name }} 今日要点</b></div
            ><button class="quiet" @click="saveIndustryNote(activeIndustry)">保存为研究笔记</button
            ><pre>{{ industryDigests[activeIndustry?.key || ''] }}</pre></article
          ><a
            v-for="item in activeIndustry?.items"
            :key="`${item.source}-${item.title}`"
            :href="item.url"
            target="_blank"
            rel="noreferrer"
            class="feed-row"
            ><time>{{ item.publishedAt }}</time
            ><span>{{ item.source }}</span
            ><strong>{{ item.title }}</strong
            ><em>原文 ↗</em></a
          ><p v-if="!activeIndustry?.items.length" class="empty">该赛道暂无可用资讯。</p></section
        >
      </template>
      <div v-if="halfYearOpen" class="modal-mask" @click.self="halfYearOpen = false">
        <section class="half-year" role="dialog" aria-modal="true" aria-label="自选股半年报追踪">
          <header
            ><div><p class="eyebrow">HALF-YEAR TRACKER</p><h3>自选股半年报追踪</h3></div
            ><button class="quiet" @click="halfYearOpen = false">关闭</button></header
          >
          <nav class="half-year-tabs"
            ><button
              v-for="item in [1, 3, 7, 30]"
              :key="item"
              :class="{ active: halfYearDays === item }"
              @click="halfYearDays = item"
              >近 {{ item }} 日</button
            ></nav
          >
          <div class="half-year-groups"
            ><article
              ><h4>已披露</h4
              ><a
                v-for="item in halfYearDetails"
                :key="item.id"
                :href="item.url || undefined"
                target="_blank"
                ><b>{{ item.stockName }} · {{ item.stockCode }}</b
                ><span>{{ item.title }}</span
                ><small>{{ formatDate(item.date) }}</small
                ><dl v-if="item.financials"
                  ><div
                    ><dt>报告期</dt><dd>{{ item.financials.period || '—' }}</dd></div
                  ><div
                    ><dt>归母净利润</dt><dd>{{ item.financials.netProfit || '—' }}</dd></div
                  ><div
                    ><dt>同比</dt><dd>{{ item.financials.netProfitYoy || '—' }}</dd></div
                  ><div
                    ><dt>机构覆盖</dt><dd>{{ item.analystCount ?? '—' }}</dd></div
                  ></dl
                ></a
              ><p v-if="!halfYearDetails.length">所选时间内没有检索到半年报披露。</p></article
            ><article
              ><h4>核对口径</h4
              ><ol
                ><li>确认报告期与公告类型，排除说明会、审计报告和募集资金公告。</li
                ><li>实际净利润、同比与一致预期回到原公告及财务模块交叉验证。</li
                ><li>AI 只提炼差异原因，不替代原始财务披露。</li></ol
              ></article
            ></div
          >
        </section>
      </div>
    </main>
  </PageWrapper>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { PageWrapper } from '@/components/Page';
  import {
    getMacroExpectations,
    getStockSnapshot,
    type MacroExpectationEvent,
    type StockSnapshotResponse,
  } from '@/api/hedgeResearch';
  import {
    getAccountResearchWatchlist,
    type AccountResearchWatchlistItem,
  } from '@/api/platform/researchWatchlist';
  import {
    getNewsRadar,
    streamFinancialAi,
    type RadarIndustry,
    type RadarPartialFailure,
  } from '@/api/financialAi';

  interface WatchFeedItem {
    id: string;
    stockCode: string;
    stockName: string;
    group: string;
    title: string;
    date: string;
    source: string;
    url: string;
  }
  const tab = ref('investment-news'),
    industries = ref<RadarIndustry[]>([]),
    industryKey = ref('macro'),
    events = ref<MacroExpectationEvent[]>([]),
    macroStatus = ref('—'),
    watchlist = ref<AccountResearchWatchlistItem[]>([]),
    filings = ref<WatchFeedItem[]>([]),
    stockNews = ref<WatchFeedItem[]>([]),
    loading = ref(false),
    error = ref(''),
    generatedAt = ref('—'),
    partialFailures = ref<RadarPartialFailure[]>([]),
    groupFilter = ref(''),
    stockFilter = ref(''),
    days = ref(7),
    earningsOnly = ref(true),
    aiLoading = ref(false),
    aiResult = ref(''),
    aiError = ref(''),
    halfYearOpen = ref(false),
    halfYearDays = ref(3);
  const stockSnapshots = ref<Record<string, StockSnapshotResponse>>({});
  const industryDigests = ref<Record<string, string>>({});
  const bulk = ref({ running: false, done: 0, total: 0 });
  let controller: AbortController | null = null;
  const activeIndustry = computed(
    () => industries.value.find((i) => i.key === industryKey.value) || industries.value[0],
  );
  const groups = computed(() => [...new Set(watchlist.value.map((i) => i.group).filter(Boolean))]);
  const filteredWatchlist = computed(() =>
    watchlist.value.filter((i) => !groupFilter.value || i.group === groupFilter.value),
  );
  const visibleWatchItems = computed(() => {
    const base = tab.value === 'filings' ? filings.value : stockNews.value;
    const cutoff = days.value ? Date.now() - days.value * 864e5 : 0;
    return base.filter(
      (i) =>
        (!groupFilter.value || i.group === groupFilter.value) &&
        (!stockFilter.value || i.stockCode === stockFilter.value) &&
        (!earningsOnly.value || /业绩|年报|季报|半年报|财报|预告/.test(i.title)) &&
        (!days.value || !i.date || new Date(i.date).getTime() >= cutoff),
    );
  });
  const tabs = computed(() => [
    { key: 'events', name: '事件概率', count: events.value.length },
    { key: 'filings', name: 'A股公告', count: filings.value.length },
    { key: 'stock-news', name: '公开新闻', count: stockNews.value.length },
    {
      key: 'investment-news',
      name: 'Investment News',
      count: industries.value.reduce((n, i) => n + i.items.length, 0),
    },
  ]);
  const currentContext = computed<any[]>(() =>
    tab.value === 'events'
      ? events.value
      : tab.value === 'filings' || tab.value === 'stock-news'
      ? visibleWatchItems.value
      : activeIndustry.value?.items || [],
  );
  const halfYearRows = computed(() => {
    const cutoff = Date.now() - halfYearDays.value * 864e5;
    return filings.value.filter(
      (item) =>
        /半年度报告|半年报|中期报告/.test(item.title) &&
        (!item.date || new Date(item.date).getTime() >= cutoff),
    );
  });
  const halfYearDetails = computed(() =>
    halfYearRows.value.map((item) => {
      const snapshot = stockSnapshots.value[item.stockCode];
      const financials = snapshot?.modules.financials?.data as
        | { period?: string; netProfit?: string; netProfitYoy?: string }
        | undefined;
      const consensus = snapshot?.modules.consensus?.data as { analystCount?: number } | undefined;
      return { ...item, financials, analystCount: consensus?.analystCount };
    }),
  );
  function rows(value: unknown) {
    if (Array.isArray(value)) return value;
    if (value && typeof value === 'object') {
      const object = value as Record<string, unknown>;
      const found = Object.values(object).find(Array.isArray);
      return Array.isArray(found) ? found : [];
    }
    return [];
  }
  function mapFeed(
    value: unknown,
    stock: AccountResearchWatchlistItem,
    kind: string,
  ): WatchFeedItem[] {
    return rows(value)
      .slice(0, 30)
      .map((raw, index) => {
        const item = raw as Record<string, unknown>;
        return {
          id: `${kind}-${stock.code}-${index}-${item.title || item.notice_date || ''}`,
          stockCode: stock.code,
          stockName: stock.name,
          group: stock.group,
          title: String(
            item.title || item.notice_title || item.news_title || item.公告标题 || '未命名信息',
          ),
          date: String(item.date || item.notice_date || item.publish_time || item.公告日期 || ''),
          source: String(item.source || item.media_name || item.文章来源 || kind),
          url: String(item.url || item.notice_url || item.article_url || ''),
        };
      });
  }
  async function loadAll(force = false) {
    loading.value = true;
    error.value = '';
    try {
      const [radar, macro, account] = await Promise.all([
        getNewsRadar(force),
        getMacroExpectations(),
        getAccountResearchWatchlist(),
      ]);
      industries.value = radar.industries;
      generatedAt.value = radar.generatedAt.replace('T', ' ').slice(0, 16);
      partialFailures.value = radar.partialFailures || [];
      events.value = macro.events;
      macroStatus.value = macro.status;
      watchlist.value = account.items;
      filings.value = [];
      stockNews.value = [];
      stockSnapshots.value = {};
      void hydrateWatchlist(account.items);
    } catch (e) {
      error.value = e instanceof Error ? e.message : '资讯雷达暂不可用';
    } finally {
      loading.value = false;
    }
  }
  async function hydrateWatchlist(items: AccountResearchWatchlistItem[]) {
    if (!items.length) return;
    try {
      const snapshots = await Promise.allSettled(
        items.slice(0, 20).map((i) => getStockSnapshot(i.code)),
      );
      snapshots.forEach((result, index) => {
        if (result.status !== 'fulfilled') return;
        const stock = items[index];
        stockSnapshots.value[stock.code] = result.value;
        filings.value.push(...mapFeed(result.value.modules.announcements?.data, stock, '公告'));
        stockNews.value.push(...mapFeed(result.value.modules.news?.data, stock, '新闻'));
      });
    } catch {
      // Watchlist enrichment is best-effort; the main radar remains available.
    }
  }
  async function summarize() {
    if (!currentContext.value.length) return;
    controller = new AbortController();
    aiLoading.value = true;
    aiResult.value = '';
    aiError.value = '';
    try {
      await streamFinancialAi(
        `请对当前“${
          tabs.value.find((i) => i.key === tab.value)?.name
        }”内容批量提炼：去重合并事件，给出时间线、影响路径、受影响行业或公司、反方证据、信息缺口和后续验证点。逐条区分事实与推断，不给交易建议。`,
        currentContext.value.slice(0, 80),
        (t) => (aiResult.value += t),
        controller.signal,
      );
    } catch (e) {
      if ((e as Error).name !== 'AbortError')
        aiError.value = e instanceof Error ? e.message : 'AI提炼失败';
    } finally {
      aiLoading.value = false;
      controller = null;
    }
  }
  async function summarizeIndustry(industry: RadarIndustry | undefined) {
    if (!industry?.items.length) return;
    controller = new AbortController();
    aiLoading.value = true;
    aiError.value = '';
    let result = '';
    try {
      await streamFinancialAi(
        `提炼“${industry.name}”赛道今日要点3-5条。先去重同一事件，每条不超过50字，并补充影响路径、反方证据和下一验证点。只根据给定标题和来源判断，不补造正文或事实，不给交易建议。`,
        industry.items.slice(0, 30),
        (text) => {
          result += text;
          industryDigests.value = { ...industryDigests.value, [industry.key]: result };
        },
        controller.signal,
      );
    } catch (e) {
      if ((e as Error).name !== 'AbortError')
        aiError.value = e instanceof Error ? e.message : '赛道提炼失败';
    } finally {
      aiLoading.value = false;
      controller = null;
    }
  }
  async function summarizeAllIndustries() {
    const targets = industries.value.filter((item) => item.items.length);
    bulk.value = { running: true, done: 0, total: targets.length };
    for (const industry of targets) {
      if (!bulk.value.running) break;
      await summarizeIndustry(industry);
      bulk.value = { ...bulk.value, done: bulk.value.done + 1 };
    }
    bulk.value = { ...bulk.value, running: false };
  }
  function cancelAi() {
    controller?.abort();
    bulk.value = { ...bulk.value, running: false };
  }
  function saveNote() {
    localStorage.setItem(
      `vg-radar-note-${Date.now()}`,
      JSON.stringify({
        tab: tab.value,
        industry: industryKey.value,
        text: aiResult.value,
        savedAt: new Date().toISOString(),
      }),
    );
  }
  function saveIndustryNote(industry: RadarIndustry | undefined) {
    if (!industry) return;
    const text = industryDigests.value[industry.key];
    if (!text) return;
    localStorage.setItem(
      `vg-radar-note-${Date.now()}`,
      JSON.stringify({
        tab: 'investment-news',
        industry: industry.key,
        title: `${industry.name} 今日要点`,
        text,
        savedAt: new Date().toISOString(),
      }),
    );
  }
  function formatDate(v: unknown) {
    if (!v) return '—';
    const d = new Date(String(v));
    return Number.isNaN(d.getTime())
      ? String(v).slice(0, 16)
      : d.toLocaleString('zh-CN', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        });
  }
  function categoryName(v: string) {
    return (
      (
        {
          monetary_policy: '货币政策',
          macro: '宏观',
          geopolitics: '地缘政治',
          election: '选举',
        } as Record<string, string>
      )[v] || v
    );
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
  .filters {
    padding: 18px;
    border: 1px solid #dbe4ed;
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 2px 8px rgb(15 23 42/5%);
  }

  .hero,
  .card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
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
    line-height: 1.6;
  }

  .actions {
    display: flex;
    gap: 8px;
  }

  .primary,
  .quiet,
  .danger,
  .main-tabs button,
  .industry-tabs button {
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

  .main-tabs,
  .industry-tabs {
    display: flex;
    gap: 7px;
    overflow: auto;
  }

  .main-tabs {
    padding: 5px;
    border: 1px solid #dbe4ed;
    border-radius: 9px;
    background: #f3f6f9;
  }

  .main-tabs button,
  .industry-tabs button {
    border: 0;
    background: transparent;
    color: #667085;
    white-space: nowrap;
  }

  .main-tabs button.active {
    background: #fff;
    box-shadow: 0 1px 4px rgb(15 23 42/10%);
    color: #1f5cc4;
  }

  .main-tabs small,
  .industry-tabs small {
    margin-left: 7px;
  }

  .industry-tabs {
    flex-wrap: wrap;
  }

  .industry-tabs button {
    border: 1px solid #dbe4ed;
    background: #fff;
  }

  .industry-tabs button.active {
    border-color: #2f6fed;
    background: #eef5ff;
    color: #1f5cc4;
  }

  .industry-tabs i {
    display: inline-block;
    width: 7px;
    height: 7px;
    margin-right: 6px;
    border-radius: 50%;
  }

  .filters {
    display: flex;
    gap: 14px;
    align-items: end;
  }

  .filters label {
    display: grid;
    gap: 5px;
    color: #667085;
    font-size: 12px;
    font-weight: 700;
  }

  .filters select {
    min-width: 160px;
    height: 36px;
    padding: 0 9px;
    border: 1px solid #d5dee8;
    border-radius: 6px;
    background: #fff;
  }

  .filters .check {
    display: flex;
    align-items: center;
    padding-bottom: 8px;
  }

  .event-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-top: 14px;
  }

  .event-grid article {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 7px;
    padding: 14px;
    border: 1px solid #e2e8ef;
    border-radius: 8px;
    background: #fbfcfe;
  }

  .event-grid article > b {
    grid-column: 1/-1;
  }

  .event-grid span,
  .event-grid small {
    color: #758196;
  }

  .event-grid strong {
    color: #1f5cc4;
    font-size: 22px;
  }

  .feed-row {
    display: grid;
    grid-template-columns: 105px 180px 1fr 90px;
    gap: 12px;
    padding: 12px 0;
    border-bottom: 1px solid #edf0f3;
    color: #344054;
    text-decoration: none;
  }

  .feed-row time,
  .feed-row span,
  .feed-row em {
    color: #758196;
    font-size: 12px;
    font-style: normal;
  }

  .feed-row:hover strong {
    color: #1f5cc4;
  }

  .industry-actions {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .industry-actions > span {
    color: #758196;
    font-size: 12px;
  }

  .industry-digest {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 10px;
    margin: 14px 0;
    padding: 14px;
    border: 1px solid #bfd2ff;
    border-radius: 8px;
    background: #f6f9ff;
  }

  .industry-digest pre {
    grid-column: 1/-1;
    margin: 0;
    color: #344054;
    font: inherit;
    line-height: 1.7;
    white-space: pre-wrap;
  }

  .ai-summary {
    border-left: 4px solid #2f6fed;
  }

  .ai-summary pre {
    max-height: 500px;
    overflow: auto;
    font: inherit;
    line-height: 1.72;
    white-space: pre-wrap;
  }

  .error {
    color: #b42318;
  }

  .empty {
    padding: 18px 0;
  }

  .modal-mask {
    display: grid;
    position: fixed;
    z-index: 1000;
    padding: 24px;
    background: rgb(15 23 42 / 42%);
    inset: 0;
    place-items: center;
  }

  .half-year {
    width: min(920px, 100%);
    max-height: 82vh;
    padding: 20px;
    overflow: auto;
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 24px 70px rgb(15 23 42 / 24%);
  }

  .half-year > header,
  .half-year-groups {
    display: flex;
    justify-content: space-between;
    gap: 18px;
  }

  .half-year-tabs {
    display: flex;
    gap: 6px;
    margin: 16px 0;
  }

  .half-year-tabs button {
    padding: 7px 10px;
    border: 1px solid #dbe4ed;
    border-radius: 6px;
    background: #fff;
    color: #667085;
  }

  .half-year-tabs button.active {
    border-color: #2f6fed;
    background: #eef5ff;
    color: #1f5cc4;
  }

  .half-year-groups article {
    flex: 1;
    padding: 14px;
    border: 1px solid #e2e8ef;
    border-radius: 8px;
  }

  .half-year-groups a {
    display: grid;
    gap: 5px;
    padding: 10px 0;
    border-bottom: 1px solid #edf0f3;
    color: #344054;
    text-decoration: none;
  }

  .half-year-groups small {
    color: #758196;
  }

  .half-year-groups dl {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 6px;
    margin: 5px 0 0;
  }

  .half-year-groups dl div {
    padding: 7px;
    border-radius: 5px;
    background: #f5f7fa;
  }

  .half-year-groups dt {
    color: #758196;
    font-size: 11px;
  }

  .half-year-groups dd {
    margin: 2px 0 0;
    color: #17212f;
    font-weight: 700;
  }

  button:focus-visible,
  a:focus-visible,
  select:focus-visible {
    outline: 3px solid rgb(47 111 237/22%);
    outline-offset: 2px;
  }

  @media (max-width: 850px) {
    .hero,
    .card header {
      flex-direction: column;
      align-items: flex-start;
    }

    .industry-actions {
      flex-direction: column;
      align-items: flex-start;
    }

    .filters {
      flex-direction: column;
      align-items: stretch;
    }

    .event-grid {
      grid-template-columns: 1fr;
    }

    .half-year-groups {
      flex-direction: column;
    }

    .feed-row {
      grid-template-columns: 1fr;
    }

    .industry-tabs {
      flex-wrap: nowrap;
    }
  }
</style>
