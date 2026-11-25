<template>
  <section class="object-workspace industry-research" aria-label="行业综合研究">
    <div class="industry-valuation-tables">
      <IndexValuationGroupTable
        :group="valuationGroup"
        :as-of="data.date || ''"
        industry-comparison
      >
        <template #heading>
          <nav class="object-tabs valuation-tabs" aria-label="行业指数估值分组">
            <button
              v-for="group in industryObservationGroups"
              :key="group.name"
              type="button"
              :aria-pressed="valuationGroup === group"
              @click="valuationGroup = group"
              >{{ group.name }}</button
            >
          </nav>
        </template>
      </IndexValuationGroupTable>
    </div>
    <VisibleChart class="industry-growth">
      <MarketMonitorPanel section="growth" embedded :refresh-key="refreshKey" />
    </VisibleChart>
    <section
      v-if="heatDates.length"
      class="object-card industry-heatmap"
      aria-label="全行业拥挤度热力图"
    >
      <header class="object-heading">
        <h3>全行业拥挤度热力图</h3>
        <div class="object-controls">
          <select v-model="heatMetric" aria-label="热力图观察维度">
            <option value="turnover">等权换手率分位</option>
            <option value="amount">成交额占比分位</option>
          </select>
        </div>
      </header>
      <div
        class="object-table heatmap-scroll"
        tabindex="0"
        role="region"
        aria-label="全行业拥挤度数据"
      >
        <table>
          <thead>
            <tr>
              <th scope="col">行业 / 日期</th>
              <th v-for="day in heatDates" :key="day" scope="col">{{ day.slice(5) }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in heatRows" :key="row.code">
              <th scope="row">
                <button
                  type="button"
                  :aria-pressed="industryCode(row.code) === selected?.code"
                  @click="emit('industry', industryCode(row.code))"
                  >{{ row.name }}</button
                >
              </th>
              <td v-for="cell in row.cells" :key="cell.date" :style="cell.style">{{
                cell.text
              }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <CrowdingResearchPanel
      v-if="selected"
      :data="data"
      view="industry"
      :industry-code="selected.code"
      :refresh-key="refreshKey"
      @industry="emit('industry', $event)"
    >
      <template #industry-history="{ chart }">
        <section v-if="selected" class="object-card industry-detail" aria-label="所选行业研究">
          <section class="industry-overview" aria-label="行业概览">
            <header class="object-heading">
              <div
                ><h2
                  >{{ selected.name }} <small>{{ selected.code }}</small></h2
                ><p
                  >申万一级行业 · {{ data.structure?.date || '暂无观察日' }} 收盘 ·
                  {{ selected.count }}只股票</p
                ></div
              >
              <div class="object-controls">
                <input
                  v-model="industrySearch"
                  aria-label="搜索研究行业"
                  placeholder="行业 / 代码"
                />
                <select :value="selected.code" aria-label="当前研究行业" @change="selectIndustry">
                  <option v-for="row in filteredIndustries" :key="row.code" :value="row.code">
                    {{ row.name }} · {{ row.code }}
                  </option>
                </select>
                <button
                  type="button"
                  class="object-button"
                  :aria-expanded="levelTwoOpen"
                  @click="levelTwoOpen = !levelTwoOpen"
                >
                  {{ levelTwoOpen ? '收起二级' : '展开二级' }}
                </button>
              </div>
            </header>
            <div v-if="observationError" class="object-note" role="alert">
              {{ observationError }}
              <button type="button" class="object-button" @click="emit('retry')">重试</button>
            </div>
            <p v-else-if="data.sectionStatus?.market === 'stale'" class="object-note">
              收盘数据待更新，当前显示最近观测。
            </p>
            <div v-if="monitorError" class="object-note" role="alert"
              >{{ monitorError }}
              <button class="object-button" @click="loadMonitor">重试</button></div
            >
            <p
              v-if="
                monitor?.sources.industry?.status === 'error' ||
                monitor?.sources.growth_netProfitYoy?.status === 'error'
              "
              class="object-note"
              >部分行业景气或拥挤度数据更新失败，以下保留最近观测。</p
            >
          </section>
          <section v-if="levelTwoOpen" class="object-card level-two" aria-label="申万二级对照">
            <header class="object-heading">
              <div>
                <h3>{{ showWatchlist ? '自选二级行业' : selected.name + ' · 申万二级' }}</h3>
                <p v-if="levelTwo?.meta.sourceTimestamp"
                  >{{ levelTwo.meta.sourceTimestamp.slice(0, 10)
                  }}<template v-if="levelTwo.meta.isStale"> · 待更新</template></p
                >
              </div>
              <button
                type="button"
                class="object-button"
                :aria-pressed="showWatchlist"
                @click="showWatchlist = !showWatchlist"
                >自选对照（{{ watchlist.length }}）</button
              >
            </header>
            <p v-if="levelTwoError" class="object-note" role="alert"
              >{{ levelTwoError }}
              <button type="button" class="object-button" @click="loadLevelTwo">重试</button>
            </p>
            <p v-else-if="levelTwoLoading" class="object-source" role="status">正在读取二级行业…</p>
            <div
              v-if="levelTwoRows.length"
              class="object-table"
              role="region"
              aria-label="二级行业截面"
              tabindex="0"
            >
              <table>
                <thead>
                  <tr
                    ><th scope="col">二级行业</th><th scope="col">成交额占全A</th
                    ><th scope="col">涨跌幅</th><th scope="col">自选</th></tr
                  >
                </thead>
                <tbody>
                  <tr v-for="row in levelTwoRows" :key="row.swL2Code">
                    <th scope="row"
                      >{{ row.swL2Name }}<small v-if="showWatchlist">{{ row.swL1Name }}</small></th
                    >
                    <td>{{ fmtPct(row.marketSharePct) }}</td>
                    <td :class="tone(row.returnPct)">{{ fmtPct(row.returnPct) }}</td>
                    <td
                      ><button
                        class="object-button"
                        type="button"
                        :aria-label="'自选：' + row.swL2Name"
                        :aria-pressed="watchlist.includes(row.swL2Code)"
                        @click="toggleWatchlist(row.swL2Code)"
                      >
                        {{ watchlist.includes(row.swL2Code) ? '移除' : '加入' }}
                      </button></td
                    >
                  </tr>
                </tbody>
              </table>
            </div>
            <p v-else-if="!levelTwoLoading && !levelTwoError" class="object-source">{{
              showWatchlist ? '暂无自选行业' : '暂无二级行业数据'
            }}</p>
          </section>
          <div class="object-columns">
            <section class="object-card">
              <div class="object-heading"><h3>市场截面</h3></div>
              <dl class="object-facts">
                <dt>PE / PB 中位数</dt>
                <dd
                  >{{ fmt(selected.medianPe) }} / {{ fmt(selected.medianPb) }}
                  <small>正值样本：PE {{ selected.peCount }} / PB {{ selected.pbCount }}</small>
                </dd>
                <dt>净利润同比中位数</dt>
                <dd :class="tone(profit?.value)"
                  >{{ fmtPct(profit?.value) }}
                  <small v-if="profit?.date"
                    >{{ profit.date
                    }}<template v-if="profit.change != null">
                      · {{ fmt(profit.change) }} pp</template
                    ></small
                  >
                </dd>
                <dt>成交额占全A</dt><dd>{{ fmtPct(selected.amountSharePct) }}</dd>
                <dt>成交额占比 · 30交易日分位</dt>
                <dd
                  >{{ fmtPct(heat?.amount) }}<small v-if="heat?.date">{{ heat.date }}</small></dd
                >
                <dt>换手率中位数</dt><dd>{{ fmtPct(selected.medianTurnover) }}</dd>
                <dt>上涨股票占比</dt><dd>{{ fmtPct(selected.advancingPct) }}</dd>
                <dt>当日涨跌中位数</dt>
                <dd :class="tone(selected.medianReturn)">{{ fmtPct(selected.medianReturn) }}</dd>
                <dt>破净股票占比</dt><dd>{{ fmtPct(selected.belowBookPct) }}</dd>
                <dt>前20股成交集中度</dt><dd>{{ fmtPct(selected.top20AmountPct) }}</dd>
                <dt>前50股成交集中度</dt><dd>{{ fmtPct(selected.top50AmountPct) }}</dd>
              </dl>
            </section>
            <section class="object-card">
              <div class="object-heading"><h3>景气指标</h3><p>财报同比中位数</p></div>
              <div class="object-table" role="region" aria-label="行业六项景气指标" tabindex="0">
                <table
                  ><thead
                    ><tr
                      ><th>指标</th><th>本期</th><th>上期</th><th>变化（pp）</th
                      ><th>财报期 / 上期</th></tr
                    ></thead
                  >
                  <tbody
                    ><tr v-for="row in growthRows" :key="row.key"
                      ><th
                        ><a
                          :href="row.source?.sourceUrl"
                          target="_blank"
                          rel="noopener noreferrer"
                          >{{ row.name }}</a
                        ><small v-if="row.source?.status === 'error'">更新失败，保留历史</small></th
                      ><td :class="tone(row.item?.value)">{{ fmt(row.item?.value) }}%</td
                      ><td>{{ fmt(row.item?.previous) }}%</td
                      ><td :class="tone(row.item?.change)">{{ fmt(row.item?.change) }}</td
                      ><td
                        >{{ row.item?.date || '—'
                        }}<small>{{ row.item?.previousDate || '—' }}</small></td
                      ></tr
                    ></tbody
                  >
                </table>
              </div>
              <p v-if="monitorLoading" class="object-source" role="status"
                >正在读取行业拥挤度与景气…</p
              >
            </section>
          </div>
          <div class="industry-history">
            <FinancingChart
              class="industry-activity-history"
              :title="`${selected.name} · 成交额占全A与换手率`"
              :rows="[]"
              :lines="industryActivityLines"
              :axis-names="['成交额占全A（%）', '换手率（%）']"
              allow-table
            />
            <FinancingChart v-bind="chart" />
          </div>
          <section v-if="related.length" class="related-strip" aria-label="关联主题">
            <h3 class="disclosure-title">关联主题</h3>
            <div class="related-links">
              <button
                v-for="item in related"
                :key="item.theme.name"
                type="button"
                @click="emit('theme', item.theme.name, selected.code)"
                >{{ item.theme.name }} · {{ item.members.length }}只</button
              >
            </div>
          </section>
        </section>
      </template>
    </CrowdingResearchPanel>
    <p v-else class="object-note" :role="observationError ? 'alert' : 'status'">
      {{ observationError || '行业观察数据暂不可用。' }}
      <button v-if="observationError" type="button" class="object-button" @click="emit('retry')"
        >重试</button
      >
    </p>
    <section class="object-card research-detail">
      <h2 class="disclosure-title">行业专题拥挤度</h2>
      <p v-if="technologyError" class="object-note" role="alert">
        {{ technologyError }} <button @click="loadTechnology">重试</button>
      </p>
      <TechnologyCrowdingTable v-if="technologyRows.length" :rows="technologyRows" expanded />
      <VisibleChart>
        <AShareCrowdingHistory :refresh-key="refreshKey" />
      </VisibleChart>
    </section>
  </section>
</template>
<script setup lang="ts">
  import { computed, defineAsyncComponent, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import {
    getEquityObservatory,
    type EquityObservatory,
    type EquityValue,
  } from '@/api/equityObservatory';
  import TechnologyCrowdingTable from '../../components/TechnologyCrowdingTable.vue';
  import VisibleChart from '../../components/VisibleChart';
  import IndexValuationGroupTable from '../../components/IndexValuationGroupTable.vue';
  import FinancingChart, { type FinanceLine } from './FinancingChart.vue';
  import { getAShareDashboard, type AShareDashboardResponse } from '@/api/hedgeResearch';
  import { useResearchViewState } from '../../composables/researchWorkspace';
  import { industryObservationGroups } from '../../components/indexValuationSnapshot';
  import { getMarketMonitor, type MarketMonitor, type MonitorItem } from '@/api/cnMarketMonitor';
  import { industryCode, industryThemes } from './industryResearch';

  const MarketMonitorPanel = defineAsyncComponent(() => import('./MarketMonitorPanel.vue'));
  const CrowdingResearchPanel = defineAsyncComponent(() => import('./CrowdingResearchPanel.vue'));
  const AShareCrowdingHistory = defineAsyncComponent(() => import('./AShareCrowdingHistory.vue'));
  const props = defineProps<{
    data: EquityObservatory;
    industry: string;
    refreshKey: number;
    observationError?: string;
  }>();
  const emit = defineEmits<{
    industry: [code: string];
    theme: [name: string, industry: string];
    retry: [];
  }>();
  const industries = computed(() => props.data.structure?.industries || []);
  const valuationGroup = shallowRef(industryObservationGroups[0]);
  const industryActivityLines: FinanceLine[] = [
    { key: 'amountSharePct', name: '成交额占全A', color: '#2864ec', unit: '%' },
    { key: 'turnoverPct', name: '换手率', color: '#d84f5a', unit: '%', right: true },
    { key: 'close', name: '行业指数', color: '#089184', unit: '点', axis: 2, hideAxis: true },
  ];
  const selected = computed(
    () =>
      industries.value.find((row) => industryCode(row.code) === industryCode(props.industry)) ||
      industries.value[0],
  );
  const industrySearch = ref('');
  const levelTwoOpen = ref(false);
  const showWatchlist = ref(false);
  const watchlist = useResearchViewState<string[]>('industry-l2-watchlist', []);
  const levelTwo = shallowRef<AShareDashboardResponse['shenwan']>();
  const levelTwoError = ref('');
  const levelTwoLoading = ref(false);
  let levelTwoController: AbortController | undefined;
  const levelTwoRows = computed(() =>
    (levelTwo.value?.data?.sw2All || []).filter((row) =>
      showWatchlist.value
        ? watchlist.value.includes(row.swL2Code)
        : industryCode(row.swL1Code) === industryCode(selected.value?.code),
    ),
  );
  function toggleWatchlist(code: string) {
    watchlist.value = watchlist.value.includes(code)
      ? watchlist.value.filter((item) => item !== code)
      : [...watchlist.value, code];
  }
  async function loadLevelTwo() {
    levelTwoController?.abort();
    const current = new AbortController();
    levelTwoController = current;
    levelTwoLoading.value = true;
    levelTwoError.value = '';
    try {
      const result = await getAShareDashboard(current.signal);
      if (!current.signal.aborted) levelTwo.value = result.shenwan;
    } catch {
      if (!current.signal.aborted) levelTwoError.value = '二级行业读取失败。';
    } finally {
      if (!current.signal.aborted) levelTwoLoading.value = false;
    }
  }
  watch([levelTwoOpen, () => props.refreshKey], ([open], [, previous]) => {
    if (open && (!levelTwo.value || props.refreshKey !== previous)) void loadLevelTwo();
  });
  onBeforeUnmount(() => levelTwoController?.abort());
  const filteredIndustries = computed(() => {
    const query = industrySearch.value.trim();
    return industries.value.filter(
      (row) => row.code === selected.value?.code || `${row.name} ${row.code}`.includes(query),
    );
  });
  function selectIndustry(event: Event) {
    emit('industry', (event.target as HTMLSelectElement).value);
    industrySearch.value = '';
  }
  const related = computed(() => industryThemes(props.data.themes, selected.value?.code || ''));
  const monitor = shallowRef<MarketMonitor>();
  const monitorError = ref(''),
    monitorLoading = ref(false);
  let controller: AbortController | undefined;
  const findIndustry = (key: string) =>
    ((monitor.value?.sources[key]?.data as MonitorItem[]) || []).find(
      (row) => industryCode(row.code) === industryCode(selected.value?.code),
    );
  const profit = computed(() => findIndustry('growth_netProfitYoy'));
  const monitorIndustry = computed(() => findIndustry('industry'));
  const heat = computed(() => monitorIndustry.value?.history?.at(-1));
  const heatMetric = ref<'turnover' | 'amount'>('amount');
  const heatDates = computed(
    () => monitorIndustry.value?.history?.slice(-10).map((point) => point.date) || [],
  );
  const heatRows = computed(() =>
    ((monitor.value?.sources.industry?.data as MonitorItem[]) || []).map((row) => {
      const dates = new Map(row.history?.map((point) => [point.date, point[heatMetric.value]]));
      return {
        ...row,
        cells: heatDates.value.map((date) => {
          const raw = dates.get(date);
          const value = raw == null ? null : Number(raw);
          const background =
            value == null || !Number.isFinite(value)
              ? undefined
              : value >= 50
              ? `rgba(220,60,70,${0.06 + value / 500})`
              : `rgba(0,150,100,${0.06 + (100 - value) / 500})`;
          return {
            date,
            style: { background },
            text: value == null || !Number.isFinite(value) ? '—' : value.toFixed(0),
          };
        }),
      };
    }),
  );
  const growthMetrics = [
    ['netProfitYoy', '净利润同比'],
    ['orYoy', '营业收入同比'],
    ['opYoy', '营业利润同比'],
    ['trYoy', '营业总收入同比'],
    ['ebtYoy', '利润总额同比'],
    ['roeYoy', 'ROE同比增长率'],
  ];
  const growthRows = computed(() =>
    growthMetrics.map(([key, name]) => ({
      key,
      name,
      item: findIndustry('growth_' + key),
      source: monitor.value?.sources['growth_' + key],
    })),
  );
  const fmt = (value: EquityValue | undefined) =>
    value == null || value === '' || !Number.isFinite(Number(value))
      ? '—'
      : Number(value).toFixed(2);
  const fmtPct = (value: EquityValue | undefined) => {
    const formatted = fmt(value);
    return formatted === '—' ? formatted : formatted + '%';
  };
  const tone = (value: EquityValue | undefined) =>
    value == null ? '' : Number(value) > 0 ? 'positive' : Number(value) < 0 ? 'negative' : '';
  async function loadMonitor() {
    controller?.abort();
    const current = (controller = new AbortController());
    monitorLoading.value = true;
    monitorError.value = '';
    try {
      const result = await getMarketMonitor(current.signal, [
        'industry',
        ...growthMetrics.map(([key]) => 'growth_' + key),
      ]);
      if (!current.signal.aborted) monitor.value = result;
    } catch {
      if (!current.signal.aborted) monitorError.value = '行业拥挤度与景气读取失败，已有数据保留。';
    } finally {
      if (!current.signal.aborted) monitorLoading.value = false;
    }
  }
  watch(() => props.refreshKey, loadMonitor, { immediate: true });
  const technologyRows = shallowRef<NonNullable<EquityObservatory['crowding']>>([]);
  const technologyError = ref('');
  let technologyController: AbortController | undefined;
  async function loadTechnology() {
    technologyController?.abort();
    const current = (technologyController = new AbortController());
    technologyError.value = '';
    try {
      const result = await getEquityObservatory('cn', current.signal, 'structure');
      if (!current.signal.aborted) technologyRows.value = result.crowding || [];
    } catch {
      if (!current.signal.aborted) technologyError.value = '科技细分行业分位读取失败。';
    }
  }
  watch(() => props.refreshKey, loadTechnology, { immediate: true });
  onBeforeUnmount(() => {
    controller?.abort();
    technologyController?.abort();
  });
</script>
<style scoped src="./objectResearch.css"></style>
<style scoped>
  .industry-valuation-tables {
    display: grid;
    min-width: 0;
    gap: 12px;
    margin-bottom: 14px;
  }

  .valuation-tabs {
    margin-bottom: 0;
    padding: 0;
    border: 0;
    background: transparent;
  }

  .industry-growth,
  .industry-heatmap {
    margin-bottom: 14px;
  }

  .heatmap-scroll {
    max-height: 620px;
  }

  .heatmap-scroll td {
    text-align: center;
  }

  .heatmap-scroll th button {
    border: 0;
    border-radius: 4px;
    background: transparent;
    color: inherit;
    cursor: pointer;
  }

  .heatmap-scroll th button[aria-pressed='true'] {
    background: #eaf2ff;
    color: #1d4ed8;
  }

  .industry-growth :deep(.monitor) {
    margin-top: 0;
  }

  .valuation-tabs button {
    min-height: 30px;
    padding: 4px 10px;
  }

  @media (min-width: 851px) {
    .industry-detail .object-columns {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      align-items: stretch;
    }
  }

  .industry-detail {
    min-width: 0;
  }

  .industry-overview {
    margin-bottom: 14px;
  }

  .level-two {
    margin-bottom: 14px;
  }

  .industry-history {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    align-items: start;
    gap: 14px;
    margin-top: 14px;
  }

  .industry-history > :deep(.chart-expand:not(:has(:modal)) .financing-chart) {
    margin: 0;
  }

  .industry-activity-history :deep(.empty) {
    display: grid;
    box-sizing: border-box;
    height: 380px;
    margin: 0;
    place-items: center;
  }

  @media (max-width: 1000px) {
    .industry-history {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  .industry-overview .object-controls input,
  .industry-overview .object-controls select {
    width: 150px;
  }

  .object-facts small {
    display: block;
    color: #60758f;
  }

  .research-detail {
    margin-top: 14px;
  }

  .research-detail > .disclosure-title {
    color: #354d68;
    font-size: 14px;
    font-weight: 600;
  }

  .object-heading h2 small {
    color: #7b8da4;
    font-size: 12px;
    font-weight: 400;
  }

  .related-strip {
    margin-top: 14px;
  }

  .related-links {
    display: flex;
    gap: 6px;
    min-width: 0;
    overflow-x: auto;
  }

  .related-links button {
    flex: none;
    padding: 3px 8px;
    border: 1px solid #d6e1ec;
    border-radius: 5px;
    background: transparent;
    color: #245da0;
    white-space: nowrap;
  }

  .disclosure-title {
    margin: 0 0 12px;
    color: #354d68;
    font-size: 14px;
    font-weight: 600;
  }
</style>
