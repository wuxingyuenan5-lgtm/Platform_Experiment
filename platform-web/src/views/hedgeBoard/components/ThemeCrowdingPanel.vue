<template>
  <section class="theme-crowding" :class="{ embedded }">
    <header class="panel-heading">
      <div
        ><h2>主题成交与价格</h2
        ><p>代表股票成交额占全A归档成交额比例 · {{ data.date || '暂无收盘数据' }}</p></div
      >
      <RouterLink
        v-if="!embedded"
        :to="{
          path: '/hedge-board/a-share',
          query: { view: 'themes', section: 'themes', theme, themeView: 'overview' },
        }"
        >返回主题画像</RouterLink
      >
    </header>
    <div class="crowding-workspace">
      <nav v-if="!embedded" class="theme-nav" aria-label="成交占比主题">
        <button
          v-for="item in data.items"
          :key="item.name"
          type="button"
          :aria-pressed="active?.name === item.name"
          @click="emit('select', item.name, '')"
        >
          <span>{{ item.name }}</span
          ><b>{{ format(item.history.at(-1)?.sharePct, '%') }}</b>
        </button>
      </nav>
      <div v-if="active && selected" class="chart-pane">
        <div class="segment-tabs" role="group" aria-label="主题内部细分">
          <button
            v-for="item in baskets"
            :key="item.name"
            type="button"
            :aria-pressed="selected.name === item.name"
            @click="emit('select', active.name, item.name === active.name ? '' : item.name)"
          >
            {{ item.name === active.name ? '主题整体' : item.name }}
          </button>
        </div>
        <div class="basket-heading"
          ><h3>{{ selected.name }}</h3
          ><span>{{ selected.expected }}只代表股票</span></div
        >
        <p v-if="route.query.themeDate && route.query.themeDate !== data.date" class="history-note"
          >主题强弱观测日 {{ route.query.themeDate }} · 成交观测日 {{ data.date || '暂无' }}</p
        >
        <div class="metrics">
          <div
            ><span>当日成交额占比</span><strong>{{ format(latest?.sharePct, '%') }}</strong>
            <small
              >{{ latest?.date || '—' }} · {{ latest?.amountCount || 0 }}/{{
                selected.expected
              }}只</small
            ></div
          >
          <div
            ><span>成交额占比 · 5日均值</span><strong>{{ format(latest?.shareMa5, '%') }}</strong>
            <small>{{
              latest?.shareMa5 == null ? '需连续5个交易日完整成交额' : latest.date
            }}</small></div
          >
          <div
            ><span>等权价格 · 基期100</span><strong>{{ format(lastPrice?.price) }}</strong>
            <small>{{ lastPrice?.date || '暂无完整价格' }}</small></div
          >
        </div>
        <component
          :is="alwaysExpanded ? 'section' : 'details'"
          v-if="selected.concentration"
          class="method"
          :key="chartKey"
        >
          <component
            :is="alwaysExpanded ? 'h3' : 'summary'"
            :class="{ 'disclosure-title': alwaysExpanded }"
            >成交额前{{ selected.concentration.leaders.length }}只占本组
            {{ format(selected.concentration.sharePct, '%') }} ·
            {{ selected.concentration.date }}</component
          >
          <p v-for="row in selected.concentration.leaders" :key="row.code">
            <RouterLink
              :to="{ path: '/hedge-board/a-share', query: { view: 'stocks', stock: row.code } }"
            >
              {{ row.name || row.code }}{{ row.name ? ' · ' + row.code : '' }} ↗</RouterLink
            >
            · {{ format(Number(row.amountYuan) / 1e8, '亿元') }}
          </p>
        </component>
        <p v-else class="history-note">组内成交集中度 —</p>
        <WidgetErrorBoundary :key="chartKey" widget-title="主题成交与价格走势">
          <VibeTimeChart
            :key="chartKey"
            :title="`${selected.name} · 成交额占比与价格`"
            y-label="成交额 / 全A归档成交额（%）"
            right-label="等权价格（基期100）"
            :initial-window="250"
            :precision="2"
            :dates="points.map((p) => p.date)"
            :series="chartSeries"
          />
        </WidgetErrorBoundary>
        <p
          v-if="!selected.history.some((p) => p.shareMa5 != null)"
          class="history-note"
          role="status"
        >
          成交额占比已有{{
            selected.history.filter((p) => p.sharePct != null).length
          }}日记录，5日均线待满5个连续交易日后显示。
        </p>
        <div
          class="table-scroll"
          tabindex="0"
          role="region"
          :aria-label="`${active.name}细分成交占比`"
        >
          <table
            ><thead
              ><tr
                ><th>主题 / 细分</th><th>成交额占比</th><th>5日均值</th><th>成交覆盖</th
                ><th>观测日</th></tr
              ></thead
            >
            <tbody
              ><tr
                v-for="item in baskets"
                :key="item.name"
                :class="{ selected: selected.name === item.name }"
              >
                <th
                  ><button
                    type="button"
                    @click="emit('select', active.name, item.name === active.name ? '' : item.name)"
                    >{{ item.name === active.name ? '主题整体' : item.name }}</button
                  ></th
                >
                <td>{{ format(item.history.at(-1)?.sharePct, '%') }}</td
                ><td>{{ format(item.history.at(-1)?.shareMa5, '%') }}</td>
                <td>{{ item.history.at(-1)?.amountCount || 0 }}/{{ item.expected }}</td
                ><td>{{ item.history.at(-1)?.date || '—' }}</td>
              </tr></tbody
            >
          </table>
        </div>
        <component :is="alwaysExpanded ? 'section' : 'details'" class="method"
          ><component
            :is="alwaysExpanded ? 'h3' : 'summary'"
            :class="{ 'disclosure-title': alwaysExpanded }"
            >计算口径</component
          >
          <p
            >成交额占比＝本组去重股票成交额合计 /
            同日平台全A成交额归档。主题和细分均使用此分母，组间有交叉，不能相加。仅完整覆盖时计算占比，5日均值需连续5个交易日有效，缺失不补零。</p
          >
          <p
            >价格为本组各股票复权价格从共同基日归一为100后的等权平均，基日
            {{
              selected.priceBaseDate || '暂无'
            }}，缺任一成员则断线；不是官方行业指数，也不含分红再投资。使用
            {{ data.effectiveFrom }} 目录的当前成员回看历史，不代表历史成分。</p
          >
          <p
            >个股成交额来自东方财富未复权日线及已留存收盘快照；分母为平台全A成交额归档。补采范围以已有价格历史为界，原始成交额不作复权；价格来源为平台已保存的腾讯复权日线。</p
          >
        </component>
      </div>
      <p v-else role="status">{{ segment || theme }}暂无对应成交数据</p>
    </div>
  </section>
</template>
<script setup lang="ts">
  import { inject, computed } from 'vue';
  import { useRoute } from 'vue-router';
  import type { ThemeCrowding, EquityValue } from '@/api/equityObservatory';
  import VibeTimeChart from '../aShare/components/VibeTimeChart.vue';
  import WidgetErrorBoundary from './WidgetErrorBoundary';

  const emit = defineEmits<{ select: [name: string, segment: string] }>();
  const alwaysExpanded = inject('themeResearchAlwaysExpanded', false);
  const props = defineProps<{
    data: ThemeCrowding;
    theme: string;
    segment: string;
    embedded?: boolean;
  }>();
  const route = useRoute();
  const active = computed(() => props.data.items.find((t) => t.name === props.theme));
  const baskets = computed(() => (active.value ? [active.value, ...active.value.segments] : []));
  const selected = computed(() =>
    props.segment ? baskets.value.find((t) => t.name === props.segment) : active.value,
  );
  const latest = computed(() => selected.value?.history.at(-1));
  const lastPrice = computed(() =>
    [...(selected.value?.history || [])].reverse().find((p) => p.price != null),
  );
  const numeric = (v: EquityValue | undefined) =>
    v == null || v === '' || !Number.isFinite(Number(v)) ? null : Number(v);
  const format = (v: EquityValue | undefined, suffix = '') =>
    numeric(v) == null ? '—' : `${numeric(v)!.toFixed(2)}${suffix}`;
  const points = computed(() => selected.value?.history || []);
  const chartKey = computed(() => `${active.value?.name}:${selected.value?.name}`);
  const chartSeries = computed(() => [
    {
      name: '当日成交额占比',
      type: 'line' as const,
      color: '#a7b6c8',
      unit: '%',
      values: points.value.map((p) => numeric(p.sharePct)),
    },
    {
      name: '成交额占比 · 5日均值',
      type: 'line' as const,
      color: '#3269ad',
      unit: '%',
      lineWidth: 2.5,
      values: points.value.map((p) => numeric(p.shareMa5)),
    },
    {
      name: '等权价格',
      type: 'line' as const,
      axis: 'right' as const,
      color: '#15191f',
      values: points.value.map((p) => numeric(p.price)),
    },
  ]);
</script>
<style scoped>
  .embedded .crowding-workspace {
    grid-template-columns: minmax(0, 1fr);
  }

  .theme-crowding {
    min-width: 0;
    padding: 22px;
    border: 1px solid #dce4ed;
    border-radius: 14px;
    background: #fff;
    color: #25374d;
  }

  h2,
  h3,
  p {
    margin: 0;
  }

  h2 {
    font-size: 21px;
    font-weight: 600;
  }

  .panel-heading,
  .basket-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .panel-heading {
    margin-bottom: 22px;
  }

  .panel-heading p,
  .catalog-label,
  .basket-heading span {
    color: #728096;
    font-size: 12px;
  }

  .panel-heading p {
    margin-top: 7px;
  }

  .catalog-label {
    padding: 5px 9px;
    border-radius: 5px;
    background: #f1f5fa;
  }

  .crowding-workspace {
    display: grid;
    grid-template-columns: 220px minmax(0, 1fr);
    gap: 22px;
    align-items: start;
  }

  .theme-nav {
    overflow: hidden;
    border: 1px solid #e0e7ef;
    border-radius: 9px;
  }

  button {
    border: 1px solid #dce4ed;
    border-radius: 6px;
    background: #fff;
    color: inherit;
    font: inherit;
    font-size: 12px;
    cursor: pointer;
  }

  button:focus-visible,
  .table-scroll:focus-visible,
  summary:focus-visible {
    outline: 2px solid #3269ad;
    outline-offset: 2px;
  }

  button:hover {
    background: #f4f8fd;
  }

  .theme-nav button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 14px 12px;
    border: 0;
    border-bottom: 1px solid #edf1f6;
    border-radius: 0;
    text-align: left;
    gap: 8px;
  }

  .theme-nav b {
    color: #627b99;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
  }

  button[aria-pressed='true'] {
    background: #edf4ff;
    color: #255baf;
  }

  .theme-nav button[aria-pressed='true'] {
    box-shadow: inset 3px 0 #3269ad;
  }

  .chart-pane {
    min-width: 0;
  }

  .segment-tabs {
    display: flex;
    flex-wrap: wrap;
    margin-bottom: 22px;
    gap: 6px;
  }

  .segment-tabs button {
    padding: 6px 10px;
  }

  .basket-heading h3 {
    font-size: 19px;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin: 20px 0;
    gap: 12px;
  }

  .metrics > div {
    padding-left: 14px;
    border-left: 2px solid #e8eef6;
  }

  .metrics span,
  .metrics small {
    display: block;
    color: #728096;
    font-size: 11px;
  }

  .metrics strong {
    display: block;
    margin: 8px 0;
    font-size: 25px;
    font-weight: 550;
    font-variant-numeric: tabular-nums;
  }

  .history-note {
    margin: 10px 0 16px;
    color: #8a6934;
    font-size: 12px;
  }

  .table-scroll {
    margin-top: 18px;
    overflow: auto;
    border: 1px solid #e1e8f0;
    border-radius: 8px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 11px 12px;
    border-bottom: 1px solid #edf1f6;
    text-align: right;
    white-space: nowrap;
  }

  th:first-child {
    text-align: left;
  }

  thead th {
    background: #f5f8fc;
    color: #657890;
    font-size: 11px;
    font-weight: 500;
  }

  tbody button {
    padding: 0;
    border: 0;
    background: transparent;
  }

  tr.selected {
    background: #f0f6ff;
  }

  .method {
    margin-top: 16px;
    color: #7a899d;
    font-size: 11px;
    line-height: 1.8;
  }

  .method summary {
    cursor: pointer;
  }

  .method p {
    margin-top: 8px;
  }

  @media (max-width: 1100px) {
    .crowding-workspace {
      grid-template-columns: 185px minmax(0, 1fr);
      gap: 14px;
    }

    .theme-crowding {
      padding: 16px;
    }

    .theme-nav button {
      padding: 12px 10px;
      font-size: 11px;
    }
  }

  @media (max-width: 760px) {
    .crowding-workspace {
      grid-template-columns: minmax(0, 1fr);
    }

    .theme-nav {
      display: flex;
      overflow: auto;
    }

    .theme-nav button {
      flex: 0 0 175px;
      border-right: 1px solid #edf1f6;
    }

    .metrics {
      grid-template-columns: 1fr;
    }

    .metrics > div {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px 12px;
    }

    .metrics strong {
      margin: 0;
      font-size: 21px;
    }

    .metrics small {
      width: 100%;
    }
  }

  .disclosure-title {
    margin: 0 0 12px;
    color: #354d68;
    font-size: 14px;
    font-weight: 600;
  }
</style>
