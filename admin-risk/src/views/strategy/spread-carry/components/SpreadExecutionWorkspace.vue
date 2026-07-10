<template>
  <CrossVenueExecutionReplica
    v-if="variant === 'crossVenue'"
    :left-leg-symbol="leftLegSymbol"
    :right-leg-symbol="rightLegSymbol"
  />
  <DomesticOverseasExecutionReplica v-else :right-leg-symbol="rightLegSymbol" />
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
    }>(),
    {
      variant: 'crossVenue',
      selectedVenue: 'Bybit',
      leftLegSymbol: 'XAUTUSDT.P',
      rightLegSymbol: 'XAUUSD',
    },
  );
</script>
