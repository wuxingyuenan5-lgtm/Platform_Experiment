<template>
  <div class="market-lab" data-testid="cross-spread-market-demo">
    <header class="lab-header">
      <div
        ><div class="eyebrow">XAUTUSDT 永续 <span>×</span> XAUUSD CFD</div
        ><h1>价差研究台 <span class="sample-tag">演示数据</span></h1
        ><p>从价格偏离，看到扣除成本后剩下的空间。</p></div
      >
      <div class="snapshot"
        ><strong>2026.11.05 · 21:30</strong><span>北京时间 · 合成行情快照</span></div
      >
    </header>

    <div class="lab-toolbar">
      <div class="scenario-picker" aria-label="行情情景"
        ><button
          v-for="(item, key) in SCENARIOS"
          :key="key"
          :aria-pressed="scenario === key"
          @click="scenario = key"
          >{{ item.label }}</button
        ></div
      >
      <label
        >研究窗口
        <select v-model.number="days" aria-label="研究窗口"
          ><option :value="7">近 7 天</option
          ><option :value="30">近 30 天</option
          ><option :value="90">近 90 天</option></select
        ></label
      >
    </div>

    <section
      class="decision-strip"
      :class="{ caution: scenario !== 'dislocation' }"
      aria-live="polite"
    >
      <div class="decision-mark">{{ scenario === 'dislocation' ? '观察' : '复核' }}</div>
      <div
        ><h2>{{ state.reason }}</h2
        ><p>{{
          scenario === 'closed'
            ? '保留历史研究；当前报价不参与机会判断。'
            : scenario === 'repricing'
            ? '价格归因与旧样本分布不一致，统计尾部不等于可修复空间。'
            : `当前美国时段 · 历史参照中枢 ${fmt(target)} 点 · 报价价差与研究中枢分开观察。`
        }}</p></div
      >
      <span class="state-badge">{{
        state.valid
          ? scenario === 'repricing'
            ? '回归依据待复核'
            : '两腿报价同步'
          : '一侧不可交易'
      }}</span>
    </section>

    <div class="quote-ribbon">
      <div
        ><span>中间价差 F − C</span
        ><strong>{{ state.valid ? fmt(state.mid) : '—' }} <small>点</small></strong
        ><em>{{
          state.valid ? `${fmt((state.mid / 4000) * 10000)} bps · 参考黄金 4,000` : 'CFD 报价停滞'
        }}</em></div
      >
      <div
        ><span>买价差 A <small>买永续 / 卖 CFD</small></span
        ><strong>{{ state.valid ? fmt(state.mid + state.width / 2) : '—' }}</strong
        ><em>开多 / 平空的报价口径</em></div
      >
      <div
        ><span>卖价差 B <small>卖永续 / 买 CFD</small></span
        ><strong>{{ state.valid ? fmt(state.mid - state.width / 2) : '—' }}</strong
        ><em>开空 / 平多的报价口径</em></div
      >
      <div
        ><span>相对同类时段的偏离</span
        ><strong>{{ state.valid ? fmt(zScore) : '—' }} <small>稳健 Z</small></strong
        ><em>历史分位 {{ state.valid ? fmt(percentile, 1) + '%' : '—' }} · 非入场信号</em></div
      >
    </div>

    <nav class="research-tabs" aria-label="研究视角"
      ><button
        v-for="item in tabs"
        :key="item.key"
        :aria-pressed="tab === item.key"
        @click="tab = item.key"
        >{{ item.label }}</button
      ></nav
    >

    <div v-if="tab === 'space'" class="space-grid">
      <section class="lab-panel chart-panel">
        <header class="panel-heading"
          ><div><h2>偏离多远，才有研究价值</h2><p>中间价差、历史区间与两方向成本门槛</p></div
          ><select v-model="unit" aria-label="图表单位"
            ><option value="points">价差点</option
            ><option value="bps">相对价差 bps</option></select
          ></header
        >
        <DemoChart
          :option="spreadOption"
          label="合成价差历史、同类时段 P10 至 P90 区间和成本门槛"
        />
        <div class="chart-foot"
          ><span>中枢 {{ fmt(target) }}</span
          ><span>P10 / P90 {{ fmt(model.p10) }} / {{ fmt(model.p90) }}</span
          ><span>参照样本 {{ model.n }} 个</span></div
        >
        <p class="caption"
          >区间取前 60%
          样本中的美国时段；虚线为所选持有期的零净空间边界。固定历史参照不等于公允价值；休市与缺口断线。</p
        >
        <div class="direction-cards">
          <button
            v-for="side in sides"
            :key="side.key"
            :aria-pressed="direction === side.key"
            @click="chooseDirection(side.key)"
            ><span
              >{{ side.label }}<small>{{ side.legs }}</small></span
            ><strong :class="valueClass(validEconomics ? estimates[side.key].net : null)"
              >{{ validEconomics ? signed(estimates[side.key].net) : '—'
              }}<small>U / oz</small></strong
            ></button
          >
        </div>
      </section>
      <section class="lab-panel economics-panel">
        <header class="panel-heading"
          ><div
            ><h2>这次修复，值多少</h2
            ><p>{{
              direction === 'short' ? '空价差 · 卖永续 / 买 CFD' : '多价差 · 买永续 / 卖 CFD'
            }}</p></div
          ><span class="small-tag">情景测算</span></header
        >
        <div class="economics-inputs"
          ><label
            >数量 / oz<input
              v-model.number="quantity"
              type="number"
              min="0.1"
              max="100"
              step="0.1"
              aria-label="研究数量" /></label
          ><label
            >持有期<select v-model.number="hours" aria-label="持有期"
              ><option :value="2">2 小时</option
              ><option :value="8">8 小时</option
              ><option :value="24">24 小时</option
              ><option :value="72">72 小时</option></select
            ></label
          ></div
        >
        <p v-if="!validInputs" class="input-error" role="alert"
          >请输入范围内的有限数值；数量须为 0.1–100 oz。</p
        >
        <div class="pnl-waterfall">
          <div v-for="item in cashRows" :key="item.label"
            ><span>{{ item.label }}</span
            ><div class="bar-track"
              ><i
                :class="{ negative: item.value < 0 }"
                :style="{
                  width: `${
                    validEconomics ? Math.min(100, (Math.abs(item.value) / 12) * 100) : 0
                  }%`,
                }"
              ></i></div
            ><strong>{{ validEconomics ? signed(item.value) : '—' }}</strong></div
          >
        </div>
        <div class="net-result"
          ><div
            ><span>情景净空间 / oz</span
            ><strong :class="valueClass(validEconomics ? result.net : null)"
              >{{ validEconomics ? signed(result.net) : '—' }} <small>U</small></strong
            ></div
          ><div
            ><span>整笔 {{ validInputs ? quantity : '—' }} oz</span
            ><b data-testid="demo-total"
              >{{ validEconomics ? signed(result.total) : '—' }} U</b
            ></div
          ></div
        >
        <p class="caption">{{
          !state.valid
            ? '休市期间不提供当前净空间估计。'
            : scenario === 'repricing'
            ? '旧中枢修复假设失效，净空间暂不评估。'
            : `至少修复 ${fmt(result.breakEven)} 点才覆盖成本；预估退出报价 ${fmt(
                result.exit,
              )}。报价损耗已计入毛空间，不重复扣除。`
        }}</p>
        <details class="assumptions"
          ><summary>调整成本假设与结算事件</summary>
          <div class="assumption-grid"
            ><label
              >永续单边费率 / bp<input
                v-model.number="feeBps"
                type="number"
                min="0"
                max="50"
                step="0.5"
                aria-label="永续单边费率" /></label
            ><label
              >每次资金费率 / bp<input
                v-model.number="fundingBps"
                type="number"
                min="-50"
                max="50"
                step="0.1"
                aria-label="每次资金费率" /></label
            ><label
              >CFD 库存费 / U·oz·次<input
                v-model.number="swap"
                type="number"
                min="-20"
                max="20"
                step="0.1"
                aria-label="CFD 库存费" /></label
            ><label
              >额外损耗 / U·oz<input
                v-model.number="buffer"
                type="number"
                min="0"
                max="20"
                step="0.1"
                aria-label="额外损耗" /></label
          ></div>
          <p
            >费率、4,000 名义单价、CFD 开仓佣金 0.06 U/oz
            与退出点差均为假设；两方向库存费可分别调整。正资金费率下多永续支付、空永续收取。</p
          >
          <ul v-if="result.events.length"
            ><li v-for="(event, i) in result.events" :key="i"
              ><span>T + {{ event.hour }}h · {{ event.label }}</span
              ><strong>{{ signed(event.cash) }} U/oz</strong></li
            ></ul
          ><p v-else>所选期限内没有假设结算事件。</p>
          <p>结算时间及三倍计费仅演示事件计数，不代表实际合约日历。资金费率按所填情景保持不变。</p>
        </details>
      </section>
      <section class="lab-panel full-width"
        ><header class="panel-heading"
          ><div><h2>能否兑现，还要过这三关</h2><p>行情资格与净空间分别判断</p></div></header
        ><div class="checks-grid"
          ><article
            ><span>报价与容量</span
            ><h3>{{
              scenario === 'closed'
                ? 'CFD 报价已停滞'
                : scenario === 'liquidity'
                ? '点差扩大，容量受限'
                : '同步报价，仍需深度验证'
            }}</h3
            ><p>{{
              scenario === 'closed'
                ? '一侧停市时，不把另一侧跳动算成可交易价差。'
                : `两腿合计点差 ${fmt(state.width)} 点。当前只用最优报价，${
                    quantity || '所选'
                  } oz 的实际成交容量未评估。`
            }}</p></article
          ><article
            ><span>持有与事件</span><h3>{{ hours >= 24 ? '跨越库存费结算' : '日内修复窗口' }}</h3
            ><p
              >资金费、CFD 开收盘、三倍计费与重大数据窗口分别核对；黄金方向不替代价差判断。</p
            ></article
          ><article
            ><span>资金与尾部</span><h3>两侧保证金独立承压</h3
            ><p
              >即使组合对冲，黄金同涨 100 点时，{{ quantity || 'Q' }} oz 的一侧浮亏约
              {{ validInputs ? fmt(Number(quantity) * 100, 0) : '—' }}
              U；尚未计入保证金档位变化。</p
            ></article
          ></div
        ></section
      >
    </div>

    <StatisticsPanel
      v-else-if="tab === 'statistics'"
      :rows="rows"
      :current-mid="state.valid ? state.mid : null"
      :current-width="state.width"
    />
    <ExecutionResearchPanel
      v-else-if="tab === 'executionResearch'"
      :input="executionInput"
      :scenario="scenario"
      :valid="validEconomics"
      :rows="rows"
      @direction="chooseDirection"
      @quantity="quantity = $event === '' ? '' : Number($event)"
      @hours="hours = $event"
    />
    <div v-else-if="tab === 'events'" class="events-grid">
      <section class="lab-panel full-width"
        ><header class="panel-heading"
          ><div><h2>极端之后，怎样走回来</h2><p>一轮偏离算一次事件，未回归与观察中断都保留</p></div
          ><label
            >事件时段
            <select v-model="eventSession" aria-label="事件时段"
              ><option value="全部">全部时段</option
              ><option>亚洲</option
              ><option>欧洲</option
              ><option>美国</option></select
            ></label
          ></header
        >
        <div class="event-kpis"
          ><div
            ><span>独立偏离事件</span><strong>{{ eventStats.n }}</strong
            ><small>{{ eventStats.censored }} 次观察中断 / 窗口未结束</small></div
          ><div
            ><span>24h 内触及中枢</span
            ><strong>{{ fmt(eventStats.rate, 1) }}<small>%</small></strong
            ><small>{{ eventStats.reverted }} / {{ eventStats.complete }} 个完整事件</small></div
          ><div
            ><span>已回归事件耗时 P50</span
            ><strong>{{ fmt(eventStats.hours, 1) }}<small>h</small></strong
            ><small>未回归事件不混入耗时中位数</small></div
          ><div
            ><span>最大不利偏离 P90</span><strong>{{ fmt(eventStats.mae) }}<small>点</small></strong
            ><small>完整事件 · 样本尾部描述</small></div
          ></div
        >
        <p class="caption"
          >前 60% 样本按时段估计中枢与 MAD，后 40% 冻结验证；|稳健 Z| ≥ 2 触发，回到 |Z| &lt; 0.5
          后才重置。目标在触发时冻结，24h 超时，跨休市 /
          缺口中断观察。这里是合成中间价的路径统计，不是净收益胜率。</p
        >
      </section>
      <section class="lab-panel"
        ><header class="panel-heading"
          ><div><h2>多空是否对称</h2><p>价差方向决定回归路径</p></div></header
        ><div class="table-scroll"
          ><table
            ><thead
              ><tr
                ><th>方向</th><th>完整事件</th><th>中枢到达率</th><th>P50 耗时</th
                ><th>P90 不利偏离</th></tr
              ></thead
            ><tbody
              ><tr v-for="side in sides" :key="side.key"
                ><td>{{ side.label }}</td
                ><td>{{ summaryFor(side.key).complete }}</td
                ><td>{{ fmt(summaryFor(side.key).rate, 1) }}%</td
                ><td>{{ fmt(summaryFor(side.key).hours, 1) }}h</td
                ><td>{{ fmt(summaryFor(side.key).mae) }}</td></tr
              ></tbody
            ></table
          ></div
        ><DemoChart :option="distributionOption" label="历史各时段价差分布直方图"
      /></section>
      <section class="lab-panel"
        ><header class="panel-heading"
          ><div><h2>时段改变，正常区间也会变</h2><p>北京时间 · 前 60% 训练样本</p></div></header
        ><div class="session-ranges"
          ><article v-for="s in sessions" :key="s"
            ><div
              ><strong>{{ s }}</strong
              ><span>{{ sessionHours[s] }} · {{ research.centres[s].n }} 个样本</span></div
            ><div class="range-track"
              ><i :style="rangeStyle(research.centres[s].p10, research.centres[s].p90)"></i
              ><b :style="{ left: `${rangePosition(research.centres[s].median)}%` }"></b></div
            ><p
              >P10 {{ fmt(research.centres[s].p10) }}
              <strong>中枢 {{ fmt(research.centres[s].median) }}</strong> P90
              {{ fmt(research.centres[s].p90) }}</p
            ></article
          ></div
        ><div class="research-note"
          ><h3>值得验证的不是一个全时期均值</h3
          ><p
            >比较不同交易时段、波动环境与开收盘窗口的中枢是否迁移。短窗口和小样本只能描述现象，不能据此确认回归规律。</p
          ><p
            >领先滞后需要秒级同步报价；本演示的 30 分钟样本不提供秒级领先关系或成交速度结论。</p
          ></div
        ></section
      >
      <section class="lab-panel full-width"
        ><header class="panel-heading"
          ><div
            ><h2>偏离事件明细</h2
            ><p>最近 {{ Math.min(12, filteredEvents.length) }} 次 · 可逐笔核对路径</p></div
          ></header
        ><div class="table-scroll"
          ><table
            ><thead
              ><tr
                ><th>发生时间 / 北京</th><th>时段</th><th>方向</th><th>起始 → 目标</th
                ><th>观察时长</th><th>最大不利偏离</th><th>结果</th></tr
              ></thead
            ><tbody
              ><tr v-for="event in recentEvents" :key="event.time"
                ><td>{{ dateLabel(event.time) }}</td
                ><td>{{ event.session }}</td
                ><td>{{ event.direction === 'long' ? '多价差' : '空价差' }}</td
                ><td>{{ fmt(event.entry) }} → {{ fmt(event.target) }}</td
                ><td>{{ fmt(event.hours, 1) }}h</td><td>{{ fmt(event.mae) }} 点</td
                ><td
                  ><span :class="['event-status', event.status]">{{
                    statusLabels[event.status]
                  }}</span></td
                ></tr
              ><tr v-if="!recentEvents.length"
                ><td colspan="7" class="empty-cell"
                  >此窗口没有满足条件的独立事件，扩大窗口后再比较。</td
                ></tr
              ></tbody
            ></table
          ></div
        ></section
      >
      <EventPathsPanel class="full-width" :rows="rows" :events="filteredEvents" />
    </div>

    <div v-else class="attribution-grid">
      <section class="lab-panel"
        ><header class="panel-heading"
          ><div
            ><h2>同样的价差，不同的修复逻辑</h2><p>四项价格归因 · 当前水平，非四份额外收益</p></div
          ></header
        ><DemoChart
          :option="attributionOption"
          label="价差四项归因：永续、代币、汇率桥接和跨市场基差"
        /><div class="attribution-total"
          ><span>合计 F − C</span
          ><strong>{{ state.valid ? fmt(state.mid) + ' 点' : '— · 当前归因不可用' }}</strong></div
        ><p class="caption"
          >F−C = (F−S) + (S−G) + G(1−r) + (Gr−C)。S 为 XAUT 现货参考，G 为黄金 / USDT 参考，r 为
          USD/USDT；本页均为合成分项。真实参考缺失时保留缺失，不倒算补齐。</p
        ></section
      >
      <section class="lab-panel"
        ><header class="panel-heading"
          ><div
            ><h2>什么值得追踪，什么会否定假设</h2><p>让每一项行情对应一个研究问题</p></div
          ></header
        ><div class="hypotheses"
          ><article v-for="item in hypotheses" :key="item.title"
            ><span>{{ item.tag }}</span
            ><div
              ><h3>{{ item.title }}</h3
              ><p>{{ item.question }}</p
              ><small>{{ item.failure }}</small></div
            ></article
          ></div
        ></section
      >
      <section class="lab-panel full-width"
        ><header class="panel-heading"
          ><div
            ><h2>敏感度：变一点，影响多少</h2
            ><p
              >{{ direction === 'short' ? '空价差' : '多价差' }} · {{ quantity }} oz · 研究平价 U
              口径</p
            ></div
          ></header
        ><div class="sensitivity-grid"
          ><article
            ><span>价差再扩大 1 点</span
            ><strong
              >{{
                validInputs ? signed((direction === 'long' ? 1 : -1) * Number(quantity)) : '—'
              }}
              U</strong
            ><p>方向与数量共同决定</p></article
          ><article
            ><span>资金费率增加 1 bp / 次</span
            ><strong
              >{{
                validInputs
                  ? signed(((direction === 'short' ? 1 : -1) * 4000 * Number(quantity)) / 10000)
                  : '—'
              }}
              U</strong
            ><p>按假设名义价 4,000 换算</p></article
          ><article
            ><span>额外执行损耗增加 0.1 点</span
            ><strong>{{ validInputs ? signed(-0.1 * Number(quantity)) : '—' }} U</strong
            ><p>尚未计入报价的损耗预算</p></article
          ><article
            ><span>两腿失配 0.1 oz，黄金涨 100</span><strong>±10.00 U</strong
            ><p>单列对冲偏差，不算价差收益</p></article
          ></div
        ></section
      >
    </div>
    <footer class="lab-footer"
      ><span
        >研究口径：F − C 直接相减；1 点 × 1 oz = 1 U 为平价假设。全部行情与费率为合成示例。</span
      ><a
        href="https://github.com/wuxingyuenan5-lgtm/strategy-research/blob/main/cross_venue_spread/README.md"
        target="_blank"
        rel="noopener noreferrer"
        >策略研究手册 ↗</a
      ></footer
    >
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import DemoChart from './DemoChart.vue';
  import StatisticsPanel from './StatisticsPanel.vue';
  import EventPathsPanel from './EventPathsPanel.vue';
  import ExecutionResearchPanel from './ExecutionResearchPanel.vue';
  import {
    HISTORY,
    HOUR,
    SNAPSHOT,
    SCENARIOS,
    study,
    economics,
    eventSummary,
    type Direction,
    type Scenario,
    type Session,
    type CostInput,
  } from './marketDemo';

  const scenario = ref<Scenario>('dislocation'),
    days = ref(30),
    tab = ref('space'),
    unit = ref('points');
  const direction = ref<Direction>('short'),
    quantity = ref<number | string>(5),
    hours = ref(8);
  const feeBps = ref<number | string>(5.5),
    fundingBps = ref<number | string>(1),
    buffer = ref<number | string>(0.3);
  const swaps = ref<Record<Direction, number | string>>({ long: 0.2, short: -0.8 });
  const swap = computed({
    get: () => swaps.value[direction.value],
    set: (value) => {
      swaps.value[direction.value] = value;
    },
  });
  const eventSession = ref('全部');
  const sessions: Session[] = ['亚洲', '欧洲', '美国'];
  const sessionHours = { 亚洲: '08–16h', 欧洲: '16–21h', 美国: '21–08h' };
  const tabs = [
    { key: 'space', label: '价差与净空间' },
    { key: 'statistics', label: '统计分析' },
    { key: 'events', label: '回归与时段' },
    { key: 'executionResearch', label: '兑现与持有' },
    { key: 'attribution', label: '来源与失效条件' },
  ];
  const sides: { key: Direction; label: string; legs: string }[] = [
    { key: 'short', label: '空价差', legs: '卖永续 · 买 CFD' },
    { key: 'long', label: '多价差', legs: '买永续 · 卖 CFD' },
  ];
  const state = computed(() => SCENARIOS[scenario.value]);
  const rows = computed(() => HISTORY.filter((r) => r.time >= SNAPSHOT - days.value * 24 * HOUR));
  const research = computed(() => study(rows.value));
  const model = computed(() => research.value.centres['美国']);
  const target = computed(() => model.value.median ?? 0);
  const zScore = computed(() =>
    model.value.scale ? (state.value.mid - target.value) / model.value.scale : null,
  );
  const percentile = computed(() => {
    const sample = research.value.training.filter((r) => r.session === '美国');
    return sample.length
      ? (sample.filter((r) => r.mid <= state.value.mid).length / sample.length) * 100
      : null;
  });
  const validNumber = (value: number | string, min: number, max: number) =>
    typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max;
  const validInputs = computed(
    () =>
      validNumber(quantity.value, 0.1, 100) &&
      validNumber(feeBps.value, 0, 50) &&
      validNumber(fundingBps.value, -50, 50) &&
      validNumber(buffer.value, 0, 20) &&
      Object.values(swaps.value).every((v) => validNumber(v, -20, 20)),
  );
  const validEconomics = computed(
    () =>
      validInputs.value &&
      state.value.valid &&
      scenario.value !== 'repricing' &&
      model.value.n >= 20,
  );
  const estimates = computed(
    () =>
      Object.fromEntries(
        sides.map((s) => [
          s.key,
          economics({
            direction: s.key,
            mid: state.value.mid,
            width: state.value.width,
            target: target.value,
            quantity: Number(quantity.value) || 0,
            hours: hours.value,
            feeBps: Number(feeBps.value) || 0,
            fundingBps: Number(fundingBps.value) || 0,
            swap: Number(swaps.value[s.key]) || 0,
            buffer: Number(buffer.value) || 0,
          }),
        ]),
      ) as Record<Direction, ReturnType<typeof economics>>,
  );
  const result = computed(() => estimates.value[direction.value]);
  const executionInput = computed<CostInput>(() => ({
    direction: direction.value,
    mid: state.value.mid,
    width: state.value.width,
    target: target.value,
    quantity: Number(quantity.value) || 0,
    hours: hours.value,
    feeBps: Number(feeBps.value) || 0,
    fundingBps: Number(fundingBps.value) || 0,
    swap: Number(swap.value) || 0,
    buffer: Number(buffer.value) || 0,
  }));
  const cashRows = computed(() => [
    { label: '报价毛空间', value: result.value.price },
    { label: '永续资金费', value: result.value.funding },
    { label: 'CFD 库存费', value: result.value.swap },
    { label: '显性手续费', value: -result.value.fees },
    { label: '额外执行损耗', value: -Number(buffer.value) },
  ]);
  const filteredEvents = computed(() =>
    research.value.events.filter(
      (e) => eventSession.value === '全部' || e.session === eventSession.value,
    ),
  );
  const eventStats = computed(() => eventSummary(filteredEvents.value));
  const recentEvents = computed(() => [...filteredEvents.value].reverse().slice(0, 12));
  const summaryFor = (side: Direction) =>
    eventSummary(filteredEvents.value.filter((e) => e.direction === side));
  const statusLabels = { reverted: '触及中枢', timeout: '24h 未回归', censored: '观察未完整' };
  const fmt = (v: unknown, digits = 2) =>
    typeof v === 'number' && Number.isFinite(v)
      ? v.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })
      : '—';
  const signed = (v: number) => `${v > 0 ? '+' : ''}${fmt(v)}`;
  const valueClass = (v: number | null) =>
    v === null ? '' : v >= 0 ? 'positive-text' : 'negative-text';
  const chooseDirection = (side: Direction) => {
    direction.value = side;
  };
  const dateLabel = (time: number) =>
    new Date(time + 8 * HOUR).toISOString().slice(5, 16).replace('T', ' ');
  const rangePosition = (v: number | null) =>
    Math.max(0, Math.min(100, (((v ?? 0) + 10) / 30) * 100));
  const rangeStyle = (lo: number | null, hi: number | null) => ({
    left: `${rangePosition(lo)}%`,
    width: `${rangePosition(hi) - rangePosition(lo)}%`,
  });
  const chartBase = {
    textStyle: {
      fontFamily: 'Segoe UI, Microsoft YaHei, sans-serif',
      color: '#66758a',
      fontSize: 11,
    },
    grid: { left: 48, right: 24, top: 50, bottom: 50 },
    tooltip: { trigger: 'axis', confine: true },
    legend: { top: 5, itemWidth: 16, itemHeight: 8, textStyle: { fontSize: 11 } },
  };
  const spreadOption = computed(() => {
    const factor = unit.value === 'bps' ? 2.5 : 1;
    const points: [number, number | null][] = [];
    rows.value.forEach((r, i) => {
      if (i && r.time - rows.value[i - 1].time > HOUR / 2) points.push([r.time - 1, null]);
      points.push([r.time, r.mid * factor]);
    });
    points.push([SNAPSHOT, state.value.valid ? state.value.mid * factor : null]);
    return {
      ...chartBase,
      xAxis: { type: 'time', axisLabel: { formatter: (v: number) => dateLabel(v).slice(0, 5) } },
      yAxis: {
        type: 'value',
        name: unit.value === 'bps' ? 'bps' : '点',
        splitLine: { lineStyle: { color: '#edf1f6' } },
      },
      dataZoom: [{ type: 'inside' }, { type: 'slider', height: 15, bottom: 6 }],
      series: [
        {
          name: '中间价差',
          type: 'line',
          data: points,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { color: '#3169b3', width: 1.6 },
          itemStyle: { color: '#3169b3' },
          markArea: {
            silent: true,
            itemStyle: { color: '#eaf1fa80' },
            data: [
              [
                { yAxis: (model.value.p10 ?? 0) * factor },
                { yAxis: (model.value.p90 ?? 0) * factor },
              ],
            ],
          },
          markLine: {
            symbol: 'none',
            label: { position: 'insideEndTop', fontSize: 10, formatter: '{b}' },
            data: [
              { name: '历史中枢', yAxis: target.value * factor, lineStyle: { color: '#8190a5' } },
              ...(validEconomics.value
                ? [
                    {
                      name: '空价差成本边界',
                      yAxis: (target.value + estimates.value.short.breakEven) * factor,
                      lineStyle: { color: '#b9802f' },
                    },
                    {
                      name: '多价差成本边界',
                      yAxis: (target.value - estimates.value.long.breakEven) * factor,
                      lineStyle: { color: '#178579' },
                    },
                  ]
                : []),
            ],
          },
        },
      ],
    };
  });
  const distributionOption = computed(() => ({
    ...chartBase,
    xAxis: {
      type: 'category',
      data: Array.from({ length: 16 }, (_, i) => `${i * 2 - 12}~${i * 2 - 10}`),
      axisLabel: { rotate: 35 },
    },
    yAxis: { type: 'value', name: '样本数' },
    series: sessions.map((s, index) => ({
      name: s,
      type: 'bar',
      stack: 'samples',
      itemStyle: { color: ['#8caed8', '#cfad70', '#438a91'][index] },
      data: Array.from(
        { length: 16 },
        (_, i) =>
          research.value.training.filter(
            (r) => r.session === s && r.mid >= i * 2 - 12 && r.mid < i * 2 - 10,
          ).length,
      ),
    })),
  }));
  const attributionOption = computed(() => ({
    ...chartBase,
    xAxis: { type: 'category', data: ['永续基差', '代币基差', '汇率桥接', '跨市场基差'] },
    yAxis: { type: 'value', name: '价差点' },
    series: [
      {
        name: '当前贡献',
        type: 'bar',
        barMaxWidth: 58,
        label: { show: true, position: 'top' },
        data: state.value.valid
          ? state.value.basis.map((value, i) => ({
              value,
              itemStyle: {
                color: ['#3169b3', '#c09645', '#7e91ab', '#438a91'][i],
                borderRadius: [4, 4, 0, 0],
              },
            }))
          : [],
      },
    ],
  }));
  const hypotheses = [
    {
      tag: '信号',
      title: '永续相对现货的短时偏离',
      question: '结合资金费、盘口与成交，检查偏离是否来自暂时杠杆需求。',
      failure: '否定条件：点差扩大或可兑现价差不足以覆盖成本。',
    },
    {
      tag: '归因',
      title: 'XAUT 自身被重新定价',
      question: '代币现货与黄金参考一起观察，识别持续溢折价与产品事件。',
      failure: '否定条件：中枢迁移，旧均值不再是修复目标。',
    },
    {
      tag: '过滤',
      title: '报价同步与可对冲窗口',
      question: '同时看两腿报价时间、CFD 交易状态和目标数量盘口。',
      failure: '否定条件：一侧陈旧、休市或容量不足。',
    },
    {
      tag: '环境',
      title: '黄金波动、宏观事件与保证金',
      question: '用于识别点差扩张和单侧资金压力，评估能否持有到修复。',
      failure: '否定条件：回归所需时间跨越无法承受的事件窗口。',
    },
  ];
</script>

<style scoped lang="less">
  @import './marketDemo.less';
</style>
