import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { yesNoOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import { FormSchema } from '@/components/Form';

export function getBasicColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'jobId',
      title: '任务ID',
    },
    {
      dataIndex: 'name',
      title: '任务名称',
    },
    {
      dataIndex: 'minute',
      title: '分钟配置',
    },
    {
      dataIndex: 'hour',
      title: '小时配置',
    },
    {
      dataIndex: 'description',
      title: '任务描述',
    },
    {
      dataIndex: 'isActivate',
      title: '是否启用',
      customRender: ({ text }) => <TextTranslate value={text} type="dot" options={yesNoOptions} />,
    },
    {
      dataIndex: 'expireTimeLimit',
      title: '过期时间限制',
      customRender: ({ text }) => text || '- -',
    },
  ];
}

export const schemas: FormSchema[] = [
  {
    field: 'jobId',
    component: 'Input',
    label: '任务ID',
    required: true,
  },
  {
    field: 'name',
    component: 'Input',
    label: '任务名称',
    required: true,
  },
  {
    field: 'minute',
    component: 'Input',
    label: '分钟配置',
  },
  {
    field: 'hour',
    component: 'Input',
    label: '小时配置',
  },
  {
    field: 'expireTimeLimit',
    component: 'Input',
    label: '过期时间限制',
  },
  {
    field: 'isActivate',
    component: 'Switch',
    label: '是否启用',
  },
  {
    field: 'description',
    component: 'Input',
    label: '任务描述',
  },
  {
    field: 'code',
    component: 'Input',
    required: true,
    label: '谷歌验证码',
  },
];
