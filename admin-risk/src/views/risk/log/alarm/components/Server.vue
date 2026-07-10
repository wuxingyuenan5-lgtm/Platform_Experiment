<template>
  <div>
    <div class="flex justify-between items-center">
      <div class="flex gap-4 items-center pb-2">
        <div class="flex items-center">
          <div class="color-secondary">服务器编号：</div>
          <Select v-model="searchInfo.symbol" placeholder="请选择标的" style="width: 100px" />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">产品类型：</div>
          <Select v-model="searchInfo.category" placeholder="请选择标的" style="width: 100px" />
        </div>
        <div class="flex items-center">
          <!-- <div class="color-secondary">标的：</div> -->
          <RangePicker v-model="searchInfo.timeRange" style="width: 200px" />
        </div>
        <Button type="primary" @click="reload">查询</Button>
      </div>
      <div>
        <Button type="primary" @click="reload">导出</Button>
      </div>
    </div>

    <BasicTable @register="registerTable" body-padding="" />
  </div>
</template>
<script lang="tsx" setup>
  import { BasicTable, useTable } from '@/components/Table';
  import { getServerColumns } from '../data';
  import { Select, RangePicker, Button } from 'ant-design-vue';
  import { reactive } from 'vue';

  const searchInfo = reactive({
    symbol: '',
    category: '',
    timeRange: [],
  });
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: false,
    // api: getMt5HistoryOrders,
    columns: getServerColumns(),
    showIndexColumn: false,
  });
</script>
