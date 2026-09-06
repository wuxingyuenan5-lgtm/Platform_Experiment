<template>
  <PageWrapper title="个股分析">
    <main class="stock-page" data-testid="financial-ai-stock-analysis">
      <section class="query-card">
        <div
          ><p class="eyebrow">STOCK FACT BASE</p><h2>个股事实底稿</h2
          ><p>行情、估值、财报、资金与事件按平台研究接口读取；AI 未接入时仅展示可复核事实。</p></div
        >
        <form @submit.prevent="query"
          ><input
            v-model.trim="code"
            maxlength="24"
            placeholder="A股代码 / AAPL / 00700 / 005930.KS"
          /><button :disabled="loading" type="submit">{{ loading ? '查询中…' : '查询个股' }}</button
          ><button v-if="aiLoading" class="danger" type="button" @click="cancelAi">停止</button
          ><button v-else :disabled="!snapshot && !globalStock" type="button" @click="runAiAnalysis"
            >问AI</button
          ></form
        >
      </section>
      <section v-if="error" class="notice error">{{ error }}</section>
      <section v-else-if="loading" class="notice">正在并行读取个股数据…</section>
      <section v-else-if="snapshot || globalStock" class="result-card">
        <header
          ><div
            ><p class="eyebrow">{{ securityCode }}</p
            ><h2>{{ securityName }}</h2></div
          ><span v-if="snapshot">数据完整度 {{ Number(snapshot.completenessPct).toFixed(0) }}%</span
          ><span v-else>{{ globalStock?.market }} · {{ globalStock?.currency }}</span></header
        >
        <section v-if="globalStock" class="global-overview"
          ><nav class="period-tabs" aria-label="K线周期"
            ><button
              v-for="item in chartPeriods"
              :key="item.key"
              :class="{ active: chartPeriod === item.key }"
              :disabled="chartLoading"
              @click="changeChartPeriod(item.key)"
              >{{ item.name }}</button
            ><i></i
            ><button
              v-for="item in indicatorControls"
              :key="item.key"
              :class="{ active: chartIndicators[item.key] }"
              @click="chartIndicators[item.key] = !chartIndicators[item.key]"
              >{{ item.name }}</button
            ></nav
          ><article
            ><small>最新价</small><b>{{ formatPrice(globalStock.price) }}</b></article
          ><article
            ><small>日涨跌</small
            ><b :class="Number(globalStock.changePct) >= 0 ? 'rise' : 'fall'">{{
              formatPercent(globalStock.changePct)
            }}</b></article
          ><article
            ><small>52周高</small><b>{{ formatPrice(globalStock.fiftyTwoWeekHigh) }}</b></article
          ><article
            ><small>52周低</small><b>{{ formatPrice(globalStock.fiftyTwoWeekLow) }}</b></article
          ><article
            ><small>开盘</small><b>{{ formatPrice(globalStock.open) }}</b></article
          ><article
            ><small>最高</small><b>{{ formatPrice(globalStock.dayHigh) }}</b></article
          ><article
            ><small>最低</small><b>{{ formatPrice(globalStock.dayLow) }}</b></article
          ><article
            ><small>成交量</small><b>{{ compactNumber(globalStock.volume) }}</b></article
          ><article
            ><small>成交额</small><b>{{ compactNumber(globalStock.amount) }}</b></article
          ><article
            ><small>总市值</small><b>{{ compactNumber(globalStock.marketCap) }}</b></article
          ><article
            ><small>昨收</small><b>{{ formatPrice(globalStock.previousClose) }}</b></article
          ><svg
            v-if="candles.length"
            viewBox="0 0 600 180"
            preserveAspectRatio="none"
            role="img"
            :aria-label="`${chartPeriods.find((item) => item.key === chartPeriod)?.name} K线`"
          >
            <g v-for="item in candles" :key="item.key">
              <line
                :x1="item.x"
                :x2="item.x"
                :y1="item.highY"
                :y2="item.lowY"
                :stroke="item.up ? '#c0362c' : '#087a55'"
                vector-effect="non-scaling-stroke"
              />
              <rect
                :x="item.x - item.width / 2"
                :y="item.bodyY"
                :width="item.width"
                :height="item.bodyHeight"
                :fill="item.up ? '#c0362c' : '#087a55'"
              />
              <rect
                :x="item.x - item.width / 2"
                :y="178 - item.volumeHeight"
                :width="item.width"
                :height="item.volumeHeight"
                :fill="item.up ? '#f0b5b0' : '#9fd4c2'"
              />
            </g>
            <polyline
              v-for="line in indicatorPaths"
              :key="line.key"
              :points="line.points"
              fill="none"
              :stroke="line.color"
              stroke-width="1.3"
              vector-effect="non-scaling-stroke"
            /></svg
          ><p v-else class="chart-empty">{{ chartLoading ? 'K线加载中…' : '暂无K线数据' }}</p
          ><a :href="globalStock.sourceUrl" target="_blank" rel="noreferrer"
            >来源：{{ globalStock.source }} ↗</a
          ></section
        >
        <section v-if="globalStock?.metrics" class="module-card global-metrics">
          <header
            ><div><h3>关键财务指标</h3><small>东财 GMAININDICATOR · 原生币种</small></div
            ><span>{{ globalStock.metrics.reportDate || '最新报告期' }}</span></header
          ><div class="metric-list"
            ><article
              ><small>营业收入</small><b>{{ compactNumber(globalStock.metrics.revenue) }}</b
              ><em>同比 {{ formatPercent(globalStock.metrics.revenueYoy) }}</em></article
            ><article
              ><small>归母净利</small
              ><b>{{ compactNumber(globalStock.metrics.netProfit) }}</b></article
            ><article
              ><small>每股收益 EPS</small><b>{{ formatPrice(globalStock.metrics.eps) }}</b></article
            ><article
              ><small>ROE</small><b>{{ formatPercent(globalStock.metrics.roe) }}</b></article
            ><article
              ><small>毛利率</small
              ><b>{{ formatPercent(globalStock.metrics.grossMargin) }}</b></article
            ><article
              ><small>净利率</small
              ><b>{{ formatPercent(globalStock.metrics.netMargin) }}</b></article
            ><article
              ><small>资产负债率</small
              ><b>{{ formatPercent(globalStock.metrics.debtRatio) }}</b></article
            ></div
          ></section
        >
        <section class="analysis-toolbar">
          <select v-model="analysisMode" aria-label="AI分析模式"
            ><option value="full">五维深度分析</option
            ><option value="bull">多头论证</option
            ><option value="bear">空头论证</option
            ><option value="debate">多空辩论</option></select
          ><textarea
            v-model="question"
            rows="2"
            placeholder="可追加你的研究问题，例如：重点检查现金流质量与估值分位"
          ></textarea
          ><button :disabled="(!snapshot && !globalStock) || aiLoading" @click="runAiAnalysis">{{
            aiLoading ? '分析中…' : '执行深度分析'
          }}</button
          ><button class="plain" @click="toggleAll">{{
            allExpanded ? '全部收起' : '全部展开'
          }}</button
          ><button class="plain" @click="saveRecord">保存研究记录</button></section
        ><div class="suggestions"
          ><span>快捷问题</span
          ><button v-for="item in suggestions" :key="item" @click="question = item">{{
            item
          }}</button></div
        >
        <section v-if="aiResult || aiError" class="ai-panel"
          ><header
            ><div><p class="eyebrow">AI SYNTHESIS</p><h3>AI 个股分析（待复核）</h3></div
            ><span>事实 → 推断 → 验证</span></header
          ><p v-if="aiError" class="error">{{ aiError }}</p
          ><div v-else-if="analysisMode === 'debate' && debateResult.judge" class="debate-grid"
            ><article
              ><b>多头研究员</b><pre>{{ debateResult.bull }}</pre></article
            ><article
              ><b>空头研究员</b><pre>{{ debateResult.bear }}</pre></article
            ><article class="judge"
              ><b>中立裁决</b><pre>{{ debateResult.judge }}</pre>
            </article></div
          ><pre v-else>{{ aiResult }}</pre>
        </section>
        <template v-if="snapshot">
          <article v-for="item in modules" :key="item.key" class="module-card">
            <button class="module-head" @click="toggle(item.key)"
              ><div
                ><h3>{{ item.label }}</h3
                ><small>{{ item.result?.meta.message || summary(item.result?.data) }}</small></div
              ><span>{{ expanded.has(item.key) ? '收起 −' : '展开 +' }}</span></button
            >
            <div v-if="expanded.has(item.key)" class="module-body"
              ><ResearchSourceState v-if="item.result" :meta="item.result.meta" />
              <ResearchDataRenderer v-if="item.result?.data" :value="item.result.data" />
              <p v-else class="empty">{{ item.result?.meta.message || '暂无数据' }}</p></div
            >
          </article>
        </template>
      </section>
      <section v-else class="notice"
        >输入代码以构建个股事实底稿；该页面不会直接给出买卖建议。</section
      >
    </main>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { PageWrapper } from '@/components/Page';
  import {
    getStockSnapshot,
    type ResearchModuleResult,
    type StockSnapshotResponse,
  } from '@/api/hedgeResearch';
  import ResearchDataRenderer from '@/views/hedgeBoard/research/components/ResearchDataRenderer.vue';
  import ResearchSourceState from '@/views/hedgeBoard/research/components/ResearchSourceState.vue';
  import { getGlobalStock, streamFinancialAi, type GlobalStockSnapshot } from '@/api/financialAi';

  const code = ref('');
  const loading = ref(false);
  const error = ref('');
  const snapshot = ref<StockSnapshotResponse | null>(null);
  const globalStock = ref<GlobalStockSnapshot | null>(null);
  const chartPeriod = ref<'60m' | 'day' | 'week' | 'month'>('day');
  const chartLoading = ref(false);
  const chartPeriods = [
    { key: '60m', name: '1小时' },
    { key: 'day', name: '日K' },
    { key: 'week', name: '周K' },
    { key: 'month', name: '月K' },
  ] as const;
  type IndicatorKey = 'ma5' | 'ma10' | 'ma20' | 'boll';
  const chartIndicators = ref<Record<IndicatorKey, boolean>>({
    ma5: true,
    ma10: true,
    ma20: false,
    boll: false,
  });
  const indicatorControls: Array<{ key: IndicatorKey; name: string }> = [
    { key: 'ma5', name: 'MA5' },
    { key: 'ma10', name: 'MA10' },
    { key: 'ma20', name: 'MA20' },
    { key: 'boll', name: 'BOLL' },
  ];
  const aiLoading = ref(false);
  const aiResult = ref('');
  const aiError = ref('');
  const debateResult = ref({ bull: '', bear: '', judge: '' });
  const question = ref('');
  const analysisMode = ref('full');
  const expanded = ref(
    new Set(['quoteValuation', 'consensus', 'financials', 'valuationPercentile', 'fundFlow']),
  );
  let controller: AbortController | null = null;
  const suggestions = [
    '这个估值贵不贵',
    '盈利与现金流质量如何',
    '近期研报分歧点',
    '最重要的风险是什么',
  ];
  const definitions = [
    { key: 'quoteValuation', label: '行情与估值' },
    { key: 'consensus', label: '一致预期' },
    { key: 'financials', label: '财报速览' },
    { key: 'valuationPercentile', label: '历史估值分位' },
    { key: 'fundFlow', label: '资金流' },
    { key: 'reports', label: '研报' },
    { key: 'announcements', label: '公告' },
    { key: 'news', label: '个股新闻' },
    { key: 'margin', label: '融资融券' },
    { key: 'holders', label: '股东户数' },
    { key: 'dividends', label: '分红' },
    { key: 'blockTrades', label: '大宗交易' },
    { key: 'dragonTiger', label: '龙虎榜' },
    { key: 'lockup', label: '限售解禁' },
    { key: 'investorQa', label: '投资者互动' },
    { key: 'shenwan', label: '板块归属 · 概念' },
  ] as const;
  const modules = computed(() =>
    definitions.map((definition) => ({
      ...definition,
      result: snapshot.value?.modules[definition.key] as ResearchModuleResult | undefined,
    })),
  );
  const allExpanded = computed(() => expanded.value.size === definitions.length);
  const securityCode = computed(
    () => snapshot.value?.securityCode || globalStock.value?.symbol || '—',
  );
  const securityName = computed(
    () => snapshot.value?.securityName || globalStock.value?.name || securityCode.value,
  );
  const candles = computed(() => {
    const rows = (globalStock.value?.chart || [])
      .filter((item) =>
        [item.open, item.high, item.low, item.close].every((value) =>
          Number.isFinite(Number(value)),
        ),
      )
      .slice(-90);
    if (!rows.length) return [];
    const min = Math.min(...rows.map((item) => Number(item.low)));
    const max = Math.max(...rows.map((item) => Number(item.high)));
    const span = max - min || 1;
    const step = 600 / rows.length;
    const maxVolume = Math.max(...rows.map((item) => Number(item.volume || 0)), 1);
    const y = (value: number) => 132 - ((value - min) / span) * 124;
    return rows.map((item, index) => {
      const open = Number(item.open);
      const close = Number(item.close);
      const openY = y(open);
      const closeY = y(close);
      return {
        key: item.time,
        x: index * step + step / 2,
        width: Math.max(1.5, step * 0.62),
        highY: y(Number(item.high)),
        lowY: y(Number(item.low)),
        bodyY: Math.min(openY, closeY),
        bodyHeight: Math.max(1.5, Math.abs(openY - closeY)),
        volumeHeight: (Number(item.volume || 0) / maxVolume) * 32,
        up: close >= open,
      };
    });
  });
  const indicatorPaths = computed(() => {
    const rows = (globalStock.value?.chart || [])
      .filter((item) => Number.isFinite(Number(item.close)))
      .slice(-90);
    if (!rows.length) return [];
    const lows = rows.map((item) => Number(item.low ?? item.close));
    const highs = rows.map((item) => Number(item.high ?? item.close));
    const min = Math.min(...lows);
    const max = Math.max(...highs);
    const span = max - min || 1;
    const step = 600 / rows.length;
    const y = (value: number) => 132 - ((value - min) / span) * 124;
    const closes = rows.map((item) => Number(item.close));
    const points = (window: number, offset = 0) =>
      closes
        .map((_, index) => {
          if (index < window - 1) return '';
          const sample = closes.slice(index - window + 1, index + 1);
          const mean = sample.reduce((sum, value) => sum + value, 0) / sample.length;
          const variance =
            sample.reduce((sum, value) => sum + (value - mean) ** 2, 0) / sample.length;
          const value = mean + offset * 2 * Math.sqrt(variance);
          return `${(index * step + step / 2).toFixed(2)},${y(value).toFixed(2)}`;
        })
        .filter(Boolean)
        .join(' ');
    const lines: Array<{ key: string; color: string; points: string }> = [];
    if (chartIndicators.value.ma5) lines.push({ key: 'ma5', color: '#d97706', points: points(5) });
    if (chartIndicators.value.ma10)
      lines.push({ key: 'ma10', color: '#2563eb', points: points(10) });
    if (chartIndicators.value.ma20)
      lines.push({ key: 'ma20', color: '#7c3aed', points: points(20) });
    if (chartIndicators.value.boll) {
      lines.push({ key: 'boll-upper', color: '#64748b', points: points(20, 1) });
      lines.push({ key: 'boll-mid', color: '#94a3b8', points: points(20) });
      lines.push({ key: 'boll-lower', color: '#64748b', points: points(20, -1) });
    }
    return lines.filter((line) => line.points);
  });
  const formatPercent = (value: unknown) =>
    Number.isFinite(Number(value))
      ? `${Number(value) >= 0 ? '+' : ''}${Number(value).toFixed(2)}%`
      : '—';
  const formatPrice = (value: unknown) => {
    if (value == null || value === '') return '—';
    const number = Number(value);
    return Number.isFinite(number)
      ? number.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
      : '—';
  };
  const compactNumber = (value: unknown) => {
    if (value == null || value === '') return '—';
    const number = Number(value);
    if (!Number.isFinite(number)) return '—';
    if (Math.abs(number) >= 1e12) return `${(number / 1e12).toFixed(2)}万亿`;
    if (Math.abs(number) >= 1e8) return `${(number / 1e8).toFixed(2)}亿`;
    if (Math.abs(number) >= 1e4) return `${(number / 1e4).toFixed(2)}万`;
    return number.toLocaleString('zh-CN');
  };
  function toggle(key: string) {
    const next = new Set(expanded.value);
    next.has(key) ? next.delete(key) : next.add(key);
    expanded.value = next;
  }
  function toggleAll() {
    expanded.value = allExpanded.value ? new Set() : new Set(definitions.map((item) => item.key));
  }
  function summary(value: unknown) {
    if (Array.isArray(value)) return `${value.length}条记录`;
    if (value && typeof value === 'object')
      return `${Object.keys(value as Record<string, unknown>).length}项数据`;
    return value == null ? '暂无数据' : String(value);
  }
  async function query() {
    const normalized = code.value
      .trim()
      .toUpperCase()
      .replace(/^(SH|SZ)/i, '')
      .replace(/\.(SH|SZ)$/i, '');
    if (!/^\d{6}$/.test(normalized) && !/^[A-Z0-9.^-]{1,24}$/.test(normalized)) {
      error.value = '请输入 A 股、美股、港股或韩股代码。';
      return;
    }
    loading.value = true;
    error.value = '';
    chartPeriod.value = 'day';
    snapshot.value = null;
    globalStock.value = null;
    try {
      if (/^\d{6}$/.test(normalized)) {
        const [facts, chart] = await Promise.allSettled([
          getStockSnapshot(normalized),
          getGlobalStock(normalized),
        ]);
        if (facts.status === 'rejected') throw facts.reason;
        snapshot.value = facts.value;
        if (chart.status === 'fulfilled') globalStock.value = chart.value;
      } else globalStock.value = await getGlobalStock(normalized);
      code.value = normalized;
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : '个股事实底稿暂不可用';
    } finally {
      loading.value = false;
    }
  }
  async function changeChartPeriod(period: '60m' | 'day' | 'week' | 'month') {
    if (!globalStock.value || chartPeriod.value === period) return;
    chartPeriod.value = period;
    chartLoading.value = true;
    try {
      const periodSnapshot = await getGlobalStock(code.value, period);
      globalStock.value = {
        ...globalStock.value,
        chart: periodSnapshot.chart,
        period: periodSnapshot.period,
      };
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : 'K线数据暂不可用';
    } finally {
      chartLoading.value = false;
    }
  }
  async function runAiAnalysis() {
    if (!snapshot.value && !globalStock.value) return;
    aiLoading.value = true;
    aiResult.value = '';
    aiError.value = '';
    debateResult.value = { bull: '', bear: '', judge: '' };
    try {
      controller = new AbortController();
      const factBase = snapshot.value || globalStock.value;
      if (analysisMode.value === 'debate') {
        const runRole = async (prompt: string) => {
          let result = '';
          await streamFinancialAi(
            prompt,
            factBase,
            (text) => {
              result += text;
            },
            controller?.signal,
          );
          return result;
        };
        debateResult.value.bull = await runRole(
          `你是多头研究员。仅依据底稿，从商业质量、盈利、估值、资金和催化建立最强多头论证；逐条注明事实、推断、待验证，并主动列出论证失效条件。${
            question.value ? `追加问题：${question.value}` : ''
          }`,
        );
        debateResult.value.bear = await runRole(
          `你是空头研究员。仅依据同一底稿，从财务质量、估值、治理、行业和交易结构反驳多头观点；逐条给证据、反证与待验证项。多头论证如下：\n${debateResult.value.bull}`,
        );
        debateResult.value.judge = await runRole(
          `你是中立投委会主持人。比较下列多空论证，输出：已确认共识、核心争议、证据强弱、需要补充的数据、未来验证条件。禁止给买卖建议。\n多头：${debateResult.value.bull}\n空头：${debateResult.value.bear}`,
        );
        aiResult.value = `## 多头研究员\n${debateResult.value.bull}\n\n## 空头研究员\n${debateResult.value.bear}\n\n## 中立裁决\n${debateResult.value.judge}`;
        return;
      }
      const modePrompt = {
        full: '按公司画像、估值、资金面、财报质量、行业景气、事件催化与风险完成深度分析',
        bull: '以多头研究员身份建立最强投资论证，同时指出该论证可能失败的证据',
        bear: '以空头研究员身份寻找财务、估值、治理、行业与交易结构中的风险，同时列出反驳证据',
        debate: '',
      }[analysisMode.value];
      await streamFinancialAi(
        `请${modePrompt}；覆盖底稿内所有模块，列出事实、推断、反方证据和待验证项，不给交易建议。${
          question.value ? `\n用户追加问题：${question.value}` : ''
        }`,
        factBase,
        (text) => {
          aiResult.value += text;
        },
        controller.signal,
      );
    } catch (reason) {
      if ((reason as Error).name !== 'AbortError')
        aiError.value = reason instanceof Error ? reason.message : '个股分析生成失败';
    } finally {
      aiLoading.value = false;
      controller = null;
    }
  }
  function cancelAi() {
    controller?.abort();
  }
  function saveRecord() {
    if (!snapshot.value && !globalStock.value) return;
    localStorage.setItem(
      `vg-stock-research-${securityCode.value}`,
      JSON.stringify({
        savedAt: new Date().toISOString(),
        snapshot: snapshot.value || globalStock.value,
        analysis: aiResult.value,
        question: question.value,
      }),
    );
  }
</script>

<style scoped lang="less">
  .stock-page {
    display: grid;
    gap: 14px;
    padding: 12px 4px 20px;
    color: #344054;
  }

  .query-card,
  .result-card,
  .module-card,
  .notice {
    border: 1px solid #dbe4ed;
    border-radius: 8px;
    background: #fff;
    box-shadow: 0 1px 3px rgb(15 23 42 / 6%);
  }

  .query-card {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px;
    gap: 20px;
  }

  .eyebrow {
    margin: 0 0 5px;
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

  h2 {
    font-size: 22px;
  }

  h3 {
    font-size: 16px;
  }

  p {
    margin: 8px 0 0;
    color: #5b6572;
    line-height: 1.65;
  }

  form {
    display: flex;
    gap: 8px;
    min-width: 360px;
  }

  input,
  button {
    height: 38px;
    border: 1px solid #d8e1ea;
    border-radius: 6px;
    background: #f8fafc;
    color: #17212f;
  }

  input {
    flex: 1;
    padding: 0 11px;
  }

  button {
    padding: 0 14px;
    border-color: #2f6fed;
    background: #eef5ff;
    color: #1f5cc4;
    font-weight: 700;
  }

  button:disabled {
    opacity: 0.6;
  }

  .notice {
    padding: 14px 16px;
  }

  .error {
    border-color: #f0c5c1;
    color: #b42318;
  }

  .result-card {
    padding: 18px;
  }

  .ai-panel {
    margin-bottom: 14px;
    padding: 14px;
    border: 1px solid #b9d4ff;
    border-radius: 8px;
    background: #f6faff;
  }

  .ai-panel p {
    white-space: pre-wrap;
  }

  .ai-panel header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .ai-panel header span {
    color: #1f5cc4;
    font-size: 12px;
    font-weight: 700;
  }

  .ai-panel pre {
    max-height: 620px;
    overflow: auto;
    color: #344054;
    font: inherit;
    line-height: 1.72;
    white-space: pre-wrap;
  }

  .ai-panel .error {
    color: #b42318;
  }

  .result-card > header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
    gap: 14px;
  }

  .result-card > header span {
    padding: 6px 10px;
    border-radius: 999px;
    background: #eef5ff;
    color: #1f5cc4;
    font-weight: 700;
  }

  .analysis-toolbar {
    display: grid;
    grid-template-columns: 150px minmax(260px, 1fr) auto auto auto;
    gap: 8px;
    margin: 14px 0;
  }

  .suggestions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: -4px 0 14px;
    color: #758196;
    font-size: 12px;
    gap: 6px;
  }

  .suggestions button {
    height: 30px;
    padding: 0 10px;
    border-color: #d8e1ea;
    background: #fff;
    color: #526174;
    font-size: 12px;
    font-weight: 500;
  }

  .debate-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 12px;
  }

  .debate-grid article {
    min-width: 0;
    padding: 12px;
    border: 1px solid #dbe4ed;
    border-radius: 7px;
    background: #fff;
  }

  .debate-grid .judge {
    grid-column: 1/-1;
    border-color: #f0d596;
    background: #fffaf0;
  }

  .debate-grid pre {
    max-height: 420px;
  }

  .global-overview {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin-bottom: 14px;
  }

  .period-tabs {
    display: flex;
    grid-column: 1/-1;
    gap: 6px;
  }

  .period-tabs i {
    width: 1px;
    height: 20px;
    margin: 6px 2px;
    background: #d8e1ea;
  }

  .period-tabs button {
    height: 32px;
    padding: 0 11px;
    border-color: #d8e1ea;
    background: #fff;
    color: #667085;
  }

  .period-tabs button.active {
    border-color: #2f6fed;
    background: #eef5ff;
    color: #1f5cc4;
  }

  .global-overview article {
    display: grid;
    gap: 5px;
    padding: 13px;
    border: 1px solid #e2e8ef;
    border-radius: 7px;
    background: #fbfcfe;
  }

  .global-overview article b {
    font-size: 20px;
  }

  .global-overview svg {
    grid-column: 1/-1;
    width: 100%;
    height: 190px;
    padding: 12px 0;
    border-bottom: 1px solid #edf0f3;
  }

  .global-overview > a {
    grid-column: 1/-1;
    color: #1f5cc4;
  }

  .global-metrics > header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .global-metrics > header > span {
    color: #667085;
    font-size: 12px;
  }

  .metric-list {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 8px;
    margin-top: 12px;
  }

  .metric-list article {
    display: grid;
    gap: 5px;
    padding: 12px;
    border: 1px solid #e2e8ef;
    border-radius: 7px;
    background: #fff;
  }

  .metric-list b {
    color: #17212f;
    font-size: 17px;
  }

  .metric-list em {
    color: #667085;
    font-size: 11px;
    font-style: normal;
  }

  .chart-empty {
    grid-column: 1/-1;
    min-height: 120px;
    padding: 45px 0;
    text-align: center;
  }

  .rise {
    color: #c0362c;
  }

  .fall {
    color: #087a55;
  }

  .analysis-toolbar textarea {
    min-height: 42px;
    padding: 9px 11px;
    border: 1px solid #d8e1ea;
    border-radius: 6px;
    background: #f8fafc;
    resize: vertical;
  }

  .analysis-toolbar select {
    min-height: 42px;
    padding: 0 9px;
    border: 1px solid #d8e1ea;
    border-radius: 6px;
    background: #fff;
  }

  .analysis-toolbar .plain {
    border-color: #d8e1ea;
    background: #fff;
    color: #667085;
  }

  .danger {
    border-color: #e7b4b0;
    background: #fff5f4;
    color: #b42318;
  }

  .module-card {
    margin-top: 10px;
    padding: 14px;
    background: #fbfcfe;
  }

  .module-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    height: auto;
    padding: 0;
    border: 0;
    background: transparent;
    color: #17212f;
    text-align: left;
  }

  .module-head > span {
    color: #1f5cc4;
    font-size: 12px;
  }

  .module-body {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 16px;
    align-items: start;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid #e7ecf1;
  }

  .module-card small {
    display: block;
    margin-top: 5px;
    color: #667085;
  }

  .module-card :deep(.research-data-renderer) {
    margin: 0;
  }

  .empty {
    margin: 0;
    color: #667085;
  }

  @media (max-width: 900px) {
    .query-card {
      flex-direction: column;
      align-items: flex-start;
    }

    form {
      width: 100%;
      min-width: 0;
    }

    .module-card {
      grid-template-columns: 1fr;
    }

    .analysis-toolbar,
    .module-body,
    .global-overview,
    .metric-list,
    .debate-grid {
      grid-template-columns: 1fr;
    }

    .debate-grid .judge {
      grid-column: auto;
    }

    .result-card > header {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
