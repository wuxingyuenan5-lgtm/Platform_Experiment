<template>
  <SimpleContainer title="平台操作日志">
    <div class="flex justify-between items-center pt-2">
      <div class="flex gap-4 items-center pb-2">
        <div class="flex items-center">
          <div class="color-secondary">用户名：</div>
          <Select
            v-model:value="searchInfo.userId"
            placeholder="请选择用户名"
            style="width: 180px"
            show-search
            :filter-option="filterAccountOption"
            :options="accountOptions"
            allow-clear
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">操作模块：</div>
          <Input
            v-model:value="searchInfo.operationModule"
            placeholder="请输入操作模块"
            style="width: 180px"
            allow-clear
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">操作状态：</div>
          <Select
            v-model:value="searchInfo.operationStatus"
            allow-clear
            placeholder="请选择操作状态"
            style="width: 180px"
            :options="logStatusOptions"
          />
        </div>
        <div class="flex items-center">
          <RangePicker v-model:value="searchInfo.timeRange" style="width: 250px" />
        </div>
        <Button type="primary" @click="reload()">查询</Button>
      </div>
      <div class="pb-2">
        <Button type="primary" :loading="exporting" @click="handleClickExport">导出</Button>
      </div>
    </div>
    <BasicTable @register="registerTable" body-padding="" />
  </SimpleContainer>
</template>

<script lang="ts" setup>
  import type { Dayjs } from 'dayjs';
  import { onMounted, reactive, ref } from 'vue';
  import { Button, Input, RangePicker, Select } from 'ant-design-vue';
  import { getOperationLogs, postOperationLogs } from '@/api/quantSystem';
  import { getAccountList } from '@/api/sys/accountDirectory';
  import { SimpleContainer } from '@/components/Container';
  import { BasicTable, useTable } from '@/components/Table';
  import { useMessage } from '@/hooks/web/useMessage';
  import { downloadFile } from '@/utils/file/download';
  import { logStatusOptions } from '@/utils/options/basicOptions';
  import { getBasicColumns } from './data';

  type RangeValue = [Dayjs, Dayjs];

  interface OperationLogSearchInfo {
    userId?: number;
    operationModule?: string;
    operationStatus?: string | number;
    timeRange?: RangeValue;
    startTime?: string;
    endTime?: string;
  }

  interface AccountOption {
    label: string;
    value: number;
  }

  const { createMessage } = useMessage();
  const exporting = ref(false);
  const accountOptions = ref<AccountOption[]>([]);
  const searchInfo = reactive<OperationLogSearchInfo>({});

  const [registerTable, { reload }] = useTable({
    useSearchForm: false,
    size: 'small',
    api: getOperationLogs,
    beforeFetch: (params) => ({ ...params, ...buildRequestParams() }),
    columns: getBasicColumns(),
    showIndexColumn: false,
  });

  function filterAccountOption(input: string, option?: AccountOption) {
    return Boolean(option?.label.toLocaleLowerCase().includes(input.toLocaleLowerCase()));
  }

  function buildRequestParams(): OperationLogSearchInfo {
    const params: OperationLogSearchInfo = {
      userId: searchInfo.userId,
      operationModule: searchInfo.operationModule,
      operationStatus: searchInfo.operationStatus,
    };
    const range = searchInfo.timeRange;
    if (range?.length === 2) {
      params.startTime = `${range[0].format('YYYY-MM-DD')} 00:00:00`;
      params.endTime = `${range[1].format('YYYY-MM-DD')} 23:59:59`;
    }
    return params;
  }

  async function handleClickExport() {
    exporting.value = true;
    const params = buildRequestParams();
    try {
      const response = await postOperationLogs(params);
      if (response?.type === 'application/json') {
        const text = await response.text();
        const payload = JSON.parse(text || '{}') as { msg?: string };
        createMessage.error(payload.msg || '操作失败！');
        return;
      }

      let fileName = '操作日志';
      if (params.startTime && params.endTime) {
        fileName += `_${params.startTime.replaceAll('-', '').split(' ')[0]}_${params.endTime
          .replaceAll('-', '')
          .split(' ')[0]}`;
      }
      downloadFile(response, fileName);
    } finally {
      exporting.value = false;
    }
  }

  async function loadAccountOptions() {
    const result = await getAccountList();
    accountOptions.value = result.items.map((item) => ({
      label: item.name,
      value: item.id,
    }));
  }

  onMounted(() => void loadAccountOptions());
</script>