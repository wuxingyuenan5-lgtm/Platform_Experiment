<template>
  <div class="chart-expand" :style="expanded ? { height: `${inlineHeight}px` } : undefined">
    <dialog
      ref="dialog"
      open
      class="chart-expand__surface"
      :role="expanded ? 'dialog' : 'group'"
      :aria-modal="expanded ? true : undefined"
      :aria-label="title"
      @cancel.prevent="close"
      @keydown.esc.stop
    >
      <button
        v-if="enabled"
        ref="toggle"
        type="button"
        class="chart-expand__toggle"
        :aria-label="`${expanded ? '关闭放大' : '放大图表'}：${title}`"
        :title="expanded ? '关闭放大（Esc）' : '放大图表'"
        :aria-expanded="expanded"
        @click.stop="expanded ? close() : expand()"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path v-if="expanded" d="m5 5 10 10M15 5 5 15" />
          <path v-else d="M7 3H3v4m10-4h4v4M3 13v4h4m10-4v4h-4" />
        </svg>
      </button>
      <slot></slot>
    </dialog>
  </div>
</template>

<script setup lang="ts">
  import { nextTick, onBeforeUnmount, onDeactivated, ref } from 'vue';

  withDefaults(defineProps<{ title: string; enabled?: boolean }>(), { enabled: true });
  const emit = defineEmits<{ (event: 'expandedChange', expanded: boolean): void }>();
  const dialog = ref<HTMLDialogElement>();
  const toggle = ref<HTMLButtonElement>();
  const expanded = ref(false);
  const inlineHeight = ref(0);
  let previousOverflow = '';

  async function resize() {
    await nextTick();
    window.dispatchEvent(new Event('resize'));
  }

  function expand() {
    if (!dialog.value || expanded.value) return;
    inlineHeight.value = dialog.value.parentElement!.getBoundingClientRect().height;
    // Promote the existing inline dialog to the browser's top layer. The slot,
    // iframe, chart instance and all current controls remain mounted in place.
    dialog.value.removeAttribute('open');
    dialog.value.showModal();
    expanded.value = true;
    emit('expandedChange', true);
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    toggle.value?.focus();
    void resize();
  }

  function close() {
    if (!expanded.value || !dialog.value) return;
    dialog.value.close();
    dialog.value.setAttribute('open', '');
    expanded.value = false;
    emit('expandedChange', false);
    document.body.style.overflow = previousOverflow;
    toggle.value?.focus({ preventScroll: true });
    void resize();
  }

  onDeactivated(close);
  onBeforeUnmount(close);
</script>

<style scoped lang="less">
  .chart-expand {
    min-width: 0;
  }

  .chart-expand__surface {
    position: relative;
    box-sizing: border-box;
    width: 100%;
    max-width: none;
    max-height: none;
    margin: 0;
    padding: 0;
    overflow: visible;
    border: 0;
    background: transparent;
    color: inherit;
    inset: auto;
  }

  .chart-expand__toggle {
    display: grid;
    position: absolute;
    z-index: 10;
    top: 16px;
    right: 18px;
    width: 30px;
    height: 30px;
    padding: 5px;
    border: 1px solid #dbe4ea;
    border-radius: 7px;
    background: var(--component-background, #fff);
    color: var(--color-text-1, #334155);
    cursor: pointer;
    place-items: center;
  }

  .chart-expand__toggle:hover,
  .chart-expand__toggle:focus-visible {
    border-color: #165dff;
    color: #165dff;
  }

  .chart-expand__toggle svg {
    width: 18px;
    height: 18px;
    stroke-width: 1.6;
    stroke-linecap: round;
    stroke: currentcolor;
    fill: none;
    stroke-linejoin: round;
  }

  .chart-expand__surface:modal {
    position: fixed;
    width: calc(100vw - 32px);
    height: calc(100dvh - 32px);
    max-height: calc(100dvh - 32px);
    padding: 16px;
    overflow: auto;
    border: 1px solid #dbe4ea;
    border-radius: 14px;
    background: var(--component-background, #fff);
    inset: 16px;
  }

  .chart-expand__surface::backdrop {
    background: rgb(15 23 42 / 55%);
  }

  .chart-expand__surface:modal > .chart-expand__toggle {
    position: sticky;
    top: 0;
    margin: 0 0 8px 8px;
    float: right;
  }

  .chart-expand__surface:modal :deep(.source-series-plot) {
    height: max(360px, calc(100dvh - 300px));
    max-height: none;
    aspect-ratio: auto;
  }

  .chart-expand__surface:modal :deep(.source-series-plot--drivers) {
    min-height: 360px;
  }

  .chart-expand__surface:modal :deep(.source-series-plot--binance) {
    min-height: 580px;
  }

  .chart-expand__surface:modal :deep(.fomc-chart) {
    height: calc(100vh - 355px);
    min-height: 300px;
  }

  .chart-expand__surface:modal :deep(.etf-flow-panel__chart) {
    max-height: none;
  }

  .chart-expand__surface:modal :deep([data-widget-height]),
  .chart-expand__surface:modal :deep(.market-terminal-chart-modal__widget) {
    height: calc(100dvh - 160px) !important;
    min-height: 360px;
  }

  .chart-expand__surface:modal :deep(.widget-frame iframe),
  .chart-expand__surface:modal :deep(.market-terminal-chart-modal__widget iframe) {
    width: 100% !important;
    height: calc(100dvh - 160px) !important;
  }

  :deep(.vibe-chart-head),
  :deep(.market-terminal-chart-modal__header) {
    padding-right: 44px;
  }
</style>
