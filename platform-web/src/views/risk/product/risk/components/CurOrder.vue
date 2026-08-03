<template>
  <SimpleContainer title="当前订单">
    <div class="flex gap-4 items-center pb-2 pt-4">
      <div class="flex items-center">
        <div class="color-secondary">标的类型：</div>
        <Select
          v-model:value="currentParame.category"
          :options="categoryTypeOptions"
          placeholder="请选择类型"
          style="width: 180px"
        />
      </div>
    </div>
    <BasicTable
      :can-click-item="true"
      body-padding=""
      :scroll="bodyScroll"
      @register="registerTableCurrent"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <div class="flex justify-center">
            <div>
              <GhostButton
                @click="handleClick({ type: 'cancel', data: record })"
                size="small"
                color="error"
                >取消
              </GhostButton>
            </div>
          </div>
        </template>
      </template>
    </BasicTable>
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import { Button, Select, Segmented } from 'ant-design-vue';
  import { nextTick, reactive, ref } from 'vue';
  import { categoryTypeOptions } from '@/utils/options/basicOptions';
  import { BasicTable, useTable } from '@/components/Table';
  import GhostButton from '@/components/Button/src/GhostButton.vue';
  import { getCurrentOrderSchemas } from '../data';
  import { useIntervalCustom } from '@/hooks/event/useIntervalCustom';

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
  console.log('props=====', props);

  const bodyScroll = ref({
    x: 'max-content',
    y: 'max-content',
  });
  const currentParame = reactive({
    category: 'spot',
  });
  // 当前订单数据定时刷新
  const { start, stop } = useIntervalCustom(reloadTable, { immediate: false, delay: 5000 });

  const [registerTableCurrent, { reload: reloadCurrent, setLoading: setLoadingCurrent }] = useTable(
    {
      // api: getExecutionOrder,
      immediate: false,
      size: 'small',
      columns: getCurrentOrderSchemas(),
      beforeFetch: (params) => {
        params.accountId = props.account?.checkCode;
        params.category = currentParame.category;
        stop();
      },
      // afterFetch: (data: any) => {
      //   const _len = data?.length || 0;
      //   changeTabVal(_len, OrderType.CURRENT);
      // },
      showIndexColumn: false,
      rowKey: 'id',
      actionColumn: {
        width: 120,
        title: '操作',
        dataIndex: 'action',
      },
    },
  );
  function handleClick(params: any) {
    switch (params.type) {
      case 'cancel':
        const _params = {
          action: 'cancel',
          accountId: props.account?.checkCode,
          symbol: params.data.symbol,
          orderId: params.data.orderId,
          category: currentParame.category,
        };
        // postExecutionOrderFn(_params);
        break;
    }
  }
  function reloadTable() {
    nextTick(() => {
      // TODO 当前订单目前只有海外交易
      reloadCurrent();
    });
  }
</script>
