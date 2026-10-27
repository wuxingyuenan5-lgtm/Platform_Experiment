<template>
  <div class="equity-observatory" :class="`equity-${market}`">
    <div class="observation-toolbar">
      <span
        >市场观察 <small v-if="data?.date">{{ data.date }}</small></span
      >
      <span v-if="data?.status === 'stale'" class="notice">数据待更新</span>
      <span v-else-if="data?.status === 'partial'" class="notice">部分数据待补齐</span>
      <button type="button" :disabled="loading" @click="load">{{
        loading ? '读取中…' : '刷新观察'
      }}</button>
    </div>
    <p v-if="error" role="alert" class="notice">观察数据读取失败，已保留当前内容。请重试。</p>
    <p v-if="!data" role="status">{{
      loading ? '正在读取市场观察…' : '暂无已发布的市场观察数据'
    }}</p>
    <template v-else>
      <section
        v-if="
          data.breadth &&
          (!view || view === 'overview' || view === 'structure' || view === 'crowding')
        "
        class="observation-section"
      >
        <h2>市场广度与参与度</h2>
        <p
          >{{ data.breadth.date }} · {{ market === 'us' ? '主题代表股票样本' : 'A股收盘快照' }} ·
          涨跌有效 {{ data.breadth.valid }} / {{ data.breadth.expected }}</p
        >
        <div class="metric-grid"
          ><article
            ><span>上涨</span><strong>{{ data.breadth.advancing }}</strong></article
          ><article
            ><span>下跌</span><strong>{{ data.breadth.declining }}</strong></article
          ><article
            ><span>平盘</span><strong>{{ data.breadth.unchanged }}</strong></article
          ><article
            ><span>涨跌家数差</span
            ><strong>{{ data.breadth.advancing - data.breadth.declining }}</strong></article
          ></div
        >
        <div class="table-scroll"
          ><table
            ><thead
              ><tr
                ><th>窗口</th><th>站上均线比例</th><th>窗口新高</th><th>窗口新低</th
                ><th>完整历史覆盖</th></tr
              ></thead
            ><tbody
              ><tr v-for="r in data.breadth.participation" :key="r.period"
                ><th>{{ r.period }}交易日</th><td>{{ format(r.abovePct, '%') }}</td
                ><td>{{ r.highs }}</td
                ><td>{{ r.lows }}</td
                ><td>{{ r.valid }} / {{ data.breadth.expected }}</td></tr
              ></tbody
            ></table
          ></div
        >
        <p class="definition"
          >均线与新高低仅统计窗口内交易日完整的个股；{{
            market === 'us'
              ? '固定代表股票样本，不代表全美股或标普500成分。'
              : '历史行情覆盖有限，历史参与度不是全A口径。'
          }}新高低包含等于窗口极值；当前样本不回填历史成分。</p
        >
      </section>
      <WidgetErrorBoundary
        v-if="!view || view === 'themes'"
        :key="`themes:${market}:${data.generatedAt}`"
        widget-title="主题与行业"
      >
        <p
          v-if="data.sectionStatus?.market === 'stale' || data.sectionStatus?.themes === 'stale'"
          role="status"
          >主题数据更新失败，当前显示已保留的数据。</p
        >
        <EquityThemePanel
          v-if="data.themes"
          :market="market"
          :data="data.themes"
          :industries="data.structure?.industries || []"
        />
        <p v-else role="status">主题与行业数据暂不可用</p>
      </WidgetErrorBoundary>
      <WidgetErrorBoundary v-if="!view || view === 'valuation'" widget-title="指数估值">
        <p v-if="data.sectionStatus?.valuation === 'stale'" role="status"
          >估值更新失败，当前显示已保留的数据。</p
        >
        <p v-else-if="data.sectionStatus?.valuation === 'error'" role="status">估值数据暂不可用</p>
        <IndexValuationPanel
          v-if="data.sectionStatus?.valuation !== 'error'"
          :charts="data.valuationCharts || []"
        />
      </WidgetErrorBoundary>

      <section
        v-if="!view || view === 'structure' || (market === 'cn' && view === 'crowding')"
        :id="`${market}-equity-structure`"
        class="observation-section"
      >
        <header
          ><div
            ><h2>{{ market === 'cn' ? '拥挤度与参与度' : '市场结构与风险环境' }}</h2
            ><p>{{
              market === 'cn'
                ? '交易集中 · 行业热度 · 宽基价格位置'
                : '相对表现 · 行业ETF参与 · 信用与利率'
            }}</p></div
          ></header
        >
        <template v-if="data.structure">
          <div class="metric-grid"
            ><article
              ><span>前20股成交额占比</span
              ><strong>{{ format(data.structure.market.top20AmountPct, '%') }}</strong></article
            ><article
              ><span>前50股成交额占比</span
              ><strong>{{ format(data.structure.market.top50AmountPct, '%') }}</strong></article
            ><article
              ><span>换手率中位数</span
              ><strong>{{ format(data.structure.market.medianTurnover, '%') }}</strong></article
            ><article
              ><span>上涨个股占比</span
              ><strong>{{ format(data.structure.market.advancingPct, '%') }}</strong></article
            ></div
          >
          <div class="table-scroll" tabindex="0" role="region" aria-label="行业估值与拥挤度">
            <table
              ><thead
                ><tr
                  ><th>申万一级行业</th><th>样本数</th><th>PE中位数</th><th>PB中位数</th
                  ><th>破净占比</th><th>成交额占比</th><th>占比分位</th><th>换手中位数</th
                  ><th>换手分位</th><th>历史样本</th></tr
                ></thead
              ><tbody
                ><tr v-for="row in shownIndustries" :key="row.code"
                  ><th>{{ row.name }}</th
                  ><td>{{ row.count }}</td
                  ><td>{{ format(row.medianPe) }}</td
                  ><td>{{ format(row.medianPb) }}</td
                  ><td>{{ format(row.belowBookPct, '%') }}</td
                  ><td>{{ format(row.amountSharePct, '%') }}</td
                  ><td>{{ format(row.shareRank, '%') }}</td
                  ><td>{{ format(row.medianTurnover, '%') }}</td
                  ><td>{{ format(row.turnoverRank, '%') }}</td
                  ><td>{{ row.sampleCount }}日</td></tr
                ></tbody
              ></table
            >
          </div>
          <button
            type="button"
            :aria-expanded="allIndustries"
            @click="allIndustries = !allIndustries"
            >{{ allIndustries ? '收起行业' : '展开全部行业' }}</button
          >
          <p class="definition"
            >按成交额占比排序；分位使用已归档收盘样本，至少60日。{{
              data.structure.unclassifiedCount
            }}
            只股票未归入当前有效行业。破净分母为正PB有效样本，非正PE与缺失值不计入PE中位数。</p
          >
          <details v-if="data.crowding?.length"
            ><summary>科技细分行业 · 已有历史分位</summary
            ><div class="table-scroll"
              ><table
                ><thead
                  ><tr
                    ><th>行业</th><th>成交占比</th><th>占比分位</th><th>换手率</th><th>换手分位</th
                    ><th>样本</th><th>观测日</th></tr
                  ></thead
                ><tbody
                  ><tr v-for="row in data.crowding" :key="row.name"
                    ><th>{{ row.name }}</th
                    ><td>{{ format(row.sharePct, '%') }}</td
                    ><td>{{ format(row.shareRank, '%') }}</td
                    ><td>{{ format(row.turnover, '%') }}</td
                    ><td>{{ format(row.turnoverRank, '%') }}</td
                    ><td>{{ row.count }}日</td><td>{{ row.date }}</td></tr
                  ></tbody
                ></table
              ></div
            ></details
          >
          <h3>宽基成分股交易拥挤</h3>
          <div class="table-scroll" tabindex="0" role="region" aria-label="宽基成分股拥挤度">
            <table
              ><thead
                ><tr
                  ><th>指数</th><th>成分覆盖</th><th>换手率中位数</th><th>换手分位</th
                  ><th>前20股成交占比</th><th>上涨比例</th><th>历史样本</th><th>成分日期</th></tr
                ></thead
              >
              <tbody
                ><tr v-for="row in data.indexCrowding" :key="row.code"
                  ><th>{{ row.name }}</th
                  ><td>{{ row.count }}/{{ row.expected }}</td
                  ><td>{{ format(row.medianTurnover, '%') }}</td
                  ><td>{{ format(row.turnoverRank, '%') }}</td
                  ><td>{{ format(row.top20AmountPct, '%') }}</td
                  ><td>{{ format(row.advancingPct, '%') }}</td
                  ><td>{{ row.sampleCount }}日</td><td>{{ row.membershipDate || '—' }}</td></tr
                ></tbody
              ></table
            >
          </div>
          <p class="definition"
            >中证官方成分与同日行情匹配；换手率取有效成分中位数。仅完整覆盖的收盘观测进入历史分位，不使用当前成分回填历史。</p
          >
          <h3>宽基价格位置</h3>
          <div class="table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>指数</th><th>20日均线偏离</th><th>60日均线偏离</th><th>200日均线偏离</th
                  ><th>距252日高点</th><th>观测日</th></tr
                ></thead
              ><tbody
                ><tr v-for="row in data.indices" :key="row.code"
                  ><th>{{ row.name }}</th
                  ><td>{{ format(row.deviation20, '%') }}</td
                  ><td>{{ format(row.deviation60, '%') }}</td
                  ><td>{{ format(row.deviation200, '%') }}</td
                  ><td>{{ format(row.drawdown252, '%') }}</td
                  ><td>{{ row.date }}</td></tr
                ></tbody
              ></table
            ></div
          >
          <p class="definition"
            >均线偏离是价格过热的观察项，不替代成分股换手率或市场广度；高拥挤不等于立即下跌。</p
          >
        </template>
        <template v-if="market === 'us'">
          <div class="metric-grid"
            ><article v-for="row in data.participation" :key="row.period"
              ><span>行业ETF站上{{ row.period }}日均线</span
              ><strong>{{ format(row.value, '%') }}</strong
              ><small>{{ row.count }}/{{ row.expected }} 只 · {{ row.date || '—' }}</small></article
            ></div
          >
          <p class="definition"
            >11只行业ETF观察池，不能解释为标普500成分股广度。相对价格不含分红再投资。</p
          >
          <div class="table-scroll"
            ><table
              ><thead
                ><tr
                  ><th>结构指标</th><th>比值</th><th>近20日变化</th><th>60日均线偏离</th
                  ><th>观测日</th></tr
                ></thead
              ><tbody
                ><tr v-for="row in data.ratios" :key="row.name"
                  ><th
                    ><button type="button" class="text-button" @click="ratioName = row.name">{{
                      row.name
                    }}</button
                    ><small>{{ row.symbols }}</small></th
                  ><td>{{ format(row.close) }}</td
                  ><td>{{ format(row.return20, '%') }}</td
                  ><td>{{ format(row.deviation60, '%') }}</td
                  ><td>{{ row.date || '—' }}</td></tr
                ></tbody
              ></table
            ></div
          >
          <WidgetErrorBoundary widget-title="走势图" :key="ratioName">
            <VibeTimeChart
              v-if="selectedRatio?.history?.length"
              :key="ratioName"
              :title="selectedRatio.name"
              y-label="比值"
              :precision="4"
              :dates="selectedRatio.history.map((p) => p.date)"
              :series="[
                {
                  name: selectedRatio.symbols || '比值',
                  type: 'line',
                  color: '#3366a3',
                  values: selectedRatio.history.map((p) => numeric(p.value)),
                },
              ]"
            />
          </WidgetErrorBoundary>
        </template>
      </section>

      <section
        v-if="data.hongKong && (!view || view === 'hk')"
        id="cn-equity-hk"
        class="observation-section"
      >
        <header
          ><div><h2>港股观察</h2><p>月度宏观四因子 · 各25%权重</p></div></header
        >
        <div v-if="data.hongKong.indices?.length" class="metric-grid"
          ><article v-for="row in data.hongKong.indices" :key="row.name"
            ><span>{{ row.name }}</span
            ><strong>{{ format(row.value) }}</strong
            ><small>{{ row.date }} · {{ format(row.returnPct, '%') }}</small></article
          ></div
        >
        <WidgetErrorBoundary
          widget-title="走势图"
          :key="row.name"
          v-for="row in (data.hongKong.indices || []).filter((i) =>
            /恒生科技|恒生互联网/.test(i.name),
          )"
        >
          <VibeTimeChart
            :key="row.name"
            :title="row.name + ' · 价格走势'"
            y-label="指数点位"
            :dates="row.history.map((p) => p.date)"
            :series="[
              {
                name: row.name,
                type: 'line',
                color: '#111111',
                values: row.history.map((p) => numeric(p.value)),
              },
            ]"
          />
        </WidgetErrorBoundary>
        <div class="composite"
          ><span>港股领航指标</span><strong>{{ format(data.hongKong.value) }}</strong
          ><span
            >{{ data.hongKong.date || '四项同月历史不足，暂不合成'
            }}{{ data.hongKong.status === 'stale' ? ' · 数据滞后' : '' }}</span
          ></div
        >
        <div class="table-scroll"
          ><table
            ><thead
              ><tr
                ><th>因子</th><th>最新原值</th><th>统计期间</th><th>有效期数</th><th>权重</th
                ><th>合成当月贡献</th></tr
              ></thead
            ><tbody
              ><tr v-for="row in data.hongKong.components" :key="row.id"
                ><th
                  ><a :href="row.sourceUrl" target="_blank" rel="noopener noreferrer">{{
                    row.name
                  }}</a></th
                ><td>{{ format(row.value, row.id === 'credit' ? '百分点' : '%') }}</td
                ><td>{{ row.date || '—' }}{{ row.status !== 'ready' ? ' · 待更新' : '' }}</td
                ><td>{{ row.count }}</td
                ><td>25%</td
                ><td
                  >{{ format(row.contribution) }}<small>{{ row.compositeDate || '' }}</small></td
                ></tr
              ></tbody
            ></table
          ></div
        >
        <p class="definition"
          >每项按过去60个月标准化，至少36期，同月四项齐全才等权合成。信用脉冲为滚动12月新增社融/名义GDP比例的同比变化；社零2月为1—2月合计口径。历史使用当前可得修订数据，不宣称已验证领先预测能力。</p
        >
        <WidgetErrorBoundary widget-title="走势图">
          <VibeTimeChart
            v-if="data.hongKong.history.length"
            title="港股宏观四因子"
            frequency="monthly"
            y-label="标准分"
            :dates="data.hongKong.history.map((p) => p.date)"
            :series="[
              {
                name: '等权标准分',
                type: 'line',
                color: '#38827c',
                values: data.hongKong.history.map((p) => numeric(p.value)),
              },
            ]"
          />
        </WidgetErrorBoundary>
      </section>
      <p v-if="view === 'hk' && !data.hongKong" role="status">暂无已发布的港股观察数据</p>
      <details class="source-details"
        ><summary>数据来源与更新日期</summary
        ><div class="table-scroll"
          ><table
            ><thead
              ><tr><th>来源</th><th>观测日期</th><th>采集状态</th></tr></thead
            ><tbody
              ><tr v-for="row in data.sources" :key="row.name"
                ><td>{{ row.name }}</td
                ><td>{{ row.date || '—' }}</td
                ><td>{{
                  row.status === 'ready'
                    ? '已采集'
                    : row.status === 'stale'
                    ? '保留历史，更新失败'
                    : '暂不可用'
                }}</td></tr
              ></tbody
            ></table
          ></div
        ></details
      >
    </template>
  </div>
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import {
    getEquityObservatory,
    type EquityObservatory,
    type EquityValue,
  } from '@/api/equityObservatory';
  import VibeTimeChart from '../aShare/components/VibeTimeChart.vue';
  import IndexValuationPanel from './IndexValuationPanel.vue';
  import WidgetErrorBoundary from './WidgetErrorBoundary';
  import EquityThemePanel from './EquityThemePanel.vue';

  import { useResearchViewState, useResearchSnapshots } from '../composables/researchWorkspace';

  const props = defineProps<{ market: 'cn' | 'us'; refreshKey?: number; view?: string }>();
  const emit = defineEmits<{ ready: [] }>();
  const snapshots = useResearchSnapshots();
  const data = shallowRef<EquityObservatory | null>(null);
  const loading = ref(false);
  const error = ref(false);
  const allIndustries = useResearchViewState('allIndustries', false);
  const ratioName = useResearchViewState('ratioName', '');
  let controller: AbortController | null = null;
  let sequence = 0;
  const numeric = (v: EquityValue | undefined) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  const format = (v: EquityValue | undefined, suffix = '') =>
    numeric(v) == null ? '—' : `${numeric(v)!.toFixed(2)}${suffix}`;
  const tone = (v: EquityValue | undefined) =>
    numeric(v) == null || numeric(v) === 0 ? '' : numeric(v)! > 0 ? 'positive' : 'negative';
  const shownIndustries = computed(() =>
    (data.value?.structure?.industries || []).slice(0, allIndustries.value ? undefined : 12),
  );
  const selectedRatio = computed(
    () => data.value?.ratios?.find((r) => r.name === ratioName.value) || data.value?.ratios?.[0],
  );
  async function load() {
    controller?.abort();
    controller = new AbortController();
    const current = ++sequence;
    loading.value = true;
    error.value = false;
    try {
      const result = await getEquityObservatory(props.market, controller.signal);
      if (current === sequence) {
        data.value = result;
        snapshots.set(`equity:${props.market}`, result);
      }
    } catch {
      if (current === sequence) error.value = true;
    } finally {
      if (current === sequence) {
        loading.value = false;
        emit('ready');
      }
    }
  }
  watch(
    () => [props.market, props.refreshKey],
    (_value, previous) => {
      const cached = !previous && snapshots.get<EquityObservatory>(`equity:${props.market}`);
      if (cached) {
        data.value = cached;
        emit('ready');
      } else void load();
    },
    { immediate: true },
  );
  const poll = window.setInterval(() => {
    if (!document.hidden && !loading.value) void load();
  }, 60000);
  onBeforeUnmount(() => {
    sequence++;
    controller?.abort();
    window.clearInterval(poll);
  });
</script>

<style scoped lang="less">
  .equity-observatory {
    --positive: #cc504a;
    --negative: #13866b;

    display: grid;
    gap: 20px;
    min-width: 0;
    color: #25374d;
  }

  .equity-us {
    --positive: #13866b;
    --negative: #cc504a;
  }

  .observation-toolbar,
  header,
  .reference-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }

  .observation-toolbar {
    padding: 8px 2px;
    font-weight: 600;
  }

  .observation-section {
    min-width: 0;
    padding: 22px;
    border: 1px solid #dce4ed;
    border-radius: 14px;
    background: #fff;
    scroll-margin-top: 86px;
  }

  header {
    margin-bottom: 18px;
    padding-bottom: 14px;
    border-bottom: 1px solid #e8edf3;
  }

  h2 {
    margin: 0 0 5px;
    color: #172d46;
    font-size: 19px;
    font-weight: 650;
  }

  h3 {
    margin: 18px 0 12px;
    font-size: 15px;
  }

  p {
    margin: 6px 0;
  }

  small,
  header p,
  .definition {
    color: #64758a;
    font-size: 12px;
    line-height: 1.8;
  }

  small {
    display: inline-block;
    font-weight: 400;
  }

  button,
  select {
    padding: 7px 12px;
    border: 1px solid #dbe3ed;
    border-radius: 7px;
    background: #f8fafc;
    color: inherit;
    cursor: pointer;
  }

  button:focus-visible,
  select:focus-visible,
  summary:focus-visible {
    outline: 2px solid #426da4;
    outline-offset: 3px;
  }

  button:disabled {
    opacity: 0.6;
    cursor: wait;
  }

  .theme-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .theme-grid button {
    display: grid;
    padding: 15px;
    background: #fbfcfe;
    text-align: left;
    gap: 5px;
  }

  .theme-grid button[aria-pressed='true'] {
    border-color: #426da4;
    background: #f0f5fc;
    box-shadow: 0 0 0 1px #426da4;
  }

  .theme-grid span {
    color: #64758a;
    font-size: 12px;
  }

  .theme-grid b {
    font-size: 19px;
    font-variant-numeric: tabular-nums;
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin: 12px 0 18px;
  }

  .metric-grid article {
    display: grid;
    padding: 15px;
    border: 1px solid #e4eaf1;
    border-radius: 9px;
    background: #f8fafc;
    gap: 6px;
  }

  .metric-grid strong {
    font-size: 24px;
    font-variant-numeric: tabular-nums;
  }

  .table-scroll {
    margin: 12px 0;
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
    text-align: right;
    white-space: nowrap;
  }

  th,
  td {
    padding: 11px 12px;
    border-bottom: 1px solid #e9eef4;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  thead {
    background: #f4f7fb;
    color: #607089;
  }

  td small,
  th small {
    display: block;
  }

  .text-button {
    padding: 0;
    border: 0;
    background: none;
    color: #315f96;
  }

  a {
    color: #315f96;
  }

  .positive {
    color: var(--positive);
  }

  .negative {
    color: var(--negative);
  }

  .notice {
    color: #98651e;
  }

  .composite {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    padding: 18px;
    border-radius: 9px;
    background: #f0f6f5;
    gap: 18px;
  }

  .composite strong {
    font-size: 30px;
  }

  .source-details {
    padding: 12px;
    color: #64758a;
    font-size: 12px;
  }

  summary {
    padding: 8px 0;
    cursor: pointer;
  }

  :deep(.vibe-time-chart) {
    margin-top: 16px;
  }

  @media (max-width: 1000px) {
    .theme-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .metric-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 600px) {
    .observation-section {
      padding: 14px;
    }

    .theme-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
