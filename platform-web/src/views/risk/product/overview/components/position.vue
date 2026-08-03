<template>
  <SimpleContainer title="仓位规模">
    <BasicTable :is-scroll="false" @register="registerTable" body-padding="" />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import { BasicTable, useTable } from '@/components/Table';
  import { getPositionColumns } from '../data';
  import { watch, nextTick } from 'vue';

  const props = defineProps({
    loading: {
      type: Boolean,
      default: false,
    },
    record: {
      type: Array as PropType<any>,
      default: () => [],
    },
  });
  const [registerTable, { setTableData }] = useTable({
    useSearchForm: false,
    immediate: false,
    dataSource: props.record,
    columns: getPositionColumns(),
    showIndexColumn: false,
  });
  watch(
    () => props.record,
    (cur) => {
      if (cur && JSON.stringify(cur) !== '{}') {
        nextTick(() => {
          setTableData(cur);
        });
      }
    },
    { immediate: true },
  );
</script>
