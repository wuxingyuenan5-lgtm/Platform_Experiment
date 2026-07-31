import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { transferTypeOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import SliderInput from '@/components/Input/SliderInput.vue';
import { formateNumStr } from '@/utils/formate';
import { FormSchema } from '@/components/Form';

export function getColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'transferTypeDisplay',
      title: '转账类型',
    },
    {
      dataIndex: 'currency',
      title: '划转币种',
    },
    {
      dataIndex: 'thresholdAmount',
      title: '最小调拨金额',
      customRender: ({ text }) => (text ? formateNumStr(text) : '- -'),
    },
    {
      dataIndex: 'updateTime',
      title: '修改时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
    {
      dataIndex: 'description',
      title: '描述',
      customRender: ({ text }) => text || '- -',
    },
  ];
}

export const schemas: FormSchema[] = [
  {
    field: 'currency',
    component: 'Input',
    label: '划转币种',
    dynamicDisabled: true,
  },
  {
    field: 'transferType',
    component: 'Select',
    label: '转账类型',
    dynamicDisabled: true,
    componentProps: {
      options: transferTypeOptions,
    },
  },
  {
    field: 'thresholdAmount',
    component: 'InputNumber',
    label: '最小调拨金额',
    required: true,
    componentProps: {
      class: 'w-full',
    },
  },
  {
    field: 'description',
    component: 'InputTextArea',
    label: '描述',
  },
  {
    field: 'code',
    component: 'Input',
    required: true,
    label: '谷歌验证码',
  },
];
