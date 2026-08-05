<template>
  <PageWrapper title="新闻日历与理财">
    <div class="news-layout">
      <aside class="section-sidebar">
        <RouterLink v-for="item in sectionTabs" :key="item.path" :to="item.path" :class="{ 'is-active': section === item.key }">
          <component :is="item.icon" /><span>{{ item.label }}</span>
        </RouterLink>
      </aside>

      <div class="section-content">
        <template v-if="section === 'macro'">
          <RestoredProductDataBanner state="live" source="TradingView Economic Calendar" as-of="provider-defined" :actionable="false" message="宏观日历直接读取第三方公开 Widget；Platform 不缓存或改写事件数值。" />
          <TradingViewEconomicCalendarPanel />
        </template>

        <RestoredProductSurface v-else-if="section === 'news'" state="sample" source="sample:news-digest" as-of="2026-08-05 · 非实时" :actionable="false" message="新闻 Provider 尚未配置；标题、摘要和影响标签为明确标记的样例内容。">
          <section class="digest-grid">
            <article v-for="item in newsItems" :key="item.title" class="news-card">
              <div><span>{{ item.asset }}</span><time>{{ item.time }}</time></div>
              <h2>{{ item.title }}</h2><p>{{ item.summary }}</p>
              <footer><b>{{ item.impact }}</b><small>{{ item.source }}</small></footer>
            </article>
          </section>
        </RestoredProductSurface>

        <RestoredProductSurface v-else state="sample" source="sample:wealth-campaigns" as-of="2026-08-05 · 非实时" :actionable="false" message="活动利率、额度和期限不是实时事实，不构成推荐或收益承诺。">
          <section class="wealth-grid">
            <article v-for="item in wealthItems" :key="item.title"><span>{{ item.type }}</span><h2>{{ item.title }}</h2><strong>{{ item.rate }}</strong><p>{{ item.note }}</p><button disabled>仅查看外部参考</button></article>
          </section>
          <p class="disclaimer">示例内容不可申购、不可执行；外部页面由第三方维护，不属于 Platform 正式数据。</p>
        </RestoredProductSurface>
      </div>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, type Component } from 'vue';
  import { RouterLink, useRoute } from 'vue-router';
  import { CalendarOutlined, FileSearchOutlined, FundOutlined } from '@ant-design/icons-vue';
  import { PageWrapper } from '@/components/Page';
  import RestoredProductDataBanner from '@/components/ProductDataState/RestoredProductDataBanner.vue';
  import RestoredProductSurface from '@/components/ProductDataState/RestoredProductSurface.vue';
  import TradingViewEconomicCalendarPanel from '@/views/hedgeBoard/tradingTools/components/TradingViewEconomicCalendarPanel.vue';

  type NewsSection = 'macro' | 'news' | 'wealth';
  const route = useRoute();
  const section = computed<NewsSection>(() => {
    const value = route.meta.newsSection;
    if (value === 'news' || value === 'wealth') return value;
    return 'macro';
  });
  const sectionTabs: Array<{ key: NewsSection; label: string; path: string; icon: Component }> = [
    { key: 'macro', label: '宏观日历', path: '/news-calendar/macro', icon: CalendarOutlined },
    { key: 'news', label: '新闻整理', path: '/news-calendar/news', icon: FileSearchOutlined },
    { key: 'wealth', label: '理财信息', path: '/news-calendar/wealth', icon: FundOutlined },
  ];
  const newsItems = [
    { asset: 'A股', time: '08:45', title: '成交扩散与风格切换观察', summary: '关注宽基上涨是否伴随成交额和行业广度同步改善。', impact: '中等影响', source: 'sample:editorial' },
    { asset: '商品', time: '10:20', title: '有色与贵金属相对强弱', summary: '比较铜、金与美元利率变量的方向一致性。', impact: '高影响', source: 'sample:editorial' },
    { asset: '加密', time: '12:10', title: '资金费与跨所价差状态', summary: '观察永续资金费、现货深度和稳定币换汇因子。', impact: '中等影响', source: 'sample:editorial' },
    { asset: '美股', time: '20:30', title: '开盘前宏观变量核对', summary: '核对利率、美元和波动率对指数期货的共同影响。', impact: '高影响', source: 'sample:editorial' },
  ];
  const wealthItems = [
    { type: '现金管理', title: '短久期流动性方案', rate: '示例 3.2%', note: '利率、额度和期限均非实时。' },
    { type: '套利工具', title: '低波动套利组合', rate: '示例 4.8%', note: '不代表真实产品或收益承诺。' },
    { type: '结构观察', title: '黄金区间研究票据', rate: '示例 6.0%', note: '仅展示产品信息结构。' },
  ];
</script>

<style scoped>
  .news-layout{display:grid;grid-template-columns:190px minmax(0,1fr);gap:16px;min-width:0;padding:16px}.section-sidebar{display:flex;flex-direction:column;gap:6px;align-self:start;padding:8px;border:1px solid #e7edf3;border-radius:10px;background:#fff}.section-sidebar a{display:flex;align-items:center;gap:9px;padding:10px 12px;border-radius:7px;color:#59636e}.section-sidebar a.is-active{color:#1769aa;background:#edf6ff;font-weight:600}.section-content{min-width:0}.digest-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.news-card,.wealth-grid article{border:1px solid #e2e8f0;border-radius:13px;background:#fff;padding:17px}.news-card>div,.news-card footer{display:flex;justify-content:space-between;gap:10px}.news-card span,.news-card time,.news-card small{color:#718096;font-size:12px}.news-card h2{margin:12px 0 8px;font-size:18px}.news-card p{color:#667085;line-height:1.65}.news-card footer b{color:#9a6712}.wealth-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.wealth-grid span{color:#607099;font-size:12px}.wealth-grid h2{font-size:17px}.wealth-grid strong{display:block;font-size:25px;color:#225a96}.wealth-grid p{color:#667085}.wealth-grid button{border:0;border-radius:8px;padding:9px 12px;background:#e7ecf3;color:#748094}.disclaimer{margin:12px 0 0;color:#687386;font-size:12px}@media(max-width:900px){.digest-grid,.wealth-grid{grid-template-columns:1fr}.news-layout{grid-template-columns:1fr}.section-sidebar{flex-direction:row;overflow-x:auto}.section-sidebar a{flex:0 0 auto}}
</style>
