<template>
  <section id="crypto-wealth" class="wealth-panel" data-testid="crypto-wealth-panel">
    <header class="wealth-header">
      <h2>理财信息</h2>
      <button type="button" class="reference-button" @click="openReferencePage">
        打开参考页面
      </button>
    </header>

    <div class="wealth-toolbar">
      <label>
        <span>平台</span>
        <select v-model="filters.exchange">
          <option value="all">全部平台</option>
          <option v-for="item in exchangeOptions" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>
      </label>
      <label>
        <span>派息</span>
        <select v-model="filters.frequency">
          <option value="all">不限派息</option>
          <option value="daily">每日派息</option>
          <option value="fixed">固定期限</option>
          <option value="floating">浮动利率</option>
        </select>
      </label>
      <label>
        <span>期限</span>
        <select v-model="filters.lock">
          <option value="all">不限期限</option>
          <option value="short">7 天以内</option>
          <option value="mid">30 天以内</option>
          <option value="long">长期</option>
        </select>
      </label>
      <label>
        <span>搜索</span>
        <input v-model="filters.keyword" placeholder="搜索平台、币种或活动" />
      </label>
    </div>

    <div class="wealth-table-head">
      <span>活动</span>
      <span>平台 / 币种</span>
      <button type="button" @click="toggleYieldSort">
        收益率 {{ sortOrder === 'desc' ? '↓' : '↑' }}
      </button>
      <span>期限 / 锁仓</span>
      <span>到期时间</span>
      <span>活动说明</span>
    </div>

    <div v-if="!filteredCampaigns.length" class="wealth-empty">暂无匹配活动</div>
    <div v-else class="wealth-list">
      <article v-for="item in filteredCampaigns" :key="item.id" class="wealth-row">
        <div>
          <strong>{{ item.name }}</strong>
          <div class="wealth-tags">
            <span v-for="tag in item.tags" :key="tag">{{ tag }}</span>
          </div>
        </div>
        <div
          ><strong>{{ item.platform }}</strong
          ><p>{{ item.coin }}</p></div
        >
        <div class="wealth-yield"
          ><strong>{{ item.apy }}</strong
          ><p>{{ item.apyNote }}</p></div
        >
        <div
          ><strong>{{ lockLabel(item.lock) }}</strong
          ><p>{{ frequencyLabel(item.frequency) }}</p></div
        >
        <div
          ><strong :class="{ 'is-urgent': item.daysLeft <= 1 }">{{ item.expiryLabel }}</strong
          ><p>{{ item.expiryNote }}</p></div
        >
        <p>{{ item.description }}</p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
  import { computed, reactive, ref } from 'vue';
  import { wealthCampaigns, type WealthFrequency, type WealthLock } from '@/data/sample/news';

  type SortOrder = 'desc' | 'asc';

  const sortOrder = ref<SortOrder>('desc');
  const filters = reactive({ exchange: 'all', frequency: 'all', lock: 'all', keyword: '' });
  const exchangeOptions = [
    { value: 'gate', label: 'Gate' },
    { value: 'aave', label: 'Aave' },
    { value: 'binance', label: 'Binance' },
    { value: 'bitget', label: 'Bitget' },
    { value: 'okx', label: 'OKX' },
    { value: 'bybit', label: 'Bybit' },
  ];

  const filteredCampaigns = computed(() => {
    const keyword = filters.keyword.trim().toLowerCase();
    return wealthCampaigns
      .filter((item) => {
        if (filters.exchange !== 'all' && item.exchange !== filters.exchange) return false;
        if (filters.frequency !== 'all' && item.frequency !== filters.frequency) return false;
        if (filters.lock !== 'all' && item.lock !== filters.lock) return false;
        return (
          !keyword ||
          [item.name, item.platform, item.coin].join(' ').toLowerCase().includes(keyword)
        );
      })
      .slice()
      .sort((left, right) =>
        sortOrder.value === 'desc'
          ? right.apyValue - left.apyValue
          : left.apyValue - right.apyValue,
      );
  });

  function toggleYieldSort() {
    sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc';
  }
  function openReferencePage() {
    window.open('https://app.barker.money/campaigns', '_blank', 'noopener,noreferrer');
  }
  function frequencyLabel(value: WealthFrequency) {
    return { daily: '每日派息', fixed: '固定期限', floating: '浮动利率' }[value];
  }
  function lockLabel(value: WealthLock) {
    return { short: '7 天以内', mid: '30 天以内', long: '长期' }[value];
  }
</script>

<style scoped lang="less">
  .wealth-panel {
    display: grid;
    gap: 16px;
    margin-top: 14px;
    padding: 18px;
    border: 1px solid #dbe4ed;
    border-radius: 10px;
    background: #fff;
    box-shadow: 0 1px 3px rgb(15 23 42 / 6%);
  }

  .wealth-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 14px;
  }

  h2 {
    margin: 0;
    color: #17212f;
    font-size: 20px;
    font-weight: 800;
  }

  .reference-button {
    height: 34px;
    padding: 0 14px;
    border: 1px solid #d8e2ee;
    border-radius: 8px;
    background: #fff;
    color: #294a67;
    font-weight: 700;
  }

  .wealth-toolbar {
    display: grid;
    grid-template-columns: repeat(3, minmax(140px, 180px)) minmax(220px, 1fr);
    gap: 10px;
  }

  label {
    display: grid;
    gap: 6px;
  }

  label span {
    color: #667085;
    font-size: 12px;
    font-weight: 700;
  }

  select,
  input {
    min-width: 0;
    height: 36px;
    padding: 0 10px;
    border: 1px solid #dce3eb;
    border-radius: 8px;
    background: #fff;
  }

  .wealth-table-head,
  .wealth-row {
    display: grid;
    grid-template-columns: 1.1fr 0.9fr 0.8fr 0.7fr 0.8fr 1.15fr;
    align-items: start;
    gap: 12px;
  }

  .wealth-table-head {
    padding: 0 12px;
    color: #778396;
    font-size: 12px;
    font-weight: 700;
  }

  .wealth-table-head button {
    border: 0;
    background: transparent;
    color: inherit;
    text-align: left;
  }

  .wealth-list {
    display: grid;
    gap: 8px;
  }

  .wealth-empty {
    padding: 28px 16px;
    border: 1px dashed #d8e0ea;
    border-radius: 10px;
    background: #fafbfd;
    color: #667085;
    text-align: center;
  }

  .wealth-row {
    padding: 14px;
    border: 1px solid #e5eaf0;
    border-radius: 10px;
    background: #fafbfd;
  }

  .wealth-row strong {
    color: #172033;
  }

  .wealth-row p {
    margin: 4px 0 0;
    color: #7b8798;
    font-size: 12px;
    line-height: 1.65;
  }

  .wealth-yield strong {
    color: #225a96;
    font-size: 20px;
  }

  .is-urgent {
    color: #b42318 !important;
  }

  .wealth-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 8px;
  }

  .wealth-tags span {
    padding: 4px 7px;
    border-radius: 999px;
    background: #eef3f8;
    color: #526b82;
    font-size: 11px;
  }

  @media (max-width: 1200px) {
    .wealth-table-head,
    .wealth-row {
      grid-template-columns: 1fr 0.8fr 0.75fr;
    }
  }

  @media (max-width: 900px) {
    .wealth-toolbar {
      grid-template-columns: 1fr;
    }

    .wealth-table-head {
      display: none;
    }
  }

  @media (max-width: 620px) {
    .wealth-row {
      grid-template-columns: 1fr;
    }
  }
</style>
