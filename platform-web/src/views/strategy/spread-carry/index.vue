<template>
  <div class="spread-page" data-testid="spread-original-structure">
    <StrategyResearchWorkspace
      v-if="activeSection === 'analysis' && variant !== 'domesticOverseas'"
      pair-id="cross-gold"
    />
    <DomesticOverseasMarketInsight v-else-if="activeSection === 'analysis'" />
    <DomesticOverseasExecutionWorkspace
      v-else-if="variant === 'domesticOverseas'"
      :selected-venue="selectedVenue"
      :left-leg-symbol="leftLegSymbol"
      :right-leg-symbol="rightLegSymbol"
      :selected-resolution="selectedResolution"
    />
    <div v-else class="execution-shell"
      ><CrossVenueExecutionWorkspace
        :left-leg-symbol="leftLegSymbol"
        :right-leg-symbol="rightLegSymbol"
    /></div>
  </div>
</template>
<script setup lang="ts">
  import StrategyResearchWorkspace from '../shared/StrategyResearchWorkspace.vue';
  import CrossVenueExecutionWorkspace from './components/CrossVenueExecutionWorkspace.vue';
  import DomesticOverseasExecutionWorkspace from './components/DomesticOverseasExecutionWorkspace.vue';
  import DomesticOverseasMarketInsight from './components/DomesticOverseasMarketInsight.vue';
  import type { SpreadWorkspaceVariant } from './types';

  withDefaults(
    defineProps<{
      activeSection?: 'analysis' | 'execution';
      selectedVenue?: string;
      leftLegSymbol?: string;
      rightLegSymbol?: string;
      selectedResolution?: string;
      variant?: SpreadWorkspaceVariant;
    }>(),
    {
      activeSection: 'analysis',
      selectedVenue: 'Bybit',
      leftLegSymbol: 'XAUTUSDT',
      rightLegSymbol: 'XAUUSD',
      selectedResolution: '30分钟',
      variant: 'crossVenue',
    },
  );
</script>
<style lang="less">
  @import '../shared/strategy-theme.less';
</style>
<style scoped lang="less">
  .spread-page {
    display: flex;
    flex-direction: column;
    gap: 18px;
    padding: 0 4px 18px;
    background: var(--strategy-bg);
    color: var(--strategy-text-1);
  }
</style>
