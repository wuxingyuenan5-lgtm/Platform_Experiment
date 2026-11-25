<template>
  <div class="analysis-stack" data-testid="execution-research">
    <section class="analysis-panel"
      ><header class="analysis-head"
        ><div
          ><h2>从屏幕价差，到可兑现空间</h2
          ><p>研究报价同步、目标数量与持有成本；CFD 滑点只作预算，不能用永续盘口代替。</p></div
        ><div class="analysis-pills"
          ><button :aria-pressed="input.direction === 'short'" @click="$emit('direction', 'short')"
            >空价差</button
          ><button :aria-pressed="input.direction === 'long'" @click="$emit('direction', 'long')"
            >多价差</button
          ></div
        ></header
      ><div class="analysis-controls"
        ><label
          >研究数量 / oz<input
            :value="input.quantity"
            type="number"
            min="0.1"
            max="100"
            step="0.1"
            aria-label="兑现研究数量"
            @input="$emit('quantity', ($event.target as HTMLInputElement).value)" /></label
        ><label
          >允许报价时差<select v-model.number="maxSkew" aria-label="允许报价时差"
            ><option :value="50">50 ms</option
            ><option :value="250">250 ms</option
            ><option :value="1000">1,000 ms</option></select
          ></label
        ><label
          >CFD 单边滑点预算 / 点<input
            v-model.number="cfdSlip"
            type="number"
            min="0"
            max="10"
            step="0.05"
            aria-label="CFD 单边滑点预算" /></label></div
      ><div class="analysis-controls holding-control"
        ><label
          >计划持有期<select
            :value="input.hours"
            aria-label="兑现计划持有期"
            @change="$emit('hours', Number(($event.target as HTMLSelectElement).value))"
            ><option :value="2">2 小时</option
            ><option :value="8">8 小时</option
            ><option :value="24">24 小时</option
            ><option :value="72">72 小时</option></select
          ></label
        ></div
      ><div class="quote-quality"
        ><div
          ><span>两腿报价时间差</span
          ><strong>{{ quoteSkew.toLocaleString() }} <small>ms</small></strong></div
        ><div
          ><span>CFD 状态</span><strong>{{ state.valid ? '可报价' : '报价无效' }}</strong></div
        ><div
          ><span>按所选同步要求</span
          ><strong :class="qualified ? 'pass' : 'fail'">{{
            qualified ? '满足' : '不满足'
          }}</strong></div
        ><div
          ><span>永续样例盘口总深度</span><strong>{{ bookSize }} <small>oz</small></strong></div
        ></div
      ><p class="analysis-caption"
        >合成快照的正常时间差为
        120ms；休市情景使用停滞报价。报价同步是筛选条件，不能证明双腿原子成交。</p
      ></section
    >
    <div class="analysis-two"
      ><section class="analysis-panel"
        ><header class="analysis-head"
          ><div
            ><h2>数量上去，价格还在吗</h2
            ><p
              >{{ input.direction === 'short' ? '永续卖出，逐档吃买盘' : '永续买入，逐档吃卖盘' }} ·
              同时检查退出代价</p
            ></div
          ></header
        ><DemoChart :option="depthOption" label="永续合成盘口累计数量及相对最优报价偏移" /><div
          class="analysis-note"
          >CFD 不提供这里可验证的集中订单簿。当前采用每边
          {{ fmt(cfdSlip) }} 点滑点预算；退出时沿用相同深度和点差仅为情景假设。</div
        ></section
      ><section class="analysis-panel"
        ><header class="analysis-head"
          ><div
            ><h2>目标数量下的经济账</h2
            ><p
              >{{ input.quantity }} oz · {{ input.hours }} 小时 · 修复到 {{ fmt(input.target) }}</p
            ></div
          ></header
        ><div class="capacity-result"
          ><span>按最优报价估计 / U·oz</span><strong>{{ usable ? signed(quoted.net) : '—' }}</strong
          ><span>按数量与滑点预算估计 / U·oz</span
          ><strong
            data-testid="depth-adjusted-net"
            :class="adjusted && adjusted.net >= 0 ? 'pass' : 'fail'"
            >{{ adjusted ? signed(adjusted.net) : '—' }}</strong
          ><span>{{
            !qualified
              ? '报价资格不足，停止净空间估计'
              : !sweep.complete
              ? `样例盘口只覆盖 ${fmt(sweep.filled)} oz，不能给出全量成交均价`
              : !valid
              ? '回归依据或输入不足，停止机会估计'
              : `整笔净空间 ${adjusted ? signed(adjusted.total) : '—'} U`
          }}</span></div
        ><p class="analysis-caption"
          >数量滑点替换原“额外执行损耗”，不重复叠加。往返额外损耗 = 2 × 永续吃盘偏移 + 2 × CFD
          单边滑点预算；资金费、库存费与显性费用沿用所选假设。</p
        ></section
      ></div
    >
    <section class="analysis-panel"
      ><header class="analysis-head"
        ><div
          ><h2>容量阶梯</h2><p>超出样例盘口容量时保留缺失，不用已成交部分冒充全量均价</p></div
        ></header
      ><div class="analysis-table-wrap"
        ><table class="analysis-table"
          ><thead
            ><tr
              ><th>目标数量 / oz</th><th>盘口覆盖 / oz</th><th>永续单边偏移 / 点</th
              ><th>往返额外损耗 / U·oz</th><th>净空间 / U·oz</th><th>整笔 / U</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in capacity" :key="row.quantity"
              ><td>{{ row.quantity }}</td
              ><td>{{ fmt(row.sweep.filled) }} / {{ row.quantity }}</td
              ><td>{{ fmt(row.impact) }}</td
              ><td>{{ fmt(row.cost) }}</td
              ><td :class="row.net !== null && row.net >= 0 ? 'positive' : 'negative'">{{
                fmt(row.net)
              }}</td
              ><td>{{ fmt(row.net === null ? null : row.net * row.quantity) }}</td></tr
            ></tbody
          ></table
        ></div
      ></section
    >
    <section class="analysis-panel"
      ><header class="analysis-head"
        ><div
          ><h2>修复幅度 × 等待时间</h2
          ><p>假设向所选方向有利移动，按目标数量计入成本；每格为净空间 U/oz</p></div
        ></header
      ><div class="analysis-table-wrap"
        ><table class="analysis-table net-matrix"
          ><thead
            ><tr
              ><th>有利修复 / 点</th><th v-for="h in holdingHours" :key="h">{{ h }} 小时</th></tr
            ></thead
          ><tbody
            ><tr v-for="repair in [2, 4, 6, 8, 10]" :key="repair"
              ><td>{{ repair }}</td
              ><td
                v-for="h in holdingHours"
                :key="h"
                :class="matrixValue(repair, h) !== null && matrixValue(repair, h)! >= 0 ? 'positive' : 'negative'"
                >{{ fmt(matrixValue(repair, h)) }}</td
              ></tr
            ></tbody
          ></table
        ></div
      ><p class="analysis-caption"
        >资金费在 T+2.5h 起每 8h 结算；库存费在 T+8.5h、32.5h（×3）、56.5h
        计入，均为演示日历。空间并非按持有天数线性变化；未来费率、交易时段与退出深度均可能改变。</p
      ></section
    >
    <section class="analysis-panel"
      ><header class="analysis-head"
        ><div
          ><h2>组合不亏，不代表两侧都轻松</h2
          ><p>盎司配平后的共同黄金冲击，仍会形成单侧资金压力</p></div
        ></header
      ><div class="analysis-table-wrap"
        ><table class="analysis-table"
          ><thead
            ><tr
              ><th>行情冲击</th><th>永续价格损益 / U</th><th>CFD 价格损益 / U</th
              ><th>组合价格损益 / U</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in stress" :key="row.label"
              ><td>{{ row.label }}</td
              ><td :class="row.f >= 0 ? 'positive' : 'negative'">{{
                valid ? signed(row.f) : '—'
              }}</td
              ><td :class="row.c >= 0 ? 'positive' : 'negative'">{{
                valid ? signed(row.c) : '—'
              }}</td
              ><td :class="row.f + row.c >= 0 ? 'positive' : 'negative'">{{
                valid ? signed(row.f + row.c) : '—'
              }}</td></tr
            ></tbody
          ></table
        ></div
      ><p class="analysis-caption"
        >等量匹配，价差冲击全分配到永续腿只为压力算例；未计费用、Carry、保证金档位和余额。两侧浮盈浮亏不能直接抵销各自账户的补充保证金要求。</p
      ></section
    >
    <section class="analysis-panel"
      ><header class="analysis-head"
        ><div
          ><h2>休市重开：跳过的不是零波动</h2
          ><p>直接比较停报前与恢复报价后的价差，不在休市区间补线</p></div
        ></header
      ><div class="analysis-metrics"
        ><div
          ><span>非连续报价边界</span><strong>{{ reopen.length }}</strong
          ><small>合成交易日历内的停报窗口</small></div
        ><div
          ><span>重开变化中位数</span><strong>{{ fmt(reopenStats.median) }}</strong
          ><small>点 · 正数为价差扩大</small></div
        ><div
          ><span>重开绝对变化 P90</span><strong>{{ fmt(reopenAbs.p90) }}</strong
          ><small>点 · 不代表可用止损宽度</small></div
        ><div
          ><span>较长停报窗口</span
          ><strong>{{ reopen.filter((r) => r.gapHours >= 24).length }}</strong
          ><small>观测间距至少 24 小时</small></div
        ></div
      ><div class="analysis-table-wrap reopen-table"
        ><table class="analysis-table"
          ><thead
            ><tr
              ><th>最后报价 → 恢复报价 / 北京</th><th>观测间距</th><th>价差变化</th
              ><th>停报前点差</th><th>重开点差</th></tr
            ></thead
          ><tbody
            ><tr v-for="row in [...reopen].reverse().slice(0, 8)" :key="row.after"
              ><td>{{ date(row.before) }} → {{ date(row.after) }}</td
              ><td>{{ row.gapHours }}h</td><td>{{ signed(row.change) }}</td
              ><td>{{ fmt(row.beforeWidth) }}</td
              ><td>{{ fmt(row.afterWidth) }}</td></tr
            ></tbody
          ></table
        ></div
      ><p class="analysis-caption"
        >连续 24
        小时事件样本可能因休市而为空；这里另看重开跳变，不把两端价格之间的未知路径当作平稳持有。真实数据还需区分计划休市、掉线与数据缺失；本页边界来自合成日历。</p
      ></section
    >
  </div>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import DemoChart from './DemoChart.vue';
  import {
    economics,
    SCENARIOS,
    HOUR,
    type Observation,
    type CostInput,
    type Scenario,
    type Direction,
  } from './marketDemo';
  import { demoBook, sweepBook, reopenEvents, describe } from './statistics';

  const props = defineProps<{
    input: CostInput;
    scenario: Scenario;
    valid: boolean;
    rows: Observation[];
  }>();
  defineEmits<{
    (e: 'direction', value: Direction): void;
    (e: 'quantity', value: string): void;
    (e: 'hours', value: number): void;
  }>();
  const reopen = computed(() => reopenEvents(props.rows));
  const reopenStats = computed(() => describe(reopen.value.map((r) => r.change)));
  const reopenAbs = computed(() => describe(reopen.value.map((r) => Math.abs(r.change))));
  const date = (time: number) =>
    new Date(time + 8 * HOUR).toISOString().slice(5, 16).replace('T', ' ');
  const maxSkew = ref(250),
    cfdSlip = ref<number | string>(0.15);
  const state = computed(() => SCENARIOS[props.scenario]);
  const quoteSkew = computed(() => (state.value.valid ? 120 : 300_000));
  const qualified = computed(() => state.value.valid && quoteSkew.value <= maxSkew.value);
  const usable = computed(
    () =>
      props.valid &&
      qualified.value &&
      typeof cfdSlip.value === 'number' &&
      Number.isFinite(cfdSlip.value) &&
      cfdSlip.value >= 0 &&
      cfdSlip.value <= 10,
  );
  const book = computed(() => demoBook(props.input.direction, props.scenario === 'liquidity'));
  const bookSize = computed(() => book.value.reduce((s, l) => s + l.quantity, 0));
  const sweep = computed(() => sweepBook(book.value, props.input.quantity));
  const impact = computed(() =>
    sweep.value.vwap === null ? null : Math.abs(sweep.value.vwap - book.value[0].price),
  );
  const extraCost = computed(() =>
    impact.value === null ? null : 2 * impact.value + 2 * Number(cfdSlip.value),
  );
  const quoted = computed(() => economics(props.input));
  const adjusted = computed(() =>
    usable.value && extraCost.value !== null
      ? economics({ ...props.input, buffer: extraCost.value })
      : null,
  );
  const capacity = computed(() =>
    [...new Set([1, 5, 10, 20, props.input.quantity])]
      .filter((q) => q > 0 && Number.isFinite(q))
      .sort((a, b) => a - b)
      .map((quantity) => {
        const s = sweepBook(book.value, quantity),
          impact = s.vwap === null ? null : Math.abs(s.vwap - book.value[0].price);
        const cost =
          impact === null || !usable.value ? null : 2 * impact + 2 * Number(cfdSlip.value);
        return {
          quantity,
          sweep: s,
          impact,
          cost,
          net: cost === null ? null : economics({ ...props.input, quantity, buffer: cost }).net,
        };
      }),
  );
  const holdingHours = [2, 8, 24, 72];
  const matrixValue = (repair: number, hours: number) =>
    usable.value && extraCost.value !== null
      ? economics({
          ...props.input,
          target: props.input.mid + (props.input.direction === 'long' ? 1 : -1) * repair,
          hours,
          buffer: extraCost.value,
        }).net
      : null;
  const stress = computed(() => {
    const d = props.input.direction === 'long' ? 1 : -1,
      q = props.input.quantity;
    return [
      { label: '黄金共同上涨 100 点', gold: 100, spread: 0 },
      { label: '黄金共同下跌 100 点', gold: -100, spread: 0 },
      { label: '黄金共同上涨 300 点', gold: 300, spread: 0 },
      { label: '价差向不利方向变化 5 点', gold: 0, spread: -5 * d },
    ].map((r) => ({ label: r.label, f: d * q * (r.gold + r.spread), c: -d * q * r.gold }));
  });
  const fmt = (v: unknown, digits = 2) =>
    typeof v === 'number' && Number.isFinite(v) ? v.toFixed(digits) : '—';
  const signed = (v: number) => `${v > 0 ? '+' : ''}${fmt(v)}`;
  const depthOption = computed(() => {
    let cumulative = 0;
    return {
      grid: { left: 48, right: 24, top: 35, bottom: 40 },
      tooltip: { trigger: 'axis', confine: true },
      textStyle: { fontSize: 11, color: '#75879c' },
      xAxis: { type: 'value', name: '累计 oz' },
      yAxis: { type: 'value', name: '偏离最优价 / 点' },
      series: [
        {
          name: '逐档深度',
          type: 'line',
          step: 'start',
          data: book.value.map((l) => [
            (cumulative += l.quantity),
            Math.abs(l.price - book.value[0].price),
          ]),
          itemStyle: { color: '#438a91' },
          areaStyle: { color: '#438a91', opacity: 0.08 },
          markLine: {
            symbol: 'none',
            label: { formatter: '目标数量', position: 'insideEndTop' },
            lineStyle: { color: '#b38b46' },
            data: [{ xAxis: props.input.quantity }],
          },
        },
      ],
    };
  });
</script>
<style scoped lang="less">
  @import './researchPanels.less';

  .holding-control,
  .reopen-table {
    margin-top: 18px;
  }

  .quote-quality {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 18px;
    margin-top: 24px;
  }

  .quote-quality > div {
    display: grid;
    gap: 10px;
  }

  .quote-quality span,
  .quote-quality small {
    color: #7b8da4;
    font-size: 11px;
  }

  .quote-quality strong {
    color: #3f5f83;
    font-size: 21px;
    font-weight: 500;
  }

  .pass {
    color: #178579 !important;
  }

  .fail {
    color: #bd5a5a !important;
  }

  .capacity-result {
    display: grid;
    gap: 12px;
    margin: 28px 0;
  }

  .capacity-result span {
    color: #7f8ea3;
    font-size: 12px;
  }

  .capacity-result strong {
    color: #60748e;
    font-size: 28px;
    font-weight: 500;
  }

  .capacity-result strong[data-testid] {
    padding-top: 15px;
    border-top: 1px solid #e3eaf2;
    font-size: 38px;
  }

  .net-matrix td.positive {
    background: #f4faf8;
  }

  .net-matrix td.negative {
    background: #fcf7f6;
  }

  @media (max-width: 700px) {
    .quote-quality {
      grid-template-columns: 1fr 1fr;
    }
  }
</style>
