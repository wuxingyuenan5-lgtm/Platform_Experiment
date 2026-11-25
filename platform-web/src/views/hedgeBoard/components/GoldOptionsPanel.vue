<template>
  <div class="gold-research">
    <p v-if="error || !data?.snapshot" class="gold-warning">{{
      error ||
      (data ? '期权数据未落地：尚未取得可校验的完整 CME 公告与历史期权链。' : '正在读取期权数据…')
    }}</p>
    <div v-show="data?.snapshot">
      <div class="gold-controls">
        <button :class="{ active: mode === 'curve' }" @click="mode = 'curve'"
          >内在价值与最大痛点</button
        >
        <button :class="{ active: mode === 'ratio' }" @click="mode = 'ratio'"
          >Put / Call · EMA30</button
        >
        <button :class="{ active: mode === 'call' }" @click="mode = 'call'"
          >Call 成交量 · EMA30</button
        >
        <button :class="{ active: mode === 'put' }" @click="mode = 'put'"
          >Put 成交量 · EMA30</button
        >
        <select v-model="product" aria-label="期权品种"
          ><option value="OG">黄金</option
          ><option value="SO">白银</option></select
        >
        <select v-model="month" aria-label="期权合约月"
          ><option v-for="c in contracts" :key="c.month">{{ c.month }}</option></select
        >
        <button @click="table = !table">{{ table ? '查看图表' : '查看数据' }}</button>
      </div>
      <p class="gold-meta"
        >{{ data?.observationDate }} · {{ data?.snapshot?.preliminary ? '初步公告' : '正式公告' }} ·
        {{ data?.status === 'stale' ? '数据待更新 · ' : '' }}历史起点 {{ data?.coverageStart }}</p
      >
      <p v-if="mode === 'curve' && contract" class="gold-meta"
        >最大痛点 {{ contract.maxPain.join(' – ') }} USD/oz · 总内在价值最低
        {{ (contract.minimumIntrinsicValue / 1e6).toFixed(2) }} 百万美元</p
      >
      <p v-if="mode !== 'curve' && !hasEma" class="gold-meta"
        >目前有 {{ data?.history?.length || 0 }} 个交易日，连续历史达到 30 个交易日后显示 EMA30。</p
      >
      <div
        v-show="!table"
        ref="chartRef"
        class="options-chart"
        role="img"
        aria-label="金银期权成交与内在价值"
      ></div>
      <div v-if="table" class="gold-table"
        ><table
          ><thead
            ><tr
              ><th>{{ mode === 'curve' ? '标的价格 USD/oz' : '日期' }}</th
              ><th>{{ mode === 'curve' ? '总内在价值 USD' : 'EMA30' }}</th></tr
            ></thead
          ><tbody
            ><tr v-for="(r, i) in points" :key="i"
              ><td>{{ r[0] }}</td
              ><td>{{ r[1] ?? '—' }}</td></tr
            ></tbody
          ></table
        ></div
      >
      <section aria-label="金银期权持仓结构">
        <h3>{{ product === 'OG' ? '黄金' : '白银' }} · {{ month }} 持仓结构 · 新增</h3>
        <template v-if="structure">
          <p class="gold-meta"
            >Call持仓 {{ structure.callOi.toLocaleString() }} 张 · Put持仓
            {{ structure.putOi.toLocaleString() }} 张 · OI Put/Call
            {{ structure.oiRatio == null ? '—' : structure.oiRatio.toFixed(3) }}；所选合约当日成交
            Call {{ structure.callVolume.toLocaleString() }} / Put
            {{ structure.putVolume.toLocaleString() }} 张。</p
          >
          <div class="gold-table"
            ><table
              ><thead
                ><tr
                  ><th>行权价 USD/oz</th><th>Call持仓</th><th>Put持仓</th><th>Call成交</th
                  ><th>Put成交</th></tr
                ></thead
              ><tbody>
                <tr v-for="r in structure.rows" :key="r.strike"
                  ><td>{{ r.strike }}</td
                  ><td>{{ r.callOi ?? '—' }}</td
                  ><td>{{ r.putOi ?? '—' }}</td
                  ><td>{{ r.callVolume ?? '—' }}</td
                  ><td>{{ r.putVolume ?? '—' }}</td></tr
                >
              </tbody></table
            ></div
          >
          <p class="gold-meta"
            >持仓比仅含所选合约月，与上方跨月成交EMA比不同。未列示的一侧保留为空；OI不识别买卖方方向，不能据此推断净多空或做市商Gamma。</p
          >
        </template>
        <p v-else class="gold-meta"
          >当前合约未取得完整且通过校验的双边行权价持仓，结构表暂不可用。</p
        >
      </section>
      <details
        ><summary>计算口径</summary
        ><p
          >黄金 OG 和白银 SO 月度期权，成交量覆盖全部合约月。EMA30 的平滑系数为
          2/31，以首日成交量初始化；Put/Call 为两项 EMA30 的比值。IV 指内在价值，不是隐含波动率。</p
        ><p
          >内在价值按每个行权价的 Call/Put
          未平仓量及合约乘数求和；最大痛点是总内在价值最低的标的价格，仅表示静态到期支付结构。未取得同日对应期货结算价时，不计算溢折价和
          ΔIV。</p
        ></details
      >
    </div>
    <GoldReferenceSnapshots group="options" :options-ready="!!data?.snapshot" />
    <p class="gold-meta"
      ><a
        href="https://www.cmegroup.com/market-data/daily-bulletin.html"
        target="_blank"
        rel="noopener noreferrer"
        >CME 每日公告 ↗</a
      ></p
    >
  </div>
</template>
<script setup lang="ts">
  import { computed, nextTick, ref, shallowRef, watch, type Ref } from 'vue';
  import { useECharts } from '@/hooks/web/useECharts';
  import { optionStructure, type OptionStrike } from './goldStructureAnalysis';
  import { goldRequest } from './goldResearch';
  import GoldReferenceSnapshots from './GoldReferenceSnapshots.vue';
  import { useDashboardRefresh } from '../useDashboardRefresh';

  interface Contract {
    calls?: OptionStrike[];
    puts?: OptionStrike[];
    product: string;
    month: string;
    maxPain: number[];
    minimumIntrinsicValue: number;
    curve: { price: number; intrinsicValue: number }[];
  }
  interface OptionsData {
    status: string;
    observationDate?: string;
    coverageStart?: string;
    snapshot?: { preliminary: boolean; contracts: Contract[] };
    history?: ({ date: string } & Record<string, string | number | null>)[];
  }
  const data = shallowRef<OptionsData>();
  const error = ref('');
  const product = ref('OG');
  const month = ref('');
  const mode = ref('curve');
  const table = ref(false);
  const contracts = computed(
    () => data.value?.snapshot?.contracts.filter((c) => c.product === product.value) || [],
  );
  watch(contracts, () => {
    if (!contracts.value.some((c) => c.month === month.value))
      month.value = contracts.value[0]?.month || '';
  });
  const contract = computed(() => contracts.value.find((c) => c.month === month.value));
  const structure = computed(() =>
    optionStructure(contract.value?.calls || [], contract.value?.puts || []),
  );
  const points = computed<[string | number, string | number | null][]>(() =>
    mode.value === 'curve'
      ? contract.value?.curve.map((r): [number, number] => [r.price, r.intrinsicValue]) || []
      : (data.value?.history || []).map((r): [string, string | number | null] => [
          r.date,
          r[product.value + (mode.value === 'ratio' ? 'ratio' : mode.value + 'Ema30')],
        ]),
  );
  const hasEma = computed(() => points.value.some((r) => r[1] != null));
  const chartRef = ref<HTMLDivElement | null>(null);
  const chart = useECharts(chartRef as Ref<HTMLDivElement>, 'light');
  watch([points, table, chartRef], async () => {
    await nextTick();
    if (!table.value && data.value?.snapshot) {
      chart.setOptions(
        {
          animation: false,
          tooltip: { trigger: 'axis', confine: true },
          grid: { left: 25, right: 25, top: 40, bottom: 75, containLabel: true },
          xAxis:
            mode.value === 'curve'
              ? { type: 'value', scale: true, name: 'USD/oz' }
              : { type: 'category', data: points.value.map((r) => r[0]) },
          yAxis: {
            type: 'value',
            scale: true,
            name: mode.value === 'curve' ? 'USD' : mode.value === 'ratio' ? 'Put / Call' : '合约',
          },
          dataZoom: [{ type: 'inside' }, { type: 'slider', height: 22, bottom: 10 }],
          series: [
            {
              type: 'line',
              showSymbol: false,
              connectNulls: false,
              data: (mode.value === 'curve' ? points.value : points.value.map((r) => r[1])) as any,
              lineStyle: { color: '#b48a43', width: 2 },
            },
          ],
        },
        true,
      );
      chart.getInstance()?.resize();
    }
  });
  useDashboardRefresh(async () => {
    try {
      data.value = await goldRequest<OptionsData>('gold-options');
      error.value = '';
    } catch {
      error.value = '期权数据暂不可用，请稍后重试。';
    }
  });
</script>
<style scoped src="./goldResearch.css"></style>
<style scoped>
  .gold-table {
    max-height: 480px;
    overflow: auto;
  }

  .options-chart {
    width: 100%;
    height: 480px;
  }
</style>
