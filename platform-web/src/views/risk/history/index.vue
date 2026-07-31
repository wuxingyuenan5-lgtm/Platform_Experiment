<template>
  <SimpleContainer title="历史数据">
    <div class="flex justify-between items-end pt-2">
      <div class="flex flex-wrap gap-4 items-center pb-2">
        <div class="flex items-center">
          <div class="color-secondary w-70px text-right">平台：</div>
          <Select
            allowClear
            v-model:value="searchInfo.platform"
            placeholder="请选择平台"
            :options="platformOptions"
            style="width: 120px"
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">产品名称：</div>
          <Select
            v-model:value="searchInfo.productCode"
            placeholder="请选择账户名称"
            style="width: 180px"
            :field-names="{ label: 'label', value: 'value', options: 'children1' }"
            :options="productOption"
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">账户名称：</div>
          <Input
            v-model:value="searchInfo.checkCode"
            placeholder="请输入账户名称"
            style="width: 150px"
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">数据类型：</div>
          <Select
            allowClear
            v-model:value="searchInfo.dataType"
            placeholder="请选择类型"
            style="width: 120px"
            :options="dataTypeOptions"
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">指标代码：</div>
          <Select
            allowClear
            v-model:value="searchInfo.metricCode"
            placeholder="请选择指标代码"
            style="width: 180px"
            :options="metricCodeOptions"
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">日期范围：</div>
          <RangePicker v-model:value="searchInfo.timeRange" style="width: 250px" />
        </div>
      </div>
      <div class="h-full flex-1 flex gap-4 justify-end items-end pb-2">
        <Button type="primary" @click="reload()">查询</Button>
        <Button type="primary" :loading="loadingExport" @click="handleClickExport()">导出</Button>
      </div>
    </div>

    <BasicTable @register="registerTable" :scroll="{ y: 'max-context' }" body-padding="" />
  </SimpleContainer>
</template>
<script lang="tsx" setup>
  import { BasicTable, useTable } from '@/components/Table';
  import { getProductColumns } from './data';
  import { Select, RangePicker, Button, Input } from 'ant-design-vue';
  import { reactive, computed, ref, watch } from 'vue';
  import { useUserStore } from '@/store/modules/user';
  import {
    platformOptions,
    dataTypeOptions,
    metricCodeOptions,
  } from '@/utils/options/basicOptions';
  import { downloadFile } from '@/utils/file/download';
  import { SimpleContainer } from '@/components/Container';
  import { getProductData, postProductData } from '@/api/risk/monitoring';

  const userStore = useUserStore();
  const productOption = computed(() => {
    return userStore.getUserInfoAccount;
  });
  // const accountOption = computed(() => {
  //   const _item = productOption.value.find((item) => {
  //     return searchInfo.productCode == item.value;
  //   });
  //   return _item?.children || [];
  // });
  // console.log('productOption-----', productOption);
  const loadingExport = ref(false);

  const searchInfo = reactive({
    productCode: undefined, // 必传
    platform: undefined, // 非必传
    checkCode: undefined, // 非必传
    dataType: undefined,
    metricCode: undefined,
    timeRange: undefined,
  });
  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    immediate: true,
    api: getProductData,
    beforeFetch(params) {
      const _params = {
        ...params,
        ...searchInfo,
      };

      if (searchInfo?.timeRange?.length > 0) {
        _params.startTime = searchInfo?.timeRange?.[0]?.format('YYYY-MM-DD') + ' 00:00:00';
        _params.endTime = searchInfo?.timeRange?.[1]?.format('YYYY-MM-DD') + ' 23:59:59';
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
      _params.startTime = _params.timeRange[0].format('YYYY-MM-DD') + ' 00:00:00';
      _params.endTime = _params.timeRange[1].format('YYYY-MM-DD') + ' 23:59:59';
    }
    loadingExport.value = true;
    postProductData(_params)
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
  watch(
    () => productOption.value,
    (cur) => {
      if (cur?.length > 0) {
        searchInfo.productCode = cur[0]?.value;
      }
    },
    { immediate: true, deep: true },
  );
</script>
