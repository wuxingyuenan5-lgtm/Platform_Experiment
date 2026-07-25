<template>
  <template v-if="variant === 'crossVenue'">
    <CrossVenueExecutionReplica
      :selected-venue="selectedVenue"
      :left-leg-symbol="leftLegSymbol"
      :right-leg-symbol="rightLegSymbol"
      :selected-resolution="selectedResolution"
    />
    <CrossSpreadMarketLifecyclePanel
      :left-leg-symbol="leftLegSymbol"
      :right-leg-symbol="rightLegSymbol"
    />
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
  import CrossSpreadMarketLifecyclePanel from './CrossSpreadMarketLifecyclePanel.vue';
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
      rightLegSymbol: 'XAUUSD+',
      selectedResolution: '30分钟',
    },
  );
</script>
