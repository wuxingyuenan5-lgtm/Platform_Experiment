<template>
  <section aria-label="ETF成交额跟踪">
    <p v-if="loading" role="status">正在读取ETF成交额跟踪…</p>
    <p v-if="error" class="turnover-error" role="status">
      {{ error }} <button type="button" @click="load">重试</button>
    </p>
    <div ref="host" class="etf-turnover"></div>
  </section>
</template>
<script setup lang="ts">
  import { onMounted, onActivated, onDeactivated, onBeforeUnmount, ref, watch } from 'vue';
  import { getEtfTurnover } from '@/api/etfTurnover';
  import { useChartReveal } from '@/hooks/web/chartMotion';
  import layout from './etfTurnover/layout.html?raw';
  import { mountEtfTurnover } from './etfTurnover/renderer';
  import './etfTurnover/reference.css';

  const props = defineProps<{ refreshKey?: number }>();
  const emit = defineEmits<{ ready: [] }>();
  const host = ref<HTMLElement>();
  const loading = ref(true),
    error = ref('');
  const reveal = useChartReveal(host, false);
  let dispose: ReturnType<typeof mountEtfTurnover> | undefined;
  let controller: AbortController | undefined;
  let active = true;
  async function request() {
    controller?.abort();
    controller = new AbortController();
    return getEtfTurnover(controller.signal);
  }
  async function load() {
    if (!active) return;
    loading.value = true;
    error.value = '';
    try {
      const snapshot = await request();
      if (!active || !host.value) return;
      if (!snapshot.data) throw new Error('成交额跟踪快照暂不可用');
      dispose?.();
      host.value.innerHTML = layout;
      dispose = mountEtfTurnover(host.value, snapshot, request, {
        onCharts: () => void reveal(500),
        onError: (message: string) => {
          error.value = message;
        },
      });
    } catch (cause) {
      if (active) error.value = cause instanceof Error ? cause.message : '成交额跟踪读取失败';
    } finally {
      if (active) {
        loading.value = false;
        emit('ready');
      }
    }
  }
  onMounted(load);
  watch(() => props.refreshKey, load);
  onActivated(() => {
    active = true;
    dispose?.resume();
  });
  onDeactivated(() => {
    active = false;
    controller?.abort();
    dispose?.pause();
  });
  onBeforeUnmount(() => {
    active = false;
    controller?.abort();
    dispose?.();
  });
</script>
<style scoped>
  .turnover-error {
    color: var(--strategy-text-3);
    font-size: 12px;
  }

  .turnover-error button {
    margin-left: 8px;
    padding: 4px 10px;
    border: 1px solid var(--strategy-border);
    border-radius: 7px;
    background: #fff;
    color: var(--strategy-accent);
    cursor: pointer;
  }
</style>
