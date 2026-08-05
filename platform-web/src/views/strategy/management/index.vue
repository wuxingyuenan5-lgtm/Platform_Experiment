<template>
  <RestoredProductSurface
    state="sample"
    source="sample:strategy-catalog"
    as-of="2026-08-05 · 非实时"
    :actionable="false"
    message="策略目录 Owner 尚未配置；策略结构和运行视图已恢复，示例策略不可启停、编辑或下单。"
  >
    <main class="strategy-page">
      <header class="page-head">
        <div>
          <span>STRATEGY OPERATIONS</span>
          <h1>策略管理</h1>
          <p>统一观察策略状态、资本占用、风险与订单链路。</p>
        </div>
        <div v-if="canWrite" class="actions">
          <button disabled>新建策略</button>
          <button disabled>部署策略（Live Write关闭）</button>
        </div>
        <strong v-else class="readonly">只读权限</strong>
      </header>

      <nav class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab"
          :class="{ active: activeTab === tab }"
          @click="activeTab = tab"
        >
          {{ tab }}
        </button>
      </nav>

      <section class="summary-grid">
        <article v-for="item in summaries" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.note }}</small>
        </article>
      </section>

      <section class="workspace">
        <article class="panel panel--table">
          <div class="panel-head">
            <h2>策略目录</h2>
            <span>{{ strategies.length }} 个样例策略</span>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>策略</th>
                  <th>类型</th>
                  <th>状态</th>
                  <th>资金占用</th>
                  <th>近30日</th>
                  <th>风险</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in strategies" :key="item.name">
                  <td>
                    <strong>{{ item.name }}</strong>
                    <small>{{ item.id }}</small>
                  </td>
                  <td>{{ item.type }}</td>
                  <td><span class="status">{{ item.status }}</span></td>
                  <td>{{ item.capital }}</td>
                  <td :class="item.pnl.startsWith('+') ? 'positive' : ''">
                    {{ item.pnl }}
                  </td>
                  <td>{{ item.risk }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </article>

        <aside class="panel">
          <div class="panel-head">
            <h2>运行边界</h2>
            <span>Read only</span>
          </div>
          <dl>
            <div>
              <dt>Platform Live Write</dt>
              <dd>关闭</dd>
            </div>
            <div>
              <dt>Runtime Live Write</dt>
              <dd>关闭</dd>
            </div>
            <div>
              <dt>策略变更</dt>
              <dd>需权限与审批</dd>
            </div>
            <div>
              <dt>风险复核</dt>
              <dd>独立门禁</dd>
            </div>
          </dl>
          <div class="notice">
            CEO 的显式业务权限不会绕过双人审批、Kill Switch、Allowlist 或 Live Write 门禁。
          </div>
        </aside>
      </section>
    </main>
  </RestoredProductSurface>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import { hasPermission } from '@/access/userAccess';
  import { useUserStore } from '@/store/modules/user';

  const userStore = useUserStore();
  const canWrite = computed(() =>
    hasPermission(userStore.getAuthentication?.permissions || [], 'strategy.write'),
  );
  const tabs = ['策略损益', '账户资金', '订单信息'];
  const activeTab = ref(tabs[0]);
  const summaries = [
    { label: '运行策略', value: '4', note: '示例状态' },
    { label: '资本占用', value: '38%', note: '组合口径' },
    { label: '近30日收益', value: '+2.84%', note: '非真实业绩' },
    { label: '风险事件', value: '0', note: '样例快照' },
  ];
  const strategies = [
    {
      id: 'STR-FUND-01',
      name: '资金费率套利',
      type: '市场中性',
      status: '观察',
      capital: '28%',
      pnl: '+1.42%',
      risk: '低',
    },
    {
      id: 'STR-XVENUE-02',
      name: '跨所黄金价差',
      type: '价差',
      status: '观察',
      capital: '34%',
      pnl: '+0.86%',
      risk: '中',
    },
    {
      id: 'STR-TREND-03',
      name: '股指趋势跟踪',
      type: '趋势',
      status: '研究',
      capital: '22%',
      pnl: '+0.44%',
      risk: '中',
    },
    {
      id: 'STR-HEDGE-04',
      name: '防守风格轮动',
      type: '轮动',
      status: '研究',
      capital: '16%',
      pnl: '+0.12%',
      risk: '低',
    },
  ];
</script>

<style scoped>
  .strategy-page {
    display: grid;
    gap: 14px;
    color: #172033;
  }

  .page-head {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 20px;
    padding: 22px;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    background: #fff;
  }

  .page-head span {
    color: #607099;
    font-size: 11px;
    letter-spacing: 0.16em;
  }

  .page-head h1 {
    margin: 4px 0;
    font-size: 28px;
  }

  .page-head p {
    margin: 0;
    color: #6d778a;
  }

  .actions {
    display: flex;
    gap: 8px;
  }

  .actions button {
    padding: 9px 13px;
    border: 0;
    border-radius: 8px;
    background: #dfe7f3;
    color: #68758c;
  }

  .readonly {
    padding: 7px 10px;
    border-radius: 999px;
    background: #edf1f6;
    color: #667085;
    font-size: 12px;
  }

  .tabs {
    display: flex;
    width: fit-content;
    gap: 6px;
    padding: 5px;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    background: #fff;
  }

  .tabs button {
    padding: 8px 14px;
    border: 0;
    border-radius: 8px;
    background: transparent;
    color: #667085;
    cursor: pointer;
  }

  .tabs button.active {
    background: #182b4d;
    color: #fff;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
  }

  .summary-grid article,
  .panel {
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    background: #fff;
  }

  .summary-grid article {
    display: grid;
    gap: 5px;
    padding: 16px;
  }

  .summary-grid span,
  .summary-grid small {
    color: #6d778a;
  }

  .summary-grid strong {
    font-size: 24px;
  }

  .workspace {
    display: grid;
    grid-template-columns: minmax(0, 2fr) minmax(250px, 0.7fr);
    gap: 12px;
  }

  .panel {
    padding: 17px;
  }

  .panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
  }

  .panel-head h2 {
    margin: 0;
    font-size: 17px;
  }

  .panel-head span {
    color: #7a8596;
    font-size: 12px;
  }

  .table-wrap {
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 12px 10px;
    border-bottom: 1px solid #edf0f4;
    text-align: left;
    white-space: nowrap;
  }

  th {
    color: #7a8596;
    font-size: 12px;
  }

  td small {
    display: block;
    margin-top: 3px;
    color: #8d96a5;
  }

  .status {
    padding: 4px 8px;
    border-radius: 999px;
    background: #eef4ff;
    color: #3a64a5;
  }

  .positive {
    color: #087a55;
    font-weight: 700;
  }

  dl {
    display: grid;
    gap: 12px;
    margin: 0;
  }

  dl div {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid #edf0f4;
  }

  dt {
    color: #6d778a;
  }

  dd {
    margin: 0;
    font-weight: 700;
  }

  .notice {
    margin-top: 16px;
    padding: 12px;
    border-radius: 10px;
    background: #fff8e6;
    color: #7b5b13;
    font-size: 12px;
    line-height: 1.6;
  }

  @media (max-width: 960px) {
    .summary-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .workspace {
      grid-template-columns: 1fr;
    }

    .page-head {
      flex-direction: column;
      align-items: start;
    }
  }

  @media (max-width: 560px) {
    .summary-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
