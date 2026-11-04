<template>
  <section
    class="observation-panel"
    :aria-label="
      {
        daily: '全市场宽基与重点ETF资金全景',
        intraday: '盘中ETF监测',
        heatmap: '宽基月度资金表',
        support: '历史大额申购信号对照',
      }[mode]
    "
  >
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
  import { getEtfObservation, type ObservationSnapshot } from '@/api/etfObservation';
  import layout from './etfObservation/layout.html?raw';
  import { mountEtfObservation } from './etfObservation/renderer';
  import './etfObservation/reference.css';

  const props = withDefaults(
    defineProps<{ mode?: 'daily' | 'intraday' | 'heatmap' | 'support' }>(),
    { mode: 'intraday' },
  );
  const host = ref<HTMLElement>();
  function prepareLayout(element: HTMLElement) {
    element.innerHTML = layout;
    element.querySelector('.top')?.remove();
    const keep = ['daily', 'heatmap'].includes(props.mode)
      ? ['etf-observation-part3']
      : props.mode === 'support'
      ? ['etf-observation-part2']
      : ['etf-observation-part1'];
    element.querySelectorAll<HTMLElement>('.part').forEach((part) => {
      if (!keep.includes(part.id)) part.remove();
    });
    function fold(label: string, nodes: Element[]) {
      if (!nodes.length) return;
      const box = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = label;
      box.append(summary);
      nodes[0].before(box);
      nodes.forEach((node) => box.append(node));
    }
    const chart = (id: string) => element.querySelector('#' + id)?.closest('.chart-wrap');
    if (props.mode === 'intraday') {
      element.querySelector('#etf-observation-part1 > .pt')?.remove();
      fold(
        '历史放量案例与常态日对照',
        [chart('chartTypCase'), chart('chartTypNorm')].filter(Boolean) as Element[],
      );
    } else if (props.mode === 'daily') {
      element.querySelector('#etf-observation-part3 > .pt')!.textContent =
        '全市场宽基与重点ETF资金全景 · 日度资金';
      element.querySelector('#broadTable')?.closest('.table-wrap')?.remove();
    } else if (props.mode === 'heatmap') {
      element
        .querySelectorAll('.chart-wrap, .part > .pt, .part > .sub, footer')
        .forEach((node) => node.remove());
    } else {
      element.querySelector('#etf-observation-part2 > .pt')!.textContent = '历史大额申购信号对照';
    }
    element.querySelectorAll('footer').forEach((footer) => fold('统计口径', [footer]));
  }
  const loading = ref(true),
    error = ref('');
  const snapshot = shallowRef<ObservationSnapshot>();
  let dispose: (() => void) | undefined,
    active = true;
  let lastRead = 0;
  let pending: Promise<ObservationSnapshot> | undefined;
  const provenance = computed(() => {
    const data = snapshot.value;
    if (!data) return '';
    const dates = data.reference.dailyData?.dates || [];
    const source = data.sources.live;
    if (props.mode !== 'intraday') return `日度资金截至 ${dates.at(-1) || '暂无数据'}`;
    return `分时截至 ${source?.observationDate || data.reference.initData?.date || '暂无数据'}${
      source?.status !== 'ready' ? ' · 分时来源更新失败，保留原日期数据' : ''
    }`;
  });
  async function read(force = false): Promise<ObservationSnapshot> {
    if (!force && snapshot.value && Date.now() - lastRead < 1000) return snapshot.value;
    if (!pending) {
      pending = getEtfObservation()
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
        prepareLayout(host.value);
        dispose = mountEtfObservation(host.value, structuredClone(data.reference), request, {
          live: props.mode === 'intraday',
        });
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
    dispose?.();
  });
</script>

<style scoped>
  .observation-panel :deep(details) {
    margin: 14px 0;
    padding: 12px;
    border: 1px solid #dbe4ee;
    border-radius: 8px;
  }

  .observation-panel :deep(summary) {
    color: #3d5067;
    font-weight: 600;
    cursor: pointer;
  }

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
