<template>
  <section class="cross-card cross-card--monitor">
    <div class="card-head">
      <div>
        <h3>价差统计分析</h3>
      </div>
    </div>

    <div class="analysis-range analysis-range--inline">
      <div class="analysis-group analysis-group--row">
        <span>时间周期</span>
        <div class="analysis-tabs">
          <button
            v-for="period in analysisPeriods"
            :key="period"
            :class="{ active: selectedAnalysisPeriod === period }"
            @click="selectedAnalysisPeriod = period"
          >
            {{ period }}
          </button>
        </div>
      </div>
      <div class="analysis-group analysis-group--row">
        <span>数据范围</span>
        <div class="analysis-tabs analysis-tabs--range">
          <button
            v-for="range in analysisDataRanges"
            :key="range"
            :class="{ active: selectedAnalysisDataRange === range }"
            @click="selectDataRange(range)"
          >
            {{ range }}
          </button>
          <button
            type="button"
            class="analysis-custom-toggle"
            :class="{ active: selectedAnalysisDataRange === '自定义' }"
            title="Custom range"
            aria-label="Custom range"
            @click="selectCustomRange"
          >
            <span>◫</span>
          </button>
        </div>
      </div>
    </div>

    <div v-if="customRangeOpen" class="analysis-custom-panel">
      <label>
        <span>开始</span>
        <input v-model="customRangeStart" type="date" />
      </label>
      <label>
        <span>结束</span>
        <input v-model="customRangeEnd" type="date" />
      </label>
    </div>

    <div class="stats-list">
      <div><span>90%分位</span><strong>0.82 USDT</strong></div>
      <div><span>75%分位</span><strong>0.18 USDT</strong></div>
      <div><span>50%分位</span><strong class="green">-0.06 USDT</strong></div>
      <div><span>25%分位</span><strong class="green">-0.34 USDT</strong></div>
      <div><span>10%分位</span><strong class="green">-0.92 USDT</strong></div>
    </div>

    <div class="monitor-box">
      <label class="field-block">
        <span>价差监控类型</span>
        <div class="input-row input-row--select">
          <select v-model="alertType">
            <option value="做多价差">做多价差（BY Ask - MT5 Bid）</option>
            <option value="做空价差">做空价差（BY Bid - MT5 Ask）</option>
            <option value="USDT Basis">USDT Basis</option>
          </select>
        </div>
      </label>

      <div class="monitor-grid">
        <label class="field-block">
          <span>触发条件</span>
          <div class="input-row input-row--condition">
            <select v-model="alertOperator">
              <option value="<=">&lt;=</option>
              <option value=">=">&gt;=</option>
            </select>
            <input :value="alertThreshold.toFixed(2)" @input="handleDecimalInput" />
            <em>USDT</em>
          </div>
        </label>
        <label class="field-block">
          <span>持续时间</span>
          <div class="input-row">
            <input :value="String(alertSeconds)" @input="handleIntegerInput('seconds', $event)" />
            <em>分钟</em>
          </div>
        </label>
        <label class="field-block">
          <span>触发后延迟校验</span>
          <div class="input-row">
            <input :value="String(alertDelay)" @input="handleIntegerInput('delay', $event)" />
            <em>秒</em>
          </div>
        </label>
        <label class="field-block">
          <span>预警渠道</span>
          <div class="input-row input-row--single-select">
            <select v-model="alertChannel">
              <option value="全部渠道">全部渠道</option>
              <option value="页面">页面</option>
              <option value="声音">声音</option>
              <option value="Webhook">Webhook</option>
            </select>
          </div>
        </label>
      </div>
    </div>

    <div class="monitor-footer">
      <div class="monitor-status monitor-status--row">
        <div>
          <span>监控状态</span>
          <strong :class="monitorRunning ? 'green' : 'warning'">
            {{ monitorRunning ? '运行中' : '已暂停' }}
          </strong>
        </div>
        <div>
          <span>运行时长</span>
          <strong>{{ monitorRuntime }}</strong>
        </div>
        <div>
          <span>上次触发</span>
          <strong>{{ lastTriggerTime }}</strong>
        </div>
      </div>

      <div class="submit-row submit-row--compact">
        <button class="submit-btn submit-btn--green submit-btn--monitor" @click="toggleMonitor(true)">
          下达监控
        </button>
        <button class="submit-btn submit-btn--red submit-btn--monitor" @click="toggleMonitor(false)">
          停止监控
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { ref } from 'vue';
  import {
    CROSS_SPREAD_ANALYSIS_DATA_RANGES,
    CROSS_SPREAD_ANALYSIS_PERIODS,
  } from '../composables/crossSpreadFixtures';

  const analysisPeriods = CROSS_SPREAD_ANALYSIS_PERIODS;
  const analysisDataRanges = CROSS_SPREAD_ANALYSIS_DATA_RANGES;
  const selectedAnalysisPeriod = ref('1m');
  const selectedAnalysisDataRange = ref('500');
  const customRangeOpen = ref(false);
  const customRangeStart = ref('2026-06-01');
  const customRangeEnd = ref('2026-06-30');
  const monitorRunning = ref(true);
  const monitorRuntime = ref('01:26:45');
  const lastTriggerTime = ref('15:34:01');
  const alertType = ref('做多价差');
  const alertOperator = ref('<=');
  const alertThreshold = ref(-2.5);
  const alertSeconds = ref(1);
  const alertDelay = ref(30);
  const alertChannel = ref('全部渠道');

  function selectDataRange(range: string) {
    selectedAnalysisDataRange.value = range;
    customRangeOpen.value = false;
  }

  function selectCustomRange() {
    selectedAnalysisDataRange.value = '自定义';
    customRangeOpen.value = true;
  }

  function handleDecimalInput(event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    alertThreshold.value = Number.isFinite(value) ? value : 0;
  }

  function handleIntegerInput(field: 'seconds' | 'delay', event: Event) {
    const value = Number((event.target as HTMLInputElement).value);
    const nextValue = Number.isFinite(value) ? Math.max(0, Math.round(value)) : 0;
    if (field === 'seconds') alertSeconds.value = nextValue;
    if (field === 'delay') alertDelay.value = nextValue;
  }

  function toggleMonitor(nextState: boolean) {
    monitorRunning.value = nextState;
    lastTriggerTime.value = nextState ? '15:34:01' : '--';
  }
</script>

<style scoped lang="less">
  .cross-card {
    padding: 16px 18px 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 18px;
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
  }

  .cross-card--monitor {
    padding: 14px;
  }

  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
  }

  .card-head h3 {
    margin: 0;
    font-family: var(--strategy-font-heading);
    font-size: 21px;
    font-weight: 800;
    letter-spacing: -0.012em;
    color: var(--strategy-text-1);
  }

  .analysis-range,
  .analysis-group,
  .monitor-status {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .analysis-range {
    gap: 12px;
    margin-bottom: 14px;
  }

  .analysis-range--inline {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 18px;
  }

  .analysis-range--inline .analysis-group {
    flex: 1;
    min-width: 0;
  }

  .analysis-group--row {
    flex-direction: row;
    align-items: center;
    gap: 14px;
  }

  .analysis-group--row .analysis-tabs {
    flex-wrap: wrap;
  }

  .analysis-group span,
  .field-block > span {
    color: #2f3640;
    font-size: 13px;
    font-weight: 700;
    white-space: nowrap;
  }

  .analysis-tabs {
    display: flex;
    gap: 8px;
  }

  .analysis-tabs--range {
    align-items: center;
  }

  .analysis-tabs button,
  .analysis-custom-toggle {
    height: 32px;
    min-width: 42px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 10px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }

  .analysis-custom-toggle {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0 10px;
  }

  .analysis-tabs button.active,
  .analysis-custom-toggle.active {
    border-color: rgba(201, 72, 72, 0.18);
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
    box-shadow: inset 0 0 0 1px rgba(201, 72, 72, 0.08);
  }

  .analysis-custom-panel {
    display: flex;
    gap: 10px;
    margin: 2px 0 14px;
  }

  .analysis-custom-panel label {
    display: grid;
    gap: 6px;
    min-width: 170px;
  }

  .analysis-custom-panel span {
    color: #556a87;
    font-size: 12px;
    font-weight: 700;
  }

  .analysis-custom-panel input {
    height: 32px;
    padding: 0 10px;
    border: 1px solid #d7e2ef;
    border-radius: 10px;
    background: #fff;
    color: #152646;
    font-size: 13px;
    font-weight: 600;
  }

  .stats-list {
    display: grid;
    gap: 10px;
    margin-bottom: 14px;
    padding: 12px 14px 10px;
    border: 1px solid #d8e2ec;
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(243, 248, 252, 0.98) 100%);
  }

  .stats-list div,
  .monitor-status div {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .stats-list strong,
  .monitor-status strong {
    color: var(--strategy-text-1);
    font-size: 16px;
    font-weight: 800;
  }

  .monitor-box {
    margin-bottom: 14px;
    padding: 14px 16px 16px;
    border: 1px solid #d8e2ec;
    border-radius: 16px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(243, 248, 252, 0.98) 100%);
  }

  .monitor-box > .field-block {
    max-width: 100%;
  }

  .monitor-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-top: 12px;
  }

  .monitor-grid .field-block {
    max-width: 100%;
  }

  .field-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .input-row {
    display: grid;
    grid-template-columns: 1fr 62px;
    height: 48px;
    overflow: hidden;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 12px;
    background: var(--strategy-surface);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  }

  .input-row input,
  .input-row select {
    width: 100%;
    min-width: 0;
    padding: 0 14px;
    border: none;
    outline: none;
    background: transparent;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-data);
    font-size: 15px;
    font-weight: 700;
  }

  .input-row em {
    display: flex;
    align-items: center;
    justify-content: center;
    border-left: 1px solid var(--strategy-border);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
    font-size: 13px;
    font-style: normal;
    font-weight: 700;
  }

  .input-row--select,
  .input-row--single-select {
    grid-template-columns: minmax(0, 1fr);
  }

  .input-row--select select,
  .input-row--single-select select {
    width: 100%;
    min-width: 0;
    padding-right: 28px;
  }

  .input-row--condition {
    grid-template-columns: 58px minmax(0, 1fr) 64px;
  }

  .input-row--condition select {
    padding: 0 18px 0 10px;
    border-right: 1px solid #e7ebf0;
    text-align: center;
    text-align-last: center;
  }

  .input-row--condition input {
    padding-right: 8px;
  }

  .monitor-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
  }

  .monitor-status {
    flex: 1;
  }

  .monitor-status--row {
    flex-direction: row;
    align-items: center;
    gap: 26px;
    padding-top: 2px;
  }

  .monitor-status--row div {
    min-width: 0;
  }

  .monitor-status strong {
    font-size: 18px;
  }

  .monitor-status--row strong {
    font-weight: 500;
  }

  .submit-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 16px;
    margin-top: 16px;
  }

  .submit-row--compact {
    margin-top: 0;
  }

  .submit-btn {
    flex: 1;
    height: 52px;
    border: none;
    border-radius: 12px;
    color: #fff;
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 0.01em;
    cursor: pointer;
  }

  .submit-btn--green {
    background: linear-gradient(90deg, #16a34a 0%, #0f8f3e 100%);
  }

  .submit-btn--red {
    background: linear-gradient(90deg, #ff4b4b 0%, #e92222 100%);
  }

  .submit-btn--monitor {
    max-width: 156px;
  }

  .green {
    color: #179b4b !important;
  }

  .warning {
    color: #d99612 !important;
  }

  @media (max-width: 1480px) {
    .monitor-grid {
      grid-template-columns: 1fr;
    }

    .analysis-range--inline,
    .monitor-status--row {
      grid-template-columns: 1fr;
      flex-direction: column;
    }
  }

  @media (max-width: 960px) {
    .submit-row,
    .monitor-footer {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
