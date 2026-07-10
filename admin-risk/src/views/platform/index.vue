<template>
  <PageWrapper title="交易平台">
    <div class="platform-page">
      <section class="platform-ribbon">
        <div class="ribbon-topline">
          <div class="desk-switcher">
            <button
              v-for="desk in desks"
              :key="desk.key"
              type="button"
              :class="{ 'is-active': desk.key === currentKey }"
              @click="selectDesk(desk.key)"
            >
              {{ desk.label }}
            </button>
          </div>

          <CompactSegmentTabs class="section-switcher" :items="platformSections" v-model="activeSection" />
        </div>

        <div class="ribbon-content">
          <div class="control-row">
            <template v-if="currentKey === 'funding'">
              <label class="control-box">
                <span>交易所</span>
                <select v-model="selectedVenue">
                  <option v-for="item in fundingVenueOptions" :key="item" :value="item">{{ item }}</option>
                </select>
              </label>

              <label class="control-box">
                <span>币种</span>
                <select v-model="selectedFundingSymbol">
                  <option v-for="item in fundingSymbols" :key="item" :value="item">{{ item }}</option>
                </select>
              </label>
            </template>

            <template v-else>
              <label class="control-box">
                <span>{{ currentDeskConfig.venueLabel }}</span>
                <select v-model="selectedVenue">
                  <option v-for="item in currentDeskConfig.venueOptions" :key="item" :value="item">{{ item }}</option>
                </select>
              </label>

              <label class="control-box">
                <span>主腿标的</span>
                <select v-model="selectedMainLeg">
                  <option v-for="item in currentDeskConfig.mainLegOptions" :key="item" :value="item">{{ item }}</option>
                </select>
              </label>

              <label class="control-box">
                <span>对冲腿标的</span>
                <select v-model="selectedHedgeLeg">
                  <option v-for="item in currentDeskConfig.hedgeLegOptions" :key="item" :value="item">{{ item }}</option>
                </select>
              </label>
            </template>

            <label class="control-box">
              <span>时间精度</span>
              <select v-model="selectedResolution">
                <option value="30分钟">30分钟</option>
                <option value="1小时">1小时</option>
                <option value="4小时">4小时</option>
              </select>
            </label>
          </div>
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
  const fundingSymbols = ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'XAUT'];
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
      hedgeLegOptions: ['XAUUSD'],
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

  const selectedVenue = ref('Bybit');
  const selectedFundingSymbol = ref('BTC');
  const selectedMainLeg = ref('XAUTUSDT.P');
  const selectedHedgeLeg = ref('XAUUSD');
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

  function selectDesk(key: DeskKey) {
    router.replace({ path: '/strategy/platform', query: { desk: key } });
  }
</script>

<style scoped lang="less">
  .platform-page {
    display: flex;
    flex-direction: column;
    gap: 16px;
    padding: 8px 4px 0;
  }

  .platform-ribbon {
    display: flex;
    flex-direction: column;
    border: 1px solid rgba(201, 164, 95, 0.1);
    border-radius: 20px;
    background:
      radial-gradient(circle at 18% 74%, rgba(101, 133, 125, 0.16) 0, rgba(101, 133, 125, 0.16) 6px, transparent 7px),
      radial-gradient(circle at 39% 56%, rgba(101, 133, 125, 0.16) 0, rgba(101, 133, 125, 0.16) 6px, transparent 7px),
      radial-gradient(circle at 82% 74%, rgba(201, 164, 95, 0.18) 0, rgba(201, 164, 95, 0.18) 6px, transparent 7px),
      linear-gradient(154deg, transparent 0 18%, rgba(149, 162, 170, 0.24) 18.2%, transparent 18.6%),
      linear-gradient(214deg, transparent 0 61%, rgba(149, 162, 170, 0.18) 61.2%, transparent 61.5%),
      linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(255, 250, 242, 0.96));
  }

  .ribbon-topline {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 16px 16px 0;
  }

  .ribbon-content {
    min-height: 126px;
    padding: 10px 16px 18px;
  }

  .desk-switcher {
    display: inline-flex;
    align-items: center;
    padding: 3px;
    border: 1px solid rgba(222, 198, 192, 0.7);
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.96);
    flex-wrap: wrap;
    gap: 4px;
  }

  .desk-switcher button {
    min-width: 88px;
    height: 34px;
    padding: 0 18px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: #7c7f86;
    font-size: 14px;
    font-weight: 700;
    cursor: pointer;
  }

  .desk-switcher .is-active {
    color: #c65e66;
    background: rgba(255, 249, 248, 0.98);
    box-shadow: inset 0 0 0 1px rgba(222, 198, 192, 0.7);
  }

  .section-switcher,
  .ribbon-topline :deep(.compact-segment-tabs) {
    margin-left: auto;
  }

  .control-row {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: flex-end;
    gap: 14px;
    min-height: 100%;
    padding-top: 20px;
    border-top: 1px solid rgba(201, 164, 95, 0.1);
  }

  .control-box {
    display: grid;
    gap: 6px;
  }

  .control-box span {
    color: #8a785e;
    font-size: 12px;
    font-weight: 700;
  }

  .control-box select {
    min-width: 148px;
    height: 42px;
    padding: 0 14px;
    border: 1px solid rgba(214, 196, 160, 0.72);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.96);
    color: #39465c;
    font-size: 14px;
  }

  @media (max-width: 980px) {
    .ribbon-topline {
      align-items: flex-start;
      flex-direction: column;
    }

    .control-row {
      justify-content: flex-start;
    }

    .section-switcher,
    .ribbon-topline :deep(.compact-segment-tabs) {
      margin-left: 0;
    }
  }
</style>
