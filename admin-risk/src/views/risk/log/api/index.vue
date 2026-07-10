<template>
  <SimpleContainer title="API操作日志">
    <div class="flex justify-between items-center pt-2">
      <div class="flex gap-4 items-center pb-2">
        <div class="flex items-center">
          <div class="color-secondary">账户编号：</div>
          <Select style="width: 180px" v-model:value="searchInfo.symbol" placeholder="请选择标的" />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">标的名称：</div>
          <Select
            style="width: 180px"
            v-model:value="searchInfo.category"
            placeholder="请选择标的"
          />
        </div>
        <div class="flex items-center">
          <!-- <div class="color-secondary">标的：</div> -->
          <RangePicker v-model:value="searchInfo.timeRange" style="width: 250px" />
        </div>
        <Button type="primary" @click="reload">查询</Button>
      </div>
      <!-- <div>
        <Button type="primary" @click="reload">导出</Button>
      </div> -->
    </div>

    <BasicTable @register="registerTable" body-padding="" />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { BasicTable, useTable } from '@/components/Table';
  import { SimpleContainer } from '@/components/Container';
  import { getColumns } from './data';
  import { Select, RangePicker, Button } from 'ant-design-vue';
  import { reactive } from 'vue';

  const searchInfo = reactive({
    symbol: undefined,
    category: undefined,
    timeRange: undefined,
  });
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: false,
    // api: getMt5HistoryOrders,
    columns: getColumns(),
    showIndexColumn: false,
  });
</script>
