<template>
  <PageWrapper title="金融AI分析">
    <main class="financial-ai-page" data-testid="financial-ai-restored">
      <section class="workspace-card">
        <header class="section-head">
          <div>
            <h2>研究辅助与情景推演中枢</h2>
            <p>围绕宏观、商品和跨资产主题沉淀研究输入、情景假设、价格表和历史结论。</p>
          </div>
          <Tag :color="reviewStatus === '待复核' ? 'orange' : 'blue'">{{ reviewStatus }}</Tag>
        </header>

        <div class="workspace-grid">
          <article class="panel input-panel">
            <h3>研究问题</h3>
            <label>
              专题
              <select v-model="selectedTopic">
                <option v-for="item in topics" :key="item">{{ item }}</option>
              </select>
            </label>
            <label>
              研究要求
              <textarea
                v-model="researchQuestion"
                placeholder="输入研究问题、时间范围、变量或证据要求"
              ></textarea>
            </label>
            <div class="input-actions">
              <button type="button" :disabled="submitting" @click="submitForReview">
                {{ submitting ? '生成复核单' : '提交复核' }}
              </button>
              <span data-testid="financial-ai-review-state">{{ reviewMessage }}</span>
            </div>
          </article>

          <article class="panel result-panel">
            <h3>分析结果</h3>
            <div class="result-summary" data-testid="financial-ai-result-panel">
              <strong>铜价中期（6-12个月）走势分析</strong>
              <p>
                当前案例以供给扰动、国内库存周期和美元利率三条主线进行情景推演；结论为区间震荡偏强，但需等待需求和库存信号确认。
              </p>
              <dl>
                <div><dt>市场判断</dt><dd>基准情景偏强震荡</dd></div>
                <div><dt>核心区间</dt><dd>9,200 - 10,400 USD/吨</dd></div>
                <div><dt>主要变量</dt><dd>美元、库存、矿端扰动</dd></div>
              </dl>
            </div>
          </article>
        </div>
      </section>

      <section class="case-card">
        <header class="section-head">
          <div>
            <h2>当前价格概览</h2>
            <p>保留旧版价格、机构预测、情景推演和风险变量的组合方式。</p>
          </div>
          <div class="case-tabs">
            <button
              v-for="item in caseTabs"
              :key="item"
              type="button"
              :class="{ active: activeCaseTab === item }"
              @click="activeCaseTab = item"
            >
              {{ item }}
            </button>
          </div>
        </header>

        <div v-if="activeCaseTab === '价格与机构'" class="table-grid">
          <article class="panel">
            <h3>当前价格</h3>
            <table>
              <thead>
                <tr>
                  <th>市场</th>
                  <th>价格</th>
                  <th>涨跌</th>
                  <th>说明</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in priceRows" :key="row.market">
                  <td>{{ row.market }}</td>
                  <td>{{ row.price }}</td>
                  <td :class="row.change.startsWith('+') ? 'positive' : 'negative'">{{
                    row.change
                  }}</td>
                  <td>{{ row.note }}</td>
                </tr>
              </tbody>
            </table>
          </article>

          <article class="panel">
            <h3>主要机构中期预测</h3>
            <table>
              <thead>
                <tr>
                  <th>机构</th>
                  <th>区间</th>
                  <th>观点</th>
                  <th>关键变量</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in forecastRows" :key="row.name">
                  <td>{{ row.name }}</td>
                  <td>{{ row.range }}</td>
                  <td>{{ row.view }}</td>
                  <td>{{ row.driver }}</td>
                </tr>
              </tbody>
            </table>
          </article>
        </div>

        <div v-else-if="activeCaseTab === '情景推演'" class="scenario-grid">
          <article v-for="item in scenarios" :key="item.name" class="scenario-card">
            <header>
              <span>{{ item.probability }}</span>
              <strong>{{ item.name }}</strong>
            </header>
            <p>{{ item.description }}</p>
            <dl>
              <div
                ><dt>价格区间</dt><dd>{{ item.range }}</dd></div
              >
              <div
                ><dt>触发条件</dt><dd>{{ item.trigger }}</dd></div
              >
            </dl>
          </article>
        </div>

        <div v-else class="risk-grid">
          <article v-for="item in riskVariables" :key="item.name" class="risk-card">
            <span>{{ item.type }}</span>
            <strong>{{ item.name }}</strong>
            <p>{{ item.impact }}</p>
          </article>
        </div>
      </section>

      <section class="history-card">
        <header class="section-head">
          <div>
            <h2>历史记录</h2>
            <p>保留研究主题、结果状态和复核流转，未接入后端动作不展示完成结果。</p>
          </div>
        </header>
        <div class="history-list">
          <button
            v-for="item in historyItems"
            :key="item.id"
            type="button"
            :class="{ active: activeHistory === item.id }"
            @click="activeHistory = item.id"
          >
            <span>{{ item.time }}</span>
            <strong>{{ item.title }}</strong>
            <em>{{ item.status }}</em>
          </button>
        </div>
      </section>
    </main>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { Tag } from 'ant-design-vue';
  import { computed, ref } from 'vue';
  import { PageWrapper } from '@/components/Page';

  const topics = [
    '铜价中期（6-12个月）走势分析',
    '黄金实际利率压力测试',
    'BTC 流动性与风险偏好跟踪',
  ];
  const selectedTopic = ref(topics[0]);
  const researchQuestion = ref('跟踪矿端扰动、国内库存和美元利率对铜价中期走势的影响。');
  const submitting = ref(false);
  const reviewStatus = ref('归档案例');
  const reviewMessage = ref('当前展示归档研究案例；新请求会进入待复核。');
  const caseTabs = ['价格与机构', '情景推演', '风险变量'];
  const activeCaseTab = ref(caseTabs[0]);
  const activeHistory = ref('H-01');

  const priceRows = [
    { market: 'LME 铜', price: '9,842 USD/吨', change: '+1.8%', note: '库存继续低位震荡' },
    { market: '沪铜主力', price: '80,420 CNY/吨', change: '+1.2%', note: '国内现货升水小幅扩大' },
    { market: 'COMEX 铜', price: '4.52 USD/lb', change: '-0.3%', note: '美元反弹压制短线估值' },
  ];

  const forecastRows = [
    { name: '高盛', range: '9,500-10,800', view: '供给扰动支撑价格中枢', driver: '矿端供给' },
    { name: '花旗', range: '8,900-10,200', view: '需求确认前维持区间判断', driver: '中国需求' },
    { name: '摩根士丹利', range: '9,200-10,400', view: '库存周期决定上行斜率', driver: '库存变化' },
  ];

  const scenarios = [
    {
      name: '强势情景',
      probability: '25%',
      range: '10,400-11,200 USD/吨',
      trigger: '国内补库与矿端扰动共振',
      description: '低库存环境下需求超预期回升，现货升水和远期曲线同步走强。',
    },
    {
      name: '基准情景',
      probability: '50%',
      range: '9,200-10,400 USD/吨',
      trigger: '供给扰动延续但需求温和',
      description: '价格中枢抬升但缺少连续突破动能，适合跟踪库存和升贴水确认。',
    },
    {
      name: '弱势情景',
      probability: '25%',
      range: '8,300-9,200 USD/吨',
      trigger: '美元走强与需求恢复不及预期',
      description: '金融属性压制估值，库存回补导致价格回到成本支撑附近。',
    },
  ];

  const riskVariables = [
    {
      type: '宏观',
      name: '美元与实际利率',
      impact: '若实际利率重新上行，铜价估值扩张会受到压制。',
    },
    { type: '供给', name: '矿端扰动', impact: '矿山检修、品位下降和运输约束会放大低库存弹性。' },
    { type: '需求', name: '国内补库', impact: '电网、地产链和新能源需求决定上行持续性。' },
    { type: '库存', name: '交易所库存', impact: '低库存支撑近月升水，但库存回升会削弱风险溢价。' },
  ];

  const historyItems = [
    { id: 'H-01', time: '2026-07-11', title: '铜价中期走势分析', status: '归档' },
    { id: 'H-02', time: '2026-07-09', title: '黄金实际利率压力测试', status: '归档' },
    { id: 'H-03', time: '2026-07-08', title: 'BTC 风险偏好跟踪', status: '待复核' },
  ];

  const selectedHistory = computed(() =>
    historyItems.find((item) => item.id === activeHistory.value),
  );

  function submitForReview() {
    submitting.value = true;
    window.setTimeout(() => {
      submitting.value = false;
      reviewStatus.value = '待复核';
      reviewMessage.value = `${selectedTopic.value} 已生成待复核请求，尚未形成正式分析结果。`;
      activeHistory.value = selectedHistory.value?.id || 'H-01';
    }, 300);
  }
</script>

<style scoped lang="less">
  .financial-ai-page {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 12px 4px 18px;
  }

  .workspace-card,
  .case-card,
  .history-card,
  .panel,
  .scenario-card,
  .risk-card {
    border: 1px solid #dbe4ed;
    border-radius: 8px;
    background: #fff;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
  }

  .workspace-card,
  .case-card,
  .history-card {
    padding: 18px;
  }

  .section-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
  }

  h2,
  h3 {
    margin: 0;
    color: #17212f;
    font-weight: 800;
  }

  h2 {
    font-size: 22px;
  }

  h3 {
    margin-bottom: 12px;
    font-size: 18px;
  }

  p {
    color: #5b6572;
    line-height: 1.7;
  }

  .section-head p {
    margin: 6px 0 0;
  }

  .workspace-grid,
  .table-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 14px;
  }

  .panel {
    padding: 16px;
  }

  .input-panel {
    display: grid;
    gap: 12px;
  }

  label {
    display: grid;
    gap: 6px;
    color: #59636e;
    font-weight: 700;
  }

  select,
  textarea {
    width: 100%;
    border: 1px solid #d8e1ea;
    border-radius: 6px;
    background: #f8fafc;
    color: #17212f;
    font-size: 14px;
  }

  select {
    height: 36px;
    padding: 0 10px;
  }

  textarea {
    min-height: 142px;
    padding: 10px;
    resize: vertical;
  }

  .input-actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
  }

  button {
    min-height: 34px;
    border: 1px solid #d8e1ea;
    border-radius: 6px;
    background: #f8fafc;
    color: #344054;
    font-weight: 700;
  }

  .input-actions button {
    padding: 0 18px;
    border-color: #2f6fed;
    background: #eef5ff;
    color: #1f5cc4;
  }

  .input-actions button:disabled {
    opacity: 0.6;
  }

  .input-actions span {
    color: #7a5a00;
    font-size: 12px;
    font-weight: 700;
  }

  .result-summary {
    display: grid;
    gap: 12px;
    padding: 14px;
    border-radius: 8px;
    background: #f8fafc;
  }

  .result-summary strong {
    color: #17212f;
    font-size: 18px;
  }

  dl {
    display: grid;
    gap: 8px;
    margin: 0;
  }

  dl div {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e8edf2;
  }

  dt {
    color: #667085;
  }

  dd {
    margin: 0;
    color: #17212f;
    font-weight: 800;
  }

  .case-tabs {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .case-tabs button {
    padding: 0 12px;
  }

  .case-tabs button.active,
  .history-list button.active {
    border-color: #2f6fed;
    background: #eef5ff;
    color: #1f5cc4;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    padding: 10px 8px;
    border-bottom: 1px solid #e8edf2;
    text-align: left;
  }

  th {
    color: #667085;
    background: #f8fafc;
    font-weight: 800;
  }

  td {
    color: #344054;
    font-weight: 700;
  }

  .positive {
    color: #14804a;
  }

  .negative {
    color: #b42318;
  }

  .scenario-grid,
  .risk-grid,
  .history-list {
    display: grid;
    gap: 12px;
  }

  .scenario-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .risk-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .scenario-card,
  .risk-card {
    padding: 14px;
  }

  .scenario-card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .scenario-card header span,
  .risk-card span {
    color: #1f5cc4;
    font-weight: 800;
  }

  .scenario-card header strong,
  .risk-card strong {
    color: #17212f;
    font-size: 17px;
  }

  .history-list {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .history-list button {
    display: grid;
    gap: 6px;
    padding: 12px;
    text-align: left;
  }

  .history-list span,
  .history-list em {
    color: #667085;
    font-style: normal;
    font-size: 12px;
  }

  @media (max-width: 1100px) {
    .workspace-grid,
    .table-grid,
    .scenario-grid,
    .risk-grid,
    .history-list {
      grid-template-columns: 1fr;
    }
  }
</style>
