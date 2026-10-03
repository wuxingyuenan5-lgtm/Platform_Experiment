<template>
  <article class="pnl-calendar-card">
    <header class="pnl-calendar-header">
      <h3 class="pnl-calendar-heading">
        <button type="button" class="pnl-calendar-title" :title="titleHint" @click="toggleMode">
          {{ calendar.title }}
          <span class="pnl-calendar-switch">{{ isMonthly ? '按月' : '按日' }} ⇄</span>
        </button>
      </h3>

      <div class="pnl-calendar-nav">
        <button
          type="button"
          class="pnl-calendar-arrow"
          :aria-label="isMonthly ? '上一年' : '上一个月'"
          @click="step(-1)"
        >
          ‹
        </button>
        <strong class="pnl-calendar-cursor">{{ calendar.cursorLabel }}</strong>
        <button
          type="button"
          class="pnl-calendar-arrow"
          :disabled="!canForward"
          :aria-label="isMonthly ? '下一年' : '下一个月'"
          @click="step(1)"
        >
          ›
        </button>
      </div>
    </header>

    <p class="pnl-calendar-summary">
      <span>{{ calendar.summaryLabel }}</span>
      <strong :class="`is-${calendar.summaryTone}`">{{ calendar.summaryAmount }}</strong>
      <span>收益率</span>
      <strong :class="`is-${calendar.summaryTone}`">{{ calendar.summaryRateText }}</strong>
    </p>

    <ul v-if="!calendar.isMonthly" class="pnl-calendar-weekdays">
      <li v-for="label in calendar.weekdayLabels" :key="label">{{ label }}</li>
    </ul>

    <ul class="pnl-calendar-grid" :class="{ 'is-monthly': calendar.isMonthly }">
      <li
        v-for="cell in calendar.cells"
        :key="cell.key"
        :class="`is-${cell.tone}`"
        :title="cell.title || undefined"
      >
        <template v-if="cell.label">
          <em>{{ cell.label }}</em>
          <strong>{{ cell.amount }}</strong>
          <span v-if="cell.rateText">{{ cell.rateText }}</span>
        </template>
      </li>
    </ul>

    <p class="pnl-calendar-note">{{ note }}</p>
  </article>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import type { PnlCalendarCursor } from '../composables/strategyPnlCalendar';
  import { buildPnlCalendar, shiftMonth, todayBeijing } from '../composables/strategyPnlCalendar';
  import type { StrategyPnlDayPoint } from '@/data/sample/strategy';

  const props = defineProps<{
    points: StrategyPnlDayPoint[];
    currency: string;
    loadError?: string;
  }>();

  const isMonthly = ref(false);
  // 用户一旦自己翻过页，就不再跟着数据跳动，避免刷新把视图拉回去。
  const touched = ref(false);
  const cursor = ref<PnlCalendarCursor>(anchor(props.points));

  function currentBeijing(): PnlCalendarCursor {
    const [year, month] = todayBeijing().split('-').map(Number);
    return { year, month };
  }

  /** 默认落在最近有数据的那一个月；没有数据时落在当月。 */
  function anchor(points: StrategyPnlDayPoint[]): PnlCalendarCursor {
    let latest = '';
    for (const point of points) {
      if (point.date > latest) latest = point.date;
    }
    const [year, month] = latest.split('-').map(Number);
    if (!Number.isFinite(year) || !Number.isFinite(month)) return currentBeijing();
    return { year, month };
  }

  watch(
    () => props.points,
    (next) => {
      if (!touched.value) cursor.value = anchor(next);
    },
  );

  const calendar = computed(() =>
    buildPnlCalendar(
      props.points,
      props.currency,
      isMonthly.value ? 'monthly' : 'daily',
      cursor.value,
    ),
  );

  const canForward = computed(() => {
    const now = currentBeijing();
    return isMonthly.value
      ? cursor.value.year < now.year
      : cursor.value.year * 12 + cursor.value.month < now.year * 12 + now.month;
  });

  const note = computed(() =>
    !props.points.length && props.loadError ? props.loadError : calendar.value.note,
  );

  const titleHint = computed(() =>
    isMonthly.value ? '点击改为每日盈亏，可按月翻页' : '点击改为每月盈亏，可按年翻页',
  );

  function toggleMode() {
    touched.value = true;
    isMonthly.value = !isMonthly.value;
  }

  function step(delta: number) {
    touched.value = true;
    cursor.value = isMonthly.value
      ? { ...cursor.value, year: cursor.value.year + delta }
      : shiftMonth(cursor.value, delta);
  }
</script>

<style scoped lang="less">
  .pnl-calendar-card {
    display: grid;
    gap: 12px;
    padding: 18px 20px;
    border: 1px solid var(--strategy-border);
    border-radius: var(--strategy-radius-panel);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-card);
  }

  .pnl-calendar-header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .pnl-calendar-heading {
    margin: 0;
  }

  .pnl-calendar-title {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 0;
    border: none;
    background: transparent;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-heading);
    font-size: var(--strategy-font-card-title);
    font-weight: 800;
    cursor: pointer;
  }

  .pnl-calendar-title:hover {
    color: var(--strategy-accent-strong);
  }

  .pnl-calendar-switch {
    padding: 2px 8px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 999px;
    color: var(--strategy-text-3);
    font-family: var(--strategy-font-sans);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  .pnl-calendar-title:hover .pnl-calendar-switch {
    border-color: var(--strategy-accent-ring);
    color: var(--strategy-accent-strong);
  }

  .pnl-calendar-nav {
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  .pnl-calendar-arrow {
    width: var(--strategy-control-height);
    height: var(--strategy-control-height);
    border: 1px solid var(--strategy-border-strong);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface);
    box-shadow: var(--strategy-shadow-soft);
    color: var(--strategy-text-2);
    font-size: 18px;
    font-weight: 800;
    line-height: 1;
    cursor: pointer;
  }

  .pnl-calendar-arrow:hover:not(:disabled) {
    border-color: var(--strategy-accent-ring);
    color: var(--strategy-accent-strong);
  }

  .pnl-calendar-arrow:disabled {
    opacity: 0.55;
    color: var(--strategy-text-faint);
    cursor: not-allowed;
  }

  .pnl-calendar-cursor {
    min-width: 88px;
    color: var(--strategy-text-1);
    font-family: var(--strategy-font-data);
    font-size: var(--strategy-font-base);
    font-weight: 800;
    text-align: center;
  }

  .pnl-calendar-summary {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px 14px;
    margin: 0;
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-sm);
    font-weight: 700;
  }

  .pnl-calendar-summary strong {
    font-family: var(--strategy-font-data);
    font-size: var(--strategy-font-base);
    font-weight: 800;
  }

  .pnl-calendar-weekdays,
  .pnl-calendar-grid {
    display: grid;
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .pnl-calendar-weekdays li {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
    text-align: center;
  }

  .pnl-calendar-grid li {
    display: grid;
    align-content: space-between;
    gap: 4px;
    min-height: 68px;
    padding: 8px 10px;
    border: 1px solid var(--strategy-border-soft);
    border-radius: var(--strategy-radius-control);
    background: var(--strategy-surface-soft);
  }

  .pnl-calendar-grid.is-monthly li {
    align-content: center;
    min-height: 84px;
    text-align: center;
    justify-items: center;
    gap: 6px;
  }

  .pnl-calendar-grid em {
    color: var(--strategy-text-faint);
    font-size: var(--strategy-font-xs);
    font-style: normal;
    font-weight: 700;
  }

  .pnl-calendar-grid strong {
    font-family: var(--strategy-font-data);
    font-size: var(--strategy-font-base);
    font-weight: 800;
    letter-spacing: -0.01em;
  }

  .pnl-calendar-grid span {
    color: var(--strategy-text-3);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  .pnl-calendar-grid li.is-positive {
    border-color: rgb(24 155 80 / 28%);
    background: var(--strategy-success-soft);
  }

  .pnl-calendar-grid li.is-positive strong,
  .pnl-calendar-grid li.is-positive span {
    color: var(--strategy-success);
  }

  .pnl-calendar-grid li.is-negative {
    border-color: rgb(223 77 77 / 28%);
    background: var(--strategy-danger-soft);
  }

  .pnl-calendar-grid li.is-negative strong,
  .pnl-calendar-grid li.is-negative span {
    color: var(--strategy-danger);
  }

  .pnl-calendar-grid li.is-neutral strong,
  .pnl-calendar-grid li.is-neutral span {
    color: var(--strategy-text-2);
  }

  .pnl-calendar-grid li.is-unavailable {
    background: var(--strategy-surface);
  }

  .pnl-calendar-grid li.is-unavailable strong {
    color: var(--strategy-text-faint);
    font-weight: 700;
  }

  .pnl-calendar-note {
    margin: 0;
    color: var(--strategy-text-faint);
    font-size: var(--strategy-font-xs);
    font-weight: 700;
  }

  @media (max-width: 860px) {
    .pnl-calendar-grid li {
      min-height: 58px;
      padding: 6px;
    }

    .pnl-calendar-grid strong {
      font-size: var(--strategy-font-sm);
    }
  }
</style>
