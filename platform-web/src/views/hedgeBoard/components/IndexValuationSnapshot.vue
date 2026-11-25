<template>
  <section class="valuation-snapshot" aria-labelledby="global-valuation-snapshot-title">
    <header class="snapshot-heading">
      <h3 id="global-valuation-snapshot-title">指数估值观察表</h3>
      <span
        >近10年历史分位 · <time :datetime="snapshotDate">{{ snapshotDate }}</time> 截图快照</span
      >
    </header>

    <div
      v-for="group in groups"
      :key="group.name"
      class="snapshot-table-scroll"
      tabindex="0"
      role="region"
      :aria-label="group.name"
    >
      <table>
        <caption>
          {{ group.name }} <span>{{ group.rows.length }} 个指数</span>
        </caption>
        <thead>
          <tr>
            <th scope="col">指数名称</th>
            <th scope="col">主观察指标</th>
            <th scope="col">当前值 / 历史分位</th>
            <th scope="col">估值判断</th>
            <th v-for="column in comparisonColumns" :key="column" scope="col">{{ column }}</th>
            <th scope="col">场内基金</th>
            <th scope="col">场外基金</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in group.rows" :key="row.code">
            <th scope="row">
              {{ row.name }}
              <small class="index-code">{{ row.code }}</small>
            </th>
            <td>
              <span class="metric-badge" :class="`metric-${row.metric.toLowerCase()}`">
                {{ row.metric }}
              </span>
              <small class="metric-label">{{ metricLabels[row.metric] }}</small>
            </td>
            <td>
              <div class="primary-reading">
                <strong>{{ row.primary }}</strong>
                <span class="percentile-track" aria-hidden="true">
                  <span :style="{ left: `${row.percentile}%` }"></span>
                </span>
                <span>{{ row.percentile.toFixed(1) }}%</span>
              </div>
            </td>
            <td>
              <span class="valuation-tier" :class="`tier-${row.tier}`">{{
                tierLabels[row.tier]
              }}</span>
            </td>
            <td v-for="reading in row.readings" :key="reading.metric" class="comparison-reading">
              {{ reading.value }}
              <small
                :class="`rank-${valuationTier(
                  reading.metric === 'DY' ? 100 - reading.rank : reading.rank,
                )}`"
                >{{ reading.rank }}%</small
              >
            </td>
            <td v-for="(fund, index) in row.funds" :key="index" class="fund-cell">
              <template v-if="fund">
                <span class="fund-code">{{ fund.code }}</span>
                <small v-if="fund.approximate" class="fund-approximate">近似</small>
                <small v-if="fund.label" class="fund-label">{{ fund.label }}</small>
              </template>
              <small v-else class="unmapped">无对应产品</small>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { globalMarketGroup, snapshotDate } from './indexValuationSnapshot';

  const metricLabels = { PE: '市盈率', PB: '市净率', DY: '股息率', PS: '市销率' };
  const comparisonColumns = ['PE', 'PB', '股息率'];
  const tierLabels = { low: '低估', lower: '合理偏低', upper: '合理偏高', high: '高估' };

  function valuationTier(percentile: number): keyof typeof tierLabels {
    if (percentile <= 20) return 'low';
    if (percentile < 50) return 'lower';
    if (percentile < 80) return 'upper';
    return 'high';
  }

  function formatFund(fund: string | null) {
    if (!fund) return null;
    const [code, label] = fund.split('|');
    return { code: code.replace(/~$/, ''), approximate: code.endsWith('~'), label };
  }

  const groups = [globalMarketGroup].map((group) => ({
    name: group.name,
    rows: group.rows.map(
      ([name, code, metric, percentile, pe, pb, dividend, listed, unlisted, ps]) => {
        const value = { PE: pe[0], PB: pb[0], DY: dividend[0], PS: ps }[metric];
        return {
          name,
          code,
          metric,
          percentile,
          primary: value === undefined ? '—' : `${value.toFixed(2)}${metric === 'DY' ? '%' : '倍'}`,
          tier: valuationTier(percentile),
          readings: [
            { metric: 'PE', value: pe[0].toFixed(2), rank: pe[1] },
            { metric: 'PB', value: pb[0].toFixed(2), rank: pb[1] },
            { metric: 'DY', value: `${dividend[0].toFixed(2)}%`, rank: dividend[1] },
          ],
          funds: [formatFund(listed), formatFund(unlisted)],
        };
      },
    ),
  }));
</script>

<style scoped>
  .valuation-snapshot {
    display: grid;
    min-width: 0;
    gap: 12px;
    margin-top: 16px;
    color: #243a51;
    font-size: 13px;
  }

  .snapshot-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    color: #596f87;
    font-size: 12px;
    gap: 4px 14px;
  }

  .snapshot-heading h3 {
    margin: 0;
    color: #10233d;
    font-size: 16px;
  }

  .snapshot-table-scroll {
    min-width: 0;
    overflow-x: auto;
    border: 1px solid #d9e3ee;
    border-radius: 8px;
    background: #fff;
  }

  .snapshot-table-scroll:focus-visible {
    outline: 2px solid #1d4ed8;
    outline-offset: 2px;
  }

  table {
    width: 100%;
    min-width: 890px;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }

  caption {
    padding: 8px 12px;
    caption-side: top;
    border-left: 4px solid #225371;
    background: #f6f9fc;
    color: #1d3950;
    font-size: 14px;
    font-weight: 600;
    text-align: left;
  }

  caption span {
    margin-left: 8px;
    color: #596f87;
    font-size: 11px;
    font-weight: 400;
  }

  th,
  td {
    padding: 6px 8px;
    border-top: 1px solid #e3ebf3;
    text-align: center;
    white-space: nowrap;
  }

  thead {
    background: #edf3f8;
    color: #354d68;
    font-size: 12px;
  }

  th:first-child {
    padding-left: 12px;
    text-align: left;
  }

  .index-code,
  .metric-label {
    display: block;
    color: #596f87;
    font-size: 11px;
    font-weight: 400;
  }

  .metric-badge {
    display: inline-block;
    min-width: 28px;
    padding: 1px 4px;
    border-radius: 4px;
    color: #fff;
    font-size: 11px;
    font-weight: 600;
  }

  .metric-pe {
    background: #326da8;
  }

  .metric-pb {
    background: #7550a3;
  }

  .metric-dy {
    background: #955e0d;
  }

  .metric-ps {
    background: #107b7c;
  }

  .primary-reading {
    display: grid;
    grid-template-columns: 8ch minmax(86px, 132px) 6ch;
    align-items: center;
    justify-content: center;
    gap: 8px;
  }

  .primary-reading strong {
    font-size: 14px;
    text-align: right;
  }

  .primary-reading > span:last-child {
    font-size: 12px;
    text-align: right;
  }

  .percentile-track {
    position: relative;
    height: 10px;
    border-radius: 2px;
    background: linear-gradient(
      to right,
      #b9e5cb 20%,
      #d4eadc 20% 50%,
      #f4dca7 50% 80%,
      #f4c5bf 80%
    );
  }

  .percentile-track span {
    position: absolute;
    top: -3px;
    bottom: -3px;
    width: 2px;
    transform: translateX(-50%);
    background: #1d3950;
    box-shadow: 0 0 0 1px #fff;
  }

  .percentile-track span::before {
    content: '';
    position: absolute;
    top: -1px;
    left: 50%;
    transform: translateX(-50%);
    border: 3px solid transparent;
    border-top-color: #1d3950;
  }

  .valuation-tier {
    display: inline-block;
    min-width: 48px;
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
  }

  .tier-low {
    background: #d4eedf;
    color: #17613e;
  }

  .tier-lower {
    background: #e5f3ea;
    color: #22674c;
  }

  .tier-upper {
    background: #fbefd8;
    color: #81530c;
  }

  .tier-high {
    background: #fbe3e0;
    color: #a33329;
  }

  .comparison-reading small {
    font-size: 11px;
  }

  .rank-low,
  .rank-lower {
    color: #23734f;
  }

  .rank-upper {
    color: #85580e;
  }

  .rank-high {
    color: #a33329;
  }

  .fund-code {
    font-weight: 600;
  }

  .fund-label {
    display: block;
    color: #596f87;
    font-size: 10px;
    font-weight: 400;
  }

  .fund-approximate {
    margin-left: 4px;
    color: #81530c;
    font-size: 10px;
  }

  .unmapped {
    color: #596f87;
  }
</style>
