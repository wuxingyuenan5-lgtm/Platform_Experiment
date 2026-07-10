<template>
  <SimpleContainer title="站内消息">
    <div class="flex justify-between items-center pt-2">
      <div class="flex gap-4 items-center pb-2">
        <div class="flex items-center">
          <div class="color-secondary">账户名称：</div>
          <Select
            v-model:value="searchInfo.accountId"
            placeholder="请选择账户名称"
            style="width: 180px"
            :field-names="{ label: 'label', value: 'id', options: 'children' }"
            :options="productOption"
            allowClear
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">警报类型：</div>
          <Select
            allowClear
            v-model:value="searchInfo.messageType"
            placeholder="请选择警报类型"
            style="width: 180px"
            :options="noticeTypeOptions"
        /></div>
        <div class="flex items-center">
          <div class="color-secondary">风险等级：</div>
          <Select
            allowClear
            v-model:value="searchInfo.riskLevel"
            placeholder="请选择风险等级"
            style="width: 180px"
            :options="riskLevelOptions"
        /></div>
        <!-- <div class="flex items-center">
          <RangePicker v-model:value="searchInfo.timeRange" style="width: 200px" />
        </div> -->
        <Button type="primary" @click="reload">查询</Button>
      </div>
      <div class="pb-2">
        <Button type="primary" @click="postNtificationFn({ action: 'readAll' })">全部已读</Button>
      </div>
    </div>

    <BasicTable :is-scroll="false" @register="registerTable" body-padding="">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <div @click="handleExpand(record)" class="cursor-pointer text-#2C97EB">
            {{ !expandedRowKeys.includes(record.id) ? '查看' : '折叠' }}
          </div>
        </template>
      </template>
      <template #expandedRowRender="{ record }">
        <p style="margin: 0">
          {{ record.content }}
        </p>
      </template>
    </BasicTable>
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import { BasicTable, useTable } from '@/components/Table';
  import { getProductColumns } from '../data';
  import { Select, RangePicker, Button } from 'ant-design-vue';
  import { reactive, computed, nextTick, ref } from 'vue';
  import { getNtification, postNtification } from '@/api/notifications';
  import { useUserStore } from '@/store/modules/user';
  import { noticeTypeOptions, riskLevelOptions } from '@/utils/options/basicOptions';
  import { watchOnce } from '@vueuse/shared';
  import { useRoute } from 'vue-router';

  const route = useRoute();

  const userStore = useUserStore();
  const productOption = computed(() => {
    return userStore.getUserInfoAccount;
  });
  const searchInfo = reactive<any>({
    accountId: undefined,
    messageType: undefined,
    riskLevel: undefined,
    timeRange: undefined,
  });
  const expandedRowKeys = ref([]);

  const [
    registerTable,
    { reload, setTableData, updateTableData, updateTableDataRecord, getDataSource },
  ] = useTable({
    useSearchForm: false,
    immediate: false,
    api: getNtification,
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
    actionColumn: {
      width: 120,
      title: '操作',
      dataIndex: 'action',
    },
    columns: getProductColumns(),
    showIndexColumn: false,
    showExpandColumn: false,
    rowKey: 'id',
    // childrenColumnName: 'children2',
    expandedRowKeys: expandedRowKeys,
  });
  watchOnce(
    () => route,
    () => {
      nextTick(() => {
        const _params = route.query;
        if (_params?.tabKey) {
          searchInfo.messageType = _params?.tabKey;
        }
        reload();
      });
    },
    { immediate: true },
  );
  function handleExpand(params?: any) {
    // console.log('params---', params);
    if (expandedRowKeys.value.includes(params?.id)) {
      expandedRowKeys.value = expandedRowKeys.value.filter((item) => item !== params.id);
    } else {
      if (!params?.isRead) {
        postNtificationFn({ action: 'read', id: params.id });
      }
      expandedRowKeys.value.push(params?.id);
    }
  }
  async function postNtificationFn(params: any) {
    const res = await postNtification(params);
    if (res.retCode == 0) {
      if (params.action == 'read') {
        readyMsgCb(params);
      } else if (params.action == 'readAll') {
        readAllCb();
      }
    }
    // console.log('postNtification----', res);
  }
  async function readAllCb() {
    // await postNtificationFn({ action: 'readAll' });
    reload();
  }
  function readyMsgCb(params: any) {
    updateTableDataRecord(params.id, { isRead: true });
  }
</script>
