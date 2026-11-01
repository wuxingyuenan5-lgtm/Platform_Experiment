<template>
  <section class="execution-steps">
    <div class="execution-steps__head">
      <div>
        <h4>执行步骤</h4>
        <p class="trace">
          <template v-if="traceId">追踪号 {{ traceId }}</template>
          <template v-else>尚未提交指令</template>
        </p>
      </div>
      <button v-if="traceId" type="button" class="ghost" :disabled="loading" @click="emit('refresh')">
        {{ loading ? '刷新中' : '刷新' }}
      </button>
    </div>

    <p v-if="!traceId" class="hint">提交开仓或平仓后，这里会显示每一步的执行结果与中断原因。</p>
    <p v-else-if="loading && !timeline" class="hint">正在读取执行步骤…</p>
    <p v-else-if="!timeline || !timeline.steps.length" class="hint">暂无执行步骤记录。</p>

    <template v-else>
      <div class="summary" :class="`summary--${timeline.summary.outcome}`">
        <span class="summary__badge">{{ outcomeLabel(timeline.summary.outcome) }}</span>
        <span class="summary__meta">共 {{ timeline.summary.stepCount }} 步</span>
        <span v-if="timeline.summary.totalDurationMs" class="summary__meta">
          耗时 {{ timeline.summary.totalDurationMs }} ms
        </span>
        <span v-if="timeline.summary.blockedStageLabel" class="summary__meta summary__meta--stop">
          卡在「{{ timeline.summary.blockedStageLabel }}」
        </span>
      </div>
      <p v-if="timeline.summary.blockedReasonDetail" class="stop-reason">
        {{ timeline.summary.blockedReasonLabel || timeline.summary.blockedReasonCode }}：{{
          timeline.summary.blockedReasonDetail
        }}
      </p>

      <ol class="steps">
        <li v-for="step in timeline.steps" :key="step.id" class="step" :class="`step--${step.status}`">
          <span class="step__dot" aria-hidden="true"></span>
          <div class="step__body">
            <div class="step__row">
              <strong>{{ step.sequence }}. {{ step.stageLabel }}</strong>
              <span class="step__time">
                <template v-if="step.durationMs !== null">{{ step.durationMs }} ms</template>
                <template v-else>{{ clock(step.occurredAt) }}</template>
              </span>
            </div>
            <p v-if="step.reasonCode || step.reasonDetail" class="step__reason">
              {{ step.reasonLabel || step.reasonCode }}
              <span v-if="step.reasonDetail">：{{ step.reasonDetail }}</span>
              <span v-if="step.statusCode" class="step__code">HTTP {{ step.statusCode }}</span>
            </p>
            <p v-if="step.orderId" class="step__id">订单 {{ step.orderId }}</p>
            <details v-if="step.payload" class="step__payload">
              <summary>上下文</summary>
              <pre>{{ formatPayload(step.payload) }}</pre>
            </details>
          </div>
        </li>
      </ol>
    </template>
  </section>
</template>

<script setup lang="ts">
  import type { ExecutionOutcome, ExecutionTimeline } from '@/api/platform/executionSteps';

  defineProps<{
    timeline: ExecutionTimeline | null;
    loading: boolean;
    traceId: string | null;
  }>();

  const emit = defineEmits<{ (event: 'refresh'): void }>();

  const OUTCOME_LABELS: Record<ExecutionOutcome, string> = {
    passed: '全部通过',
    blocked: '被拦截',
    failed: '执行失败',
    in_progress: '执行中',
    not_found: '无记录',
  };

  function outcomeLabel(outcome: ExecutionOutcome): string {
    return OUTCOME_LABELS[outcome] ?? outcome;
  }

  function clock(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '--';
    return parsed.toLocaleTimeString('zh-CN', { hour12: false });
  }

  function formatPayload(payload: Record<string, unknown>): string {
    return Object.entries(payload)
      .map(([key, value]) => `${key}: ${value === null ? '--' : String(value)}`)
      .join('\n');
  }
</script>

<style scoped lang="less">
  .execution-steps {
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid var(--strategy-border-soft);
  }

  .execution-steps__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
  }

  .execution-steps__head h4 {
    margin: 0;
    font-size: 13px;
    font-weight: 700;
    color: var(--strategy-text-1);
  }

  .trace {
    margin: 4px 0 0;
    font-family: var(--strategy-font-data);
    font-size: 11px;
    color: var(--strategy-text-faint);
    word-break: break-all;
  }

  .ghost {
    height: 28px;
    padding: 0 12px;
    border: 1px solid var(--strategy-border-strong);
    border-radius: 8px;
    background: #fff;
    color: var(--strategy-text-2);
    font-size: 12px;
    cursor: pointer;
  }

  .ghost:disabled {
    opacity: 0.6;
    cursor: default;
  }

  .hint {
    margin: 8px 0 0;
    font-size: 12px;
    color: var(--strategy-text-faint);
  }

  .summary {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
    padding: 8px 10px;
    border-radius: 10px;
    background: var(--strategy-surface-muted);
    font-size: 12px;
    color: var(--strategy-text-2);
  }

  .summary__badge {
    padding: 2px 8px;
    border-radius: 999px;
    font-weight: 700;
  }

  .summary--passed .summary__badge {
    background: var(--strategy-success-soft);
    color: var(--strategy-success);
  }

  .summary--blocked .summary__badge {
    background: var(--strategy-warning-soft);
    color: var(--strategy-warning);
  }

  .summary--failed .summary__badge {
    background: var(--strategy-danger-soft);
    color: var(--strategy-danger);
  }

  .summary--in_progress .summary__badge,
  .summary--not_found .summary__badge {
    background: var(--strategy-surface-selected);
    color: var(--strategy-text-2);
  }

  .summary__meta--stop {
    color: var(--strategy-warning);
    font-weight: 600;
  }

  .stop-reason {
    margin: 8px 0 0;
    font-size: 12px;
    color: var(--strategy-danger);
    word-break: break-word;
  }

  .steps {
    margin: 12px 0 0;
    padding: 0 0 0 6px;
    list-style: none;
  }

  .step {
    position: relative;
    padding: 0 0 12px 18px;
    border-left: 1px solid var(--strategy-border-soft);
  }

  .step:last-child {
    padding-bottom: 0;
    border-left-color: transparent;
  }

  .step__dot {
    position: absolute;
    top: 3px;
    left: -4px;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--strategy-border-strong);
  }

  .step--passed .step__dot {
    background: var(--strategy-success);
  }

  .step--blocked .step__dot {
    background: var(--strategy-warning);
  }

  .step--failed .step__dot {
    background: var(--strategy-danger);
  }

  .step__row {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
  }

  .step__row strong {
    font-size: 12px;
    font-weight: 600;
    color: var(--strategy-text-1);
  }

  .step__time {
    font-family: var(--strategy-font-data);
    font-size: 11px;
    color: var(--strategy-text-faint);
    white-space: nowrap;
  }

  .step__reason {
    margin: 4px 0 0;
    font-size: 11px;
    line-height: 1.5;
    color: var(--strategy-warning);
    word-break: break-word;
  }

  .step--failed .step__reason {
    color: var(--strategy-danger);
  }

  .step__code {
    margin-left: 6px;
    padding: 1px 6px;
    border-radius: 6px;
    background: var(--strategy-surface-muted);
    color: var(--strategy-text-3);
  }

  .step__id {
    margin: 4px 0 0;
    font-family: var(--strategy-font-data);
    font-size: 11px;
    color: var(--strategy-text-faint);
    word-break: break-all;
  }

  .step__payload {
    margin-top: 4px;
    font-size: 11px;
    color: var(--strategy-text-3);
  }

  .step__payload summary {
    cursor: pointer;
    color: var(--strategy-text-faint);
  }

  .step__payload pre {
    margin: 6px 0 0;
    padding: 8px;
    border-radius: 8px;
    background: var(--strategy-surface-muted);
    font-family: var(--strategy-font-data);
    font-size: 11px;
    line-height: 1.5;
    white-space: pre-wrap;
    word-break: break-all;
  }
</style>
