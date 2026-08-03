<template>
  <SimpleContainer title="仓位规模">
    <BasicTable @register="registerTable" :is-scroll="false" body-padding="" />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import { BasicTable, useTable } from '@/components/Table';
  import { getPositionFutureColumns } from '../data';
  import { ref, reactive, computed, watch, nextTick } from 'vue';
  import { getFutureStrategyPosition } from '@/api/future';

  const props = defineProps({
    productChildrenRisk: {
      type: Array as PropType<any>,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
  });
  const expandedRowKeys = ref(['沪金合计']);

  const [registerTable, { reload, setLoading }] = useTable({
    useSearchForm: false,
    immediate: false,
    api: getFutureStrategyPosition,
    expandedRowKeys: expandedRowKeys,
    rowKey: 'exchange',
    beforeFetch: (params) => {
      if (props.productChildrenRisk.length > 0) {
        const _first = props.productChildrenRisk[0];
        params.checkCode = _first.checkCode;
        params.strategyCode = _first.strategy_code;
      }
    },
    columns: getPositionFutureColumns(),
    showIndexColumn: false,
  });
  watch(
    () => props.productChildrenRisk,
    (cur) => {
      if (cur.length > 0) {
        nextTick(() => {
          setLoading(true);
          reload();
        });
      }
    },
    { immediate: true },
  );
</script>
