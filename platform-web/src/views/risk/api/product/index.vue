<template>
  <SimpleContainer title="API切断">
    <div class="flex justify-between items-center">
      <div class="flex gap-4 items-center pb-2 pt-4">
        <div class="flex items-center">
          <div class="color-secondary">产品：</div>
          <Input v-model:value="searchInfo.value" placeholder="产品" style="width: 200px" />
        </div>
        <!-- <div class="flex items-center">
          <div class="color-secondary">连接状态：</div>
          <Select v-model="searchInfo.symbol" placeholder="请选择标的" style="width: 180px" />
        </div> -->
        <Button class="w-74px" type="primary" @click="reload">查询</Button>
      </div>
      <!-- <Button type="primary" @click="reload">全部切断</Button> -->
    </div>

    <BasicTable @register="registerTable" body-padding="">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <div class="flex items-center gap-4">
            <Popconfirm placement="topRight" @confirm="changeSwitch(record)">
              <div
                :class="[record.is_switch ? 'text-#52C41A' : 'text-#FF4D4F', 'cursor-pointer']"
                >{{ record.is_switch ? '连接' : '切断' }}</div
              >
              <template #title>是否确认{{ record.is_switch ? '连接' : '切断' }}？</template>
            </Popconfirm>
          </div>
        </template>
      </template>
    </BasicTable>
    <!-- 谷歌验证 -->
    <GoogleCode
      ref="refGoogle"
      :type="TypeGoogleCode.PASS"
      v-model:visible="visibleGoogle"
      @confirm="handleClickConfirm"
    />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';
  import { SimpleContainer } from '@/components/Container';
  import { BasicTable, useTable } from '@/components/Table';
  import { getColumns } from './data';
  import { Select, Popconfirm, Button, Input } from 'ant-design-vue';
  import { reactive, ref } from 'vue';
  import { getStrategyConfig, postStrategyRiskSwitch } from '@/api/future';

  const visibleGoogle = ref(false); // google验证码
  const refGoogle = ref();
  let curParams = {};

  const searchInfo = reactive({
    value: undefined,
    symbol: '',
    category: '',
    timeRange: [],
  });
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getStrategyConfig,
    columns: getColumns(),
    showIndexColumn: false,
    actionColumn: {
      width: 200,
      title: '操作',
      dataIndex: 'action',
      // slots: { customRender: 'action' },
    },
  });
  function changeSwitch(params: any) {
    curParams = {
      strategyCode: params.strategyCode,
      is_switch: !params.is_switch,
    };
    visibleGoogle.value = true;
  }
  function handleClickConfirm(params: any) {
    const _params = { ...curParams, ...params };
    postStrategyRiskSwitchFn(_params);
  }
  function postStrategyRiskSwitchFn(params: any) {
    visibleGoogle.value = false;
    postStrategyRiskSwitch(params).then((res) => {
      if (res.retCode == 0) {
        reload();
      }
    });
  }
</script>
