<template>
  <section class="sp-research" aria-label="标普500长期统计">
    <header
      ><div><h2>标普500 · 长期统计</h2><p>价格回报，不含现金分红再投资</p></div
      ><button @click="load">刷新</button></header
    >
    <p v-if="loading" role="status">正在读取长期统计…</p
    ><p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <p v-if="stale" class="notice">部分来源本轮更新失败，保留上次有效历史。</p>
    <nav aria-label="标普500统计分类"
      ><button v-for="t in tabs" :key="t.id" :aria-pressed="view === t.id" @click="view = t.id">{{
        t.name
      }}</button></nav
    >
    <div class="controls"
      ><label
        >开始年份
        <select v-model.number="start"
          ><option v-for="y in allYears" :key="y" :value="y">{{ y }}</option></select
        ></label
      ><label
        >结束年份
        <select v-model.number="end"
          ><option v-for="y in allYears" :key="y" :value="y">{{ y }}</option></select
        ></label
      ><button @click="reset">全部</button
      ><button @click="methodOpen = !methodOpen" :aria-expanded="methodOpen"
        >如何理解？</button
      ></div
    >
    <p v-if="start > end" role="alert">开始年份应不晚于结束年份。</p>
    <template v-if="view === 'drivers' && drivers.length">
      <h3>回报归因：估值扩张与盈利驱动</h3
      ><div class="summary"
        ><article
          ><span>区间</span><b>{{ drivers[0].year }}—{{ drivers.at(-1)?.year }}</b
          ><small>{{ drivers.length }}年</small></article
        ><article v-for="c in categories" :key="c.id"
          ><span>{{ c.name }}</span
          ><b>{{ drivers.filter((r) => c.keys.includes(r.driver)).length }}</b
          ><small>年</small></article
        ></div
      >
      <ReferencePlot
        title="年度回报拆分：估值、盈利与口径差额"
        :rows="drivers"
        :lines="driverLines"
      />
      <p class="definition"
        >同口径下，价格变动＝PE变动＋EPS变动＋交互项。图中交互项均分给两项，参考输入与价格序列的差额另列，避免误当成精确两项相加。</p
      >
      <div class="table-scroll"
        ><table
          ><thead
            ><tr
              ><th>年份</th><th>价格回报</th><th>PE变化</th><th>EPS变化</th><th>口径差额（pp）</th
              ><th>主导因素</th><th>年末PE</th><th>年末EPS</th></tr
            ></thead
          ><tbody
            ><tr v-for="r in [...drivers].reverse()" :key="r.year"
              ><th>{{ r.year }}</th
              ><td :class="tone(r.returnPct)">{{ fmt(r.returnPct) }}%</td
              ><td>{{ fmt(r.pePct) }}%</td><td>{{ fmt(r.epsPct) }}%</td
              ><td>{{ fmt(r.residual) }}</td
              ><td
                ><span class="driver-tag">{{ driverName(r.driver) }}</span></td
              ><td>{{ fmt(r.endingPE) }}×</td><td>{{ fmt(r.endingEPS) }}</td></tr
            ></tbody
          ></table
        ></div
      >
    </template>
    <template v-else-if="view === 'drawdown' && annual.length">
      <h3>年内最深跌幅 vs 全年最终收益</h3
      ><div class="summary"
        ><article
          ><span>完整年度</span><b>{{ completed.length }}</b></article
        ><article
          ><span>平均年内回撤</span
          ><b class="negative">{{ fmt(mean(completed, 'drawdown')) }}%</b></article
        ><article
          ><span>平均年度收益</span><b>{{ fmt(mean(completed, 'returnPct')) }}%</b></article
        ><article
          ><span>正收益比例</span
          ><b
            >{{ completed.filter((r) => Number(r.returnPct) > 0).length }} /
            {{ completed.length }}</b
          ></article
        ><article
          ><span>最深回撤年份</span><b>{{ deepest?.year || '—' }}</b
          ><small>{{ fmt(deepest?.drawdown) }}%</small></article
        ></div
      >
      <ReferencePlot
        title="年内最大回撤与年度价格收益"
        :rows="annual"
        :lines="[
          { key: 'returnPct', name: '年度 / YTD收益', color: '#087f80', type: 'bar', signed: true },
          { key: 'drawdown', name: '年内最大回撤', color: '#bd4a54', type: 'scatter' },
        ]"
      />
      <div class="table-scroll"
        ><table
          ><thead
            ><tr
              ><th>年份</th><th>年内最大回撤</th><th>年度 / YTD收益</th><th>创历史新高次数</th
              ><th>低点日期</th><th>最后收盘日期</th></tr
            ></thead
          ><tbody
            ><tr v-for="r in [...annual].reverse()" :key="r.year"
              ><th>{{ r.year }}{{ r.ongoing ? ' *' : '' }}</th
              ><td class="negative">{{ fmt(r.drawdown) }}%</td
              ><td :class="tone(r.returnPct)">{{ fmt(r.returnPct) }}%</td><td>{{ r.ath ?? '—' }}</td
              ><td>{{ r.trough_date }}</td
              ><td>{{ r.year_end_date }}</td></tr
            ></tbody
          ></table
        ></div
      ><p class="definition"
        >*为进行中年度，不参与完整年度均值与正收益比例；回撤取每日收盘相对此前高点的最深跌幅，不是年内最低价相对年初。</p
      >
    </template>
    <template v-else-if="view === 'monthly' && months.length">
      <h3>月度收益热力表</h3
      ><div class="table-scroll"
        ><table class="monthly"
          ><thead
            ><tr
              ><th>年份</th><th v-for="m in 12" :key="m">{{ m }}月</th><th>年度</th></tr
            ><tr
              ><th>上涨概率</th
              ><td v-for="m in 12" :key="m" :title="monthSample(m) + '个有效月份'"
                >{{ fmt(winRate(m), 0) }}%</td
              ><td>—</td></tr
            ></thead
          ><tbody
            ><tr v-for="r in [...months].reverse()" :key="r.year"
              ><th>{{ r.year }}</th
              ><td v-for="m in 12" :key="m"
                ><span
                  :style="heat(r.months[String(m)])"
                  :title="r.year + '年' + m + '月价格收益'"
                  >{{
                    r.months[String(m)] == null
                      ? '—'
                      : fmt(Number(r.months[String(m)]) * 100, 1) + '%'
                  }}</span
                ></td
              ><td
                ><span :style="heat(r.annual)">{{
                  r.annual == null ? '—' : fmt(Number(r.annual) * 100, 1) + '%'
                }}</span></td
              ></tr
            ></tbody
          ></table
        ></div
      >
      <div class="summary"
        ><article
          ><span>区间</span><b>{{ months[0].year }}—{{ months.at(-1)?.year }}</b></article
        ><article
          ><span>月收益中位数</span><b>{{ fmt(monthStats.median) }}%</b></article
        ><article
          ><span>最佳月</span><b>{{ monthStats.best?.date || '—' }}</b
          ><small>{{ fmt(monthStats.best?.value) }}%</small></article
        ><article
          ><span>最差月</span><b>{{ monthStats.worst?.date || '—' }}</b
          ><small>{{ fmt(monthStats.worst?.value) }}%</small></article
        ></div
      >
      <p class="definition"
        >上涨概率只统计所选区间中有数值的月份；零收益保留在分母。尚未发生的月份留空，年度收益为来源年度序列，不把月收益简单相加。</p
      >
    </template>
    <p v-else-if="!loading">所选区间暂无有效数据。</p>
    <article v-if="methodOpen" class="education" aria-label="标普统计方法"
      ><h3>如何看这三张图</h3
      ><p
        >估值提高，意味着相同盈利被给予更高价格；盈利增长则提高每股对应的利润。两者反向变化时，不能只看涨跌推断哪一项没有作用。</p
      ><p
        >精确恒等式为(1+价格回报)=(1+PE变化)×(1+EPS变化)。交互项为PE变化×EPS变化。这里将交互项各分一半；由于来源的月度PE、季度TTM
        EPS与年末价格并非完全同口径，剩余差额单列，不归给任何一方。分类沿用来源标签，不是因果识别。</p
      ><p
        >年内回撤描述持有过程中的损失，年度收益描述年末结果；经历回撤并不必然意味着全年亏损。月度上涨概率仅是历史样本频率，不是下个月获利的承诺。1957年前为标普综合指数历史，不是当时已存在的现代500只成分组合。</p
      ><a
        href="https://historyofmarket.com/zh-cn/sp500/sp500-driver-decomp/"
        target="_blank"
        rel="noopener noreferrer"
        >数据与回报拆分说明 ↗</a
      ></article
    >
    <footer
      ><a :href="sourceLink" target="_blank" rel="noopener noreferrer">数据：History of Market ↗</a
      ><span>CC BY 4.0 · {{ updated }}</span></footer
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useReferenceBoard } from '../composables/useReferenceBoard';
  import ReferencePlot, { type ReferenceLine } from './ReferencePlot.vue';

  const { data, error, loading, load } = useReferenceBoard('stocks');
  const view = ref('drivers'),
    start = ref(1928),
    end = ref(new Date().getFullYear()),
    methodOpen = ref(false);
  const tabs = [
    { id: 'drivers', name: '回报归因' },
    { id: 'drawdown', name: '年内回撤与收益' },
    { id: 'monthly', name: '月度收益' },
  ];
  const allYears = computed(() => {
    const list =
      view.value === 'drivers'
        ? data.value?.driverRows
        : view.value === 'monthly'
        ? data.value?.sp_monthly?.years
        : data.value?.sp_drawdowns?.annual;
    return (list || []).map((r: any) => r.year).sort((a: number, b: number) => a - b);
  });
  function reset() {
    start.value = allYears.value[0] || 1928;
    end.value = allYears.value.at(-1) || new Date().getFullYear();
  }
  watch(view, reset);
  const included = (r: any) => r.year >= start.value && r.year <= end.value;
  const drivers = computed(() => data.value?.driverRows?.filter(included) || []);
  const annual = computed(() =>
    (data.value?.sp_drawdowns?.annual || []).filter(included).map((r: any) => ({
      ...r,
      date: r.year + '-12-31',
      drawdown: r.dd == null ? null : Number(r.dd) * 100,
      returnPct: r.tr == null ? null : Number(r.tr) * 100,
    })),
  );
  const completed = computed(() => annual.value.filter((r: any) => !r.ongoing));
  const deepest = computed(
    () =>
      [...annual.value]
        .filter((r) => r.drawdown != null)
        .sort((a, b) => Number(a.drawdown) - Number(b.drawdown))[0],
  );
  const months = computed(() => (data.value?.sp_monthly?.years || []).filter(included));
  const stale = computed(() => data.value?.sources?.some((s: any) => s.status !== 'ready'));
  const categories = [
    { id: 'pe', name: '估值驱动', keys: ['pe'] },
    { id: 'eps', name: 'EPS驱动', keys: ['eps'] },
    { id: 'both', name: '双轮驱动', keys: ['both'] },
    { id: 'opposite', name: '对抗', keys: ['opposite_pe', 'opposite_eps'] },
  ];
  const driverName = (id: string) =>
    ({
      pe: '估值驱动',
      eps: 'EPS驱动',
      both: '双轮驱动',
      opposite_pe: '对抗 · 估值主导',
      opposite_eps: '对抗 · EPS主导',
    }[id] || id);
  const driverLines: ReferenceLine[] = [
    {
      key: 'peContribution',
      name: '估值贡献（含半数交互项）',
      color: '#243e60',
      type: 'bar',
      stack: 'return',
    },
    {
      key: 'epsContribution',
      name: 'EPS贡献（含半数交互项）',
      color: '#008984',
      type: 'bar',
      stack: 'return',
    },
    { key: 'residual', name: '口径差额', color: '#b3bbc5', type: 'bar', stack: 'return' },
    { key: 'returnPct', name: '实际价格回报', color: '#171717' },
  ];
  const fmt = (v: any, n = 1) =>
    v == null || !Number.isFinite(Number(v))
      ? '—'
      : Number(v).toLocaleString('zh-CN', { minimumFractionDigits: n, maximumFractionDigits: n });
  const tone = (v: any) =>
    v == null ? '' : Number(v) > 0 ? 'positive' : Number(v) < 0 ? 'negative' : '';
  const mean = (rows: any[], key: string) => {
    const vs = rows.filter((r) => r[key] != null);
    return vs.length ? vs.reduce((s, r) => s + Number(r[key]), 0) / vs.length : null;
  };
  const monthlyValues = (m: number) =>
    months.value
      .map((r: any) => r.months[String(m)])
      .filter((v: any) => v != null)
      .map(Number);
  const monthSample = (m: number) => monthlyValues(m).length;
  const winRate = (m: number) => {
    const v = monthlyValues(m);
    return v.length ? (v.filter((x: number) => x > 0).length / v.length) * 100 : null;
  };
  const monthStats = computed(() => {
    const vs = months.value
        .flatMap((r: any) =>
          Object.entries(r.months)
            .filter(([, v]) => v != null)
            .map(([m, v]) => ({ date: r.year + '-' + m.padStart(2, '0'), value: Number(v) * 100 })),
        )
        .sort((a: any, b: any) => a.value - b.value),
      n = vs.length;
    return {
      median: n ? (vs[Math.floor((n - 1) / 2)].value + vs[Math.floor(n / 2)].value) / 2 : null,
      best: vs.at(-1),
      worst: vs[0],
    };
  });
  const heat = (v: any) =>
    v == null
      ? {}
      : {
          background:
            Number(v) >= 0
              ? `rgba(0,117,117,${Math.min(0.9, 0.14 + Math.abs(Number(v)) * 4)})`
              : `rgba(178,55,63,${Math.min(0.9, 0.14 + Math.abs(Number(v)) * 4)})`,
          color: Math.abs(Number(v)) > 0.045 ? 'white' : '#17324d',
        };
  const sourceKey = computed(() =>
    view.value === 'drivers'
      ? 'sp_drivers'
      : view.value === 'monthly'
      ? 'sp_monthly'
      : 'sp_drawdowns',
  );
  const updated = computed(
    () =>
      data.value?.[sourceKey.value]?.updated ||
      data.value?.sp_drawdowns?.annual?.at(-1)?.year_end_date ||
      '—',
  );
  const sourceLink = computed(
    () => data.value?.[sourceKey.value]?._canonical || 'https://historyofmarket.com/',
  );
</script>
<style scoped>
  .sp-research {
    min-width: 0;
    margin-top: 24px;
    padding: 20px;
    border: 1px solid #dce5ef;
    border-radius: 14px;
    background: #fff;
    color: #17324d;
  }

  header,
  nav,
  .controls,
  footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }

  header {
    justify-content: space-between;
  }

  h2 {
    margin: 0;
    font-size: 20px;
  }

  h3 {
    font-size: 18px;
  }

  p {
    color: #71869c;
    font-size: 12px;
    line-height: 1.8;
  }

  nav,
  .controls {
    margin: 18px 0;
  }

  button,
  select {
    padding: 6px 11px;
    border: 1px solid #dce5ef;
    border-radius: 6px;
    background: #fff;
    color: #37658c;
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    border-color: #a9c4ed;
    background: #eaf2ff;
  }

  .controls {
    font-size: 12px;
  }

  .summary {
    display: flex;
    flex-wrap: wrap;
    margin: 18px 0;
    padding: 16px 0;
    border-top: 1px solid #dce5ef;
    border-bottom: 1px solid #dce5ef;
  }

  .summary article {
    flex: 1;
    min-width: 130px;
    padding: 0 14px;
    border-right: 1px solid #e2e9f0;
  }

  .summary span,
  .summary small {
    display: block;
    color: #70839a;
    font-size: 12px;
  }

  .summary b {
    display: block;
    margin: 7px 0;
    font-size: 23px;
  }

  .table-scroll {
    max-height: 600px;
    margin-top: 20px;
    overflow: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    white-space: nowrap;
  }

  th,
  td {
    padding: 10px 12px;
    border-bottom: 1px solid #e1e8f0;
    text-align: right;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  thead {
    position: sticky;
    z-index: 1;
    top: 0;
    background: #f6f9fc;
  }

  .driver-tag {
    padding: 3px 6px;
    border: 1px solid #b9ccdc;
    border-radius: 3px;
  }

  .monthly {
    min-width: 950px;
  }

  .monthly td span {
    display: block;
    padding: 5px 8px;
    border-radius: 3px;
  }

  .monthly td {
    padding: 4px;
  }

  .positive {
    color: #008577;
  }

  .negative {
    color: #bc424c;
  }

  .education {
    margin: 20px 0;
    padding: 18px;
    border: 1px solid #e0e8f1;
    border-radius: 10px;
    background: #f7fafd;
  }

  .education p {
    color: #426079;
  }

  .notice {
    color: #a87811;
  }

  footer {
    margin-top: 20px;
    color: #7b8b9d;
    font-size: 11px;
  }

  a {
    color: #3876a4;
  }
</style>
