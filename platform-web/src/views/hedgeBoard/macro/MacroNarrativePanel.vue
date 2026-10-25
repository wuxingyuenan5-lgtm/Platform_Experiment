<template>
  <div class="macro-narratives">
    <header class="narrative-header"
      ><div
        ><small>MACRO NARRATIVES</small><h2>宏观主题与叙事</h2
        ><p>经济状态 · 市场定价 · 叙事轮动</p></div
      ><button :disabled="loading" @click="load">{{
        loading ? '读取中…' : '刷新观察'
      }}</button></header
    >
    <p v-if="error" role="alert">读取失败，请重试。{{ data ? '已保留上次观察。' : '' }}</p>
    <p v-if="!data" role="status">{{ loading ? '正在读取本地宏观历史…' : '暂无宏观叙事数据' }}</p>
    <template v-else>
      <section class="narrative-section">
        <div class="section-head"
          ><div
            ><h3>宏观状态 · 最新证据</h3
            ><p>增长与通胀确定观察象限，政策、流动性、财政和风险溢价提供背景。</p></div
          ><div class="segmented"
            ><button
              v-for="region in regions"
              :key="region.id"
              :aria-pressed="market === region.id"
              @click="market = region.id"
              >{{ region.label }}</button
            ></div
          ></div
        >
        <div class="state-heading"
          ><strong>{{ regime }}</strong
          ><span>3期均值相对前3期变化 · 当前数据版本</span></div
        >
        <div class="evidence-grid"
          ><article v-for="row in state?.evidence" :key="row.dimension"
            ><small>{{ row.dimension }}</small
            ><b
              >{{ row.value === null ? '—' : num(Number(row.value)) }}
              <em>{{ row.value === null ? '' : displayUnit(row.unit) }}</em></b
            ><p>{{ row.label || '暂无对应指标' }}</p
            ><span
              >{{ row.date || '暂无观测' }} ·
              {{
                row.status === 'ready' ? '可用' : row.status === 'no_data' ? '待补充' : '来源待更新'
              }}</span
            ><div v-if="row.delta !== null">3期变化 {{ signed(Number(row.delta)) }}</div
            ><a
              v-if="safeUrl(row.url)"
              :href="safeUrl(row.url)"
              target="_blank"
              rel="noopener noreferrer"
              >{{ row.source || '参考来源' }} ↗</a
            ></article
          ></div
        >
        <p class="method-note"
          >宏观状态只描述最新证据；下方历史日期只回看市场定价，不代表当时可获得的宏观数据。</p
        >
      </section>

      <section class="narrative-section map-section">
        <div class="section-head"
          ><div class="matrix-heading"
            ><span>STRENGTH MAP</span><h3>宏观叙事地图</h3
            ><p>横轴：20期变化强度；纵轴：最近5期强度变化。σ为历史标准差单位。</p></div
          ><label
            >观察日期
            <input
              type="date"
              aria-label="叙事地图日期"
              :min="data.dates[0]"
              :max="data.asOf || undefined"
              :value="end"
              @change="setDate(($event.target as HTMLInputElement).value)" /></label
        ></div>
        <p class="method-note"
          >价格与利率代理，不是新闻情绪或持仓拥挤度；各点显示自身实际观测日期，超过14天不进入地图。</p
        >
        <div class="matrix-legend">
          <span class="matrix-legend--leader">强势升温 {{ quadrants.leader }}</span>
          <span class="matrix-legend--improving">弱势修复 {{ quadrants.improving }}</span>
          <span class="matrix-legend--weakening">强势降温 {{ quadrants.weakening }}</span>
          <span class="matrix-legend--lagging">弱势回落 {{ quadrants.lagging }}</span>
        </div>
        <div v-if="map.points.length" class="narrative-map">
          <svg viewBox="0 0 1100 500" role="img" aria-label="宏观叙事轮动地图">
            <rect
              x="65"
              y="65"
              width="485"
              height="185"
              class="matrix-zone matrix-zone--improving"
            />
            <rect x="550" y="65" width="485" height="185" class="matrix-zone matrix-zone--leader" />
            <rect
              x="65"
              y="250"
              width="485"
              height="185"
              class="matrix-zone matrix-zone--lagging"
            />
            <rect
              x="550"
              y="250"
              width="485"
              height="185"
              class="matrix-zone matrix-zone--weakening"
            />
            <line x1="65" x2="1035" y1="250" y2="250" class="crosshair" />
            <line x1="550" x2="550" y1="65" y2="435" class="crosshair" />
            <text x="80" y="87" class="quadrant">弱势修复</text>
            <text x="1020" y="87" text-anchor="end" class="quadrant">强势升温</text>
            <text x="80" y="420" class="quadrant">弱势回落</text>
            <text x="1020" y="420" text-anchor="end" class="quadrant">强势降温</text>
            <text x="550" y="470" text-anchor="middle" class="axis-label">20期变化强度 →</text>
            <text
              x="25"
              y="250"
              transform="rotate(-90 25 250)"
              text-anchor="middle"
              class="axis-label"
            >
              5期强度变化 →
            </text>
            <text x="65" y="452" class="axis-label">{{ signed(-map.domain.x) }}σ</text>
            <text x="550" y="452" text-anchor="middle" class="axis-label">0</text>
            <text x="1035" y="452" text-anchor="end" class="axis-label">
              {{ signed(map.domain.x) }}σ
            </text>
            <text x="52" y="70" text-anchor="end" class="axis-label">
              {{ signed(map.domain.y) }}
            </text>
            <text x="52" y="437" text-anchor="end" class="axis-label">
              {{ signed(-map.domain.y) }}
            </text>
            <g
              v-for="row in map.points"
              :key="row.driver.id"
              class="narrative-point"
              role="button"
              tabindex="0"
              :aria-label="`查看${row.driver.label}`"
              @click="select(row.driver.id)"
              @keydown.enter="select(row.driver.id)"
              @keydown.space.prevent="select(row.driver.id)"
              :opacity="!selected || selected === row.driver.id ? 1 : 0.4"
            >
              <line
                v-if="Math.abs(row.labelY - row.y) > 20"
                :x1="row.x"
                :y1="row.y"
                :x2="row.labelX"
                :y2="row.labelY - 4"
                stroke="#607080"
                stroke-width=".6"
              />
              <circle
                :cx="row.x"
                :cy="row.y"
                :r="selected === row.driver.id ? 7 : 6"
                :fill="row.color"
                :stroke="selected === row.driver.id ? '#1d4ed8' : '#fff'"
              />
              <text :x="row.labelX" :y="row.labelY" class="point-label">
                {{ row.driver.label }}
              </text>
              <title>
                {{ row.driver.label }} · {{ row.point.date }} · 强度 {{ signed(row.point.score) }}σ
                · 5期变化 {{ signed(row.point.momentum!) }}σ
              </title>
            </g>
          </svg>
        </div>
        <p v-else role="status">该日期暂无满足历史长度要求的主题。</p>
        <div class="date-slider"
          ><span>{{ data.dates[0] }}</span
          ><input
            type="range"
            aria-label="叙事地图时间轴"
            min="0"
            :max="data.dates.length - 1"
            :value="dateIndex"
            @input="dateIndex = Number(($event.target as HTMLInputElement).value)"
          /><span>{{ end }}</span
          ><button @click="dateIndex = data.dates.length - 1">最新</button></div
        >
        <p v-if="excluded.length" class="method-note"
          >未进入当前地图：{{
            excluded.map((d) => `${d.label}（${d.date || '历史不足'}）`).join('、')
          }}</p
        >
        <div class="map-table-wrap"
          ><table
            ><thead
              ><tr
                ><th>主题</th><th>定价强度</th><th>5期变化</th><th>观测日</th><th>代理含义</th></tr
              ></thead
            ><tbody
              ><tr
                v-for="row in sortedRows"
                :key="row.driver.id"
                :class="{ chosen: selected === row.driver.id }"
                ><th
                  ><button @click="select(row.driver.id)"
                    ><i :style="{ background: row.color }"></i>{{ row.driver.label }}</button
                  ></th
                ><td>{{ signed(row.point.score) }}σ</td><td>{{ signed(row.point.momentum!) }}σ</td
                ><td>{{ row.point.date }}</td
                ><td>{{ row.driver.meaning }}</td></tr
              ></tbody
            ></table
          ></div
        >
      </section>

      <section class="narrative-section">
        <div class="section-head"
          ><div><h3>叙事强度轨迹</h3><p>同一主题颜色与地图一致，点击主题可聚焦曲线。</p></div
          ><div class="segmented"
            ><button
              v-for="period in periods"
              :key="period.value"
              :aria-pressed="years === period.value"
              @click="years = period.value"
              >{{ period.label }}</button
            ></div
          ></div
        >
        <div class="curve-legend"
          ><button :aria-pressed="!selected" @click="selected = ''">显示全部</button
          ><button
            v-for="(driver, index) in data.drivers"
            :key="driver.id"
            :aria-pressed="selected === driver.id"
            @click="select(driver.id)"
            ><i :style="{ background: colorFor(index) }"></i>{{ driver.label }}</button
          ></div
        >
        <div class="trajectory"
          ><MacroNarrativeLines
            :drivers="data.drivers"
            :end="end"
            :years="years"
            :selected="selected"
        /></div>
      </section>

      <section v-if="chosen" class="narrative-section" aria-label="叙事构成明细"
        ><div class="section-head"
          ><div
            ><h3>{{ chosen.label }}</h3
            ><p>{{ chosen.meaning }}</p></div
          ><button @click="selected = ''">取消聚焦</button></div
        ><div class="source-list"
          ><article v-for="source in chosen.sources" :key="source.id"
            ><b>{{ source.label }}</b
            ><span
              >{{ source.id }} · {{ source.direction > 0 ? '正向' : '反向' }} ·
              {{ source.transform === 'ratio' ? '价格比值变化' : '数值差变化' }}</span
            ><small
              >{{ source.date || '暂无历史' }} · {{ source.status }} · {{ source.source }}</small
            ><a
              v-if="safeUrl(source.url)"
              :href="safeUrl(source.url)"
              target="_blank"
              rel="noopener noreferrer"
              >参考来源 ↗</a
            ></article
          ></div
        ></section
      >

      <section class="narrative-section"
        ><h3>宏观叙事观察框架</h3
        ><p>状态回答经济发生了什么；叙事回答市场正在定价什么。两者可能背离。</p
        ><div class="lens-grid"
          ><article v-for="lens in lenses" :key="lens.name"
            ><b>{{ lens.name }}</b
            ><p>{{ lens.meaning }}</p
            ><small>{{ lens.evidence }}</small></article
          ></div
        ></section
      >
      <details class="narrative-section"
        ><summary>指标构成与计算口径</summary
        ><p
          >基础信号为连续21个有效观测形成的20期变化：价格使用末值/初值−1，利率和利差使用末值−初值。对照此前最多252个同类变化、至少126个样本计算Z分数；当前变化不进入自身基准。历史方差为零时不计算。多腿主题按注明方向等权平均标准分数，只使用所有腿的共同日期。</p
        ><p
          >纵轴为当前强度减去5个共同有效观测前的强度；两端相隔超过14天则留空。原始连续观测间隔超过14天会重新预热，曲线在超过7天的缺口处断开。20期/5期是各自来源的有效观测，不强行等同同一交易所的交易日。</p
        ><p
          >来源历史较短的主题只展示实际可计算区间；无补值、无模拟历史、无新闻情绪或持仓推断。地图可保留14天以内最近值，明列各主题实际日期。宏观证据采用每月最后有效值，最近3个月均值减前3个月均值，必须连续6个月；日频数据的当月值可能尚未月结。宏观历史为当前修订版本，不构成无前视回测。</p
        ><p
          >数据随既有后台采集更新；页面读取本地存储，不触发外部采集。财政、生产率和真实持仓尚无完整证据时，不据此自动判断财政再通胀、生产率繁荣或拥挤交易。</p
        ></details
      >
    </template>
  </div>
</template>
<script setup lang="ts">
  import { computed, onMounted, onBeforeUnmount, ref } from 'vue';
  import { getMacroNarratives, type MacroNarratives } from '@/api/macroNarratives';
  import { colorFor, narrativeMap } from './narrativeOptions';
  import MacroNarrativeLines from './MacroNarrativeLines.vue';

  const data = ref<MacroNarratives | null>(null),
    loading = ref(false),
    error = ref(false);
  const dateIndex = ref(0),
    selected = ref(''),
    market = ref('us'),
    years = ref(1);
  const regions = [
    { id: 'us', label: '美国' },
    { id: 'cn', label: '中国' },
  ];
  const periods = [
    { value: 0.25, label: '近90日' },
    { value: 1, label: '1年' },
    { value: 3, label: '3年' },
    { value: 5, label: '5年' },
  ];
  const controller = new AbortController();
  async function load() {
    if (loading.value) return;
    loading.value = true;
    error.value = false;
    try {
      data.value = await getMacroNarratives(controller.signal);
      dateIndex.value = Math.max(0, data.value.dates.length - 1);
    } catch {
      if (!controller.signal.aborted) error.value = true;
    } finally {
      loading.value = false;
    }
  }
  onMounted(load);
  onBeforeUnmount(() => controller.abort());
  const end = computed(() => data.value?.dates[dateIndex.value] || data.value?.asOf || '');
  function setDate(value: string) {
    const dates = data.value?.dates || [];
    const index = dates.findIndex((d) => d > value);
    dateIndex.value = index === -1 ? Math.max(0, dates.length - 1) : Math.max(0, index - 1);
  }
  const map = computed(() => narrativeMap(data.value?.drivers || [], end.value));
  const quadrants = computed(() => {
    const counts = { leader: 0, improving: 0, weakening: 0, lagging: 0 };
    for (const { point } of map.value.points) {
      if (point.score >= 0) counts[point.momentum! >= 0 ? 'leader' : 'weakening']++;
      else counts[point.momentum! >= 0 ? 'improving' : 'lagging']++;
    }
    return counts;
  });
  const excluded = computed(() =>
    (data.value?.drivers || []).filter((d) => !map.value.points.some((p) => p.driver.id === d.id)),
  );
  const displayUnit = (unit: string) =>
    (({ percent: '%', index: '指数', usd_million: '百万美元' } as Record<string, string>)[unit] ||
    unit);
  const sortedRows = computed(() =>
    [...map.value.points].sort((a, b) => b.point.score - a.point.score),
  );
  const chosen = computed(() => data.value?.drivers.find((d) => d.id === selected.value));
  const state = computed(() => data.value?.states.find((s) => s.market === market.value));
  const regime = computed(() => {
    const rows = state.value?.evidence || [],
      growth = rows.find((r) => r.dimension === '增长'),
      inflation = rows.find((r) => r.dimension === '通胀');
    if (growth?.delta == null || inflation?.delta == null) return '增长／通胀证据不足';
    const g = Number(growth.delta),
      i = Number(inflation.delta);
    if (Math.abs(g) < 0.1 || Math.abs(i) < 0.05) return '增长／通胀方向交错';
    return g > 0
      ? i < 0
        ? '增长改善 · 通胀回落（Goldilocks观察）'
        : '增长改善 · 通胀上行（Reflation观察）'
      : i < 0
      ? '增长放缓 · 通胀回落（Disinflationary Slowdown观察）'
      : '增长放缓 · 通胀上行（Stagflation观察）';
  });
  const num = (v: number) =>
    Number.isFinite(v) ? v.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '—';
  const signed = (v: number) => `${v > 0 ? '+' : ''}${num(v)}`;
  const safeUrl = (url: string | null | undefined) =>
    url && /^https?:\/\//i.test(url) ? url : undefined;
  function select(id: string) {
    selected.value = selected.value === id ? '' : id;
  }
  const lenses = [
    {
      name: 'Goldilocks · 温和增长',
      meaning: '增长改善，通胀回落',
      evidence: '观察PMI、消费与核心通胀是否一致。',
    },
    {
      name: 'Reflation · 再通胀',
      meaning: '增长与通胀同时改善／上行',
      evidence: '区分需求修复与供给冲击。',
    },
    {
      name: 'Overheating / Higher-for-longer',
      meaning: '需求过强、通胀偏高，政策高利率维持更久',
      evidence: '增长方向之外，还需价格水平与政策证据。',
    },
    {
      name: 'Disinflationary Slowdown',
      meaning: '增长放缓，通胀回落',
      evidence: '观察久期、信用与风险资产的分歧。',
    },
    {
      name: 'Stagflation · 滞胀',
      meaning: '增长放缓，通胀上行',
      evidence: '核对能源、工资与需求证据。',
    },
    {
      name: 'Liquidity Crisis · 流动性压力',
      meaning: '融资和信用条件恶化、去杠杆',
      evidence: '观察融资利差、信用利差与波动率。',
    },
    {
      name: 'Liquidity Reflation',
      meaning: '增长尚弱，流动性率先改善',
      evidence: '货币与金融条件先于实体修复。',
    },
    {
      name: 'Fiscal Reflation',
      meaning: '财政扩张推动需求与通胀',
      evidence: '需要财政脉冲；国债发行量不能单独证明。',
    },
    {
      name: 'Productivity Boom · 生产率繁荣',
      meaning: '供给效率改善，增长与通胀约束缓和',
      evidence: '需要生产率、单位劳动力成本等独立证据。',
    },
  ];
</script>
<style scoped lang="less">
  .macro-narratives {
    display: grid;
    min-width: 0;
    color: #17334d;
    font-size: 13px;
    gap: 18px;

    button,
    input {
      font: inherit;
    }

    button {
      padding: 6px 10px;
      border: 1px solid #d7e2ed;
      border-radius: 7px;
      background: #fff;
      color: inherit;
      cursor: pointer;
    }

    button[aria-pressed='true'] {
      border-color: #93b6ef;
      background: #e9f1ff;
      color: #1d4ed8;
    }

    button:focus-visible,
    input:focus-visible,
    g:focus-visible {
      outline: 2px solid #4c8bff;
      outline-offset: 3px;
    }

    h2,
    h3,
    p {
      margin: 0;
    }

    h2 {
      margin: 3px 0;
      font-size: 23px;
    }

    h3 {
      font-size: 16px;
    }

    p {
      margin-top: 6px;
      color: #708397;
      line-height: 1.7;
    }

    a {
      color: #326cbc;
    }

    i {
      display: inline-block;
      width: 7px;
      height: 7px;
      margin-right: 6px;
      border-radius: 50%;
    }

    small {
      font-size: 11px;
    }
  }

  .narrative-header,
  .section-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
  }

  .narrative-header small {
    color: #947c45;
    font-weight: 600;
    letter-spacing: 0.13em;
  }

  .narrative-section {
    min-width: 0;
    padding: 20px;
    border: 1px solid #dbe5ee;
    border-radius: 13px;
    background: #fff;
  }

  .segmented {
    display: flex;
    gap: 5px;
  }

  .state-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    margin: 20px 0 14px;
    gap: 15px;

    strong {
      font-size: 18px;
    }

    span {
      color: #8393a5;
      font-size: 11px;
    }
  }

  .evidence-grid {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 9px;

    article {
      min-width: 0;
      padding: 12px;
      border: 1px solid #e1e8f1;
      border-radius: 9px;
      background: #f8fafd;
    }

    b {
      display: block;
      margin: 8px 0;
      font-size: 19px;
    }

    em {
      font-size: 10px;
      font-style: normal;
    }

    span,
    small,
    div,
    a {
      display: block;
      font-size: 10px;
      line-height: 1.7;
    }

    p {
      min-height: 34px;
      font-size: 11px;
    }

    .evidence-grid a {
      overflow-wrap: anywhere;
    }
  }

  .method-note {
    color: #8694a4 !important;
    font-size: 11px;
  }

  .narrative-map,
  .trajectory {
    margin-top: 15px;
    overflow: hidden;
    border: 1px solid #d9e3ee;
    border-radius: 10px;
    background: #fbfcfe;
  }

  .narrative-map svg {
    display: block;
    width: 100%;
    min-height: 350px;
  }

  .map-section {
    background: #f7f9fc;
  }

  .narrative-map {
    border: 1px solid #c4cfdd;
    border-radius: 11px;
    background: #fbfcfe;
    box-shadow: inset 0 1px 0 rgb(255 255 255 / 80%);
  }

  .matrix-heading > span {
    display: block;
    margin-bottom: 3px;
    color: #1d4ed8;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.12em;
  }

  .matrix-legend {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 5px;
    margin-top: 10px;
  }

  .matrix-legend span {
    padding: 4px 7px;
    border-radius: 99px;
    font-size: 10px;
    font-variant-numeric: tabular-nums;
  }

  .matrix-legend--leader {
    background: #fee2e2;
    color: #b91c1c;
  }

  .matrix-legend--improving {
    background: #fff7ed;
    color: #c2410c;
  }

  .matrix-legend--weakening {
    background: #ecfdf5;
    color: #047857;
  }

  .matrix-legend--lagging {
    background: #eff6ff;
    color: #1d4ed8;
  }

  .matrix-zone {
    stroke-width: 1;
    stroke: #e2e8f0;
  }

  .matrix-zone--leader {
    fill: #fff1f2;
  }

  .matrix-zone--improving {
    fill: #fffaf0;
  }

  .matrix-zone--weakening {
    fill: #f0fdf4;
  }

  .matrix-zone--lagging {
    fill: #f0f7ff;
  }

  .crosshair {
    stroke-width: 1;
    stroke-dasharray: 3 5;
    stroke: #94a3b8;
  }

  .quadrant {
    fill: #64748b;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.08em;
  }

  .axis-label {
    fill: #60758f;
    font-size: 10px;
  }

  .point-label {
    stroke-width: 3px;
    stroke: #fff;
    fill: #10233d;
    font-size: 10px;
    font-weight: 500;
    paint-order: stroke;
  }

  .narrative-point {
    cursor: pointer;
  }

  .narrative-point circle {
    stroke-width: 1.5;
    opacity: 0.9;
    filter: drop-shadow(0 1px 1px rgb(15 23 42 / 18%));
  }

  .narrative-point:hover circle,
  .narrative-point:focus-visible circle {
    stroke-width: 3;
    stroke: #1d4ed8;
    opacity: 1;
  }

  .date-slider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 16px;
    font-size: 11px;

    input {
      flex: 1;
      min-width: 70px;
      accent-color: #7289a3;
    }
  }

  .map-table-wrap {
    max-height: 320px;
    margin-top: 14px;
    overflow: auto;

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }

    th,
    td {
      padding: 9px;
      border-bottom: 1px solid #e8edf3;
      text-align: left;
      white-space: nowrap;
    }

    thead {
      position: sticky;
      top: 0;
      background: #f5f8fc;
    }

    tbody th {
      font-weight: 500;
    }

    button {
      padding: 0;
      border: 0;
      background: transparent;
    }

    .chosen {
      background: #f0f5ff;
    }
  }

  .curve-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 15px;

    button {
      padding: 4px 7px;
      font-size: 11px;
    }
  }

  .source-list {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-top: 14px;

    article {
      display: grid;
      padding: 13px;
      border-radius: 8px;
      background: #f7f9fc;
      gap: 7px;
    }

    span,
    small {
      color: #728397;
    }
  }

  .lens-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
    margin-top: 16px;

    article {
      padding: 14px;
      border: 1px solid #e4eaf1;
      border-radius: 8px;
    }

    small {
      display: block;
      margin-top: 8px;
      color: #8796a7;
      line-height: 1.6;
    }
  }

  summary {
    font-weight: 600;
    cursor: pointer;
  }

  @media (max-width: 1100px) {
    .evidence-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .lens-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 650px) {
    .narrative-section {
      padding: 12px;
    }

    .evidence-grid,
    .lens-grid,
    .source-list {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .narrative-map {
      overflow: auto;

      svg {
        min-width: 750px;
      }
    }

    .date-slider span:first-child {
      display: none;
    }
  }
</style>
