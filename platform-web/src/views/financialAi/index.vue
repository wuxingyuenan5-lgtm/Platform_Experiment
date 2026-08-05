<template>
  <RestoredProductSurface
    state="unavailable"
    source="not-configured:financial-ai-provider"
    :actionable="false"
    message="金融 AI 产品结构已恢复，但真实模型 Provider 尚未配置；页面不会把静态内容伪装成模型输出。"
  >
    <main class="ai-page">
      <header class="ai-head">
        <div><span>FINANCIAL INTELLIGENCE</span><h1>金融 AI</h1><p>研究提问、资料引用、情景推演与风险提示的统一工作台。</p></div>
        <b>Provider 未配置</b>
      </header>

      <section class="ai-layout">
        <aside class="panel sessions">
          <div class="panel-head"><h2>研究会话</h2><span>只读结构</span></div>
          <button v-for="item in sessions" :key="item.title"><strong>{{ item.title }}</strong><small>{{ item.note }}</small></button>
        </aside>

        <section class="panel conversation">
          <div class="panel-head"><div><h2>跨资产研究助手</h2><small>未调用任何真实模型</small></div><span>Unavailable</span></div>
          <div class="message message--user">分析当前进攻风格与防守风格的相对状态。</div>
          <div class="message message--assistant">
            <strong>等待 Provider</strong>
            <p>模型服务尚未配置。正式接入后，回答必须附带数据时间、引用来源和不可执行声明。</p>
            <div class="evidence"><span>数据时间：未获取</span><span>引用来源：未获取</span><span>可操作性：否</span></div>
          </div>
          <div class="composer">
            <textarea disabled placeholder="Provider 配置完成后可输入研究问题"></textarea>
            <button v-if="canWrite" disabled>运行分析</button><b v-else>只读权限</b>
          </div>
        </section>

        <aside class="panel evidence-panel">
          <div class="panel-head"><h2>证据要求</h2><span>Contract</span></div>
          <ul><li v-for="item in evidence" :key="item"><i></i>{{ item }}</li></ul>
          <div class="guard">无来源、无时间戳或数据状态不明时，结果不得作为交易依据。</div>
        </aside>
      </section>
    </main>
  </RestoredProductSurface>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import { hasPermission } from '@/access/userAccess';
  import { useUserStore } from '@/store/modules/user';

  const userStore = useUserStore();
  const canWrite = computed(() => hasPermission(userStore.getAuthentication?.permissions || [], 'research.write'));
  const sessions = [
    { title: '跨资产晨报', note: '模板' },
    { title: 'A股进攻行情判断', note: '研究框架' },
    { title: '黄金价差拆分', note: '策略研究' },
    { title: '组合风险复核', note: '风险提示' },
  ];
  const evidence = ['标注数据来源与时间', '区分事实、计算和推断', '展示 live/sample/unavailable/error', '禁止无门禁的交易执行'];
</script>

<style scoped>
  .ai-page{display:grid;gap:12px;color:#172033}.ai-head{display:flex;justify-content:space-between;align-items:end;gap:16px;padding:24px;border-radius:16px;background:linear-gradient(135deg,#151a2e,#293a68);color:#fff}.ai-head span{font-size:11px;letter-spacing:.18em;color:#bdc8e2}.ai-head h1{margin:5px 0;font-size:28px}.ai-head p{margin:0;color:#cbd4e7}.ai-head b{padding:7px 11px;border-radius:999px;background:rgba(255,255,255,.12);font-size:12px}.ai-layout{display:grid;grid-template-columns:240px minmax(0,1fr) 260px;gap:10px;min-height:560px}.panel{border:1px solid #e1e7ef;border-radius:14px;background:#fff;padding:15px}.panel-head{display:flex;justify-content:space-between;align-items:start;margin-bottom:14px}.panel-head h2{margin:0;font-size:16px}.panel-head span,.panel-head small{color:#7b8798;font-size:11px}.sessions{display:grid;align-content:start;gap:8px}.sessions button{display:grid;gap:3px;text-align:left;padding:11px;border:1px solid #e6eaf0;border-radius:9px;background:#fafbfd;color:#26334a}.sessions small{color:#7b8798}.conversation{display:flex;flex-direction:column;gap:14px}.message{max-width:82%;padding:14px;border-radius:12px;line-height:1.65}.message--user{align-self:flex-end;background:#eaf1ff;color:#274d86}.message--assistant{background:#f5f7fa}.message p{margin:6px 0}.evidence{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}.evidence span{padding:4px 7px;border-radius:999px;background:#fff;color:#677386;font-size:11px}.composer{display:grid;grid-template-columns:1fr auto;gap:8px;margin-top:auto}.composer textarea{min-height:86px;resize:none;border:1px solid #dfe5ed;border-radius:10px;padding:10px;background:#f7f9fb}.composer button{border:0;border-radius:10px;background:#dfe6f2;color:#657188;padding:0 16px}.composer b{align-self:center;padding:7px 10px;border-radius:999px;background:#eef1f5;color:#687386;font-size:12px}.evidence-panel ul{display:grid;gap:12px;padding:0;margin:0;list-style:none}.evidence-panel li{display:grid;grid-template-columns:10px 1fr;gap:8px;align-items:start;color:#596579}.evidence-panel i{width:8px;height:8px;margin-top:6px;border-radius:50%;background:#4e75b6}.guard{margin-top:18px;padding:12px;border-radius:10px;background:#fff6dd;color:#765816;line-height:1.6;font-size:12px}@media(max-width:1050px){.ai-layout{grid-template-columns:1fr}.sessions{grid-template-columns:repeat(2,1fr)}.evidence-panel{display:none}}@media(max-width:560px){.ai-head{align-items:start;flex-direction:column}.sessions{grid-template-columns:1fr}.composer{grid-template-columns:1fr}.message{max-width:100%}}
</style>
