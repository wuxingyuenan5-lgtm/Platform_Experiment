<script setup lang="ts">
  import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';

  type ImportanceFilterId = 'all' | 'focus' | 'high';
  type CountryOptionId =
    | 'us'
    | 'cn'
    | 'eu'
    | 'jp'
    | 'gb'
    | 'au'
    | 'nz'
    | 'ca'
    | 'ch';

  interface CountryOption {
    id: CountryOptionId;
    label: string;
    code: string;
  }

  const widgetHostRef = ref<HTMLDivElement | null>(null);
  const selectedCountries = ref<CountryOptionId[]>(['us', 'cn']);
  const selectedImportance = ref<ImportanceFilterId>('focus');
  let widgetScript: HTMLScriptElement | null = null;

  const countryOptions: CountryOption[] = [
    { id: 'us', label: '美国', code: 'us' },
    { id: 'cn', label: '中国', code: 'cn' },
    { id: 'eu', label: '欧洲', code: 'eu' },
    { id: 'jp', label: '日本', code: 'jp' },
    { id: 'gb', label: '英国', code: 'gb' },
    { id: 'au', label: '澳洲', code: 'au' },
    { id: 'nz', label: '新西兰', code: 'nz' },
    { id: 'ca', label: '加拿大', code: 'ca' },
    { id: 'ch', label: '瑞士', code: 'ch' },
  ];

  const importanceOptions: Array<{ id: ImportanceFilterId; label: string }> = [
    { id: 'all', label: '全部' },
    { id: 'focus', label: '中高 / 高' },
    { id: 'high', label: '仅高' },
  ];

  const countryFilterValue = computed(() =>
    selectedCountries.value
      .map((id) => countryOptions.find((item) => item.id === id)?.code)
      .filter(Boolean)
      .join(','),
  );

  const importanceFilterValue = computed(() => {
    if (selectedImportance.value === 'high') return '1';
    if (selectedImportance.value === 'focus') return '0,1';
    return '-1,0,1';
  });

  async function renderWidget() {
    await nextTick();

    const host = widgetHostRef.value;
    if (!host) return;

    host.innerHTML = '';

    widgetScript = document.createElement('script');
    widgetScript.src = 'https://s3.tradingview.com/external-embedding/embed-widget-events.js';
    widgetScript.async = true;
    widgetScript.type = 'text/javascript';
    widgetScript.innerHTML = JSON.stringify({
      colorTheme: 'light',
      isTransparent: true,
      width: '100%',
      height: 920,
      locale: 'zh_CN',
      importanceFilter: importanceFilterValue.value,
      countryFilter: countryFilterValue.value || 'us,cn',
    });

    host.appendChild(widgetScript);
  }

  function toggleCountry(countryId: CountryOptionId) {
    const current = new Set(selectedCountries.value);

    if (current.has(countryId)) {
      if (current.size === 1) return;
      current.delete(countryId);
    } else {
      current.add(countryId);
    }

    selectedCountries.value = countryOptions
      .map((item) => item.id)
      .filter((id) => current.has(id));
    renderWidget();
  }

  function setImportance(importanceId: ImportanceFilterId) {
    selectedImportance.value = importanceId;
    renderWidget();
  }

  onMounted(() => {
    renderWidget();
  });

  onBeforeUnmount(() => {
    if (widgetScript?.parentNode) {
      widgetScript.parentNode.removeChild(widgetScript);
    }
    widgetScript = null;
    if (widgetHostRef.value) {
      widgetHostRef.value.innerHTML = '';
    }
  });
</script>

<template>
  <section class="macro-calendar-panel">
    <div class="macro-calendar-panel__header">
      <div>
        <h3>宏观日历</h3>
      </div>

      <div class="macro-calendar-panel__actions">
        <button class="macro-calendar-panel__action" type="button" @click="renderWidget">
          刷新
        </button>
      </div>
    </div>

    <div class="macro-calendar-panel__filters">
      <div class="macro-calendar-panel__filter-group">
        <span class="macro-calendar-panel__filter-label">国家</span>
        <div class="macro-calendar-panel__chips">
          <button
            v-for="item in countryOptions"
            :key="item.id"
            type="button"
            class="macro-calendar-panel__chip"
            :class="{ 'is-active': selectedCountries.includes(item.id) }"
            @click="toggleCountry(item.id)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>

      <div class="macro-calendar-panel__filter-group">
        <span class="macro-calendar-panel__filter-label">重要性</span>
        <div class="macro-calendar-panel__chips">
          <button
            v-for="item in importanceOptions"
            :key="item.id"
            type="button"
            class="macro-calendar-panel__chip"
            :class="{ 'is-active': selectedImportance === item.id }"
            @click="setImportance(item.id)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>
    </div>

    <div class="macro-calendar-panel__widget-shell">
      <div ref="widgetHostRef" class="macro-calendar-panel__widget-host"></div>
    </div>
  </section>
</template>

<style scoped lang="less">
  .macro-calendar-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
    border: 1px solid rgba(193, 207, 220, 0.9);
    border-radius: 28px;
    background:
      radial-gradient(circle at top right, rgba(226, 237, 247, 0.82), transparent 36%),
      linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(245, 249, 252, 0.98));
    padding: 22px 22px 24px;
    box-shadow: 0 18px 42px rgba(15, 23, 42, 0.045);
  }

  .macro-calendar-panel__header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
  }

  .macro-calendar-panel__eyebrow {
    margin: 0 0 8px;
    font-size: 13px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #8298a8;
  }

  .macro-calendar-panel__header h3 {
    margin: 4px 0 0;
    font-size: 32px;
    line-height: 1.1;
    color: #18313c;
  }

  .macro-calendar-panel__actions {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 10px;
  }

  .macro-calendar-panel__action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 82px;
    min-height: 38px;
    border: 1px solid rgba(191, 203, 214, 0.92);
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.92);
    padding: 0 14px;
    font-size: 14px;
    font-weight: 600;
    color: #35576d;
    cursor: pointer;
    transition:
      transform 0.2s ease,
      border-color 0.2s ease,
      box-shadow 0.2s ease;
  }

  .macro-calendar-panel__action:hover,
  .macro-calendar-panel__chip:hover {
    transform: translateY(-1px);
    border-color: rgba(87, 118, 142, 0.42);
    box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
  }

  .macro-calendar-panel__filters {
    display: flex;
    flex-direction: column;
    gap: 14px;
    padding: 16px 18px;
    border: 1px solid rgba(209, 220, 229, 0.88);
    border-radius: 20px;
    background: rgba(250, 252, 254, 0.9);
  }

  .macro-calendar-panel__filter-group {
    display: flex;
    align-items: flex-start;
    gap: 14px;
  }

  .macro-calendar-panel__filter-label {
    width: 72px;
    padding-top: 8px;
    color: #6d8495;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    flex: 0 0 auto;
  }

  .macro-calendar-panel__chips {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .macro-calendar-panel__chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 36px;
    border: 1px solid rgba(197, 209, 219, 0.92);
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.95);
    padding: 0 14px;
    color: #4a6679;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition:
      transform 0.2s ease,
      border-color 0.2s ease,
      box-shadow 0.2s ease,
      background-color 0.2s ease,
      color 0.2s ease;
  }

  .macro-calendar-panel__chip.is-active {
    border-color: rgba(76, 113, 141, 0.72);
    background: linear-gradient(180deg, rgba(231, 239, 246, 0.98), rgba(242, 247, 251, 0.98));
    color: #18313c;
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
  }

  .macro-calendar-panel__widget-shell {
    overflow: hidden;
    border: 1px solid rgba(201, 213, 223, 0.92);
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.92);
    padding: 8px;
  }

  .macro-calendar-panel__widget-host {
    min-height: 920px;
  }

  @media (max-width: 900px) {
    .macro-calendar-panel {
      padding: 18px;
    }

    .macro-calendar-panel__header,
    .macro-calendar-panel__filter-group {
      flex-direction: column;
    }

    .macro-calendar-panel__header h3 {
      font-size: 28px;
    }

    .macro-calendar-panel__actions,
    .macro-calendar-panel__filter-label {
      width: 100%;
      justify-content: flex-start;
    }

    .macro-calendar-panel__filter-label {
      padding-top: 0;
    }

    .macro-calendar-panel__widget-host {
      min-height: 980px;
    }
  }
</style>
