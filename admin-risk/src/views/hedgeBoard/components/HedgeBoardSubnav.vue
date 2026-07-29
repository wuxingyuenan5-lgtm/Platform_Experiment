<template>
  <nav class="module-subnav" :class="{ 'module-subnav--gold': unified }" :aria-label="`${moduleLabel} 子页导航`">
    <button
      v-for="(section, index) in sections"
      :key="section.id"
      type="button"
      @click="$emit('jump', section.id)"
    >
      <span class="module-subnav__title-row">
        <span class="module-subnav__index">{{ String(index + 1).padStart(2, '0') }}</span>
        <strong>{{ resolveTitle(section.id, section.title) }}</strong>
      </span>
    </button>
  </nav>
</template>

<script setup lang="ts">
  import type { ChartSection } from '../nativeData/dashboardClean';

  defineProps<{
    sections: readonly ChartSection[];
    moduleLabel: string;
    unified: boolean;
    resolveTitle: (sectionId: string, fallback: string) => string;
  }>();

  defineEmits<{
    (event: 'jump', sectionId: string): void;
  }>();
</script>

<style scoped lang="less">
  .module-subnav {
    position: sticky;
    top: 0;
    z-index: 4;
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding: 8px 4px 10px;
    background: var(--strategy-bg);
  }

  .module-subnav button {
    min-width: 156px;
    padding: 10px 12px;
    border: 1px solid var(--strategy-border);
    border-radius: 12px;
    background: var(--strategy-surface);
    color: var(--strategy-text-2);
    text-align: left;
    cursor: pointer;
    box-shadow: var(--strategy-shadow-soft);
  }

  .module-subnav__title-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .module-subnav__title-row strong {
    color: #111827;
    font-size: 14px;
    font-weight: 800;
    white-space: nowrap;
  }

  .module-subnav__index {
    color: #111827;
    font-size: 14px;
    font-weight: 800;
  }

  .module-subnav--gold {
    padding: 0;
    background: transparent;
  }

  .module-subnav--gold button {
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.74);
  }

  .module-subnav--gold .module-subnav__title-row strong,
  .module-subnav--gold .module-subnav__index {
    color: #111827;
    font-size: 14px;
  }
</style>
