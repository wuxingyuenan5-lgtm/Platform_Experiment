<template>
  <button
    type="button"
    class="market-terminal__info-card option-iv-info-card"
    :aria-expanded="open"
    :title="
      summary.previousDate
        ? '较' + summary.previousDate + '变动，点击查看国内股票期权 IV'
        : '点击查看国内股票期权 IV'
    "
    @click="open = true"
  >
    <span>国内股票期权 IV</span>
    <strong
      >{{ summary.value }} <span class="iv-change">{{ summary.change }}</span></strong
    >
    <small>{{ summary.name }} · {{ summary.date || (loading ? '读取中…' : '暂无数据') }}</small>
  </button>
  <Modal
    v-if="open"
    v-model:open="open"
    title="国内股票期权 IV"
    :footer="null"
    centered
    width="min(1100px, calc(100vw - 32px))"
    :body-style="{ maxHeight: 'calc(100dvh - 160px)', overflowY: 'auto' }"
  >
    <p v-if="error" role="alert">{{ error }} <button @click="load(true)">重试</button></p>
    <DomesticOptionIvPanel v-if="data" />
    <p v-else-if="loading" role="status">正在读取本地期权历史…</p>
  </Modal>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue';
  import { Modal } from 'ant-design-vue';
  import DomesticOptionIvPanel from './DomesticOptionIvPanel.vue';
  import { useDomesticOptionIv } from './useDomesticFinancing';

  const props = defineProps<{ refreshKey?: number }>();
  const open = ref(false);
  const { data, summary, loading, error, load } = useDomesticOptionIv();
  watch(
    () => props.refreshKey,
    (_, previous) => load(previous !== undefined),
    { immediate: true },
  );
</script>
<style scoped>
  .option-iv-info-card {
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .option-iv-info-card:focus-visible {
    outline: 2px solid var(--strategy-accent);
    outline-offset: 2px;
  }

  .iv-change {
    font-size: 12px;
    font-weight: 400;
  }
</style>
