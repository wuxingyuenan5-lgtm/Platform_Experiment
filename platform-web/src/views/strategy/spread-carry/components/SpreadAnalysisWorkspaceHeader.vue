<template>
  <header class="spread-analysis-header" data-testid="spread-analysis-workspace-header">
    <div>
      <h1>{{ title }}</h1>
    </div>
    <div class="filters">
      <select :value="selectedVenue" @change="$emit('update:selectedVenue', valueOf($event))">
        <option v-for="venue in venueOptions" :key="venue">{{ venue }}</option>
      </select>
      <input
        :value="leftLegSymbol"
        aria-label="左腿标的"
        @input="$emit('update:leftLegSymbol', valueOf($event))"
      />
      <input
        :value="rightLegSymbol"
        aria-label="右腿标的"
        @input="$emit('update:rightLegSymbol', valueOf($event))"
      />
      <select
        :value="selectedResolution"
        @change="$emit('update:selectedResolution', valueOf($event))"
      >
        <option v-for="resolution in resolutionOptions" :key="resolution">{{ resolution }}</option>
      </select>
    </div>
  </header>
</template>

<script setup lang="ts">
  withDefaults(
    defineProps<{
      title?: string;
      selectedVenue: string;
      leftLegSymbol: string;
      rightLegSymbol: string;
      selectedResolution: string;
      venueOptions?: string[];
      resolutionOptions?: string[];
    }>(),
    {
      title: '\u8de8\u6240\u4ef7\u5dee\u7814\u7a76',
      venueOptions: () => ['Bybit', 'Binance', 'OKX'],
      resolutionOptions: () => [
        '15\u5206\u949f',
        '30\u5206\u949f',
        '1\u5c0f\u65f6',
        '4\u5c0f\u65f6',
        '\u65e5\u7ebf',
      ],
    },
  );
  defineEmits<{
    (event: 'update:selectedVenue', value: string): void;
    (event: 'update:leftLegSymbol', value: string): void;
    (event: 'update:rightLegSymbol', value: string): void;
    (event: 'update:selectedResolution', value: string): void;
  }>();
  function valueOf(event: Event) {
    return (event.target as HTMLInputElement | HTMLSelectElement).value;
  }
</script>

<style scoped lang="less">
  .spread-analysis-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    gap: 16px;
    padding: 18px;
    border: 1px solid #e1e7ef;
    border-radius: 14px;
    background: #fff;
  }

  header > div:first-child {
    display: grid;
    gap: 4px;
  }

  h1 {
    margin: 0;
    font-size: 24px;
  }

  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  select,
  input {
    height: 36px;
    padding: 0 10px;
    border: 1px solid #dce3eb;
    border-radius: 8px;
    background: #fff;
  }

  input {
    width: 135px;
  }

  @media (max-width: 900px) {
    .spread-analysis-header {
      flex-direction: column;
      align-items: stretch;
    }
  }
</style>
