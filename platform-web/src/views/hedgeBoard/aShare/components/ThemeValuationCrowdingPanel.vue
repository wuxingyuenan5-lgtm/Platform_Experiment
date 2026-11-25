<template>
  <section class="object-workspace combined-research" aria-label="主题研究">
    <nav class="object-tabs workspace-tabs" aria-label="主题研究工作区">
      <button
        v-for="item in tabs"
        :key="item.key"
        type="button"
        :aria-pressed="tab === item.key"
        @click="navigate(item.key)"
        >{{ item.label }}</button
      >
    </nav>
    <template v-if="tab === 'themes' || (tab === 'industries' && !data)">
      <div v-if="tab === 'themes'" class="object-heading shared-observation">
        <div class="object-controls">
          <span class="object-source"
            >收盘 {{ data?.structure?.date || data?.date || '—' }} · 主题
            {{ data?.themes?.date || '—' }}</span
          >
        </div>
      </div>
      <p v-if="error" class="object-note" role="alert"
        >{{ error }} <button class="object-button" @click="load(true)">重试</button></p
      >
      <p v-if="!data" class="object-source" role="status">{{
        loading ? '正在读取行业与主题…' : '暂无已发布的行业与主题数据'
      }}</p>
      <p
        v-else-if="
          data.status === 'stale' ||
          data.sectionStatus?.themes === 'stale' ||
          data.sectionStatus?.market === 'stale'
        "
        class="object-note"
        >部分来源待更新，当前保留已有观测；各指标日期见对应内容。</p
      >
      <p v-else-if="data.status === 'partial'" class="object-source">行业与主题数据部分待补齐。</p>
    </template>
    <KeepAlive>
      <IndustryResearchWorkspace
        v-if="tab === 'industries' && data"
        :data="data"
        :industry="selectedIndustry"
        :refresh-key="refreshKey"
        :observation-error="error"
        @retry="load(true)"
        @industry="selectIndustry"
        @theme="openTheme"
      />
    </KeepAlive>
    <KeepAlive>
      <ThemeResearchWorkspace
        v-if="tab === 'themes' && data"
        :data="data"
        :theme="selectedTheme"
        :member-industry="memberIndustry"
        :refresh-key="refreshKey"
        @theme="selectTheme"
        @industry="openIndustry"
        @clear-member-industry="clearMemberIndustry"
      />
    </KeepAlive>
    <KeepAlive>
      <IndexResearchWorkspace
        v-if="tab === 'indices'"
        v-model="indexTab"
        :data="data"
        :refresh-key="refreshKey"
      />
    </KeepAlive>
  </section>
</template>
<script setup lang="ts">
  import {
    computed,
    defineAsyncComponent,
    nextTick,
    onActivated,
    provide,
    onBeforeUnmount,
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useDashboardRefresh } from '../../useDashboardRefresh';
  import { useRoute, useRouter } from 'vue-router';
  import { getEquityObservatory, type EquityObservatory } from '@/api/equityObservatory';
  import { useResearchSnapshots, useResearchViewState } from '../../composables/researchWorkspace';
  import { industryCode } from './industryResearch';
  import { RESEARCH_HISTORY_RANGE_KEY } from '../../components/indexValuationStats';

  const IndustryResearchWorkspace = defineAsyncComponent(
    () => import('./IndustryResearchWorkspace.vue'),
  );
  const ThemeResearchWorkspace = defineAsyncComponent(() => import('./ThemeResearchWorkspace.vue'));
  const IndexResearchWorkspace = defineAsyncComponent(() => import('./IndexResearchWorkspace.vue'));
  provide('themeResearchAlwaysExpanded', true);
  provide(RESEARCH_HISTORY_RANGE_KEY, true);
  const props = defineProps<{ refreshKey: number }>();
  const emit = defineEmits<{ ready: [] }>();
  const route = useRoute(),
    router = useRouter();
  const snapshots = useResearchSnapshots();
  const tabs = [
    { key: 'indices', label: '指数与风格' },
    { key: 'industries', label: '行业研究' },
    { key: 'themes', label: '主题研究' },
  ];
  const legacyMarket = computed(
    () =>
      route.query.section === 'market' ||
      (route.query.section === 'crowding' && !route.query.theme),
  );
  const indexTab = ref('valuation');
  watch(
    legacyMarket,
    (market) => {
      indexTab.value = market ? 'breadth' : 'valuation';
    },
    { immediate: true },
  );
  const tab = computed(() => {
    const section = String(route.query.section || '');
    if (section === 'valuation' || legacyMarket.value) return 'indices';
    if (section === 'crowding') return 'themes';
    return tabs.some((item) => item.key === section) ? section : 'industries';
  });
  onActivated(() => {
    if (tab.value === 'indices' && !legacyMarket.value) indexTab.value = 'valuation';
  });
  const savedIndustry = useResearchViewState('research-industry', '801080');
  const savedTheme = useResearchViewState('theme-selected', '');
  const selectedIndustry = computed(
    () =>
      industryCode(typeof route.query.industry === 'string' ? route.query.industry : '') ||
      savedIndustry.value,
  );
  const selectedTheme = computed(() => {
    const name = typeof route.query.theme === 'string' ? route.query.theme : savedTheme.value;
    return (
      data.value?.themes?.items.find((item) => item.name === name)?.name ||
      data.value?.themes?.items[0]?.name ||
      ''
    );
  });
  const data = shallowRef<EquityObservatory | null>(null);
  const memberIndustry = computed(() => {
    const code = industryCode(
      typeof route.query.themeIndustry === 'string' ? route.query.themeIndustry : '',
    );
    if (!code) return undefined;
    const name = data.value?.structure?.industries.find(
      (row) => industryCode(row.code) === code,
    )?.name;
    return { code, name: name || code };
  });
  const loading = ref(false),
    error = ref('');
  let controller: AbortController | undefined;
  async function load(force = false) {
    controller?.abort();
    const current = (controller = new AbortController());
    error.value = '';
    const cached = !force && snapshots.get<EquityObservatory>('equity:cn:themes:');
    if (cached) {
      data.value = cached;
      loading.value = false;
      emit('ready');
      return;
    }
    loading.value = true;
    try {
      const result = await getEquityObservatory('cn', current.signal, 'themes');
      if (!current.signal.aborted) {
        data.value = result;
        snapshots.set('equity:cn:themes:', result);
      }
    } catch {
      if (!current.signal.aborted) error.value = '行业与主题读取失败，已有内容保留。';
    } finally {
      if (!current.signal.aborted) {
        loading.value = false;
        emit('ready');
      }
    }
  }
  function navigate(section: string) {
    if (section === 'indices') indexTab.value = 'valuation';
    if (section === tab.value) return;
    void router.push({
      query: { ...route.query, view: 'themes', section, themeIndustry: undefined },
    });
  }
  function selectIndustry(code: string) {
    savedIndustry.value = industryCode(code);
    void router.replace({ query: { ...route.query, industry: savedIndustry.value } });
  }
  function openIndustry(code: string) {
    savedIndustry.value = industryCode(code);
    void router.push({
      query: {
        ...route.query,
        view: 'themes',
        section: 'industries',
        industry: savedIndustry.value,
        themeIndustry: undefined,
      },
    });
  }
  function selectTheme(name: string) {
    savedTheme.value = name;
    void router.replace({
      query: {
        ...route.query,
        view: 'themes',
        section: 'themes',
        theme: name,
        themeIndustry: undefined,
        segment: undefined,
        themeDate: data.value?.themes?.date,
      },
    });
  }
  function openTheme(name: string, industry: string) {
    savedTheme.value = name;
    void router.push({
      query: {
        ...route.query,
        view: 'themes',
        section: 'themes',
        themeView: 'overview',
        theme: name,
        themeIndustry: industryCode(industry) || undefined,
        segment: undefined,
        themeDate: data.value?.themes?.date,
      },
    });
  }
  function clearMemberIndustry() {
    void router.replace({ query: { ...route.query, themeIndustry: undefined } });
  }
  watch(
    () => props.refreshKey,
    (_, previous) => void load(previous !== undefined),
    { immediate: true },
  );
  watch(tab, async () => {
    await nextTick();
    if (route.path !== '/hedge-board/a-share' || route.query.view !== 'themes') return;
    document.querySelector<HTMLElement>('.board-workspace__viewport')?.scrollTo({ top: 0 });
  });
  useDashboardRefresh(() => load(true), {
    immediate: false,
    enabled: () => !loading.value,
  });
  onBeforeUnmount(() => {
    controller?.abort();
  });
</script>
<style scoped src="./objectResearch.css"></style>
<style scoped>
  .workspace-tabs {
    position: sticky;
    z-index: 6;
    top: 0;
    padding: 10px;
    box-shadow: 0 3px 12px rgb(26 54 93 / 4%);
  }

  .workspace-tabs button {
    min-width: 100px;
  }

  @media (max-width: 600px) {
    .workspace-tabs {
      padding: 6px;
    }

    .workspace-tabs button {
      flex: 1;
      min-width: 0;
      padding: 7px 4px;
      white-space: nowrap;
    }
  }
</style>
