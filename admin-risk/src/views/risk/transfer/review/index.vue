<template>
  <SimpleContainer title="调拨审核">
    <div class="flex gap-4 items-center pb-2 pt-4">
      <div class="flex items-center">
        <div class="color-secondary">发起人：</div>
        <Input
          v-model:value="searchInfo.userName"
          placeholder="请输入发起人"
          style="width: 120px"
        />
      </div>
      <div class="flex items-center">
        <div class="color-secondary">审核人：</div>
        <Input
          v-model:value="searchInfo.reviewerName"
          placeholder="请输入审核人"
          style="width: 120px"
        />
      </div>
      <div class="flex items-center">
        <div class="color-secondary">调拨模式：</div>
        <Select
          v-model:value="searchInfo.transferType"
          :options="transferTypeOptions"
          allowClear
          placeholder="请选择模式"
          style="width: 120px"
        />
      </div>
      <div class="flex items-center">
        <div class="color-secondary">调拨风险等级：</div>
        <Select
          v-model:value="searchInfo.riskLevel"
          placeholder="请选择风险等级"
          allowClear
          style="width: 150px"
          :options="riskLevelOptions2"
        />
      </div>
      <div class="flex items-center">
        <div class="color-secondary">审核状态：</div>
        <Select
          v-model:value="searchInfo.status"
          :options="auditStatusOptions"
          allowClear
          placeholder="请选择审核状态"
          style="width: 150px"
        />
      </div>
      <div class="flex items-center">
        <!-- <div class="color-secondary">标的：</div> -->
        <RangePicker v-model:value="searchInfo.timeRange" style="width: 240px" />
      </div>
      <div class="flex-1 flex justify-between gap-4">
        <div class="flex gap-2">
          <Button :loading="loading" class="w-74px" @click="resetState">重置</Button>
          <Button :loading="loading" class="w-74px" type="primary" @click="() => reload()"
            >查询</Button
          >
        </div>

        <Button class="w-74px" type="primary" :loading="loadingExport" @click="handleClickExport"
          >导出</Button
        >
      </div>
    </div>
    <BasicTable @register="registerTable" body-padding="">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <div v-if="record.status === 'pending'" class="flex items-center gap-4">
            <div
              @click="handleEdit({ ...record, action: 'approve' })"
              class="text-#2C97EB cursor-pointer"
              >同意</div
            >
            <div
              @click="handleEdit({ ...record, action: 'reject' })"
              class="cursor-pointer text-#FF4D4F"
              >驳回</div
            >
          </div>
        </template>
      </template>
    </BasicTable>

    <!-- 编辑 -->
    <EditModal ref="editModal" @success="editSuccess" :record="curCreate" />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { SimpleContainer } from '@/components/Container';
  import { BasicTable, useTable } from '@/components/Table';
  import { getColumns } from './data';
  import { Select, RangePicker, Button, Input } from 'ant-design-vue';
  import { reactive, ref } from 'vue';
  import { getTransferRequests, postTransferRequests } from '@/api/risk/transfer';
  import EditModal from './components/Edit.vue';
  import {
    riskLevelOptions2,
    auditStatusOptions,
    transferTypeOptions,
  } from '@/utils/options/basicOptions';
  import { downloadFile } from '@/utils/file/download';

  const loading = ref(false);
  const loadingExport = ref(false);
  const curCreate = ref<any>();
  const editModal = ref();
  const searchInfoInit = {
    userName: undefined,
    reviewerName: undefined,
    transferType: undefined,
    riskLevel: undefined,
    status: undefined,
    timeRange: [],
  };
  const searchInfo = reactive({ ...searchInfoInit });
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getTransferRequests,
    columns: getColumns(),
    showIndexColumn: false,
    beforeFetch: (params) => {
      const _params = {
        ...params,
        ...searchInfo,
      };
      if (_params.timeRange?.length) {
        _params.startTime = _params.timeRange[0].format('YYYY-MM-DD');
        _params.endTime = _params.timeRange[1].format('YYYY-MM-DD');
      }
      return _params;
    },
    actionColumn: {
      width: 200,
      title: '操作',
      dataIndex: 'action',
      // slots: { customRender: 'action' },
    },
  });
  function editSuccess(params: any) {
    reload();
    editModal.value.openModal(false);
  }
  function handleEdit(record: Recordable | null) {
    curCreate.value = record;
    editModal.value.openModal(true);
  }
  function handleClickExport() {
    const _params = {
      ...searchInfo,
    };
    if (_params.timeRange?.length) {
      _params.startTime = _params.timeRange[0].format('YYYY-MM-DD');
      _params.endTime = _params.timeRange[1].format('YYYY-MM-DD');
    }
    loadingExport.value = true;
    postTransferRequests(_params)
      .then((res) => {
        const disposition = res?.headers?.['content-disposition'] || '';
        if (disposition) {
          let _fileName = disposition.match(/filename=(.*)/)?.[1];
          if (_fileName) {
            _fileName = decodeURIComponent(_fileName.replace(/['"]/g, ''));
          }
          downloadFile(res.data, _fileName);
        }
      })
      .finally(() => {
        loadingExport.value = false;
      });
  }
  function resetState() {
    Object.assign(searchInfo, searchInfoInit);
  }
</script>
