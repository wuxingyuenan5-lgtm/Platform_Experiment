<template>
  <main class="spread-page">
    <template v-if="activeSection === 'analysis'">
      <RestoredProductSurface
        state="sample"
        source="sample:spread-research"
        as-of="2026-08-05 · 非实时"
        :actionable="false"
        message="价差研究结构已恢复；图表与拆分值为不可执行样例，当前执行区继续使用正式 CrossVenueExecutionWorkspace。"
      >
        <header class="spread-head">
          <div><span>SPREAD RESEARCH</span><h2>跨所价差研究</h2><p>{{ selectedVenue }} · {{ leftLegSymbol }} / {{ rightLegSymbol }} · {{ selectedResolution }}</p></div>
          <b>{{ variant === 'domesticOverseas' ? '海内外价差' : '跨所价差' }}</b>
        </header>

        <section class="quote-grid">
          <article v-for="item in quotes" :key="item.label"><span>{{ item.label }}</span><strong>{{ item.value }}</strong><small>{{ item.note }}</small></article>
        </section>

        <section class="research-grid">
          <article class="panel chart-panel">
            <div class="panel-head"><h3>价差路径</h3><span>Sample</span></div>
            <div class="chart-area">
              <div class="zero-line"></div>
              <svg viewBox="0 0 800 250" preserveAspectRatio="none" aria-label="sample spread chart">
                <polyline points="0,150 70,130 140,165 210,108 280,126 350,72 420,96 490,54 560,88 630,46 700,76 800,42" fill="none" stroke="currentColor" stroke-width="5" />
              </svg>
            </div>
            <div class="axis"><span>09:30</span><span>12:00</span><span>15:00</span><span>21:30</span></div>
          </article>

          <article class="panel">
            <div class="panel-head"><h3>损益拆分</h3><span>只读</span></div>
            <dl><div v-for="item in decomposition" :key="item.label"><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></div></dl>
          </article>
        </section>

        <section class="panel scenario-panel">
          <div class="panel-head"><h3>研究场景</h3><span>不可下单</span></div>
          <div class="scenario-grid"><article v-for="item in scenarios" :key="item.title"><strong>{{ item.title }}</strong><p>{{ item.body }}</p><small>{{ item.result }}</small></article></div>
        </section>
      </RestoredProductSurface>
    </template>

    <template v-else>
      <div class="execution-state">
        <div>
          <strong>正式执行工作区</strong>
          <span>继续使用 Platform API 与 Execution Runtime 的事实和安全门禁。</span>
        </div>
        <b>Live Write关闭</b>
      </div>
      <CrossVenueExecutionWorkspace :left-leg-symbol="leftLegSymbol" :right-leg-symbol="rightLegSymbol" />
    </template>
  </main>
</template>

<script setup lang="ts">
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import CrossVenueExecutionWorkspace from './components/CrossVenueExecutionWorkspace.vue';
  import type { SpreadWorkspaceVariant } from './types';

  withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedVenue?: string;
      leftLegSymbol?: string;
      rightLegSymbol?: string;
      selectedResolution?: string;
      variant?: SpreadWorkspaceVariant;
    }>(),
    {
      activeSection: 'analysis', selectedVenue: 'Bybit', leftLegSymbol: 'XAUTUSDT.P',
      rightLegSymbol: 'XAUUSD+', selectedResolution: '30分钟', variant: 'crossVenue',
    },
  );

  const quotes = [
    { label: '做多价差', value: '+18.42', note: '主腿Ask - 对冲腿Bid' },
    { label: '做空价差', value: '+17.96', note: '主腿Bid - 对冲腿Ask' },
    { label: 'USDT/USD', value: '1.0008', note: '样例换算因子' },
    { label: '资金费库存', value: '+0.010%', note: '非实时' },
  ];
  const decomposition = [
    { label: '合约溢价', value: '+6.18' },
    { label: '稳定币换汇', value: '+1.87' },
    { label: '场所报价差', value: '+9.96' },
    { label: '交易成本预估', value: '-0.42' },
  ];
  const scenarios = [
    { title: '价差扩张', body: '主腿相对对冲腿继续走强，观察资金费与库存是否同步恶化。', result: '研究阈值：+20.00' },
    { title: '均值回归', body: '价差回到中轴，检查两腿流动性和成交确认是否完整。', result: '研究阈值：+14.50' },
    { title: '结果不确定', body: '任一场所查询不可用时保持 fail-closed，不把 ACK 当作 Fill。', result: '状态：result_unknown' },
  ];
</script>

<style scoped>
  .spread-page{display:grid;gap:12px;color:#172033}.spread-head,.execution-state{display:flex;justify-content:space-between;align-items:end;gap:16px;padding:18px;border:1px solid #e1e7ef;border-radius:14px;background:#fff}.spread-head span{font-size:11px;letter-spacing:.16em;color:#63739b}.spread-head h2{margin:4px 0;font-size:24px}.spread-head p{margin:0;color:#6d788a}.spread-head b,.execution-state b{padding:6px 10px;border-radius:999px;background:#eef3fb;color:#44618f;font-size:12px}.quote-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:12px}.quote-grid article,.panel{border:1px solid #e1e7ef;border-radius:13px;background:#fff}.quote-grid article{display:grid;gap:5px;padding:15px}.quote-grid span,.quote-grid small{color:#6c778a}.quote-grid strong{font-size:22px}.research-grid{display:grid;grid-template-columns:1.6fr .8fr;gap:10px;margin-top:10px}.panel{padding:16px}.panel-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.panel-head h3{margin:0;font-size:16px}.panel-head span{padding:4px 8px;border-radius:999px;background:#fff4d5;color:#846116;font-size:11px}.chart-area{position:relative;height:260px;border-radius:10px;background:linear-gradient(180deg,#f7faff,#fff);overflow:hidden;color:#3978c9}.chart-area svg{position:absolute;inset:20px 0 12px;width:100%;height:calc(100% - 32px)}.zero-line{position:absolute;left:0;right:0;top:55%;border-top:1px dashed #ccd6e4}.axis{display:flex;justify-content:space-between;color:#8290a5;font-size:11px;margin-top:8px}dl{display:grid;gap:13px;margin:0}dl div{display:flex;justify-content:space-between;padding-bottom:10px;border-bottom:1px solid #edf1f5}dt{color:#6d788a}dd{margin:0;font-weight:700}.scenario-panel{margin-top:10px}.scenario-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.scenario-grid article{padding:14px;border:1px solid #e5eaf1;border-radius:10px;background:#fafbfd}.scenario-grid p{color:#667085;line-height:1.6}.scenario-grid small{color:#3c649d;font-weight:700}.execution-state{align-items:center}.execution-state div{display:grid;gap:4px}.execution-state span{color:#687386;font-size:12px}@media(max-width:960px){.quote-grid{grid-template-columns:repeat(2,1fr)}.research-grid{grid-template-columns:1fr}.scenario-grid{grid-template-columns:1fr}}@media(max-width:560px){.quote-grid{grid-template-columns:1fr}.spread-head,.execution-state{align-items:start;flex-direction:column}}
</style>
