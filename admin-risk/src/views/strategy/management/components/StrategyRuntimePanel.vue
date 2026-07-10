<template>
  <section class="runtime-grid">
    <article class="runtime-card">
      <header>
        <h3>策略账户信息</h3>
        <span>{{ strategyName }}</span>
      </header>

      <div class="gauge-grid">
        <div v-for="item in gauges" :key="item.label" class="gauge-card">
          <div
            class="gauge-ring"
            :style="{
              background: `conic-gradient(${item.leftColor} 0 ${item.progress}%, ${item.rightColor} ${item.progress}% 100%)`,
            }"
          >
            <div class="gauge-ring__inner">
              <strong>{{ item.value }}</strong>
              <span>{{ item.label }}</span>
            </div>
          </div>
          <div class="gauge-footer">
            <span :style="{ color: item.leftColor }">{{ item.leftLabel }}</span>
            <em>{{ item.subValue }}</em>
            <span :style="{ color: item.rightColor }">{{ item.rightLabel }}</span>
          </div>
        </div>
      </div>

      <div class="breakdown-grid">
        <div v-for="item in breakdown" :key="item.label" class="breakdown-item">
          <label>{{ item.label }}</label>
          <strong :class="item.tone ? `is-${item.tone}` : 'is-neutral'">{{ item.value }}</strong>
          <p>{{ item.note }}</p>
        </div>
      </div>
    </article>
  </section>
</template>

<script setup lang="ts">
  import type { StrategyAccountBreakdown, StrategyGaugeMetric } from '../types';
  defineProps<{
    strategyName: string;
    gauges: StrategyGaugeMetric[];
    breakdown: StrategyAccountBreakdown[];
  }>();
</script>

<style scoped lang="less">
  .runtime-grid { display: block; }
  .runtime-card {
    padding: 22px;
    border-radius: 24px;
    background: linear-gradient(180deg, rgba(255,255,255,.97), rgba(255,251,245,.94));
    box-shadow: 0 18px 40px rgba(28,35,40,.05);
    border: 1px solid rgba(201,164,95,.14);
  }
  .runtime-card header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 18px;
  }
  .runtime-card h3 {
    margin: 0;
    color: #15252a;
    font-size: 18px;
  }
  .runtime-card header span {
    color: #8a94a1;
    font-size: 12px;
  }
  .gauge-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
  .gauge-card {
    padding: 18px;
    border-radius: 18px;
    background: rgba(255,255,255,.78);
    box-shadow: inset 0 0 0 1px rgba(201,164,95,.08);
  }
  .gauge-ring {
    display: grid;
    place-items: center;
    width: 164px;
    height: 164px;
    margin: 0 auto 14px;
    border-radius: 50%;
  }
  .gauge-ring__inner {
    display: grid;
    place-items: center;
    width: 118px;
    height: 118px;
    border-radius: 50%;
    background: #fff;
    text-align: center;
  }
  .gauge-ring__inner strong {
    color: #21313d;
    font-size: 22px;
    line-height: 1.1;
  }
  .gauge-ring__inner span {
    color: #8a94a1;
    font-size: 12px;
  }
  .gauge-footer {
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    gap: 12px;
    font-size: 13px;
    font-weight: 700;
  }
  .gauge-footer em {
    color: #6b7280;
    font-style: normal;
    text-align: center;
    font-weight: 500;
  }
  .breakdown-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin-top: 18px;
  }
  .breakdown-item {
    padding: 16px 18px;
    border-radius: 16px;
    background: rgba(255,255,255,.78);
    box-shadow: inset 0 0 0 1px rgba(201,164,95,.08);
  }
  .breakdown-item label,
  .breakdown-item p {
    display: block;
  }
  .breakdown-item label {
    color: #8a94a1;
    font-size: 12px;
  }
  .breakdown-item strong {
    display: block;
    margin: 10px 0 6px;
    font-size: 22px;
  }
  .breakdown-item p {
    margin: 0;
    color: #7c8693;
    font-size: 12px;
  }
  .is-positive { color: #1d9f6e; }
  .is-negative { color: #d8585f; }
  .is-neutral { color: #1f2e3d; }
  @media (max-width: 1200px) {
    .gauge-grid,
    .breakdown-grid { grid-template-columns: 1fr; }
  }
</style>
