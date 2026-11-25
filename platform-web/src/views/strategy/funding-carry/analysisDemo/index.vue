<template>
  <div class="funding-lab" data-testid="funding-analysis-demo">
    <header class="lab-header">
      <div
        ><div class="eyebrow">FUNDING RESEARCH <span>同所现货多 · 永续空</span></div
        ><h1>行情分析<span class="new-label">新</span></h1
        ><p>研究资费的持续性、基差的代价，以及收益能否兑现。</p></div
      >
      <div class="header-actions"
        ><span class="demo-badge">DEMO · 全部为模拟数据</span
        ><small>情景截面 2026-11-06 00:00 · 北京时间</small
        ><button
          class="text-button"
          @click="methodOpen = !methodOpen"
          :aria-expanded="methodOpen"
          >{{ methodOpen ? '收起口径' : '研究口径 ↗' }}</button
        ></div
      >
    </header>

    <section v-if="methodOpen" class="method-box" aria-label="研究口径">
      <h3>只分析会改变配对收益或生存条件的变量</h3>
      <p
        >资费持续性决定收入；基差变化决定双腿价格损益；OI、主动成交和波动提供状态解释；双腿深度与可用现金约束规模。方向指标只作为背景，持仓收益与下单留在各自工作区。</p
      >
      <p
        >本页为合成情景：交易所、资产名称只用于设计演示，不表示产品已上市或账户可交易。30天历史、下一期假设、深度、费用和事件均非市场实测；未来费率沿所设单期费率延续，结算标记价格暂按入场现货价格不变。没有经过拟合的预测或概率区间。</p
      >
      <p
        >净收益＝资费＋q×（入场中间价基差－退出中间价基差）－四次交易费用－双腿开平盘口成本。此处用中间价及独立成本假设；未来改用可成交
        VWAP 时不得重复扣盘口成本。总资本＝现货资金＋独立合约储备，收益率以总资本为分母。</p
      >
      <p
        >本地基差＝永续－本所现货＝（永续－指数）－（本所现货－指数）。Premium Index
        是独立机制变量，不用 Last
        基差替代。基差上移对现货多／永续空不利；无到期回零假设。1bp＝0.01%。</p
      >
      <div class="source-links"
        ><a
          href="https://github.com/wuxingyuenan5-lgtm/strategy-research/blob/main/funding_rate/README.md"
          target="_blank"
          rel="noreferrer"
          >策略设计 v0.6.0 ↗</a
        ><a
          href="https://bybit-exchange.github.io/docs/v5/market/instrument"
          target="_blank"
          rel="noreferrer"
          >合约规则定义 ↗</a
        ><a
          href="https://bybit-exchange.github.io/docs/v5/market/orderbook"
          target="_blank"
          rel="noreferrer"
          >盘口字段定义 ↗</a
        ></div
      >
    </section>

    <section class="universe-card">
      <div class="section-heading"
        ><div
          ><h2>机会观察池</h2><p>先看配对资格，再比较持有期净收益；所有组合均为同所双腿。</p></div
        ><div class="global-inputs"
          ><label
            >持有期<select v-model.number="days" aria-label="持有期"
              ><option v-for="d in [1, 3, 7, 14]" :key="d" :value="d">{{ d }} 天</option></select
            ></label
          ><label
            >单腿名义金额<select v-model.number="notional" aria-label="单腿名义金额"
              ><option v-for="n in [10000, 50000, 100000, 500000, 1000000]" :key="n" :value="n"
                >{{ money(n) }} USDT</option
              ></select
            ></label
          ></div
        ></div
      >
      <div class="pool-overview"
        ><div
          ><span>可进一步研究</span
          ><strong
            >{{ counts.ready }}<small> / {{ pairs.length }} 组</small></strong
          ></div
        ><div
          ><span>收益或容量暂缓</span><strong>{{ counts.wait }}</strong></div
        ><div
          ><span>产品资格待核验</span><strong>{{ counts.excluded }}</strong></div
        ><p
          >最高费率不等于最佳机会。<br />退出能力不足、产品映射不明时，高资费不能抵消约束。</p
        ></div
      >
      <div class="pool-filters"
        ><div class="pill-group"
          ><button
            v-for="a in ['全部', '加密', '金属', '股票']"
            :key="a"
            :class="{ active: asset === a }"
            :aria-pressed="asset === a"
            @click="asset = a"
            >{{ a }}</button
          ></div
        ><label class="sr-only" for="funding-search">搜索配对</label
        ><input
          id="funding-search"
          v-model="search"
          class="search"
          placeholder="搜索标的 / 交易所"
        /><label
          ><span class="sr-only">交易所</span
          ><select v-model="venue" aria-label="交易所"
            ><option>全部交易所</option
            ><option>Binance</option
            ><option>Bybit</option
            ><option>Bitget</option></select
          ></label
        ><label class="check"><input v-model="onlyReady" type="checkbox" />仅可研究</label
        ><select v-model="sort" aria-label="机会排序"
          ><option value="quality">资格优先 · 净收益排序</option
          ><option value="funding">24h 已结算资费排序</option></select
        ></div
      >
      <div class="table-scroll"
        ><table class="opportunity-table"
          ><thead
            ><tr
              ><th>配对 / 场所</th><th>市场状态</th><th>24h 已结算<small>累计资费 · bp</small></th
              ><th>下一期假设<small>bp / 结算周期</small></th
              ><th>30d 正资费<small>结算次数占比</small></th
              ><th>{{ days }}d 净收益<small>USDT · 基准情景</small></th
              ><th
                >总资本收益率<small>非年化 · {{ days }}d</small></th
              ><th>研究结论</th></tr
            ></thead
          ><tbody
            ><tr
              v-for="row in rows"
              :key="row.pair.id"
              :class="{ selected: selectedId === row.pair.id }"
              :data-pair="row.pair.id"
              ><td
                ><button
                  class="pair-button"
                  :aria-pressed="selectedId === row.pair.id"
                  @click="selectPair(row.pair.id)"
                  ><b>{{ row.pair.symbol }}<span>/ USDT</span></b
                  ><small>{{ row.pair.venue }} · {{ row.pair.asset }}</small></button
                ></td
              ><td
                ><span class="state-dot" :class="stateColor(row.pair)"></span
                >{{ row.pair.state }}</td
              ><td :class="sign(row.stats.day)">{{ bp(row.stats.day) }}</td
              ><td
                >{{ bp(row.pair.nextBp) }}<small>/ {{ row.pair.hours }}h</small></td
              ><td>{{ row.stats.positive.toFixed(1) }}%</td
              ><td :class="row.pair.eligible ? sign(row.result.net) : ''">{{
                row.pair.eligible ? money(row.result.net, true) : '—'
              }}</td
              ><td>{{ row.pair.eligible ? row.result.returnPct.toFixed(3) + '%' : '—' }}</td
              ><td
                ><span class="status-pill" :class="statusClass(row.result.status)">{{
                  row.result.status
                }}</span></td
              ></tr
            ></tbody
          ></table
        ></div
      >
      <div v-if="!rows.length" class="empty-state"
        ><b>没有符合条件的配对</b><p>调整资产、交易所或搜索条件后继续研究。</p
        ><button @click="resetFilters">清除筛选</button></div
      >
      <footer class="table-footer"
        ><span>{{ rows.length }} 组配对 · 统一按实际周期生成模拟结算序列</span
        ><span>净收益已计四次交易费用与盘口成本；待核验配对不参与收益排名</span></footer
      >
    </section>

    <section v-if="rows.length" class="pair-research" aria-label="单配对研究">
      <div class="detail-heading"
        ><div class="coin-monogram">{{ selected.symbol.slice(0, 1) }}</div
        ><div
          ><div class="eyebrow">PAIR RESEARCH / {{ selected.venue }}</div
          ><h2>{{ selected.symbol }} <span>现货多头 ＋ 永续空头</span></h2></div
        ><span class="status-pill" :class="statusClass(result.status)">{{ result.status }}</span
        ><button class="export-button" @click="exportScenario">导出当前情景 ↓</button></div
      >
      <div v-if="!selected.eligible" class="mapping-warning"
        ><b>资格待核验</b
        ><span>{{ selected.reason }}。以下保留行情观察，不生成净收益与容量结论。</span></div
      >
      <div class="detail-layout">
        <div class="analysis-main">
          <nav class="analysis-tabs" aria-label="研究维度"
            ><button
              v-for="item in tabs"
              :key="item.id"
              :class="{ active: tab === item.id }"
              :aria-pressed="tab === item.id"
              @click="tab = item.id"
              >{{ item.label }}</button
            ></nav
          >

          <template v-if="tab === 'carry'">
            <div class="finding"
              ><span class="finding-label">研究判断</span><h3>{{ carryHeadline }}</h3
              ><p>{{ carryDescription }}</p></div
            >
            <div class="metrics-row"
              ><div
                ><span>30d 累计资费</span
                ><strong>{{ bp(stats.month) }}<small>bp</small></strong></div
              ><div
                ><span>连续正资费</span><strong>{{ stats.streak }}<small>期</small></strong></div
              ><div
                ><span>最高 10% 周期收入占比</span
                ><strong>{{ stats.concentration.toFixed(1) }}<small>%</small></strong></div
              ></div
            >
            <article class="analysis-card"
              ><div class="card-heading"
                ><div
                  ><h3>资费是否持续，还是只靠尖峰？</h3
                  ><p>模拟已结算历史 · 单期 bp · {{ selected.hours }} 小时 / 期</p></div
                ><div class="pill-group small"
                  ><button
                    v-for="r in [7, 30]"
                    :key="r"
                    :class="{ active: range === r }"
                    @click="range = r"
                    >{{ r }}d</button
                  ></div
                ></div
              ><ResearchPlot
                :key="'funding-' + selected.id"
                title="模拟资金费率结算序列"
                unit="bp"
                :labels="fundingLabels"
                :series="fundingSeries"
              /><div class="chart-note"
                >{{ stats.count }} 期完整合成样本；收入集中度仅以正资费收入为分母。下一期假设
                {{ bp(selected.nextBp) }}bp，不混入已结算序列。</div
              ></article
            >
            <article class="analysis-card"
              ><div class="card-heading"
                ><div
                  ><h3>收益桥：资费最后还剩多少？</h3
                  ><p>{{ days }} 天 · {{ money(notional) }} USDT 单腿 · 当前情景</p></div
                ><span class="unit">USDT</span></div
              ><template v-if="selected.eligible"
                ><div class="return-bridge"
                  ><div v-for="part in bridge" :key="part.label" class="bridge-column"
                    ><strong :class="sign(part.value)">{{ money(part.value, true) }}</strong
                    ><div class="bar-track"
                      ><div
                        :style="{
                          height: Math.max(3, (Math.abs(part.value) / bridgeMax) * 90) + '%',
                        }"
                        :class="[
                          'bridge-bar',
                          part.total ? 'total' : part.value >= 0 ? 'gain' : 'loss',
                        ]"
                      ></div></div
                    ><span>{{ part.label }}</span></div
                  ></div
                ><div class="chart-note"
                  >基差损益已合并现货与永续价格损益；不再重复叠加两腿损益。</div
                ></template
              ><p v-else class="unavailable">产品映射与公司行动未确认，净收益暂不计算。</p></article
            >
          </template>

          <template v-if="tab === 'basis'">
            <div class="finding"
              ><span class="finding-label">研究判断</span
              ><h3>{{
                selected.state === '杠杆拥挤'
                  ? '资费扩张伴随杠杆扩张，需同时看基差与退出深度'
                  : '基差向上移动，才是这组头寸的不利方向'
              }}</h3
              ><p
                >负基差不会每天重复扣款，也没有必须回到零的到期日。OI
                数量、价格和主动成交用于解释状态，不能单独证明交易方向。</p
              ></div
            >
            <div class="metrics-row"
              ><div
                ><span>本地基差 / 现货价</span
                ><strong>{{ bp(selected.basisBp) }}<small>bp</small></strong></div
              ><div
                ><span>现货－指数 / 现货价</span
                ><strong>{{ bp(selected.spotIndexBp) }}<small>bp</small></strong></div
              ><div><span>Premium Index</span><strong class="missing">待采集</strong></div></div
            >
            <article class="analysis-card"
              ><div class="card-heading"
                ><div
                  ><h3>价格偏离来自哪一条腿？</h3
                  ><p>7天合成轨迹 · 三项统一以本地现货价格为分母</p></div
                ></div
              ><ResearchPlot
                title="本地基差与指数偏离"
                unit="bp"
                :labels="dailyLabels"
                :series="basisSeries"
              /><div class="equation"
                >本地基差 {{ bp(selected.basisBp) }} ＝ 永续－指数
                {{ bp(selected.basisBp + selected.spotIndexBp) }} − 现货－指数
                {{ bp(selected.spotIndexBp) }} bp</div
              ></article
            >
            <article class="analysis-card"
              ><div class="card-heading"
                ><div
                  ><h3>杠杆扩张，还是价格带动名义 OI？</h3
                  ><p>7天合成轨迹 · 起点＝100 · OI 数量与名义价值分开</p></div
                ></div
              ><ResearchPlot
                title="价格与OI数量及名义价值"
                unit="指数"
                :labels="dailyLabels"
                :series="oiSeries"
              /><div class="three-facts"
                ><span
                  >价格 <b>{{ bp(selected.priceChange) }}%</b></span
                ><span
                  >OI 数量 <b>{{ bp(selected.oi) }}%</b></span
                ><span
                  >主动买入占比 <b>{{ selected.taker }}%</b></span
                ></div
              ><p class="chart-note"
                >主动买入占比是成交方向比例；OI
                每份合约都有多空双方，不代表净多头。清算、撤单与恢复速度尚无独立样本，状态标签为预设情景。</p
              ></article
            >
          </template>

          <template v-if="tab === 'capacity'">
            <div class="finding"
              ><span class="finding-label">研究判断</span
              ><h3>{{
                result.covered
                  ? '可部署规模由较薄的一条腿和现金储备共同决定'
                  : '目标规模超过压力深度，理论收益无法按当前条件兑现'
              }}</h3
              ><p
                >现货浮盈不作为永续可用现金。急涨时，空头亏损与追加保证金可能先于划转到账。</p
              ></div
            >
            <article class="analysis-card"
              ><div class="card-heading"
                ><div
                  ><h3>退出时，两条腿能否同时承接？</h3
                  ><p>25bp 价格带内深度 · USDT · 压力深度减少 {{ depthLoss }}%</p></div
                ></div
              ><div v-for="(depth, i) in selected.depth" :key="i" class="depth-row"
                ><div
                  ><span>{{ i === 0 ? '现货卖出 · 买盘' : '永续买回 · 卖盘' }}</span
                  ><strong>{{ money(depth * (1 - depthLoss / 100)) }}</strong></div
                ><div class="depth-track"
                  ><div
                    :style="{ width: ((depth * (1 - depthLoss / 100)) / depthMax) * 100 + '%' }"
                  ></div
                  ><i
                    :style="{ left: Math.min(99, (notional / depthMax) * 100) + '%' }"
                  ></i></div></div
              ><div class="chart-note"
                >竖线为目标规模 {{ money(notional) }} USDT；25bp
                深度是观察边界，不是实际成交成本保证。</div
              ><div class="capacity-verdict" :class="result.covered ? 'positive' : 'negative'">{{
                selected.eligible
                  ? result.covered
                    ? '双腿深度覆盖目标规模'
                    : '深度不足 · 暂缓'
                  : '映射待核验 · 容量结论不适用'
              }}</div></article
            >
            <article class="analysis-card"
              ><div class="card-heading"
                ><div
                  ><h3>急涨时的独立现金账</h3
                  ><p>标的上涨 {{ priceShock }}% · 基差变化 {{ bp(basisMove) }}bp</p></div
                ></div
              ><dl class="cash-ledger"
                ><div
                  ><dt>现货投入</dt><dd>{{ money(notional) }} USDT</dd></div
                ><div
                  ><dt>独立合约储备（{{ reservePct }}%）</dt
                  ><dd>{{ money(result.reserve) }} USDT</dd></div
                ><div
                  ><dt>压力现金需求</dt
                  ><dd>{{
                    selected.eligible ? money(result.cashNeed) + ' USDT' : '待核验'
                  }}</dd></div
                ><div class="ledger-total"
                  ><dt>储备减压力需求</dt
                  ><dd :class="sign(result.cashLeft)">{{
                    selected.eligible ? money(result.cashLeft, true) + ' USDT' : '—'
                  }}</dd></div
                ></dl
              ><p class="chart-note"
                >现金需求包含上涨造成的空头现金亏损、不利基差变化、假设 0.5%
                维持保证金与半程退出成本。不是交易所强平价模型；不计场外资金、现货浮盈或未来资费到账。</p
              ></article
            >
          </template>

          <template v-if="tab === 'events'">
            <div class="finding"
              ><span class="finding-label">研究判断</span
              ><h3>{{
                selected.asset === '股票'
                  ? '先确认权利与公司行动，再研究高资费'
                  : selected.asset === '金属'
                  ? '同代币与黄金代理对冲，需要分开研究'
                  : '把流动性危机拆成可以检验的组合冲击'
              }}</h3
              ><p>{{ selected.event }}。以下为研究场景，未声称当前市场发生这些事件。</p></div
            >
            <article class="analysis-card"
              ><div class="card-heading"
                ><div
                  ><h3>配对资格与资产特有问题</h3
                  ><p>{{ selected.mapping }} · {{ selected.venue }}</p></div
                ></div
              ><div class="event-list"
                ><div v-for="item in assetQuestions" :key="item[0]"
                  ><b>{{ item[0] }}</b
                  ><span>{{ item[1] }}</span></div
                ></div
              ></article
            >
            <article class="analysis-card"
              ><div class="card-heading"
                ><div><h3>压力场景</h3><p>点击应用到当前试算；损失情景不代表发生概率</p></div
                ><button class="text-button" @click="resetScenario">恢复基准</button></div
              ><div class="stress-grid"
                ><button v-for="s in stressPresets" :key="s.name" @click="applyStress(s)"
                  ><b>{{ s.name }} ↗</b><span>{{ s.description }}</span></button
                ></div
              ><div class="event-list hard-events"
                ><div
                  ><b>提款 / 划转暂停</b
                  ><span>托管与现金可达性问题，无法用市场收益或“正常盘口”抵消。</span></div
                ><div
                  ><b>ADL / 单腿停牌</b
                  ><span>重新核对残余 Delta；原配对的净收益公式可能失效。</span></div
                ><div
                  ><b>规则 / 指数异常</b
                  ><span>结算周期、指数和标记价格失真时，先暂停结论，再核验规则。</span></div
                ></div
              ></article
            >
          </template>
        </div>

        <aside class="scenario-panel" aria-label="持有期试算">
          <div class="scenario-title"
            ><div
              ><span class="eyebrow">HOLDING SCENARIO</span><h3>{{ days }} 天持有期试算</h3></div
            ><span class="scenario-tag">{{ scenarioName }}</span></div
          >
          <div class="scenario-result"
            ><span>情景净收益 · USDT</span
            ><strong :class="sign(result.net)" data-testid="scenario-net">{{
              selected.eligible ? money(result.net, true) : '待核验'
            }}</strong
            ><p v-if="selected.eligible"
              >总资本收益率 <b>{{ result.returnPct.toFixed(3) }}%</b><span> / 非年化</span></p
            ><p v-else>{{ selected.reason }}</p></div
          >
          <div class="scenario-facts"
            ><div
              ><span>组合占用资本</span><b>{{ money(result.capital) }} USDT</b></div
            ><div
              ><span>双腿匹配数量</span
              ><b>{{
                selected.eligible
                  ? result.quantity.toLocaleString('en-US', { maximumFractionDigits: 6 }) +
                    ' ' +
                    selected.symbol
                  : '待核验'
              }}</b></div
            ><div
              ><span>假设结算次数</span
              ><b>{{ result.settlements }} 次 / {{ selected.hours }}h</b></div
            ><div
              ><span>静态回本期</span
              ><b>{{
                selected.eligible && result.breakEven !== null
                  ? result.breakEven.toFixed(1) + ' 天'
                  : '—'
              }}</b></div
            ></div
          >
          <div class="scenario-controls"
            ><label
              ><span
                >资费延续比例 <b>{{ fundingScale }}%</b></span
              ><input
                aria-label="资费延续比例"
                v-model.number="fundingScale"
                type="range"
                min="-100"
                max="150"
                step="5" /></label
            ><label
              ><span
                >退出基差变化 <b>{{ bp(basisMove) }} bp</b></span
              ><input
                aria-label="退出基差变化"
                v-model.number="basisMove"
                type="range"
                min="-50"
                max="100"
                step="1" /></label
            ><label
              ><span
                >退出深度减少 <b>{{ depthLoss }}%</b></span
              ><input
                aria-label="退出深度减少"
                v-model.number="depthLoss"
                type="range"
                min="0"
                max="95"
                step="5" /></label
            ><label
              ><span
                >标的上涨冲击 <b>{{ priceShock }}%</b></span
              ><input
                aria-label="标的上涨冲击"
                v-model.number="priceShock"
                type="range"
                min="0"
                max="50"
                step="1" /></label
            ><label
              ><span
                >合约储备 / 现货投入 <b>{{ reservePct }}%</b></span
              ><input
                aria-label="合约储备比例"
                v-model.number="reservePct"
                type="range"
                min="5"
                max="100"
                step="5" /></label
          ></div>
          <button class="reset-scenario" @click="resetScenario">恢复基准情景</button>
          <div class="gate-list"
            ><div v-for="(gate, i) in result.gates" :key="gate.name" :title="gate.detail"
              ><span
                :class="
                  i > 0 && !selected.eligible ? 'gate-na' : gate.pass ? 'gate-pass' : 'gate-fail'
                "
                >{{ i > 0 && !selected.eligible ? '—' : gate.pass ? '✓' : '!' }}</span
              ><b>{{ gate.name }}</b
              ><small>{{
                i > 0 && !selected.eligible ? '待资格核验' : gate.pass ? '情景通过' : '未通过'
              }}</small></div
            ></div
          >
          <p class="scenario-explanation">{{
            selected.eligible
              ? result.gates
                  .filter((g) => !g.pass)
                  .map((g) => g.detail)
                  .join('；') || '当前假设下可继续研究；尚未验证预测效果或实际成交。'
              : selected.reason
          }}</p>
          <p class="scenario-footnote"
            >费用 {{ selected.feeBp }}bp
            为双腿开平合计假设。静态回本期假设资费不变及同一退出基差，不是预测持有期限。</p
          >
        </aside>
      </div>
    </section>
    <div class="lab-footer"
      ><span>行情研究 → 持有期净收益 → 可实现性</span><span>示例数据 · 未连接行情、账户或交易</span
      ><span v-if="exported" role="status">情景 CSV 已导出</span></div
    >
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import ResearchPlot from './ResearchPlot.vue';
  import { pairs, history, statistics, evaluate, money, bp, type Pair } from './model';
  import './style.css';

  const days = ref(7),
    notional = ref(100000),
    search = ref(''),
    asset = ref('全部'),
    venue = ref('全部交易所'),
    onlyReady = ref(false),
    sort = ref('quality');
  const selectedId = ref('btc-bn'),
    tab = ref('carry'),
    range = ref(7),
    methodOpen = ref(false),
    exported = ref(false);
  const fundingScale = ref(100),
    basisMove = ref(3),
    depthLoss = ref(0),
    priceShock = ref(15),
    reservePct = ref(25);
  const selected = computed(() => pairs.find((p) => p.id === selectedId.value) || pairs[0]);
  const stats = computed(() => statistics(selected.value));
  const assumptions = computed(() => ({
    notional: notional.value,
    days: days.value,
    fundingScale: fundingScale.value,
    basisMove: basisMove.value,
    depthLoss: depthLoss.value,
    priceShock: priceShock.value,
    reservePct: reservePct.value,
  }));
  const result = computed(() => evaluate(selected.value, assumptions.value));
  const baseline = (p: Pair) =>
    evaluate(p, {
      notional: notional.value,
      days: days.value,
      fundingScale: 100,
      basisMove: p.exitMoveBp,
      depthLoss: 0,
      priceShock: 15,
      reservePct: 25,
    });
  const allRows = computed(() =>
    pairs.map((p) => ({ pair: p, stats: statistics(p), result: baseline(p) })),
  );
  const counts = computed(() => ({
    ready: allRows.value.filter((r) => r.result.status === '可研究').length,
    wait: allRows.value.filter((r) => r.result.status === '暂缓').length,
    excluded: allRows.value.filter((r) => r.result.status === '待核验').length,
  }));
  const rows = computed(() =>
    allRows.value
      .filter(
        (r) =>
          (asset.value === '全部' || r.pair.asset === asset.value) &&
          (venue.value === '全部交易所' || r.pair.venue === venue.value) &&
          (!onlyReady.value || r.result.status === '可研究') &&
          `${r.pair.symbol} ${r.pair.venue}`
            .toLowerCase()
            .includes(search.value.trim().toLowerCase()),
      )
      .sort((a, b) =>
        sort.value === 'funding'
          ? b.stats.day - a.stats.day
          : { 可研究: 0, 暂缓: 1, 待核验: 2 }[a.result.status] -
              { 可研究: 0, 暂缓: 1, 待核验: 2 }[b.result.status] || b.result.net - a.result.net,
      ),
  );
  watch(rows, (list) => {
    if (list.length && !list.some((r) => r.pair.id === selectedId.value))
      selectedId.value = list[0].pair.id;
  });
  watch(selectedId, () => {
    resetScenario();
    exported.value = false;
  });
  const sign = (value: number) => (value >= 0 ? 'positive' : 'negative');
  const statusClass = (value: string) =>
    value === '可研究' ? 'ready' : value === '暂缓' ? 'watch' : 'unverified';
  const stateColor = (p: Pair) =>
    p.state === '稳定 Carry' ? 'calm' : p.state === '去杠杆' ? 'danger' : 'caution';
  function selectPair(id: string) {
    selectedId.value = id;
  }
  function resetFilters() {
    search.value = '';
    asset.value = '全部';
    venue.value = '全部交易所';
    onlyReady.value = false;
  }
  function resetScenario() {
    fundingScale.value = 100;
    basisMove.value = selected.value.exitMoveBp;
    depthLoss.value = 0;
    priceShock.value = 15;
    reservePct.value = 25;
  }
  const scenarioName = computed(() =>
    fundingScale.value === 100 &&
    basisMove.value === selected.value.exitMoveBp &&
    depthLoss.value === 0 &&
    priceShock.value === 15 &&
    reservePct.value === 25
      ? '基准情景'
      : '自定义情景',
  );
  const tabs = [
    { id: 'carry', label: '资费与收益' },
    { id: 'basis', label: '基差与拥挤' },
    { id: 'capacity', label: '容量与现金' },
    { id: 'events', label: '产品与事件' },
  ];
  const carryHeadline = computed(() =>
    !selected.value.eligible
      ? '行情可以观察，产品资格仍需先核验'
      : selected.value.state === 'Carry 衰减'
      ? '下一期假设低于历史水平，外推高资费会高估收益'
      : selected.value.nextBp <= 0
      ? '当前资费方向不支持正资费套利'
      : selected.value.state === '杠杆拥挤'
      ? '高资费伴随拥挤，先压测持续性与退出容量'
      : '资费持续性，比单次费率的高度更值得研究',
  );
  const carryDescription = computed(
    () =>
      `模拟30天中 ${stats.value.positive.toFixed(
        1,
      )}% 的结算为正；最高10%周期贡献 ${stats.value.concentration.toFixed(
        1,
      )}% 的正资费收入。结合费用与退出基差，判断这段现金流是否值得持有。`,
  );
  const dateLabel = (time: number) =>
    new Date(time + 8 * 3600000).toISOString().slice(5, 16).replace('T', ' ');
  const fundingPoints = computed(() =>
    history(selected.value).slice((-range.value * 24) / selected.value.hours),
  );
  const fundingLabels = computed(() => fundingPoints.value.map((p) => dateLabel(p.time)));
  const fundingSeries = computed(() => [
    { name: '已结算（模拟）', color: '#27877d', values: fundingPoints.value.map((p) => p.value) },
  ]);
  const dailyLabels = ['10/30', '10/31', '11/01', '11/02', '11/03', '11/04', '11/05', '11/06'];
  const basisSeries = computed(() => {
    const local = dailyLabels.map(
      (_, i) => selected.value.basisBp + Math.sin(i * 1.2) * (7 - i) * 0.7,
    );
    const spot = dailyLabels.map(
      (_, i) => selected.value.spotIndexBp + Math.cos(i) * (7 - i) * 0.4,
    );
    return [
      { name: '永续－现货', color: '#366dba', values: local },
      { name: '永续－指数', color: '#258879', values: local.map((v, i) => v + spot[i]) },
      { name: '现货－指数', color: '#b38643', values: spot },
    ];
  });
  const oiSeries = computed(() => {
    const price = dailyLabels.map((_, i) => 100 + (selected.value.priceChange * i) / 7);
    const oi = dailyLabels.map((_, i) => 100 + (selected.value.oi * i) / 7);
    return [
      { name: '价格', color: '#366dba', values: price },
      { name: 'OI 数量', color: '#258879', values: oi },
      { name: 'OI 名义价值', color: '#b38643', values: oi.map((v, i) => (v * price[i]) / 100) },
    ];
  });
  const bridge = computed(() => [
    { label: '资费收入', value: result.value.funding },
    { label: '基差损益', value: result.value.basis },
    { label: '交易费用', value: -result.value.fees },
    { label: '盘口成本', value: -result.value.impact },
    { label: '情景净收益', value: result.value.net, total: true },
  ]);
  const bridgeMax = computed(() => Math.max(1, ...bridge.value.map((p) => Math.abs(p.value))));
  const depthMax = computed(() => Math.max(...selected.value.depth, notional.value));
  const assetQuestions = computed(() =>
    selected.value.asset === '股票'
      ? [
          ['经济数量', '股票代币权利、永续乘数、拆合股必须匹配。'],
          ['公司行动', '现货分红与永续现金补偿分别核算；缺少一边不能假设净额为零。'],
          ['交易时段', '财报、停牌、盘前盘后与周末的指数、深度分开观察。'],
        ]
      : selected.value.asset === '金属'
      ? [
          ['对冲映射', 'XAUT、PAXG 与 XAU 指数不自动视为同资产。'],
          ['偏离来源', '区分代币相对黄金的跟踪误差、现货偏离与永续溢价。'],
          ['事件窗口', '底层休市、赎回受限、美元与利率事件分别压测。'],
        ]
      : [
          ['经济数量', '现货与线性永续按相同底层数量配平，不按等金额假设 Delta 为零。'],
          ['拥挤与供给', 'OI 数量、主动成交、流通集中、解锁与下架需要联合观察。'],
          ['交易与托管', '稳定币折价、提款限制、ADL、单腿停牌不能靠另一腿方向盈利覆盖。'],
        ],
  );
  const stressPresets = [
    {
      name: '资费衰减',
      description: '资费降至 25%，基差上移 10bp',
      scale: 25,
      depth: 0,
      shock: 15,
      basis: 10,
    },
    {
      name: '流动性收缩',
      description: '深度减少 80%，基差上移 40bp',
      scale: 50,
      depth: 80,
      shock: 15,
      basis: 40,
    },
    {
      name: '急涨现金压力',
      description: '标的上涨 35%，基差上移 25bp',
      scale: 100,
      depth: 40,
      shock: 35,
      basis: 25,
    },
    {
      name: '资费反转',
      description: '资费变为基准的 −50%',
      scale: -50,
      depth: 20,
      shock: 15,
      basis: 15,
    },
  ];
  function applyStress(s: (typeof stressPresets)[number]) {
    fundingScale.value = s.scale;
    depthLoss.value = s.depth;
    priceShock.value = s.shock;
    basisMove.value = s.basis;
    reservePct.value = 25;
  }
  function exportScenario() {
    const data = [
      ['字段', '值'],
      ['数据性质', '全部为合成模拟情景；非实测或预测'],
      ['情景截面', '2026-11-06T00:00:00+08:00'],
      ['配对', selected.value.symbol],
      ['交易所', selected.value.venue],
      ['配对资格', selected.value.eligible ? '同资产模拟' : selected.value.reason],
      ['持有天数', days.value],
      ['单腿名义金额_USDT', notional.value],
      ['每期资费_bp', selected.value.nextBp],
      ['结算周期_h', selected.value.hours],
      ['结算次数', result.value.settlements],
      ['资费延续_pct', fundingScale.value],
      ['退出基差变化_bp', basisMove.value],
      ['深度减少_pct', depthLoss.value],
      ['上涨冲击_pct', priceShock.value],
      ['储备比例_pct', reservePct.value],
      ['总资本_USDT', result.value.capital],
      ['资费收入_USDT', selected.value.eligible ? result.value.funding : '待核验'],
      ['基差损益_USDT', selected.value.eligible ? result.value.basis : '待核验'],
      ['交易费用_USDT', selected.value.eligible ? result.value.fees : '待核验'],
      ['盘口成本_USDT', selected.value.eligible ? result.value.impact : '待核验'],
      ['净收益_USDT', selected.value.eligible ? result.value.net : '待核验'],
      ['持有期资本收益_pct', selected.value.eligible ? result.value.returnPct : '待核验'],
      ['压力现金余量_USDT', selected.value.eligible ? result.value.cashLeft : '待核验'],
      ['研究结论', result.value.status],
    ];
    const csv =
      '\uFEFF' +
      data
        .map((row) => row.map((v) => '"' + String(v).replace(/"/g, '""') + '"').join(','))
        .join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `funding-demo-${selected.value.id}-${days.value}d.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    exported.value = true;
  }
</script>
