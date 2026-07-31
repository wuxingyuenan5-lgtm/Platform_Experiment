<template>
  <SimpleContainer title="风险处理日志">
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
          <div class="color-secondary">风险类型：</div>
          <Select
            allowClear
            v-model:value="searchInfo.riskType"
            placeholder="请选择风险类型"
            style="width: 180px"
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">风险等级：</div>
          <Select
            allowClear
            v-model:value="searchInfo.riskLevel"
            placeholder="请选择风险等级"
            style="width: 180px"
            :options="riskLevelOptions"
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">风险状态：</div>
          <Select
            allowClear
            v-model:value="searchInfo.isProcessed"
            placeholder="请选择风险状态"
            style="width: 180px"
            :options="riskStatusOptions"
          />
        </div>
        <div class="flex items-center">
          <!-- <div class="color-secondary">标的：</div> -->
          <RangePicker v-model:value="searchInfo.timeRange" style="width: 250px" />
        </div>
        <Button type="primary" @click="reload()">查询</Button>
      </div>
      <div class="pb-2">
        <Button type="primary" :loading="loadingExport" @click="handleClickExport()">导出</Button>
      </div>
    </div>

    <BasicTable @register="registerTable" :scroll="{ y: 'max-context' }" body-padding="" />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { BasicTable, useTable } from '@/components/Table';
  import { getProductColumns } from '../data';
  import { Select, RangePicker, Button } from 'ant-design-vue';
  import { reactive, computed, ref } from 'vue';
  import { getRiskRecords, postRiskRecordsExport } from '@/api/risk/risk';
  import { useUserStore } from '@/store/modules/user';
  import { riskLevelOptions, riskStatusOptions } from '@/utils/options/basicOptions';
  import { downloadFile } from '@/utils/file/download';
  import { SimpleContainer } from '@/components/Container';

  const userStore = useUserStore();
  const productOption = computed(() => {
    return userStore.getUserInfoAccount;
  });
  console.log('productOption-----', productOption);
  const loadingExport = ref(false);

  const searchInfo = reactive({
    productId: undefined,
    accountId: undefined,
    riskType: undefined,
    riskLevel: undefined,
    isProcessed: undefined,
    timeRange: undefined,
  });
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getRiskRecords,
    beforeFetch(params) {
      const _params = {
        ...params,
        ...searchInfo,
      };

      if (searchInfo?.timeRange?.length > 0) {
        _params.startTime = searchInfo?.timeRange?.[0]?.format('YYYY-MM-DD') + ' ' + '00:00:00';
        _params.endTime = searchInfo?.timeRange?.[1]?.format('YYYY-MM-DD') + ' ' + '23:59:59';
      }

      return _params;
    },
    columns: getProductColumns(),
    showIndexColumn: false,
  });
  function handleClickExport() {
    const _params = {
      ...searchInfo,
    };
    if (_params.timeRange?.length) {
      _params.startTime = _params.timeRange[0].format('YYYY-MM-DD') + ' ' + '00:00:00';
      _params.endTime = _params.timeRange[1].format('YYYY-MM-DD') + ' ' + '23:59:59';
    }
    loadingExport.value = true;
    postRiskRecordsExport(_params)
      .then((res) => {
        const disposition =
          res?.headers?.['Content-Disposition'] || res?.headers?.['content-disposition'] || '';
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
</script>
