<template>
  <div v-if="dataSource?.length > 0">
    <div class="text-base leading-6 font-500 pb-2">待处理风险</div>
    <ConfigProvider>
      <template #renderEmpty>
        <Empty :image="Empty.PRESENTED_IMAGE_SIMPLE" :imageStyle="{ fill: 'red' }" />
      </template>
      <BasicTable class="risk-table" :is-scroll="false" @register="registerTable" body-padding="">
        <template #bodyCell="{ column, index, record }">
          <template v-if="column.key === 'action'">
            <div class="flex gap-4">
              <Popover v-model:open="record.open" trigger="click" placement="leftTop">
                <template #content>
                  <div class="w-288px">
                    <Input
                      v-model:value="searchInfo.code"
                      placeholder="谷歌验证码"
                      class="has-fill mb-2"
                    />
                    <Textarea
                      v-model:value="searchInfo.remarks"
                      placeholder="填写处理备注"
                      :rows="4"
                      class="has-fill"
                    />
                    <div class="flex justify-end gap-2 pt-2">
                      <Button @click="handleCancel(index)" size="small">取消</Button>
                      <Button @click="handleSure(record, index)" type="primary" size="small"
                        >确定</Button
                      >
                    </div>
                  </div>
                </template>
                <div class="cursor-pointer text-#2FB97B">处理完成</div>
              </Popover>
              <div
                @click="handleIgnore(record)"
                v-if="record?.riskLevel != 'level4' && record?.riskLevel != 'level5'"
                class="text-[#2FB97B] cursor-pointer"
              >
                忽略
              </div>
            </div>
          </template>
        </template>
      </BasicTable>
    </ConfigProvider>

    <!-- 谷歌验证 -->
    <GoogleCode
      ref="refGoogle"
      :type="TypeGoogleCode.PASS"
      v-model:visible="visibleGoogle"
      @confirm="handleClickConfirm"
    />
  </div>
</template>
<script lang="tsx" setup>
  import GoogleCode from '@/components/google/GoogleCode.vue';
  import { TypeGoogleCode } from '@/components/google/type';
  import { Popover, Textarea, Button, Input, ConfigProvider, Empty } from 'ant-design-vue';
  import { nextTick, onMounted, ref, reactive } from 'vue';
  import { getRiskRecords, postRiskRecords } from '@/api/risk/risk';
  import { useRoute } from 'vue-router';
  import { BasicTable, useTable } from '@/components/Table';
  import { getBasicColumns } from '../data';
  import { useApiBasic } from '@/hooks/web/useApi';
  import { useEventBus } from '@vueuse/core';

  const { emit: emitBus } = useEventBus('riskChange');
  const route = useRoute();
  const visibleGoogle = ref(false); // google验证码
  const refGoogle = ref();
  let curParams = {};
  const searchInfo = reactive({
    code: undefined,
    remarks: undefined,
  });
  const dataSource = ref([]);
  const [registerTable, { updateTableData }] = useTable({
    useSearchForm: false,
    immediate: false,
    dataSource,
    columns: getBasicColumns(),
    showIndexColumn: false,
    pagination: false,
    actionColumn: {
      width: 160,
      title: '操作',
      dataIndex: 'action',
    },
  });

  function handleCancel(index: number) {
    updateTableData(index, 'open', false);
    searchInfo.code = undefined;
    searchInfo.remarks = undefined;
  }
  function handleSure(params: any, index: number) {
    updateTableData(index, 'open', false);
    handleClickConfirm({ ...searchInfo, id: params?.id, action: 'process' });
  }

  function handleIgnore(params: any) {
    curParams = {
      id: params?.id,
      action: 'ignore',
    };
    visibleGoogle.value = true;
  }
  function handleClickConfirm(params: any) {
    const _params = { ...curParams, ...params };
    useApiBasic({
      apiFn: postRiskRecords(_params),
      successFn: () => {
        console.log('成功-----');
        setTimeout(() => {
          initData();
          emitBus(_params.id);
        }, 1500);
      },
      finallyFn: () => {
        visibleGoogle.value = false;
      },
    });
  }
  onMounted(() => {
    initData();
  });
  function initData() {
    const _params = {
      isProcessed: false,
      productId: route.path.split('/').pop(),
    };
    getRiskRecordsFn(_params);
  }
  function getRiskRecordsFn(params?: any) {
    getRiskRecords(params).then((res) => {
      if (res?.retCode == 0) {
        dataSource.value = res?.data?.list || [];
      }
    });
  }
</script>
<style lang="less">
  .risk-table {
    width: 100%;
    background: #ffe5bc;
    line-height: 38px;
    text-align: left;

    thead {
      th {
        padding-left: 12px;
        border: transparent !important;
        background: #ffe5bc !important;
        color: @text-color-secondary;
        font-weight: 400;
      }
    }

    tbody {
      tr {
        td {
          padding-left: 12px;
          border: transparent !important;
          background: #ffe5bc !important;
          color: @text-color-base;
        }
      }
    }
  }
</style>
