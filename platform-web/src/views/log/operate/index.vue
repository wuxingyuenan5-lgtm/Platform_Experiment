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
            :filter-option="
              (input, option) => {
                return option?.label.toLocaleLowerCase().includes(input?.toLocaleLowerCase());
              }
            "
            :options="accountOptions"
            allowClear
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">操作模块：</div>
          <Input
            v-model:value="searchInfo.operationModule"
            placeholder="请输入操作模块"
            style="width: 180px"
            allowClear
          />
        </div>
        <div class="flex items-center">
          <div class="color-secondary">操作状态：</div>
          <Select
            allowClear
            v-model:value="searchInfo.operationStatus"
            placeholder="请选择操作状态"
            style="width: 180px"
            :options="logStatusOptions"
        /></div>
        <div class="flex items-center">
          <RangePicker style="width: 250px" v-model:value="searchInfo.timeRange" />
        </div>
        <Button type="primary" @click="reload()">查询</Button>
      </div>
      <div class="pb-2">
        <Button type="primary" @click="handleClickExport">导出</Button>
      </div>
    </div>
    <BasicTable @register="registerTable" body-padding="">
      <!-- <template #form-timeRange="{ model, field }">
        <FormItem :labelCol="labelCol" :name="field" :label="t('account.timeRange')">
          <RangePicker
            :value="hackValue || model[field]"
            @change="
              (val) => {
                model[field] = val;
              }
            "
            @openChange="onOpenChange"
            @calendarChange="onCalendarChange"
            class="w-full"
          />
        </FormItem>
      </template> -->
      <!-- <template #form-advanceAfter>
        <Button
          :loading="loading"
          type="primary"
          @click="handleClickExport"
          class="is-green min-w-15 ml-2"
        >
          <span>导出</span>
        </Button>
      </template> -->
    </BasicTable>
  </SimpleContainer>
</template>
<script lang="ts" setup>
  import { SimpleContainer, CollapseContainer } from '@/components/Container';

  import { ref, computed, watch, reactive, onMounted } from 'vue';
  import { BasicTable, useTable } from '@/components/Table';
  import { getBasicColumns, setSchemas } from './data';
  import { getOperationLogs, postOperationLogs } from '@/api/quantSystem';
  import { Select, FormItem, RangePicker, Cascader, Input, Button } from 'ant-design-vue';
  // import { useSymbol, useUserInfo } from '@/utils/options/useBasicOptions';
  import { Dayjs } from 'dayjs';
  import { useMessage } from '@/hooks/web/useMessage';
  import { useI18n } from '@/hooks/web/useI18n';
  import { downloadFile } from '@/utils/file/download';
  import { getAccountList } from '@/api/sys/accountDirectory';
  import { logStatusOptions } from '@/utils/options/basicOptions';

  const { createMessage } = useMessage();

  const searchInfo = reactive({
    userId: undefined,
    operationModule: undefined,
    operationStatus: undefined,
    timeRange: undefined,
  });
  const accountOptions = ref();

  type RangeValue = [Dayjs, Dayjs];
  const dates = ref<RangeValue>();
  const hackValue = ref<RangeValue>();
  const loading = ref(false);

  const onOpenChange = (open: boolean) => {
    if (open) {
      dates.value = [] as any;
      hackValue.value = [] as any;
    } else {
      hackValue.value = undefined;
    }
  };

  const onCalendarChange = (val: RangeValue) => {
    dates.value = val;
  };

  const labelCol = { style: { width: '100px' } };

  const [registerTable, { reload, getForm }] = useTable({
    useSearchForm: false,
    size: 'small',
    // formConfig: {
    //   // labelWidth: 100,
    //   actionColOptions: { span: 24 },
    //   submitOnReset: false,
    //   schemas: setSchemas(),
    // },
    api: getOperationLogs,
    beforeFetch: (params) => {
      const _params = {
        ...params,
        ...searchInfo,
      };

      if (searchInfo?.timeRange?.length > 0) {
        _params.startTime = searchInfo?.timeRange?.[0]?.format('YYYY-MM-DD') + ' ' + '00:00:00';
        _params.endTime = searchInfo?.timeRange?.[1]?.format('YYYY-MM-DD') + ' ' + '23:59:59';
      }
      console.log('_params----', _params);

      return _params;
    },
    columns: getBasicColumns(),
    showIndexColumn: false,
  });

  function handleClickExport() {
    loading.value = true;
    const _params = {
      ...searchInfo,
    };
    // const { getFieldsValue } = getForm();
    // let _params = getFieldsValue();
    if (_params.timeRange?.length > 0) {
      _params.startTime = _params.timeRange[0].split(' ')[0] + ' ' + '00:00:00';
      _params.endTime = _params.timeRange[1].split(' ')[0] + ' ' + '23:59:59';
    }

    postOperationLogs(_params)
      .then((res) => {
        if (res?.type == 'application/json') {
          var reader = new FileReader();
          reader.readAsText(res, 'utf-8');
          reader.onload = function (e) {
            const _res = JSON.parse(reader.result);
            createMessage.error(_res?.msg || '操作失败！');
          };
        } else {
          let _fileName = '操作日志';
          if (_params.timeRange?.length > 0) {
            _fileName +=
              '_' +
              _params.startTime.replaceAll('-', '').split(' ')?.[0] +
              '_' +
              _params.endTime.replaceAll('-', '').split(' ')?.[0];
          }
          downloadFile(res, _fileName);
        }
      })
      .finally(() => {
        loading.value = false;
      });
  }
  function getAccountListFn() {
    getAccountList().then((res) => {
      if (res.retCode == 0) {
        accountOptions.value = res?.data?.map((item) => {
          return {
            label: item.name,
            value: item.id,
          };
        });
      }
    });
  }
  onMounted(() => {
    getAccountListFn();
  });
</script>
