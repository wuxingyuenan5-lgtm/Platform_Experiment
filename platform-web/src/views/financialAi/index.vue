<template>
  <RestoredProductSurface
    state="unavailable"
    source="not-configured:financial-ai-provider"
    :actionable="false"
    message="原金融 AI 页面布局和信息架构已恢复；真实模型 Provider 尚未配置，不生成假回答或伪成功状态。"
  >
    <PageWrapper title="金融AI分析">
      <main class="financial-ai-page" data-testid="financial-ai-original-structure">
        <section class="hero-card">
          <div class="hero-copy">
            <div class="eyebrow">FINANCIAL AI</div>
            <h1>研究辅助与情景推演中枢</h1>
            <p>保留研究输入、资料引用、情景推演与结果容器；Provider 接入前，全部执行入口关闭。</p>
          </div>
          <div class="hero-status">
            <span>当前状态</span>
            <strong>Provider 未配置</strong>
            <p>不调用模型，不展示静态内容冒充模型输出，不伪造数据来源或运行成功。</p>
          </div>
        </section>

        <section class="case-card">
          <header class="section-head">
            <div>
              <div class="eyebrow">RESEARCH WORKSPACE</div>
              <h2>专题研究输入与结果区</h2>
            </div>
            <b>Unavailable</b>
          </header>

          <div class="case-grid">
            <article class="panel input-panel">
              <h3>研究问题</h3>
              <label>
                专题
                <select disabled><option>铜价中期（6-12个月）走势分析</option></select>
              </label>
              <label>
                研究要求
                <textarea disabled placeholder="Provider 配置后可输入研究问题、时间范围与证据要求"></textarea>
              </label>
              <div class="input-actions">
                <button type="button" disabled data-write-action="true">运行分析</button>
                <span>执行入口禁用：not-configured:financial-ai-provider</span>
              </div>
            </article>

            <article class="panel result-panel">
              <h3>分析结果</h3>
              <div class="unavailable-result">
                <strong>暂无模型结果</strong>
                <p>真实 Provider、数据引用与时间戳均未配置，因此不生成任何结论、预测或机构观点汇总。</p>
                <dl>
                  <div><dt>模型状态</dt><dd>unavailable</dd></div>
                  <div><dt>数据来源</dt><dd>未获取</dd></div>
                  <div><dt>数据时间</dt><dd>未获取</dd></div>
                  <div><dt>可操作性</dt><dd>false</dd></div>
                </dl>
              </div>
            </article>
          </div>

          <div class="case-grid case-grid--bottom">
            <article class="panel">
              <h3>情景推演容器</h3>
              <div class="scenario-board">
                <div v-for="item in scenarioSlots" :key="item" class="scenario-row">
                  <span>--</span><strong>{{ item }}</strong><em>等待 Provider</em>
                </div>
              </div>
            </article>
            <article class="panel">
              <h3>证据与风险要求</h3>
              <div class="risk-columns">
                <section>
                  <h4>结果必须包含</h4>
                  <ul><li>明确数据来源与时间</li><li>区分事实、计算与推断</li><li>展示数据状态和局限</li></ul>
                </section>
                <section>
                  <h4>禁止事项</h4>
                  <ul><li>无来源模型回答</li><li>伪造机构观点或数值</li><li>绕过交易安全门禁</li></ul>
                </section>
              </div>
            </article>
          </div>
        </section>

        <section class="todo-card">
          <div class="eyebrow">PIPELINE</div>
          <h3>待真实 Owner 接入</h3>
          <ul><li>模型 Provider 与鉴权</li><li>研究数据引用和时间戳</li><li>结果审计与来源追踪</li><li>受控研究 Memo 输出</li></ul>
        </section>
      </main>
    </PageWrapper>
  </RestoredProductSurface>
</template>

<script setup lang="ts">
  import { PageWrapper } from '@/components/Page';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';

  const scenarioSlots = ['强势情景', '基准情景', '弱势情景', '压力情景'];
</script>

<style scoped lang="less">
  .financial-ai-page { display: flex; flex-direction: column; gap: 18px; padding: 12px 4px 18px; }
  .hero-card, .case-card, .todo-card, .panel { border: 1px solid rgba(214, 223, 232, .92); border-radius: 22px; background: linear-gradient(180deg, rgba(255,255,255,.98), rgba(246,250,253,.96)); box-shadow: 0 18px 40px rgba(137,160,187,.1); }
  .hero-card { display: grid; grid-template-columns: minmax(0, 1.45fr) 320px; gap: 18px; padding: 24px 26px; }
  .eyebrow { color: #6c8fb1; font-size: 12px; font-weight: 700; letter-spacing: .18em; }
  h1, h2 { margin: 8px 0 0; color: #172126; }
  .hero-copy p, .hero-status p { color: #5f6b78; line-height: 1.8; }
  .hero-status { padding: 18px 20px; border-radius: 18px; background: rgba(239,246,252,.92); }
  .hero-status span { color: #8b97a5; font-size: 12px; }
  .hero-status strong { display: block; margin-top: 8px; color: #7c5b11; font-size: 24px; }
  .case-card { padding: 22px; }
  .section-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }
  .section-head b { padding: 6px 10px; border-radius: 999px; background: #fff4d5; color: #846116; font-size: 12px; }
  .case-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
  .case-grid--bottom { margin-top: 16px; }
  .panel { padding: 18px 20px; }
  .panel h3 { margin: 0 0 14px; color: #203247; font-size: 18px; }
  .input-panel { display: grid; gap: 13px; }
  label { display: grid; gap: 6px; color: #657181; }
  select, textarea { padding: 10px; border: 1px solid #dce3eb; border-radius: 10px; background: #f7f9fb; }
  textarea { min-height: 150px; resize: none; }
  .input-actions { display: grid; gap: 7px; }
  button { height: 40px; border: 0; border-radius: 9px; background: #e2e7ed; color: #75808e; }
  .input-actions span { color: #846116; font-size: 12px; }
  .unavailable-result { display: grid; gap: 12px; padding: 18px; border-radius: 14px; background: #f6f8fb; }
  .unavailable-result p { margin: 0; color: #637083; line-height: 1.7; }
  dl { display: grid; gap: 8px; margin: 0; }
  dl div { display: flex; justify-content: space-between; gap: 12px; padding-bottom: 8px; border-bottom: 1px solid #e8edf2; }
  dt { color: #768294; } dd { margin: 0; font-weight: 700; }
  .scenario-board { display: grid; gap: 10px; }
  .scenario-row { display: grid; grid-template-columns: .8fr 1fr 1fr; gap: 12px; padding: 12px 14px; border-radius: 12px; background: rgba(21,37,42,.05); }
  .scenario-row em { color: #7c5b11; font-style: normal; }
  .risk-columns { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }
  .risk-columns section { padding: 14px; border-radius: 13px; background: #f8fafc; }
  .risk-columns h4 { margin: 0 0 8px; } ul { margin: 0; padding-left: 18px; color: #5f6b78; line-height: 1.8; }
  .todo-card { padding: 22px 24px; }
  .todo-card h3 { margin: 10px 0 12px; }
  @media (max-width: 1000px) { .hero-card, .case-grid, .risk-columns { grid-template-columns: 1fr; } }
</style>
