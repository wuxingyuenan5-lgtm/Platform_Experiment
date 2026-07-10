<template>
  <PageWrapper title="金融AI分析">
    <div class="financial-ai-page">
      <section class="hero-card">
        <div class="hero-copy">
          <div class="eyebrow">FINANCIAL AI</div>
          <h1>研究辅助与情景推演中枢</h1>
          <p>
            这一页先不接真实推理链路，先把未来的展示壳、分析案例与结果容器定下来。
            第一版重点是给程序员一个清晰的前端形态：上方展示案例，下方保留“待开发”入口。
          </p>
        </div>

        <div class="hero-status">
          <span>当前状态</span>
          <strong>待开发</strong>
          <p>后续可承接机构观点归纳、宏观解读、商品/加密专题推演、会议纪要摘要与策略 Memo 生成。</p>
        </div>
      </section>

      <section class="case-card">
        <header class="section-head">
          <div>
            <div class="eyebrow">SHOWCASE</div>
            <h2>展示案例：铜价中期（6-12个月）走势分析</h2>
          </div>
        </header>

        <div class="case-grid">
          <article class="panel">
            <h3>当前价格概览</h3>
            <table class="info-table">
              <tbody>
                <tr>
                  <th>铜期货（HGUSD）</th>
                  <td>$6.1795 / 磅 <span class="negative">(-0.44%)</span></td>
                </tr>
                <tr>
                  <th>LME 3个月期铜</th>
                  <td>~$13,613 / 吨</td>
                </tr>
                <tr>
                  <th>52周区间</th>
                  <td>$4.32 - $6.65 / 磅</td>
                </tr>
                <tr>
                  <th>50日均线</th>
                  <td>$6.33 / 磅 → 当前价低于均线</td>
                </tr>
              </tbody>
            </table>

            <div class="memo-box">
              <h4>核心矛盾</h4>
              <p>结构性紧缺 vs 宏观逆风</p>
            </div>
          </article>

          <article class="panel">
            <h3>主要机构中期预测汇总</h3>
            <table class="forecast-table">
              <thead>
                <tr>
                  <th>机构</th>
                  <th>2026H2 预测（LME 美元/吨）</th>
                  <th>核心逻辑</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>摩根大通</td>
                  <td>Q3: $13,000 → Q4: $12,500</td>
                  <td>短期宏观逆风，但中国基本面改善提供缓冲</td>
                </tr>
                <tr>
                  <td>花旗</td>
                  <td>基准 ~$12,000；乐观 $15,000</td>
                  <td>结构性需求托底，大跌空间有限</td>
                </tr>
                <tr>
                  <td>高盛</td>
                  <td>2026 年均价 $12,650</td>
                  <td>能源冲击拖累增长，远期扩产仍慢</td>
                </tr>
                <tr>
                  <td>中信证券</td>
                  <td>站稳 $13,000+</td>
                  <td>国内超预期去库 + 供给扰动加剧</td>
                </tr>
                <tr>
                  <td>RBC</td>
                  <td>H2 ~$5.75/磅（≈$12,676/吨）</td>
                  <td>供给恢复快于 H2 需求温和改善</td>
                </tr>
              </tbody>
            </table>
          </article>
        </div>

        <div class="case-grid case-grid--bottom">
          <article class="panel">
            <h3>中期情景推演</h3>
            <div class="scenario-board">
              <div class="scenario-row">
                <span>$14,000+</span>
                <strong>强牛情景</strong>
                <em>~20%</em>
              </div>
              <div class="scenario-row">
                <span>$12,500-$14,000</span>
                <strong>基准偏强</strong>
                <em>~40%</em>
              </div>
              <div class="scenario-row">
                <span>$11,000-$12,500</span>
                <strong>震荡偏弱</strong>
                <em>~30%</em>
              </div>
              <div class="scenario-row">
                <span>&lt;$11,000</span>
                <strong>悲观情景</strong>
                <em>~10%</em>
              </div>
            </div>
          </article>

          <article class="panel">
            <h3>关键风险变量</h3>
            <div class="risk-columns">
              <div class="risk-column">
                <h4>向上风险（催化）</h4>
                <ul>
                  <li>美联储转向，风险偏好回升</li>
                  <li>中国加码财政 / 基建刺激</li>
                  <li>更多矿山停产与供应扰动放大</li>
                  <li>AI 与电网投资继续超预期</li>
                </ul>
              </div>
              <div class="risk-column">
                <h4>向下风险（威胁）</h4>
                <ul>
                  <li>全球衰退预期显著加深</li>
                  <li>美元与实际利率重新上行</li>
                  <li>需求兑现弱于新能源 / AI 叙事</li>
                  <li>库存恢复快于市场预期</li>
                </ul>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="todo-card">
        <div class="eyebrow">PIPELINE</div>
        <h3>功能待开发</h3>
        <ul>
          <li>机构研报摘要与多来源归纳</li>
          <li>宏观 / 商品 / 加密专题问答</li>
          <li>策略 Memo 自动生成</li>
          <li>情景推演与风险清单输出</li>
        </ul>
      </section>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { PageWrapper } from '@/components/Page';
</script>

<style scoped lang="less">
  .financial-ai-page {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 12px 4px 18px;
  }

  .hero-card,
  .case-card,
  .todo-card,
  .panel {
    border: 1px solid rgba(214, 223, 232, 0.92);
    border-radius: 22px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(246, 250, 253, 0.96));
    box-shadow: 0 18px 40px rgba(137, 160, 187, 0.1);
  }

  .hero-card {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) 320px;
    gap: 18px;
    padding: 24px 26px;
  }

  .eyebrow {
    color: #6c8fb1;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.18em;
  }

  .hero-copy h1,
  .section-head h2 {
    margin: 8px 0 0;
    color: #172126;
  }

  .hero-copy p {
    margin: 14px 0 0;
    color: #5f6b78;
    line-height: 1.85;
  }

  .hero-status {
    padding: 18px 20px;
    border-radius: 18px;
    background: rgba(239, 246, 252, 0.92);
  }

  .hero-status span {
    color: #8b97a5;
    font-size: 12px;
  }

  .hero-status strong {
    display: block;
    margin-top: 8px;
    color: #17322d;
    font-size: 30px;
  }

  .hero-status p {
    margin: 10px 0 0;
    color: #5f6b78;
    line-height: 1.8;
  }

  .case-card {
    padding: 22px;
  }

  .section-head {
    margin-bottom: 16px;
  }

  .case-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .case-grid--bottom {
    margin-top: 16px;
  }

  .panel {
    padding: 18px 20px;
  }

  .panel h3 {
    margin: 0 0 14px;
    color: #203247;
    font-size: 18px;
  }

  .info-table,
  .forecast-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }

  .info-table th,
  .info-table td,
  .forecast-table th,
  .forecast-table td {
    padding: 12px 10px;
    border-bottom: 1px solid rgba(221, 228, 236, 0.95);
    text-align: left;
    vertical-align: top;
  }

  .info-table th,
  .forecast-table th {
    color: #6d7987;
    font-weight: 600;
  }

  .negative {
    color: #d8585f;
  }

  .memo-box {
    margin-top: 16px;
    padding: 14px 16px;
    border-radius: 14px;
    background: rgba(235, 243, 250, 0.92);
  }

  .memo-box h4 {
    margin: 0 0 8px;
    color: #203247;
  }

  .memo-box p {
    margin: 0;
    color: #5f6b78;
  }

  .scenario-board {
    display: grid;
    gap: 10px;
  }

  .scenario-row {
    display: grid;
    grid-template-columns: 1.25fr 1fr auto;
    gap: 12px;
    padding: 12px 14px;
    border-radius: 12px;
    background: rgba(21, 37, 42, 0.05);
    color: #203247;
  }

  .scenario-row em {
    color: #5479a2;
    font-style: normal;
    font-weight: 700;
  }

  .risk-columns {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .risk-column {
    padding: 14px 16px;
    border-radius: 14px;
    background: rgba(248, 250, 252, 0.9);
  }

  .risk-column h4 {
    margin: 0 0 10px;
    color: #203247;
  }

  .risk-column ul {
    margin: 0;
    padding-left: 18px;
    color: #5f6b78;
    line-height: 1.8;
  }

  .todo-card {
    padding: 22px 24px;
  }

  .todo-card h3 {
    margin: 10px 0 12px;
    color: #172126;
  }

  .todo-card ul {
    margin: 0;
    padding-left: 18px;
    color: #5f6b78;
    line-height: 1.85;
  }

  @media (max-width: 1100px) {
    .hero-card,
    .case-grid,
    .risk-columns {
      grid-template-columns: 1fr;
    }
  }
</style>
