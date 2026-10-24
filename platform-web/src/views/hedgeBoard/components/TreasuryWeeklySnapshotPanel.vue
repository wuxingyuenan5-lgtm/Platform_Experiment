<template
  ><div
    ><p v-if="snapshot?.observedAt"
      >快照时间 {{ new Date(snapshot.observedAt).toLocaleString('zh-CN') }}</p
    ><img
      v-if="snapshot?.status === 'ready' && !imageError"
      :src="`/api/v1/research/crypto/treasury-weekly-snapshot/image?t=${encodeURIComponent(
        snapshot.observedAt ?? '',
      )}`"
      alt="BTC财库公司周度变化网页快照"
      style="width: 100%; height: auto"
      @error="imageError = true"
    /><p v-else>暂无可核验的周度快照。</p
    ><a
      href="https://sosovalue.com/zh/assets/bitcoin-treasuries/weekly-net-inflow"
      target="_blank"
      rel="noopener noreferrer"
      >参考网页 ↗</a
    ></div
  ></template
>
<script setup lang="ts">
  import { onMounted, ref } from 'vue';
  import { getTreasuryWeeklySnapshot } from '@/api/hedgeResearch';

  const snapshot = ref<Awaited<ReturnType<typeof getTreasuryWeeklySnapshot>> | null>(null);
  const imageError = ref(false);
  onMounted(async () => {
    try {
      snapshot.value = await getTreasuryWeeklySnapshot();
    } catch {
      imageError.value = true;
    }
  });
</script>
