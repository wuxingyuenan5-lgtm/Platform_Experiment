<template>
  <main class="spread-page" data-testid="spread-original-structure">
    <template v-if="localSection === 'analysis'">
      <RestoredProductSurface
        :state="spreadSampleMeta.state"
        :source="spreadSampleMeta.source"
        :as-of="spreadSampleMeta.asOf"
        :actionable="spreadSampleMeta.actionable"
        message="原研究筛选、价差路径与统计结构已选择性恢复；研究样例不可执行，正式执行工作区保持不变。"
      >
        <div class="spread-analysis-layout">
          <SpreadAnalysisWorkspaceHeader
            v-model:selected-venue="localVenue"
            v-model:left-leg-symbol="localLeftLeg"
            v-model:right-leg-symbol="localRightLeg"
            v-model:selected-resolution="localResolution"
          />
          <SpreadAnalysisOverview :items="spreadOverview" />

          <section class="spread-chart-card" data-testid="spread-research-chart">
            <div class="spread-chart-toolbar">
              <div>
                <select v-model="progressLevel" aria-label="价差图表周期">
                  <option value="15min">15min</option
                  ><option value="1h">1h</option
                  ><option value="4h">4h</option
                  ><option value="日线">日线</option>
                </select>
                <input v-model="startDate" type="date" aria-label="开始日期" />
                <input v-model="endDate" type="date" aria-label="结束日期" />
              </div>
              <div>
                <button
                  type="button"
                  :class="{ active: showSpread }"
                  @click="showSpread = !showSpread"
                  >价差</button
                >
                <button
                  type="button"
                  :class="{ active: showGoldPrice }"
                  @click="showGoldPrice = !showGoldPrice"
                  >黄金价格</button
                >
              </div>
            </div>
            <div class="chart-area" role="img" aria-label="跨所价差与黄金价格非实时样例路径">
              <svg v-if="showSpread" viewBox="0 0 800 280" preserveAspectRatio="none">
                <polyline
                  :points="toPoints(spreadSeries, 800, 250)"
                  fill="none"
                  class="spread-line"
                  stroke-width="4"
                />
              </svg>
              <svg v-if="showGoldPrice" viewBox="0 0 800 280" preserveAspectRatio="none">
                <polyline
                  :points="toPoints(goldPriceSeries, 800, 250)"
                  fill="none"
                  class="gold-line"
                  stroke-width="4"
                />
              </svg>
            </div>
            <footer
              ><span>{{ spreadChartDates[0] }}</span
              ><span>{{ progressLevel }} · 非实时</span
              ><span>{{ spreadChartDates[spreadChartDates.length - 1] }}</span></footer
            >
          </section>

          <SpreadStatisticsSection
            :decomposition="spreadDecomposition"
            :scenarios="spreadScenarios"
          />
        </div>
      </RestoredProductSurface>
    </template>

    <template v-else>
      <div class="execution-state">
        <div>
          <strong>正式 CrossVenueExecutionWorkspace</strong>
          <span>继续服从正式权限、审批、风险检查、ACK/Fill 区分和 result_unknown 处置语义。</span>
        </div>
        <b>Live Write 关闭</b>
      </div>
      <CrossVenueExecutionWorkspace
        :left-leg-symbol="localLeftLeg"
        :right-leg-symbol="localRightLeg"
      />
    </template>
  </main>
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import {
    goldPriceSeries,
    spreadChartDates,
    spreadDecomposition,
    spreadOverview,
    spreadSampleMeta,
    spreadScenarios,
    spreadSeries,
  } from '@/data/sample/spread';
  import CrossVenueExecutionWorkspace from './components/CrossVenueExecutionWorkspace.vue';
  import SpreadAnalysisOverview from './components/SpreadAnalysisOverview.vue';
  import SpreadAnalysisWorkspaceHeader from './components/SpreadAnalysisWorkspaceHeader.vue';
  import SpreadStatisticsSection from './components/SpreadStatisticsSection.vue';
  import type { SpreadWorkspaceVariant } from './types';

  const props = withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedVenue?: string;
      leftLegSymbol?: string;
      rightLegSymbol?: string;
      selectedResolution?: string;
      variant?: SpreadWorkspaceVariant;
    }>(),
    {
      activeSection: 'analysis',
      selectedVenue: 'Bybit',
      leftLegSymbol: 'XAUTUSDT.P',
      rightLegSymbol: 'XAUUSD+',
      selectedResolution: '30分钟',
      variant: 'crossVenue',
    },
  );

  const localSection = ref(props.activeSection);
  const localVenue = ref(props.selectedVenue);
  const localLeftLeg = ref(props.leftLegSymbol);
  const localRightLeg = ref(props.rightLegSymbol);
  const localResolution = ref(props.selectedResolution);
  const startDate = ref('2026-03-16');
  const endDate = ref('2026-04-16');
  const progressLevel = ref<'15min' | '1h' | '4h' | '日线'>('日线');
  const showSpread = ref(true);
  const showGoldPrice = ref(true);

  watch(
    () => props.activeSection,
    (value) => (localSection.value = value),
  );
  watch(
    () => props.selectedVenue,
    (value) => (localVenue.value = value),
  );
  watch(
    () => props.leftLegSymbol,
    (value) => (localLeftLeg.value = value),
  );
  watch(
    () => props.rightLegSymbol,
    (value) => (localRightLeg.value = value),
  );
  watch(
    () => props.selectedResolution,
    (value) => (localResolution.value = value),
  );

  function toPoints(values: number[], width: number, height: number): string {
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = Math.max(max - min, 1);
    return values
      .map(
        (value, index) =>
          `${((index / Math.max(values.length - 1, 1)) * width).toFixed(1)},${(
            height -
            ((value - min) / range) * (height - 40) -
            20
          ).toFixed(1)}`,
      )
      .join(' ');
  }
</script>

<style scoped lang="less">
  .spread-page,
  .spread-analysis-layout {
    display: grid;
    gap: 14px;
    color: #172033;
  }
  .spread-chart-card,
  .execution-state {
    padding: 18px;
    border: 1px solid #e1e7ef;
    border-radius: 14px;
    background: #fff;
  }
  .spread-chart-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }
  .spread-chart-toolbar > div {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  select,
  input,
  button {
    height: 36px;
    padding: 0 10px;
    border: 1px solid #dce3eb;
    border-radius: 8px;
    background: #fff;
    color: #526173;
  }
  button.active {
    border-color: #aac4dd;
    background: #edf4fa;
    color: #294a67;
    font-weight: 700;
  }
  .chart-area {
    position: relative;
    height: 330px;
    margin-top: 14px;
    overflow: hidden;
    border-radius: 12px;
    background: linear-gradient(to bottom, transparent 24%, #edf1f5 25%, transparent 26%) 0 0 / 100%
        82px,
      #fafbfd;
  }
  .chart-area svg {
    position: absolute;
    inset: 22px 12px;
    width: calc(100% - 24px);
    height: calc(100% - 44px);
  }
  .spread-line {
    stroke: #3da6de;
  }
  .gold-line {
    stroke: #d9a72d;
    opacity: 0.78;
  }
  .spread-chart-card footer {
    display: flex;
    justify-content: space-between;
    margin-top: 8px;
    color: #8290a5;
    font-size: 11px;
  }
  .execution-state {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .execution-state div {
    display: grid;
    gap: 4px;
  }
  .execution-state span {
    color: #687386;
    font-size: 12px;
  }
  .execution-state b {
    padding: 6px 10px;
    border-radius: 999px;
    background: #fff5d6;
    color: #8a6210;
    font-size: 12px;
  }
  @media (max-width: 720px) {
    .spread-chart-toolbar,
    .execution-state {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
