<script setup lang="ts">
  import type { TradingToolLink } from '../data/marketTools';

  defineProps<{
    tool: TradingToolLink;
  }>();
</script>

<template>
  <a
    class="tool-link-card"
    :href="tool.url"
    target="_blank"
    rel="noreferrer noopener"
  >
    <div class="tool-link-card__head">
      <div class="tool-link-card__content">
        <p class="tool-link-card__domain">{{ tool.domain }}</p>
        <h4>{{ tool.name }}</h4>
      </div>
      <span class="tool-link-card__cta">Open</span>
    </div>
  </a>
</template>

<style scoped lang="less">
  .tool-link-card {
    position: relative;
    display: flex;
    min-height: 132px;
    flex-direction: column;
    justify-content: flex-start;
    gap: 0;
    border: 1px solid rgba(193, 207, 220, 0.9);
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(245, 249, 252, 0.96));
    padding: 22px;
    color: #18313c;
    text-decoration: none;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.05);
    transition:
      transform 0.22s ease,
      box-shadow 0.22s ease,
      border-color 0.22s ease;
  }

  .tool-link-card:hover {
    transform: translateY(-2px);
    border-color: rgba(88, 119, 142, 0.6);
    box-shadow: 0 18px 34px rgba(15, 23, 42, 0.08);
  }

  .tool-link-card__head {
    position: relative;
    min-height: 46px;
    padding-right: 72px;
  }

  .tool-link-card__content {
    min-width: 0;
  }

  .tool-link-card__head h4 {
    margin: 4px 0 0;
    font-size: 18px;
    font-weight: 600;
    line-height: 1.35;
    color: #18313c;
    word-break: break-word;
  }

  .tool-link-card__domain {
    margin: 0;
    font-size: 11px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6d8293;
    word-break: break-all;
  }

  .tool-link-card__cta {
    position: absolute;
    top: 0;
    right: 0;
    border-radius: 999px;
    background: rgba(227, 236, 243, 0.9);
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #35586e;
  }
</style>
