<template>
  <BasicTable @register="registerTable" body-padding="" />
</template>
<script lang="tsx" setup>
  import { BasicTable, useTable } from '@/components/Table';
  import { getBasicColumns } from './data';
  import { getMonitoringServices } from '@/api/risk/monitoring';
  import { useIntervalFn } from '@vueuse/shared';

  const [registerTable, { reload }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getMonitoringServices,
    columns: getBasicColumns(),
    showIndexColumn: false,
  });
  useIntervalFn(() => {
    reload();
  }, 1000 * 60);
</script>
