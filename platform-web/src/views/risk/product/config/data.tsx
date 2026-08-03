import { BasicColumn, FormSchema, FormProps } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
// import { serverStatusOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';

export function getStrategyColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'factorName',
      title: '因子名称',
    },
    {
      dataIndex: 'factorCode',
      title: '代码',
    },
    {
      dataIndex: 'level1threshold',
      title: '一级',
    },
    {
      dataIndex: 'level2threshold',
      title: '二级',
    },
    {
      dataIndex: 'level3threshold',
      title: '三级',
    },
    {
      dataIndex: 'level4threshold',
      title: '四级',
    },
    {
      dataIndex: 'level5threshold',
      title: '五级',
    },
    {
      dataIndex: 'updateTime',
      title: '更新时间',
      customRender: ({ text }) => {
        return formatToDateTime(text);
      },
    },
  ];
}

export const schemasStrategy: FormSchema[] = [
  {
    field: 'productId',
    component: 'Input',
    show: false,
  },
  {
    field: 'factorName',
    component: 'Input',
    label: '因子名称',
    required: true,
  },
  {
    field: 'factorCode',
    component: 'Input',
    label: '代码',
    required: true,
  },
  {
    field: 'level1threshold',
    component: 'Input',
    label: '一级',
    required: true,
  },
  {
    field: 'level2threshold',
    component: 'Input',
    label: '二级',
    required: true,
  },
  {
    field: 'level3threshold',
    component: 'Input',
    label: '三级',
    required: true,
  },
  {
    field: 'level4threshold',
    component: 'Input',
    label: '四级',
    required: true,
  },
  {
    field: 'level5threshold',
    component: 'Input',
    label: '五级',
    required: true,
  },
  {
    field: 'code',
    component: 'Input',
    required: true,
    label: '谷歌验证码',
  },
];
