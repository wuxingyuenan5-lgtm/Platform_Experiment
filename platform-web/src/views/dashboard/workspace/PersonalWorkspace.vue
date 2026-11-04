<template>
  <section class="workspace" aria-label="个人工作台">
    <header
      ><div><h2>我的工作台</h2><p>组合需要关注的图表、数据表与指标</p></div
      ><div
        ><button @click="chooseWidget()">添加小组件</button
        ><button v-if="canResearch" @click="openChart()">自由图表</button
        ><button @click="save" :disabled="saving || loading">{{
          saving ? '保存中…' : '保存布局'
        }}</button></div
      ></header
    >
    <p v-if="error" role="alert">{{ error }} <button @click="load">重新载入</button></p
    ><p v-if="notice" role="status">{{ notice }}</p>
    <form v-if="adding === 'module'" class="editor" @submit.prevent="addModule"
      ><h3>选择小组件</h3
      ><input
        v-model="search"
        aria-label="搜索小组件"
        placeholder="搜索指标或图表名称，如净流动性、沪深300"
      /><select v-model="selectedPath" required aria-label="选择小组件"
        ><option disabled value="">请选择</option
        ><option v-for="m in filteredModules" :key="m.path" :value="m.path">{{
          m.title
        }}</option></select
      ><label v-if="selectedPath.startsWith('series:')"
        >展示形式<select v-model="componentDisplay" aria-label="小组件展示形式"
          ><option value="chart">图表</option
          ><option value="table">数据表</option></select
        ></label
      ><button>{{ replacingId ? '替换卡片' : '添加卡片' }}</button
      ><button type="button" @click="adding = null">取消</button></form
    >
    <form v-if="draft" class="editor" @submit.prevent="commitChart"
      ><h3>{{ editingId ? '编辑图表' : '自由图表' }}</h3
      ><label>标题<input v-model.trim="draft.title" required maxlength="100" /></label
      ><input v-model="seriesSearch" aria-label="搜索数据库指标" placeholder="搜索数据库指标" />
      <label
        >数据A<select v-model="draft.seriesA" required
          ><option disabled value="">选择指标</option
          ><option v-for="s in filteredSeries" :key="s.id" :value="s.id"
            >{{ s.group }} · {{ s.name }} ({{ s.unit }})</option
          ></select
        ></label
      >
      <label
        >数据B<select v-model="draft.seriesB"
          ><option value="">不叠加</option
          ><option v-for="s in filteredSeries" :key="s.id" :value="s.id"
            >{{ s.group }} · {{ s.name }} ({{ s.unit }})</option
          ></select
        ></label
      >
      <label
        >形式<select v-model="draft.display"
          ><option value="chart">图表</option
          ><option value="table">数据表</option></select
        ></label
      >
      <label
        >展示<select v-model="draft.transform"
          ><option value="level">原值 · 双轴</option
          ><option value="index">各自起点归一为100</option
          ><option value="return">各自观察期变化率（%）</option></select
        ></label
      >
      <label>开始<input v-model="draft.start" type="date" /></label
      ><label>结束<input v-model="draft.end" type="date" /></label>
      <p>不同频率按原始日期展示，缺值断线；变化率为各自相邻观察期，并非统一日收益。</p
      ><div
        ><button type="button" @click="preview = true" :disabled="!draft.seriesA">预览</button
        ><button>保留图表</button
        ><button
          type="button"
          @click="
            draft = null;
            preview = false;
          "
          >取消</button
        ></div
      >
      <SeriesComparison
        v-if="preview && draft.seriesA"
        :key="JSON.stringify(draft)"
        :card="draft"
      />
    </form>
    <p v-if="loading">正在加载个人布局…</p
    ><p v-else-if="!visibleCards.length && !draft" class="empty"
      >添加图表、数据表或指标卡，组合自己的工作台。</p
    >
    <div class="cards"
      ><article
        v-for="(card, i) in visibleCards"
        :key="card.id"
        :class="['card', { full: card.width === 2 }]"
      >
        <header
          ><h3>{{ card.title }}</h3
          ><div class="actions"
            ><button @click="move(card.id, -1)" :disabled="i === 0" aria-label="上移卡片">↑</button
            ><button
              @click="move(card.id, 1)"
              :disabled="i === visibleCards.length - 1"
              aria-label="下移卡片"
              >↓</button
            ><button @click="card.width = card.width === 1 ? 2 : 1">{{
              card.width === 1 ? '全宽' : '半宽'
            }}</button
            ><button v-if="card.type === 'chart'" @click="openChart(card)">编辑</button
            ><button @click="remove(card.id)">移除</button></div
          ></header
        >
        <template v-if="card.type === 'module'">
          <template v-if="isWidget(card)">
            <div class="module-tools"
              ><button @click="toggle(card.id)">{{
                opened.has(card.id) ? '收起组件' : '展开组件'
              }}</button
              ><button @click="chooseWidget(card.id)">更换组件</button
              ><a :href="`#${card.path.split('&workbenchWidget=')[0]}`">查看原图 ↗</a></div
            >
            <WidgetViewport v-if="opened.has(card.id)"
              ><EmbeddedModule :path="card.path" :title="card.title"
            /></WidgetViewport>
          </template>
          <div v-else class="empty"
            >这张卡片原来包含完整页面，请重新选择图表或数据表。<button
              @click="chooseWidget(card.id)"
              >选择小组件</button
            ></div
          >
        </template>
        <WidgetViewport v-else><SeriesComparison :card="card" /></WidgetViewport> </article
    ></div>
  </section>
</template>
<script setup lang="ts">
  import { computed, onMounted, onBeforeUnmount, ref, shallowRef, watch } from 'vue';
  import { useUserStore } from '@/store/modules/user';
  import { hasPermission } from '@/access/userAccess';
  import {
    loadWorkspace,
    saveWorkspace,
    loadSeriesCatalog,
    type WorkspaceCard,
    type SeriesInfo,
  } from '@/api/workspace';
  import { moduleCatalog } from './moduleCatalog';
  import { useRouter } from 'vue-router';
  import { canAccessMatchedRoute } from '@/access/routeAccess';
  import WidgetViewport from './WidgetViewport.vue';
  import EmbeddedModule from './EmbeddedModule.vue';
  import SeriesComparison from './SeriesComparison.vue';

  const user = useUserStore(),
    permissions = computed(() => user.getAuthentication?.permissions || []),
    canResearch = computed(() => hasPermission(permissions.value, 'research.read'));
  const router = useRouter();
  const replacingId = ref(''),
    componentDisplay = ref<'chart' | 'table'>('chart');
  const cards = ref<WorkspaceCard[]>([]),
    loading = ref(true),
    saving = ref(false),
    error = ref(''),
    notice = ref(''),
    adding = ref<'module' | null>(null),
    search = ref(''),
    selectedPath = ref(''),
    seriesSearch = ref(''),
    catalog = shallowRef<SeriesInfo[]>([]),
    draft = ref<WorkspaceCard | null>(null),
    editingId = ref(''),
    preview = ref(false),
    opened = ref(new Set<string>());
  let version = 0,
    generation = 0;
  onBeforeUnmount(() => {
    generation++;
  });
  const modules = computed(() => moduleCatalog(permissions.value, catalog.value));
  const filteredModules = computed(() =>
    modules.value.filter((m) => m.title.toLowerCase().includes(search.value.toLowerCase())),
  );
  const filteredSeries = computed(() =>
    catalog.value.filter(
      (s) =>
        (s.name + s.group + s.id).toLowerCase().includes(seriesSearch.value.toLowerCase()) ||
        s.id === draft.value?.seriesA ||
        s.id === draft.value?.seriesB,
    ),
  );
  const visibleCards = computed(() =>
    cards.value.filter((c) =>
      c.type === 'chart' ? canResearch.value : isWidget(c) || canAccessSavedPage(c),
    ),
  );
  function isWidget(card: WorkspaceCard) {
    return modules.value.some((m) => m.path === card.path && (!!m.widget || !!m.broadView));
  }
  function canAccessSavedPage(card: WorkspaceCard) {
    const matched = router.resolve(card.path).matched;
    return matched.length > 0 && canAccessMatchedRoute(matched, permissions.value);
  }
  async function chooseWidget(id = '') {
    replacingId.value = id;
    adding.value = 'module';
    selectedPath.value = '';
    search.value = '';
    draft.value = null;
    if (canResearch.value && !catalog.value.length)
      try {
        catalog.value = await loadSeriesCatalog();
      } catch {
        error.value = '指标目录读取失败，请重试';
      }
  }
  async function load() {
    const active = ++generation;
    loading.value = true;
    saving.value = false;
    notice.value = '';
    error.value = '';
    try {
      const r = await loadWorkspace<WorkspaceCard>('cards');
      if (active !== generation) return;
      cards.value = r.items;
      opened.value = new Set(
        r.items.filter((c) => c.type === 'module' && isWidget(c)).map((c) => c.id),
      );
      version = r.rowVersion;
    } catch (e) {
      if (active === generation) error.value = String(e);
    } finally {
      if (active === generation) loading.value = false;
    }
  }
  async function save() {
    if (loading.value || saving.value) return;
    const active = generation;
    const submitted = JSON.stringify(cards.value);
    saving.value = true;
    error.value = '';
    notice.value = '';
    try {
      const r = await saveWorkspace(
        'cards',
        cards.value.map((c) => ({ ...c, start: c.start || null, end: c.end || null })),
        version,
      );
      if (active !== generation) return;
      version = r.rowVersion;
      if (JSON.stringify(cards.value) === submitted) {
        cards.value = r.items;
        notice.value = '已保存到当前账号';
      } else {
        notice.value = '此前布局已保存，后续修改尚未保存';
      }
    } catch (e) {
      if (active === generation) error.value = String(e);
    } finally {
      if (active === generation) saving.value = false;
    }
  }
  function blank(): WorkspaceCard {
    return {
      id: crypto.randomUUID(),
      type: 'chart',
      title: '自定义图表',
      width: 1,
      path: '',
      seriesA: '',
      seriesB: '',
      transform: 'level',
      display: 'chart',
      start: null,
      end: null,
    };
  }
  function addModule() {
    const m = modules.value.find((m) => m.path === selectedPath.value);
    if (!m) return;
    if (!replacingId.value && cards.value.length >= 24) {
      error.value = '最多保留24张卡片';
      return;
    }
    const card: WorkspaceCard = m.series
      ? { ...blank(), title: m.title, seriesA: m.series.id, display: componentDisplay.value }
      : { ...blank(), type: 'module', title: m.title, path: m.path };
    if (replacingId.value) {
      card.id = replacingId.value;
      card.width = cards.value.find((c) => c.id === card.id)?.width || 1;
      cards.value = cards.value.map((c) => (c.id === card.id ? card : c));
    } else cards.value.push(card);
    if (card.type === 'module') opened.value.add(card.id);
    replacingId.value = '';
    adding.value = null;
    notice.value = '小组件已添加，点击保存布局以保留';
  }
  async function openChart(card?: WorkspaceCard) {
    editingId.value = card?.id || '';
    draft.value = card ? { ...card } : blank();
    preview.value = false;
    adding.value = null;
    error.value = '';
    if (!catalog.value.length)
      try {
        catalog.value = await loadSeriesCatalog();
      } catch (e) {
        error.value = String(e);
      }
  }
  function commitChart() {
    if (!draft.value?.seriesA) return;
    if (draft.value.start && draft.value.end && draft.value.start > draft.value.end) {
      error.value = '开始日期不能晚于结束日期';
      return;
    }
    if (!editingId.value && cards.value.length >= 24) {
      error.value = '最多保留24张卡片';
      return;
    }
    const next = { ...draft.value };
    if (editingId.value)
      cards.value = cards.value.map((c) => (c.id === editingId.value ? next : c));
    else cards.value.push(next);
    draft.value = null;
    preview.value = false;
    notice.value = '图表已保留，点击保存布局以保存到账号';
  }
  function move(id: string, direction: number) {
    const index = cards.value.findIndex((c) => c.id === id),
      target = index + direction;
    if (index < 0 || target < 0 || target >= cards.value.length) return;
    [cards.value[index], cards.value[target]] = [cards.value[target], cards.value[index]];
  }
  function remove(id: string) {
    cards.value = cards.value.filter((c) => c.id !== id);
    opened.value.delete(id);
  }
  function toggle(id: string) {
    const next = new Set(opened.value);
    next.has(id) ? next.delete(id) : next.add(id);
    opened.value = next;
  }
  watch(
    () => user.getUserInfo.userId,
    () => {
      cards.value = [];
      opened.value = new Set();
      catalog.value = [];
      draft.value = null;
      void load();
    },
  );
  onMounted(load);
</script>
<style scoped>
  .workspace {
    margin: 24px clamp(16px, 2vw, 42px);
    color: #20364b;
  }

  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }

  h2 {
    margin: 0;
    font-size: 21px;
  }

  h3 {
    margin: 0;
    font-size: 16px;
  }

  header p {
    margin: 5px 0 14px;
    color: #708397;
    font-size: 13px;
  }

  button,
  input,
  select {
    min-width: 0;
    max-width: 100%;
    padding: 7px 11px;
    border: 1px solid #dbe4ed;
    border-radius: 7px;
    background: #fff;
    color: #36516a;
    font: inherit;
  }

  button {
    margin: 3px;
    cursor: pointer;
  }

  button:disabled {
    opacity: 0.45;
  }

  .cards {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 20px;
    margin-top: 20px;
  }

  .card {
    min-width: 0;
    padding: 18px;
    border: 1px solid #dfe8f1;
    border-radius: 16px;
    background: #fff;
    box-shadow: 0 8px 25px #9caec315;
  }

  .card.full {
    grid-column: 1/-1;
  }

  .card > header {
    padding-bottom: 10px;
    border-bottom: 1px solid #edf1f6;
  }

  .actions {
    font-size: 12px;
  }

  .module-tools {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 10px 0;
    font-size: 12px;
  }

  .module-body {
    min-width: 0;
    height: 620px;
    overflow: auto;
    contain: layout;
  }

  .editor {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    margin: 16px 0;
    padding: 20px;
    border: 1px solid #dbe4ed;
    border-radius: 12px;
    background: #fff;
    gap: 12px;
  }

  .editor h3,
  .editor > p,
  .editor > div {
    grid-column: 1/-1;
  }

  .editor label {
    display: grid;
    gap: 5px;
  }

  .editor > select {
    grid-column: 1/-1;
  }

  .editor p {
    color: #708397;
    font-size: 12px;
  }

  .empty {
    padding: 38px;
    border-radius: 16px;
    background: #fff;
    color: #708397;
    text-align: center;
  }

  a {
    color: #2864ec;
  }

  @media (max-width: 800px) {
    .cards {
      grid-template-columns: 1fr;
    }

    .editor {
      grid-template-columns: 1fr;
    }

    .module-body {
      height: 540px;
    }

    .workspace > header > div:last-child {
      display: flex;
      flex-wrap: wrap;
    }
  }
</style>
