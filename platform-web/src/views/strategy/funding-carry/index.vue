<template>
  <RestoredProductSurface
    state="sample"
    source="sample:funding-carry-research"
    as-of="2026-08-05 · 非实时"
    :actionable="false"
    message="真实资金费率 Provider 尚未配置；行情、机会与订单结构均为不可执行的样例展示。"
  >
    <main class="funding-page">
      <header class="desk-head">
        <div>
          <span>FUNDING CARRY</span>
          <h2>资金费率套利</h2>
          <p>{{ selectedExchange }} · {{ selectedSymbol }} · {{ selectedResolution }}</p>
        </div>
        <div v-if="canWrite" class="write-actions">
          <button disabled>创建组合</button>
          <button disabled>执行（Live Write关闭）</button>
        </div>
        <b v-else>只读权限</b>
      </header>

      <section class="summary-grid">
        <article v-for="item in summary" :key="item.label">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.note }}</small>
        </article>
      </section>

      <template v-if="activeSection === 'analysis'">
        <section class="analysis-grid">
          <article class="panel panel--wide">
            <div class="panel-head">
              <h3>交易所资金费率比较</h3>
              <span>Sample</span>
            </div>
            <div class="bars">
              <div v-for="item in exchanges" :key="item.name">
                <span>{{ item.name }}</span>
                <div><i :style="{ width: item.width }"></i></div>
                <strong>{{ item.rate }}</strong>
              </div>
            </div>
          </article>
          <article class="panel">
            <div class="panel-head">
              <h3>候选组合</h3>
              <span>不可执行</span>
            </div>
            <ul>
              <li v-for="item in opportunities" :key="item.pair">
                <div>
                  <strong>{{ item.pair }}</strong>
                  <small>{{ item.route }}</small>
                </div>
                <b>{{ item.apr }}</b>
              </li>
            </ul>
          </article>
        </section>
      </template>

      <template v-else>
        <section class="execution-grid">
          <article class="panel order-panel">
            <div class="panel-head">
              <h3>组合订单</h3>
              <span>Live Write关闭</span>
            </div>
            <label>
              名义金额
              <input value="10,000 USDT" disabled />
            </label>
            <label>
              开仓方式
              <select disabled>
                <option>双腿同步限价</option>
              </select>
            </label>
            <label>
              最大滑点
              <input value="0.05%" disabled />
            </label>
            <button v-if="canWrite" disabled>提交组合订单</button>
            <div v-else class="readonly-box">员工与会员仅可查看研究和状态。</div>
          </article>
          <article class="panel panel--wide">
            <div class="panel-head">
              <h3>执行预览</h3>
              <span>ACK ≠ Fill</span>
            </div>
            <table>
              <thead>
                <tr>
                  <th>腿</th>
                  <th>场所</th>
                  <th>方向</th>
                  <th>数量</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>现货</td>
                  <td>Bybit</td>
                  <td>买入</td>
                  <td>0.16 BTC</td>
                  <td>未提交</td>
                </tr>
                <tr>
                  <td>永续</td>
                  <td>OKX</td>
                  <td>卖出</td>
                  <td>0.16 BTC</td>
                  <td>未提交</td>
                </tr>
              </tbody>
            </table>
          </article>
        </section>
      </template>
    </main>
  </RestoredProductSurface>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import { hasPermission } from '@/access/userAccess';
  import { useUserStore } from '@/store/modules/user';

  withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedExchange?: string;
      selectedSymbol?: string;
      selectedResolution?: string;
    }>(),
    {
      activeSection: 'analysis',
      selectedExchange: 'Bybit',
      selectedSymbol: 'BTC',
      selectedResolution: '30分钟',
    },
  );

  const userStore = useUserStore();
  const canWrite = computed(() =>
    hasPermission(userStore.getAuthentication?.permissions || [], 'trading.write'),
  );
  const summary = [
    { label: '当前费率差', value: '0.021%', note: '8小时口径' },
    { label: '样例年化', value: '18.4%', note: '未扣成本' },
    { label: '基差', value: '-0.14%', note: '现货/永续' },
    { label: '风险等级', value: '中', note: '非实时评估' },
  ];
  const exchanges = [
    { name: 'Bybit', rate: '+0.0100%', width: '48%' },
    { name: 'Binance', rate: '+0.0068%', width: '34%' },
    { name: 'OKX', rate: '-0.0112%', width: '58%' },
  ];
  const opportunities = [
    { pair: 'BTC/USDT', route: 'Bybit Spot → OKX Perp', apr: '18.4%' },
    { pair: 'ETH/USDT', route: 'Binance Spot → Bybit Perp', apr: '12.7%' },
    { pair: 'SOL/USDT', route: 'OKX Spot → Binance Perp', apr: '9.8%' },
  ];
</script>

<style scoped>
  .funding-page {
    display: grid;
    gap: 12px;
    color: #172033;
  }

  .desk-head {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 16px;
    padding: 18px;
    border: 1px solid #e1e7ef;
    border-radius: 14px;
    background: #fff;
  }

  .desk-head span {
    color: #63739b;
    font-size: 11px;
    letter-spacing: 0.16em;
  }

  .desk-head h2 {
    margin: 4px 0;
    font-size: 24px;
  }

  .desk-head p {
    margin: 0;
    color: #6c778a;
  }

  .desk-head b {
    padding: 6px 10px;
    border-radius: 999px;
    background: #eef1f5;
    color: #687386;
    font-size: 12px;
  }

  .write-actions {
    display: flex;
    gap: 8px;
  }

  .write-actions button,
  .order-panel button {
    padding: 9px 12px;
    border: 0;
    border-radius: 8px;
    background: #dfe7f2;
    color: #657188;
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
  }

  .summary-grid article,
  .panel {
    border: 1px solid #e1e7ef;
    border-radius: 13px;
    background: #fff;
  }

  .summary-grid article {
    display: grid;
    gap: 5px;
    padding: 15px;
  }

  .summary-grid span,
  .summary-grid small {
    color: #6d788b;
  }

  .summary-grid strong {
    font-size: 22px;
  }

  .analysis-grid,
  .execution-grid {
    display: grid;
    grid-template-columns: 1.5fr 1fr;
    gap: 10px;
  }

  .execution-grid {
    grid-template-columns: 0.8fr 1.4fr;
  }

  .panel {
    padding: 16px;
  }

  .panel-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
  }

  .panel-head h3 {
    margin: 0;
    font-size: 16px;
  }

  .panel-head span {
    padding: 4px 8px;
    border-radius: 999px;
    background: #fff6dc;
    color: #8a6414;
    font-size: 11px;
  }

  .bars {
    display: grid;
    gap: 16px;
  }

  .bars > div {
    display: grid;
    grid-template-columns: 70px 1fr 80px;
    align-items: center;
    gap: 10px;
  }

  .bars > div > div {
    height: 8px;
    overflow: hidden;
    border-radius: 999px;
    background: #edf1f5;
  }

  .bars i {
    display: block;
    height: 100%;
    background: linear-gradient(90deg, #557ed0, #34a57b);
  }

  ul {
    display: grid;
    gap: 12px;
    padding: 0;
    margin: 0;
    list-style: none;
  }

  li {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid #edf1f5;
  }

  li div {
    display: grid;
    gap: 3px;
  }

  li small {
    color: #7a8595;
  }

  li b {
    color: #087a55;
  }

  .order-panel {
    display: grid;
    gap: 12px;
  }

  .order-panel label {
    display: grid;
    gap: 6px;
    color: #667085;
  }

  .order-panel input,
  .order-panel select {
    height: 38px;
    padding: 0 10px;
    border: 1px solid #dde3eb;
    border-radius: 8px;
    background: #f7f9fb;
  }

  .readonly-box {
    padding: 12px;
    border-radius: 9px;
    background: #f1f4f8;
    color: #667085;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 12px;
    border-bottom: 1px solid #edf1f5;
    text-align: left;
  }

  th {
    color: #758094;
    font-size: 12px;
  }

  @media (max-width: 900px) {
    .summary-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .analysis-grid,
    .execution-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 540px) {
    .summary-grid {
      grid-template-columns: 1fr;
    }

    .desk-head {
      flex-direction: column;
      align-items: start;
    }
  }
</style>
