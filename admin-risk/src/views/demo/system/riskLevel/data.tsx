import { BasicColumn } from '@/components/Table';
import { TextTranslate } from '@/components/OptionTranslate';
import { yesNoOptions, riskLevelOptions } from '@/utils/options/basicOptions';
import { formatToDateTime, formatToDate, dateUtil } from '@/utils/dateUtil';
import SliderInput from '@/components/Input/SliderInput.vue';
import { FormSchema } from '@/components/Form';

export function getColumns(): BasicColumn[] {
  return [
    {
      dataIndex: 'riskLevel',
      title: '风险等级',
      customRender: ({ text }) => (
        <TextTranslate
          options={riskLevelOptions.map((item) => ({
            label: item.grade,
            value: item.value,
            color: item.color,
          }))}
          value={text}
        />
      ),
    },
    {
      dataIndex: 'isIgnorable',
      title: '是否可忽略',
      customRender: ({ text }) => <TextTranslate options={yesNoOptions} value={text} />,
    },
    {
      dataIndex: 'reminderInterval',
      title: '提醒间隔时间(M)',
    },
    {
      dataIndex: 'ignoreInterval',
      title: '忽略时间间隔(M)',
      customRender: ({ text }) => (text ? text : '- -'),
    },
    {
      dataIndex: 'updateTime',
      title: '修改时间',
      customRender: ({ text }) => (text ? formatToDateTime(text) : '- -'),
    },
  ];
}

export const schemas: FormSchema[] = [
  {
    field: 'riskLevelDisplay',
    component: 'Input',
    label: '风险等级',
    dynamicDisabled: true,
  },
  // {
  //   field: 'isIgnorable',
  //   component: 'Switch',
  //   label: '是否可忽略',
  //   dynamicDisabled: true,
  // },
  {
    field: 'reminderInterval',
    component: 'Input',
    label: '提醒间隔时间',
    componentProps: {
      addonAfter: 'M',
    },
  },
  {
    field: 'ignoreInterval',
    component: 'Input',
    label: '忽略时间间隔',
    componentProps: {
      addonAfter: 'M',
    },
  },
  {
    field: 'code',
    component: 'Input',
    required: true,
    label: '谷歌验证码',
  },
];
