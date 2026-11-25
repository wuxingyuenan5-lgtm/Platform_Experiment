<template>
  <section class="capital-handbook" :aria-label="titles[mode]">
    <header v-if="mode === 'funds' || mode === 'fund-research'" class="heading"
      ><div
        ><h2>{{ titles[mode] }}</h2></div
      ></header
    >
    <nav v-if="mode === 'others'" class="category-grid" aria-label="其他资金分类">
      <button
        v-for="c in categories"
        :key="c.key"
        :aria-pressed="category === c.key"
        @click="category = c.key"
        ><span>{{ c.label }}</span
        ><small>{{ c.detail }}</small></button
      >
    </nav>

    <template v-if="mode === 'overview'">
      <FinancingChart
        class="institution-chart"
        :key="institutionMetric"
        :title="institutionMetrics[institutionMetric]"
        :rows="overviewInstitutionRows"
        :lines="overviewInstitutionLines"
        :initial-range="0"
        allow-table
        :note="
          institutionMetric === 'change'
            ? '相隔半年的同口径披露市值之差。变动含股价及披露范围变化，不能作为净流入。来源：Choice。'
            : 'Choice 机构类型统计表，按所选报告口径展示披露持股市值。'
        "
      >
        <template #toolbar>
          <div class="controls institution-controls">
            <div class="institution-tabs" role="group" aria-label="机构持股指标">
              <button
                v-for="(label, key) in institutionMetrics"
                :key="key"
                type="button"
                :aria-pressed="institutionMetric === key"
                @click="institutionMetric = key"
                >{{ label }}</button
              >
            </div>
            <label
              >披露口径
              <select v-model="overviewReportBasis" aria-label="披露口径"
                ><option value="half">半年报与年报</option
                ><option value="quarter">一季报与三季报</option></select
              ></label
            >
            <label>
              机构角色
              <select v-model="institutionRole" aria-label="机构角色">
                <option v-for="(role, key) in institutionRoles" :key="key" :value="key">
                  {{ role.label }}
                </option>
              </select>
            </label>
          </div>
        </template>
      </FinancingChart>
      <FinancingChart
        title="股票与混合基金新发份额"
        :rows="handbook.issues || []"
        :lines="issueLines"
        :initial-range="1095"
        allow-table
        note="亿份；成立日口径，含主动和被动产品，完整月份。"
      />
      <p class="source"
        >{{ handbook.source || '暂无Choice专题数据' }} · 采集
        {{ handbook.fetchedAt?.slice(0, 10) || '—' }}</p
      >
    </template>

    <template v-if="mode === 'funds'">
      <InstitutionalCapitalPanel :sources="data.institutions" fixed-kind="public">
        <template #issuance>
          <FinancingChart
            title="新成立股票、混合基金份额"
            :rows="handbook.issues || []"
            :lines="issueLines"
            :initial-range="1095"
            allow-table
            note="亿份；成立日口径，含主动和被动产品。"
          />
        </template>
      </InstitutionalCapitalPanel>
    </template>

    <section v-if="mode === 'fund-research' && selectedFundReport">
      <div class="controls">
        <h3>基金披露持股前20与季度变化</h3>
        <label
          >报告期
          <select v-model="fundReportDate">
            <option
              v-for="report in handbook.fundStockReports"
              :key="report.date"
              :value="report.date"
            >
              {{ report.date }}
            </option>
          </select>
        </label>
      </div>
      <div class="fund-stock-table">
        <table>
          <thead
            ><tr
              ><th>股票</th><th>代码</th><th>持股市值（亿元）</th><th>持股机构数</th
              ><th>较上季增减（万股）</th></tr
            ></thead
          >
          <tbody>
            <tr v-for="stock in selectedFundReport.rows" :key="stock.code">
              <td>{{ stock.name }}</td
              ><td>{{ stock.code }}</td> <td>{{ formatAmount(stock.valueYi) }}</td
              ><td>{{ formatAmount(stock.fundCount) }}</td>
              <td>{{ formatAmount(stock.shareChangeWan) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="source">{{
        selectedFundReport.method === 'css'
          ? 'Choice 截面 · 沪深 A 股。披露市值为股数乘期末收盘价，变化为两期披露股数之差。'
          : 'Choice · 机构持股明细（机构类型为基金）。按披露持股市值排序，持股差值包含披露范围变化。'
      }}</p>
    </section>
    <section v-if="mode === 'fund-research' && fundBenchmark">
      <div class="controls">
        <h3>申万一级行业 · A股市场基准</h3>
        <label
          >基准期
          <select v-model="fundBenchmarkQuarter">
            <option
              v-for="report in handbook.fundIndustryBenchmarks"
              :key="report.date"
              :value="report.date"
              >{{ report.date }}</option
            >
          </select>
        </label>
      </div>
      <CapitalBars
        title="各行业自由流通市值权重"
        :rows="fundBenchmark.rows.map((row) => ({ date: row.name, weightPct: row.weightPct }))"
        :lines="[line('weightPct', '市场基准权重', '%', 0, true)]"
        :note="`Choice · ${fundBenchmark.tradeDate}，使用历史板块成分。各行业自由流通市值除以31个行业合计。`"
      />
    </section>

    <template v-if="mode === 'margin'">
      <CapitalBars
        title="分行业融资余额与杠杆占比"
        :rows="marginCross"
        :lines="[
          line('balance', '融资余额', '亿元', 0, true),
          { ...line('leverage', '融资余额 / 自由流通市值', '%', 1), right: true },
        ]"
        note="月末截面；最新月截至所选日期，分母为同日自由流通市值。"
      >
        <template #toolbar>
          <div class="controls chart-controls">
            <label>
              观察日期
              <select v-model="marginDate" aria-label="观察日期">
                <option v-for="d in marginDates" :key="d">{{ d }}</option>
              </select>
            </label>
          </div>
        </template>
      </CapitalBars>
      <div class="chart-grid">
        <FinancingChart
          title="TMT行业融资结构"
          :rows="technologyMargin"
          :lines="[
            line('balance', '电子、计算机、传媒、通信融资余额', '亿元', 0),
            { ...line('share', '占31行业融资余额', '%', 1), right: true },
          ]"
          :initial-range="1095"
          allow-table
          note="电子、计算机、传媒、通信合计。"
        />
        <FinancingChart
          :title="`${industryName} · 融资规模与交易强度`"
          :rows="marginHistory"
          :lines="[
            line('balance', '融资余额', '亿元', 0),
            { ...line('buyShare', '当日融资买入 / 成交额', '%', 1), right: true },
          ]"
          :initial-range="1095"
          allow-table
          note="月末交易日截面。"
        >
          <template #toolbar>
            <div class="controls chart-controls">
              <label>
                行业
                <select v-model="industry" aria-label="行业">
                  <option v-for="r in industryOptions" :key="String(r.code)" :value="r.code">
                    {{ r.name }}
                  </option>
                </select>
              </label>
            </div>
          </template>
        </FinancingChart>
      </div>
      <p class="source">Choice申万一级行业 · 统计日期 {{ marginDate || '—' }}</p>
    </template>

    <template v-if="mode === 'others'">
      <template v-if="category === 'foreign'">
        <FinancingChart
          class="institution-chart"
          :key="foreignMetric"
          :title="foreignMetrics[foreignMetric]"
          :rows="foreignMetric === 'value' ? institutionRows : foreignFlow.rows"
          :lines="foreignMetric === 'value' ? disclosedHoldingLines : foreignFlow.lines"
          :initial-range="0"
          allow-table
          :note="
            foreignMetric === 'value'
              ? 'Choice · QFII披露持股，覆盖范围为QFII。'
              : 'Demo · 模拟季度净买入，不代表真实外资流量。'
          "
        >
          <template #toolbar>
            <div class="controls institution-controls">
              <div class="institution-tabs" role="group" aria-label="外资指标">
                <button
                  v-for="(label, key) in foreignMetrics"
                  :key="key"
                  type="button"
                  :aria-pressed="foreignMetric === key"
                  @click="foreignMetric = key"
                  >{{ label }}</button
                >
              </div>
              <label v-if="foreignMetric === 'value'">
                披露口径
                <select v-model="reportBasis" aria-label="外资披露口径">
                  <option value="half">半年报与年报</option>
                  <option value="quarter">一季报与三季报</option>
                </select>
              </label>
              <label v-else>
                Demo报告期
                <select v-model="foreignDemoPeriod" aria-label="外资净买入Demo报告期">
                  <option v-for="period in demoPeriods" :key="period">{{ period }}</option>
                </select>
              </label>
            </div>
          </template>
        </FinancingChart>
        <FinancingChart
          :title="
            hasForeignValueShare
              ? '境外持有境内人民币股票市值及占A股市值比例'
              : '境外持有境内人民币股票市值'
          "
          :rows="foreignMonthly"
          :lines="foreignLines"
          :initial-range="1095"
          allow-table
          :note="
            hasForeignValueShare
              ? '占比为人民银行月末境外持股市值除以Choice全A同月最后交易日总市值。市值变化包含估值和交易影响。'
              : '人民银行统计。市值变化包含估值和交易影响。'
          "
        >
          <template #toolbar>
            <span class="source chart-source"
              >中国人民银行 · 统计期 {{ handbook.foreign?.at(-1)?.date || '—'
              }}{{ publicStatus('foreign') }}</span
            >
          </template>
        </FinancingChart>
        <section v-if="northReport" class="other-table-card">
          <div class="controls">
            <h3>北向季末持仓 · 申万一级行业前10</h3>
            <label
              >报告期
              <select v-model="northQuarter">
                <option
                  v-for="report in handbook.northIndustryReports"
                  :key="report.date"
                  :value="report.date"
                  >{{ report.date }}</option
                >
              </select>
            </label>
          </div>
          <div class="fund-stock-table">
            <table>
              <thead
                ><tr
                  ><th>排名</th><th>行业</th><th>持股市值（亿元）</th><th>占北向样本（%）</th
                  ><th>持股只数</th></tr
                ></thead
              >
              <tbody
                ><tr v-for="(row, index) in northReport.rows.slice(0, 10)" :key="row.name">
                  <td>{{ index + 1 }}</td
                  ><td>{{ row.name }}</td
                  ><td>{{ formatAmount(row.valueYi) }}</td>
                  <td>{{ formatAmount(row.weightPct) }}</td
                  ><td>{{ row.stocks }}</td>
                </tr></tbody
              >
            </table>
          </div>
          <p class="source"
            >Choice · 沪深股通季末持股股数 ×
            {{ northReport.tradeDate }} 收盘价，按历史申万行业汇总。覆盖
            {{ northReport.coveredCount }}/{{ northReport.eligibleCount }} 只标的。</p
          >
        </section>
      </template>
      <template v-if="category === 'pension'">
        <div class="chart-grid">
          <FinancingChart
            title="全国社保基金资产规模"
            :rows="handbook.social || []"
            :lines="[line('assets', '总资产', '亿元', 0), line('domestic', '境内投资', '亿元', 1)]"
            :initial-range="0"
            allow-table
            note="全资产口径，非股票持仓。"
          />
          <FinancingChart
            title="全国社保基金年度投资收益率"
            :rows="handbook.social || []"
            :lines="[line('returnPct', '投资收益率', '%', 0, true)]"
            :initial-range="0"
            allow-table
          />
        </div>
        <FinancingChart
          v-if="handbook.pension?.length"
          title="企业年金积累基金规模"
          :rows="handbook.pension"
          :lines="[line('assets', '积累基金', '亿元', 0)]"
          :initial-range="1095"
          allow-table
        />
        <FinancingChart
          v-if="pensionReturns.length"
          title="企业年金投资收益率"
          :rows="handbook.pension || []"
          :lines="pensionReturns"
          :initial-range="1095"
          allow-table
          note="人社部披露口径随报告期变化：当季或当年加权收益与近三年累计收益分列。"
        >
          <template #toolbar>
            <span v-if="handbook.pension?.length" class="source chart-source">
              <a
                :href="String(handbook.pension.at(-1)?.sourceUrl)"
                target="_blank"
                rel="noopener noreferrer"
                >人社部企业年金基金业务数据摘要</a
              >
              · {{ handbook.pension.at(-1)?.date }}{{ publicStatus('pension') }}
            </span>
          </template>
        </FinancingChart>
        <FinancingChart
          v-if="handbook.occupationalPension?.length"
          title="全国职业年金投资运营规模"
          :rows="handbook.occupationalPension"
          :lines="[line('assets', '投资运营规模', '亿元', 0, true)]"
          :initial-range="0"
          allow-table
          note="人社部年度披露，按年末统计。"
        >
          <template #toolbar>
            <span v-if="handbook.occupationalPension?.length" class="source chart-source">
              <a
                :href="String(handbook.occupationalPension.at(-1)?.sourceUrl)"
                target="_blank"
                rel="noopener noreferrer"
                >人社部全国职业年金基金市场化投资运营情况</a
              >
              · {{ handbook.occupationalPension.at(-1)?.date
              }}{{ publicStatus('occupationalPension') }}
            </span>
          </template>
        </FinancingChart>
        <p class="source"
          >全国社会保障基金理事会 · 统计期 {{ handbook.social?.at(-1)?.date || '—'
          }}{{ publicStatus('social') }}</p
        >
      </template>
      <InstitutionalCapitalPanel
        v-if="category === 'insurance' || category === 'private'"
        :key="category"
        :sources="data.institutions"
        :fixed-kind="category"
      />
      <template v-if="category === 'insurance' && premiumRows.length">
        <FinancingChart
          title="原保险保费收入 · 月度"
          :rows="premiumRows"
          :lines="[line('premiumMonth', '当月原保险保费收入', '亿元', 0, true)]"
          :initial-range="1095"
          allow-table
          note="国家金融监督管理总局。按同年相邻月份累计值计算，缺上月数据保留空值。"
        >
          <template #toolbar>
            <span class="source chart-source"
              ><a
                :href="String(premiumRows.at(-1)?.sourceUrl)"
                target="_blank"
                rel="noopener noreferrer"
                >保险业经营情况表</a
              >
              · {{ premiumRows.at(-1)?.date }}</span
            >
          </template>
        </FinancingChart>
      </template>
      <FinancingChart
        v-if="category === 'insurance' || category === 'pension'"
        :title="`${categoryLabel} · 披露持股市值`"
        :rows="institutionRows"
        :lines="disclosedHoldingLines"
        :initial-range="1095"
        allow-table
        note="Choice · 披露持股市值。"
      >
        <template #toolbar>
          <div class="controls chart-controls">
            <label>
              披露口径
              <select v-model="reportBasis" aria-label="持仓披露口径">
                <option value="half">半年报与年报</option>
                <option value="quarter">一季报与三季报</option>
              </select>
            </label>
          </div>
        </template>
      </FinancingChart>
      <template v-if="category === 'bank'">
        <dl class="bank-summary" aria-label="银行理财规模摘要">
          <div
            ><dt>存续规模</dt
            ><dd>{{ formatAmount(latestBank?.assets) }}<small>万亿元</small></dd></div
          >
          <div
            ><dt>投资资产</dt
            ><dd>{{ formatAmount(latestBank?.investmentAssets) }}<small>万亿元</small></dd></div
          >
        </dl>
        <FinancingChart
          title="理财权益配置比例"
          :rows="handbook.bank || []"
          :lines="[line('equityPct', '权益资产 / 投资资产', '%', 0)]"
          :initial-range="1095"
          allow-table
          note="分母为投资资产。"
        />
        <p class="source"
          >银行业理财登记托管中心 · 统计期 {{ handbook.bank?.at(-1)?.date || '—'
          }}{{ publicStatus('bank') }}
          <a
            v-for="r in handbook.bank || []"
            :key="r.date"
            :href="String(r.sourceUrl)"
            target="_blank"
            rel="noopener noreferrer"
          >
            · {{ r.date }}</a
          >
        </p>
      </template>
      <template v-if="category === 'resident'">
        <FinancingChart
          :title="hasResidentMarket ? '新开户与市场表现' : '上交所个人A股新开户'"
          :rows="hasResidentMarket ? handbook.residentMarket! : handbook.residents || []"
          :lines="[
            line('personal', '个人A股新开户', '万户', 0, true),
            ...(hasResidentMarket
              ? [{ ...line('marketReturnPct', '沪深300月涨跌幅', '%', 1), right: true }]
              : []),
          ]"
          :initial-range="1095"
          allow-table
          :note="
            hasResidentMarket
              ? '上交所个人A股新开户；沪深300按Choice月末收盘计算月涨跌幅。'
              : '上交所账户口径，非全国去重投资者人数。'
          "
        >
          <template #toolbar>
            <span class="source chart-source"
              ><a
                href="https://www.sse.com.cn/aboutus/publication/monthly/investor/"
                target="_blank"
                rel="noopener noreferrer"
                >上交所投资者月报</a
              >
              · {{ handbook.residents?.[0]?.date.slice(0, 7) }}—{{
                handbook.residents?.at(-1)?.date.slice(0, 7)
              }}</span
            >
          </template>
        </FinancingChart>
      </template>
      <template v-if="category === 'corporate'">
        <CapitalBars
          title="回购计划累计实施规模 · 按最近披露月"
          :rows="buybackMonths"
          :lines="[line('amount', '累计实施金额', '亿元', 0, true)]"
          note="按最新披露月归组的计划累计金额，非当月回购流量。"
        />
        <CapitalEventsTable
          title="回购与股东增减持"
          :sources="data.sources"
          :source-keys="['buybacks', 'holders']"
          :as-of="data.asOf"
        />
      </template>
      <template v-if="category === 'demand'">
        <FinancingChart
          v-if="eventMonthly.length"
          title="A股增发与现金分红实施 · 月度"
          :rows="eventMonthly"
          :lines="eventLines"
          :initial-range="1095"
          allow-table
          note="Choice实施披露。增发按上市月汇总披露金额，含资产认购；现金分红按发放月汇总税前每股派息×分红股本基数。"
        />
        <FinancingChart
          title="股票发行规模 · 月度"
          :rows="data.sources.issuance.rows"
          :lines="issuanceLines"
          :initial-range="1095"
          allow-table
          note="募集口径；增发含非现金认购，本月尚未完整。"
        />
        <FinancingChart
          title="未来30天解禁 · 按周汇总"
          :rows="data.unlockWeeks"
          :lines="[line('value', '解禁参考市值', '亿元', 1, true)]"
          allow-table
          note="潜在供给，非实际卖出；首尾周不足整周。"
        />
        <CapitalEventsTable
          title="解禁日历"
          :sources="data.sources"
          :source-keys="['unlocks']"
          :as-of="data.asOf"
        />
      </template>
    </template>
    <section v-if="showHoldings">
      <CapitalBars
        :title="`${holdingTitle} · 行业持股比例`"
        :rows="holdingCross"
        :lines="holdingLines"
        note="Choice · 申万一级行业持股比例，分母为行业口径。"
      >
        <template #toolbar>
          <div class="controls chart-controls">
            <label
              >报告期
              <select v-model="holdingDate" aria-label="行业持股报告期">
                <option v-for="d in holdingDates" :key="d">{{ d }}</option>
              </select>
            </label>
          </div>
        </template>
      </CapitalBars>
      <FinancingChart
        :title="`${industryName} · 机构持股比例历史`"
        :rows="holdingHistory"
        :lines="holdingLines"
        :initial-range="1095"
        allow-table
        note="季度重仓与半年、年度披露范围不同。"
      >
        <template #toolbar>
          <div class="controls chart-controls">
            <label
              >行业
              <select v-model="industry" aria-label="持股行业">
                <option v-for="r in industryOptions" :key="String(r.code)" :value="r.code">{{
                  r.name
                }}</option>
              </select>
            </label>
          </div>
        </template>
      </FinancingChart>
    </section>
    <CapitalHandbookDemo
      v-for="demo in otherDemos"
      :key="demo.id"
      :demo-id="demo.id"
      :comparison-ids="demo.id === 'foreign-pmi' ? FOREIGN_COMPARISON_IDS : undefined"
    />
  </section>
</template>
<script setup lang="ts">
  import { computed, defineAsyncComponent, ref, watch } from 'vue';
  import Decimal from 'decimal.js';
  import type { CapitalDashboard, CapitalRow } from '@/api/platform/aShareCapital';
  import FinancingChart, { type FinanceLine } from './FinancingChart.vue';
  import CapitalBars from './CapitalBars.vue';
  import CapitalEventsTable from './CapitalEventsTable.vue';
  import InstitutionalCapitalPanel from './InstitutionalCapitalPanel.vue';
  import { buildCapitalDemo, demoPeriods } from './capitalHandbookDemoData';
  import { DEMO_CATALOG, FOREIGN_COMPARISON_IDS } from './capitalHandbookDemoCatalog';

  const CapitalHandbookDemo = defineAsyncComponent(() => import('./CapitalHandbookDemo.vue'));
  const otherDemos = computed(() =>
    props.mode === 'others'
      ? DEMO_CATALOG.filter(
          (demo) =>
            demo.category === category.value &&
            demo.id !== 'foreign-quarter-flow' &&
            !FOREIGN_COMPARISON_IDS.slice(1).includes(demo.id) &&
            (demo.id !== 'resident-market' || !hasResidentMarket.value) &&
            (demo.id !== 'foreign-value-share' || !hasForeignValueShare.value) &&
            (demo.id !== 'foreign-sector-rank' || !northReport.value) &&
            (demo.id !== 'pension-enterprise' || !hasPensionResearch.value) &&
            (demo.id !== 'pension-occupation' || !handbook.value.occupationalPension?.length),
        )
      : [],
  );

  const foreignMetrics = { value: '外资 · 披露持股市值', flow: '外资季度净买入 · Demo' };
  const foreignMetric = ref<keyof typeof foreignMetrics>('value');
  const foreignDemoPeriod = ref(demoPeriods.at(-1)!);
  const foreignFlow = computed(() =>
    buildCapitalDemo('foreign-quarter-flow', foreignDemoPeriod.value),
  );

  const props = defineProps<{
    data: CapitalDashboard;
    mode: 'overview' | 'funds' | 'fund-research' | 'margin' | 'others';
  }>();
  const titles = {
    overview: '资金面总览',
    funds: '规模与份额变化',
    'fund-research': '扩展研究 · 行业持股偏好',
    margin: '融资行业结构',
    others: '其他资金',
  };
  const colors = ['#174e76', '#ce9a42', '#67a6bd', '#df8079', '#798b70', '#9482a1'];
  const line = (key: string, name: string, unit: string, index = 0, bar = false): FinanceLine => ({
    key,
    name,
    unit,
    color: colors[index],
    bar,
  });
  const categories = [
    { key: 'foreign', label: '外资', detail: '境外持股与QFII' },
    { key: 'insurance', label: '险资', detail: '规模与行业配置' },
    { key: 'pension', label: '养老资金', detail: '社保与企业年金' },
    { key: 'resident', label: '居民资金', detail: '开户与参与' },
    { key: 'private', label: '私募', detail: '存续与备案' },
    { key: 'corporate', label: '产业资本', detail: '回购与增减持' },
    { key: 'demand', label: '融资需求', detail: '发行与解禁' },
    { key: 'bank', label: '银行理财', detail: '规模与资产配置' },
  ];
  const category = ref('foreign'),
    reportBasis = ref('half'),
    holdingDate = ref(''),
    marginDate = ref(''),
    industry = ref('B_009001006006');
  const institutionMetrics = {
    change: '机构持股市值变动',
    value: '主要机构披露持股市值',
  };
  const institutionMetric = ref<keyof typeof institutionMetrics>('change');
  const overviewReportBasis = ref('quarter');
  const institutionRoles = {
    main: {
      label: '主要机构',
      keys: ['fund', 'insurance', 'insuranceProduct', 'qfii', 'social', 'pension'],
    },
    fund: { label: '基金及基金资管', keys: ['fund', 'fundManager', 'fundAssetPlan'] },
    insurance: { label: '保险资金', keys: ['insurance', 'insuranceProduct'] },
    foreign: { label: '外资 · QFII', keys: ['qfii'] },
    pension: { label: '养老资金', keys: ['social', 'pension'] },
    broker: { label: '券商及集合资管', keys: ['broker', 'brokerCollective'] },
    bank: { label: '银行', keys: ['bank'] },
    trust: { label: '信托', keys: ['trust', 'trustPlan'] },
  };
  const institutionRole = ref<keyof typeof institutionRoles>('main');
  const categoryLabel = computed(
    () => categories.find((c) => c.key === category.value)?.label || '',
  );
  const handbook = computed(() => props.data.handbook || {});
  const fundBenchmarkQuarter = ref('');
  const fundBenchmark = computed(() => {
    const reports = handbook.value.fundIndustryBenchmarks;
    return reports?.find((report) => report.date === fundBenchmarkQuarter.value) || reports?.at(-1);
  });
  watch(
    fundBenchmark,
    (report) => {
      fundBenchmarkQuarter.value = report?.date || '';
    },
    { immediate: true },
  );
  const premiumRows = computed(() => props.data.institutions?.insurancePremium?.rows || []);
  const northQuarter = ref('');
  const northReport = computed(() => {
    const reports = handbook.value.northIndustryReports;
    return reports?.find((report) => report.date === northQuarter.value) || reports?.at(-1);
  });
  watch(
    northReport,
    (report) => {
      northQuarter.value = report?.date || '';
    },
    { immediate: true },
  );
  const pensionReturns = computed(() =>
    [
      line('periodReturnPct', '本期加权平均收益率', '%', 0, true),
      line('threeYearReturnPct', '近三年累计收益率', '%', 1, true),
    ].filter(({ key }) => handbook.value.pension?.some((row) => row[key] != null)),
  );
  const hasPensionResearch = computed(() =>
    Boolean(handbook.value.pension?.length && pensionReturns.value.length),
  );
  const fundReportDate = ref('');
  const selectedFundReport = computed(() => {
    const reports = handbook.value.fundStockReports;
    return reports?.find((report) => report.date === fundReportDate.value) || reports?.at(-1);
  });
  watch(
    selectedFundReport,
    (report) => {
      fundReportDate.value = report?.date || '';
    },
    { immediate: true },
  );
  const hasForeignValueShare = computed(() => Boolean(handbook.value.foreignValueShare?.length));
  const foreignLines = computed(() => [
    line('equities', '股票市值', '亿元'),
    ...(hasForeignValueShare.value
      ? [{ ...line('sharePct', '占A股市值比例', '%', 1), right: true }]
      : []),
  ]);
  const eventSeries = computed(() => [
    {
      key: 'seasonedIssuance',
      title: '增发披露金额',
      data: handbook.value.capitalEvents?.['capital-events-seasoned-issues'],
    },
    {
      key: 'dividends',
      title: '税前现金分红',
      data: handbook.value.capitalEvents?.['capital-events-cash-dividends'],
    },
  ]);
  const eventLines = computed(() =>
    eventSeries.value.flatMap(({ key, title, data }, i) =>
      data?.rows.length ? [line(key, title, '亿元', i, true)] : [],
    ),
  );
  const eventMonthly = computed(() => {
    const rows = new Map<string, CapitalRow>();
    for (const { data } of eventSeries.value) {
      for (const row of data?.rows || []) rows.set(row.date, { ...rows.get(row.date), ...row });
    }
    return [...rows.values()].sort((left, right) => left.date.localeCompare(right.date));
  });
  const hasResidentMarket = computed(() => Boolean(handbook.value.residentMarket?.length));
  const latestBank = computed(() => handbook.value.bank?.at(-1));
  const formatAmount = (value: unknown) =>
    value == null || value === '' || !Number.isFinite(Number(value))
      ? '—'
      : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 });
  const publicStatus = (key: string) =>
    ['error', 'partial'].includes(handbook.value.publicSources?.[key]?.status || '')
      ? ' · 更新暂不可用'
      : '';
  const foreignMonthly = computed(() => {
    const shares = new Map(
      handbook.value.foreignValueShare?.map((row) => [row.date, row.sharePct]),
    );
    const values = (handbook.value.foreign || []).filter(
      (row) => row.date.slice(0, 7) >= monthCutoff.value,
    );
    if (!values.length) return [];
    const start = new Date(values[0].date.slice(0, 7) + '-01T00:00:00Z');
    const end = values.at(-1)!.date.slice(0, 7);
    const rows: CapitalRow[] = [];
    while (start.toISOString().slice(0, 7) <= end) {
      const month = start.toISOString().slice(0, 7);
      rows.push(
        values.find((r) => r.date.startsWith(month)) || { date: month + '-01', equities: null },
      );
      start.setUTCMonth(start.getUTCMonth() + 1);
    }
    return rows.map((row) => ({ ...row, sharePct: shares.get(row.date) ?? null }));
  });
  const monthCutoff = computed(
    () => `${Number(props.data.asOf.slice(0, 4)) - 3}${props.data.asOf.slice(4, 7)}`,
  );
  const holdingDates = computed(() =>
    [...new Set((handbook.value.holdings || []).map((r) => r.date))].sort(),
  );
  const marginDates = computed(() =>
    [...new Set((handbook.value.margins || []).map((r) => r.date))].sort(),
  );
  watch(
    holdingDates,
    (ds) => {
      if (!ds.includes(holdingDate.value)) holdingDate.value = ds.at(-1) || '';
    },
    { immediate: true },
  );
  watch(
    marginDates,
    (ds) => {
      if (!ds.includes(marginDate.value)) marginDate.value = ds.at(-1) || '';
    },
    { immediate: true },
  );
  const institutionLines = [
    line('fund', '基金', '亿元', 0, true),
    line('insurance', '保险公司', '亿元', 1, true),
    line('insuranceProduct', '保险产品', '亿元', 2, true),
    line('qfii', 'QFII', '亿元', 3, true),
    line('social', '社保基金', '亿元', 4, true),
    line('pension', '企业年金', '亿元', 5, true),
  ];
  const institutionRows = computed(() =>
    (handbook.value.institutions || []).filter((r) =>
      reportBasis.value === 'half' ? /-(06|12)-/.test(r.date) : /-(03|09)-/.test(r.date),
    ),
  );
  const overviewInstitutionLines = computed(() =>
    [
      ...institutionLines,
      line('fundManager', '基金管理公司', '亿元', 1, true),
      line('fundAssetPlan', '基金资产管理计划', '亿元', 2, true),
      line('broker', '券商', '亿元', 0, true),
      line('brokerCollective', '券商集合理财', '亿元', 1, true),
      line('bank', '银行', '亿元', 0, true),
      line('trust', '信托公司', '亿元', 0, true),
      line('trustPlan', '信托计划', '亿元', 1, true),
    ]
      .filter((series) => institutionRoles[institutionRole.value].keys.includes(series.key))
      .map((series): FinanceLine => ({ ...series, barColor: 'series' })),
  );
  const overviewInstitutionRows = computed(() => {
    const reports = (handbook.value.institutions || []).filter((row) =>
      overviewReportBasis.value === 'half'
        ? /-(06|12)-/.test(row.date)
        : /-(03|09)-/.test(row.date),
    );
    if (institutionMetric.value === 'value') return reports;
    return reports.flatMap((current, index) => {
      const previous = reports[index - 1];
      const monthIndex = (day: string) => Number(day.slice(0, 4)) * 12 + Number(day.slice(5, 7));
      if (!previous || monthIndex(current.date) - monthIndex(previous.date) !== 6) return [];
      const change: CapitalRow = { date: current.date };
      for (const { key } of overviewInstitutionLines.value) {
        const now = current[key],
          before = previous[key];
        if (numeric(now) !== null && numeric(before) !== null) {
          change[key] = new Decimal(now!).minus(before!).toString();
        }
      }
      return Object.keys(change).length > 1 ? [change] : [];
    });
  });
  const issueLines: FinanceLine[] = [
    { ...line('stock', '股票型', '亿份', 0, true), color: '#2563eb', barColor: 'series' },
    { ...line('mixed', '混合型', '亿份', 1, true), color: '#0d9488', barColor: 'series' },
  ];
  const issuanceLines = [
    line('ipo', '首发', '亿元', 0, true),
    line('seo', '增发', '亿元', 1, true),
    line('rights', '配股', '亿元', 2, true),
  ];
  const holdingKeys = computed(() =>
    props.mode === 'fund-research'
      ? ['fund']
      : category.value === 'insurance'
      ? ['insurance', 'insuranceProduct']
      : category.value === 'foreign'
      ? ['qfii']
      : ['social', 'pension'],
  );
  const holdingLines = computed(() =>
    institutionLines
      .filter((l) => holdingKeys.value.includes(l.key))
      .map((l) => ({ ...l, unit: '%', bar: false })),
  );
  const disclosedHoldingLines = computed<FinanceLine[]>(() =>
    holdingLines.value.map((l) => ({ ...l, unit: '亿元', bar: true, barColor: 'series' })),
  );
  const holdingTitle = computed(() =>
    props.mode === 'fund-research' ? '基金' : categoryLabel.value,
  );
  const showHoldings = computed(
    () =>
      props.mode === 'fund-research' ||
      (props.mode === 'others' && ['insurance', 'foreign', 'pension'].includes(category.value)),
  );
  const numeric = (v: unknown): number | null =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  const holdingCross = computed(() =>
    (handbook.value.holdings || [])
      .filter((r) => r.date === holdingDate.value)
      .slice()
      .sort(
        (a, b) =>
          (numeric(b[holdingKeys.value[0]]) ?? -Infinity) -
          (numeric(a[holdingKeys.value[0]]) ?? -Infinity),
      )
      .map((r) => ({ ...r, date: String(r.name) })),
  );
  const industryOptions = computed(() =>
    (handbook.value.holdings || []).filter((r) => r.date === holdingDates.value.at(-1)),
  );
  const industryName = computed(
    () => industryOptions.value.find((r) => r.code === industry.value)?.name || '所选行业',
  );
  const holdingHistory = computed(() =>
    (handbook.value.holdings || []).filter((r) => r.code === industry.value),
  );
  const marginCross = computed(() =>
    (handbook.value.margins || [])
      .filter((r) => r.date === marginDate.value)
      .slice()
      .sort((a, b) => (numeric(b.balance) ?? -Infinity) - (numeric(a.balance) ?? -Infinity))
      .map((r) => ({ ...r, date: String(r.name) })),
  );
  const marginHistory = computed(() =>
    (handbook.value.margins || []).filter((r) => r.code === industry.value),
  );
  const technologyMargin = computed(() =>
    marginDates.value.map((date) => {
      const rows = (handbook.value.margins || []).filter(
        (r) => r.date === date && ['电子', '计算机', '传媒', '通信'].includes(String(r.name)),
      );
      if (
        rows.length !== 4 ||
        rows.some((r) => numeric(r.balance) == null || numeric(r.freeValue) == null)
      )
        return { date, balance: null, share: null };
      const b = rows.reduce((s, r) => s.plus(String(r.balance)), new Decimal(0));
      const all = (handbook.value.margins || []).filter((r) => r.date === date);
      const total =
        all.length === 31 && all.every((r) => numeric(r.balance) != null)
          ? all.reduce((s, r) => s.plus(String(r.balance)), new Decimal(0))
          : null;
      return {
        date,
        balance: b.toString(),
        share: total?.gt(0) ? b.div(total).mul(100).toString() : null,
      };
    }),
  );
  const buybackMonths = computed(() => {
    const plans = new Map<string, CapitalRow>();
    for (const r of props.data.sources.buybacks.rows)
      if (!plans.has(String(r.id)) || plans.get(String(r.id))!.date < r.date)
        plans.set(String(r.id), r);
    const months = new Map<string, Array<CapitalRow>>();
    for (const r of plans.values()) {
      const m = r.date.slice(0, 7);
      months.set(m, [...(months.get(m) || []), r]);
    }
    return [...months]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, rows]) => ({
        date,
        amount: rows.some((r) => numeric(r.amount) == null)
          ? null
          : rows.reduce((s, r) => s.plus(String(r.amount)), new Decimal(0)).toString(),
      }));
  });
</script>
<style scoped>
  .capital-handbook {
    min-width: 0;
  }

  .heading {
    display: flex;
    justify-content: space-between;
    margin: 22px 0 16px;
  }

  .heading h2 {
    margin: 0;
    color: var(--strategy-text-1);
    font-size: 20px;
    letter-spacing: 0.02em;
  }

  .heading p {
    margin: 8px 0 0;
    color: var(--strategy-text-3);
    font-size: 13px;
  }

  .category-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 16px 0 24px;
  }

  .category-grid button {
    display: flex;
    flex-direction: column;
    padding: 15px 18px;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    text-align: left;
    cursor: pointer;
    gap: 6px;
  }

  .category-grid button[aria-pressed='true'] {
    border-color: #174e76;
    background: var(--strategy-accent-soft);
    box-shadow: inset 3px 0 #174e76;
  }

  .category-grid span {
    font-size: 14px;
    font-weight: 600;
  }

  .category-grid small {
    color: var(--strategy-text-3);
    font-size: 11px;
  }

  .chart-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    margin: 18px 0;
  }

  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 18px 0;
    font-size: 12px;
    gap: 16px;
  }

  .controls h3 {
    margin: 0 auto 0 0;
    font-size: 16px;
  }

  .controls select {
    padding: 6px 9px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface);
    color: inherit;
  }

  .other-table-card {
    padding: 16px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface);
  }

  .chart-source {
    margin: 0;
  }

  .chart-controls {
    margin: 0;
  }

  .institution-controls {
    gap: 6px 12px;
    margin: 0;
  }

  .institution-controls label {
    white-space: nowrap;
  }

  .institution-chart :deep(header > h3) {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }

  .institution-tabs {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }

  .institution-tabs button {
    padding: 6px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 6px;
    background: var(--strategy-surface);
    color: inherit;
    cursor: pointer;
  }

  .institution-tabs button[aria-pressed='true'] {
    border-color: #2376a4;
    color: #2376a4;
    font-weight: 600;
  }

  .fund-stock-table {
    overflow-x: auto;
    border: 1px solid var(--strategy-border);
    border-radius: 10px;
    background: var(--strategy-surface);
  }

  .fund-stock-table table {
    width: 100%;
    border-collapse: collapse;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  .fund-stock-table :is(th, td) {
    padding: 9px 14px;
    border-bottom: 1px solid var(--strategy-border);
    text-align: left;
  }

  .fund-stock-table :is(th, td):nth-child(n + 3) {
    text-align: right;
  }

  .fund-stock-table tbody tr:last-child td {
    border-bottom: 0;
  }

  .bank-summary {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    margin: 18px 0;
  }

  .bank-summary dt {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .bank-summary dd {
    margin: 6px 0 0;
    font-size: 22px;
    font-weight: 600;
  }

  .bank-summary small {
    margin-left: 6px;
    font-size: 12px;
    font-weight: 400;
  }

  .source,
  .missing-card p {
    color: var(--strategy-text-3);
    font-size: 12px;
    line-height: 1.8;
  }

  .missing-card {
    padding: 28px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
  }

  .missing-card h3 {
    color: var(--strategy-text-1);
    font-size: 16px;
  }

  @media (max-width: 1000px) {
    .chart-grid {
      grid-template-columns: minmax(0, 1fr);
    }
  }

  @media (max-width: 600px) {
    .category-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px;
    }

    .category-grid button {
      padding: 12px;
    }

    .heading h2 {
      font-size: 18px;
    }
  }
</style>
