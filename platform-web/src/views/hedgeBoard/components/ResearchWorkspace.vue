<template>
  <div class="board-workspace" :class="{ 'is-collapsed': collapsed }">
    <ResearchSidebar
      :items="pages"
      :active="active"
      :label="label"
      :collapsed="collapsed"
      @toggle="collapsed = !collapsed"
    />
    <main
      ref="viewport"
      class="board-workspace__viewport"
      tabindex="0"
      :aria-label="currentTitle"
      @scroll.passive="saveScroll"
      @wheel.passive="restoring = false"
      @touchstart.passive="restoring = false"
      @keydown="restoring = false"
    >
      <div ref="content" class="board-workspace__content" :key="`${account}:${active}`"
        ><slot></slot
      ></div>
    </main>
  </div>
</template>
<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
  import { useUserStore } from '@/store/modules/user';
  import ResearchSidebar from './ResearchSidebar.vue';
  import { provideResearchWorkspace } from '../composables/researchWorkspace';

  const props = defineProps<{
    pages: Array<{ key: string; label: string; short?: string; path?: string }>;
    active: string;
    label: string;
  }>();
  const currentTitle = computed(
    () => props.pages.find((p) => p.key === props.active)?.label || props.label,
  );
  const collapsed = ref(false);
  const viewport = ref<HTMLElement>();
  const content = ref<HTMLElement>();
  const workspace = provideResearchWorkspace(() => props.active);
  const user = useUserStore();
  const account = computed(() => String(user.getUserInfo.userId || 'anonymous'));
  const positions = new Map<string, number>();
  let restoring = true;
  let observer: ResizeObserver | undefined;
  let frame = 0;
  function saveScroll() {
    if (!restoring && viewport.value) positions.set(props.active, viewport.value.scrollTop);
  }
  function restore() {
    if (!restoring || !viewport.value) return;
    const target = positions.get(props.active) || 0;
    viewport.value.scrollTop = target;
    // Async panels and lazy charts can increase height after the first render.
    if (Math.abs(viewport.value.scrollTop - target) < 2) restoring = false;
  }
  async function observeContent() {
    observer?.disconnect();
    await nextTick();
    if (!content.value) return;
    observer = new ResizeObserver(() => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(restore);
    });
    observer.observe(content.value);
    restore();
  }
  watch(
    () => props.active,
    () => {
      restoring = true;
      if (viewport.value) viewport.value.scrollTop = 0;
      void observeContent();
    },
    { flush: 'sync' },
  );
  watch(account, () => {
    workspace.states.clear();
    workspace.snapshots.clear();
    positions.clear();
    restoring = true;
    void observeContent();
  });
  onMounted(observeContent);
  onBeforeUnmount(() => {
    observer?.disconnect();
    cancelAnimationFrame(frame);
  });
</script>
<style scoped>
  :global(#app:has(.board-workspace)) {
    min-width: 0;
  }

  .board-workspace {
    display: grid;
    grid-template-columns: 150px minmax(0, 1fr);
    gap: 16px;
    min-width: 0;
  }

  .board-workspace.is-collapsed {
    grid-template-columns: 76px minmax(0, 1fr);
  }

  .board-workspace__viewport {
    min-width: 0;
    height: calc(100dvh - 270px);
    min-height: 420px;
    overflow: auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
  }

  .board-workspace__content {
    min-width: 0;
    padding: 0 4px 24px;
  }

  .board-workspace__content > :deep(:first-child) {
    margin-top: 0;
  }

  @media (max-width: 900px) {
    .board-workspace,
    .board-workspace.is-collapsed {
      grid-template-columns: minmax(0, 1fr);
      gap: 10px;
    }

    .board-workspace__viewport {
      height: calc(100dvh - 320px);
    }
  }
</style>
