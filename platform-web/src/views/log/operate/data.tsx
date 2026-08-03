// import { ColumnType } from 'ant-design-vue/lib/table';
import { useI18n } from '@/hooks/web/useI18n';
import { BasicColumn } from '@/components/Table';
import { FormSchema } from '@/components/Form';
import {
  execTypeOptions,
  categoryTypeOptions,
  logStatusOptions,
} from '@/utils/options/basicOptions';
// import { getMonitorSymbol, getCheckCode } from '@/api/monitor';
import { formatToDateTime } from '@/utils/dateUtil';
import { formateNumStr, formatNumberWithCommas } from '@/utils/formate';
import { TextTranslate } from '@/components/OptionTranslate';
import { getAccountList } from '@/api/sys/accountDirectory';

const { t } = useI18n();

export function getBasicColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'name',
      title: '用户名',
    },
    {
      dataIndex: 'operationType',
      title: '操作类型',
    },
    {
      dataIndex: 'operationContent',
      title: '操作内容',
      ellipsis: true,
    },
    {
      dataIndex: 'operationIp',
      title: '操作IP',
    },
    {
      dataIndex: 'operationStatus',
      title: '操作状态',
      customRender: ({ text }) => <TextTranslate value={text ? 1 : 0} options={logStatusOptions} />,
    },
    {
      dataIndex: 'operationModule',
      title: '操作模块',
    },
    {
      dataIndex: 'operationDetail',
      title: '操作详情',
      ellipsis: true,
      customRender({ text }) {
        return text || '- -';
      },
    },
    {
      dataIndex: 'operationTime',
      title: '操作时间',
      width: 200,
      customRender: ({ record }) =>
        record.operationTime ? formatToDateTime(record.operationTime) : '- -',
    },
  ];
}

export function setSchemas(
  fieldValueChange?: Function,
  selectChange?: Function,
  optionChange?: Function,
): FormSchema[] {
  return [
    {
      field: 'userId',
      component: 'ApiSelect',
      label: '用户名',
      colProps: {
        span: 6,
      },
      componentProps: {
        showSearch: true,
        api: getAccountList,
        labelField: 'name',
        valueField: 'id',
        resultField: 'data',
        filterOption: (input, option) => {
          return option?.label.toLocaleLowerCase().includes(input?.toLocaleLowerCase());
        },
      },
    },
    {
      field: 'operationModule',
      component: 'Input',
      label: '操作模块',
      colProps: {
        span: 6,
      },
    },
    {
      field: 'operationStatus',
      component: 'Select',
      label: '操作状态',
      colProps: {
        span: 6,
      },
      componentProps: {
        options: logStatusOptions,
      },
    },
    {
      field: 'timeRange',
      component: 'RangePicker',
      label: t('account.timeRange'),
      colProps: {
        span: 6,
      },
      componentProps: {
        class: 'w-full',
      },
      colSlot: 'timeRange',
    },
  ];
}
