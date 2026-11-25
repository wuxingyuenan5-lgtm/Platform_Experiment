<template>
  <div aria-label="机构规模与配置">
    <div v-if="!fixedKind" class="research-controls">
      <label v-if="!fixedKind"
        >资金类别
        <select v-model="kind">
          <option value="public">公募基金</option
          ><option value="private">私募证券基金</option
          ><option value="insurance">保险资金</option>
        </select></label
      >
    </div>
    <p v-if="kind !== 'public'" class="research-source"
      >{{ source?.provider || '—' }} · 统计期 {{ rows.at(-1)?.date || '—' }} · {{ status }}</p
    >
    <FinancingChart
      v-if="kind === 'public'"
      title="公募基金资产净值"
      :rows="rows"
      :lines="publicAssets"
      :initial-range="0"
      independent-dates
      allow-table
    >
      <template #toolbar>
        <div class="public-toolbar">
          <label>
            统计口径
            <select v-model="publicBasis" aria-label="统计口径">
              <option value="all">全体基金分类（新表）</option>
              <option value="open">开放式基金分类（旧表）</option>
            </select>
          </label>
          <span class="research-source">
            {{ source?.provider || '—' }} · 统计期 {{ rows.at(-1)?.date || '—' }} · {{ status }}
          </span>
        </div>
      </template>
    </FinancingChart>
    <div v-if="kind === 'public'" class="public-share-grid">
      <FinancingChart
        title="股票与混合基金份额月变化"
        :rows="changes"
        :lines="shareChanges"
        :initial-range="0"
        allow-table
        note="亿份；同口径相邻月份变化，含主动与被动产品。"
      />
      <slot name="issuance"></slot>
    </div>
    <template v-if="rows.length">
      <div v-if="kind !== 'public'" class="research-metrics">
        <article v-for="metric in metrics" :key="metric.key"
          ><span>{{ metric.name }}</span
          ><strong
            >{{ fmt(latest[metric.key]) }}<small>{{ metric.unit }}</small></strong
          ></article
        >
      </div>
      <template v-if="kind === 'private'">
        <FinancingChart
          title="私募证券基金存续规模"
          :rows="rows"
          :lines="privateAssets"
          :initial-range="0"
          independent-dates
          allow-table
        />
        <FinancingChart
          title="私募证券基金新备案规模"
          :rows="rows"
          :lines="privateNew"
          :initial-range="0"
          independent-dates
          allow-table
        />
        <FinancingChart
          title="私募证券基金数量"
          :rows="rows"
          :lines="[line('securitiesCount', '存续基金数量', '#2563eb', '只')]"
          :initial-range="0"
          independent-dates
          allow-table
        />
        <p class="research-note">规模含多种策略及FOF；新备案不等于净申购。</p>
      </template>
      <template v-else-if="kind === 'insurance'">
        <FinancingChart
          :key="insurer + '-total'"
          :title="insurerName + '资金运用规模'"
          :rows="rows"
          :lines="[line(insurer + 'Total', '资金运用余额', '#2563eb')]"
          :initial-range="0"
          independent-dates
          allow-table
        >
          <template #toolbar
            ><div class="public-toolbar">
              <label
                >机构
                <select v-model="insurer"
                  ><option value="life">人身险公司</option
                  ><option value="property">财产险公司</option></select
                ></label
              >
            </div></template
          >
        </FinancingChart>
        <FinancingChart
          :key="insurer + '-amount'"
          :title="insurerName + '资金配置账面余额'"
          :rows="rows"
          :lines="insuranceAmounts"
          :initial-range="0"
          independent-dates
          allow-table
        />
        <FinancingChart
          :key="insurer + '-ratio'"
          :title="insurerName + '配置比例'"
          :rows="rows"
          :lines="insuranceRatios"
          :initial-range="0"
          independent-dates
          allow-table
        />
        <p class="research-note"
          >比例以所选机构资金运用余额为分母；证券投资基金含非股票基金，账面余额变化不等于净买入。</p
        >
      </template>
      <details class="research-reference"
        ><summary>统计期与原始来源</summary>
        <div class="research-table"
          ><table
            ><thead
              ><tr><th>统计期</th><th>原始统计</th></tr></thead
            ><tbody>
              <tr v-for="row in [...rows].reverse()" :key="row.date"
                ><th>{{ row.date }}</th
                ><td
                  ><a :href="String(row.sourceUrl)" target="_blank" rel="noopener noreferrer"
                    >{{ row.sourceTitle }} ↗</a
                  ></td
                ></tr
              >
            </tbody></table
          ></div
        >
      </details>
    </template>
    <p v-else-if="kind !== 'public'" class="research-note">暂无已核验的公开统计。</p>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref } from 'vue';
  import Decimal from 'decimal.js';
  import type { CapitalSource } from '@/api/platform/aShareCapital';
  import FinancingChart, { type FinanceLine } from './FinancingChart.vue';
  import { formatResearch as fmt } from './researchFrameworkAnalysis';

  const props = defineProps<{ sources?: Record<string, CapitalSource>; fixedKind?: string }>();
  const selectedKind = ref('public');
  const kind = computed({
    get: () => props.fixedKind || selectedKind.value,
    set: (v) => {
      selectedKind.value = v;
    },
  });
  const insurer = ref('life'),
    publicBasis = ref('all');
  const source = computed(() => props.sources?.[kind.value]);
  const rows = computed(() =>
    (source.value?.rows || []).filter(
      (r) => kind.value !== 'public' || r.basis === publicBasis.value,
    ),
  );
  const latest = computed(() => rows.value.at(-1) || {});
  const status = computed(() =>
    !rows.value.length
      ? '暂无数据'
      : source.value?.status !== 'ready'
      ? '更新暂不可用'
      : source.value?.isStale
      ? '采集待更新'
      : '公开统计',
  );
  const insurerName = computed(() => (insurer.value === 'life' ? '人身险公司' : '财产险公司'));
  const line = (
    key: string,
    name: string,
    color: string,
    unit = '亿元',
    bar = false,
  ): FinanceLine => ({ key, name, color, unit, bar });
  const publicAssets = [
    line('stockAssets', '股票基金', '#2563eb'),
    line('mixedAssets', '混合基金', '#0d9488'),
  ];
  const publicShares = [
    line('stockShares', '股票基金份额', '#2563eb', '亿份'),
    line('mixedShares', '混合基金份额', '#0d9488', '亿份'),
  ];
  const shareChanges = publicShares.map(
    (l): FinanceLine => ({
      ...l,
      key: l.key + 'Change',
      name: l.name + '月变化',
      bar: true,
      barColor: 'series',
    }),
  );
  const privateAssets = [line('securitiesAssets', '私募证券基金', '#2563eb')];
  const privateNew = [line('newRegistered', '新备案规模', '#0d9488', '亿元', true)];
  const insuranceAmounts = computed(() => [
    line(insurer.value + 'Stock', '股票', '#2563eb'),
    line(insurer.value + 'Funds', '证券投资基金', '#0d9488'),
    line(insurer.value + 'Equity', '长期股权投资', '#a87932'),
  ]);
  const insuranceRatios = computed(() =>
    insuranceAmounts.value.map((l) => ({ ...l, key: l.key + 'Pct', unit: '%' })),
  );
  const metrics = computed(() =>
    kind.value === 'private'
      ? [...privateAssets, ...privateNew, line('securitiesCount', '存续基金数量', '', '只')]
      : [
          line(insurer.value + 'Total', insurerName.value + '资金运用余额', ''),
          line(insurer.value + 'Stock', '股票账面余额', ''),
          line(insurer.value + 'StockPct', '股票配置比例', '', '%'),
        ],
  );
  const changes = computed(() =>
    rows.value.map((row, i) => {
      const previous = rows.value[i - 1];
      const monthIndex = (date: string) => Number(date.slice(0, 4)) * 12 + Number(date.slice(5, 7));
      const adjacent = previous && monthIndex(row.date) - monthIndex(previous.date) === 1;
      const difference = (key: string) =>
        adjacent && row[key] != null && previous[key] != null
          ? new Decimal(row[key]!).minus(previous[key]!).toString()
          : null;
      return {
        date: row.date,
        stockSharesChange: difference('stockShares'),
        mixedSharesChange: difference('mixedShares'),
      };
    }),
  );
</script>
<style scoped src="./researchSupplement.css"></style>
<style scoped>
  .public-share-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  @media (max-width: 1000px) {
    .public-share-grid {
      grid-template-columns: minmax(0, 1fr);
      gap: 0;
    }
  }

  .public-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px 14px;
    font-size: 12px;
  }

  .public-toolbar .research-source {
    margin: 0;
  }
</style>
