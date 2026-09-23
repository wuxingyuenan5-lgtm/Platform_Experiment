<template>
  <div class="fedwatch-panel">
    <div v-if="loading" class="fedwatch-panel__state">加载中…</div>
    <div v-else-if="error" class="fedwatch-panel__state fedwatch-panel__state--error">
      {{ error }}
    </div>
    <div v-else-if="meetings.length === 0" class="fedwatch-panel__state"> 暂无 FedWatch 数据 </div>
    <div v-else class="fedwatch-panel__body">
      <!-- 顶部 header：标题 + 更新时间 | 右上次会议 + 当前目标 -->
      <header class="fedwatch-panel__header">
        <span class="fedwatch-panel__updated">更新 {{ updatedTime }}</span>
        <span class="fedwatch-panel__headline-meta">
          下次会议 {{ nextMeetingLabel }} · 当前 {{ currentTarget ?? '—' }}
        </span>
      </header>

      <!-- 3 段汇总卡：降息 Ease / 维持 No Change / 加息 Hike（首场会议口径） -->
      <section class="fedwatch-panel__summary">
        <div class="fedwatch-panel__metric fedwatch-panel__metric--ease">
          <span class="fedwatch-panel__metric-label">降息 Ease</span>
          <strong class="fedwatch-panel__metric-value">{{ formatPct(nextSummary.ease) }}</strong>
        </div>
        <div
          class="fedwatch-panel__metric fedwatch-panel__metric--no-change"
          :class="{ 'fedwatch-panel__metric--leader': leader === 'no_change' }"
        >
          <span class="fedwatch-panel__metric-label">维持 No Change</span>
          <strong class="fedwatch-panel__metric-value">{{
            formatPct(nextSummary.noChange)
          }}</strong>
        </div>
        <div
          class="fedwatch-panel__metric fedwatch-panel__metric--hike"
          :class="{ 'fedwatch-panel__metric--leader': leader === 'hike' }"
        >
          <span class="fedwatch-panel__metric-label">加息 Hike</span>
          <strong class="fedwatch-panel__metric-value">{{ formatPct(nextSummary.hike) }}</strong>
        </div>
      </section>

      <!-- 矩阵：行=会议日期，列=8 个目标利率区间，单元格高亮每行 maxProb -->
      <section class="fedwatch-panel__matrix">
        <div class="fedwatch-panel__table-wrap">
          <table class="fedwatch-panel__table">
            <thead>
              <tr>
                <th class="fedwatch-panel__corner">会议日期</th>
                <th v-for="range in ranges" :key="range" class="fedwatch-panel__range-head">
                  {{ range }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(meeting, idx) in meetings"
                :key="meeting.date"
                :class="{ 'fedwatch-panel__row--official': idx === 0 }"
              >
                <th class="fedwatch-panel__meeting-cell">
                  {{ formatMeetingDate(meeting.date) }}
                  <span v-if="idx === 0" class="fedwatch-panel__today">今天</span>
                </th>
                <td
                  v-for="range in ranges"
                  :key="range + '|' + meeting.date"
                  class="fedwatch-panel__cell"
                  :class="cellClass(meeting, range)"
                >
                  {{ formatProbability(meeting.probabilities[range]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 底部说明 -->
      <p class="fedwatch-panel__footnote">
        概率由 30 天联邦基金期货曲线计算；当前行情源：{{ settlementSource ?? '—' }}。
        <template v-if="observedAt"> 数据抓取于 {{ observedAt }}。 </template>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, onMounted, ref } from 'vue';

  import { getMacroFedwatch, type FedWatchData, type FedWatchMeeting } from '@/api/hedgeResearch';

  const loading = ref(true);
  const error = ref('');
  const data = ref<FedWatchData | null>(null);

  const meetings = computed(() => data.value?.meetings ?? []);
  const currentTarget = computed(() => data.value?.currentTarget ?? null);
  const observedAt = computed(() => data.value?.observedAt ?? null);
  const settlementSource = computed(() => data.value?.settlementSource ?? null);

  // 显示在 header 右上的下次会议日期（MM/DD/YY）
  const nextMeetingLabel = computed(() => {
    const m = meetings.value[0];
    if (!m) return '—';
    return formatMeetingDate(m.date);
  });

  // 显示更新时间（小时级采集时间，按浏览器本地时区展示）
  const updatedTime = computed(() => {
    const ts = observedAt.value;
    if (!ts) {
      const d = new Date();
      return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
    }
    const d = new Date(ts.includes('T') ? ts : `${ts}T00:00:00`);
    if (Number.isNaN(d.getTime())) return '—';
    return `${d.toLocaleDateString('zh-CN')} ${String(d.getHours()).padStart(2, '0')}:${String(
      d.getMinutes(),
    ).padStart(2, '0')}`;
  });

  /** 当前目标利率下限（bps，整数），用于判断 ease/no_change/hike */
  const currentTargetLowerBps = computed<number | null>(() => {
    const v = currentTarget.value;
    if (!v) return null;
    const m = v.match(/(\d+(?:\.\d+)?)%?-(\d+(?:\.\d+)?)%?/);
    if (!m) return null;
    return Math.round(parseFloat(m[1]) * 100);
  });

  /** 首场会议三段汇总（降息/维持/加息） */
  const nextSummary = computed(() => {
    const m = meetings.value[0];
    const lower = currentTargetLowerBps.value;
    if (!m || lower == null) return { ease: 0, noChange: 0, hike: 0 };
    let ease = 0;
    let noChange = 0;
    let hike = 0;
    for (const [key, v] of Object.entries(m.probabilities ?? {})) {
      const probability = normalizeProbability(v);
      if (probability <= 0) continue;
      const rngLower = parseLower(key);
      if (rngLower < lower) ease += probability;
      else if (rngLower === lower) noChange += probability;
      else hike += probability;
    }
    return {
      ease,
      noChange,
      hike: Math.min(hike, 100 - noChange),
    };
  });

  /** 首场会议中哪段最大（用于 leader 高亮） */
  const leader = computed<'ease' | 'no_change' | 'hike' | null>(() => {
    const s = nextSummary.value;
    if (s.noChange + s.ease + s.hike < 0.5) return null;
    if (s.hike >= s.noChange && s.hike >= s.ease) return 'hike';
    if (s.noChange >= s.ease) return 'no_change';
    return 'ease';
  });

  /** 所有出现过的目标利率区间（升序，自然顺序），保证 8 列固定 */
  const ranges = computed(() => {
    const set = new Set<string>();
    for (const meeting of meetings.value) {
      for (const key of Object.keys(meeting.probabilities ?? {})) set.add(key);
    }
    return [...set].sort((a, b) => parseLower(a) - parseLower(b));
  });

  function parseLower(label: string): number {
    const raw = Number(label.split('-')[0].replace('%', ''));
    if (!Number.isFinite(raw)) return 0;
    // The API uses basis points in matrix keys (375-400), while the current
    // target is a percentage range (3.75%-4.00%). Normalize both to bps.
    return raw < 20 ? Math.round(raw * 100) : raw;
  }

  function formatMeetingDate(iso: string): string {
    // iso = YYYY-MM-DD -> MM/DD/YY
    const [y, m, d] = iso.split('-');
    return `${m}/${d}/${y.slice(2)}`;
  }

  function formatProbability(value: number | undefined): string {
    if (value == null) return '0.0%';
    return `${normalizeProbability(value).toFixed(1)}%`;
  }

  function formatPct(value: number): string {
    return `${normalizeProbability(value).toFixed(1)}%`;
  }

  function normalizeProbability(value: number | undefined): number {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed <= 0) return 0;
    // Accept both the persisted percentage contract (42.0) and a legacy
    // fractional payload (0.42), but never multiply an already-percent value.
    return parsed <= 1 ? parsed * 100 : Math.min(parsed, 100);
  }

  /**
   * 矩阵单元格样式（对齐 data.rtatrade.xyz 截图）：
   *  - 0 / 缺失：fw-zero（暗淡文本）
   *  - 该行 maxProb：fw-max（金底）
   *  - 其他：常规
   */
  function cellClass(meeting: FedWatchMeeting, range: string): string {
    const v = meeting.probabilities?.[range];
    if (v == null || v <= 0) return 'fedwatch-panel__cell--zero';
    const probs = Object.values(meeting.probabilities ?? {})
      .map((x) => normalizeProbability(x))
      .filter((x) => x > 0);
    if (probs.length === 0) return '';
    const max = Math.max(...probs);
    if (normalizeProbability(v) >= max && max >= 0.5) return 'fedwatch-panel__cell--max';
    return '';
  }

  onMounted(async () => {
    try {
      const response = await getMacroFedwatch();
      data.value = response.data;
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'FedWatch 数据获取失败';
    } finally {
      loading.value = false;
    }
  });
</script>

<style scoped lang="less">


  @media (max-width: 640px) {
    .fedwatch-panel__summary {
      grid-template-columns: 1fr;
    }

    .fedwatch-panel__metric-value {
      font-size: 18px;
    }
  }

  .fedwatch-panel {
    min-height: 200px;
    padding: 6px 2px 0;
    color: var(--strategy-text-1, #13243d);
  }

  .fedwatch-panel__state {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 180px;
    color: var(--strategy-text-faint, #667085);
    font-size: 13px;
  }

  .fedwatch-panel__state--error {
    color: var(--strategy-danger, #df4d4d);
  }

  .fedwatch-panel__body {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  /* ---------- header ---------- */
  .fedwatch-panel__header {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    align-items: baseline;
    justify-content: space-between;
    padding: 4px 2px 0;
  }

  .fedwatch-panel__title {
    display: inline-flex;
    align-items: baseline;
    gap: 10px;
    color: var(--strategy-text-1, #13243d);
    font-size: 14px;
    font-weight: 700;
  }

  .fedwatch-panel__updated {
    color: var(--strategy-text-faint, #667085);
    font-size: 11px;
    font-weight: 500;
  }

  .fedwatch-panel__headline-meta {
    color: var(--strategy-text-2, #2f3e52);
    font-size: 12px;
    font-weight: 500;
  }

  /* ---------- 3 段汇总卡 ---------- */
  .fedwatch-panel__summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 8px;
  }

  .fedwatch-panel__metric {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 10px 8px;
    transition: transform 0.12s ease, border-color 0.12s ease;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 8px;
    background: var(--strategy-surface-muted, #f5f8fc);
    gap: 4px;
  }

  .fedwatch-panel__metric-label {
    color: var(--strategy-text-2, #2f3e52);
    font-size: 11.5px;
    font-weight: 500;
    letter-spacing: 0.02em;
  }

  .fedwatch-panel__metric-value {
    color: var(--strategy-text-1, #13243d);
    font-size: 22px;
    font-weight: 700;
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }

  /* 美式惯例：no-change 金色，ease 绿/跌色（平台 A 股绿=跌/负向），hike 红/涨色（平台 A 股红=涨/正向） */
  .fedwatch-panel__metric--no-change {
    border-color: #d6b94a;
    background: #fff7df;
  }

  .fedwatch-panel__metric--no-change .fedwatch-panel__metric-value {
    color: #8a6b00;
  }

  .fedwatch-panel__metric--ease {
    border-color: #c6e3cf;
    background: #ecf8f0;
  }

  .fedwatch-panel__metric--ease .fedwatch-panel__metric-value {
    color: #1d8a4a;
  }

  .fedwatch-panel__metric--hike {
    border-color: #f3c5c5;
    background: #fdecec;
  }

  .fedwatch-panel__metric--hike .fedwatch-panel__metric-value {
    color: #c0392b;
  }

  /* ---------- 矩阵 ---------- */
  .fedwatch-panel__matrix {
    padding: 10px 12px 12px;
    border: 1px solid var(--strategy-border, #e5ebf3);
    border-radius: 10px;
    background: #fff;
  }

  .fedwatch-panel__table-wrap {
    overflow-x: auto;
  }

  .fedwatch-panel__table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  .fedwatch-panel__table th,
  .fedwatch-panel__table td {
    padding: 6px 8px;
    border-right: 1px solid var(--strategy-border-soft, #edf2f7);
    border-bottom: 1px solid var(--strategy-border-soft, #edf2f7);
    text-align: center;
  }

  .fedwatch-panel__table th:last-child,
  .fedwatch-panel__table td:last-child {
    border-right: none;
  }

  .fedwatch-panel__table thead th {
    background: var(--strategy-table-head-bg, #f7f9fc);
    color: var(--strategy-text-2, #2f3e52);
    font-weight: 700;
  }

  .fedwatch-panel__corner {
    min-width: 88px;
    background: var(--strategy-surface-muted, #f5f8fc);
    text-align: left !important;
  }

  .fedwatch-panel__range-head {
    font-size: 11.5px;
    font-variant-numeric: tabular-nums;
  }

  .fedwatch-panel__meeting-cell {
    min-width: 88px;
    background: var(--strategy-surface-muted, #f5f8fc);
    color: var(--strategy-text-1, #13243d);
    font-weight: 600;
    text-align: left !important;
  }

  .fedwatch-panel__today {
    display: inline-block;
    margin-left: 6px;
    padding: 1px 6px;
    border: 1px solid var(--strategy-accent, #d4af37);
    border-radius: 4px;
    background: #fff7df;
    color: #8a6b00;
    font-size: 10px;
    font-weight: 600;
    vertical-align: 1px;
  }

  .fedwatch-panel__cell {
    color: var(--strategy-text-2, #2f3e52);
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }

  .fedwatch-panel__cell--zero {
    color: var(--strategy-text-faint, #9aa7b6);
    font-weight: 400;
  }

  .fedwatch-panel__cell--max {
    border: 1px solid #e7c87e;
    background: #fff2c8;
    color: #7a5b00;
  }

  .fedwatch-panel__row--official .fedwatch-panel__meeting-cell {
    color: var(--strategy-accent, #d4af37);
  }

  /* ---------- footnote ---------- */
  .fedwatch-panel__footnote {
    margin: 0;
    color: var(--strategy-text-faint, #667085);
    font-size: 11px;
    line-height: 1.6;
  }
</style>
