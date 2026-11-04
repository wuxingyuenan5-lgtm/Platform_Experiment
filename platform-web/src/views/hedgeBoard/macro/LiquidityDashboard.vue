<template>
  <section class="liquidity-dashboard" aria-label="美元流动性评分与透镜">
    <p v-if="loading" role="status">正在读取流动性评分…</p
    ><p v-if="error" role="alert">{{ error }} <button @click="load">重试</button></p>
    <p v-if="stale" class="notice">部分来源更新未成功，保留上次有效读数；各数据日期分别列示。</p>
    <div v-if="regime" class="headline-grid">
      <article class="card score-card"
        ><h2>DLI 流动性评分</h2
        ><p class="muted"
          >{{ regime.coverage?.indicators }} / {{ regime.coverage?.totalIndicators }} 项指标 ·
          {{ regime.dataAsOf }}</p
        >
        <p v-if="swap" class="swap">Fed互换额度动用 ${{ fmt(swap.value, 2) }}B · {{ swap.date }}</p>
        <div class="score"
          ><div
            ><small>流动性状态</small><strong>{{ label(regime.status) }}</strong></div
          ><b>{{ fmt(regime.percentile5y, 0) }}<small>/100</small></b></div
        >
        <div class="gauge"><i :style="{ left: regime.percentile5y + '%' }"></i></div
        ><div class="scale"
          ><span>宽松 &lt;33</span><span>中性 33–67</span><span>紧缩 &gt;67</span></div
        >
        <p>7日趋势：{{ label(regime.momentum) }} · 原始评分 {{ fmt(regime.compositeScore) }}</p
        ><p
          >结构状态：{{ label(regime.vulnerability) }} · 准备金缓冲 {{ fmt(regime.buffer, 1) }}%</p
        >
        <p>Fed：{{ label(regime.structuralStance) }} · 财政部：{{ label(regime.tacticalPulse) }}</p>
        <div class="actions"
          ><button @click="methodOpen = !methodOpen" :aria-expanded="methodOpen"
            >计算方法是什么？</button
          ><button @click="historyOpen = !historyOpen" :aria-expanded="historyOpen"
            >历史走势</button
          ></div
        >
      </article>
      <article class="card"
        ><h2>流动性评分与今日要点</h2
        ><p class="judgment"
          >当前美元流动性处于{{ label(regime.status) }}状态，趋势{{
            label(regime.momentum)
          }}，评分{{ fmt(regime.percentile5y, 0) }}/100。Fed立场{{
            label(regime.structuralStance)
          }}，财政脉冲{{ label(regime.tacticalPulse) }}；准备金缓冲为{{
            fmt(regime.buffer, 1)
          }}%。</p
        >
        <h3>近期关键变化</h3
        ><div v-for="c in changes" :key="c.id" class="change"
          ><b>{{ c.name }}</b
          ><span>近5次有效观测 {{ c.delta }} {{ c.unit }} · {{ c.date }}</span></div
        >
      </article>
    </div>
    <p v-else-if="!loading">暂无已发布的流动性评分</p>
    <ReferencePlot
      v-if="historyOpen && history.length"
      title="DLI 流动性评分历史"
      :rows="history"
      :lines="[{ key: 'tightnessScore', name: '流动性紧张度', color: '#a77916' }]"
      unit="分"
    />
    <article v-if="methodOpen" class="card education" aria-label="流动性方法科普"
      ><h2>如何理解流动性评分与量·价·构</h2> <h3>钱的数量、价格和流向是三回事</h3
      ><p
        >净流动性＝Fed总资产−TGA−ON RRP。Fed扩表通常增加系统资金；TGA积累现金、ON
        RRP吸收资金通常反向作用。余额是存量，变化才是流量，两者不能混为一谈。</p
      >
      <h3>评分如何形成</h3
      ><p
        >DLI以平滑后的净流动性六个月等效流量为主干，考虑准备金稀缺，并叠加SOFR−IORB、SOFR尾部、SRF和互换额度等融资压力。信用利差、VIX等作为背景观察，不直接进入头条评分。0–100是模型的绝对松紧读数，不是历史百分位；低于33偏宽松，高于67偏紧缩。</p
      >
      <h3>三个透镜如何读</h3
      ><p
        >量：Fed资产流量、准备金缓冲与SRF是否常态使用。价：2年期收益率减EFFR反映政策路径定价，实际利率与期限溢价补充长端成本。构：TGA财政脉冲、RRP缓冲与信用层级分化。三个轴分别读，不相加成一个新分数。</p
      >
      <h3>矩阵与局限</h3
      ><p
        >结构立场是慢变量，财政脉冲是快变量。两者可以同向，也可能一边收紧、一边注入。评分描述当期环境，不能直接推导未来收益；官方数据有发布滞后，历史模型还可能修订。本页保留公开模型读数与其观测日期。</p
      >
      <a href="https://dollarliquidity.com/zh/methodology" target="_blank" rel="noopener noreferrer"
        >完整方法与模型变更 ↗</a
      >
    </article>
    <template v-if="lens"
      ><header class="section-head"
        ><h2>流动性透镜：量·价·构</h2
        ><button @click="methodOpen = !methodOpen" :aria-expanded="methodOpen"
          >如何理解这三个读数？</button
        ></header
      >
      <div class="lens-grid"
        ><article v-for="axis in axes" :key="axis.id" class="card"
          ><h3>{{ axis.icon }} {{ axis.name }}</h3
          ><p class="muted">{{ axis.description }}</p
          ><strong class="stance">{{ label(axis.state) }}</strong>
          <div class="gauge"><i :style="{ left: axis.dial + '%' }"></i></div
          ><div class="scale"
            ><span v-for="s in axis.scale" :key="s">{{ s }}</span></div
          >
          <div class="metrics"
            ><div v-for="m in axis.metrics" :key="m[0]"
              ><span>{{ m[0] }}</span
              ><b>{{ m[1] }}</b></div
            ></div
          >
          <p class="muted">{{ axis.sparkName }}</p>
          <svg class="spark" viewBox="0 0 300 65" role="img" :aria-label="axis.name + '近期走势'">
            <polyline :points="spark(axis.rows)" fill="none" stroke="#6b7d90" stroke-width="1.5" />
          </svg>
          <p class="muted">数据截至 {{ axis.date }}</p>
        </article></div
      >
      <article class="card matrix"
        ><h2>结构立场 × 战术脉冲</h2><p>慢变量与快变量并列观察，标记当前组合。</p
        ><div class="matrix-grid"
          ><span>结构立场 / 战术脉冲</span><span v-for="p in pulses" :key="p">{{ label(p) }}</span>
          <template v-for="s in postures" :key="s"
            ><span>{{ label(s) }}</span
            ><div
              v-for="p in pulses"
              :key="p"
              :class="{
                current: lens.synthesis?.cell?.posture === s && lens.synthesis?.cell?.pulse === p,
              }"
              >{{ label(s) }} · {{ label(p)
              }}<b v-if="lens.synthesis?.cell?.posture === s && lens.synthesis?.cell?.pulse === p"
                >当前</b
              ></div
            ></template
          ></div
        >
        <p
          >结构流量 {{ fmt(lens.quantity.flow) }}，财政流量
          {{ fmt(lens.structure.tgaFlow) }} 万亿美元 / 6个月 · {{ lens.synthesis.dataAsOf }}</p
        ></article
      >
    </template>
    <footer
      ><a href="https://dollarliquidity.com/zh" target="_blank" rel="noopener noreferrer"
        >数据：Dollar Liquidity ↗</a
      ><small>CC BY 4.0 · {{ regime?.dataAsOf || '—' }}</small
      ><button @click="load">刷新</button></footer
    >
  </section>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useReferenceBoard } from '../composables/useReferenceBoard';
  import ReferencePlot from '../components/ReferencePlot.vue';

  const { data, error, loading, load } = useReferenceBoard('liquidity');
  const methodOpen = ref(false),
    historyOpen = ref(false);
  const regime = computed(() => data.value?.dli_regime),
    lens = computed(() => data.value?.dli_lens);
  const history = computed(() => data.value?.dli_history?.dli || []);
  const stale = computed(() => data.value?.sources?.some((s: any) => s.status !== 'ready'));
  const names: Record<string, string> = {
    neutral: '中性',
    loose: '宽松',
    tight: '紧缩',
    deteriorating: '恶化中',
    improving: '改善中',
    stable: '稳定',
    low: '较低',
    elevated: '脆弱',
    high: '较高',
    flat: '持平',
    expanding: '扩张',
    contracting: '缩减',
    draining: '抽走',
    injecting: '注入',
    'pricing-hikes': '定价加息',
    'pricing-cuts': '定价降息',
    rising: '上行',
    falling: '下行',
    thin: '偏紧',
    ample: '充裕',
    depleted: '枯竭',
    compressed: '收窄',
    normal: '正常',
    widening: '走阔',
    tightening: '收紧',
    easing: '宽松',
    'sofr-iorb': 'SOFR−IORB利差',
    srf: 'SRF',
    'fed-swap-lines': 'Fed互换额度',
  };
  const label = (v: any) => (v == null ? '—' : names[v] || v);
  const fmt = (v: any, n = 2) =>
    v == null || !Number.isFinite(Number(v))
      ? '—'
      : Number(v).toLocaleString('zh-CN', { minimumFractionDigits: n, maximumFractionDigits: n });
  const series = (id: string) =>
    (data.value?.['dli_series_' + id]?.data || []).filter((r: any) => r.value != null);
  const swap = computed(() => {
    const r = series('fed-swap-lines').at(-1);
    return r && Number(r.value) > 0 ? r : null;
  });
  const changes = computed(() =>
    [
      ['tga', 'TGA余额', '十亿美元'],
      ['sofr-iorb', 'SOFR−IORB利差', 'bp'],
      ['reserve-buffer', '准备金缓冲', '百分点'],
    ].map(([id, name, unit]) => {
      const rows = series(id),
        last = rows.at(-1),
        prev = rows.at(-6);
      return {
        id,
        name,
        unit,
        date: last?.date || '—',
        delta: prev ? fmt(Number(last.value) - Number(prev.value)) : '—',
      };
    }),
  );
  const pulses = ['injecting', 'flat', 'draining'],
    postures = ['easing', 'flat', 'tightening'];
  const axes = computed(() => {
    if (!lens.value) return [];
    const { quantity: q, price: p, structure: s } = lens.value;
    const rate = new Map(series('effr').map((r: any) => [r.date, Number(r.value)]));
    return [
      {
        id: 'q',
        icon: 'Q',
        name: '量',
        sparkName: 'Fed结构流量（DLI口径）',
        description: '池子在变大还是变小，现金缓冲有多厚。',
        state: q.stance,
        dial: q.dial,
        date: q.dataAsOf,
        scale: ['扩张', '持平', '缩减'],
        rows: history.value.slice(-90).map((r: any) => r.structuralFlow),
        metrics: [
          ['6个月流量', fmt(q.flow) + 'T'],
          ['立场刻度', fmt(q.dial, 0) + '/100'],
          ['准备金缓冲', fmt(q.bufferPct, 1) + '% · ' + label(q.bufferState)],
          [
            'SRF使用占比（90天）',
            q.srfNonZeroShare90d == null ? '—' : fmt(Number(q.srfNonZeroShare90d) * 100, 1) + '%',
          ],
          ['现实化里程碑', q.realized == null ? '—' : q.realized ? '已出现' : '尚未'],
        ],
      },
      {
        id: 'p',
        icon: 'P',
        name: '价',
        sparkName: '2年期 − EFFR（bp）',
        description: '借美元的成本，以及市场在定价什么政策路径。',
        state: p.pathPricing,
        dial: p.pathPricing === 'pricing-hikes' ? 85 : p.pathPricing === 'pricing-cuts' ? 15 : 50,
        date: p.dataAsOf,
        scale: ['定价降息', '中性', '定价加息'],
        rows: series('ust-2y')
          .filter((r: any) => rate.has(r.date))
          .map((r: any) => (Number(r.value) - Number(rate.get(r.date))) * 100),
        metrics: [
          ['2年期 − EFFR', fmt(p.pathSpreadBps) + ' bp'],
          ['10年实际利率', fmt(p.realYieldPct) + '%'],
          ['实际利率趋势', label(p.realYieldTrend)],
          ['10年期限溢价', fmt(p.termPremiumPct) + '%'],
          ['期限溢价水平', p.termPremiumLevel === 'elevated' ? '偏高' : label(p.termPremiumLevel)],
          ['期限溢价趋势', label(p.termPremiumTrend)],
          ['10年−2年利差（背景）', fmt(p.curveContextBps) + ' bp'],
        ],
      },
      {
        id: 's',
        icon: 'S',
        name: '构',
        sparkName: '财政脉冲（DLI口径）',
        description: '财政现金流向与银行、信用市场的层级分化。',
        state: s.fiscalPulse,
        dial: s.fiscalPulse === 'draining' ? 85 : s.fiscalPulse === 'injecting' ? 15 : 50,
        date: s.dataAsOf,
        scale: ['注入', '持平', '抽走'],
        rows: history.value.slice(-90).map((r: any) => r.tacticalFlow),
        metrics: [
          ['TGA流量（6个月折算）', fmt(s.tgaFlow) + 'T'],
          ['隔夜逆回购缓冲', label(s.rrpBufferState)],
          ['隔夜逆回购余额', '$' + fmt(s.rrpBalanceB, 1) + 'B'],
          [
            '短债占比（背景）',
            fmt(s.billsShareContext?.levelPct, 1) +
              '% · ' +
              label(s.billsShareContext?.direction6m),
          ],
          ['融资压力叠加项', fmt(s.fundingOverride)],
          ['主导腿', label(s.dominantFundingLeg)],
          [
            'CP−美债分层',
            fmt(s.cpTbillTiering?.spreadBps) + ' bp · ' + label(s.cpTbillTiering?.state),
          ],
          ['HY−IG分层', fmt(s.hyIgTiering?.spreadBps) + ' bp · ' + label(s.hyIgTiering?.state)],
          [
            '大小行现金分层',
            fmt(s.bankCashTiering?.gapPp) + ' pp · ' + label(s.bankCashTiering?.state),
          ],
        ],
      },
    ];
  });
  function spark(rows: any[]) {
    const vs = rows.filter((v) => v != null && Number.isFinite(Number(v))).map(Number);
    if (!vs.length) return '';
    const lo = Math.min(...vs),
      hi = Math.max(...vs);
    return rows
      .map((v, i) =>
        v == null
          ? null
          : `${(i * 300) / Math.max(1, rows.length - 1)},${
              60 - ((Number(v) - lo) / (hi - lo || 1)) * 55
            }`,
      )
      .filter(Boolean)
      .join(' ');
  }
</script>
<style scoped>
  .liquidity-dashboard {
    min-width: 0;
    margin-bottom: 24px;
    color: #17324d;
  }

  .headline-grid {
    display: grid;
    grid-template-columns: 1.05fr 1fr;
    gap: 20px;
  }

  .card {
    margin-bottom: 16px;
    padding: 22px;
    border: 1px solid #dfe8f1;
    border-radius: 13px;
    background: #fff;
  }

  h2 {
    margin: 0 0 14px;
    font-size: 20px;
  }

  h3 {
    margin: 12px 0;
    font-size: 15px;
  }

  p {
    font-size: 13px;
    line-height: 1.8;
  }

  .muted,
  small {
    color: #72869c;
    font-size: 11px;
  }

  .score {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 20px 0;
    padding: 20px;
    border: 1px solid #e6edf4;
    border-radius: 12px;
  }

  .score strong {
    display: block;
    color: #a77916;
    font-size: 34px;
  }

  .score b {
    color: #a77916;
    font-size: 34px;
  }

  .score small {
    font-size: 12px;
  }

  .gauge {
    position: relative;
    height: 8px;
    margin-top: 24px;
    border-radius: 5px;
    background: linear-gradient(90deg, #4e98bd, #b48d3c, #c84e49);
  }

  .gauge i {
    position: absolute;
    top: -4px;
    width: 16px;
    height: 16px;
    transform: translateX(-50%);
    border: 2px solid white;
    border-radius: 50%;
    background: #a77916;
    box-shadow: 0 0 0 1px #bdc9d3;
  }

  .scale {
    display: flex;
    justify-content: space-between;
    margin: 10px 0 22px;
    color: #7d90a1;
    font-size: 11px;
  }

  .actions,
  .section-head,
  footer {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 14px;
  }

  .section-head {
    justify-content: space-between;
    margin: 24px 0 14px;
  }

  .judgment {
    padding-left: 16px;
    border-left: 2px solid #158267;
    font-size: 17px;
  }

  .change {
    margin: 10px 0;
    padding: 12px 15px;
    border: 1px solid #e7edf5;
    border-radius: 9px;
  }

  .change span {
    display: block;
    margin-top: 7px;
    color: #72869c;
    font-size: 12px;
  }

  .lens-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 16px;
  }

  .stance {
    display: block;
    margin-top: 22px;
    color: #ad7715;
    font-size: 26px;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
  }

  .metrics > div {
    padding: 10px;
    border: 1px solid #e0e9f3;
    border-radius: 6px;
    background: #f6f9fc;
    font-size: 12px;
  }

  .metrics span,
  .metrics b {
    display: block;
  }

  .metrics span {
    margin-bottom: 7px;
    color: #7086a0;
  }

  .spark {
    width: 100%;
    height: 70px;
    margin-top: 20px;
  }

  .matrix-grid {
    display: grid;
    grid-template-columns: 130px repeat(3, minmax(0, 1fr));
    gap: 6px;
    font-size: 12px;
  }

  .matrix-grid > * {
    padding: 17px 8px;
    text-align: center;
  }

  .matrix-grid > div {
    position: relative;
    border: 1px solid #edf1f6;
    background: #f8fafc;
  }

  .matrix-grid .current {
    border-color: #167c66;
    background: #e8f2ee;
  }

  .current b {
    display: block;
    color: #167c66;
  }

  .education {
    background: #f8fbfe;
    line-height: 1.8;
  }

  .swap {
    color: #b74c4c;
    font-size: 12px;
  }

  .notice {
    color: #a57112;
  }

  button {
    padding: 6px 11px;
    border: 1px solid #dbe5ef;
    border-radius: 6px;
    background: #fff;
    color: #37628b;
    cursor: pointer;
  }

  a {
    color: #376f9d;
  }

  footer {
    padding: 10px 0;
    font-size: 12px;
  }

  @media (max-width: 1000px) {
    .headline-grid,
    .lens-grid {
      grid-template-columns: 1fr;
    }

    .matrix-grid {
      grid-template-columns: 80px repeat(3, minmax(0, 1fr));
    }
  }
</style>
