<template>
  <template v-if="variant === 'crossVenue'">
    <div class="spread-workspace__legacy-design">
      <CrossVenueExecutionReplica
        :selected-venue="selectedVenue"
        :left-leg-symbol="leftLegSymbol"
        :right-leg-symbol="rightLegSymbol"
        :selected-resolution="selectedResolution"
      />
    </div>
  </template>
  <DomesticOverseasExecutionReplica
    v-else
    :selected-venue="selectedVenue"
    :left-leg-symbol="leftLegSymbol"
    :right-leg-symbol="rightLegSymbol"
    :selected-resolution="selectedResolution"
  />
</template>

<script setup lang="ts">
  import CrossVenueExecutionReplica from './CrossVenueExecutionReplica.vue';
  import DomesticOverseasExecutionReplica from './DomesticOverseasExecutionReplica.vue';
  import type { SpreadWorkspaceVariant } from '../types';

  withDefaults(
    defineProps<{
      variant?: SpreadWorkspaceVariant;
      selectedVenue?: string;
      leftLegSymbol?: string;
      rightLegSymbol?: string;
      selectedResolution?: string;
    }>(),
    {
      variant: 'crossVenue',
      selectedVenue: 'Bybit',
      leftLegSymbol: 'XAUTUSDT.P',
      rightLegSymbol: 'XAUUSD.s',
      selectedResolution: '30分钟',
    },
  );
</script>

<style scoped lang="less">
  .spread-workspace__legacy-design {
    position: relative;
  }
</style>
