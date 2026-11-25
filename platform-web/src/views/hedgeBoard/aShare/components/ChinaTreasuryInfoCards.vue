<template>
  <article
    v-for="item in cards"
    :key="item.label"
    class="market-terminal__info-card china-treasury-info-card"
    :title="item.title"
  >
    <span>{{ item.label }}</span
    ><strong
      >{{ item.yieldLabel
      }}<span v-if="item.changeLabel" class="yield-change">（{{ item.changeLabel }}）</span></strong
    ><small>{{ item.note }}</small>
  </article>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, shallowRef, ref, watch } from 'vue';
  import { getMacroDashboardV1, type MacroDashboardSeries } from '@/api/hedgeResearch';
  import { chinaTreasuryInfoCards } from './chinaTreasuryInfo';

  const props = defineProps<{ refreshKey?: number }>();
  const series = shallowRef<MacroDashboardSeries[]>([]);
  const failed = ref(false);
  const cards = computed(() => chinaTreasuryInfoCards(series.value, failed.value));
  let active = true;
  onBeforeUnmount(() => {
    active = false;
  });
  watch(
    () => props.refreshKey,
    async () => {
      try {
        const snapshot = await getMacroDashboardV1(['cnTreasury']);
        if (active) {
          series.value = snapshot.groups.cnTreasury || [];
          failed.value = false;
        }
      } catch {
        if (active) failed.value = true;
      }
    },
    { immediate: true },
  );
</script>

<style scoped>
  .china-treasury-info-card strong {
    white-space: nowrap;
  }

  .china-treasury-info-card .yield-change {
    font-size: 12px;
  }
</style>
