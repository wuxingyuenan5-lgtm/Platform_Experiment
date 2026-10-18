<template>
  <div class="polymarket-fed-panel">
    <div v-if="loading" class="polymarket-fed-panel__state">加载 Polymarket 历史概率…</div>
    <div v-else-if="error" class="polymarket-fed-panel__state polymarket-fed-panel__state--error">
      {{ error }}
    </div>
    <div v-else-if="!events.length" class="polymarket-fed-panel__state">暂无货币政策事件数据</div>
    <div v-else class="polymarket-fed-panel__body">
      <header class="polymarket-fed-panel__toolbar">
        <div>
          <strong>FOMC 会议利率路径</strong>
          <span>加息、维持与降息概率 · 历史数据</span>
        </div>
        <div class="polymarket-fed-panel__ranges" role="tablist" aria-label="历史范围">
          <button
            v-for="option in rangeOptions"
            :key="option.value"
            type="button"
            :class="{ 'is-active': selectedRange === option.value }"
            role="tab"
            :aria-selected="selectedRange === option.value"
            @click="selectedRange = option.value"
          >
            {{ option.label }}
          </button>
        </div>
      </header>

      <div class="polymarket-fed-panel__contracts" role="tablist" aria-label="货币政策事件">
        <button
          v-for="(event, index) in events"
          :key="event.id"
          type="button"
          class="polymarket-fed-panel__contract"
          :class="{ 'is-active': selectedEventId === event.id }"
          role="tab"
          :aria-selected="selectedEventId === event.id"
          @click="selectedEventId = event.id"
        >
          <span>{{ event.label }}</span>
          <strong>{{ formatProbability(event.probability) }}</strong>
          <small>{{ index + 1 }} / {{ events.length }}</small>
        </button>
      </div>

      <section class="polymarket-fed-panel__chart" aria-label="Polymarket 历史概率曲线">
        <div class="polymarket-fed-panel__chart-head">
          <div>
            <h6 :title="selectedEvent?.originalLabel || undefined">{{ selectedEvent?.label }}</h6>
            <span>市场隐含概率（%）</span>
          </div>
          <span v-if="selectedEvent?.expiryAt">到期 {{ formatDate(selectedEvent.expiryAt) }}</span>
        </div>
        <svg viewBox="0 0 640 220" preserveAspectRatio="none">
          <line
            v-for="value in gridValues"
            :key="value"
            x1="38"
            :y1="yFor(value)"
            x2="630"
            :y2="yFor(value)"
          />
          <text v-for="value in gridValues" :key="`label-${value}`" x="2" :y="yFor(value) + 4">
            {{ value }}
          </text>
          <polyline :points="chartPoints" />
        </svg>
        <div class="polymarket-fed-panel__axis">
          <span>{{ chartStart }}</span>
          <span>{{ chartEnd }}</span>
        </div>
      </section>

      <footer class="polymarket-fed-panel__footnote">
        数据按 5 分钟周期从 Polymarket CLOB 历史价格接口抓取并存入平台，页面只读取本地历史快照。
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';
  import { getMacroExpectations, type MacroExpectationEvent } from '@/api/hedgeResearch';

  type RangeKey = '1D' | '7D' | '30D' | 'ALL';
  const rangeOptions: ReadonlyArray<{ value: RangeKey; label: string }> = [
    { value: '1D', label: '1日' },
    { value: '7D', label: '7日' },
    { value: '30D', label: '30日' },
    { value: 'ALL', label: '全部' },
  ];

  const loading = ref(true);
  const error = ref('');
  const response = ref<{ events: MacroExpectationEvent[] } | null>(null);
  const selectedRange = ref<RangeKey>('7D');
  const selectedEventId = ref('');
  const events = computed(() =>
    (response.value?.events ?? []).filter((event) => event.category === 'monetary_policy'),
  );
  const selectedEvent = computed(() => {
    return (
      events.value.find((event) => event.id === selectedEventId.value) ?? events.value[0] ?? null
    );
  });
  const history = computed(() => {
    const values = (selectedEvent.value?.history ?? [])
      .map((point) => ({
        time: new Date(point.observedAt).getTime(),
        value: Number(point.probability),
      }))
      .filter((point) => Number.isFinite(point.time) && Number.isFinite(point.value))
      .sort((a, b) => a.time - b.time);
    if (!values.length || selectedRange.value === 'ALL') return values;
    const days = Number(selectedRange.value.slice(0, -1));
    const cutoff = values[values.length - 1].time - days * 86_400_000;
    return values.filter((point) => point.time >= cutoff);
  });
  const chartPoints = computed(() => {
    if (!history.value.length) return '38,180 630,180';
    if (history.value.length === 1) {
      return `38,${yFor(history.value[0].value)} 630,${yFor(history.value[0].value)}`;
    }
    return history.value
      .map((point, index) => {
        const x = 38 + (index / (history.value.length - 1)) * 592;
        return `${x.toFixed(2)},${yFor(point.value).toFixed(2)}`;
      })
      .join(' ');
  });
  const chartStart = computed(() => formatDate(history.value[0]?.time));
  const chartEnd = computed(() => formatDate(history.value[history.value.length - 1]?.time));
  const gridValues = [100, 75, 50, 25, 0];

  function yFor(value: number) {
    return 20 + (1 - Math.min(100, Math.max(0, value)) / 100) * 160;
  }

  function formatProbability(value: string | number | null | undefined) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? `${parsed.toFixed(1)}%` : '—';
  }

  function formatDate(value: string | number | null | undefined) {
    if (value == null) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' });
  }

  onMounted(async () => {
    try {
      response.value = await getMacroExpectations();
      selectedEventId.value = events.value[0]?.id ?? '';
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : 'Polymarket 历史概率加载失败';
    } finally {
      loading.value = false;
    }
  });
</script>

<style scoped lang="less">
  .polymarket-fed-panel {
    min-height: 250px;
    color: var(--strategy-text-1, #13243d);
  }

  .polymarket-fed-panel__state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 220px;
    color: var(--strategy-text-faint, #667085);
    font-size: 13px;
  }

  .polymarket-fed-panel__state--error {
    color: var(--strategy-danger, #df4d4d);
  }

  .polymarket-fed-panel__body {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .polymarket-fed-panel__toolbar,
  .polymarket-fed-panel__chart-head,
  .polymarket-fed-panel__axis {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .polymarket-fed-panel__toolbar strong {
    display: block;
    font-size: 14px;
  }

  .polymarket-fed-panel__toolbar span,
  .polymarket-fed-panel__chart-head span,
  .polymarket-fed-panel__axis,
  .polymarket-fed-panel__footnote {
    color: var(--strategy-text-faint, #667085);
    font-size: 11px;
  }

  .polymarket-fed-panel__ranges {
    display: inline-flex;
    gap: 4px;
    padding: 3px;
    border: 1px solid var(--strategy-border, #e2e8f0);
    border-radius: 8px;
    background: #f8fafc;
  }

  .polymarket-fed-panel__ranges button {
    padding: 4px 8px;
    border: 0;
    border-radius: 6px;
    background: transparent;
    color: var(--strategy-text-3, #64748b);
    font-size: 11px;
    cursor: pointer;
  }

  .polymarket-fed-panel__ranges button.is-active {
    background: #fff;
    box-shadow: 0 1px 3px rgb(15 23 42 / 12%);
    color: #4338ca;
    font-weight: 700;
  }

  .polymarket-fed-panel__contracts {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 7px;
  }

  .polymarket-fed-panel__contract {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto;
    padding: 8px 10px;
    border: 1px solid var(--strategy-border, #e2e8f0);
    border-radius: 8px;
    background: #fff;
    color: var(--strategy-text-2, #334155);
    text-align: left;
    cursor: pointer;
    gap: 4px 8px;
  }

  .polymarket-fed-panel__contract span {
    grid-column: 1 / -1;
    overflow: hidden;
    font-size: 11px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .polymarket-fed-panel__contract strong {
    color: #4338ca;
    font-size: 17px;
  }

  .polymarket-fed-panel__contract small {
    align-self: end;
    color: var(--strategy-text-4, #94a3b8);
    font-size: 10px;
  }

  .polymarket-fed-panel__contract.is-active {
    border-color: #818cf8;
    background: #eef2ff;
  }

  .polymarket-fed-panel__chart {
    padding: 10px 10px 4px;
    border: 1px solid var(--strategy-border, #e2e8f0);
    border-radius: 10px;
    background: #fff;
  }

  .polymarket-fed-panel__chart-head {
    align-items: flex-start;
    margin-bottom: 4px;
  }

  .polymarket-fed-panel__chart-head h6 {
    max-width: 70%;
    margin: 0 0 3px;
    overflow: hidden;
    font-size: 12px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .polymarket-fed-panel__chart svg {
    display: block;
    width: 100%;
    height: 190px;
  }

  .polymarket-fed-panel__chart line {
    stroke-width: 1;
    stroke: #e2e8f0;
  }

  .polymarket-fed-panel__chart text {
    fill: #94a3b8;
    font-size: 10px;
  }

  .polymarket-fed-panel__chart polyline {
    stroke-width: 2;
    stroke-linecap: round;
    stroke: #4338ca;
    fill: none;
    stroke-linejoin: round;
    vector-effect: non-scaling-stroke;
  }

  .polymarket-fed-panel__axis {
    padding: 0 2px 2px 38px;
  }

  .polymarket-fed-panel__footnote {
    margin: 0;
    line-height: 1.5;
  }

  @media (max-width: 780px) {
    .polymarket-fed-panel__toolbar {
      flex-direction: column;
      align-items: flex-start;
    }
  }
</style>
