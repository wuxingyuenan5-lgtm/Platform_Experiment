<template>
  <SimpleContainer title="平仓日志">
    <div class="flex gap-4 items-center pb-2 pt-4">
      <div class="flex items-center">
        <div class="color-secondary">标的名称：</div>
        <Input v-model:value="searchInfo.symbol" placeholder="请选择标的" style="width: 180px" />
      </div>
      <div class="flex items-center">
        <div class="color-secondary">状态：</div>
        <Select
          v-model:value="searchInfo.status"
          :options="closeLogStatusOptions"
          placeholder="请选择状态"
          style="width: 180px"
          allowClear
        />
      </div>
      <!-- <div class="flex items-center">
        <div class="color-secondary">操作类型：</div>
        <Select v-model="searchInfo.category" placeholder="请选择标的" style="width: 100px" />
      </div> -->
      <div class="flex items-center">
        <!-- <div class="color-secondary">标的：</div> -->
        <RangePicker v-model:value="searchInfo.timeRange" style="width: 250px" />
      </div>
      <Button type="primary" @click="reload()">查询</Button>
    </div>
    <BasicTable :is-scroll="false" @register="registerTable" body-padding="" />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import { BasicTable, useTable } from '@/components/Table';
  import { getLogColumns, setSchemas } from '../data';
  import { Select, RangePicker, Button, Input } from 'ant-design-vue';
  import { nextTick, reactive, watch } from 'vue';
  import { getExecutionTasks } from '@/api/risk/execution';
  import { closeLogStatusOptions } from '@/utils/options/basicOptions';

  const props = defineProps({
    product: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
    account: {
      type: Object as PropType<any>,
      default: () => ({}),
    },
  });
  const searchInfo = reactive({
    symbol: undefined,
    status: undefined,
    timeRange: undefined,
  });
  const [registerTable, { reload }] = useTable({
    useSearchForm: false,
    immediate: false,
    api: getExecutionTasks,
    beforeFetch(params) {
      console.log('account======', props.account);
      const _params = {
        ...params,
        ...searchInfo,
        productId: props.product?.id,
        accountId: props.account?.accountId,
      };
      if (searchInfo?.timeRange?.length > 0) {
        _params.startTime = searchInfo?.timeRange?.[0]?.format('YYYY-MM-DD') + ' ' + '00:00:00';
        _params.endTime = searchInfo?.timeRange?.[1]?.format('YYYY-MM-DD') + ' ' + '23:59:59';
      }
      return _params;
    },
    columns: getLogColumns(),
    showIndexColumn: false,
  });
  watch(
    () => props.product,
    (cur) => {
      if (cur && cur.id) {
        nextTick(() => {
          reload();
        });
      }
    },
    { immediate: true },
  );
  watch(
    () => props.account,
    (cur) => {
      if (cur && cur.accountId) {
        nextTick(() => {
          reload();
        });
      }
    },
    { immediate: true },
  );
  defineExpose({
    reload,
  });
</script>
