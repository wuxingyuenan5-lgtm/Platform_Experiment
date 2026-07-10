<template>
  <article class="execution-card">
    <header class="panel-head">
      <div>
        <h3>{{ title }}</h3>
        <p>聚合策略指令、执行反馈与风控影响，避免下单后再切多个页面查看。</p>
      </div>

      <button type="button" class="ghost-btn" @click="refreshStatus">刷新</button>
    </header>

    <div class="status-tabs">
      <button
        v-for="item in status"
        :key="item"
        type="button"
        :class="{ 'is-active': item === currentStatus }"
        @click="currentStatus = item"
      >
        {{ item }}
      </button>
    </div>

    <div class="execution-shell">
      <section class="execution-left">
        <article class="shell-card shell-card--command">
          <div class="shell-card__head">
            <div>
              <h4>策略指令</h4>
              <span>{{ currentStatus }}阶段的前端执行预案</span>
            </div>
            <span class="tag-pill">{{ currentStatus }}</span>
          </div>

          <div class="command-board">
            <div class="command-title">{{ currentInstruction.title }}</div>
            <p>{{ currentInstruction.description }}</p>

            <div class="command-points">
              <div v-for="point in currentInstruction.points" :key="point" class="command-point">
                {{ point }}
              </div>
            </div>
          </div>
        </article>

        <article class="shell-card shell-card--logs">
          <div class="shell-card__head">
            <div>
              <h4>执行反馈</h4>
              <span>只保留对交易员有价值的回报信息</span>
            </div>
            <span class="tag-pill tag-pill--muted">{{ filteredLogs.length }} 条</span>
          </div>

          <div class="log-list">
            <div v-for="item in filteredLogs" :key="`${item.time}-${item.text}`" class="log-item">
              <span class="log-time">{{ item.time }}</span>
              <p :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.text }}</p>
            </div>
          </div>
        </article>
      </section>

      <section class="execution-right">
        <article class="shell-card shell-card--overview">
          <div class="shell-card__head">
            <div>
              <h4>{{ currentStatus }}执行视图</h4>
              <span>{{ currentDescription }}</span>
            </div>
            <div class="overview-tags">
              <span>账户</span>
              <span>风控</span>
              <span>影响</span>
            </div>
          </div>

          <div class="impact-grid">
            <div v-for="item in visibleMetrics" :key="item.label" class="impact-card">
              <label>{{ item.label }}</label>
              <div class="impact-values">
                <strong>{{ item.before }}</strong>
                <span>→</span>
                <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.after }}</strong>
              </div>
              <p>{{ item.alert || '执行后指标保持在预设风控区间。' }}</p>
            </div>
          </div>
        </article>

        <article class="shell-card shell-card--actions">
          <div class="shell-card__head">
            <div>
              <h4>执行动作</h4>
              <span>按钮不是摆设，点击后会切换对应说明与反馈。</span>
            </div>
          </div>

          <div class="action-row">
            <button
              v-for="item in actionButtons"
              :key="item.key"
              type="button"
              :class="['action-btn', { 'is-primary': activeAction === item.key }]"
              @click="handleAction(item.key)"
            >
              {{ item.label }}
            </button>
          </div>

          <div class="action-feedback">
            <strong>{{ activeActionLabel }}</strong>
            <p>{{ actionFeedback }}</p>
          </div>
        </article>
      </section>
    </div>
  </article>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import type { StrategyExecutionMetric, StrategyLogItem } from '../types';

  const props = defineProps<{
    title: string;
    status: string[];
    metrics: StrategyExecutionMetric[];
    logs: StrategyLogItem[];
  }>();

  const currentStatus = ref(props.status[0] || '开仓');
  const activeAction = ref<'execute' | 'reduce' | 'protect'>('execute');

  const instructionMap: Record<
    string,
    {
      title: string;
      description: string;
      points: string[];
    }
  > = {
    开仓: {
      title: '等待最优成交与仓位确认',
      description: '优先确认执行窗口、成交深度与风控约束，再判断是否真正进入策略敞口。',
      points: ['检查目标仓位与可用保证金', '确认主腿与对冲腿成交顺序', '若滑点超阈值则暂停执行'],
    },
    移仓: {
      title: '主力切换与旧仓回收',
      description: '移仓阶段更关注换月损耗与过渡期间的净敞口，而不是单笔盈亏。',
      points: ['先确认新主力流动性', '控制旧腿平仓与新腿建仓的时间差', '记录移仓成本并回写策略归因'],
    },
    平仓: {
      title: '回收占用并锁定收益',
      description: '平仓阶段主要任务是回收资金占用、清理尾仓与确认策略闭环。',
      points: ['按收益优先级依次平仓', '检查尾仓是否清零', '同步更新已实现收益与复盘标签'],
    },
    止盈: {
      title: '收益兑现优先',
      description: '止盈动作强调在不破坏对冲结构的前提下，尽可能平滑兑现收益。',
      points: ['优先保护盈利腿', '检查剩余仓位是否仍满足约束', '必要时切换为分批成交'],
    },
    加仓: {
      title: '放大有效信号',
      description: '只在原有逻辑未失效、且资金与集中度仍然安全时考虑加仓。',
      points: ['检查新增仓位后集中度', '避免单腿放大过快', '加仓后重新评估最大回撤阈值'],
    },
    减仓: {
      title: '先降风险再看机会',
      description: '减仓通常用于削减集中度、回收保证金或应对异常波动。',
      points: ['优先减高波动腿', '记录风险释放幅度', '保留必要的最小跟踪仓位'],
    },
  };

  const descriptionMap: Record<string, string> = {
    开仓: '核心看成交、占用与风险敞口是否按预案落地。',
    移仓: '核心看换月效率、过渡敞口与回写质量。',
    平仓: '核心看收益兑现与仓位清零效率。',
    止盈: '核心看保护单执行与收益回收。',
    加仓: '核心看信号有效性与新增风险。',
    减仓: '核心看风险释放与仓位收缩效率。',
  };

  const actionButtons = [
    { key: 'execute', label: '执行预案' },
    { key: 'reduce', label: '降风险' },
    { key: 'protect', label: '保护单' },
  ] as const;

  const actionFeedbackMap: Record<(typeof actionButtons)[number]['key'], string> = {
    execute: '已切换到执行预案视图，重点检查成交顺序、保证金占用和目标名义规模。',
    reduce: '已切换到风险收缩视图，建议优先释放高波动、高滑点或高集中度腿。',
    protect: '已切换到保护单视图，建议同步检查止盈、止损与撤单回补逻辑。',
  };

  const currentInstruction = computed(() => {
    return instructionMap[currentStatus.value] || instructionMap.开仓;
  });

  const currentDescription = computed(() => {
    return descriptionMap[currentStatus.value] || descriptionMap.开仓;
  });

  const filteredLogs = computed(() => {
    if (currentStatus.value === props.status[0]) return props.logs;
    return props.logs.slice(0, Math.max(props.logs.length - 1, 1));
  });

  const visibleMetrics = computed(() => {
    if (currentStatus.value === props.status[0]) return props.metrics;
    return [...props.metrics].reverse();
  });

  const activeActionLabel = computed(() => {
    return actionButtons.find((item) => item.key === activeAction.value)?.label || '执行预案';
  });

  const actionFeedback = computed(() => actionFeedbackMap[activeAction.value]);

  function refreshStatus() {
    currentStatus.value = props.status[0] || currentStatus.value;
    activeAction.value = 'execute';
  }

  function handleAction(action: (typeof actionButtons)[number]['key']) {
    activeAction.value = action;
  }
</script>

<style scoped lang="less">
  .execution-card {
    padding: 22px;
    border-radius: 24px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.97), rgba(255, 251, 245, 0.94));
    box-shadow: 0 18px 40px rgba(28, 35, 40, 0.05);
    border: 1px solid rgba(201, 164, 95, 0.14);
  }

  .panel-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 16px;

    h3 {
      margin: 0;
      color: #15252a;
      font-size: 18px;
    }

    p {
      margin: 6px 0 0;
      color: #8a94a1;
      font-size: 12px;
      line-height: 1.7;
    }
  }

  .ghost-btn {
    height: 32px;
    padding: 0 14px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #fff;
    color: #667085;
    cursor: pointer;
  }

  .status-tabs {
    display: inline-flex;
    padding: 4px;
    border: 1px solid #ecd8d2;
    border-radius: 10px;
    background: #fff;
    margin-bottom: 16px;

    button {
      min-width: 74px;
      height: 34px;
      border: none;
      border-radius: 8px;
      background: transparent;
      color: #6b7280;
      font-weight: 700;
      cursor: pointer;
    }

    .is-active {
      color: #c95b63;
      background: #fff6f6;
    }
  }

  .execution-shell {
    display: grid;
    grid-template-columns: 0.88fr 1.12fr;
    gap: 16px;
  }

  .execution-left,
  .execution-right {
    display: grid;
    gap: 14px;
  }

  .shell-card {
    padding: 18px;
    border-radius: 18px;
    background: rgba(255, 255, 255, 0.86);
    box-shadow: inset 0 0 0 1px rgba(201, 164, 95, 0.08);
  }

  .shell-card__head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;

    h4 {
      margin: 0;
      color: #21313d;
      font-size: 15px;
    }

    span {
      color: #8a94a1;
      font-size: 12px;
    }
  }

  .tag-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 58px;
    height: 28px;
    padding: 0 12px;
    border-radius: 999px;
    background: rgba(23, 111, 176, 0.1);
    color: #176fb0;
    font-size: 12px;
    font-weight: 700;
  }

  .tag-pill--muted {
    background: #f4efe7;
    color: #8d6f3b;
  }

  .command-board {
    display: grid;
    gap: 12px;
  }

  .command-title {
    color: #172b3a;
    font-size: 18px;
    font-weight: 700;
  }

  .command-board p {
    margin: 0;
    color: #617182;
    font-size: 13px;
    line-height: 1.8;
  }

  .command-points {
    display: grid;
    gap: 10px;
  }

  .command-point {
    padding: 10px 12px;
    border-radius: 12px;
    background: #faf6ef;
    color: #5d5144;
    font-size: 12px;
    line-height: 1.7;
  }

  .execution-card,
  .shell-card {
    border-color: var(--strategy-border);
    background: linear-gradient(180deg, var(--strategy-surface) 0%, var(--strategy-surface-soft) 100%);
    box-shadow: var(--strategy-shadow);
  }

  .panel-head h3,
  .shell-card__head h4,
  .command-title {
    color: var(--strategy-text-1);
    font-weight: 900;
  }

  .panel-head p,
  .shell-card__head span,
  .command-board p,
  .log-time {
    color: var(--strategy-text-3);
  }

  .ghost-btn,
  .status-tabs,
  .status-tabs button {
    border-color: var(--strategy-border-strong);
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
  }

  .status-tabs .is-active,
  .tag-pill,
  .tag-pill--muted {
    background: var(--strategy-accent-soft);
    color: var(--strategy-accent-strong);
  }

  .command-point {
    background: var(--strategy-surface-muted);
    color: var(--strategy-text-2);
    font-size: 13px;
    font-weight: 700;
  }

  .log-list {
    display: grid;
    gap: 10px;
    max-height: 240px;
    overflow: auto;
  }

  .log-item {
    padding-bottom: 10px;
    border-bottom: 1px solid #eef2f7;
  }

  .log-time {
    color: #9aa3af;
    font-size: 11px;
  }

  .log-item p {
    margin: 4px 0 0;
    font-size: 13px;
    line-height: 1.7;
  }

  .overview-tags {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;

    span {
      padding: 6px 10px;
      border-radius: 999px;
      background: #f8f2e4;
      color: #87651e;
      font-size: 12px;
      font-weight: 700;
    }
  }

  .impact-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
  }

  .impact-card {
    padding: 14px 16px;
    border-radius: 16px;
    background: #fff;
    box-shadow: inset 0 0 0 1px rgba(201, 164, 95, 0.08);

    label,
    p {
      display: block;
    }

    label {
      color: #8a94a1;
      font-size: 12px;
    }

    p {
      margin: 0;
      color: #7c8693;
      font-size: 12px;
      line-height: 1.7;
    }
  }

  .impact-values {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 10px 0 8px;

    strong {
      font-size: 22px;
      color: #21313d;
    }

    span {
      color: #9aa3af;
      font-size: 16px;
      font-weight: 700;
    }
  }

  .action-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .action-btn {
    height: 40px;
    border: 1px solid rgba(134, 115, 87, 0.12);
    border-radius: 10px;
    background: #f8fafc;
    color: #475569;
    font-weight: 700;
    cursor: pointer;
  }

  .action-btn.is-primary {
    border-color: #c92d31;
    background: #c92d31;
    color: #fff;
  }

  .action-feedback {
    margin-top: 14px;
    padding: 14px 16px;
    border-radius: 14px;
    background: #fbfbfa;

    strong {
      display: block;
      color: #21313d;
      font-size: 14px;
    }

    p {
      margin: 8px 0 0;
      color: #667085;
      font-size: 12px;
      line-height: 1.7;
    }
  }

  .is-positive {
    color: #1d9f6e !important;
  }

  .is-negative {
    color: #d8585f !important;
  }

  .is-neutral {
    color: #1f2e3d !important;
  }

  @media (max-width: 1200px) {
    .execution-shell,
    .impact-grid,
    .action-row {
      grid-template-columns: 1fr;
    }
  }
</style>
