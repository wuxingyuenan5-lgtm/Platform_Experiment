<template>
  <div
    class="equity-observatory"
    :class="[`equity-${market}`, { 'market-breadth-grid': crowdingScope === 'market' }]"
  >
    <div
      v-if="crowdingScope !== 'market' && (!embedded || (!crowdingScope && observationNotice))"
      class="observation-toolbar"
    >
      <div class="observation-meta">
        <span v-if="!embedded"
          >市场观察 <small v-if="data?.date">{{ data.date }}</small></span
        >
        <span v-if="observationNotice" class="notice">{{ observationNotice }}</span>
      </div>
      <button v-if="!embedded" type="button" :disabled="loading" @click="load">{{
        loading ? '读取中…' : '刷新观察'
      }}</button>
    </div>
    <p v-if="error" role="alert" class="notice"
      >观察数据读取失败，已保留当前内容。<button @click="load">重试</button></p
    >
    <p v-if="!data" role="status">{{
      loading ? '正在读取市场观察…' : '暂无已发布的市场观察数据'
    }}</p>
    <template v-else>
      <CrowdingResearchPanel
        v-if="market === 'cn' && view === 'crowding' && !crowdingScope"
        :data="data"
        :refresh-key="refreshKey"
      />
      <WidgetErrorBoundary
        v-if="
          market === 'cn' && view === 'crowding' && (!crowdingScope || crowdingScope === 'theme')
        "
        :key="`theme-crowding:${data.generatedAt}`"
        widget-title="主题成交与价格"
      >
        <ThemeCrowdingPanel
          v-if="data.themeCrowding"
          :data="data.themeCrowding"
          :embedded="embedded"
          :theme="crowdingTheme"
          :segment="crowdingSegment"
          @select="selectBasket"
        />
        <p v-else role="status">主题成交与价格数据待生成</p>
      </WidgetErrorBoundary>
      <CrowdingResearchPanel
        v-if="crowdingScope === 'market'"
        :data="data"
        market-only
        :refresh-key="refreshKey"
      >
        <template #market="{ breadthRanks }">
          <section class="market-breadth-wide">
            <slot
              name="concentration-history"
              :snapshot="data.structure"
              :stale="data.sectionStatus?.market === 'stale'"
            ></slot>
          </section>
          <section class="market-breadth-wide">
            <slot
              name="breadth-history"
              :snapshot="data.breadth"
              :stale="data.sectionStatus?.market === 'stale'"
              :breadth-ranks="breadthRanks"
            ></slot>
          </section>
        </template>
      </CrowdingResearchPanel>
      <section
        v-if="
          data.breadth &&
          (!view || view === 'overview' || view === 'structure' || view === 'crowding') &&
          !crowdingScope
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
            ><span>上涨</span
            ><strong>{{ data.breadth.valid ? data.breadth.advancing : '—' }}</strong></article
          ><article
            ><span>下跌</span
            ><strong>{{ data.breadth.valid ? data.breadth.declining : '—' }}</strong></article
          ><article
            ><span>平盘</span
            ><strong>{{ data.breadth.valid ? data.breadth.unchanged : '—' }}</strong></article
          ><article
            ><span>涨跌家数差</span
            ><strong>{{
              data.breadth.valid ? data.breadth.advancing - data.breadth.declining : '—'
            }}</strong></article
          ></div
        >
        <div>
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
                  ><td>{{ r.valid ? r.highs : '—' }}</td
                  ><td>{{ r.valid ? r.lows : '—' }}</td
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
        </div>
      </section>
      <WidgetErrorBoundary
        v-if="!view || view === 'themes'"
        :key="`themes:${market}:${data.generatedAt}`"
        widget-title="主题研究"
      >
        <p
          v-if="data.sectionStatus?.market === 'stale' || data.sectionStatus?.themes === 'stale'"
          role="status"
          ><template v-if="data.themes?.date && data.themes.date !== data.date"
            >最新收盘历史尚未齐全，当前主题统计截至 {{ data.themes.date }}。</template
          ><template v-else>主题数据更新失败，当前显示已保留的数据。</template></p
        >
        <EquityThemePanel
          v-if="data.themes"
          :market="market"
          :data="data.themes"
          :industries="data.structure?.industries || []"
        />
        <p v-else role="status">主题研究数据暂不可用</p>
      </WidgetErrorBoundary>
      <WidgetErrorBoundary v-if="!view || view === 'valuation'" widget-title="指数估值">
        <p v-if="data.sectionStatus?.valuation === 'stale'" role="status"
          >估值更新失败，当前显示已保留的数据。</p
        >
        <p v-else-if="data.sectionStatus?.valuation === 'error'" role="status">估值数据暂不可用</p>
        <template v-if="data.sectionStatus?.valuation !== 'error'">
          <slot name="valuation" :charts="data.valuationCharts || []">
            <IndexValuationPanel
              :charts="data.valuationCharts || []"
              :initial-comparison-open="market === 'cn'"
              :refresh-key="refreshKey"
            />
          </slot>
        </template>
      </WidgetErrorBoundary>

      <section
        v-if="
          (!view || view === 'structure' || (market === 'cn' && view === 'crowding')) &&
          (!crowdingScope || crowdingScope === 'indices')
        "
        :id="
          crowdingScope === 'indices'
            ? `${market}-equity-index-participation`
            : `${market}-equity-structure`
        "
        class="observation-section"
      >
        <header v-if="crowdingScope !== 'indices'"
          ><div
            ><h2>{{ market === 'cn' ? '拥挤度与参与度' : '市场结构与风险环境' }}</h2
            ><p>{{
              market === 'cn'
                ? '交易集中 · 行业热度 · 宽基价格位置'
                : '相对表现 · 行业ETF参与 · 信用与利率'
            }}</p></div
          ></header
        >
        <IndexParticipationTable v-if="crowdingScope === 'indices'" :data="data" />
        <template v-else-if="data.structure">
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
          <template v-if="!crowdingScope">
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
              v-if="!inThemeResearch"
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
          </template>
          <TechnologyCrowdingTable
            v-if="!crowdingScope && data.crowding?.length"
            :rows="data.crowding"
            :expanded="inThemeResearch"
          />
          <template v-if="!crowdingScope">
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

      <WidgetErrorBoundary v-if="data.hongKong && (!view || view === 'hk')" widget-title="港股观察">
        <HongKongObservationPanel :data="data.hongKong" />
      </WidgetErrorBoundary>
      <p v-if="view === 'hk' && !data.hongKong" role="status">暂无已发布的港股观察数据</p>
      <details v-if="!inThemeResearch" class="source-details"
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
  import {
    inject,
    computed,
    defineAsyncComponent,
    onBeforeUnmount,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useDashboardRefresh } from '../useDashboardRefresh';
  import {
    getEquityObservatory,
    type EquityObservatory,
    type EquityValue,
  } from '@/api/equityObservatory';
  import VibeTimeChart from '../aShare/components/VibeTimeChart.vue';
  import { useRoute, useRouter } from 'vue-router';
  import IndexValuationPanel from './IndexValuationPanel.vue';
  import WidgetErrorBoundary from './WidgetErrorBoundary';
  import EquityThemePanel from './EquityThemePanel.vue';
  import ThemeCrowdingPanel from './ThemeCrowdingPanel.vue';
  import IndexParticipationTable from '../aShare/components/IndexParticipationTable.vue';
  import TechnologyCrowdingTable from './TechnologyCrowdingTable.vue';

  import { useResearchViewState, useResearchSnapshots } from '../composables/researchWorkspace';

  const HongKongObservationPanel = defineAsyncComponent(
    () => import('../aShare/components/HongKongObservationPanel.vue'),
  );
  const CrowdingResearchPanel = defineAsyncComponent(
    () => import('../aShare/components/CrowdingResearchPanel.vue'),
  );

  const inThemeResearch = inject('themeResearchAlwaysExpanded', false);
  const props = defineProps<{
    market: 'cn' | 'us';
    refreshKey?: number;
    view?: string;
    embedded?: boolean;
    selectedTheme?: string;
    crowdingScope?: 'theme' | 'market' | 'indices';
  }>();
  const emit = defineEmits<{ ready: [] }>();
  const snapshots = useResearchSnapshots();
  const data = shallowRef<EquityObservatory | null>(null);
  const observationNotice = computed(() =>
    data.value?.status === 'stale'
      ? '数据待更新'
      : data.value?.status === 'partial'
      ? '部分数据待补齐'
      : '',
  );
  const crowdingTheme = useResearchViewState('crowdingTheme', '机器人／高端制造');
  const crowdingSegment = useResearchViewState('crowdingSegment', '');
  const route = useRoute();
  const router = useRouter();
  watch(
    () => [route.query.view, props.selectedTheme || route.query.theme, route.query.segment],
    ([view, theme, segment]) => {
      if (
        props.view === 'crowding' &&
        (view === 'crowding' || view === 'themes') &&
        typeof theme === 'string'
      ) {
        crowdingTheme.value = theme;
        crowdingSegment.value = typeof segment === 'string' ? segment : '';
      }
    },
    { immediate: true },
  );
  function selectBasket(theme: string, segment = '') {
    void router.replace({
      query: {
        ...route.query,
        view: 'themes',
        section: 'themes',
        themeView: 'activity',
        theme,
        segment: segment || undefined,
        themeDate: theme === crowdingTheme.value ? route.query.themeDate : undefined,
      },
    });
  }
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
  const shownIndustries = computed(() =>
    (data.value?.structure?.industries || []).slice(
      0,
      inThemeResearch || allIndustries.value ? undefined : 12,
    ),
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
      const result = await getEquityObservatory(
        props.market,
        controller.signal,
        props.view,
        props.view === 'crowding' ? crowdingTheme.value : undefined,
      );
      if (current === sequence) {
        data.value = result;
        snapshots.set(
          `equity:${props.market}:${props.view || 'all'}:${
            props.view === 'crowding' ? crowdingTheme.value : ''
          }`,
          result,
        );
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
    () => [
      props.market,
      props.refreshKey,
      props.view,
      props.view === 'crowding' ? crowdingTheme.value : '',
    ],
    (value, previous) => {
      const cached =
        (!previous ||
          (props.market === 'cn' &&
            value[1] === previous[1] &&
            (value[0] !== previous[0] || value[2] !== previous[2] || value[3] !== previous[3]))) &&
        snapshots.get<EquityObservatory>(
          `equity:${props.market}:${props.view || 'all'}:${
            props.view === 'crowding' ? crowdingTheme.value : ''
          }`,
        );
      if (cached) {
        controller?.abort();
        sequence++;
        loading.value = false;
        error.value = false;
        data.value = cached;
        emit('ready');
      } else void load();
    },
    { immediate: true },
  );
  useDashboardRefresh(load, { immediate: false, enabled: () => !loading.value });
  onBeforeUnmount(() => {
    sequence++;
    controller?.abort();
  });
</script>

<style scoped lang="less">
  .equity-observatory {
    --positive: #cc504a;
    --negative: #13866b;

    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
    min-width: 0;
    color: #25374d;
  }

  .market-breadth-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
  }

  .market-breadth-wide,
  .market-breadth-grid > :deep(p) {
    grid-column: 1 / -1;
    min-width: 0;
  }

  @media (max-width: 1180px) {
    .market-breadth-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  .equity-us {
    --positive: #13866b;
    --negative: #cc504a;
  }

  header,
  .reference-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }

  .observation-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 6px 12px;
    padding: 0 2px;
    font-weight: 600;
  }

  .observation-meta {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 3px 12px;
  }

  .observation-toolbar button {
    padding: 5px 10px;
  }

  .equity-observatory > p {
    margin: 0;
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

  .disclosure-title {
    margin: 0 0 12px;
    color: #354d68;
    font-size: 14px;
    font-weight: 600;
  }
</style>
