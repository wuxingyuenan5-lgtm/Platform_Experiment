<template>
  <aside v-if="draft" class="research-import">
    <p
      >研究参数：{{ draft.direction === 'buy_spread' ? '买价差' : '卖价差' }} · 数量
      {{ draft.quantity }} · 入场 {{ draft.entryThreshold }} · 退出 {{ draft.exitTarget }}</p
    >
    <p>只预填参数。执行仍须重新鉴权、取价、配平数量和风控；研究触价不代表成交。</p>
    <button type="button" :disabled="disabled || incompatible" @click="apply">预填执行表单</button>
    <span v-if="incompatible">当前 Funding 执行仅支持现货多、永续空，该研究方向不能直接交接。</span>
    <span>{{ message }}</span>
  </aside>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useRoute } from 'vue-router';
  import { researchReadDraft } from '@/api/platform/strategyResearch';
  import type { components } from '@/api/platform/generated/strategy';

  type Draft = components['schemas']['DraftRequest'];
  const props = defineProps<{ pairId: 'cross-gold' | 'funding-btc'; disabled?: boolean }>();
  const emit = defineEmits<{ (e: 'apply', draft: Draft): void }>();
  const route = useRoute();
  const draft = ref<Draft>();
  const message = ref('');
  const incompatible = computed(
    () => props.pairId === 'funding-btc' && draft.value?.direction !== 'sell_spread',
  );
  watch(
    () => route.query.researchDraft,
    async (id) => {
      draft.value = undefined;
      if (typeof id !== 'string') return;
      try {
        const result = await researchReadDraft(id);
        if (result.data?.parameters?.pairId === props.pairId)
          draft.value = result.data.parameters as Draft;
      } catch {
        message.value = '研究参数不可用或不属于当前用户。';
      }
    },
    { immediate: true },
  );
  function apply() {
    if (draft.value && !incompatible.value) {
      emit('apply', draft.value);
      message.value = '已预填，请核对当前执行条件。';
    }
  }
</script>
<style scoped>
  .research-import {
    padding: 16px;
    border: 1px solid var(--strategy-border);
    background: var(--strategy-surface);
    color: var(--strategy-text-1);
  }

  button {
    cursor: pointer;
  }
</style>
