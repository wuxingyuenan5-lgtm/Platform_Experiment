<template>
  <section class="workbook-screener" aria-label="标的筛选">
    <header class="workbook-header">
      <div class="workbook-switch" role="group" aria-label="标的池">
        <button
          v-for="item in pools"
          :key="item"
          type="button"
          :aria-pressed="pool === item"
          @click="switchPool(item)"
        >
          {{ snapshot.pools[item].sheet }} <small>{{ snapshot.pools[item].rows.length }}</small>
        </button>
      </div>
      <p class="workbook-source" :title="currentPool.file">
        <time :datetime="snapshot.date">{{ snapshot.date }}</time> · {{ currentPool.sheet }} · Excel
        历史快照
      </p>
    </header>

    <div class="workbook-filters">
      <div class="screening-controls">
        <label class="screening-search">
          搜索
          <input v-model.trim="query" type="search" placeholder="代码、名称、分类或代理资产" />
        </label>
        <label>
          一级分类
          <select v-model="group" aria-label="一级分类" @change="category = ''">
            <option value="">全部</option>
            <option v-for="value in groups" :key="value">{{ value }}</option>
          </select>
        </label>
        <label>
          二级分类
          <select v-model="category" aria-label="二级分类">
            <option value="">全部</option>
            <option v-for="value in categories" :key="value">{{ value }}</option>
          </select>
        </label>
        <label>
          异动
          <select v-model="activity" aria-label="异动">
            <option value="">全部</option>
            <option value="any">有异动</option>
            <option value="强异动">强异动</option>
            <option value="-">无异动</option>
          </select>
        </label>
        <button type="button" :disabled="!filterCount && !sort" @click="reset">清除条件</button>
      </div>
      <div v-if="proxy" class="screening-filter-chips">
        <button type="button" :aria-label="'清除代理资产 ' + proxy" @click="proxy = ''">
          代理资产 {{ proxy }} <span aria-hidden="true">×</span>
        </button>
      </div>
      <details class="workbook-advanced">
        <summary
          >指标筛选 <small v-if="advancedCount">{{ advancedCount }} 项</small></summary
        >
        <div class="screening-controls">
          <label v-for="field in filterFields" :key="field.key">
            {{ field.label }}
            <select v-model="metricFilters[field.key]" :aria-label="field.label">
              <option value="">全部</option>
              <option v-for="value in optionsFor(field.key)" :key="value">{{ value }}</option>
            </select>
          </label>
        </div>
      </details>
    </div>

    <div class="workbook-views">
      <div class="workbook-switch" role="group" aria-label="指标视图">
        <button
          v-for="item in views"
          :key="item.key"
          type="button"
          :aria-pressed="view === item.key"
          @click="switchView(item.key)"
          >{{ item.label }}</button
        >
      </div>
      <span role="status">{{ results.length }} / {{ currentPool.rows.length }} 个标的</span>
    </div>
    <p v-if="viewNote" class="workbook-note">{{ viewNote }}</p>
    <div class="screening-table workbook-table" tabindex="0" role="region" aria-label="筛选结果">
      <table>
        <thead>
          <tr>
            <th
              scope="col"
              :aria-sort="
                sort?.key === 'code' ? (sort.ascending ? 'ascending' : 'descending') : undefined
              "
            >
              <button type="button" @click="sortBy('code')">标的 {{ sortMark('code') }}</button>
            </th>
            <th v-if="pool === 'tools'" scope="col">代理资产</th>
            <th v-else-if="view === 'directory'" scope="col">代理工具</th>
            <th
              v-for="column in columns"
              :key="column.key"
              scope="col"
              :aria-sort="
                sort?.key === column.key ? (sort.ascending ? 'ascending' : 'descending') : undefined
              "
            >
              <button v-if="column.format" type="button" @click="sortBy(column.key)">
                {{ column.label }} {{ sortMark(column.key) }}
              </button>
              <template v-else>{{ column.label }}</template>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in pageRows"
            :key="JSON.stringify([row.group, row.category, row.code, row.name])"
          >
            <th scope="row">
              <button class="workbook-asset" type="button" @click="selected = row">
                <strong>{{ row.name }}</strong>
                <small>
                  {{ row.code
                  }}<template v-if="view !== 'directory'">
                    · {{ row.group }} / {{ row.category }}</template
                  >
                </small>
              </button>
            </th>
            <td v-if="pool === 'tools'">
              <button
                v-if="row.proxy"
                class="workbook-proxy"
                type="button"
                :aria-label="'按代理资产筛选 ' + row.proxy"
                @click="proxy = row.proxy"
              >
                {{ row.proxy }}
              </button>
              <template v-else>—</template>
            </td>
            <td v-else-if="view === 'directory'">
              <button
                v-if="proxyCounts.has(row.name)"
                class="workbook-proxy"
                type="button"
                :aria-label="'查看' + row.name + '的代理工具'"
                @click="showTools(row.name)"
              >
                查看 {{ proxyCounts.get(row.name) }} 个工具
              </button>
              <template v-else>—</template>
            </td>
            <td
              v-for="column in columns"
              :key="column.key"
              :class="{ 'workbook-number': column.format }"
            >
              <span :class="stateClass(row[column.key])">{{
                display(row[column.key], column.format)
              }}</span>
              <small v-if="column.sub && row[column.sub] != null"
                >{{ display(row[column.sub], 'count') }} 期</small
              >
            </td>
          </tr>
          <tr v-if="!pageRows.length">
            <td
              :colspan="columns.length + (pool === 'tools' || view === 'directory' ? 2 : 1)"
              class="screening-empty"
            >
              没有匹配的标的
              <button type="button" @click="reset">清除条件</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-if="pageCount > 1" class="screening-pagination" aria-label="筛选结果分页">
      <button type="button" :disabled="page === 1" @click="page--">上一页</button>
      <span>{{ page }} / {{ pageCount }}</span>
      <button type="button" :disabled="page === pageCount" @click="page++">下一页</button>
    </div>

    <Modal
      :open="Boolean(selected)"
      :title="selected?.name"
      :footer="null"
      width="min(720px, calc(100vw - 32px))"
      centered
      wrap-class-name="cross-asset-profile-modal"
      @cancel="selected = undefined"
    >
      <div v-if="selected" class="workbook-detail">
        <p>
          {{ selected.code }} · {{ selected.group }} / {{ selected.category }}
          <template v-if="selected.proxy"> · 代理资产 {{ selected.proxy }}</template>
        </p>
        <p class="workbook-source"
          >{{ snapshot.date }} · {{ currentPool.sheet }} · Excel 历史快照</p
        >
        <button
          v-if="pool === 'core' && proxyCounts.has(selected.name)"
          class="workbook-detail-action"
          type="button"
          @click="showTools(selected.name)"
          >查看代理工具</button
        >
        <button
          v-else-if="selected.proxy && (proxyCounts.get(selected.proxy) ?? 0) > 1"
          class="workbook-detail-action"
          type="button"
          @click="showTools(selected.proxy)"
          >查看同代理资产的工具</button
        >
        <div class="workbook-detail-groups">
          <section v-for="item in details" :key="item.label">
            <h3>{{ item.label }}</h3>
            <dl>
              <template v-for="field in item.fields" :key="field.key">
                <dt>{{ field.label }}</dt>
                <dd>
                  {{ display(selected[field.key], field.format) }}
                  <small v-if="field.sub && selected[field.sub] != null">
                    · {{ display(selected[field.sub], 'count') }} 期</small
                  >
                </dd>
              </template>
            </dl>
          </section>
        </div>
        <p class="workbook-source">资金、动能与状态区间涨跌幅沿用原表数值尺度。</p>
      </div>
    </Modal>
  </section>
</template>

<script setup lang="ts">
  import { computed, reactive, ref, watch } from 'vue';
  import { Modal } from 'ant-design-vue';
  import type { WorkbookAsset, WorkbookSnapshot } from './workbookSnapshot';

  const props = defineProps<{ snapshot: WorkbookSnapshot }>();
  const pools = ['core', 'tools'] as const;
  type Pool = (typeof pools)[number];
  type Field = keyof WorkbookAsset;
  type Format = 'count' | 'position' | 'score' | 'signed';
  type Column = { key: Field; label: string; format?: Format; sub?: Field };
  type View = 'directory' | 'trend' | 'relative' | 'money' | 'momentum';

  const activityColumn: Column = { key: 'activity', label: '异动' };
  const rank: Column = { key: 'activityRank', label: '异动排名', format: 'count' };
  const day: Column = { key: 'day', label: '日线', sub: 'dayAge' };
  const week: Column = { key: 'week', label: '周线', sub: 'weekAge' };
  const month: Column = { key: 'month', label: '月线', sub: 'monthAge' };
  const position: Column = { key: 'position', label: '60 日区间位置', format: 'position' };
  const relative: Column = { key: 'relativeState', label: '选美状态', sub: 'relativeAge' };
  const strength: Column = { key: 'relativeStrength', label: '选美强度', format: 'score' };
  const money: Column = { key: 'flowState', label: '资金状态', sub: 'flowAge' };
  const momentum: Column = { key: 'momentumState', label: '动能状态', sub: 'momentumAge' };
  const views: { key: View; label: string; fields: Column[]; note?: string }[] = [
    {
      key: 'directory',
      label: '标的目录',
      fields: [
        { key: 'group', label: '一级分类' },
        { key: 'category', label: '二级分类' },
      ],
    },
    {
      key: 'trend',
      label: '趋势识别',
      fields: [
        day,
        week,
        month,
        position,
        activityColumn,
        rank,
        { key: 'attentionAge', label: '连续关注期数', format: 'count' },
      ],
    },
    {
      key: 'relative',
      label: '相对比价',
      fields: [
        relative,
        strength,
        { key: 'relativeMomentum', label: '选美动量', format: 'signed' },
        { key: 'relativeTurn', label: '选美转向', format: 'score' },
        position,
      ],
      note: '选美指标沿用工作簿的相对强弱评分。',
    },
    {
      key: 'money',
      label: '资金监控',
      fields: [
        money,
        { key: 'flowValue', label: '主力资金评分', format: 'score' },
        { key: 'flowChange', label: '评分较前日', format: 'signed' },
        { key: 'previousFlowState', label: '此前状态' },
      ],
      note: '主力资金状态为工作簿信号，评分沿用原表 0–100 尺度。',
    },
    {
      key: 'momentum',
      label: '动能',
      fields: [
        momentum,
        { key: 'momentumValue', label: '动能读数', format: 'score' },
        { key: 'momentumChange', label: '较前日变化', format: 'signed' },
        { key: 'previousMomentumState', label: '此前状态' },
      ],
    },
  ];
  const additions: Partial<Record<View, Column[]>> = {
    relative: [
      { key: 'relativeReturn', label: '当前区间涨跌幅', format: 'signed' },
      { key: 'previousRelativeState', label: '此前状态', sub: 'previousRelativeAge' },
      { key: 'previousRelativeReturn', label: '此前区间涨跌幅', format: 'signed' },
    ],
    money: [
      { key: 'flowReturn', label: '当前区间涨跌幅', format: 'signed' },
      { key: 'previousFlowReturn', label: '此前区间涨跌幅', format: 'signed' },
    ],
    momentum: [
      { key: 'momentumReturn', label: '当前区间涨跌幅', format: 'signed' },
      { key: 'previousMomentumReturn', label: '此前区间涨跌幅', format: 'signed' },
    ],
  };
  const details = views.slice(1).map((item) => ({
    label: item.label,
    fields: [...item.fields, ...(additions[item.key] ?? [])],
  }));
  const filterFields = [day, week, month, relative, money, momentum];
  const pool = ref<Pool>('core');
  const view = ref<View>('directory');
  const query = ref('');
  const group = ref('');
  const category = ref('');
  const activity = ref('');
  const proxy = ref('');
  const metricFilters = reactive<Partial<Record<Field, string>>>({});
  const sort = ref<{ key: Field; ascending: boolean }>();
  const selected = ref<WorkbookAsset>();
  const page = ref(1);
  const pageSize = 25;
  const currentPool = computed(() => props.snapshot.pools[pool.value]);
  const proxyCounts = computed(() => {
    const counts = new Map<string, number>();
    for (const { proxy } of props.snapshot.pools.tools.rows) {
      if (proxy) counts.set(proxy, (counts.get(proxy) ?? 0) + 1);
    }
    return counts;
  });
  const groups = computed(() => [...new Set(currentPool.value.rows.map((row) => row.group))]);
  const categories = computed(() => [
    ...new Set(
      currentPool.value.rows
        .filter((row) => !group.value || row.group === group.value)
        .map((row) => row.category),
    ),
  ]);
  const activeView = computed(() => views.find((item) => item.key === view.value)!);
  const columns = computed(() => activeView.value.fields);
  const viewNote = computed(() => activeView.value.note);
  const advancedCount = computed(() => Object.values(metricFilters).filter(Boolean).length);
  const filterCount = computed(
    () =>
      advancedCount.value +
      [query.value, group.value, category.value, activity.value, proxy.value].filter(Boolean)
        .length,
  );
  const stateOptions = computed(
    () =>
      new Map(
        filterFields.map(({ key }) => [
          key,
          [
            ...new Set(
              currentPool.value.rows
                .map((row) => row[key])
                .filter((value): value is string => typeof value === 'string'),
            ),
          ],
        ]),
      ),
  );
  const optionsFor = (key: Field) => stateOptions.value.get(key);
  const results = computed(() => {
    const terms = query.value.toLowerCase().split(/\s+/).filter(Boolean);
    const filters = filterFields.filter(({ key }) => metricFilters[key]);
    const rows = currentPool.value.rows.filter((row) => {
      const haystack = [row.code, row.name, row.group, row.category, row.proxy]
        .join(' ')
        .toLowerCase();
      return (
        (!group.value || row.group === group.value) &&
        (!category.value || row.category === category.value) &&
        (!proxy.value || row.proxy === proxy.value) &&
        (!activity.value ||
          (activity.value === 'any'
            ? row.activity === '异动' || row.activity === '强异动'
            : row.activity === activity.value)) &&
        terms.every((term) => haystack.includes(term)) &&
        filters.every(({ key }) => row[key] === metricFilters[key])
      );
    });
    if (!sort.value) return rows;
    const { key, ascending } = sort.value;
    return rows.sort((a, b) => {
      const left = a[key];
      const right = b[key];
      if (left == null) return right == null ? 0 : 1;
      if (right == null) return -1;
      const order =
        typeof left === 'number' && typeof right === 'number'
          ? left - right
          : String(left).localeCompare(String(right), 'zh-CN', { numeric: true });
      return ascending ? order : -order;
    });
  });
  const pageCount = computed(() => Math.max(1, Math.ceil(results.value.length / pageSize)));
  const pageRows = computed(() =>
    results.value.slice((page.value - 1) * pageSize, page.value * pageSize),
  );
  watch(results, () => {
    page.value = 1;
  });
  watch(
    () => props.snapshot,
    () => {
      selected.value = undefined;
      if (!groups.value.includes(group.value)) group.value = '';
      if (!categories.value.includes(category.value)) category.value = '';
      if (!proxyCounts.value.has(proxy.value)) proxy.value = '';
      for (const { key } of filterFields) {
        const value = metricFilters[key];
        if (value && !optionsFor(key)?.includes(value)) metricFilters[key] = '';
      }
    },
  );

  function reset() {
    query.value = '';
    group.value = '';
    category.value = '';
    activity.value = '';
    proxy.value = '';
    for (const { key } of filterFields) metricFilters[key] = '';
    sort.value = undefined;
  }

  function switchPool(value: Pool) {
    if (pool.value === value) return;
    pool.value = value;
    reset();
  }

  function showTools(value: string) {
    selected.value = undefined;
    pool.value = 'tools';
    view.value = 'directory';
    reset();
    proxy.value = value;
  }

  function switchView(value: View) {
    view.value = value;
    if (
      sort.value &&
      sort.value.key !== 'code' &&
      !columns.value.some((column) => column.key === sort.value?.key)
    ) {
      sort.value = undefined;
    }
  }

  function sortBy(key: Field) {
    const ascending =
      sort.value?.key === key ? !sort.value.ascending : key === 'activityRank' || key === 'code';
    sort.value = { key, ascending };
  }

  function sortMark(key: Field) {
    return sort.value?.key === key ? (sort.value.ascending ? '↑' : '↓') : '';
  }

  function display(value: WorkbookAsset[Field], format?: Format) {
    if (value == null) return '—';
    if (typeof value === 'string') return value === '-' ? '无异动' : value;
    if (format === 'count') return String(value);
    if (format === 'position') return (value * 100).toFixed(1) + '%';
    return value.toLocaleString('zh-CN', {
      maximumFractionDigits: 4,
      signDisplay: format === 'signed' ? 'exceptZero' : 'auto',
    });
  }

  function stateClass(value: WorkbookAsset[Field]) {
    if (value === '上行趋势' || value === '主力流入' || value === '正') return 'workbook-positive';
    if (value === '下行趋势' || value === '主力流出' || value === '负') return 'workbook-negative';
    if (value === '强异动' || value === '异动') return 'workbook-activity';
    return undefined;
  }
</script>

<style scoped>
  .workbook-header,
  .workbook-views {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px 20px;
  }

  .workbook-header {
    padding: 14px 0;
    border-top: 1px solid #e0e7ef;
  }

  .workbook-switch {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
  }

  .workbook-switch button {
    border-color: transparent;
    background: transparent;
  }

  .workbook-switch button[aria-pressed='true'] {
    border-color: #bed1f5;
    background: #eaf1ff;
    color: #245dc7;
    font-weight: 600;
  }

  .workbook-switch small {
    margin-left: 5px;
    font: inherit;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
  }

  .workbook-source,
  .workbook-note,
  .workbook-views > span {
    margin: 0;
    color: #62738a;
    font-size: 12px;
  }

  .workbook-filters {
    padding: 12px 14px 4px;
    border: 1px solid #e0e7ef;
    border-radius: 8px;
    background: #fff;
  }

  .workbook-advanced small {
    margin-left: 4px;
    color: #245dc7;
  }

  .workbook-advanced .screening-controls {
    padding: 0 0 10px;
  }

  .workbook-views {
    margin: 14px 0 8px;
  }

  .workbook-note {
    margin: 0 0 8px;
  }

  .workbook-table thead button,
  .workbook-table .workbook-proxy,
  .workbook-table .workbook-asset {
    padding: 0;
    border: 0;
    background: transparent;
    text-align: left;
  }

  .workbook-table .workbook-proxy {
    color: #245dc7;
  }

  .workbook-table .workbook-asset strong {
    color: #245dc7;
    font-weight: 650;
  }

  .workbook-table td small,
  .workbook-table .workbook-asset small {
    margin-top: 3px;
    color: #63758c;
  }

  .workbook-number {
    font-variant-numeric: tabular-nums;
  }

  .workbook-positive {
    color: #ab394b;
  }

  .workbook-negative {
    color: #147864;
  }

  .workbook-activity {
    color: #8a540c;
    font-weight: 650;
  }

  .workbook-detail p {
    margin-bottom: 8px;
  }

  .workbook-detail-action {
    margin-top: 4px;
    padding: 4px 8px;
    border: 1px solid #bed1f5;
    border-radius: 5px;
    background: #eaf1ff;
    color: #245dc7;
    cursor: pointer;
  }

  .workbook-detail-groups {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
    gap: 12px 20px;
    margin: 16px 0 12px;
  }

  .workbook-detail-groups section {
    padding-top: 12px;
    border-top: 1px solid #e0e7ef;
  }

  .workbook-detail-groups h3 {
    margin: 0 0 8px;
    font-weight: 650;
  }

  .workbook-detail-groups dl {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 5px 12px;
    margin: 0;
  }

  .workbook-detail-groups dt {
    color: #62738a;
  }

  .workbook-detail-groups dd {
    margin: 0;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
</style>
