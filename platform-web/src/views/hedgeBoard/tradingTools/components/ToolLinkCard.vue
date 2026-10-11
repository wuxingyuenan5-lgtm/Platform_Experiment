<script setup lang="ts">
  import type { TradingToolLink } from '../data/marketTools';

  defineProps<{
    tool: TradingToolLink;
  }>();
</script>

<template>
  <a class="tool-link-card" :href="tool.url" target="_blank" rel="noreferrer noopener">
    <div class="tool-link-card__head">
      <div class="tool-link-card__content">
        <p class="tool-link-card__domain">{{ tool.domain }}</p>
        <h4>{{ tool.name }}</h4>
      </div>
      <span class="tool-link-card__cta" aria-hidden="true">↗</span>
    </div>
  </a>
</template>

<style scoped lang="less">
  .tool-link-card {
    display: flex;
    position: relative;
    flex-direction: column;
    justify-content: flex-start;
    min-height: 100px;
    padding: 16px;
    transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
    border: 1px solid rgb(193 207 220 / 90%);
    border-radius: 12px;
    background: linear-gradient(180deg, rgb(255 255 255 / 98%), rgb(245 249 252 / 96%));
    box-shadow: none;
    color: #18313c;
    text-decoration: none;
    gap: 0;
  }

  .tool-link-card:hover,
  .tool-link-card:focus-visible {
    border-color: rgb(88 119 142 / 60%);
    box-shadow: 0 18px 34px rgb(15 23 42 / 8%);
  }

  .tool-link-card__head {
    display: flex;
    position: relative;
    align-items: flex-start;
    justify-content: space-between;
    min-height: 46px;
    gap: 12px;
  }

  .tool-link-card__content {
    min-width: 0;
  }

  .tool-link-card__head h4 {
    margin: 4px 0 0;
    color: #18313c;
    font-size: 15px;
    font-weight: 600;
    line-height: 1.35;
    word-break: break-word;
  }

  .tool-link-card__domain {
    margin: 0;
    color: #6d8293;
    font-size: 11px;
    letter-spacing: 0;
    text-transform: uppercase;
    word-break: break-all;
  }

  .tool-link-card__cta {
    flex: 0 0 auto;
    padding: 4px 8px;
    border-radius: 999px;
    background: rgb(227 236 243 / 90%);
    color: #35586e;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
</style>
