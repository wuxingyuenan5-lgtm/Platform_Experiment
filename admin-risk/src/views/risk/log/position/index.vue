<template>
  <SimpleContainer title="平仓日志">
    <div class="flex justify-between items-center pt-2">
      <div class="flex gap-4 items-center pb-2">
        <div class="flex items-center">
          <div class="color-secondary">产品名称：</div>
          <Select
            v-model:value="searchInfo.productId"
            placeholder="请选择账户名称"
            style="width: 180px"
            :field-names="{ label: 'label', value: 'id' }"
            :options="productOption"
            allowClear
          />
        </div>
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
        <div class="flex items-center">
          <RangePicker v-model:value="searchInfo.timeRange" style="width: 250px" />
        </div>
        <Button type="primary" @click="reload()">查询</Button>
      </div>
      <!-- <div class="pb-2">
        <Button type="primary" @click="reload">导出</Button>
      </div> -->
    </div>

    <BasicTable :is-scroll="false" @register="registerTable" body-padding="">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <div @click="handleDetail(record)" class="cursor-pointer text-#2C97EB">详情</div>
        </template>
      </template>
    </BasicTable>
    <!-- 编辑 -->
    <DetailModal ref="detailModal" :record="curCreate" />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { BasicTable, useTable } from '@/components/Table';
  import { SimpleContainer } from '@/components/Container';
  import { getColumns } from './data';
  import { Select, RangePicker, Button, Input } from 'ant-design-vue';
  import { reactive, ref, computed } from 'vue';
  import { getExecutionTasks } from '@/api/risk/execution';
  import DetailModal from './components/detail.vue';
  import { useUserStore } from '@/store/modules/user';
  import { closeLogStatusOptions } from '@/utils/options/basicOptions';

  const userStore = useUserStore();
  const productOption = computed(() => {
    return userStore.getUserInfoAccount;
  });
  const curCreate = ref<any>();
  const detailModal = ref();

  const searchInfo = reactive({
    productId: undefined,
    symbol: undefined,
    status: undefined,
    timeRange: undefined,
  });
  const [registerTable, { reload }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getExecutionTasks,
    beforeFetch(params) {
      const _params = {
        ...params,
        ...searchInfo,
      };
      if (searchInfo?.timeRange?.length > 0) {
        _params.startTime = searchInfo?.timeRange?.[0]?.format('YYYY-MM-DD') + ' ' + '00:00:00';
        _params.endTime = searchInfo?.timeRange?.[1]?.format('YYYY-MM-DD') + ' ' + '23:59:59';
      }
      // console.log('_params----', _params);

      return _params;
    },
    columns: getColumns(),
    showIndexColumn: false,
    actionColumn: {
      width: 100,
      title: '操作',
      dataIndex: 'action',
    },
  });
  function handleDetail(record: any) {
    curCreate.value = record;
    detailModal.value?.openModal();
  }
</script>
