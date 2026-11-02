<template>
  <section class="observation-panel" aria-label="20只重点ETF资金观测">
    <p v-if="loading" role="status">正在读取 ETF 资金观测…</p>
    <p v-if="error" class="observation-notice" role="status"
      >{{ error }}<button @click="load">重试</button></p
    >
    <p v-if="provenance" class="observation-provenance">{{ provenance }}</p>
    <div ref="host" class="etf-observation"></div>
  </section>
</template>

<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue';
  import { researchRequest } from '@/api/hedgeResearch';
  import layout from './etfObservation/layout.html?raw';
  import { mountEtfObservation } from './etfObservation/renderer';
  import './etfObservation/reference.css';

  interface ObservationSnapshot {
    reference: Record<string, any>;
    live: { klines?: Record<string, any[]>; hq?: { data?: { diff?: any[] } } };
    sources: Record<string, { status: string; retrievedAt: string; observationDate?: string }>;
  }
  const host = ref<HTMLElement>();
  const loading = ref(true),
    error = ref('');
  const snapshot = shallowRef<ObservationSnapshot>();
  let dispose: (() => void) | undefined,
    active = true;
  let lastRead = 0;
  let pending: Promise<ObservationSnapshot> | undefined;
  const controller = new AbortController();
  const provenance = computed(() => {
    const data = snapshot.value;
    if (!data) return '';
    const dates = data.reference.dailyData?.dates || [];
    const source = data.sources.live;
    return `日度资金截至 ${dates.at(-1) || '暂无数据'} · 分时截至 ${
      source?.observationDate || data.reference.initData?.date || '暂无数据'
    }${source?.status !== 'ready' ? ' · 分时来源更新失败，保留原日期数据' : ''}`;
  });
  async function read(force = false): Promise<ObservationSnapshot> {
    if (!force && snapshot.value && Date.now() - lastRead < 1000) return snapshot.value;
    if (!pending) {
      pending = researchRequest<ObservationSnapshot>({
        method: 'GET',
        url: '/research/a-share/etf-observation',
        signal: controller.signal,
      })
        .then((data) => {
          if (active) {
            snapshot.value = data;
            lastRead = Date.now();
          }
          return data;
        })
        .finally(() => {
          pending = undefined;
        });
    }
    return pending;
  }
  async function request(path: string) {
    const data = await read();
    const url = new URL(path, 'http://localhost');
    if (url.pathname === '/api/kline') {
      const rows = data.live.klines?.[url.searchParams.get('symbol') || ''];
      if (!rows?.length) throw new Error('分钟数据暂不可用');
      return url.searchParams.get('datalen') === '1' ? rows.slice(-1) : rows;
    }
    if (url.pathname === '/api/hq') {
      const codes = new Set(
        (url.searchParams.get('codes') || '').split(',').map((code) => code.slice(2)),
      );
      const rows = data.live.hq?.data?.diff?.filter((row) => codes.has(row.f12));
      if (!rows?.length) throw new Error('行情快照暂不可用');
      return { data: { diff: rows } };
    }
    throw new Error('未知ETF数据类型');
  }
  async function load() {
    loading.value = true;
    error.value = '';
    try {
      const data = await read(true);
      if (!active) return;
      if (!data.reference.dailyData?.dates?.length)
        throw new Error('ETF历史尚未取得，请稍后重试。');
      await nextTick();
      dispose?.();
      if (host.value) {
        host.value.innerHTML = layout;
        dispose = mountEtfObservation(host.value, structuredClone(data.reference), request);
      }
    } catch (cause) {
      if (active) error.value = cause instanceof Error ? cause.message : 'ETF资金观测暂不可用';
    } finally {
      if (active) loading.value = false;
    }
  }
  onMounted(load);
  onBeforeUnmount(() => {
    active = false;
    controller.abort();
    dispose?.();
  });
</script>

<style scoped>
  .observation-panel {
    min-width: 0;
  }

  .observation-provenance,
  .observation-notice {
    margin: 0 0 10px;
    color: #5a6472;
    font-size: 12px;
  }

  .observation-notice button {
    margin-left: 10px;
    cursor: pointer;
  }
</style>
