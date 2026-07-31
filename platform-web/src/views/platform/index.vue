<template>
  <PageWrapper title="交易平台">
    <div class="platform-page">
      <section class="strategy-top-toolbar">
        <div class="strategy-top-toolbar__left">
          <CompactSegmentTabs :items="deskTabs" :model-value="currentKey" @update:modelValue="selectDesk" />
        </div>

        <div class="strategy-top-toolbar__meta">
          <CompactSegmentTabs class="section-switcher" :items="platformSections" v-model="activeSection" />
        </div>
      </section>

      <FundingCarryWorkspace
        v-if="currentKey === 'funding'"
        :active-section="activeSection"
        :selected-exchange="selectedVenue as any"
        :selected-symbol="selectedFundingSymbol as any"
        :selected-resolution="selectedResolution"
      />

      <SpreadCarryWorkspace
        v-else
        :active-section="activeSection"
        :selected-venue="selectedVenue"
        :left-leg-symbol="selectedMainLeg"
        :right-leg-symbol="selectedHedgeLeg"
        :selected-resolution="selectedResolution"
        :variant="currentDeskConfig.variant"
      />
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useRoute, useRouter } from 'vue-router';
  import { PageWrapper } from '@/components/Page';
  import CompactSegmentTabs from '@/views/strategy/shared/CompactSegmentTabs.vue';
  import FundingCarryWorkspace from '@/views/strategy/funding-carry/index.vue';
  import SpreadCarryWorkspace from '@/views/strategy/spread-carry/index.vue';
  import type { SpreadWorkspaceVariant } from '@/views/strategy/spread-carry/types';

  type DeskKey = 'funding' | 'crossSpread' | 'domesticOverseas';

  interface DeskConfig {
    key: DeskKey;
    label: string;
    variant?: SpreadWorkspaceVariant;
    venueLabel: string;
    venueOptions: string[];
    mainLegOptions: string[];
    hedgeLegOptions: string[];
  }

  const route = useRoute();
  const router = useRouter();

  const fundingVenueOptions = ['Bybit', 'Binance', 'OKX'];
  const platformSections = [
    { key: 'analysis', label: '行情分析' },
    { key: 'execution', label: '交易执行' },
  ];

  const desks: DeskConfig[] = [
    {
      key: 'funding',
      label: '资费',
      venueLabel: '交易所',
      venueOptions: fundingVenueOptions,
      mainLegOptions: [],
      hedgeLegOptions: [],
    },
    {
      key: 'crossSpread',
      label: '跨所价差',
      variant: 'crossVenue',
      venueLabel: '主交易所',
      venueOptions: ['Bybit', 'Binance', 'OKX'],
      mainLegOptions: ['XAUTUSDT.P'],
      hedgeLegOptions: ['XAUUSD+'],
    },
    {
      key: 'domesticOverseas',
      label: '海内外价差',
      variant: 'domesticOverseas',
      venueLabel: '交易场景',
      venueOptions: ['SHFE / XAUUSD', 'AU9999 / XAUUSD'],
      mainLegOptions: ['SHFE.au2606', 'AU9999'],
      hedgeLegOptions: ['XAUUSD'],
    },
  ];

  const deskTabs = desks.map((desk) => ({
    key: desk.key,
    label: desk.label,
  }));

  const selectedVenue = ref('Bybit');
  const selectedFundingSymbol = ref('BTC');
  const selectedMainLeg = ref('XAUTUSDT.P');
  const selectedHedgeLeg = ref('XAUUSD+');
  const selectedResolution = ref('30分钟');
  const activeSection = ref<'analysis' | 'execution'>('analysis');

  const currentKey = computed<DeskKey>(() => {
    if (route.query.desk === 'domesticOverseas') return 'domesticOverseas';
    if (route.query.desk === 'crossSpread') return 'crossSpread';
    return 'funding';
  });

  const currentDeskConfig = computed(
    () => desks.find((item) => item.key === currentKey.value) || desks[0],
  );

  watch(
    currentKey,
    (deskKey) => {
      activeSection.value = 'analysis';

      if (deskKey === 'funding') {
        selectedVenue.value = fundingVenueOptions[0];
        return;
      }

      const config = desks.find((item) => item.key === deskKey);
      if (!config) return;

      selectedVenue.value = config.venueOptions[0] || '';
      selectedMainLeg.value = config.mainLegOptions[0] || '';
      selectedHedgeLeg.value = config.hedgeLegOptions[0] || '';
    },
    { immediate: true },
  );

  function selectDesk(key: string) {
    router.replace({ path: '/strategy/platform', query: { desk: key as DeskKey } });
  }
</script>

<style scoped lang="less">
  @import '../strategy/shared/strategy-theme.less';

  .platform-page {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 6px 4px 0;
  }

  .section-switcher,
  .strategy-top-toolbar :deep(.compact-segment-tabs) {
    margin-left: auto;
  }

  @media (max-width: 980px) {
    .section-switcher,
    .strategy-top-toolbar :deep(.compact-segment-tabs) {
      margin-left: 0;
    }
  }
</style>
