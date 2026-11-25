<template>
  <section class="etf-methodology" aria-label="ETF持仓基准与方法论">
    <section class="panel" aria-labelledby="etf-baseline-title">
      <header>
        <h3 id="etf-baseline-title">国家队官方持仓基准</h3>
        <span v-if="baseline">{{ baseline.asof }} 来源：{{ baseline.source }}</span>
      </header>
      <p v-if="loading" role="status">正在读取持仓基准…</p>
      <p v-else-if="error" role="status">{{ error }} <button @click="load">重试</button></p>
      <template v-else-if="baseline">
        <p v-if="summary?.baselineStatus !== 'ready'" class="note" role="status"
          >更新暂未成功，当前显示已保留的披露基准。</p
        >
        <div class="table-scroll">
          <table>
            <thead
              ><tr
                ><th>机构</th><th>持有ETF数</th><th>持仓份额(亿份)</th><th>持仓市值(亿元)</th
                ><th>平均持仓占比</th></tr
              ></thead
            >
            <tbody>
              <tr v-for="holder in baseline.holders" :key="holder.name">
                <td>{{ holder.name }}</td
                ><td>{{ format(holder.etf_count) }}</td
                ><td>{{ format(holder.shares_yi) }}</td
                ><td>{{ format(holder.value_yi) }}</td
                ><td>{{ holder.avg_pct == null ? '—' : `${format(holder.avg_pct, 1)}%` }}</td>
              </tr>
            </tbody>
            <tfoot
              ><tr
                ><td>合计</td><td></td><td></td><td>{{ format(baseline.total_value_yi) }}</td
                ><td></td></tr
            ></tfoot>
          </table>
        </div>
        <p class="note"
          >{{
            baseline.note
          }}
          国家队持仓随基金定期报告披露；表中统计范围沿用原披露，日度ETF净申赎不能直接归因于某一机构。</p
        >
      </template>
      <p v-else role="status">暂无已采集的持仓披露基准。</p>
    </section>
    <details class="panel">
      <summary>方法论</summary>
      <dl>
        <div
          ><dt>监控范围</dt
          ><dd
            >ETF总览统一统计已跟踪的12类宽基ETF目录，资金卡、日度成交额、净流入图表、双创比例及历史信号使用相同目录，显示实际日期及覆盖数。固定25只ETF仅用于盘中分钟监测。日度份额和申赎为各ETF全部持有人合计，不能直接归因于某一机构。</dd
          ></div
        >
        <div
          ><dt>数据来源</dt
          ><dd
            >份额来自沪深交易所每日披露，单位净值来自基金公开净值接口，未复权价格与成交额来自公开日行情；日期按各数据实际观察日展示。</dd
          ></div
        >
        <div
          ><dt>净流入估算</dt
          ><dd
            >当日估算净流入＝相邻真实交易日份额变动×同日单位净值。近5日、近20日按交易日完整窗口求和，缺失值不补零；已核实的份额折算按精确比例调整前日份额。</dd
          ></div
        >
        <div
          ><dt>组合规模与成交额</dt
          ><dd
            >总览成交额为宽基目录各ETF二级市场实际成交金额合计，与净申赎分别统计；历史按当日已存续的目录成员计算。盘中分钟成交额采用固定25只ETF。</dd
          ></div
        >
        <div
          ><dt>期货席位</dt
          ><dd
            >中信期货净空头变动＝IH、IF、IC、IM四品种各合约卖单增减−买单增减，统计该会员全部客户，日期独立于ETF日度数据。</dd
          ></div
        >
        <div
          ><dt>官方持仓</dt
          ><dd
            >上表保留披露报告期、来源及原统计范围，与日度资金估算分开。持仓占比和机构归属以基金定期报告披露为准。</dd
          ></div
        >
      </dl>
    </details>
  </section>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue';
  import { getEtfObservation, type ObservationSnapshot } from '@/api/etfObservation';

  const props = defineProps<{ refreshKey?: number }>();
  const summary = shallowRef<ObservationSnapshot['summary']>();
  const baseline = computed(() => summary.value?.baseline);
  const loading = ref(true),
    error = ref('');
  let active = true;
  function format(value: number | null | undefined, digits = 0) {
    return value == null || !Number.isFinite(value)
      ? '—'
      : value.toLocaleString('zh-CN', {
          minimumFractionDigits: digits,
          maximumFractionDigits: digits,
        });
  }
  async function load() {
    loading.value = true;
    error.value = '';
    try {
      const data = await getEtfObservation();
      if (active) summary.value = data.summary;
    } catch {
      if (active) error.value = '持仓基准暂不可用。';
    } finally {
      if (active) loading.value = false;
    }
  }
  onMounted(load);
  watch(() => props.refreshKey, load);
  onBeforeUnmount(() => {
    active = false;
  });
</script>
<style scoped>
  .etf-methodology {
    margin-top: 14px;
    color: #243b53;
  }

  .panel {
    margin-bottom: 14px;
    padding: 14px;
    border: 1px solid #dbe4ee;
    border-radius: 10px;
    background: #fff;
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 10px;
  }

  h3 {
    margin: 0;
    font-size: 15px;
  }

  header span,
  .note {
    color: #64748b;
    font-size: 12px;
    line-height: 1.8;
  }

  .note {
    margin: 8px 0 0;
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 7px 8px;
    border-bottom: 1px solid #dbe4ee;
    text-align: right;
    white-space: nowrap;
  }

  th {
    color: #64748b;
    font-size: 12px;
    font-weight: 500;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }

  tfoot {
    font-weight: 700;
  }

  summary {
    color: #2864ec;
    font-size: 13px;
    cursor: pointer;
  }

  dl {
    margin: 10px 0 0;
    font-size: 12px;
    line-height: 1.8;
  }

  dl > div {
    display: flex;
  }

  dt {
    flex: 0 0 auto;
    font-weight: 600;
  }

  dt::after {
    content: '：';
  }

  dd {
    margin: 0;
  }
</style>
